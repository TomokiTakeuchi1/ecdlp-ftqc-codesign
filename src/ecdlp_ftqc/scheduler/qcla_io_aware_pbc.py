"""Finite-capacity QCLA adaptive-PBC scheduling with explicit memory moves."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, replace
from itertools import pairwise
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaTrace
from ecdlp_ftqc.codes import PbcMittenBackendConfig
from ecdlp_ftqc.compiler.qcla_pbc import (
    QclaAdaptivePbcLowering,
    lower_qcla_to_adaptive_pbc,
)
from ecdlp_ftqc.io import (
    QclaFixedOrderSchedule,
    QclaMemoryProgram,
    TransferAction,
    TransferKind,
    adapt_qcla_schedule_to_memory_program,
    qcla_fixed_order_schedule_to_data,
    schedule_qcla_fixed_order_belady,
)
from ecdlp_ftqc.io.model import MemoryIoError
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler.adaptive_pbc import (
    AdaptivePbcSchedule,
    schedule_adaptive_pbc_greedy,
)
from ecdlp_ftqc.scheduler.io_aware_pbc import (
    IoAwareComputeEvent,
    MemoryIoTimingConfig,
    ScheduledMemoryTransfer,
)

QCLA_IO_AWARE_POLICY = "qcla_relaxed_order_then_fixed_belady_no_overlap_v1"


class UnsupportedQclaMemoryIoScheduleError(ValueError):
    """Raised when strict mode would consume unresolved timing assumptions."""


@dataclass(frozen=True, slots=True)
class ResourceStateDemandPoint:
    """Aggregate T-state demand at one shifted PBC event start round."""

    start_round: int
    demand: int
    event_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QclaIoAwarePbcSchedule:
    """Fixed-order realizable upper bound under finite J300 logical capacity."""

    trace_id: str
    configuration_id: str
    allow_check_assumptions: bool
    policy_identity: str
    scratch_slot_count: int
    source_logical_capacity: int
    total_logical_capacity: int
    ordering_capacity: int
    high_rate_enabled: bool
    factory_mode: str
    base_scheduled_rounds: int
    scheduled_rounds: int
    added_rounds: int
    transfer_action_rounds: int
    timing_evidence_status: EvidenceStatus
    clean_ancilla_timing_evidence_status: EvidenceStatus
    base_strict_executable: bool
    lowering: QclaAdaptivePbcLowering
    base_schedule: AdaptivePbcSchedule
    memory_program: QclaMemoryProgram
    placement: QclaFixedOrderSchedule
    transfers: tuple[ScheduledMemoryTransfer, ...]
    compute_events: tuple[IoAwareComputeEvent, ...]
    resource_state_demand: tuple[ResourceStateDemandPoint, ...]

    @property
    def strict_executable(self) -> bool:
        return (
            self.base_strict_executable
            and self.timing_evidence_status is not EvidenceStatus.CHECK
            and self.clean_ancilla_timing_evidence_status is not EvidenceStatus.CHECK
        )

    @property
    def high_rate_batch_count(self) -> int:
        return self.base_schedule.high_rate_batch_count

    @property
    def total_resource_state_demand(self) -> int:
        return sum(point.demand for point in self.resource_state_demand)

    @property
    def peak_resource_state_burst(self) -> int:
        return max((point.demand for point in self.resource_state_demand), default=0)


def _schedule_transfer_phase(
    actions: tuple[TransferAction, ...],
    *,
    boundary_ready: int,
    duration: int,
    lane_count: int,
    first_transfer_index: int,
    evidence: EvidenceStatus,
) -> tuple[tuple[ScheduledMemoryTransfer, ...], int]:
    lane_available = [boundary_ready] * lane_count
    transfers: list[ScheduledMemoryTransfer] = []
    for offset, action in enumerate(actions):
        lane = min(range(lane_count), key=lambda index: (lane_available[index], index))
        start = lane_available[lane]
        end = start + duration
        transfers.append(
            ScheduledMemoryTransfer(
                transfer_id=f"qcla-transfer:{first_transfer_index + offset:06d}",
                boundary_index=action.boundary_index,
                value_id=action.value_id,
                kind=action.kind,
                reason=action.reason,
                lane=lane,
                start_round=start,
                end_round=end,
                timing_evidence_status=evidence,
            )
        )
        lane_available[lane] = end
    return tuple(transfers), max(lane_available, default=boundary_ready)


def _schedule_boundary_transfers(
    actions: tuple[TransferAction, ...],
    *,
    boundary_ready: int,
    config: MemoryIoTimingConfig,
    first_transfer_index: int,
) -> tuple[tuple[ScheduledMemoryTransfer, ...], int]:
    stores = tuple(action for action in actions if action.kind is TransferKind.STORE)
    loads = tuple(action for action in actions if action.kind is TransferKind.LOAD)
    if actions != stores + loads:
        raise MemoryIoError("QCLA boundary must store before loading replacements")
    scheduled_stores, stores_done = _schedule_transfer_phase(
        stores,
        boundary_ready=boundary_ready,
        duration=config.store_rounds,
        lane_count=config.transfer_lanes,
        first_transfer_index=first_transfer_index,
        evidence=config.timing_evidence_status,
    )
    scheduled_loads, loads_done = _schedule_transfer_phase(
        loads,
        boundary_ready=stores_done,
        duration=config.load_rounds,
        lane_count=config.transfer_lanes,
        first_transfer_index=first_transfer_index + len(stores),
        evidence=config.timing_evidence_status,
    )
    return scheduled_stores + scheduled_loads, loads_done


def _demand_series(
    base_schedule: AdaptivePbcSchedule,
    compute_events: tuple[IoAwareComputeEvent, ...],
) -> tuple[ResourceStateDemandPoint, ...]:
    shifted = {event.event_id: event for event in compute_events}
    demand_by_round: dict[int, int] = defaultdict(int)
    events_by_round: dict[int, list[str]] = defaultdict(list)
    for event in base_schedule.events:
        if event.resource_state_demand == 0:
            continue
        start = shifted[event.event_id].start_round
        demand_by_round[start] += event.resource_state_demand
        events_by_round[start].append(event.event_id)
    return tuple(
        ResourceStateDemandPoint(
            start_round=start,
            demand=demand_by_round[start],
            event_ids=tuple(sorted(events_by_round[start])),
        )
        for start in sorted(demand_by_round)
    )


def schedule_qcla_io_aware_pbc(
    trace: QclaTrace,
    backend_config: PbcMittenBackendConfig,
    io_config: MemoryIoTimingConfig,
    *,
    scratch_slot_count: int,
    enable_high_rate: bool,
    allow_check_assumptions: bool = False,
) -> QclaIoAwarePbcSchedule:
    """Select a deterministic compute order, then realize it within J300.

    The adaptive-PBC list scheduler is run with capacity relaxed only enough to
    select a complete event order.  That order is not called executable.  The
    epoch-aware placement and transfer overlay enforce the actual capacity.
    """

    if io_config.logical_qubits != backend_config.logical_qubits:
        raise ValueError("QCLA backend and memory-I/O logical capacities disagree")
    if scratch_slot_count < 1 or scratch_slot_count >= io_config.logical_qubits:
        raise ValueError("QCLA scratch count must leave positive source capacity")
    if io_config.timing_evidence_status is EvidenceStatus.CHECK and not allow_check_assumptions:
        raise UnsupportedQclaMemoryIoScheduleError(
            "strict QCLA I/O-aware schedule rejected CHECK transfer durations"
        )
    if not allow_check_assumptions:
        raise UnsupportedQclaMemoryIoScheduleError(
            "strict QCLA I/O-aware schedule rejected CHECK clean-ancilla "
            "allocation/release timing"
        )
    lowering = lower_qcla_to_adaptive_pbc(trace)
    ordering_capacity = lowering.pbc_trace.peak_source_processor_occupancy + scratch_slot_count
    relaxed_backend = replace(backend_config, logical_qubits=ordering_capacity)
    base_schedule = schedule_adaptive_pbc_greedy(
        lowering.pbc_trace,
        relaxed_backend,
        scratch_slot_count=scratch_slot_count,
        enable_high_rate=enable_high_rate,
        allow_check_assumptions=allow_check_assumptions,
    )
    program = adapt_qcla_schedule_to_memory_program(trace, lowering.logical, base_schedule)
    source_capacity = io_config.logical_qubits - scratch_slot_count
    placement = schedule_qcla_fixed_order_belady(program, source_capacity)

    actions_by_boundary: list[list[TransferAction]] = [
        [] for _ in range(len(base_schedule.events) + 1)
    ]
    for action in placement.actions:
        actions_by_boundary[action.boundary_index].append(action)
    delay_offset = 0
    prior_compute_end = 0
    zero_latency = io_config.load_rounds == 0 and io_config.store_rounds == 0
    transfers: list[ScheduledMemoryTransfer] = []
    compute_events: list[IoAwareComputeEvent] = []
    for boundary_index, base_event in enumerate(base_schedule.events):
        nominal_start = base_event.start_round + delay_offset
        boundary_actions = tuple(actions_by_boundary[boundary_index])
        boundary_ready = (
            base_event.start_round
            if zero_latency
            else (max(nominal_start, prior_compute_end) if boundary_actions else nominal_start)
        )
        scheduled_transfers, transfer_ready = _schedule_boundary_transfers(
            boundary_actions,
            boundary_ready=boundary_ready,
            config=io_config,
            first_transfer_index=len(transfers),
        )
        transfers.extend(scheduled_transfers)
        start = base_event.start_round if zero_latency else max(nominal_start, transfer_ready)
        duration = base_event.end_round - base_event.start_round
        end = start + duration
        if not zero_latency:
            delay_offset = max(delay_offset, start - base_event.start_round)
        prior_compute_end = max(prior_compute_end, end)
        compute_events.append(
            IoAwareComputeEvent(
                event_id=base_event.event_id,
                operation_ids=base_event.operation_ids,
                source_primitive_ids=base_event.source_primitive_ids,
                base_start_round=base_event.start_round,
                base_end_round=base_event.end_round,
                start_round=start,
                end_round=end,
                transfer_ready_round=transfer_ready,
            )
        )
    final_transfers, final_ready = _schedule_boundary_transfers(
        tuple(actions_by_boundary[-1]),
        boundary_ready=(base_schedule.scheduled_rounds if zero_latency else prior_compute_end),
        config=io_config,
        first_transfer_index=len(transfers),
    )
    transfers.extend(final_transfers)
    scheduled_rounds = max(prior_compute_end, final_ready)
    compute_tuple = tuple(compute_events)
    schedule = QclaIoAwarePbcSchedule(
        trace_id=lowering.pbc_trace.trace_id,
        configuration_id=io_config.configuration_id,
        allow_check_assumptions=allow_check_assumptions,
        policy_identity=QCLA_IO_AWARE_POLICY,
        scratch_slot_count=scratch_slot_count,
        source_logical_capacity=source_capacity,
        total_logical_capacity=io_config.logical_qubits,
        ordering_capacity=ordering_capacity,
        high_rate_enabled=enable_high_rate,
        factory_mode="ideal_supply_no_stalls_demand_trace_only",
        base_scheduled_rounds=base_schedule.scheduled_rounds,
        scheduled_rounds=scheduled_rounds,
        added_rounds=scheduled_rounds - base_schedule.scheduled_rounds,
        transfer_action_rounds=sum(
            transfer.end_round - transfer.start_round for transfer in transfers
        ),
        timing_evidence_status=io_config.timing_evidence_status,
        clean_ancilla_timing_evidence_status=EvidenceStatus.CHECK,
        base_strict_executable=base_schedule.strict_executable,
        lowering=lowering,
        base_schedule=base_schedule,
        memory_program=program,
        placement=placement,
        transfers=tuple(transfers),
        compute_events=compute_tuple,
        resource_state_demand=_demand_series(base_schedule, compute_tuple),
    )
    validate_qcla_io_aware_pbc(io_config, schedule)
    return schedule


def validate_qcla_io_aware_pbc(
    io_config: MemoryIoTimingConfig, schedule: QclaIoAwarePbcSchedule
) -> None:
    """Replay combined timing, capacity, lane, event, and demand invariants."""

    base_schedule = schedule.base_schedule
    if schedule.policy_identity != QCLA_IO_AWARE_POLICY:
        raise MemoryIoError("QCLA I/O-aware policy identity mismatch")
    if schedule.source_logical_capacity + schedule.scratch_slot_count != (
        schedule.total_logical_capacity
    ):
        raise MemoryIoError("QCLA source and scratch capacities do not sum to J300")
    if schedule.placement.peak_source_logical_occupancy > schedule.source_logical_capacity:
        raise MemoryIoError("QCLA placement exceeds its source logical capacity")
    if len(schedule.compute_events) != len(base_schedule.events):
        raise MemoryIoError("QCLA I/O-aware event count mismatch")
    for base, shifted in zip(base_schedule.events, schedule.compute_events, strict=True):
        if (
            shifted.event_id != base.event_id
            or shifted.operation_ids != base.operation_ids
            or shifted.source_primitive_ids != base.source_primitive_ids
            or shifted.base_start_round != base.start_round
            or shifted.base_end_round != base.end_round
            or shifted.end_round - shifted.start_round != base.end_round - base.start_round
            or shifted.start_round < base.start_round
            or shifted.transfer_ready_round > shifted.start_round
        ):
            raise MemoryIoError("QCLA I/O-aware event does not preserve base compute")
    for lane in range(io_config.transfer_lanes):
        lane_transfers = sorted(
            (transfer for transfer in schedule.transfers if transfer.lane == lane),
            key=lambda transfer: (transfer.start_round, transfer.transfer_id),
        )
        for earlier, later in pairwise(lane_transfers):
            if earlier.end_round > later.start_round:
                raise MemoryIoError("QCLA transfers overlap on one lane")
    prior_compute_ends = [0]
    for event in schedule.compute_events:
        prior_compute_ends.append(max(prior_compute_ends[-1], event.end_round))
    for transfer in schedule.transfers:
        duration = (
            io_config.load_rounds if transfer.kind is TransferKind.LOAD else io_config.store_rounds
        )
        if transfer.end_round - transfer.start_round != duration:
            raise MemoryIoError("QCLA transfer duration mismatch")
        prior_end = prior_compute_ends[transfer.boundary_index]
        if transfer.start_round < prior_end:
            raise MemoryIoError("QCLA transfer overlaps prior compute")
        if (
            transfer.boundary_index < len(schedule.compute_events)
            and transfer.end_round > schedule.compute_events[transfer.boundary_index].start_round
        ):
            raise MemoryIoError("QCLA transfer finishes after its consumer starts")
    transfer_loads = sum(transfer.kind is TransferKind.LOAD for transfer in schedule.transfers)
    transfer_stores = sum(transfer.kind is TransferKind.STORE for transfer in schedule.transfers)
    if transfer_loads != schedule.placement.loads or transfer_stores != schedule.placement.stores:
        raise MemoryIoError("QCLA timed and logical transfer counts disagree")
    if schedule.total_resource_state_demand != base_schedule.total_resource_state_demand:
        raise MemoryIoError("QCLA T-state demand is not conserved")
    expected_rounds = max(
        max((event.end_round for event in schedule.compute_events), default=0),
        max((transfer.end_round for transfer in schedule.transfers), default=0),
    )
    if (
        schedule.scheduled_rounds != expected_rounds
        or schedule.added_rounds != schedule.scheduled_rounds - schedule.base_scheduled_rounds
    ):
        raise MemoryIoError("QCLA I/O-aware makespan mismatch")


def qcla_io_aware_schedule_to_data(
    schedule: QclaIoAwarePbcSchedule,
) -> dict[str, Any]:
    """Return a compact deterministic JSON-compatible schedule summary."""

    return {
        "added_rounds": schedule.added_rounds,
        "allow_check_assumptions": schedule.allow_check_assumptions,
        "base_scheduled_rounds": schedule.base_scheduled_rounds,
        "base_strict_executable": schedule.base_strict_executable,
        "clean_ancilla_timing_evidence_status": (
            schedule.clean_ancilla_timing_evidence_status.value
        ),
        "configuration_id": schedule.configuration_id,
        "factory_mode": schedule.factory_mode,
        "high_rate_batch_count": schedule.high_rate_batch_count,
        "high_rate_enabled": schedule.high_rate_enabled,
        "ordering_capacity": schedule.ordering_capacity,
        "placement": qcla_fixed_order_schedule_to_data(schedule.placement),
        "policy_identity": schedule.policy_identity,
        "resource_state_demand_point_count": len(schedule.resource_state_demand),
        "peak_resource_state_burst": schedule.peak_resource_state_burst,
        "scheduled_rounds": schedule.scheduled_rounds,
        "scratch_slot_count": schedule.scratch_slot_count,
        "source_logical_capacity": schedule.source_logical_capacity,
        "strict_executable": schedule.strict_executable,
        "timing_evidence_status": schedule.timing_evidence_status.value,
        "total_logical_capacity": schedule.total_logical_capacity,
        "total_resource_state_demand": schedule.total_resource_state_demand,
        "trace_id": schedule.trace_id,
        "transfer_action_rounds": schedule.transfer_action_rounds,
    }


def resource_state_demand_to_data(
    schedule: QclaIoAwarePbcSchedule,
) -> list[dict[str, Any]]:
    """Serialize the complete time-stamped demand series."""

    return [
        {
            "demand": point.demand,
            "event_ids": list(point.event_ids),
            "start_round": point.start_round,
        }
        for point in schedule.resource_state_demand
    ]


def dumps_qcla_io_aware_schedule(schedule: QclaIoAwarePbcSchedule) -> str:
    """Serialize the compact schedule summary canonically."""

    return json.dumps(qcla_io_aware_schedule_to_data(schedule), indent=2, sort_keys=True) + "\n"
