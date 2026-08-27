"""Deterministic adaptive-PBC scheduling for a finite Mitten processor."""

from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from ecdlp_ftqc.codes import (
    PbcMittenBackendConfig,
    PbcMittenImplementationKind,
    PbcMittenOperationCost,
)
from ecdlp_ftqc.compiler import (
    CompilerAncillaLifetime,
    PbcDependencyKind,
    PbcOperation,
    PbcOperationKind,
    PbcTrace,
)
from ecdlp_ftqc.metadata import EvidenceStatus


class UnsupportedAdaptivePbcScheduleError(ValueError):
    """Raised when strict scheduling would consume an unresolved claim."""


class AdaptivePbcProcessorCapacityError(ValueError):
    """Raised when source data plus requested compiler scratch exceed J300."""


@dataclass(frozen=True, slots=True)
class AdaptivePbcScheduledEvent:
    event_id: str
    operation_ids: tuple[str, ...]
    source_primitive_ids: tuple[str, ...]
    implementation: PbcMittenImplementationKind
    start_round: int
    end_round: int
    logical_support: tuple[str, ...]
    carrier_support: tuple[str, ...]
    scratch_slots: tuple[int, ...]
    exclusive_resource: str
    resource_slot: int
    dependency_ready_round: int
    classical_ready_round: int
    scratch_ready_round: int
    carrier_ready_round: int
    resource_ready_round: int
    gadget_data_ancilla_qubits: int
    gadget_check_ancilla_qubits: int
    resource_state_demand: int
    timing_evidence_status: EvidenceStatus
    space_evidence_status: EvidenceStatus
    selection_reason: str

    @property
    def added_physical_qubits(self) -> int:
        return self.gadget_data_ancilla_qubits + self.gadget_check_ancilla_qubits

    @property
    def primary_bottleneck(self) -> str:
        candidates = (
            ("classical_reaction", self.classical_ready_round),
            ("dependency", self.dependency_ready_round),
            ("scratch", self.scratch_ready_round),
            ("carrier", self.carrier_ready_round),
            ("exclusive_resource", self.resource_ready_round),
        )
        return max(candidates, key=lambda item: (item[1], -candidates.index(item)))[0]


@dataclass(frozen=True, slots=True)
class AdaptivePbcSchedule:
    trace_id: str
    configuration_id: str
    allow_check_assumptions: bool
    high_rate_enabled: bool
    factory_mode: str
    scratch_slot_count: int
    peak_source_processor_occupancy: int
    peak_total_logical_occupancy: int
    serialized_operation_rounds: int
    dependency_only_critical_path_rounds: int
    scheduled_rounds: int
    known_peak_physical_qubits_lower_bound: int
    physical_qubit_total_complete: bool
    total_resource_state_demand: int
    unresolved_implementations: tuple[PbcMittenImplementationKind, ...]
    classical_reaction_evidence_status: EvidenceStatus
    events: tuple[AdaptivePbcScheduledEvent, ...]

    @property
    def strict_executable(self) -> bool:
        return (
            not self.unresolved_implementations
            and self.classical_reaction_evidence_status is not EvidenceStatus.CHECK
        )

    @property
    def high_rate_batch_count(self) -> int:
        return sum(
            event.implementation is PbcMittenImplementationKind.HIGH_RATE_XX_10
            for event in self.events
        )

    @property
    def high_rate_operation_count(self) -> int:
        return sum(
            len(event.operation_ids)
            for event in self.events
            if event.implementation is PbcMittenImplementationKind.HIGH_RATE_XX_10
        )

    @property
    def implementation_counts(self) -> Counter[PbcMittenImplementationKind]:
        counts: Counter[PbcMittenImplementationKind] = Counter()
        for event in self.events:
            counts[event.implementation] += len(event.operation_ids)
        return counts

    @property
    def primary_bottleneck_counts(self) -> Counter[str]:
        return Counter(event.primary_bottleneck for event in self.events)


def _pauli_family(operation: PbcOperation) -> str:
    return "".join(term.split(":", maxsplit=1)[0] for term in operation.pauli_terms)


