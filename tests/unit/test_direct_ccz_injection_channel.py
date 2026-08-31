from __future__ import annotations

import pytest

from ecdlp_ftqc.verification import (
    direct_ccz_branch_correction,
    verify_direct_ccz_injection_channel,
)


def test_figure14_correction_truth_table_terms() -> None:
    branch = direct_ccz_branch_correction((1, 0, 1), (1, 1, 0))

    assert branch.conditional_cz_exponents == (1, 0, 1)
    assert branch.pauli_exponents == (1, 0, 0)


def test_all_64_measurement_branches_match_ideal_ccx() -> None:
    result = verify_direct_ccz_injection_channel()

    assert result.branch_count == 64
    assert result.nonzero_branch_count == 64
    assert result.minimum_branch_probability == pytest.approx(1 / 64)
    assert result.maximum_branch_probability == pytest.approx(1 / 64)
    assert result.maximum_probability_error < 1e-14
    assert result.maximum_operator_frobenius_error < 1e-14
    assert result.all_passed
