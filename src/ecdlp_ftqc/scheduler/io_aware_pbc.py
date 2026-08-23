"""Conservative no-prefetch I/O overlay for a reviewed adaptive-PBC schedule."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.compiler import LogicalTrace, PbcTrace
from ecdlp_ftqc.io import (
    FixedOrderSchedule,
    MemoryIoError,
    MemoryProgram,
    MemoryUnit,
    MemoryValue,
    MemoryValueOrigin,
    TransferAction,
    TransferKind,
    TransferReason,
    adapt_gidney_dag_to_memory_program,
    schedule_fixed_order_belady,
)
from ecdlp_ftqc.metadata import CircuitDag, EvidenceStatus
from ecdlp_ftqc.scheduler.adaptive_pbc import AdaptivePbcSchedule

MEMORY_IO_TIMING_SCHEMA = "ecdlp-ftqc/memory-io-timing-config"
MEMORY_IO_TIMING_SCHEMA_VERSION = 1
NO_PREFETCH_OVERLAP_POLICY = "no_prefetch_no_compute_overlap_v1"


class UnsupportedMemoryIoTimingError(ValueError):
    """Raised when strict scheduling would use a CHECK transfer duration."""


@dataclass(frozen=True, slots=True)
class MemoryIoTimingConfig:
    """Finite transfer-lane timing used by the bounded I/O overlay."""

    configuration_id: str
    logical_qubits: int
    transfer_lanes: int
    load_rounds: int
    store_rounds: int
    timing_evidence_status: EvidenceStatus
    source_note: str
    overlap_policy: str = NO_PREFETCH_OVERLAP_POLICY
    schema: str = MEMORY_IO_TIMING_SCHEMA
    schema_version: int = MEMORY_IO_TIMING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.configuration_id or not self.source_note:
            raise ValueError("memory-I/O timing provenance cannot be empty")
        for name, value, minimum in (
            ("logical_qubits", self.logical_qubits, 1),
            ("transfer_lanes", self.transfer_lanes, 1),
            ("load_rounds", self.load_rounds, 0),
            ("store_rounds", self.store_rounds, 0),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer of at least {minimum}")
        if self.overlap_policy != NO_PREFETCH_OVERLAP_POLICY:
            raise ValueError("unsupported memory-I/O overlap policy")
        if self.schema != MEMORY_IO_TIMING_SCHEMA:
            raise ValueError("unsupported memory-I/O timing schema")
        if self.schema_version != MEMORY_IO_TIMING_SCHEMA_VERSION:
            raise ValueError("unsupported memory-I/O timing schema version")


@dataclass(frozen=True, slots=True)
class ScheduledMemoryTransfer:
    """One transfer assigned to a lane on the combined timeline."""

    transfer_id: str
    boundary_index: int
    value_id: str
    kind: TransferKind
    reason: TransferReason
    lane: int
    start_round: int
    end_round: int
    timing_evidence_status: EvidenceStatus


@dataclass(frozen=True, slots=True)
class IoAwareComputeEvent:
    """One base PBC event after conservative I/O delays are inserted."""

    event_id: str
    operation_ids: tuple[str, ...]
    source_primitive_ids: tuple[str, ...]
    base_start_round: int
    base_end_round: int
    start_round: int
    end_round: int
    transfer_ready_round: int


@dataclass(frozen=True, slots=True)
class IoAwareAdaptivePbcSchedule:
    """Combined no-prefetch logical-I/O and adaptive-PBC upper bound."""

    trace_id: str
    configuration_id: str
    allow_check_assumptions: bool
    overlap_policy: str
    scratch_slot_count: int
    available_source_logical_capacity: int
    base_scheduled_rounds: int
    scheduled_rounds: int
    added_rounds: int
    loads: int
    stores: int
    transfer_action_rounds: int
    timing_evidence_status: EvidenceStatus
    base_strict_executable: bool
    transfer_schedule: FixedOrderSchedule
    transfers: tuple[ScheduledMemoryTransfer, ...]
    compute_events: tuple[IoAwareComputeEvent, ...]

    @property
    def strict_executable(self) -> bool:
        return (
            self.base_strict_executable
            and self.timing_evidence_status is not EvidenceStatus.CHECK
        )


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{path} must be a mapping")
    return value


def _required(obj: Mapping[str, object], key: str, path: str) -> object:
    if key not in obj:
        raise ValueError(f"{path}.{key} is required")
    return obj[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a nonempty string")
    return value


def _integer(value: object, path: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{path} must be an integer of at least {minimum}")
    return value


def load_memory_io_timing_config(path: Path) -> MemoryIoTimingConfig:
    """Load a strict memory-I/O timing configuration from YAML."""

    try:
        root = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "$")
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load memory-I/O timing config {path}: {exc}") from exc
    schema = _string(_required(root, "schema", "$"), "$.schema")
    schema_version = _integer(
        _required(root, "schema_version", "$"), "$.schema_version", 1
    )
    evidence_text = _string(
        _required(root, "timing_evidence_status", "$"), "$.timing_evidence_status"
    )
    try:
        evidence = EvidenceStatus(evidence_text)
    except ValueError as exc:
        raise ValueError("$.timing_evidence_status is unsupported") from exc
    return MemoryIoTimingConfig(
        configuration_id=_string(
            _required(root, "configuration_id", "$"), "$.configuration_id"
        ),
        logical_qubits=_integer(
            _required(root, "logical_qubits", "$"), "$.logical_qubits", 1
        ),
        transfer_lanes=_integer(
            _required(root, "transfer_lanes", "$"), "$.transfer_lanes", 1
        ),
        load_rounds=_integer(
            _required(root, "load_rounds", "$"), "$.load_rounds", 0
        ),
        store_rounds=_integer(
            _required(root, "store_rounds", "$"), "$.store_rounds", 0
        ),
        timing_evidence_status=evidence,
        source_note=_string(_required(root, "source_note", "$"), "$.source_note"),
        overlap_policy=_string(
            _required(root, "overlap_policy", "$"), "$.overlap_policy"
        ),
        schema=schema,
        schema_version=schema_version,
    )


def _event_memory_program(
    dag: CircuitDag,
    logical_trace: LogicalTrace,
    base_schedule: AdaptivePbcSchedule,
) -> MemoryProgram:
    source_program = adapt_gidney_dag_to_memory_program(dag)
    primitive_to_node = {
        primitive.primitive_id: primitive.source_node_id
        for primitive in logical_trace.primitives
    }
    source_unit_by_node = {
        node_id: unit
        for unit in source_program.units
        for node_id in unit.node_ids
    }
    source_index_by_node = {
        node_id: unit.source_operation_index
        for unit in source_program.units
        for node_id in unit.node_ids
    }
    event_source_indices: list[set[int]] = []
    event_nodes: list[tuple[str, ...]] = []
    for event in base_schedule.events:
        try:
            nodes = tuple(
                sorted({primitive_to_node[value] for value in event.source_primitive_ids})
            )
        except KeyError as exc:
            raise MemoryIoError("PBC event references an unknown logical primitive") from exc
        event_nodes.append(nodes)
        event_source_indices.append({source_index_by_node[node_id] for node_id in nodes})

    remapped_values: list[MemoryValue] = []
    for value in source_program.values:
        if value.origin is MemoryValueOrigin.MEMORY_INPUT_OR_INOUT:
            remapped_values.append(value)
            continue
        assert value.birth_unit_index is not None
        assert value.release_unit_index is not None
        birth_candidates = [
            index
            for index, source_indices in enumerate(event_source_indices)
            if value.birth_unit_index in source_indices
        ]
        release_candidates = [
            index
            for index, source_indices in enumerate(event_source_indices)
            if value.release_unit_index in source_indices
        ]
        if not birth_candidates or not release_candidates:
            raise MemoryIoError(f"cannot remap lifetime of {value.value_id!r} to PBC events")
        birth = min(birth_candidates)
        release = max(release_candidates)
        if birth > release:
            raise MemoryIoError(f"PBC schedule releases {value.value_id!r} before creation")
        remapped_values.append(
            MemoryValue(
                value_id=value.value_id,
                origin=value.origin,
                initial_location=value.initial_location,
                birth_unit_index=birth,
                release_unit_index=release,
                requires_memory_residency=False,
                must_store_on_release=value.must_store_on_release,
                must_preserve_initial_state=value.must_preserve_initial_state,
            )
        )

    live_generated_by_event: list[set[str]] = [set() for _ in base_schedule.events]
    for value in remapped_values:
        if value.origin is not MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY:
            continue
        assert value.birth_unit_index is not None
        assert value.release_unit_index is not None
        for event_index in range(value.birth_unit_index, value.release_unit_index + 1):
            live_generated_by_event[event_index].add(value.value_id)

    units: list[MemoryUnit] = []
    for event_index, (event, nodes) in enumerate(
        zip(base_schedule.events, event_nodes, strict=True)
    ):
        source_units = tuple(source_unit_by_node[node_id] for node_id in nodes)
        memory_support = tuple(
            sorted({value for unit in source_units for value in unit.memory_support})
        )
        occupancy_support = tuple(
            sorted(
                {value for unit in source_units for value in unit.occupancy_support}
                | live_generated_by_event[event_index]
            )
        )
        units.append(
            MemoryUnit(
                unit_id=f"pbc-event-memory-unit:{event_index:06d}",
                source_operation_id=event.event_id,
                source_operation_index=event_index,
                node_ids=nodes,
                memory_support=memory_support,
                occupancy_support=occupancy_support,
            )
        )
    return MemoryProgram(
        circuit_id=f"{dag.circuit_id}:adaptive-pbc-event-order",
        width=dag.width,
        source_commit=source_program.source_commit,
        units=tuple(units),
        values=tuple(remapped_values),
    )


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
                transfer_id=f"transfer:{first_transfer_index + offset:06d}",
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
        raise MemoryIoError("I/O boundary must return values before loading replacements")
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


def schedule_io_aware_adaptive_pbc(
    dag: CircuitDag,
    logical_trace: LogicalTrace,
    pbc_trace: PbcTrace,
    base_schedule: AdaptivePbcSchedule,
    config: MemoryIoTimingConfig,
    *,
    allow_check_assumptions: bool = False,
) -> IoAwareAdaptivePbcSchedule:
    """Insert no-prefetch I/O before a fixed reviewed PBC event order.

    This is a deterministic realizable upper bound for that supplied order.
    It does not optimize the quantum event order jointly with placement.
    """

    if pbc_trace.trace_id != base_schedule.trace_id:
        raise ValueError("base schedule and PBC trace identity mismatch")
    if pbc_trace.source_trace_id != logical_trace.trace_id:
        raise ValueError("logical and PBC trace identity mismatch")
    if logical_trace.source_circuit_id != dag.circuit_id:
        raise ValueError("DAG and logical trace identity mismatch")
    if base_schedule.peak_total_logical_occupancy > config.logical_qubits:
        raise MemoryIoError("base schedule exceeds the I/O configuration capacity")
    event_program = _event_memory_program(dag, logical_trace, base_schedule)
    available_capacity = config.logical_qubits - base_schedule.scratch_slot_count
    transfer_schedule = schedule_fixed_order_belady(
        event_program, available_capacity
    )
    if (
        transfer_schedule.actions
        and config.timing_evidence_status is EvidenceStatus.CHECK
        and not allow_check_assumptions
    ):
        raise UnsupportedMemoryIoTimingError(
            "strict I/O-aware schedule rejected CHECK transfer durations"
        )

    actions_by_boundary: list[list[TransferAction]] = [
        [] for _ in range(len(base_schedule.events) + 1)
    ]
    for action in transfer_schedule.actions:
        actions_by_boundary[action.boundary_index].append(action)
    delay_offset = 0
    prior_compute_end = 0
    zero_latency = config.load_rounds == 0 and config.store_rounds == 0
    transfers: list[ScheduledMemoryTransfer] = []
    compute_events: list[IoAwareComputeEvent] = []
    for boundary_index, base_event in enumerate(base_schedule.events):
        nominal_start = base_event.start_round + delay_offset
        boundary_actions = tuple(actions_by_boundary[boundary_index])
        boundary_ready = (
            base_event.start_round
            if zero_latency
            else (
                max(nominal_start, prior_compute_end)
                if boundary_actions
                else nominal_start
            )
        )
        boundary_transfers, transfer_ready = _schedule_boundary_transfers(
            boundary_actions,
            boundary_ready=boundary_ready,
            config=config,
            first_transfer_index=len(transfers),
        )
        transfers.extend(boundary_transfers)
        start = (
            base_event.start_round
            if zero_latency
            else max(nominal_start, transfer_ready)
        )
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
        boundary_ready=(
            base_schedule.scheduled_rounds if zero_latency else prior_compute_end
        ),
        config=config,
        first_transfer_index=len(transfers),
    )
    transfers.extend(final_transfers)
    scheduled_rounds = max(prior_compute_end, final_ready)
    transfer_action_rounds = sum(
        transfer.end_round - transfer.start_round for transfer in transfers
    )
    schedule = IoAwareAdaptivePbcSchedule(
        trace_id=pbc_trace.trace_id,
        configuration_id=config.configuration_id,
        allow_check_assumptions=allow_check_assumptions,
        overlap_policy=config.overlap_policy,
        scratch_slot_count=base_schedule.scratch_slot_count,
        available_source_logical_capacity=available_capacity,
        base_scheduled_rounds=base_schedule.scheduled_rounds,
        scheduled_rounds=scheduled_rounds,
        added_rounds=scheduled_rounds - base_schedule.scheduled_rounds,
        loads=transfer_schedule.loads,
        stores=transfer_schedule.stores,
        transfer_action_rounds=transfer_action_rounds,
        timing_evidence_status=config.timing_evidence_status,
        base_strict_executable=base_schedule.strict_executable,
        transfer_schedule=transfer_schedule,
        transfers=tuple(transfers),
        compute_events=tuple(compute_events),
    )
    validate_io_aware_adaptive_pbc(base_schedule, config, schedule)
    return schedule


def validate_io_aware_adaptive_pbc(
    base_schedule: AdaptivePbcSchedule,
    config: MemoryIoTimingConfig,
    schedule: IoAwareAdaptivePbcSchedule,
) -> None:
    """Replay timing, lane capacity, and base-event preservation."""

    if len(schedule.compute_events) != len(base_schedule.events):
        raise MemoryIoError("I/O-aware compute-event count mismatch")
    for base, shifted in zip(base_schedule.events, schedule.compute_events, strict=True):
        if (
            shifted.event_id != base.event_id
            or shifted.operation_ids != base.operation_ids
            or shifted.source_primitive_ids != base.source_primitive_ids
            or shifted.base_start_round != base.start_round
            or shifted.base_end_round != base.end_round
            or shifted.end_round - shifted.start_round
            != base.end_round - base.start_round
            or shifted.start_round < base.start_round
            or shifted.transfer_ready_round > shifted.start_round
        ):
            raise MemoryIoError("I/O-aware compute event does not preserve the base event")
    for lane in range(config.transfer_lanes):
        events = sorted(
            (transfer for transfer in schedule.transfers if transfer.lane == lane),
            key=lambda transfer: (transfer.start_round, transfer.transfer_id),
        )
        for earlier, later in pairwise(events):
            if earlier.end_round > later.start_round:
                raise MemoryIoError("memory transfers overlap on one lane")
    for transfer in schedule.transfers:
        expected_duration = (
            config.load_rounds
            if transfer.kind is TransferKind.LOAD
            else config.store_rounds
        )
        if transfer.end_round - transfer.start_round != expected_duration:
            raise MemoryIoError("memory transfer duration mismatch")
        if transfer.boundary_index < len(schedule.compute_events):
            event = schedule.compute_events[transfer.boundary_index]
            if transfer.end_round > event.start_round:
                raise MemoryIoError("memory transfer finishes after its consumer starts")
        elif transfer.start_round < max(
            (event.end_round for event in schedule.compute_events), default=0
        ):
            raise MemoryIoError("final return overlaps unfinished compute")
    loads = sum(transfer.kind is TransferKind.LOAD for transfer in schedule.transfers)
    stores = sum(transfer.kind is TransferKind.STORE for transfer in schedule.transfers)
    if loads != schedule.loads or stores != schedule.stores:
        raise MemoryIoError("I/O-aware transfer counts mismatch")
    expected_rounds = max(
        (event.end_round for event in schedule.compute_events),
        default=0,
    )
    expected_rounds = max(
        expected_rounds,
        max((transfer.end_round for transfer in schedule.transfers), default=0),
    )
    if (
        schedule.scheduled_rounds != expected_rounds
        or schedule.added_rounds
        != schedule.scheduled_rounds - schedule.base_scheduled_rounds
    ):
        raise MemoryIoError("I/O-aware makespan mismatch")


def io_aware_schedule_to_data(schedule: IoAwareAdaptivePbcSchedule) -> dict[str, Any]:
    """Return deterministic JSON-compatible I/O-aware schedule data."""

    return {
        "added_rounds": schedule.added_rounds,
        "allow_check_assumptions": schedule.allow_check_assumptions,
        "available_source_logical_capacity": (
            schedule.available_source_logical_capacity
        ),
        "base_scheduled_rounds": schedule.base_scheduled_rounds,
        "base_strict_executable": schedule.base_strict_executable,
        "compute_events": [
            {
                "base_end_round": event.base_end_round,
                "base_start_round": event.base_start_round,
                "end_round": event.end_round,
                "event_id": event.event_id,
                "operation_ids": list(event.operation_ids),
                "source_primitive_ids": list(event.source_primitive_ids),
                "start_round": event.start_round,
                "transfer_ready_round": event.transfer_ready_round,
            }
            for event in schedule.compute_events
        ],
        "configuration_id": schedule.configuration_id,
        "loads": schedule.loads,
        "overlap_policy": schedule.overlap_policy,
        "scheduled_rounds": schedule.scheduled_rounds,
        "scratch_slot_count": schedule.scratch_slot_count,
        "stores": schedule.stores,
        "strict_executable": schedule.strict_executable,
        "timing_evidence_status": schedule.timing_evidence_status.value,
        "trace_id": schedule.trace_id,
        "transfer_action_rounds": schedule.transfer_action_rounds,
        "transfers": [
            {
                "boundary_index": transfer.boundary_index,
                "end_round": transfer.end_round,
                "kind": transfer.kind.value,
                "lane": transfer.lane,
                "reason": transfer.reason.value,
                "start_round": transfer.start_round,
                "timing_evidence_status": transfer.timing_evidence_status.value,
                "transfer_id": transfer.transfer_id,
                "value_id": transfer.value_id,
            }
            for transfer in schedule.transfers
        ],
    }


def dumps_io_aware_schedule(schedule: IoAwareAdaptivePbcSchedule) -> str:
    """Serialize an I/O-aware schedule canonically."""

    return json.dumps(io_aware_schedule_to_data(schedule), indent=2, sort_keys=True) + "\n"