def _implementation(operation: PbcOperation) -> PbcMittenImplementationKind:
    if operation.kind is PbcOperationKind.PREPARE:
        if operation.resource_state_demand or any(
            choice.state == "magic_t" for choice in operation.prepared_states
        ):
            return PbcMittenImplementationKind.MAGIC_T_PREPARATION
        return PbcMittenImplementationKind.STABILIZER_PREPARATION
    if operation.kind is PbcOperationKind.MEASURE_PAULI:
        family = _pauli_family(operation)
        return {
            "X": PbcMittenImplementationKind.SEED_X,
            "Y": PbcMittenImplementationKind.SEED_Y,
            "Z": PbcMittenImplementationKind.SEED_Z,
            "XX": PbcMittenImplementationKind.SEED_XX,
            "ZZ": PbcMittenImplementationKind.SEED_ZZ,
        }.get(family, PbcMittenImplementationKind.FULL_EXTRACTOR)
    if operation.kind is PbcOperationKind.PAULI_FRAME_UPDATE:
        return PbcMittenImplementationKind.PAULI_FRAME_UPDATE
    if operation.kind is PbcOperationKind.CONDITIONAL_CLIFFORD_FRAME:
        return PbcMittenImplementationKind.CONDITIONAL_CZ
    if operation.kind in {PbcOperationKind.RELEASE, PbcOperationKind.REBIND_LOGICAL_VALUE}:
        return PbcMittenImplementationKind.BOOKKEEPING
    raise AssertionError(f"unhandled PBC operation kind {operation.kind.value}")


def _cost(operation: PbcOperation, config: PbcMittenBackendConfig) -> PbcMittenOperationCost:
    return config.cost(_implementation(operation))


def _dependency_maps(
    trace: PbcTrace,
) -> tuple[dict[str, set[str]], set[tuple[str, str]]]:
    predecessors: dict[str, set[str]] = {
        operation.operation_id: set() for operation in trace.operations
    }
    classical_edges: set[tuple[str, str]] = set()
    for dependency in trace.dependencies:
        predecessors[dependency.successor].add(dependency.predecessor)
        if dependency.kind is PbcDependencyKind.CLASSICAL_FEED_FORWARD:
            classical_edges.add((dependency.predecessor, dependency.successor))
    return predecessors, classical_edges


def _dependency_critical_path(trace: PbcTrace, config: PbcMittenBackendConfig) -> int:
    operations = {operation.operation_id: operation for operation in trace.operations}
    predecessors, classical_edges = _dependency_maps(trace)
    finish: dict[str, int] = {}
    for operation_id in trace.topological_order():
        starts = []
        for predecessor in predecessors[operation_id]:
            reaction = (
                config.classical_reaction_rounds
                if (predecessor, operation_id) in classical_edges
                else 0
            )
            starts.append(finish[predecessor] + reaction)
        start = max(starts, default=0)
        finish[operation_id] = start + _cost(operations[operation_id], config).rounds
    return max(finish.values(), default=0)


def _strictly_validate(trace: PbcTrace, config: PbcMittenBackendConfig) -> None:
    unresolved: set[str] = set()
    for operation in trace.operations:
        cost = _cost(operation, config)
        if (
            cost.timing_evidence_status is EvidenceStatus.CHECK
            or cost.space_evidence_status is EvidenceStatus.CHECK
        ):
            unresolved.add(cost.implementation.value)
    has_classical_edges = any(
        dependency.kind is PbcDependencyKind.CLASSICAL_FEED_FORWARD
        for dependency in trace.dependencies
    )
    if has_classical_edges and config.classical_reaction_evidence_status is EvidenceStatus.CHECK:
        unresolved.add("classical_reaction")
    if unresolved:
        raise UnsupportedAdaptivePbcScheduleError(
            "strict adaptive-PBC schedule rejected CHECK assumptions: "
            + ", ".join(sorted(unresolved))
        )


