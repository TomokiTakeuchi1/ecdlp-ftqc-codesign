"""Deterministic greedy scheduling for an evidence-qualified Mitten backend."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from ecdlp_ftqc.codes import (
    HighRateBatchSpec,
    MittenBackendConfig,
    MittenImplementationKind,
    MittenOperationCost,
)
from ecdlp_ftqc.compiler import LogicalPrimitive, LogicalPrimitiveKind, LogicalTrace
from ecdlp_ftqc.metadata import EvidenceStatus


class ProcessorCapacityError(ValueError):
    """The source circuit's recorded resident values exceed code capacity."""


class UnsupportedMittenLoweringError(ValueError):
    """Strict scheduling encountered a primitive whose native lowering is CHECK."""


@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    """One scheduled gadget, possibly batching several phase-exact primitives."""

    event_id: str
    primitive_ids: tuple[str, ...]
    source_node_ids: tuple[str, ...]
    implementation: MittenImplementationKind
    start_round: int
    end_round: int
    logical_support: tuple[str, ...]
    exclusive_resource: str
    resource_slot: int
    gadget_data_ancilla_qubits: int
    gadget_check_ancilla_qubits: int
    resource_state_demand: int
    evidence_status: EvidenceStatus
    selection_reason: str

    def __post_init__(self) -> None:
        if not self.event_id or not self.primitive_ids or not self.source_node_ids:
            raise ValueError("schedule-event IDs cannot be empty")
        if len(self.primitive_ids) != len(set(self.primitive_ids)):
            raise ValueError("an event cannot contain a primitive twice")
        if self.start_round < 0 or self.end_round < self.start_round:
            raise ValueError("schedule-event round interval is invalid")
        if self.resource_slot < 0:
            raise ValueError("resource slot cannot be negative")

    @property
    def rounds(self) -> int:
        return self.end_round - self.start_round

    @property
    def added_physical_qubits(self) -> int:
        return self.gadget_data_ancilla_qubits + self.gadget_check_ancilla_qubits


@dataclass(frozen=True, slots=True)
class MittenSchedule:
    """Runtime views kept separate from their evidence and completeness status."""

    trace_id: str
    configuration_id: str
    allow_check_assumptions: bool
    factory_mode: str
    peak_source_processor_occupancy: int
    sequential_rounds: int
    dependency_only_critical_path_rounds: int
    scheduled_rounds: int
    known_peak_physical_qubits_lower_bound: int
    physical_qubit_total_complete: bool
    total_resource_state_demand: int
    unresolved_primitive_kinds: tuple[LogicalPrimitiveKind, ...]
    events: tuple[ScheduledEvent, ...]

    @property
    def strict_executable(self) -> bool:
        return not self.unresolved_primitive_kinds

    @property
    def implementation_counts(self) -> Counter[MittenImplementationKind]:
        counts: Counter[MittenImplementationKind] = Counter()
        for event in self.events:
            counts[event.implementation] += len(event.primitive_ids)
        return counts

    @property
    def high_rate_primitive_count(self) -> int:
        return self.implementation_counts[MittenImplementationKind.HIGH_RATE_XX_10]


_SINGLE_IMPLEMENTATION = {
    LogicalPrimitiveKind.PREPARE_T: MittenImplementationKind.CHECK_PREPARE_T,
    LogicalPrimitiveKind.CNOT: MittenImplementationKind.CHECK_CNOT_CQLU,
    LogicalPrimitiveKind.T: MittenImplementationKind.CHECK_T_GATE,
    LogicalPrimitiveKind.T_DAGGER: MittenImplementationKind.CHECK_T_GATE,
    LogicalPrimitiveKind.H: MittenImplementationKind.CHECK_H_CQLU,
    LogicalPrimitiveKind.S: MittenImplementationKind.CHECK_S_CQLU,
    LogicalPrimitiveKind.MEASURE_X: MittenImplementationKind.SEED_X_SURGERY,
    LogicalPrimitiveKind.MEASURE_Y: MittenImplementationKind.SEED_Y_SURGERY,
    LogicalPrimitiveKind.MEASURE_Z: MittenImplementationKind.SEED_Z_SURGERY,
    LogicalPrimitiveKind.MEASURE_XX: MittenImplementationKind.SEED_XX_SURGERY,
    LogicalPrimitiveKind.MEASURE_ZZ: MittenImplementationKind.SEED_ZZ_SURGERY,
    LogicalPrimitiveKind.MEASURE_GENERAL_PAULI: MittenImplementationKind.FULL_EXTRACTOR,
    LogicalPrimitiveKind.CONDITIONAL_CZ_FRAME: (
        MittenImplementationKind.CHECK_CONDITIONAL_CZ_FRAME
    ),
    LogicalPrimitiveKind.RELEASE: MittenImplementationKind.CHECK_RELEASE,
}


