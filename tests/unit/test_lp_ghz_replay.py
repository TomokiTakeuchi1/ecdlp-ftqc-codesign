from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

from ecdlp_ftqc.code_constructions.lp_ghz import audit_instance
from ecdlp_ftqc.verification.lp_ghz import (
    LpGhzReplayError,
    dense_logical_audit,
    validate_emitted_certificate,
)


@pytest.fixture(scope="module")
def audit() -> dict[str, Any]:
    return dense_logical_audit()


def test_z_action_requires_transposed_computational_gate(audit: dict[str, Any]) -> None:
    assert audit["all_checks_passed"]
    assert audit["conjugation_checks"] == 8
    assert audit["maximum_conjugation_residual"] == 0
    assert audit["missing_transpose_maximum_z_conjugation_residual"] > 1
    z_action = audit["z_generator_column_action"]
    bit_action = audit["computational_bit_column_action"]
    assert bit_action == [list(column) for column in zip(*z_action, strict=True)]
    assert bit_action != z_action


def test_fourth_input_creates_both_signed_ghz_branches(audit: dict[str, Any]) -> None:
    assert audit["correct_plus_input_index_one_based"] == 4
    branches = audit["single_quartet_branches"]
    assert [branch["outcome"] for branch in branches] == [0, 1]
    assert sum(branch["probability"] for branch in branches) == pytest.approx(1)
    for branch in branches:
        assert branch["probability"] == pytest.approx(0.5)
        assert branch["signed_ghz_residual"] < 1e-12
        assert branch["corrected_ghz_residual"] < 1e-12
        signs = branch["signed_stabilizer_expectations"]
        assert signs["XXXX"] == pytest.approx((-1) ** branch["outcome"])
        assert [signs[word] for word in ("ZZII", "IZZI", "IIZZ")] == pytest.approx([1] * 3)
        assert list(branch["corrected_stabilizer_expectations"].values()) == pytest.approx([1] * 4)
    assert branches[1]["post_correction"] == "IIIZ"
    assert audit["individual_measurement_outcome_postselection_required"] is False


def test_source_first_input_is_a_negative_control(audit: dict[str, Any]) -> None:
    for branch in audit["single_quartet_branches"]:
        assert branch["wrong_first_input_is_fixed"]
        assert branch["wrong_first_input_signed_ghz_fidelity"] == pytest.approx(0.25)


def test_two_individual_measurements_accept_all_four_outcomes(audit: dict[str, Any]) -> None:
    branches = audit["independent_two_quartet_branches"]
    assert [branch["outcomes"] for branch in branches] == [[0, 0], [0, 1], [1, 0], [1, 1]]
    assert sum(branch["probability"] for branch in branches) == pytest.approx(1)
    for branch in branches:
        assert branch["probability"] == pytest.approx(0.25)
        assert branch["two_signed_ghz_residual"] < 1e-12
        assert branch["two_corrected_ghz_residual"] < 1e-12


def test_product_measurement_does_not_prepare_independent_quartets(audit: dict[str, Any]) -> None:
    for branch in audit["product_measurement_negative_control"]:
        assert branch["probability"] == pytest.approx(0.5)
        assert branch["eight_qubit_ghz_residual"] < 1e-12
        assert branch["is_two_independent_four_qubit_ghz_states"] is False
        assert list(branch["local_four_qubit_x_expectations"].values()) == pytest.approx([0, 0])
        assert branch["joint_eight_qubit_x_expectation"] == pytest.approx((-1) ** branch["outcome"])


def test_audit_is_reproducible_json_and_not_a_physical_certificate(audit: dict[str, Any]) -> None:
    assert audit["evidence"] == "NUMERICAL"
    assert audit["physical_fault_tolerance_certified"] is False
    serialized = json.dumps(audit, sort_keys=True, allow_nan=False)
    assert json.loads(serialized) == audit
    assert dense_logical_audit() == audit


@pytest.fixture(scope="module")
def emitted_certificate() -> dict[str, Any]:
    result = audit_instance()
    result["independent_dense_logical_audit"] = dense_logical_audit()
    return result


def test_saved_certificate_passes_semantic_gate(emitted_certificate: dict[str, Any]) -> None:
    validate_emitted_certificate(emitted_certificate)


@pytest.mark.parametrize(("path", "replacement"), [
    (("admission", "fault_tolerant_factory"), True),
    (("admission", "runtime_seconds"), 0),
    (("auxiliaries", 0, "ft_single_shot_admitted"), True),
    (("auxiliaries", 0, "logical_qubits"), 300),
    (("auxiliaries", 0, "independent_measured_data_x"), 300),
    (("auxiliaries", 0, "additional_residual_x_measurements"), 0),
    (("auxiliaries", 1, "z_distance"), 2),
    (("auxiliaries", 1, "hz_weight_max"), 7),
    (("auxiliaries", 1, "single_fault_witness", "canonical_outcomes_flipped"), 0),
    (("convention", "correct_selected_logical_row_one_based"), 1),
    (("convention", "wrong_x_action_failures_of_1200"), 0),
    (("checks", "canonical_x_syndromes"), 1),
    (("checks", "canonical_x_syndromes"), False),
    (("checks", "canonical_x_syndromes"), 0.0),
    (("independent_dense_logical_audit", "physical_fault_tolerance_certified"), True),
])
def test_semantic_gate_rejects_mutated_claim(
    emitted_certificate: dict[str, Any], path: tuple[str | int, ...], replacement: Any,
) -> None:
    changed = deepcopy(emitted_certificate)
    target: Any = changed
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement
    with pytest.raises(LpGhzReplayError):
        validate_emitted_certificate(changed)


@pytest.mark.parametrize("section", ["checks", "admission", "independent_dense_logical_audit"])
def test_semantic_gate_rejects_missing_sections(
    emitted_certificate: dict[str, Any], section: str,
) -> None:
    changed = deepcopy(emitted_certificate)
    del changed[section]
    with pytest.raises(LpGhzReplayError, match="missing section"):
        validate_emitted_certificate(changed)


def test_semantic_gate_requires_every_failure_counter(emitted_certificate: dict[str, Any]) -> None:
    changed = deepcopy(emitted_certificate)
    del changed["checks"]["raw_interface"]
    with pytest.raises(LpGhzReplayError, match="failure counters missing"):
        validate_emitted_certificate(changed)


def test_dense_replay_allows_only_small_finite_roundoff(emitted_certificate: dict[str, Any]) -> None:
    changed = deepcopy(emitted_certificate)
    dense = changed["independent_dense_logical_audit"]
    dense["maximum_conjugation_residual"] = 1e-13
    validate_emitted_certificate(changed)
    for invalid in (2e-12, float("nan"), float("inf")):
        dense["maximum_conjugation_residual"] = invalid
        with pytest.raises(LpGhzReplayError, match="numerical certificate"):
            validate_emitted_certificate(changed)
