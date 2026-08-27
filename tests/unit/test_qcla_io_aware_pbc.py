from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import build_qcla_trace
from ecdlp_ftqc.codes import load_pbc_mitten_backend_config
from ecdlp_ftqc.io import (
    MemoryIoError,
    QclaMemoryValueOrigin,
    replay_qcla_fixed_order_schedule,
    schedule_qcla_fixed_order_belady,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    UnsupportedQclaMemoryIoScheduleError,
    load_memory_io_timing_config,
    schedule_qcla_io_aware_pbc,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONFIG = REPOSITORY_ROOT / "configs" / "codes" / "mitten_j300_pbc_v2.yaml"
IO_CONFIG = REPOSITORY_ROOT / "configs" / "architectures" / "j300_memory_io_v1.yaml"


def _backend():
    return load_pbc_mitten_backend_config(BACKEND_CONFIG)


def _io():
    return load_memory_io_timing_config(IO_CONFIG)


def _schedule(width: int, *, scratch: int = 1, high_rate: bool = False):
    return schedule_qcla_io_aware_pbc(
        build_qcla_trace(width),
        _backend(),
        _io(),
        scratch_slot_count=scratch,
        enable_high_rate=high_rate,
        allow_check_assumptions=True,
    )


def test_qcla_origin_overlay_separates_data_and_clean_ancilla_epochs() -> None:
    result = _schedule(4)
    values = result.memory_program.values
    input_output = {
        value.value_id
        for value in values
        if value.origin is QclaMemoryValueOrigin.MEMORY_INPUT_OR_INOUT
    }
    clean_epochs = {
        value.value_id
        for value in values
        if value.origin is QclaMemoryValueOrigin.CLEAN_ANCILLA_EPOCH
    }

    assert input_output == {
        "a:0",
        "a:1",
        "a:2",
        "a:3",
        "b:0",
        "b:1",
        "b:2",
        "b:3",
    }
    assert clean_epochs
    assert all("#epoch:" in value_id for value_id in clean_epochs)
    assert result.placement.compulsory_input_loads == 8
    assert result.placement.final_output_stores == 8
    assert result.placement.clean_ancilla_creations == len(clean_epochs)


def test_tight_fixed_order_placement_spills_reloads_and_replays_independently() -> None:
    result = _schedule(4)
    first = schedule_qcla_fixed_order_belady(
        result.memory_program, source_logical_capacity=2
    )
    second = schedule_qcla_fixed_order_belady(
        result.memory_program, source_logical_capacity=2
    )
    replay = replay_qcla_fixed_order_schedule(result.memory_program, first)

    assert first == second
    assert first.reloads > 0
    assert first.eviction_stores > 0
    assert first.peak_source_logical_occupancy == 2
    assert replay.compulsory_input_loads == 8
    assert replay.final_processor_values == ()
    assert len(replay.final_memory_inputs_outputs) == 8
    assert len(replay.final_released_clean_ancillas) == first.clean_ancilla_creations


def test_independent_replay_rejects_a_free_duplicate_load() -> None:
    result = _schedule(4)
    placement = result.placement
    first_load = next(action for action in placement.actions if action.kind.value == "load")
    corrupted = replace(
        placement,
        actions=(first_load, *placement.actions),
        compulsory_input_loads=placement.compulsory_input_loads + 1,
    )

    with pytest.raises(MemoryIoError, match="free copies"):
        replay_qcla_fixed_order_schedule(result.memory_program, corrupted)


def test_zero_round_transfers_preserve_every_base_event_start() -> None:
    zero_io = replace(
        _io(),
        configuration_id="qcla-zero-round-regression",
        load_rounds=0,
        store_rounds=0,
        timing_evidence_status=EvidenceStatus.PROVED,
    )
    result = schedule_qcla_io_aware_pbc(
        build_qcla_trace(4),
        _backend(),
        zero_io,
        scratch_slot_count=1,
        enable_high_rate=False,
        allow_check_assumptions=True,
    )

    assert result.scheduled_rounds == result.base_scheduled_rounds
    assert [event.start_round for event in result.compute_events] == [
        event.start_round for event in result.base_schedule.events
    ]
    assert result.transfer_action_rounds == 0


def test_one_lane_one_round_adds_exact_serial_transfer_duration() -> None:
    result = _schedule(4)

    assert result.added_rounds == result.placement.loads + result.placement.stores
    assert result.transfer_action_rounds == result.added_rounds
    assert result.total_resource_state_demand == 70
    assert result.total_resource_state_demand == sum(
        point.demand for point in result.resource_state_demand
    )
    assert tuple(point.start_round for point in result.resource_state_demand) == tuple(
        sorted(point.start_round for point in result.resource_state_demand)
    )


def test_width17_is_realized_with_total_capacity_sixty() -> None:
    result = _schedule(17)

    assert result.ordering_capacity > result.total_logical_capacity
    assert result.source_logical_capacity == 59
    assert result.placement.peak_source_logical_occupancy <= 59
    assert result.placement.reloads > 0
    assert result.placement.compulsory_input_loads == 34
    assert result.placement.final_output_stores == 34


def test_ten_scratch_high_rate_uses_fifty_source_slots() -> None:
    result = _schedule(15, scratch=10, high_rate=True)

    assert result.source_logical_capacity == 50
    assert result.placement.peak_source_logical_occupancy <= 50
    assert result.high_rate_batch_count > 0
    assert result.base_schedule.high_rate_operation_count == 10 * result.high_rate_batch_count


def test_strict_mode_rejects_check_transfer_timing() -> None:
    with pytest.raises(
        UnsupportedQclaMemoryIoScheduleError, match="CHECK transfer durations"
    ):
        schedule_qcla_io_aware_pbc(
            build_qcla_trace(4),
            _backend(),
            _io(),
            scratch_slot_count=1,
            enable_high_rate=False,
        )


def test_strict_mode_also_rejects_clean_lifecycle_with_proved_transfers() -> None:
    proved_io = replace(
        _io(),
        configuration_id="qcla-proved-transfer-regression",
        timing_evidence_status=EvidenceStatus.PROVED,
    )

    with pytest.raises(
        UnsupportedQclaMemoryIoScheduleError, match="CHECK clean-ancilla"
    ):
        schedule_qcla_io_aware_pbc(
            build_qcla_trace(4),
            _backend(),
            proved_io,
            scratch_slot_count=1,
            enable_high_rate=False,
        )
