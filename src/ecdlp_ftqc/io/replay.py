"""Independent replay validation for memory-I/O action streams."""

from __future__ import annotations

from dataclasses import dataclass

from ecdlp_ftqc.io.model import (
    MEMORY_TRANSFER_SEMANTICS,
    FixedOrderSchedule,
    MemoryIoError,
    MemoryProgram,
    MemoryValueOrigin,
    PartitionLayout,
    PartitionSchedule,
    TransferAction,
    TransferKind,
    TransferReason,
)


@dataclass(frozen=True, slots=True)
class ReplaySummary:
    """Counts and final location facts reproduced from an action stream."""

    loads: int
    stores: int
    objective_cost: int
    final_processor_values: tuple[str, ...]


def _actions_by_boundary(
    actions: tuple[TransferAction, ...], boundary_count: int
) -> tuple[tuple[TransferAction, ...], ...]:
    grouped: list[list[TransferAction]] = [[] for _ in range(boundary_count)]
    for action in actions:
        if not 0 <= action.boundary_index < boundary_count:
            raise MemoryIoError("transfer action has an invalid boundary")
        grouped[action.boundary_index].append(action)
    return tuple(tuple(values) for values in grouped)


def _apply_store(resident: set[str], action: TransferAction) -> None:
    if action.value_id not in resident:
        raise MemoryIoError(f"cannot store non-resident value {action.value_id!r}")
    resident.remove(action.value_id)


def _apply_load(resident: set[str], action: TransferAction) -> None:
    if action.value_id in resident:
        raise MemoryIoError(f"cannot load resident value {action.value_id!r}")
    resident.add(action.value_id)


def replay_fixed_order_schedule(
    program: MemoryProgram, schedule: FixedOrderSchedule
) -> ReplaySummary:
    """Replay fixed-order moves without consulting the placement algorithm."""

    if schedule.transfer_semantics != MEMORY_TRANSFER_SEMANTICS:
        raise MemoryIoError("fixed-order replay received different transfer semantics")
    if len(schedule.placements) != len(program.units):
        raise MemoryIoError("fixed-order replay placement count mismatch")
    memory_values = program.memory_value_ids
    grouped = _actions_by_boundary(schedule.actions, len(program.units) + 1)
    resident: set[str] = set()
    for boundary_index, unit in enumerate(program.units):
        for action in grouped[boundary_index]:
            if action.value_id not in memory_values:
                raise MemoryIoError("fixed-order action references a non-memory value")
            if action.kind is TransferKind.STORE:
                if action.reason is not TransferReason.EVICTION_RETURN:
                    raise MemoryIoError("nonfinal fixed-order store must be an eviction")
                _apply_store(resident, action)
            else:
                if action.reason is not TransferReason.REQUIRED_LOAD:
                    raise MemoryIoError("fixed-order load must be required")
                if action.value_id not in unit.memory_support:
                    raise MemoryIoError("fixed-order policy cannot prefetch")
                _apply_load(resident, action)
        required = set(unit.memory_support)
        if not required.issubset(resident):
            raise MemoryIoError(f"{unit.unit_id} executes without required values")
        local = set(unit.occupancy_support) - memory_values
        processor = resident | local
        placement = schedule.placements[boundary_index]
        if (
            placement.unit_id != unit.unit_id
            or placement.resident_memory != tuple(sorted(resident))
            or placement.local_occupancy != tuple(sorted(local))
            or placement.processor_occupancy != tuple(sorted(processor))
        ):
            raise MemoryIoError("fixed-order placement does not match replay")
        if len(processor) > schedule.capacity:
            raise MemoryIoError("fixed-order replay exceeds processor capacity")
    for action in grouped[-1]:
        if action.kind is not TransferKind.STORE:
            raise MemoryIoError("final fixed-order boundary cannot load")
        if action.reason is not TransferReason.FINAL_RETURN:
            raise MemoryIoError("final fixed-order store must be a final return")
        _apply_store(resident, action)
    if resident:
        raise MemoryIoError("fixed-order replay leaves values in the processor")
    loads = sum(action.kind is TransferKind.LOAD for action in schedule.actions)
    stores = sum(action.kind is TransferKind.STORE for action in schedule.actions)
    objective = loads * schedule.load_cost + stores * schedule.store_cost
    if (
        loads != schedule.loads
        or stores != schedule.stores
        or objective != schedule.objective_cost
    ):
        raise MemoryIoError("fixed-order replay count or objective mismatch")
    return ReplaySummary(loads, stores, objective, tuple(sorted(resident)))


def _alive_after(value_origin: MemoryValueOrigin, release: int | None, stop: int) -> bool:
    if value_origin is MemoryValueOrigin.MEMORY_INPUT_OR_INOUT:
        return True
    if release is None:
        raise MemoryIoError("processor-generated value lacks a release unit")
    return release >= stop


