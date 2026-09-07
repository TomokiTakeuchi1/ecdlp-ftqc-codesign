from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_oop_qcla_trace
from ecdlp_ftqc.compiler import lower_oop_qcla_to_direct_ccz_events
from ecdlp_ftqc.scheduler import (
    build_width256_commutation_aware_study,
    width256_commutation_aware_study_to_data,
)
from ecdlp_ftqc.verification import (
    Width256CommutationAwareReplayError,
    replay_width256_commutation_aware_study,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)


@pytest.fixture(scope="module")
def study_data() -> tuple[dict[str, object], object]:
    trace = build_oop_qcla_trace(256)
    capability = load_direct_ccz_capability(CAPABILITY)
    events = lower_oop_qcla_to_direct_ccz_events(trace, capability)
    study = build_width256_commutation_aware_study(events)
    return width256_commutation_aware_study_to_data(study), events


def test_width256_unitary_schedule_and_support_headlines(
    study_data: tuple[dict[str, object], object],
) -> None:
    raw, events = study_data
    replay = replay_width256_commutation_aware_study(raw, events)  # type: ignore[arg-type]
    assert replay.all_passed
    assert replay.full_pair_count_checked == 754_606
    assert replay.unitary_macro_depth == 15
    assert replay.unitary_candidate_levels == 30
    assert replay.candidate_support_profiles_recomputed == 7_374

    unitary = raw["unitary"]
    assert isinstance(unitary, dict)
    oracle = unitary["pair_oracle"]
    assert isinstance(oracle, dict)
    assert oracle["dependency_pair_count"] == 251_125
    assert oracle["admitted_pair_count"] == 503_481
    assert oracle["noncommuting_pair_count"] == 3_249
    levels = unitary["candidate_levels"]
    assert isinstance(levels, list)
    assert max(item["direct_ccz_event_count"] for item in levels) == 255
    assert max(item["unique_target_h_count"] for item in levels) == 255
    assert max(item["maximum_ppm_weight_upper_bound"] for item in levels) == 1_003
    assert max(item["maximum_possible_contact_count"] for item in levels) == 54
    assert max(item["possible_support_union_size"] for item in levels) == 1_647
    live = unitary["live_values"]
    assert isinstance(live, dict)
    assert live["fully_resident_source_values"] == 1_008
    assert live["peak_live_source_values"] == 1_004
    assert raw["source_cnot_layer_demands"] == [[2, 254], [19, 256], [20, 256]]


def test_width256_cleanup_fails_closed_on_mixed_axis(
    study_data: tuple[dict[str, object], object],
) -> None:
    raw, _ = study_data
    measured = raw["measured_cleanup"]
    assert isinstance(measured, dict)
    assert measured["proposed_cleanup_count"] == 240
    assert measured["removed_cleanup_ccx_count"] == 0
    assert measured["cleanup_axis_safe"] is False
    assert measured["fallback_variant"] == "commutation_aware_unitary"
    cleanups = measured["cleanup_certificates"]
    assert isinstance(cleanups, list)
    assert max(item["later_ppm_count"] for item in cleanups) == 236
    assert all(item["axis_witness"]["mixed_axis"] for item in cleanups)
    assert all(
        item["released_target_later_ppm_use_count"] == 0 for item in cleanups
    )


@pytest.mark.parametrize("mutation", ["rank", "cleanup_axis", "native"])
def test_width256_replay_rejects_mutations(
    study_data: tuple[dict[str, object], object], mutation: str
) -> None:
    raw, events = study_data
    changed = deepcopy(raw)
    unitary = changed["unitary"]
    measured = changed["measured_cleanup"]
    assert isinstance(unitary, dict)
    assert isinstance(measured, dict)
    if mutation == "rank":
        nodes = unitary["dependency_nodes"]
        assert isinstance(nodes, list)
        nodes[-1]["macro_rank"] += 1
    elif mutation == "cleanup_axis":
        cleanups = measured["cleanup_certificates"]
        assert isinstance(cleanups, list)
        cleanups[0]["admitted_to_z_x_only_high_rate_ppm"] = True
    else:
        unitary["native_cycles"] = 1
    with pytest.raises(Width256CommutationAwareReplayError):
        replay_width256_commutation_aware_study(changed, events)  # type: ignore[arg-type]
