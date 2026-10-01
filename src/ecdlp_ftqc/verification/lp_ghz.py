"""Independent dense logical checks for the completed-LP GHZ proposal.

This module deliberately imports no LP constructor or compiler.  It verifies only
four- and eight-*logical*-qubit channels, not physical code distance, preparation
fault tolerance, ancilla construction, or runtime.
"""

from __future__ import annotations

import math
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray


class LpGhzReplayError(ValueError):
    """An independently reconstructed logical GHZ identity failed."""


_ComplexArray = NDArray[np.complex128]
_BinaryArray = NDArray[np.uint8]
_TOLERANCE = 1e-12


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LpGhzReplayError(message)


def _tensor(left: _ComplexArray, right: _ComplexArray) -> _ComplexArray:
    return np.asarray(np.kron(left, right), dtype=np.complex128)


def _pauli(word: str) -> _ComplexArray:
    letters = {
        "I": np.eye(2, dtype=np.complex128),
        "X": np.array([[0, 1], [1, 0]], dtype=np.complex128),
        "Z": np.array([[1, 0], [0, -1]], dtype=np.complex128),
    }
    result: _ComplexArray = np.ones((1, 1), dtype=np.complex128)
    for letter in word:
        result = _tensor(result, letters[letter])
    return result


def _basis_permutation(action: _BinaryArray) -> _ComplexArray:
    """Construct |u> -> |action*u>, with qubit one the leftmost bit."""
    width = action.shape[0]
    result = np.zeros((2**width, 2**width), dtype=np.complex128)
    for source in range(2**width):
        bits = np.array(
            [(source >> (width - 1 - bit)) & 1 for bit in range(width)],
            dtype=np.uint8,
        )
        image = (action @ bits) % 2
        target = sum(int(bit) << (width - 1 - index) for index, bit in enumerate(image))
        result[target, source] = 1
    return result


def _zero(width: int) -> _ComplexArray:
    result = np.zeros(2**width, dtype=np.complex128)
    result[0] = 1
    return result


def _signed_ghz(width: int, outcome: int) -> _ComplexArray:
    result = _zero(width)
    result[-1] = (-1) ** outcome
    return result / (2**0.5)


def _project(
    state: _ComplexArray, observable: _ComplexArray, outcome: int
) -> tuple[float, _ComplexArray]:
    image = (state + (-1) ** outcome * (observable @ state)) / 2
    probability = float(np.vdot(image, image).real)
    _require(probability > _TOLERANCE, "A claimed deterministic-acceptance branch is zero")
    return probability, image / np.sqrt(probability)


def _residual(left: _ComplexArray, right: _ComplexArray) -> float:
    return float(np.linalg.norm(left - right))


def _expectation(state: _ComplexArray, observable: _ComplexArray) -> float:
    value = complex(np.vdot(state, observable @ state))
    _require(abs(value.imag) < _TOLERANCE, "Non-real Pauli expectation")
    return value.real


