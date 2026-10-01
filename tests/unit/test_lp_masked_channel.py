from __future__ import annotations

import json
from typing import Any

import numpy as np
import pytest

from ecdlp_ftqc.verification import lp_masked_channel
from ecdlp_ftqc.verification.lp_masked_channel import (
    MaskedChannelError,
    dense_masked_channel_audit,
)


@pytest.fixture(scope="module")
def audit() -> dict[str, Any]:
    return dense_masked_channel_audit()


def test_masked_channel_checks_every_signed_branch(audit: dict[str, Any]) -> None:
    assert audit["all_checks_passed"]
    assert audit["retained_mask_outcomes"] == 8
    assert audit["retained_auxiliary_x_outcomes_per_mask"] == 16
    assert audit["kraus_operator_count"] == 128
    assert audit["mask_outcome_probability_min"] == pytest.approx(1 / 8)
    assert audit["mask_outcome_probability_max"] == pytest.approx(1 / 8)
    assert audit["zero_input_branch_probability_min"] == pytest.approx(1 / 128)
    assert audit["zero_input_branch_probability_max"] == pytest.approx(1 / 128)
    assert audit["zero_input_total_probability"] == pytest.approx(1)
    assert audit["measurement_outcome_postselection_required"] is False
    assert audit["arbitrary_input_branch_probabilities_uniform"] is False


def test_operator_identity_preserves_unwanted_data_coherence(audit: dict[str, Any]) -> None:
    assert audit["corrected_kraus_maximum_residual"] == 0
    assert audit["trace_preservation_maximum_residual"] == 0
    assert audit["coarse_grained_x4_instrument_weights"] == [1.0, 1.0]
    assert audit["uncoupled_data_logicals_preserved_by_measurement"] == [1, 2, 3]
    assert audit["spectator_bell_fidelity_minimum"] == pytest.approx(1)
    assert audit["corrected_ghz_fidelity_minimum"] == pytest.approx(1)


def test_both_mask_frame_and_measurement_sign_are_required(audit: dict[str, Any]) -> None:
    assert audit["missing_propagated_mask_x_frame_mean_ghz_fidelity"] == pytest.approx(1 / 8)
    assert audit["missing_x4_sign_frame_mean_ghz_fidelity"] == pytest.approx(1 / 2)


def test_reversed_mask_cnot_is_not_a_valid_substitute(audit: dict[str, Any]) -> None:
    reverse = audit["reversed_mask_cnot"]
    assert reverse["nonzero_zero_input_branches"] == 16
    assert reverse["zero_input_total_probability"] == pytest.approx(1)
    assert reverse["desired_kraus_maximum_residual"] > 0.01
    assert reverse["measures_all_four_data_xs"] is True
    assert reverse["corrected_ghz_fidelity_minimum"] == pytest.approx(1 / 8)
    assert reverse["corrected_ghz_fidelity_maximum"] == pytest.approx(1 / 8)


def test_eigenstate_inputs_need_not_have_all_branches_nonzero() -> None:
    preparation = lp_masked_channel._mask_preparation()
    plus_four = np.zeros(16, dtype=np.complex128)
    plus_four[[0, 8]] = 1 / np.sqrt(2)
    for mask in range(8):
        for outcome in range(16):
            image = lp_masked_channel._kraus(preparation[:, mask], outcome) @ plus_four
            probability = float(np.vdot(image, image).real)
            expected = 0 if outcome & 8 else 1 / 64
            assert probability == pytest.approx(expected)


def test_mutated_mask_direction_fails_positive_channel_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = lp_masked_channel._mask_preparation
    monkeypatch.setattr(lp_masked_channel, "_mask_preparation",
                        lambda *, reverse=False: original(reverse=True))
    with pytest.raises(MaskedChannelError, match="X4-only projector"):
        dense_masked_channel_audit()


def test_mutated_final_cnot_rejected_even_if_zero_input_test_could_hide_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = lp_masked_channel._kraus
    # A spurious spectator-Z phase would leave |0000> alone but corrupt the
    # arbitrary-input channel. The operator comparison must reject it.
    spectator_z = np.diag([(-1) ** (i & 1) for i in range(16)])
    monkeypatch.setattr(lp_masked_channel, "_kraus",
                        lambda amplitudes, outcome: original(amplitudes, outcome) @ spectator_z)
    with pytest.raises(MaskedChannelError, match="X4-only projector"):
        dense_masked_channel_audit()


def test_masked_audit_is_json_safe_reproducible_and_not_ft(audit: dict[str, Any]) -> None:
    assert audit["evidence"] == "NUMERICAL"
    assert audit["physical_fault_tolerance_certified"] is False
    assert json.loads(json.dumps(audit, sort_keys=True, allow_nan=False)) == audit
    assert dense_masked_channel_audit() == audit