def _single_cost(
    primitive: LogicalPrimitive, config: MittenBackendConfig
) -> MittenOperationCost:
    return config.cost(_SINGLE_IMPLEMENTATION[primitive.kind])


def _predecessors(trace: LogicalTrace) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for dependency in trace.dependencies:
        result[dependency.successor].add(dependency.predecessor)
    return result


def _weighted_critical_path(trace: LogicalTrace, config: MittenBackendConfig) -> int:
    primitive_by_id = {
        primitive.primitive_id: primitive for primitive in trace.primitives
    }
    predecessors = _predecessors(trace)
    finish: dict[str, int] = {}
    for primitive_id in trace.topological_order():
        primitive = primitive_by_id[primitive_id]
        start = max(
            (finish[predecessor] for predecessor in predecessors[primitive_id]),
            default=0,
        )
        finish[primitive_id] = start + _single_cost(primitive, config).rounds
    return max(finish.values(), default=0)


def _high_rate_batch(
    primitives: list[LogicalPrimitive],
    config: MittenBackendConfig,
) -> tuple[tuple[LogicalPrimitive, ...], HighRateBatchSpec] | None:
    xx_batches = sorted(
        (
            batch
            for batch in config.high_rate_batches
            if batch.pauli_family == "XX"
        ),
        key=lambda batch: batch.batch_size,
        reverse=True,
    )
    candidates = [
        primitive
        for primitive in primitives
        if primitive.kind is LogicalPrimitiveKind.MEASURE_XX
        and len(primitive.logical_support) == 2
    ]
    for batch in xx_batches:
        selected: list[LogicalPrimitive] = []
        occupied: set[str] = set()
        for primitive in candidates:
            support = set(primitive.logical_support)
            if batch.disjoint_support_required and support & occupied:
                continue
            selected.append(primitive)
            occupied.update(support)
            if len(selected) == batch.batch_size:
                return tuple(selected), batch
    return None


def _selection_reason(
    primitives: tuple[LogicalPrimitive, ...],
    implementation: MittenImplementationKind,
) -> str:
    if implementation is MittenImplementationKind.HIGH_RATE_XX_10:
        return "Greedy exact-size batch of ten ready, pairwise-disjoint XX measurements"
    if implementation in {
        MittenImplementationKind.SEED_X_SURGERY,
        MittenImplementationKind.SEED_Y_SURGERY,
        MittenImplementationKind.SEED_Z_SURGERY,
        MittenImplementationKind.SEED_XX_SURGERY,
        MittenImplementationKind.SEED_ZZ_SURGERY,
    }:
        return "No source-supported high-rate batch matched; use the reusable seed gadget"
    if implementation is MittenImplementationKind.FULL_EXTRACTOR:
        return "Pauli family is outside the basic seed set; use the fixed full extractor"
    if implementation.value.startswith("check_"):
        kinds = ",".join(sorted({primitive.kind.value for primitive in primitives}))
        return f"CHECK placeholder: source-audited PBC/native lowering is missing for {kinds}"
    raise AssertionError(f"unhandled implementation {implementation.value}")


