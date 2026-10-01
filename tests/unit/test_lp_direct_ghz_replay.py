from __future__ import annotations

import json
from pathlib import Path

import pytest

from ecdlp_ftqc.verification.lp_direct_ghz import (
    audit_projection_recovery,
    dense_direct_ghz_audit,
    projection_recovery,
)


def test_all_direct_branches_and_residual_factorization() -> None:
    result = dense_direct_ghz_audit()
    assert result["nonzero_branches"] == 16
    assert result["total_probability"] == pytest.approx(1)
    assert result["branch_probability"] == pytest.approx(1 / 16)
    assert result["pre_and_post_automorphism_frame_max_residual"] < 1e-12
    assert result["canonical_reduced_purity_minimum"] == pytest.approx(1)
    assert result["all_checks_passed"]
    assert not result["physical_fault_tolerance_certified"]
    assert not result["outcome_postselection"]
    assert json.loads(json.dumps(result)) == result


def test_negative_controls_discriminate_frame_and_direction() -> None:
    result = dense_direct_ghz_audit()
    assert result["omitted_canonical_frame_mean_ghz_fidelity"] == pytest.approx(1 / 8)
    assert result["untransformed_output_frame_mean_ghz_fidelity"] == pytest.approx(1 / 2)
    assert result["wrong_auto_mean_ghz_fidelity"] == pytest.approx(1 / 4)
    assert result["reversed_matching_nonzero_branches"] == 1


def test_replay_does_not_import_construction() -> None:
    source = Path("src/ecdlp_ftqc/verification/lp_direct_ghz.py").read_text(encoding="utf-8")
    assert "from ecdlp_ftqc" not in source
    assert "import ecdlp_ftqc" not in source


def test_projection_sign_recovery_covers_all_allowed_redundant_syndromes() -> None:
    rows = (0b011, 0b110, 0b101, 0)
    recovery = projection_recovery(rows, 3)
    syndromes = {sum(((r & v).bit_count() % 2) << i for i, r in enumerate(rows))
                 for v in range(8)}
    for outcome in range(16):
        if outcome in syndromes:
            support = recovery.recover(outcome)
            actual = sum(((r & support).bit_count() % 2) << i for i, r in enumerate(rows))
            assert actual == outcome
        else:
            with pytest.raises(ValueError, match="Inconsistent"):
                recovery.recover(outcome)
    assert recovery.recover(0) == 0
    report = audit_projection_recovery(rows, rows, 3, 3)
    assert report["maps"]["Q_Z_projection"]["independent_ideal_sign_bits"] == 2
    assert report["maps"]["M_X_projection"]["physical_correction_axis"] == "Z"
    assert not report["noisy_decoder"]


@pytest.mark.parametrize("rows,n", [((-1,), 3), ((8,), 3), ((True,), 3), ((1,), True)])
def test_projection_invalid_inputs_fail_closed(rows: tuple[int, ...], n: int) -> None:
    with pytest.raises(ValueError):
        projection_recovery(rows, n)


@pytest.mark.parametrize("outcome", [-1, 2, True, 0.5])
def test_projection_invalid_outcome_fails_closed(outcome: int) -> None:
    with pytest.raises(ValueError):
        projection_recovery((1,), 1).recover(outcome)
