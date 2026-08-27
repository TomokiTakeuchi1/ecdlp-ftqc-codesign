"""Origin-aware fixed-order placement for QCLA adaptive-PBC events.

The generic Gidney I/O model keeps processor-generated temporaries resident
for their full lifetime.  QCLA source ancillas have a different contract:
they are clean at the start of each reuse epoch, may be spilled while live,
and are clean again when that epoch ends.  This module keeps that distinction
explicit instead of weakening the reviewed Gidney contract.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from ecdlp_ftqc.io.model import (
    MEMORY_TRANSFER_SEMANTICS,
    MemoryIoError,
    TransferAction,
    TransferKind,
    TransferReason,
)

if TYPE_CHECKING:
    from ecdlp_ftqc.circuits.qcla import QclaAncillaInterval, QclaTrace
    from ecdlp_ftqc.compiler.qcla_pbc import QclaLogicalLowering
    from ecdlp_ftqc.scheduler.adaptive_pbc import AdaptivePbcSchedule

QCLA_MEMORY_IO_SCHEMA = "ecdlp-ftqc/qcla-memory-io-overlay"
QCLA_MEMORY_IO_SCHEMA_VERSION = 1
QCLA_FIXED_ORDER_POLICY = "qcla_epoch_aware_fixed_order_belady_v1"


class QclaMemoryValueOrigin(str, Enum):
    """Origins with different creation and final-return rules."""

    MEMORY_INPUT_OR_INOUT = "memory_input_or_inout"
    CLEAN_ANCILLA_EPOCH = "clean_ancilla_epoch"


@dataclass(frozen=True, slots=True)
class QclaMemoryValue:
    """One input/output value or one clean source-ancilla reuse epoch."""

    value_id: str
    source_value_id: str
    origin: QclaMemoryValueOrigin
    first_unit_index: int
    last_unit_index: int

    def __post_init__(self) -> None:
        if not self.value_id or not self.source_value_id:
            raise MemoryIoError("QCLA memory value identifiers cannot be empty")
        if not 0 <= self.first_unit_index <= self.last_unit_index:
            raise MemoryIoError("QCLA memory value has an invalid use interval")


@dataclass(frozen=True, slots=True)
class QclaMemoryUnit:
    """Logical source-value support of one fixed adaptive-PBC event."""

    unit_id: str
    source_event_id: str
    unit_index: int
    value_support: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.unit_id or not self.source_event_id or not self.value_support:
            raise MemoryIoError("QCLA memory unit identifiers and support cannot be empty")
        if self.unit_index < 0:
            raise MemoryIoError("QCLA memory unit index cannot be negative")
        if len(self.value_support) != len(set(self.value_support)):
            raise MemoryIoError("QCLA memory unit support cannot contain duplicates")


@dataclass(frozen=True, slots=True)
class QclaMemoryProgram:
    """Replayable value-origin overlay for a supplied PBC event order."""

    trace_id: str
    width: int
    units: tuple[QclaMemoryUnit, ...]
    values: tuple[QclaMemoryValue, ...]
    schema: str = QCLA_MEMORY_IO_SCHEMA
    schema_version: int = QCLA_MEMORY_IO_SCHEMA_VERSION
    transfer_semantics: str = MEMORY_TRANSFER_SEMANTICS

    def __post_init__(self) -> None:
        if not self.trace_id or self.width < 2 or not self.units or not self.values:
            raise MemoryIoError("QCLA memory program requires provenance, width, and data")
        if (
            self.schema != QCLA_MEMORY_IO_SCHEMA
            or self.schema_version != QCLA_MEMORY_IO_SCHEMA_VERSION
        ):
            raise MemoryIoError("unsupported QCLA memory-I/O schema")
        if self.transfer_semantics != MEMORY_TRANSFER_SEMANTICS:
            raise MemoryIoError("unsupported QCLA transfer semantics")
        if tuple(unit.unit_index for unit in self.units) != tuple(range(len(self.units))):
            raise MemoryIoError("QCLA memory units must have contiguous fixed-order indices")
        value_ids = tuple(value.value_id for value in self.values)
        if len(value_ids) != len(set(value_ids)):
            raise MemoryIoError("QCLA memory value IDs must be unique")
        known = set(value_ids)
        observed: dict[str, list[int]] = defaultdict(list)
        for unit in self.units:
            if not set(unit.value_support).issubset(known):
                raise MemoryIoError("QCLA memory unit references an unknown value")
            for value_id in unit.value_support:
                observed[value_id].append(unit.unit_index)
        for value in self.values:
            uses = observed.get(value.value_id, [])
            if not uses:
                raise MemoryIoError("QCLA memory value is never used")
            if uses[0] != value.first_unit_index or uses[-1] != value.last_unit_index:
                raise MemoryIoError("QCLA memory value interval disagrees with event uses")

    @property
    def values_by_id(self) -> dict[str, QclaMemoryValue]:
        return {value.value_id: value for value in self.values}

    @property
    def input_output_value_ids(self) -> set[str]:
        return {
            value.value_id
            for value in self.values
            if value.origin is QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT
        }


@dataclass(frozen=True, slots=True)
class QclaUnitPlacement:
    """Source logical values resident while one PBC event executes."""

    unit_id: str
    required_values: tuple[str, ...]
    resident_values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QclaFixedOrderSchedule:
    """Deterministic QCLA move stream with auditable transfer categories."""

    trace_id: str
    source_logical_capacity: int
    load_cost: int
    store_cost: int
    actions: tuple[TransferAction, ...]
    placements: tuple[QclaUnitPlacement, ...]
    compulsory_input_loads: int
    reloads: int
    eviction_stores: int
    final_output_stores: int
    clean_ancilla_creations: int
    peak_source_logical_occupancy: int
    objective_cost: int
    policy_identity: str = QCLA_FIXED_ORDER_POLICY
    transfer_semantics: str = MEMORY_TRANSFER_SEMANTICS

    @property
    def loads(self) -> int:
        return self.compulsory_input_loads + self.reloads

    @property
    def stores(self) -> int:
        return self.eviction_stores + self.final_output_stores


@dataclass(frozen=True, slots=True)
class QclaPlacementReplaySummary:
    """Location and transfer facts reproduced independently from actions."""

    loads: int
    stores: int
    compulsory_input_loads: int
    reloads: int
    final_memory_inputs_outputs: tuple[str, ...]
    final_released_clean_ancillas: tuple[str, ...]
    final_processor_values: tuple[str, ...]


def _virtual_ancilla_id(source_value_id: str, reuse_epoch: int) -> str:
    return f"{source_value_id}#epoch:{reuse_epoch}"


def adapt_qcla_schedule_to_memory_program(
    trace: QclaTrace,
    lowering: QclaLogicalLowering,
    base_schedule: AdaptivePbcSchedule,
) -> QclaMemoryProgram:
    """Map QCLA source values onto an already selected PBC event order."""

    if lowering.qcla_trace_id != trace.trace_id:
        raise MemoryIoError("QCLA trace and logical lowering identity mismatch")
    if base_schedule.trace_id == "" or base_schedule.trace_id != (
        f"{lowering.logical_trace.trace_id}:adaptive-pbc-v1"
    ):
        raise MemoryIoError("QCLA logical lowering and PBC schedule identity mismatch")
    primitives = {
        primitive.primitive_id: primitive for primitive in lowering.logical_trace.primitives
    }
    provenance = {record.primitive_id: record for record in lowering.provenance}
    intervals_by_source: dict[str, list[QclaAncillaInterval]] = defaultdict(list)
    for interval in trace.ancilla_intervals:
        intervals_by_source[interval.value_id].append(interval)

    units: list[QclaMemoryUnit] = []
    uses: dict[str, list[int]] = defaultdict(list)
    sources: dict[str, tuple[str, QclaMemoryValueOrigin]] = {}
    for unit_index, event in enumerate(base_schedule.events):
        event_primitives = []
        for primitive_id in event.source_primitive_ids:
            try:
                event_primitives.append(primitives[primitive_id])
            except KeyError as exc:
                raise MemoryIoError("PBC event references an unknown QCLA primitive") from exc
        remapped: list[str] = []
        for source_value_id in event.logical_support:
            if source_value_id not in intervals_by_source:
                if not source_value_id.startswith(("a:", "b:")):
                    raise MemoryIoError("PBC event references an unknown QCLA source value")
                value_id = source_value_id
                origin = QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT
            else:
                layers = {
                    provenance[primitive.primitive_id].source_algorithmic_layer
                    for primitive in event_primitives
                    if source_value_id in primitive.logical_support
                }
                matching_epochs = {
                    interval.reuse_epoch
                    for interval in intervals_by_source[source_value_id]
                    for layer in layers
                    if interval.start_layer <= layer <= interval.end_layer
                }
                if len(matching_epochs) != 1:
                    raise MemoryIoError(
                        f"cannot assign {source_value_id!r} to one clean ancilla epoch"
                    )
                value_id = _virtual_ancilla_id(source_value_id, matching_epochs.pop())
                origin = QclaMemoryValueOrigin.CLEAN_ANCILLA_EPOCH
            prior = sources.setdefault(value_id, (source_value_id, origin))
            if prior != (source_value_id, origin):
                raise MemoryIoError("QCLA virtual value origin is inconsistent")
            remapped.append(value_id)
            uses[value_id].append(unit_index)
        units.append(
            QclaMemoryUnit(
                unit_id=f"qcla-pbc-memory-unit:{unit_index:06d}",
                source_event_id=event.event_id,
                unit_index=unit_index,
                value_support=tuple(sorted(remapped)),
            )
        )
    values = tuple(
        QclaMemoryValue(
            value_id=value_id,
            source_value_id=sources[value_id][0],
            origin=sources[value_id][1],
            first_unit_index=indices[0],
            last_unit_index=indices[-1],
        )
        for value_id, indices in sorted(uses.items())
    )
    program = QclaMemoryProgram(
        trace_id=f"{trace.trace_id}:qcla-memory-order-v1",
        width=trace.width,
        units=tuple(units),
        values=values,
    )
    expected_inputs = {
        *(f"a:{index}" for index in range(trace.width)),
        *(f"b:{index}" for index in range(trace.width)),
    }
    if program.input_output_value_ids != expected_inputs:
        raise MemoryIoError("QCLA memory program does not cover both complete data registers")
    return program


def _future_use_queues(program: QclaMemoryProgram) -> dict[str, deque[int]]:
    future: dict[str, deque[int]] = {value.value_id: deque() for value in program.values}
    for unit in program.units:
        for value_id in unit.value_support:
            future[value_id].append(unit.unit_index)
    return future


def _action_order(action: TransferAction) -> tuple[int, int, str, str]:
    return (
        action.boundary_index,
        0 if action.kind is TransferKind.STORE else 1,
        action.value_id,
        action.reason.value,
    )


def _expected_qcla_fixed_order(
    program: QclaMemoryProgram, source_logical_capacity: int
) -> tuple[tuple[TransferAction, ...], tuple[QclaUnitPlacement, ...]]:
    if isinstance(source_logical_capacity, bool) or source_logical_capacity < 1:
        raise MemoryIoError("QCLA source logical capacity must be positive")
    values = program.values_by_id
    future = _future_use_queues(program)
    resident: set[str] = set()
    memory = set(program.input_output_value_ids)
    actions: list[TransferAction] = []
    placements: list[QclaUnitPlacement] = []
    for unit in program.units:
        required = set(unit.value_support)
        if len(required) > source_logical_capacity:
            raise MemoryIoError(
                f"{unit.unit_id} atomic support exceeds QCLA source logical capacity"
            )
        for value_id in required:
            queue = future[value_id]
            if not queue or queue[0] != unit.unit_index:
                raise MemoryIoError("QCLA future-use queue is out of sync")
            queue.popleft()
        missing = required - resident
        unavailable = {
            value_id
            for value_id in missing
            if value_id not in memory
            and not (
                values[value_id].origin is QclaMemoryValueOrigin.CLEAN_ANCILLA_EPOCH
                and values[value_id].first_unit_index == unit.unit_index
            )
        }
        if unavailable:
            raise MemoryIoError("QCLA value is required before creation or without a copy")
        evicted: set[str] = set()
        while len(resident) + len(missing) > source_logical_capacity:
            candidates = resident - required
            if not candidates:
                raise MemoryIoError(f"no QCLA Belady victim exists at {unit.unit_id}")
            victim = max(
                candidates,
                key=lambda value_id: (
                    future[value_id][0] if future[value_id] else len(program.units),
                    value_id,
                ),
            )
            resident.remove(victim)
            memory.add(victim)
            evicted.add(victim)
        actions.extend(
            TransferAction(
                unit.unit_index,
                value_id,
                TransferKind.STORE,
                TransferReason.EVICTION_RETURN,
            )
            for value_id in sorted(evicted)
        )
        loaded = missing & memory
        actions.extend(
            TransferAction(
                unit.unit_index,
                value_id,
                TransferKind.LOAD,
                TransferReason.REQUIRED_LOAD,
            )
            for value_id in sorted(loaded)
        )
        memory.difference_update(loaded)
        resident.update(missing)
        placements.append(
            QclaUnitPlacement(
                unit_id=unit.unit_id,
                required_values=tuple(sorted(required)),
                resident_values=tuple(sorted(resident)),
            )
        )
        for value_id in sorted(required):
            value = values[value_id]
            if value.last_unit_index != unit.unit_index:
                continue
            if value.origin is QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT:
                actions.append(
                    TransferAction(
                        unit.unit_index + 1,
                        value_id,
                        TransferKind.STORE,
                        TransferReason.FINAL_RETURN,
                    )
                )
                memory.add(value_id)
            resident.remove(value_id)
    if resident:
        raise MemoryIoError("QCLA placement leaves source values in the processor")
    if memory != program.input_output_value_ids:
        raise MemoryIoError("QCLA placement does not return exactly the data registers")
    return tuple(sorted(actions, key=_action_order)), tuple(placements)


def schedule_qcla_fixed_order_belady(
    program: QclaMemoryProgram,
    source_logical_capacity: int,
    *,
    load_cost: int = 1,
    store_cost: int = 1,
) -> QclaFixedOrderSchedule:
    """Place a fixed event order with farthest-next-use retention."""

    for name, cost_value in (("load_cost", load_cost), ("store_cost", store_cost)):
        if isinstance(cost_value, bool) or not isinstance(cost_value, int) or cost_value < 0:
            raise MemoryIoError(f"{name} must be a nonnegative integer")
    actions, placements = _expected_qcla_fixed_order(program, source_logical_capacity)
    values = program.values_by_id
    loaded_before: set[str] = set()
    compulsory = 0
    reloads = 0
    eviction_stores = 0
    final_stores = 0
    for action in actions:
        if action.kind is TransferKind.LOAD:
            value = values[action.value_id]
            if (
                value.origin is QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT
                and action.value_id not in loaded_before
            ):
                compulsory += 1
            else:
                reloads += 1
            loaded_before.add(action.value_id)
        elif action.reason is TransferReason.EVICTION_RETURN:
            eviction_stores += 1
        else:
            final_stores += 1
    creations = sum(
        value.origin is QclaMemoryValueOrigin.CLEAN_ANCILLA_EPOCH for value in program.values
    )
    loads = compulsory + reloads
    stores = eviction_stores + final_stores
    schedule = QclaFixedOrderSchedule(
        trace_id=program.trace_id,
        source_logical_capacity=source_logical_capacity,
        load_cost=load_cost,
        store_cost=store_cost,
        actions=actions,
        placements=placements,
        compulsory_input_loads=compulsory,
        reloads=reloads,
        eviction_stores=eviction_stores,
        final_output_stores=final_stores,
        clean_ancilla_creations=creations,
        peak_source_logical_occupancy=max(
            len(placement.resident_values) for placement in placements
        ),
        objective_cost=loads * load_cost + stores * store_cost,
    )
    validate_qcla_fixed_order_schedule(program, schedule)
    return schedule


def _actions_by_boundary(
    actions: tuple[TransferAction, ...], boundary_count: int
) -> tuple[tuple[TransferAction, ...], ...]:
    grouped: list[list[TransferAction]] = [[] for _ in range(boundary_count)]
    for action in actions:
        if not 0 <= action.boundary_index < boundary_count:
            raise MemoryIoError("QCLA transfer action has an invalid boundary")
        grouped[action.boundary_index].append(action)
    return tuple(tuple(group) for group in grouped)


def replay_qcla_fixed_order_schedule(
    program: QclaMemoryProgram, schedule: QclaFixedOrderSchedule
) -> QclaPlacementReplaySummary:
    """Replay moves without consulting the Belady victim-selection logic."""

    if schedule.transfer_semantics != MEMORY_TRANSFER_SEMANTICS:
        raise MemoryIoError("QCLA replay received different transfer semantics")
    values = program.values_by_id
    memory = set(program.input_output_value_ids)
    resident: set[str] = set()
    released: set[str] = set()
    loaded_before: set[str] = set()
    compulsory = 0
    reloads = 0
    grouped = _actions_by_boundary(schedule.actions, len(program.units) + 1)
    for unit in program.units:
        boundary_actions = grouped[unit.unit_index]
        stores = tuple(action for action in boundary_actions if action.kind is TransferKind.STORE)
        loads = tuple(action for action in boundary_actions if action.kind is TransferKind.LOAD)
        if boundary_actions != stores + loads:
            raise MemoryIoError("QCLA boundary must store before loading")
        for action in stores:
            if action.value_id not in resident:
                raise MemoryIoError("QCLA replay cannot store a non-resident value")
            value = values[action.value_id]
            if action.reason is TransferReason.FINAL_RETURN:
                if (
                    value.origin is not QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT
                    or value.last_unit_index + 1 != unit.unit_index
                ):
                    raise MemoryIoError("QCLA final return has the wrong origin or boundary")
            elif action.reason is not TransferReason.EVICTION_RETURN:
                raise MemoryIoError("QCLA nonfinal store must be an eviction")
            resident.remove(action.value_id)
            memory.add(action.value_id)
        for action in loads:
            if action.reason is not TransferReason.REQUIRED_LOAD:
                raise MemoryIoError("QCLA loads must be required loads")
            if action.value_id not in unit.value_support or action.value_id not in memory:
                raise MemoryIoError("QCLA replay forbids prefetches and free copies")
            memory.remove(action.value_id)
            resident.add(action.value_id)
            value = values[action.value_id]
            if (
                value.origin is QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT
                and action.value_id not in loaded_before
            ):
                compulsory += 1
            else:
                reloads += 1
            loaded_before.add(action.value_id)
        required = set(unit.value_support)
        for value_id in required - resident:
            value = values[value_id]
            if (
                value.origin is not QclaMemoryValueOrigin.CLEAN_ANCILLA_EPOCH
                or value.first_unit_index != unit.unit_index
                or value_id in memory
                or value_id in released
            ):
                raise MemoryIoError("QCLA replay observes use before origin")
            resident.add(value_id)
        if not required.issubset(resident):
            raise MemoryIoError("QCLA event executes without its required values")
        placement = schedule.placements[unit.unit_index]
        if (
            placement.unit_id != unit.unit_id
            or placement.required_values != tuple(sorted(required))
            or placement.resident_values != tuple(sorted(resident))
        ):
            raise MemoryIoError("QCLA placement does not match independent replay")
        if len(resident) > schedule.source_logical_capacity:
            raise MemoryIoError("QCLA replay exceeds source logical capacity")
        for value_id in required:
            value = values[value_id]
            if (
                value.origin is QclaMemoryValueOrigin.CLEAN_ANCILLA_EPOCH
                and value.last_unit_index == unit.unit_index
            ):
                resident.remove(value_id)
                released.add(value_id)
    for action in grouped[-1]:
        if (
            action.kind is not TransferKind.STORE
            or action.reason is not TransferReason.FINAL_RETURN
            or action.value_id not in resident
        ):
            raise MemoryIoError("QCLA final boundary contains an invalid action")
        value = values[action.value_id]
        if (
            value.origin is not QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT
            or value.last_unit_index + 1 != len(program.units)
        ):
            raise MemoryIoError("QCLA final-boundary return has invalid provenance")
        resident.remove(action.value_id)
        memory.add(action.value_id)
    clean_values = {
        value.value_id
        for value in program.values
        if value.origin is QclaMemoryValueOrigin.CLEAN_ANCILLA_EPOCH
    }
    if resident or memory != program.input_output_value_ids or released != clean_values:
        raise MemoryIoError("QCLA replay has an invalid final location state")
    loads_count = sum(action.kind is TransferKind.LOAD for action in schedule.actions)
    stores_count = sum(action.kind is TransferKind.STORE for action in schedule.actions)
    if (
        compulsory != schedule.compulsory_input_loads
        or reloads != schedule.reloads
        or loads_count != schedule.loads
        or stores_count != schedule.stores
        or schedule.objective_cost
        != loads_count * schedule.load_cost + stores_count * schedule.store_cost
    ):
        raise MemoryIoError("QCLA replay transfer counts disagree")
    return QclaPlacementReplaySummary(
        loads=loads_count,
        stores=stores_count,
        compulsory_input_loads=compulsory,
        reloads=reloads,
        final_memory_inputs_outputs=tuple(sorted(memory)),
        final_released_clean_ancillas=tuple(sorted(released)),
        final_processor_values=tuple(sorted(resident)),
    )


def validate_qcla_fixed_order_schedule(
    program: QclaMemoryProgram, schedule: QclaFixedOrderSchedule
) -> None:
    """Require deterministic Belady output and an independent location replay."""

    if schedule.trace_id != program.trace_id:
        raise MemoryIoError("QCLA fixed-order schedule trace mismatch")
    if schedule.policy_identity != QCLA_FIXED_ORDER_POLICY:
        raise MemoryIoError("QCLA fixed-order policy identity mismatch")
    if tuple(sorted(schedule.actions, key=_action_order)) != schedule.actions:
        raise MemoryIoError("QCLA transfer actions are not canonically ordered")
    expected_actions, expected_placements = _expected_qcla_fixed_order(
        program, schedule.source_logical_capacity
    )
    if schedule.actions != expected_actions or schedule.placements != expected_placements:
        raise MemoryIoError("QCLA schedule is not deterministic fixed-order Belady output")
    if len(schedule.placements) != len(program.units):
        raise MemoryIoError("QCLA placement count mismatch")
    replay_qcla_fixed_order_schedule(program, schedule)


def qcla_fixed_order_schedule_to_data(schedule: QclaFixedOrderSchedule) -> dict[str, Any]:
    """Return a deterministic compact JSON-compatible placement summary."""

    return {
        "clean_ancilla_creations": schedule.clean_ancilla_creations,
        "compulsory_input_loads": schedule.compulsory_input_loads,
        "eviction_stores": schedule.eviction_stores,
        "final_output_stores": schedule.final_output_stores,
        "loads": schedule.loads,
        "objective_cost": schedule.objective_cost,
        "peak_source_logical_occupancy": schedule.peak_source_logical_occupancy,
        "policy_identity": schedule.policy_identity,
        "reloads": schedule.reloads,
        "source_logical_capacity": schedule.source_logical_capacity,
        "stores": schedule.stores,
        "trace_id": schedule.trace_id,
        "transfer_action_count": len(schedule.actions),
        "transfer_semantics": schedule.transfer_semantics,
    }