def _strictly_validate_costs(trace: LogicalTrace, config: MittenBackendConfig) -> None:
    unresolved = sorted(
        {
            primitive.kind.value
            for primitive in trace.primitives
            if _single_cost(primitive, config).evidence_status is EvidenceStatus.CHECK
        }
    )
    if unresolved:
        raise UnsupportedMittenLoweringError(
            "strict Mitten schedule rejected CHECK native lowerings: "
            + ", ".join(unresolved)
        )


def schedule_mitten_greedy(
    trace: LogicalTrace,
    config: MittenBackendConfig,
    *,
    allow_check_assumptions: bool = False,
) -> MittenSchedule:
    """List-schedule a phase-exact trace using high-rate, seed, then extractor.

    High-rate selection is intentionally narrow: configuration v1 only batches
    the exact ten disjoint XX products directly simulated in the primary source.
    A single-X measurement is not silently promoted to an unverified parallel
    gadget.  Factory supply never stalls this scheduler, but each T-state demand
    remains counted.
    """

    if trace.peak_source_processor_occupancy > config.logical_qubits:
        raise ProcessorCapacityError(
            f"source occupancy {trace.peak_source_processor_occupancy} exceeds "
            f"Mitten capacity {config.logical_qubits}"
        )
    if not allow_check_assumptions:
        _strictly_validate_costs(trace, config)

    primitive_by_id = {
        primitive.primitive_id: primitive for primitive in trace.primitives
    }
    order = trace.topological_order()
    position = {primitive_id: index for index, primitive_id in enumerate(order)}
    predecessors = _predecessors(trace)
    pending = set(order)
    finish: dict[str, int] = {}
    value_available: dict[str, int] = defaultdict(int)
    resource_available = {
        pool.name: [0] * pool.capacity for pool in config.resource_pools
    }
    events: list[ScheduledEvent] = []

    while pending:
        ready = [
            primitive_by_id[primitive_id]
            for primitive_id in order
            if primitive_id in pending
            and predecessors[primitive_id].issubset(finish)
        ]
        if not ready:
            raise ValueError("scheduler reached a dependency deadlock")

        def dependency_ready_round(primitive: LogicalPrimitive) -> int:
            return max(
                (finish[pred] for pred in predecessors[primitive.primitive_id]),
                default=0,
            )

        earliest_dependency_round = min(map(dependency_ready_round, ready))
        earliest_ready = [
            primitive
            for primitive in ready
            if dependency_ready_round(primitive) == earliest_dependency_round
        ]
        earliest_ready.sort(key=lambda primitive: position[primitive.primitive_id])
        batch_selection = _high_rate_batch(earliest_ready, config)
        selected: tuple[LogicalPrimitive, ...]
        if batch_selection is None:
            selected = (earliest_ready[0],)
            cost = _single_cost(selected[0], config)
        else:
            selected, batch = batch_selection
            cost = config.cost(batch.implementation)

        if not allow_check_assumptions and cost.evidence_status is EvidenceStatus.CHECK:
            raise UnsupportedMittenLoweringError(
                f"strict Mitten schedule rejected {cost.implementation.value}"
            )

        support = tuple(
            sorted({value for primitive in selected for value in primitive.logical_support})
        )
        dependency_round = max(map(dependency_ready_round, selected))
        support_round = max((value_available[value] for value in support), default=0)
        slots = resource_available[cost.exclusive_resource]
        resource_slot = min(range(len(slots)), key=lambda index: (slots[index], index))
        start_round = max(dependency_round, support_round, slots[resource_slot])
        end_round = start_round + cost.rounds
        event_index = len(events)
        event = ScheduledEvent(
            event_id=f"event:{event_index:05d}",
            primitive_ids=tuple(primitive.primitive_id for primitive in selected),
            source_node_ids=tuple(
                dict.fromkeys(primitive.source_node_id for primitive in selected)
            ),
            implementation=cost.implementation,
            start_round=start_round,
            end_round=end_round,
            logical_support=support,
            exclusive_resource=cost.exclusive_resource,
            resource_slot=resource_slot,
            gadget_data_ancilla_qubits=cost.gadget_data_ancilla_qubits,
            gadget_check_ancilla_qubits=cost.gadget_check_ancilla_qubits,
            resource_state_demand=sum(
                primitive.resource_state_demand for primitive in selected
            ),
            evidence_status=cost.evidence_status,
            selection_reason=_selection_reason(selected, cost.implementation),
        )
        events.append(event)
        slots[resource_slot] = end_round
        for value in support:
            value_available[value] = end_round
        for primitive in selected:
            finish[primitive.primitive_id] = end_round
            pending.remove(primitive.primitive_id)

    ordered_events = tuple(
        sorted(events, key=lambda event: (event.start_round, event.event_id))
    )
    unresolved_kinds = tuple(
        sorted(
            {
                primitive.kind
                for primitive in trace.primitives
                if _single_cost(primitive, config).evidence_status
                is EvidenceStatus.CHECK
            },
            key=lambda kind: kind.value,
        )
    )
    peak_added_qubits = max(
        (event.added_physical_qubits for event in ordered_events), default=0
    )
    return MittenSchedule(
        trace_id=trace.trace_id,
        configuration_id=config.configuration_id,
        allow_check_assumptions=allow_check_assumptions,
        factory_mode="ideal_supply_no_stalls",
        peak_source_processor_occupancy=trace.peak_source_processor_occupancy,
        sequential_rounds=sum(
            _single_cost(primitive, config).rounds for primitive in trace.primitives
        ),
        dependency_only_critical_path_rounds=_weighted_critical_path(trace, config),
        scheduled_rounds=max((event.end_round for event in ordered_events), default=0),
        known_peak_physical_qubits_lower_bound=(
            config.known_base_physical_qubits + peak_added_qubits
        ),
        physical_qubit_total_complete=False,
        total_resource_state_demand=sum(
            primitive.resource_state_demand for primitive in trace.primitives
        ),
        unresolved_primitive_kinds=unresolved_kinds,
        events=ordered_events,
    )


