from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.compiler import (
    DirectCczEventTrace,
    lower_oop_qcla_to_direct_ccz_events,
    lower_qcla_to_direct_ccz_events,
)
from ecdlp_ftqc.scheduler import (
    build_width256_commutation_aware_study,
    build_width256_ip_commutation_aware_study,
    build_width256_oop_ip_branch_weight_study,
    width256_oop_ip_branch_weight_study_to_data,
)
from ecdlp_ftqc.verification import (
    Width256BranchWeightReplayError,
    replay_width256_oop_ip_branch_weight_study,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)


@pytest.fixture(scope="module")
def study_inputs() -> tuple[
    dict[str, Any], object, DirectCczEventTrace, object, DirectCczEventTrace
]:
    capability = load_direct_ccz_capability(CAPABILITY)
    oop_source = build_oop_qcla_trace(256)
    oop_events = lower_oop_qcla_to_direct_ccz_events(oop_source, capability)
    oop_reviewed = build_width256_commutation_aware_study(oop_events)
    ip_source = build_qcla_trace(256)
    ip_events = lower_qcla_to_direct_ccz_events(ip_source, capability)
    ip_reviewed = build_width256_ip_commutation_aware_study(ip_events)
    study = build_width256_oop_ip_branch_weight_study(
        oop_source=oop_source,
        oop_events=oop_events,
        oop_study=oop_reviewed,
        ip_source=ip_source,
        ip_events=ip_events,
        ip_study=ip_reviewed,
    )
    return (
        width256_oop_ip_branch_weight_study_to_data(study),
        oop_source,
        oop_events,
        ip_source,
        ip_events,
    )


def test_shared_protocol_and_independent_scalar_replay(
    study_inputs: tuple[
        dict[str, Any], object, DirectCczEventTrace, object, DirectCczEventTrace
    ],
) -> None:
    raw, oop_source, oop_events, ip_source, ip_events = study_inputs
    replay = replay_width256_oop_ip_branch_weight_study(
        raw,
        oop_source=oop_source,  # type: ignore[arg-type]
        oop_events=oop_events,
        ip_source=ip_source,  # type: ignore[arg-type]
        ip_events=ip_events,
    )
    assert replay.all_passed
    assert replay.total_sampled_level_values_checked == 46_080
    assert replay.total_evaluated_branch_ppm_instances_checked == 11_326_464
    assert replay.non_null_native_output_count == 0

    oop = raw["oop"]
    ip = raw["ip"]
    assert isinstance(oop, dict) and isinstance(ip, dict)
    assert oop["candidate_level_count"] == 30
    assert ip["candidate_level_count"] == 60
    assert oop["evaluated_branch_ppm_instance_count"] == 3_775_488
    assert ip["evaluated_branch_ppm_instance_count"] == 7_550_976
    assert oop["sample_seed"] == ip["sample_seed"]
    assert oop["sample_count"] == ip["sample_count"] == 512


@pytest.mark.parametrize("variant", ["oop", "ip"])
def test_sampled_distributions_are_qualified_and_bounded(
    study_inputs: tuple[
        dict[str, Any], object, DirectCczEventTrace, object, DirectCczEventTrace
    ],
    variant: str,
) -> None:
    raw = study_inputs[0]
    variant_data = raw[variant]
    assert isinstance(variant_data, dict)
    levels = variant_data["levels"]
    assert isinstance(levels, list)
    for level in levels:
        assert level["minimum"] <= level["p50"]
        assert level["p50"] <= level["p95"]
        assert level["p95"] <= level["p99"]
        assert level["p99"] <= level["sampled_maximum"]
        assert level["forced_all_zero_weight"] == level[
            "branch_maximum_weights"
        ][0]
        assert level["forced_all_one_weight"] == level[
            "branch_maximum_weights"
        ][1]
        assert level["hashed_branch_maximum"] == max(
            level["branch_maximum_weights"][2:]
        )
        assert level["hashed_branch_sample_count"] == 510
        assert (
            level["sampled_maximum"]
            <= level["support_weight_upper_bound"]
        )
        if level["axis"] == "X":
            assert set(level["branch_maximum_weights"]) == {1}
            assert level["sampled_maximum_is_true_maximum"] is True
            assert level["evidence_status"] == "PROVED"
        else:
            assert level["sampled_maximum_is_true_maximum"] is False
            assert level["evidence_status"] == "NUMERICAL"
    assert raw["sampled_maximum_is_global_true_maximum"] is False
    assert raw["native_cycles"] is None
    assert raw["runtime_seconds"] is None
    assert raw["physical_qubits"] is None
    assert raw["failure_probability"] is None


@pytest.mark.parametrize("mutation", ["vector", "quantile", "native"])
def test_independent_replay_rejects_mutations(
    study_inputs: tuple[
        dict[str, Any], object, DirectCczEventTrace, object, DirectCczEventTrace
    ],
    mutation: str,
) -> None:
    raw, oop_source, oop_events, ip_source, ip_events = study_inputs
    changed = deepcopy(raw)
    if mutation == "native":
        changed["native_cycles"] = 1
    else:
        oop = changed["oop"]
        assert isinstance(oop, dict)
        levels = oop["levels"]
        assert isinstance(levels, list)
        if mutation == "vector":
            levels[0]["branch_maximum_weights"][0] += 1
        else:
            levels[0]["p95"] += 1
    with pytest.raises(Width256BranchWeightReplayError):
        replay_width256_oop_ip_branch_weight_study(
            changed,
            oop_source=oop_source,  # type: ignore[arg-type]
            oop_events=oop_events,
            ip_source=ip_source,  # type: ignore[arg-type]
            ip_events=ip_events,
        )
