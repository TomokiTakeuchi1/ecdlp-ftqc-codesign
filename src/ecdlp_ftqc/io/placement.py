"""Deterministic fixed-order and partition-aware I/O placement policies."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations

from ecdlp_ftqc.io.model import (
    FIXED_ORDER_BELADY_POLICY,
    MEMORY_TRANSFER_SEMANTICS,
    SMALL_WIDTH_PARTITION_REFERENCE_POLICY,
    FixedOrderSchedule,
    MemoryIoError,
    MemoryPartition,
    MemoryProgram,
    MemoryValue,
    MemoryValueOrigin,
    PartitionLayout,
    PartitionPlacement,
    PartitionSchedule,
    TransferAction,
    TransferKind,
    TransferReason,
    UnitPlacement,
)

SMALL_WIDTH_REFERENCE_WIDTHS = (2, 3, 4)


def _positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise MemoryIoError(f"{name} must be a positive integer")


def _nonnegative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MemoryIoError(f"{name} must be a nonnegative integer")


def _future_use_queues(program: MemoryProgram) -> dict[str, deque[int]]:
    future: dict[str, deque[int]] = {}
    for unit_index, unit in enumerate(program.units):
        for value_id in unit.memory_support:
            future.setdefault(value_id, deque()).append(unit_index)
    return future


def _expected_fixed_order_belady(
    program: MemoryProgram, capacity: int
) -> tuple[tuple[TransferAction, ...], tuple[UnitPlacement, ...]]:
    future_uses = _future_use_queues(program)
    memory_values = program.memory_value_ids
    resident: set[str] = set()
    actions: list[TransferAction] = []
    placements: list[UnitPlacement] = []
    for boundary_index, unit in enumerate(program.units):
        required = set(unit.memory_support)
        local = set(unit.occupancy_support) - memory_values
        memory_capacity = capacity - len(local)
        if memory_capacity < len(required):
            raise MemoryIoError(
                f"{unit.unit_id} requires {len(required) + len(local)} processor values, "
                f"exceeding capacity {capacity}"
            )
        for value_id in required:
            uses = future_uses[value_id]
            if not uses or uses[0] != boundary_index:
                raise MemoryIoError("future-use queue is out of sync")
            uses.popleft()
        missing = required - resident
        evicted: set[str] = set()
        while len(resident) + len(missing) > memory_capacity:
            candidates = resident - required
            if not candidates:
                raise MemoryIoError(f"no Belady victim exists at {unit.unit_id}")
            victim = max(
                candidates,
                key=lambda value_id: (
                    future_uses[value_id][0]
                    if future_uses.get(value_id)
                    else len(program.units),
                    value_id,
                ),
            )
            resident.remove(victim)
            evicted.add(victim)
        actions.extend(
            TransferAction(
                boundary_index,
                value_id,
                TransferKind.STORE,
                TransferReason.EVICTION_RETURN,
            )
            for value_id in sorted(evicted)
        )
        actions.extend(
            TransferAction(
                boundary_index,
                value_id,
                TransferKind.LOAD,
                TransferReason.REQUIRED_LOAD,
            )
            for value_id in sorted(missing)
        )
        resident.update(missing)
        processor = resident | local
        placements.append(
            UnitPlacement(
                unit_id=unit.unit_id,
                resident_memory=tuple(sorted(resident)),
                local_occupancy=tuple(sorted(local)),
                processor_occupancy=tuple(sorted(processor)),
            )
        )
    actions.extend(
        TransferAction(
            len(program.units),
            value_id,
            TransferKind.STORE,
            TransferReason.FINAL_RETURN,
        )
        for value_id in sorted(resident)
    )
    return tuple(actions), tuple(placements)


def schedule_fixed_order_belady(
    program: MemoryProgram,
    capacity: int,
    *,
    load_cost: int = 1,
    store_cost: int = 1,
) -> FixedOrderSchedule:
    """Schedule a supplied fixed unit order by farthest-next-use retention."""

    _positive_integer("capacity", capacity)
    _nonnegative_integer("load_cost", load_cost)
    _nonnegative_integer("store_cost", store_cost)
    actions, placements = _expected_fixed_order_belady(program, capacity)
    loads = sum(action.kind is TransferKind.LOAD for action in actions)
    stores = sum(action.kind is TransferKind.STORE for action in actions)
    schedule = FixedOrderSchedule(
        circuit_id=program.circuit_id,
        capacity=capacity,
        load_cost=load_cost,
        store_cost=store_cost,
        actions=actions,
        placements=placements,
        loads=loads,
        stores=stores,
        objective_cost=loads * load_cost + stores * store_cost,
    )
    validate_fixed_order_schedule(program, schedule)
    return schedule


def _action_order(action: TransferAction) -> tuple[int, int, str, str]:
    return (
        action.boundary_index,
        0 if action.kind is TransferKind.STORE else 1,
        action.value_id,
        action.reason.value,
    )


def validate_fixed_order_schedule(
    program: MemoryProgram, schedule: FixedOrderSchedule
) -> None:
    """Replay and require the deterministic fixed-order Belady stream."""

    _positive_integer("capacity", schedule.capacity)
    _nonnegative_integer("load_cost", schedule.load_cost)
    _nonnegative_integer("store_cost", schedule.store_cost)
    if schedule.circuit_id != program.circuit_id:
        raise MemoryIoError("fixed-order schedule circuit mismatch")
    if schedule.policy_identity != FIXED_ORDER_BELADY_POLICY:
        raise MemoryIoError("fixed-order policy identity mismatch")
    if schedule.transfer_semantics != MEMORY_TRANSFER_SEMANTICS:
        raise MemoryIoError("fixed-order transfer semantics mismatch")
    if len(schedule.placements) != len(program.units):
        raise MemoryIoError("fixed-order placement count mismatch")
    if tuple(sorted(schedule.actions, key=_action_order)) != schedule.actions:
        raise MemoryIoError("fixed-order actions are not canonically ordered")
    expected_actions, expected_placements = _expected_fixed_order_belady(
        program, schedule.capacity
    )
    if schedule.actions != expected_actions or schedule.placements != expected_placements:
        raise MemoryIoError("fixed-order schedule is not deterministic Belady output")
    loads = sum(action.kind is TransferKind.LOAD for action in schedule.actions)
    stores = sum(action.kind is TransferKind.STORE for action in schedule.actions)
    if schedule.loads != loads or schedule.stores != stores:
        raise MemoryIoError("fixed-order transfer counts mismatch")
    if schedule.objective_cost != loads * schedule.load_cost + stores * schedule.store_cost:
        raise MemoryIoError("fixed-order objective mismatch")
    from ecdlp_ftqc.io.replay import replay_fixed_order_schedule

    replay_fixed_order_schedule(program, schedule)


def _derive_partition_layout(program: MemoryProgram, capacity: int) -> PartitionLayout:
    _positive_integer("capacity", capacity)
    memory_values = program.memory_value_ids
    partitions: list[MemoryPartition] = []
    start = 0
    while start < len(program.units):
        memory_interface: set[str] = set()
        peak_local = 0
        selected_stop: int | None = None
        selected_memory: tuple[str, ...] | None = None
        selected_peak = 0
        for unit_index in range(start, len(program.units)):
            unit = program.units[unit_index]
            memory_interface.update(unit.memory_support)
            peak_local = max(
                peak_local, len(set(unit.occupancy_support) - memory_values)
            )
            footprint = len(memory_interface) + peak_local
            if footprint > capacity:
                break
            selected_stop = unit_index + 1
            selected_memory = tuple(sorted(memory_interface))
            selected_peak = peak_local
        if selected_stop is None or selected_memory is None:
            unit = program.units[start]
            local = len(set(unit.occupancy_support) - memory_values)
            raise MemoryIoError(
                f"{unit.unit_id} atomic footprint "
                f"{len(unit.memory_support) + local} exceeds capacity {capacity}"
            )
        partitions.append(
            MemoryPartition(
                partition_index=len(partitions),
                start_unit_index=start,
                stop_unit_index=selected_stop,
                unit_ids=tuple(
                    unit.unit_id for unit in program.units[start:selected_stop]
                ),
                memory_interface=selected_memory,
                peak_live_local_occupancy=selected_peak,
                footprint=len(selected_memory) + selected_peak,
            )
        )
        start = selected_stop
    return PartitionLayout(
        circuit_id=program.circuit_id,
        width=program.width,
        capacity=capacity,
        strict_memory_values=tuple(sorted(memory_values)),
        partitions=tuple(partitions),
    )


def build_maximal_prefix_partitions(
    program: MemoryProgram, capacity: int
) -> PartitionLayout:
    """Build deterministic maximal feasible source-unit prefixes."""

    layout = _derive_partition_layout(program, capacity)
    validate_partition_layout(program, layout)
    return layout


def validate_partition_layout(program: MemoryProgram, layout: PartitionLayout) -> None:
    """Re-derive partition coverage, footprint, and maximality."""

    if layout != _derive_partition_layout(program, layout.capacity):
        raise MemoryIoError("partition layout does not match maximal-prefix derivation")


def _subsets(values: set[str]) -> tuple[frozenset[str], ...]:
    ordered = tuple(sorted(values))
    return tuple(
        frozenset(selection)
        for size in range(len(ordered) + 1)
        for selection in combinations(ordered, size)
    )


def _alive_after_partition(value: MemoryValue, stop_unit_index: int) -> bool:
    if value.origin is MemoryValueOrigin.MEMORY_INPUT_OR_INOUT:
        return True
    if value.release_unit_index is None:
        raise MemoryIoError(f"generated value {value.value_id!r} lacks a release unit")
    return value.release_unit_index >= stop_unit_index


def _required_entry_values(
    partition: MemoryPartition, values: tuple[MemoryValue, ...]
) -> set[str]:
    required = set(partition.memory_interface)
    for value in values:
        if value.origin is not MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY:
            continue
        if value.birth_unit_index is None or value.release_unit_index is None:
            raise MemoryIoError(f"generated value {value.value_id!r} lacks unit bounds")
        if (
            value.birth_unit_index < partition.start_unit_index
            and value.release_unit_index >= partition.start_unit_index
        ):
            required.add(value.value_id)
    return required


def _peak_occupancy(
    program: MemoryProgram,
    partition: MemoryPartition,
    entry_resident: frozenset[str],
) -> int:
    return max(
        len(
            set(unit.occupancy_support)
            | set(partition.memory_interface)
            | set(entry_resident)
        )
        for unit in program.units[
            partition.start_unit_index : partition.stop_unit_index
        ]
    )


def _post_partition_live_values(
    partition: MemoryPartition,
    entry_resident: frozenset[str],
    values: tuple[MemoryValue, ...],
) -> frozenset[str]:
    available = set(entry_resident)
    for value in values:
        if (
            value.origin is MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY
            and value.birth_unit_index is not None
            and partition.start_unit_index
            <= value.birth_unit_index
            < partition.stop_unit_index
        ):
            available.add(value.value_id)
    by_id = {value.value_id: value for value in values}
    return frozenset(
        value_id
        for value_id in available
        if _alive_after_partition(by_id[value_id], partition.stop_unit_index)
    )


def _transfer_reason(
    value: MemoryValue,
    kind: TransferKind,
    boundary_index: int,
    partition_count: int,
    prior_actions: tuple[TransferAction, ...],
) -> TransferReason:
    if kind is TransferKind.STORE:
        if boundary_index < partition_count:
            return TransferReason.PARTITION_BOUNDARY_SPILL
        return TransferReason.BASELINE_INTERFACE_TRANSFER
    was_spilled = any(
        action.value_id == value.value_id
        and action.kind is TransferKind.STORE
        and action.reason is TransferReason.PARTITION_BOUNDARY_SPILL
        for action in prior_actions
    )
    if was_spilled:
        return TransferReason.PARTITION_BOUNDARY_RELOAD
    if value.origin is MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY:
        raise MemoryIoError(
            f"processor-generated value {value.value_id!r} would load before creation"
        )
    return TransferReason.BASELINE_INTERFACE_TRANSFER


def _actions_for_values(
    *,
    boundary_index: int,
    value_ids: set[str] | frozenset[str],
    kind: TransferKind,
    values_by_id: dict[str, MemoryValue],
    partition_count: int,
    prior_actions: tuple[TransferAction, ...],
) -> tuple[TransferAction, ...]:
    actions: list[TransferAction] = []
    for value_id in sorted(value_ids):
        actions.append(
            TransferAction(
                boundary_index=boundary_index,
                value_id=value_id,
                kind=kind,
                reason=_transfer_reason(
                    values_by_id[value_id],
                    kind,
                    boundary_index,
                    partition_count,
                    prior_actions + tuple(actions),
                ),
            )
        )
    return tuple(actions)


@dataclass(frozen=True, slots=True)
class _PartitionPath:
    actions: tuple[TransferAction, ...]
    placements: tuple[PartitionPlacement, ...]
    objective_cost: int
    loads: int
    stores: int


def _path_key(path: _PartitionPath) -> tuple[object, ...]:
    return (
        path.objective_cost,
        len(path.actions),
        sum(
            action.reason
            in {
                TransferReason.PARTITION_BOUNDARY_SPILL,
                TransferReason.PARTITION_BOUNDARY_RELOAD,
            }
            for action in path.actions
        ),
        path.stores,
        path.loads,
        tuple(
            (
                action.boundary_index,
                action.kind.value,
                action.value_id,
                action.reason.value,
            )
            for action in path.actions
        ),
        tuple(placement.exit_resident for placement in path.placements),
    )


def _compute_small_width_partition_reference(
    program: MemoryProgram,
    layout: PartitionLayout,
    load_cost: int,
    store_cost: int,
) -> PartitionSchedule:
    values = tuple(sorted(program.values, key=lambda value: value.value_id))
    values_by_id = {value.value_id: value for value in values}
    frontier: dict[frozenset[str], _PartitionPath] = {
        frozenset(): _PartitionPath((), (), 0, 0, 0)
    }
    states_explored = 0
    transitions_explored = 0
    for partition in layout.partitions:
        states_explored += len(frontier)
        required = _required_entry_values(partition, values)
        next_frontier: dict[frozenset[str], _PartitionPath] = {}
        is_final = partition.partition_index == len(layout.partitions) - 1
        for resident, path in frontier.items():
            missing = required - set(resident)
            entry = resident | required
            peak = _peak_occupancy(program, partition, frozenset(entry))
            if peak > layout.capacity:
                continue
            entry_actions = _actions_for_values(
                boundary_index=partition.partition_index,
                value_ids=missing,
                kind=TransferKind.LOAD,
                values_by_id=values_by_id,
                partition_count=len(layout.partitions),
                prior_actions=path.actions,
            )
            post_live = _post_partition_live_values(
                partition, frozenset(entry), values
            )
            exit_candidates = (frozenset(),) if is_final else _subsets(set(post_live))
            for exit_resident in exit_candidates:
                transitions_explored += 1
                stored = post_live - exit_resident
                exit_actions = _actions_for_values(
                    boundary_index=partition.partition_index + 1,
                    value_ids=stored,
                    kind=TransferKind.STORE,
                    values_by_id=values_by_id,
                    partition_count=len(layout.partitions),
                    prior_actions=path.actions + entry_actions,
                )
                added_loads = len(entry_actions)
                added_stores = len(exit_actions)
                candidate = _PartitionPath(
                    actions=path.actions + entry_actions + exit_actions,
                    placements=path.placements
                    + (
                        PartitionPlacement(
                            partition_index=partition.partition_index,
                            entry_resident=tuple(sorted(entry)),
                            post_partition_live_resident=tuple(sorted(post_live)),
                            exit_resident=tuple(sorted(exit_resident)),
                            peak_processor_occupancy=peak,
                        ),
                    ),
                    objective_cost=(
                        path.objective_cost
                        + added_loads * load_cost
                        + added_stores * store_cost
                    ),
                    loads=path.loads + added_loads,
                    stores=path.stores + added_stores,
                )
                previous = next_frontier.get(exit_resident)
                if previous is None or _path_key(candidate) < _path_key(previous):
                    next_frontier[exit_resident] = candidate
        if not next_frontier:
            raise MemoryIoError(
                f"no feasible exact placement reaches partition {partition.partition_index}"
            )
        frontier = next_frontier
    final_path = frontier.get(frozenset())
    if final_path is None:
        raise MemoryIoError("partition reference did not return all live values")
    return PartitionSchedule(
        circuit_id=program.circuit_id,
        width=program.width,
        capacity=layout.capacity,
        load_cost=load_cost,
        store_cost=store_cost,
        actions=final_path.actions,
        placements=final_path.placements,
        loads=final_path.loads,
        stores=final_path.stores,
        objective_cost=final_path.objective_cost,
        states_explored=states_explored,
        transitions_explored=transitions_explored,
    )


def schedule_small_width_partition_reference(
    program: MemoryProgram,
    layout: PartitionLayout,
    *,
    load_cost: int = 1,
    store_cost: int = 1,
) -> PartitionSchedule:
    """Exhaustively minimize partition-boundary moves for widths two to four."""

    if program.width not in SMALL_WIDTH_REFERENCE_WIDTHS:
        raise MemoryIoError(
            f"width {program.width} is outside exact reference scope "
            f"{SMALL_WIDTH_REFERENCE_WIDTHS}"
        )
    _nonnegative_integer("load_cost", load_cost)
    _nonnegative_integer("store_cost", store_cost)
    validate_partition_layout(program, layout)
    schedule = _compute_small_width_partition_reference(
        program, layout, load_cost, store_cost
    )
    validate_partition_schedule(program, layout, schedule)
    return schedule


def validate_partition_schedule(
    program: MemoryProgram,
    layout: PartitionLayout,
    schedule: PartitionSchedule,
) -> None:
    """Recompute and exactly compare the deterministic small-width reference."""

    validate_partition_layout(program, layout)
    if program.width not in SMALL_WIDTH_REFERENCE_WIDTHS:
        raise MemoryIoError("only widths two to four admit the exact reference")
    if (
        schedule.circuit_id != program.circuit_id
        or schedule.width != program.width
        or schedule.capacity != layout.capacity
        or schedule.policy_identity != SMALL_WIDTH_PARTITION_REFERENCE_POLICY
        or schedule.transfer_semantics != MEMORY_TRANSFER_SEMANTICS
    ):
        raise MemoryIoError("partition schedule identity or source binding mismatch")
    expected = _compute_small_width_partition_reference(
        program, layout, schedule.load_cost, schedule.store_cost
    )
    if schedule != expected:
        raise MemoryIoError("partition schedule does not match the exact reference")
    from ecdlp_ftqc.io.replay import replay_partition_schedule

    replay_partition_schedule(program, layout, schedule)