def dense_logical_audit() -> dict[str, Any]:
    """Reconstruct the GHZ channels and two misleading alternatives from scratch.

    The supplied source matrix acts on column coefficients of logical Z
    generators.  The computational-basis action must therefore be its inverse
    transpose.  Here the matrix is involutory, so the transpose suffices.  Both
    signs of each individual measurement are accepted with a known Z frame;
    measuring a product of the individual observables is explicitly *not* the
    same channel.

    The JSON-safe result records numerical evidence, including negative controls.
    Any positive claim that fails its dense check raises ``LpGhzReplayError``.
    """
    z_action = np.array(
        [[1, 0, 0, 0], [1, 1, 0, 0], [1, 0, 1, 0], [1, 1, 1, 1]],
        dtype=np.uint8,
    )
    _require(
        np.array_equal((z_action @ z_action) % 2, np.eye(4, dtype=np.uint8)),
        "The independently specified Z action is not involutory",
    )
    bit_action = z_action.T.copy()
    unitary = _basis_permutation(bit_action)
    _require(
        _residual(unitary @ unitary.conj().T, np.eye(16, dtype=np.complex128)) < _TOLERANCE,
        "Computational-basis map is not unitary",
    )
    conjugation_residuals: list[float] = []
    wrong_action_residuals: list[float] = []
    wrong_unitary = _basis_permutation(z_action)
    for index in range(4):
        for letter, action in (("Z", z_action), ("X", bit_action)):
            word = "I" * index + letter + "I" * (3 - index)
            expected_word = "".join(letter if bit else "I" for bit in action[:, index])
            expected = _pauli(expected_word)
            actual = unitary @ _pauli(word) @ unitary.conj().T
            conjugation_residuals.append(_residual(actual, expected))
            if letter == "Z":
                wrong = wrong_unitary @ _pauli(word) @ wrong_unitary.conj().T
                wrong_action_residuals.append(_residual(wrong, expected))
    _require(max(conjugation_residuals) < _TOLERANCE, "X/Z conjugation identity failed")
    _require(max(wrong_action_residuals) > 1, "Missing transpose negative control failed")

    stabilizer_words = ("XXXX", "ZZII", "IZZI", "IIZZ")
    stabilizers = {word: _pauli(word) for word in stabilizer_words}
    single_branches: list[dict[str, Any]] = []
    for outcome in (0, 1):
        probability, prepared = _project(_zero(4), _pauli("IIIX"), outcome)
        result = unitary @ prepared
        expected = _signed_ghz(4, outcome)
        corrected = (_pauli("IIIZ") @ result) if outcome else result
        expectations = {
            word: _expectation(result, observable) for word, observable in stabilizers.items()
        }
        corrected_expectations = {
            word: _expectation(corrected, observable)
            for word, observable in stabilizers.items()
        }
        branch_residual = _residual(result, expected)
        corrected_residual = _residual(corrected, _signed_ghz(4, 0))
        _require(abs(probability - 0.5) < _TOLERANCE, "Incorrect individual outcome probability")
        _require(branch_residual < _TOLERANCE, "Fourth-input GHZ preparation failed")
        _require(corrected_residual < _TOLERANCE, "GHZ Pauli-frame correction failed")
        _require(
            all(abs(value - 1) < _TOLERANCE for value in corrected_expectations.values()),
            "Corrected GHZ stabilizer failed",
        )

        _, wrong_input = _project(_zero(4), _pauli("XIII"), outcome)
        wrong_result = unitary @ wrong_input
        wrong_fidelity = float(abs(np.vdot(expected, wrong_result)) ** 2)
        _require(_residual(wrong_result, wrong_input) < _TOLERANCE, "First input not fixed")
        _require(abs(wrong_fidelity - 0.25) < _TOLERANCE, "Wrong-input negative control failed")
        single_branches.append(
            {
                "outcome": outcome,
                "probability": probability,
                "signed_ghz_residual": branch_residual,
                "post_correction": "IIIZ" if outcome else "IIII",
                "corrected_ghz_residual": corrected_residual,
                "signed_stabilizer_expectations": expectations,
                "corrected_stabilizer_expectations": corrected_expectations,
                "wrong_first_input_is_fixed": True,
                "wrong_first_input_signed_ghz_fidelity": wrong_fidelity,
            }
        )

    two_unitary = _tensor(unitary, unitary)
    first_x = _pauli("IIIXIIII")
    second_x = _pauli("IIIIIIIX")
    independent_branches: list[dict[str, Any]] = []
    for first in (0, 1):
        for second in (0, 1):
            p_first, intermediate = _project(_zero(8), first_x, first)
            p_second, prepared = _project(intermediate, second_x, second)
            result = two_unitary @ prepared
            expected = _tensor(_signed_ghz(4, first), _signed_ghz(4, second))
            correction_word = ("IIIZ" if first else "IIII") + (
                "IIIZ" if second else "IIII"
            )
            corrected = _pauli(correction_word) @ result
            branch_residual = _residual(result, expected)
            corrected_residual = _residual(
                corrected, _tensor(_signed_ghz(4, 0), _signed_ghz(4, 0))
            )
            _require(branch_residual < _TOLERANCE, "Independent GHZ preparation failed")
            _require(corrected_residual < _TOLERANCE, "Two-quartet frame correction failed")
            _require(abs(p_first * p_second - 0.25) < _TOLERANCE, "Wrong joint probability")
            independent_branches.append(
                {
                    "outcomes": [first, second],
                    "probability": p_first * p_second,
                    "two_signed_ghz_residual": branch_residual,
                    "post_correction": correction_word,
                    "two_corrected_ghz_residual": corrected_residual,
                }
            )

    product_branches: list[dict[str, Any]] = []
    for outcome in (0, 1):
        probability, prepared = _project(_zero(8), _pauli("IIIXIIIX"), outcome)
        result = two_unitary @ prepared
        global_residual = _residual(result, _signed_ghz(8, outcome))
        local_expectations = {
            word: _expectation(result, _pauli(word)) for word in ("XXXXIIII", "IIIIXXXX")
        }
        joint_expectation = _expectation(result, _pauli("XXXXXXXX"))
        _require(global_residual < _TOLERANCE, "Product-measurement negative control failed")
        _require(
            all(abs(value) < _TOLERANCE for value in local_expectations.values()),
            "A joint measurement was incorrectly admitted as separate measurements",
        )
        _require(
            abs(joint_expectation - (-1) ** outcome) < _TOLERANCE,
            "Joint-measurement sign was lost",
        )
        product_branches.append(
            {
                "outcome": outcome,
                "probability": probability,
                "eight_qubit_ghz_residual": global_residual,
                "local_four_qubit_x_expectations": local_expectations,
                "joint_eight_qubit_x_expectation": joint_expectation,
                "is_two_independent_four_qubit_ghz_states": False,
            }
        )

    return {
        "schema_version": 1,
        "evidence": "NUMERICAL",
        "scope": "ideal four- and eight-logical-qubit Clifford channels only",
        "qubit_order": "qubit 1 is the leftmost computational-basis bit",
        "z_generator_column_action": z_action.tolist(),
        "computational_bit_column_action": bit_action.tolist(),
        "conjugation_checks": len(conjugation_residuals),
        "maximum_conjugation_residual": max(conjugation_residuals),
        "missing_transpose_maximum_z_conjugation_residual": max(wrong_action_residuals),
        "correct_plus_input_index_one_based": 4,
        "single_quartet_branches": single_branches,
        "independent_two_quartet_branches": independent_branches,
        "product_measurement_negative_control": product_branches,
        "individual_measurement_outcome_postselection_required": False,
        "physical_fault_tolerance_certified": False,
        "all_checks_passed": True,
    }


