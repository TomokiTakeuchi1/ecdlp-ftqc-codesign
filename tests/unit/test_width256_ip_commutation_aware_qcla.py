from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_qcla_trace
from ecdlp_ftqc.compiler import DirectCczEventTrace, lower_qcla_to_direct_ccz_events
from ecdlp_ftqc.scheduler import (
    build_width256_ip_commutation_aware_study,
    width256_ip_commutation_aware_study_to_data,
)
from ecdlp_ftqc.verification import (
    Width256IpCommutationAwareReplayError,
    replay_width256_ip_commutation_aware_study,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)


@pytest.fixture(scope="module")
def study_data() -> tuple[dict[str, object], DirectCczEventTrace]:
    trace = build_qcla_trace(256)
    capability = load_direct_ccz_capability(CAPABILITY)
    events = lower_qcla_to_direct_ccz_events(trace, capability)
    study = build_width256_ip_commutation_aware_study(events)
    return width256_ip_commutation_aware_study_to_data(study), events


def test_width256_ip_exact_schedule_and_pair_headlines(
    study_data: tuple[dict[str, object], DirectCczEventTrace],
) -> None:
    raw, events = study_data
    replay = replay_width256_ip_commutation_aware_study(raw, events)
    assert replay.all_passed
    assert replay.full_pair_count_checked == 3_019_653
    assert replay.macro_depth == 30
    assert replay.candidate_levels == 60
    assert replay.candidate_support_profiles_recomputed == 14_748
    assert replay.coherent_cleanup_ccx_count == 1_229
    assert replay.small_width_basis_rows_checked == 87_376

    assert raw["compact_bridge_widths_2_to_8"] == [
        [2, 2, 2],
        [3, 4, 4],
        [4, 6, 6],
        [5, 12, 8],
        [6, 12, 8],
        [7, 14, 10],
        [8, 14, 10],
    ]
    assert raw["macro_layers"] and [
        len(layer) for layer in raw["macro_layers"]  # type: ignore[union-attr]
    ] == [
        255,
        253,
        126,
        64,
        34,
        23,
        20,
        28,
        40,
        61,
        66,
        72,
        53,
        70,
        64,
        253,
        126,
        64,
        34,
        23,
        20,
        28,
        40,
        61,
        66,
        72,
        53,
        70,
        64,
        255,
    ]
    oracle = raw["pair_oracle"]
    assert isinstance(oracle, dict)
    assert oracle["dependency_pair_count"] == 2_012_691
    assert oracle["admitted_pair_count"] == 1_006_962
    assert oracle["noncommuting_pair_count"] == 12_996
    assert oracle["barrier_pair_count"] == 2_007_181


def test_width256_ip_support_and_resource_envelopes_are_qualified(
    study_data: tuple[dict[str, object], DirectCczEventTrace],
) -> None:
    raw, _ = study_data
    levels = raw["candidate_levels"]
    assert isinstance(levels, list)
    assert max(item["direct_ccz_event_count"] for item in levels) == 255
    assert max(item["distinct_target_h_count"] for item in levels) == 255
    assert max(item["maximum_ppm_weight_upper_bound"] for item in levels) == 1_006
    assert max(item["maximum_sampled_branch_weight"] for item in levels) == 509
    assert max(item["may_support_union_upper_bound_size"] for item in levels) == 1_770
    assert max(
        item["witnessed_support_union_lower_bound_size"] for item in levels
    ) == 1_770
    assert max(item["maximum_may_contact_count"] for item in levels) == 634
    assert max(item["maximum_witnessed_contact_count"] for item in levels) == 633
    assert sum(item["unwitnessed_may_incidence_count"] for item in levels) == 118_038
    assert any(item["possible_support_exact"] is False for item in levels)
    assert all(item["may_union_is_simultaneous_branch_weight"] is False for item in levels)
    assert raw["support_envelope_status"] == "CHECK"
    assert raw["peak_fresh_ccz_resource_count"] == 255
    assert raw["peak_distinct_target_h_count"] == 255
    assert raw["total_target_h_count"] == 4_916

    live = raw["live_ancillas"]
    assert isinstance(live, dict)
    assert live["source_ancilla_values"] == 495
    assert live["peak_live_source_ancillas"] == 495
    assert live["fully_resident_source_values"] == 1_007
    assert live["coordinate"] == "source_algorithmic_layer_liveness_not_macro_schedule"


@pytest.mark.parametrize("mutation", ["rank", "support", "native"])
def test_width256_ip_replay_rejects_mutations(
    study_data: tuple[dict[str, object], DirectCczEventTrace], mutation: str
) -> None:
    raw, events = study_data
    changed = deepcopy(raw)
    if mutation == "rank":
        nodes = changed["dependency_nodes"]
        assert isinstance(nodes, list)
        nodes[-1]["macro_rank"] += 1
    elif mutation == "support":
        levels = changed["candidate_levels"]
        assert isinstance(levels, list)
        levels[0]["maximum_sampled_branch_weight"] += 1
    else:
        changed["native_cycles"] = 1
    with pytest.raises(Width256IpCommutationAwareReplayError):
        replay_width256_ip_commutation_aware_study(changed, events)
