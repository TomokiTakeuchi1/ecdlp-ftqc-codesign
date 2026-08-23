from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import load_gidney_oracle_dag
from ecdlp_ftqc.io import (
    MemoryIoError,
    MemoryValueOrigin,
    TransferKind,
    TransferReason,
    adapt_gidney_dag_to_memory_program,
    build_maximal_prefix_partitions,
    dumps_memory_program,
    replay_fixed_order_schedule,
    replay_partition_schedule,
    schedule_fixed_order_belady,
    schedule_small_width_partition_reference,
    validate_fixed_order_schedule,
    validate_partition_schedule,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
GIDNEY_ROOT = FIXTURE_ROOT / "gidney_oracle"
REFERENCE_PATH = FIXTURE_ROOT / "memory_io" / "legacy_partition_reference.json"


def _program(width: int):  # type: ignore[no-untyped-def]
    dag = load_gidney_oracle_dag(
        GIDNEY_ROOT / f"gidney_width{width}_oracle_v3.json"
    )
    return adapt_gidney_dag_to_memory_program(dag)


@pytest.mark.parametrize("width", (2, 3, 4))
def test_gidney_memory_program_reproduces_source_structure(width: int) -> None:
    program = _program(width)
    memory_values = {
        value.value_id
        for value in program.values
        if value.origin is MemoryValueOrigin.MEMORY_INPUT_OR_INOUT
    }
    generated_values = {
        value.value_id
        for value in program.values
        if value.origin is MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY
    }

    assert len(program.units) == 10 * width - 13
    assert len(memory_values) == 2 * width
    assert len(generated_values) == width - 1
    assert max(len(unit.occupancy_support) for unit in program.units) == width + 1
    assert dumps_memory_program(program) == dumps_memory_program(_program(width))


def test_small_width_partition_reference_matches_pinned_legacy_results() -> None:
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    assert reference["source_commit"] == "75a6e83d5acde37f0987ab867352ee8b2c6afd10"
    for width_text, expected_rows in reference["widths"].items():
        program = _program(int(width_text))
        for expected in expected_rows:
            layout = build_maximal_prefix_partitions(program, expected["capacity"])
            schedule = schedule_small_width_partition_reference(program, layout)
            assert {
                "capacity": schedule.capacity,
                "loads": schedule.loads,
                "partitions": len(layout.partitions),
                "stores": schedule.stores,
            } == expected
            replay = replay_partition_schedule(program, layout, schedule)
            assert (replay.loads, replay.stores) == (
                expected["loads"],
                expected["stores"],
            )


@pytest.mark.parametrize("width", (2, 3, 4))
def test_fixed_order_belady_reproduces_registered_scaling_laws(width: int) -> None:
    program = _program(width)
    expected = {
        width + 1: 4 * width - 2,
        2 * width: 3 * width - 1,
        3 * width - 1: 2 * width,
    }
    for capacity, transfer_count in expected.items():
        schedule = schedule_fixed_order_belady(program, capacity)
        assert schedule.loads == transfer_count
        assert schedule.stores == transfer_count
        assert replay_fixed_order_schedule(program, schedule).objective_cost == (
            2 * transfer_count
        )


def test_replay_rejects_a_free_copy_and_a_changed_partition_event() -> None:
    program = _program(2)
    fixed = schedule_fixed_order_belady(program, 3)
    first_load = next(
        index
        for index, action in enumerate(fixed.actions)
        if action.kind is TransferKind.LOAD
    )
    duplicate_actions = (
        *fixed.actions[: first_load + 1],
        fixed.actions[first_load],
        *fixed.actions[first_load + 1 :],
    )
    with pytest.raises(MemoryIoError):
        replay_fixed_order_schedule(
            program,
            replace(
                fixed,
                actions=duplicate_actions,
                loads=fixed.loads + 1,
                objective_cost=fixed.objective_cost + fixed.load_cost,
            ),
        )

    layout = build_maximal_prefix_partitions(program, 3)
    partition = schedule_small_width_partition_reference(program, layout)
    spill_index = next(
        index
        for index, action in enumerate(partition.actions)
        if action.reason is TransferReason.PARTITION_BOUNDARY_SPILL
    )
    changed = replace(
        partition.actions[spill_index],
        reason=TransferReason.BASELINE_INTERFACE_TRANSFER,
    )
    corrupted = replace(
        partition,
        actions=(
            *partition.actions[:spill_index],
            changed,
            *partition.actions[spill_index + 1 :],
        ),
    )
    with pytest.raises(MemoryIoError):
        validate_partition_schedule(program, layout, corrupted)


def test_large_width_exact_partition_reference_fails_closed() -> None:
    program = _program(4)
    falsified_width = replace(program, width=8)
    layout = build_maximal_prefix_partitions(falsified_width, 9)
    with pytest.raises(MemoryIoError, match="outside exact reference scope"):
        schedule_small_width_partition_reference(falsified_width, layout)


def test_fixed_order_validator_rejects_capacity_or_action_mutation() -> None:
    program = _program(3)
    schedule = schedule_fixed_order_belady(program, 4)
    with pytest.raises(MemoryIoError):
        validate_fixed_order_schedule(program, replace(schedule, loads=0))