def replay_partition_schedule(
    program: MemoryProgram,
    layout: PartitionLayout,
    schedule: PartitionSchedule,
) -> ReplaySummary:
    """Replay partition moves and enforce origin, location, and category rules."""

    if schedule.transfer_semantics != MEMORY_TRANSFER_SEMANTICS:
        raise MemoryIoError("partition replay received different transfer semantics")
    if len(schedule.placements) != len(layout.partitions):
        raise MemoryIoError("partition replay placement count mismatch")
    values = program.values_by_id
    grouped = _actions_by_boundary(schedule.actions, len(layout.partitions) + 1)
    resident: set[str] = set()
    spilled: set[str] = set()
    previous_exit: tuple[str, ...] | None = None
    for partition in layout.partitions:
        boundary_actions = grouped[partition.partition_index]
        boundary_stores = tuple(
            action for action in boundary_actions if action.kind is TransferKind.STORE
        )
        boundary_loads = tuple(
            action for action in boundary_actions if action.kind is TransferKind.LOAD
        )
        if boundary_actions != boundary_stores + boundary_loads:
            raise MemoryIoError("partition boundary must store before loading")
        for action in boundary_stores:
            if action.reason is not TransferReason.PARTITION_BOUNDARY_SPILL:
                raise MemoryIoError("nonfinal partition store must be a spill")
            _apply_store(resident, action)
            spilled.add(action.value_id)
        if previous_exit is not None and previous_exit != tuple(sorted(resident)):
            raise MemoryIoError("partition exit retention does not match replay")
        for action in boundary_loads:
            value = values[action.value_id]
            if value.origin is MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY:
                if action.value_id not in spilled:
                    raise MemoryIoError("processor-generated value loads before a spill")
                if value.birth_unit_index is None:
                    raise MemoryIoError("processor-generated value lacks a birth unit")
                if value.birth_unit_index >= partition.start_unit_index:
                    raise MemoryIoError("processor-generated value loads before creation")
            expected_reason = (
                TransferReason.PARTITION_BOUNDARY_RELOAD
                if action.value_id in spilled
                else TransferReason.BASELINE_INTERFACE_TRANSFER
            )
            if action.reason is not expected_reason:
                raise MemoryIoError("partition load category does not match replay")
            _apply_load(resident, action)
        placement = schedule.placements[partition.partition_index]
        if placement.entry_resident != tuple(sorted(resident)):
            raise MemoryIoError("partition entry placement does not match replay")
        required = set(partition.memory_interface)
        required.update(
            value.value_id
            for value in program.values
            if value.origin is MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY
            and value.birth_unit_index is not None
            and value.release_unit_index is not None
            and value.birth_unit_index < partition.start_unit_index
            and value.release_unit_index >= partition.start_unit_index
        )
        if not required.issubset(resident):
            raise MemoryIoError("partition begins without a required value")
        peak = max(
            len(
                set(unit.occupancy_support)
                | set(partition.memory_interface)
                | resident
            )
            for unit in program.units[
                partition.start_unit_index : partition.stop_unit_index
            ]
        )
        if placement.peak_processor_occupancy != peak or peak > layout.capacity:
            raise MemoryIoError("partition peak occupancy does not match replay")
        for value in program.values:
            if (
                value.origin is MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY
                and value.birth_unit_index is not None
                and partition.start_unit_index
                <= value.birth_unit_index
                < partition.stop_unit_index
            ):
                resident.add(value.value_id)
        resident = {
            value_id
            for value_id in resident
            if _alive_after(
                values[value_id].origin,
                values[value_id].release_unit_index,
                partition.stop_unit_index,
            )
        }
        if placement.post_partition_live_resident != tuple(sorted(resident)):
            raise MemoryIoError("partition live-exit placement does not match replay")
        previous_exit = placement.exit_resident

    final_actions = grouped[-1]
    if any(action.kind is not TransferKind.STORE for action in final_actions):
        raise MemoryIoError("final partition boundary cannot load")
    for action in final_actions:
        if action.reason is not TransferReason.BASELINE_INTERFACE_TRANSFER:
            raise MemoryIoError("final partition store must be a baseline return")
        _apply_store(resident, action)
    if previous_exit != tuple(sorted(resident)):
        raise MemoryIoError("final partition exit does not match replay")
    if resident:
        raise MemoryIoError("partition replay leaves values in the processor")
    loads = sum(action.kind is TransferKind.LOAD for action in schedule.actions)
    stores = sum(action.kind is TransferKind.STORE for action in schedule.actions)
    objective = loads * schedule.load_cost + stores * schedule.store_cost
    if (
        loads != schedule.loads
        or stores != schedule.stores
        or objective != schedule.objective_cost
    ):
        raise MemoryIoError("partition replay count or objective mismatch")
    return ReplaySummary(loads, stores, objective, tuple(sorted(resident)))
