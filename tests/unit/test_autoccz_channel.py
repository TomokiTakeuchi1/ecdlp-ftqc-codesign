from __future__ import annotations

from ecdlp_ftqc.verification import (
    AUTOCCZ_DELAYED_CHOICE_CZ_COUNT,
    AUTOCCZ_ROUTING_QUBIT_COUNT,
    verify_autoccz_consumption_channel,
)


def test_autoccz_consumption_matches_ideal_ccx_on_all_branches() -> None:
    result = verify_autoccz_consumption_channel()

    assert result.all_passed
    assert result.branch_count == 64
    assert result.nonzero_branch_count == 64
    assert result.expected_branch_probability == 1 / 64
    assert result.maximum_probability_error <= result.tolerance
    assert result.maximum_operator_frobenius_error <= result.tolerance


def test_autoccz_delayed_choice_resource_contract_is_explicit() -> None:
    result = verify_autoccz_consumption_channel()

    assert AUTOCCZ_DELAYED_CHOICE_CZ_COUNT == 3
    assert AUTOCCZ_ROUTING_QUBIT_COUNT == 6
    assert result.delayed_choice_cz_count == 3
    assert result.routing_qubit_count == 6
    assert result.delayed_choice_truth_table_passed
    assert "source-proved CZ/identity carrier" in result.source_contract
