from __future__ import annotations

import json
from pathlib import Path

import pytest

from ecdlp_ftqc.verification.lp_flag_preparation import dense_uniform_preparation_audit


@pytest.mark.parametrize("axis", ["Z", "X"])
def test_dense_uniform_preparation_all_valid_branches(axis: str) -> None:
    result = dense_uniform_preparation_audit()
    report = result["axis_reports"][axis]
    assert report["no_fault_valid_branches"] == 4
    assert report["no_fault_total_probability"] == pytest.approx(1)
    assert report["no_fault_acceptance_probability"] == pytest.approx(1)
    assert report["no_fault_branch_probabilities"] == pytest.approx([0.25] * 4)
    assert report["no_fault_target_fidelity_minimum"] == pytest.approx(1)
    assert result["all_checks_passed"]
    assert not result["full_LP_certificate_from_this_replay_alone"]
    assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize("axis", ["Z", "X"])
def test_dense_uniform_preparation_all_declared_single_faults(axis: str) -> None:
    report = dense_uniform_preparation_audit()["axis_reports"][axis]
    assert report["declared_single_fault_events"] == 828
    assert report["event_categories"] == {
        "initial": 12, "final_idle": 12, "prep": 36,
        "readout": 12, "gate": 420, "idle": 336,
    }
    assert report["events_with_accepted_branches"] + report["fully_rejected_events"] == 828
    assert report["accepted_fault_branches"] > 0
    assert report["bad_accepted_branches"] == 0
    assert report["accepted_one_pauli_orbit_max_infidelity"] < 1e-12
    assert report["max_total_probability_error"] < 1e-12


@pytest.mark.parametrize("axis", ["Z", "X"])
def test_dense_flag_and_repeat_negative_controls(axis: str) -> None:
    report = dense_uniform_preparation_audit()["axis_reports"][axis]
    assert report["weight_two_hook_flagged_and_rejected"]
    assert report["drop_flags_negative_control_accepted_branches"] == 4
    assert report["drop_flags_negative_control_best_orbit_fidelity"] < 1e-12
    assert report["one_pass_readout_negative_control_accepted_branches"] == 4
    assert report["one_pass_readout_negative_control_best_orbit_fidelity"] < 1e-12


def test_dense_replay_is_independent_of_analysis_and_construction() -> None:
    source = Path("src/ecdlp_ftqc/verification/lp_flag_preparation.py").read_text(encoding="utf-8")
    assert "from ecdlp_ftqc" not in source
    assert "import ecdlp_ftqc" not in source
