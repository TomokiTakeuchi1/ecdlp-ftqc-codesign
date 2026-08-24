from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import build_bridge_ripple_trace
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    BRIDGE_SCHEDULE_POLICY,
    NORMALIZED_SENSITIVITY_UNIT,
    BridgeScheduleError,
    UnsupportedBridgeTimingError,
    dumps_bridge_schedule,
    load_bridge_timing_config,
    schedule_bridge_ripple,
    validate_bridge_schedule,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    REPOSITORY_ROOT
    / "configs"
    / "architectures"
    / "bridge_ripple_sensitivity_v1.yaml"
)


def test_configuration_is_explicitly_normalized_and_check() -> None:
    config = load_bridge_timing_config(CONFIG_PATH)

    assert config.time_unit == NORMALIZED_SENSITIVITY_UNIT
    assert config.policy == BRIDGE_SCHEDULE_POLICY
    assert config.high_rate_xx_batch_size == 10
    assert config.bell_measurement_lanes == 1
    assert config.timing_evidence_status is EvidenceStatus.CHECK


def test_strict_mode_rejects_unpinned_bridge_timing() -> None:
    trace = build_bridge_ripple_trace(4)
    config = load_bridge_timing_config(CONFIG_PATH)

    with pytest.raises(UnsupportedBridgeTimingError, match="CHECK"):
        schedule_bridge_ripple(trace, config)


@pytest.mark.parametrize(
    ("width", "batch_count", "operation_count"),
    [(10, 0, 0), (11, 1, 10), (21, 2, 20), (32, 3, 30)],
)
def test_exact_ten_xx_boundary_is_workload_visible(
    width: int, batch_count: int, operation_count: int
) -> None:
    trace = build_bridge_ripple_trace(width)
    config = load_bridge_timing_config(CONFIG_PATH)

    schedule = schedule_bridge_ripple(
        trace, config, allow_check_assumptions=True, high_rate_enabled=True
    )

    assert schedule.eligible_xx_measurements == width - 1
    assert schedule.high_rate_batch_count == batch_count
    assert schedule.high_rate_operation_count == operation_count
    assert schedule.replay_summary.all_bridges_rebound


def test_high_rate_reduces_one_lane_width32_sensitivity() -> None:
    trace = build_bridge_ripple_trace(32)
    config = load_bridge_timing_config(CONFIG_PATH)

    disabled = schedule_bridge_ripple(
        trace, config, allow_check_assumptions=True, high_rate_enabled=False
    )
    enabled = schedule_bridge_ripple(
        trace, config, allow_check_assumptions=True, high_rate_enabled=True
    )

    assert enabled.scheduled_steps < disabled.scheduled_steps
    assert disabled.high_rate_batch_count == 0
    assert enabled.high_rate_batch_count == 3
    # Reserving the batch lets the independent bridge-0 ZZ component use the
    # early lane slot. Three batches then replace 30 singleton XX steps with
    # 3 batch steps, retaining all 27 raw saved steps in this one-lane case.
    assert disabled.scheduled_steps - enabled.scheduled_steps == 27
    assert enabled.strict_executable is False


def test_more_bell_lanes_do_not_increase_sensitivity_makespan() -> None:
    trace = build_bridge_ripple_trace(32)
    config = load_bridge_timing_config(CONFIG_PATH)
    makespans = []
    for lane_count in (1, 2, 4, 8, 10):
        schedule = schedule_bridge_ripple(
            trace,
            replace(config, bell_measurement_lanes=lane_count),
            allow_check_assumptions=True,
            high_rate_enabled=True,
        )
        makespans.append(schedule.scheduled_steps)

    assert makespans == sorted(makespans, reverse=True)


def test_resource_state_demand_is_a_burst_not_only_a_total() -> None:
    trace = build_bridge_ripple_trace(32)
    config = load_bridge_timing_config(CONFIG_PATH)
    schedule = schedule_bridge_ripple(
        trace, config, allow_check_assumptions=True
    )

    assert schedule.total_resource_state_demand == 31
    assert schedule.peak_resource_state_demand_per_step == 30
    assert schedule.source_logical_carrier_slots == 160
    assert schedule.encoded_patch_family_count == 5
    assert schedule.reactive_ancilla_patch_count == 6


def test_validator_rejects_malformed_exact_ten_batch() -> None:
    trace = build_bridge_ripple_trace(11)
    config = load_bridge_timing_config(CONFIG_PATH)
    schedule = schedule_bridge_ripple(
        trace, config, allow_check_assumptions=True
    )
    batch_index = next(
        index
        for index, event in enumerate(schedule.events)
        if event.implementation == "high_rate_xx_10"
    )
    events = list(schedule.events)
    events[batch_index] = replace(
        events[batch_index],
        source_event_ids=events[batch_index].source_event_ids[:-1],
    )
    malformed = replace(schedule, events=tuple(events))

    with pytest.raises(BridgeScheduleError, match="cover every source event"):
        validate_bridge_schedule(trace, config, malformed)


def test_serialization_is_deterministic_and_qualified() -> None:
    trace = build_bridge_ripple_trace(11)
    config = load_bridge_timing_config(CONFIG_PATH)
    schedule = schedule_bridge_ripple(
        trace, config, allow_check_assumptions=True
    )

    first = dumps_bridge_schedule(schedule)
    second = dumps_bridge_schedule(schedule)
    data = json.loads(first)

    assert first == second
    assert data["time_unit"] == NORMALIZED_SENSITIVITY_UNIT
    assert data["timing_evidence_status"] == "CHECK"
    assert data["strict_executable"] is False
    assert data["high_rate_batch_count"] == 1