def _object(value: Any, path: str) -> dict[str, Any]:
    _require(type(value) is dict, f"{path}: expected an object")
    _require(all(type(key) is str for key in value), f"{path}: non-string key")
    return cast(dict[str, Any], value)


def _equal(value: Any, expected: Any, path: str) -> None:
    """Compare JSON values without accepting bools as integer counts."""
    _require(type(value) is type(expected), f"{path}: incorrect value type")
    if isinstance(expected, dict):
        _require(value.keys() == expected.keys(), f"{path}: missing or unexpected fields")
        for key in expected:
            _equal(value[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        _require(len(value) == len(expected), f"{path}: incorrect list length")
        for index, item in enumerate(expected):
            _equal(value[index], item, f"{path}[{index}]")
    elif isinstance(expected, float):
        _require(
            math.isfinite(value) and abs(value - expected) <= _TOLERANCE,
            f"{path}: changed numerical certificate value",
        )
    else:
        _require(value == expected, f"{path}: changed certificate value")


def _fields(value: Any, expected: dict[str, Any], path: str) -> dict[str, Any]:
    block = _object(value, path)
    for key, item in expected.items():
        _require(key in block, f"{path}.{key}: missing field")
        _equal(block[key], item, f"{path}.{key}")
    return block


def _digest(value: Any, path: str) -> None:
    _require(
        type(value) is str and len(value) == 64
        and all(character in "0123456789abcdef" for character in value),
        f"{path}: expected lowercase SHA-256",
    )


def validate_emitted_certificate(payload: dict[str, Any]) -> None:
    """Fail closed on v1 certificate semantics and replay its dense logical audit.

    This is an independent *consistency and admission* check, not a second
    reconstruction of the 9,600-physical-qubit code.  The finite physical ranks
    and hashes must still be checked by the code-level verifier and cross-review.
    The dense logical report is recomputed here without importing that generator.
    No missing field, nonzero failure counter, distance-one FT admission, or
    conflation of 302 raw observables with 300 canonical observables is accepted.
    """
    document = _fields(payload, {
        "schema": "lp-ghz-certificate-v1", "task_id": "T-20261001-001",
    }, "certificate")
    required_sections = (
        "code", "convention", "checks", "residual_image", "auxiliaries",
        "admission", "independent_dense_logical_audit",
    )
    for name in required_sections:
        _require(name in document, f"certificate.{name}: missing section")

    code = _fields(document["code"], {
        "name": "Q_one=LP(tilde_A,A*)", "lift": 75, "data_qubits": 9600,
        "hx_rows": 5250, "hx_rank": 5226, "hz_rows": 3150, "hz_rank": 3134,
        "logical_qubits": 1240, "canonical_logical_qubits": 1200,
        "residual_logical_qubits": 40, "hx_max_weight": 10, "hz_max_weight": 13,
        "hx_edges": 45150, "hz_edges": 34650, "base_rank": 223,
        "completed_seed_rank": 746,
    }, "code")
    for name in ("hx_sha256", "hz_sha256", "canonical_x_sha256", "canonical_z_sha256"):
        _digest(code.get(name), f"code.{name}")
    convention = _fields(document["convention"], {
        "support": "binary column vector; circulant row c, column c-t",
        "canonical_order": "((i*4+j)*75+a), all indices zero-based",
        "canonical_section": "pi_J E=I; parity of base columns 2 and 5 is zero",
        "g_z_rows_little_endian": [1, 3, 5, 15],
        "computational_gate": "transpose(g_z)", "correct_ghz_input": "000+",
        "correct_selected_logical_row_one_based": 4,
        "source_ghz_input_negative_control": "+000",
        "wrong_x_action_failures_of_1200": 1200,
    }, "convention")
    words = convention.get("canonical_seed_words_hex")
    _require(type(words) is list and len(words) == 4, "convention: missing encoder words")
    for word in cast(list[Any], words):
        _require(
            type(word) is str and word.startswith("0x") and len(word) > 2
            and all(letter in "0123456789abcdef" for letter in word[2:]),
            "convention: invalid encoder word",
        )
        _require(0 < int(word, 16) < 2**525, "convention: encoder word exceeds support")

    required_checks = {
        "css_commutator_nonzeros", "canonical_x_syndromes", "canonical_z_syndromes",
        "canonical_pairing_rows", "permuted_x_checks", "permuted_z_checks",
        "canonical_x_auto_action", "canonical_z_auto_action", "residual_canonical_pairing",
        "raw_interface", "strict_interface",
    }
    checks = _object(document["checks"], "checks")
    _require(required_checks <= checks.keys(), "checks: required failure counters missing")
    for name, value in checks.items():
        _equal(value, 0, f"checks.{name}")
    _fields(document["residual_image"], {
        "additional_rank_beyond_all_canonical_x": 2,
        "canonical_symplectic_pairing_failures": 0,
        "canonical_symplectic_space_invariant": True,
    }, "residual_image")

    variants = document["auxiliaries"]
    _require(type(variants) is list and len(variants) == 2, "auxiliaries: need both variants")
    common = {
        "evidence": "NUMERICAL", "data_qubits": 525, "hx_generators": 0,
        "canonical_x_measurements": 300, "homomorphic_inclusion_failures": [0, 0],
        "measured_space_failures": 0, "interface_cnots": 525,
        "interface_matching_layers": 1, "algebraic_batch_ghz4_count": 300,
        "z_distance": 1, "single_z_logical_count": 525,
        "readout_fault_canonical_outcomes_flipped_min": 1,
        "readout_fault_canonical_outcomes_flipped_max": 156,
        "ft_single_shot_admitted": False, "data_plus_helper_qubits_excluding_qec": 10125,
        "initialization_rounds": None, "logical_failure_probability": None,
        "native_runtime_seconds": None, "ft_admitted_parallel_measurements": None,
        "single_fault_witness": {
            "auxiliary_physical_qubit_zero_based": 150,
            "fault": "Z immediately before destructive X readout",
            "auxiliary_syndrome": [], "data_error_propagated": False,
            "canonical_outcomes_flipped": 1,
            "incorrect_canonical_sign": "GHZ quartet j=1,a=0",
        },
    }
    for index, strict in enumerate((False, True)):
        expected = common | {
            "name": "strict_300" if strict else "raw_302",
            "hz_generators": 227 if strict else 225, "hz_rank": 225 if strict else 223,
            "hz_weight_max": 75 if strict else 7, "hz_edges": 1725 if strict else 1575,
            "logical_qubits": 300 if strict else 302,
            "independent_measured_data_x": 300 if strict else 302,
            "additional_residual_x_measurements": 0 if strict else 2,
            "preserves_unmeasured_residual_subsystem_ideally": strict,
            "qec_ancillas_one_per_supplied_check_not_ft_schedule": 8627 if strict else 8625,
        }
        variant = _fields(variants[index], expected, f"auxiliaries[{index}]")
        for name in ("hz_sha256", "kernel_sha256"):
            _digest(variant.get(name), f"auxiliaries[{index}].{name}")
    _equal(document["admission"], {
        "ideal_algebra": True, "fault_tolerant_factory": False,
        "runtime_seconds": None, "failure_probability": None,
        "distance_of_data_code_certified_this_cycle": None, "review_status": "PENDING",
    }, "admission")
    _equal(
        document["independent_dense_logical_audit"], dense_logical_audit(),
        "independent_dense_logical_audit",
    )
    if "manifest_sha256" in document:
        _digest(document["manifest_sha256"], "manifest_sha256")