def schedule_to_data(schedule: MittenSchedule) -> dict[str, Any]:
    """Convert a schedule to deterministic JSON-compatible data."""

    return {
        "allow_check_assumptions": schedule.allow_check_assumptions,
        "configuration_id": schedule.configuration_id,
        "dependency_only_critical_path_rounds": (
            schedule.dependency_only_critical_path_rounds
        ),
        "events": [
            {
                "added_physical_qubits": event.added_physical_qubits,
                "end_round": event.end_round,
                "event_id": event.event_id,
                "evidence_status": event.evidence_status.value,
                "exclusive_resource": event.exclusive_resource,
                "gadget_check_ancilla_qubits": event.gadget_check_ancilla_qubits,
                "gadget_data_ancilla_qubits": event.gadget_data_ancilla_qubits,
                "implementation": event.implementation.value,
                "logical_support": list(event.logical_support),
                "primitive_ids": list(event.primitive_ids),
                "resource_slot": event.resource_slot,
                "resource_state_demand": event.resource_state_demand,
                "selection_reason": event.selection_reason,
                "source_node_ids": list(event.source_node_ids),
                "start_round": event.start_round,
            }
            for event in schedule.events
        ],
        "factory_mode": schedule.factory_mode,
        "high_rate_primitive_count": schedule.high_rate_primitive_count,
        "implementation_counts": {
            implementation.value: count
            for implementation, count in sorted(
                schedule.implementation_counts.items(), key=lambda item: item[0].value
            )
        },
        "known_peak_physical_qubits_lower_bound": (
            schedule.known_peak_physical_qubits_lower_bound
        ),
        "peak_source_processor_occupancy": schedule.peak_source_processor_occupancy,
        "physical_qubit_total_complete": schedule.physical_qubit_total_complete,
        "scheduled_rounds": schedule.scheduled_rounds,
        "sequential_rounds": schedule.sequential_rounds,
        "strict_executable": schedule.strict_executable,
        "total_resource_state_demand": schedule.total_resource_state_demand,
        "trace_id": schedule.trace_id,
        "unresolved_primitive_kinds": [
            kind.value for kind in schedule.unresolved_primitive_kinds
        ],
    }