def _find_high_rate_batch(
    ready: list[PbcOperation],
    active_scratch_slots: dict[str, int],
    config: PbcMittenBackendConfig,
) -> tuple[PbcOperation, ...] | None:
    specs = sorted(
        (spec for spec in config.high_rate_batches if spec.pauli_family == "XX"),
        key=lambda spec: spec.batch_size,
        reverse=True,
    )
    candidates = [
        operation
        for operation in ready
        if operation.kind is PbcOperationKind.MEASURE_PAULI and _pauli_family(operation) == "XX"
    ]
    for spec in specs:
        selected: list[PbcOperation] = []
        occupied: set[str] = set()
        slots: set[int] = set()
        for operation in candidates:
            support = set(operation.logical_support)
            operation_slots = {
                active_scratch_slots[carrier]
                for carrier in operation.carrier_support
                if carrier in active_scratch_slots
            }
            if spec.disjoint_logical_support_required and support & occupied:
                continue
            if spec.distinct_scratch_slots_required and (
                len(operation_slots) != 1 or operation_slots & slots
            ):
                continue
            selected.append(operation)
            occupied.update(support)
            slots.update(operation_slots)
            if len(selected) == spec.batch_size:
                return tuple(selected)
    return None


def schedule_adaptive_pbc_greedy(
    trace: PbcTrace,
    config: PbcMittenBackendConfig,
    *,
    scratch_slot_count: int | None = None,
    enable_high_rate: bool = True,
    allow_check_assumptions: bool = False,
) -> AdaptivePbcSchedule:
    """List-schedule adaptive PPMs with explicit scratch and reaction constraints.

    The high-rate rule is deliberately narrow: it only selects an exact batch
    of ten ready, pairwise-disjoint XX products with ten distinct live compiler
    scratch slots.  This is a deterministic greedy upper bound, not an optimal
    schedule.
    """

    requested_scratch = (
        config.default_scratch_slots if scratch_slot_count is None else scratch_slot_count
    )
    if requested_scratch < trace.minimum_reusable_compiler_scratch_slots:
        raise AdaptivePbcProcessorCapacityError(
            f"requested {requested_scratch} scratch slots, but the trace requires at "
            f"least {trace.minimum_reusable_compiler_scratch_slots}"
        )
    total_occupancy = trace.peak_source_processor_occupancy + requested_scratch
    if total_occupancy > config.logical_qubits:
        raise AdaptivePbcProcessorCapacityError(
            f"source occupancy {trace.peak_source_processor_occupancy} plus "
            f"{requested_scratch} scratch slots exceeds Mitten capacity "
            f"{config.logical_qubits}"
        )
    if not allow_check_assumptions:
        _strictly_validate(trace, config)

    operations = {operation.operation_id: operation for operation in trace.operations}
    order = trace.topological_order()
    position = {operation_id: index for index, operation_id in enumerate(order)}
    predecessors, classical_edges = _dependency_maps(trace)
    allocation_lifetimes = {
        lifetime.allocation_operation_id: lifetime for lifetime in trace.compiler_ancillas
    }
    release_lifetimes: dict[str, list[CompilerAncillaLifetime]] = defaultdict(list)
    for lifetime in trace.compiler_ancillas:
        release_lifetimes[lifetime.release_operation_id].append(lifetime)

    successors: dict[str, set[str]] = {operation_id: set() for operation_id in order}
    for successor, operation_predecessors in predecessors.items():
        for predecessor in operation_predecessors:
            successors[predecessor].add(successor)
    pending = set(order)
    initial_ready_ids = tuple(
        operation_id for operation_id in order if not predecessors[operation_id]
    )
    ready_ids: set[str] = set()
    finish: dict[str, int] = {}
    carrier_available: dict[str, int] = defaultdict(int)
    resource_available = {pool.name: [0] * pool.capacity for pool in config.resource_pools}
    scratch_available = [0] * requested_scratch
    scratch_owners: list[str | None] = [None] * requested_scratch
    active_scratch_slots: dict[str, int] = {}
    events: list[AdaptivePbcScheduledEvent] = []
    ready_regular_non_xx: list[tuple[int, str]] = []
    ready_allocation_non_xx: list[tuple[int, str]] = []
    ready_xx: list[tuple[int, str]] = []
    ready_batch_xx: set[str] = set()

    def is_xx(operation: PbcOperation) -> bool:
        return operation.kind is PbcOperationKind.MEASURE_PAULI and _pauli_family(operation) == "XX"

    def add_ready(operation_id: str) -> None:
        if operation_id in ready_ids:
            return
        ready_ids.add(operation_id)
        operation = operations[operation_id]
        item = (position[operation_id], operation_id)
        if is_xx(operation):
            heapq.heappush(ready_xx, item)
            operation_slots = {
                active_scratch_slots[carrier]
                for carrier in operation.carrier_support
                if carrier in active_scratch_slots
            }
            if len(operation_slots) == 1:
                ready_batch_xx.add(operation_id)
        elif operation_id in allocation_lifetimes:
            heapq.heappush(ready_allocation_non_xx, item)
        else:
            heapq.heappush(ready_regular_non_xx, item)

    def heap_candidate(heap: list[tuple[int, str]]) -> PbcOperation | None:
        while heap and heap[0][1] not in ready_ids:
            heapq.heappop(heap)
        return operations[heap[0][1]] if heap else None

    for operation_id in initial_ready_ids:
        add_ready(operation_id)

    def readiness(operation: PbcOperation) -> tuple[int, int, int, int]:
        dependency_round = max(
            (
                finish[predecessor]
                for predecessor in predecessors[operation.operation_id]
                if (predecessor, operation.operation_id) not in classical_edges
            ),
            default=0,
        )
        classical_round = max(
            (
                finish[predecessor] + config.classical_reaction_rounds
                for predecessor in predecessors[operation.operation_id]
                if (predecessor, operation.operation_id) in classical_edges
            ),
            default=0,
        )
        effective_carriers = tuple(
            (
                f"scratch:{active_scratch_slots[carrier]}"
                if carrier in active_scratch_slots
                else carrier
            )
            for carrier in operation.carrier_support
        )
        carrier_round = max(
            (carrier_available[carrier] for carrier in effective_carriers),
            default=0,
        )
        if operation.operation_id in allocation_lifetimes:
            free_slots = [index for index, owner in enumerate(scratch_owners) if owner is None]
            if not free_slots:
                return dependency_round, classical_round, 10**30, carrier_round
            scratch_round = min(scratch_available[index] for index in free_slots)
        else:
            scratch_round = max(
                (
                    scratch_available[active_scratch_slots[carrier]]
                    for carrier in operation.carrier_support
                    if carrier in active_scratch_slots
                ),
                default=0,
            )
        return dependency_round, classical_round, scratch_round, carrier_round

    completed: set[str] = set()
    while pending:
        batch = (
            _find_high_rate_batch(
                [
                    operations[operation_id]
                    for operation_id in sorted(ready_batch_xx, key=position.__getitem__)
                    if operation_id in ready_ids
                ],
                active_scratch_slots,
                config,
            )
            if enable_high_rate
            else None
        )
        if batch is not None:
            selected = batch
            cost = config.cost(PbcMittenImplementationKind.HIGH_RATE_XX_10)
            selection_reason = (
                "Exact greedy batch of ten ready, pairwise-disjoint XX products "
                "on ten distinct live scratch slots"
            )
        else:
            non_xx_candidates = [heap_candidate(ready_regular_non_xx)]
            if any(owner is None for owner in scratch_owners):
                non_xx_candidates.append(heap_candidate(ready_allocation_non_xx))
            feasible_non_xx = [
                operation for operation in non_xx_candidates if operation is not None
            ]
            fallback: PbcOperation | None
            if feasible_non_xx:
                fallback = min(
                    feasible_non_xx,
                    key=lambda operation: position[operation.operation_id],
                )
            else:
                fallback = heap_candidate(ready_xx)
            if fallback is None:
                raise ValueError("adaptive-PBC scheduler reached a scratch or dependency deadlock")
            selected = (fallback,)
            cost = _cost(selected[0], config)
            selection_reason = (
                "Greedy single-operation fallback; no supported exact high-rate batch was ready"
            )

        selected_readiness = [readiness(operation) for operation in selected]
        dependency_round = max(item[0] for item in selected_readiness)
        classical_round = max(item[1] for item in selected_readiness)
        scratch_round = max(item[2] for item in selected_readiness)
        carrier_round = max(item[3] for item in selected_readiness)
        resource_slots = resource_available[cost.exclusive_resource]
        resource_slot = min(
            range(len(resource_slots)), key=lambda index: (resource_slots[index], index)
        )
        resource_round = resource_slots[resource_slot]
        start_round = max(
            dependency_round,
            classical_round,
            scratch_round,
            carrier_round,
            resource_round,
        )
        end_round = start_round + cost.rounds

        for operation in selected:
            allocation_lifetime = allocation_lifetimes.get(operation.operation_id)
            if allocation_lifetime is not None:
                slot = min(
                    (index for index, owner in enumerate(scratch_owners) if owner is None),
                    key=lambda index: (max(scratch_available[index], start_round), index),
                )
                scratch_owners[slot] = allocation_lifetime.carrier_id
                active_scratch_slots[allocation_lifetime.carrier_id] = slot
                scratch_available[slot] = end_round

        event_scratch_slots = tuple(
            sorted(
                {
                    active_scratch_slots[carrier]
                    for operation in selected
                    for carrier in operation.carrier_support
                    if carrier in active_scratch_slots
                }
            )
        )
        effective_carriers = tuple(
            sorted(
                {
                    (
                        f"scratch:{active_scratch_slots[carrier]}"
                        if carrier in active_scratch_slots
                        else carrier
                    )
                    for operation in selected
                    for carrier in operation.carrier_support
                }
            )
        )
        logical_support = tuple(
            sorted({value for operation in selected for value in operation.logical_support})
        )
        event = AdaptivePbcScheduledEvent(
            event_id=f"event:{len(events):06d}",
            operation_ids=tuple(operation.operation_id for operation in selected),
            source_primitive_ids=tuple(
                dict.fromkeys(operation.source_primitive_id for operation in selected)
            ),
            implementation=cost.implementation,
            start_round=start_round,
            end_round=end_round,
            logical_support=logical_support,
            carrier_support=effective_carriers,
            scratch_slots=event_scratch_slots,
            exclusive_resource=cost.exclusive_resource,
            resource_slot=resource_slot,
            dependency_ready_round=dependency_round,
            classical_ready_round=classical_round,
            scratch_ready_round=scratch_round,
            carrier_ready_round=carrier_round,
            resource_ready_round=resource_round,
            gadget_data_ancilla_qubits=cost.gadget_data_ancilla_qubits,
            gadget_check_ancilla_qubits=cost.gadget_check_ancilla_qubits,
            resource_state_demand=sum(operation.resource_state_demand for operation in selected),
            timing_evidence_status=cost.timing_evidence_status,
            space_evidence_status=cost.space_evidence_status,
            selection_reason=selection_reason,
        )
        events.append(event)
        resource_slots[resource_slot] = end_round
        for carrier in effective_carriers:
            carrier_available[carrier] = end_round
        for operation in selected:
            for carrier in operation.carrier_support:
                carrier_available[carrier] = end_round
            finish[operation.operation_id] = end_round
            completed.add(operation.operation_id)
            pending.remove(operation.operation_id)
            ready_ids.remove(operation.operation_id)
            ready_batch_xx.discard(operation.operation_id)
            for successor in successors[operation.operation_id]:
                if successor in pending and predecessors[successor].issubset(completed):
                    add_ready(successor)
            for lifetime in release_lifetimes.get(operation.operation_id, []):
                slot = active_scratch_slots.pop(lifetime.carrier_id)
                scratch_owners[slot] = None
                scratch_available[slot] = end_round

    unresolved = tuple(
        sorted(
            {
                _cost(operation, config).implementation
                for operation in trace.operations
                if _cost(operation, config).timing_evidence_status is EvidenceStatus.CHECK
                or _cost(operation, config).space_evidence_status is EvidenceStatus.CHECK
            },
            key=lambda implementation: implementation.value,
        )
    )
    ordered_events = tuple(sorted(events, key=lambda event: (event.start_round, event.event_id)))
    peak_added = max((event.added_physical_qubits for event in ordered_events), default=0)
    return AdaptivePbcSchedule(
        trace_id=trace.trace_id,
        configuration_id=config.configuration_id,
        allow_check_assumptions=allow_check_assumptions,
        high_rate_enabled=enable_high_rate,
        factory_mode="ideal_supply_no_stalls",
        scratch_slot_count=requested_scratch,
        peak_source_processor_occupancy=trace.peak_source_processor_occupancy,
        peak_total_logical_occupancy=total_occupancy,
        serialized_operation_rounds=sum(
            _cost(operation, config).rounds for operation in trace.operations
        ),
        dependency_only_critical_path_rounds=_dependency_critical_path(trace, config),
        scheduled_rounds=max((event.end_round for event in ordered_events), default=0),
        known_peak_physical_qubits_lower_bound=(config.known_base_physical_qubits + peak_added),
        physical_qubit_total_complete=False,
        total_resource_state_demand=trace.resource_state_demand,
        unresolved_implementations=unresolved,
        classical_reaction_evidence_status=(
            config.classical_reaction_evidence_status if classical_edges else EvidenceStatus.PROVED
        ),
        events=ordered_events,
    )


def adaptive_pbc_schedule_to_data(schedule: AdaptivePbcSchedule) -> dict[str, Any]:
    """Convert a schedule to deterministic JSON-compatible data."""

    return {
        "allow_check_assumptions": schedule.allow_check_assumptions,
        "classical_reaction_evidence_status": (schedule.classical_reaction_evidence_status.value),
        "configuration_id": schedule.configuration_id,
        "dependency_only_critical_path_rounds": (schedule.dependency_only_critical_path_rounds),
        "events": [
            {
                "added_physical_qubits": event.added_physical_qubits,
                "carrier_ready_round": event.carrier_ready_round,
                "carrier_support": list(event.carrier_support),
                "classical_ready_round": event.classical_ready_round,
                "dependency_ready_round": event.dependency_ready_round,
                "end_round": event.end_round,
                "event_id": event.event_id,
                "exclusive_resource": event.exclusive_resource,
                "gadget_check_ancilla_qubits": event.gadget_check_ancilla_qubits,
                "gadget_data_ancilla_qubits": event.gadget_data_ancilla_qubits,
                "implementation": event.implementation.value,
                "logical_support": list(event.logical_support),
                "operation_ids": list(event.operation_ids),
                "primary_bottleneck": event.primary_bottleneck,
                "resource_ready_round": event.resource_ready_round,
                "resource_slot": event.resource_slot,
                "resource_state_demand": event.resource_state_demand,
                "scratch_ready_round": event.scratch_ready_round,
                "scratch_slots": list(event.scratch_slots),
                "selection_reason": event.selection_reason,
                "source_primitive_ids": list(event.source_primitive_ids),
                "space_evidence_status": event.space_evidence_status.value,
                "start_round": event.start_round,
                "timing_evidence_status": event.timing_evidence_status.value,
            }
            for event in schedule.events
        ],
        "factory_mode": schedule.factory_mode,
        "high_rate_batch_count": schedule.high_rate_batch_count,
        "high_rate_enabled": schedule.high_rate_enabled,
        "high_rate_operation_count": schedule.high_rate_operation_count,
        "implementation_counts": {
            implementation.value: count
            for implementation, count in sorted(
                schedule.implementation_counts.items(), key=lambda item: item[0].value
            )
        },
        "known_peak_physical_qubits_lower_bound": (schedule.known_peak_physical_qubits_lower_bound),
        "peak_source_processor_occupancy": schedule.peak_source_processor_occupancy,
        "peak_total_logical_occupancy": schedule.peak_total_logical_occupancy,
        "physical_qubit_total_complete": schedule.physical_qubit_total_complete,
        "primary_bottleneck_counts": dict(sorted(schedule.primary_bottleneck_counts.items())),
        "scheduled_rounds": schedule.scheduled_rounds,
        "scratch_slot_count": schedule.scratch_slot_count,
        "serialized_operation_rounds": schedule.serialized_operation_rounds,
        "strict_executable": schedule.strict_executable,
        "total_resource_state_demand": schedule.total_resource_state_demand,
        "trace_id": schedule.trace_id,
        "unresolved_implementations": [
            implementation.value for implementation in schedule.unresolved_implementations
        ],
    }
