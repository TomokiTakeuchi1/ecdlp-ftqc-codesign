"""Independent ideal channel audit of a masked LP GHZ measurement interface.

Only one four-logical-qubit quartet is simulated. No LP construction, compiler,
or other verifier is imported. The mask has three logical zero qubits; auxiliary
uniform-plus preparation and the two CNOT matchings are contracted into 16 by
16 data Kraus operators. This is not a physical fault-tolerance certificate.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

_Array = NDArray[np.complex128]
_TOLERANCE = 1e-12


class MaskedChannelError(ValueError):
    """An independently reconstructed masked measurement identity failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MaskedChannelError(message)


def _x_shift(support: int) -> _Array:
    result = np.zeros((16, 16), dtype=np.complex128)
    for source in range(16):
        result[source ^ support, source] = 1
    return result


def _z_sign(support: int) -> _Array:
    return np.diag(
        np.array([(-1) ** ((support & i).bit_count() % 2) for i in range(16)],
                 dtype=np.complex128)
    )


def _mask_preparation(*, reverse: bool = False) -> _Array:
    """Return unnormalized A amplitudes for each Z outcome of M.

    A starts in |++++>, M in |000>. The columns are physical logical-Z
    measurement branches of M, not postselected or renormalized states.
    Qubit one is the least significant bit throughout this module.
    """
    initial = np.zeros((16, 8), dtype=np.complex128)
    initial[:, 0] = 0.25
    result = np.zeros_like(initial)
    for auxiliary in range(16):
        for mask in range(8):
            if reverse:
                result[auxiliary ^ mask, mask] += initial[auxiliary, mask]
            else:
                result[auxiliary, mask ^ (auxiliary & 7)] += initial[auxiliary, mask]
    return result


def _kraus(amplitudes: _Array, x_outcome: int) -> _Array:
    """Contract identity A->data CNOT and destructive X readout of A."""
    result = np.zeros((16, 16), dtype=np.complex128)
    for auxiliary, amplitude in enumerate(amplitudes):
        # <b_X|a_Z> is (-1)^(a dot b)/4 for the four auxiliary qubits.
        coefficient = amplitude * (-1) ** ((auxiliary & x_outcome).bit_count() % 2) / 4
        for source in range(16):
            result[source ^ auxiliary, source] += coefficient
    return result


def _computational_automorphism() -> _Array:
    """Specify the source Z-label action independently, then use its transpose."""
    z_action = np.array(
        [[1, 0, 0, 0], [1, 1, 0, 0], [1, 0, 1, 0], [1, 1, 1, 1]],
        dtype=np.uint8,
    )
    _require(
        np.array_equal((z_action @ z_action) % 2, np.eye(4, dtype=np.uint8)),
        "The explicit Z action is not involutory",
    )
    result = np.zeros((16, 16), dtype=np.complex128)
    for source in range(16):
        binary = np.array([(source >> i) & 1 for i in range(4)], dtype=np.uint8)
        image = (z_action.T @ binary) % 2
        target = sum(int(bit) << i for i, bit in enumerate(image))
        result[target, source] = 1
    return result


def _norm(vector: _Array) -> float:
    return float(np.vdot(vector, vector).real)


def _residual(left: _Array, right: _Array) -> float:
    return float(np.max(np.abs(left - right)))


def _fidelity(left: _Array, right: _Array) -> float:
    return float(abs(np.vdot(left, right)) ** 2)


def dense_masked_channel_audit() -> dict[str, Any]:
    """Audit every signed branch and the full arbitrary-input Kraus operators.

    The mask outcomes are retained as an X frame on A. During the subsequent
    identity CNOT, that frame propagates onto data. Correcting that known data
    frame must give a scalar times the X4 projector and identity on qubits 1-3.
    Operator equality certifies the entire input channel, including inputs
    entangled with external systems; uniform branch probabilities are claimed
    only for the explicitly tested |0000> input.
    """
    identity = np.eye(16, dtype=np.complex128)
    x_four = _x_shift(8)
    auto = _computational_automorphism()
    _require(_residual(auto.conj().T @ auto, identity) < _TOLERANCE,
             "The computational automorphism is not unitary")
    zero = identity[:, 0]
    ghz = (zero + identity[:, 15]) / np.sqrt(2)
    bell_input = (identity[:, 0] + identity[:, 3]) / np.sqrt(2)
    bell_output = (identity[:, 0] + identity[:, 3]
                   + identity[:, 8] + identity[:, 11]) / 2

    preparation = _mask_preparation()
    completeness = np.zeros_like(identity)
    probabilities: list[float] = []
    residuals: list[float] = []
    fidelities: list[float] = []
    spectator_fidelities: list[float] = []
    missing_frame_fidelities: list[float] = []
    missing_sign_fidelities: list[float] = []
    outcome_weights = [0.0, 0.0]
    mask_probabilities = [_norm(preparation[:, m]) for m in range(8)]

    for mask in range(8):
        for outcome in range(16):
            raw = _kraus(preparation[:, mask], outcome)
            completeness += raw.conj().T @ raw
            sign = (outcome >> 3) & 1
            phase = (-1) ** ((mask & outcome).bit_count() % 2)
            projector = (identity + (-1) ** sign * x_four) / 2
            corrected = _x_shift(mask) @ raw
            residuals.append(_residual(corrected, phase * projector / 8))
            _require(residuals[-1] < _TOLERANCE,
                     "Corrected branch is not the X4-only projector")
            outcome_weights[sign] += (1 / 8) ** 2

            state = corrected @ zero
            probability = _norm(state)
            _require(probability > _TOLERANCE, "A |0000> branch is unexpectedly zero")
            probabilities.append(probability)
            state /= np.sqrt(probability)
            sign_correction = _z_sign(8 * sign)
            fidelities.append(_fidelity(ghz, auto @ sign_correction @ state))
            missing_sign_fidelities.append(_fidelity(ghz, auto @ state))
            uncorrected = raw @ zero / np.sqrt(probability)
            missing_frame_fidelities.append(
                _fidelity(ghz, auto @ sign_correction @ uncorrected)
            )

            spectator = sign_correction @ corrected @ bell_input
            spectator /= np.sqrt(_norm(spectator))
            spectator_fidelities.append(_fidelity(bell_output, spectator))

    completeness_residual = _residual(completeness, identity)
    _require(completeness_residual < _TOLERANCE, "The full Kraus family is not trace preserving")
    _require(max(abs(p - 1 / 128) for p in probabilities) < _TOLERANCE,
             "Incorrect branch probabilities for |0000>")
    _require(min(fidelities) > 1 - _TOLERANCE, "A corrected GHZ branch is wrong")
    _require(min(spectator_fidelities) > 1 - _TOLERANCE,
             "The unwanted data logicals have lost Bell coherence")
    _require(max(abs(weight - 1) for weight in outcome_weights) < _TOLERANCE,
             "Coarse-grained X4 instrument has the wrong normalization")
    missing_frame_mean = float(np.mean(missing_frame_fidelities))
    missing_sign_mean = float(np.mean(missing_sign_fidelities))
    _require(abs(missing_frame_mean - 1 / 8) < _TOLERANCE,
             "Missing-mask-frame negative control failed")
    _require(abs(missing_sign_mean - 0.5) < _TOLERANCE,
             "Missing-X4-sign negative control failed")

    # Reversing the mask matching leaves A uniformly +. It then measures all
    # four data Xs, not only X4. Even correcting all four output signs prepares
    # ++++ rather than a GHZ state. These are separate negative-control frames.
    reversed_preparation = _mask_preparation(reverse=True)
    reverse_fidelities: list[float] = []
    reverse_operator_residuals: list[float] = []
    reversed_nonzero_branches = 0
    reversed_probability_sum = 0.0
    for mask in range(8):
        for outcome in range(16):
            raw = _kraus(reversed_preparation[:, mask], outcome)
            state = raw @ zero
            probability = _norm(state)
            reversed_probability_sum += probability
            if probability < _TOLERANCE:
                continue
            reversed_nonzero_branches += 1
            state = _z_sign(outcome) @ state / np.sqrt(probability)
            reverse_fidelities.append(_fidelity(ghz, auto @ state))
            sign = (outcome >> 3) & 1
            expected = (identity + (-1) ** sign * x_four) / 16
            reverse_operator_residuals.append(_residual(raw, expected))
    _require(reversed_nonzero_branches == 16, "Reversed mask has unexpected branches")
    _require(abs(reversed_probability_sum - 1) < _TOLERANCE,
             "Reversed-mask channel lost probability")
    _require(max(reverse_operator_residuals) > 0.01,
             "Reversed-mask channel incorrectly equals the desired instrument")
    _require(max(abs(f - 1 / 8) for f in reverse_fidelities) < _TOLERANCE,
             "Reversed-mask negative-control fidelity failed")

    return {
        "schema_version": 1,
        "evidence": "NUMERICAL",
        "scope": "ideal four-logical-qubit channel; physical LP map checked separately",
        "qubit_order": "qubit 1 is the least significant computational-basis bit",
        "mask_cnot_direction": "auxiliary control to uniform-zero mask target",
        "data_cnot_direction": "masked auxiliary control to data target",
        "retained_mask_outcomes": 8,
        "retained_auxiliary_x_outcomes_per_mask": 16,
        "kraus_operator_count": len(probabilities),
        "mask_outcome_probability_min": min(mask_probabilities),
        "mask_outcome_probability_max": max(mask_probabilities),
        "zero_input_branch_probability_min": min(probabilities),
        "zero_input_branch_probability_max": max(probabilities),
        "zero_input_total_probability": sum(probabilities),
        "arbitrary_input_branch_probabilities_uniform": False,
        "corrected_kraus_maximum_residual": max(residuals),
        "trace_preservation_maximum_residual": completeness_residual,
        "coarse_grained_x4_instrument_weights": outcome_weights,
        "uncoupled_data_logicals_preserved_by_measurement": [1, 2, 3],
        "spectator_bell_fidelity_minimum": min(spectator_fidelities),
        "corrected_ghz_fidelity_minimum": min(fidelities),
        "missing_propagated_mask_x_frame_mean_ghz_fidelity": missing_frame_mean,
        "missing_x4_sign_frame_mean_ghz_fidelity": missing_sign_mean,
        "reversed_mask_cnot": {
            "nonzero_zero_input_branches": reversed_nonzero_branches,
            "zero_input_total_probability": reversed_probability_sum,
            "desired_kraus_maximum_residual": max(reverse_operator_residuals),
            "measures_all_four_data_xs": True,
            "frame_for_negative_control": "correct all four X-readout signs by data Zs",
            "corrected_ghz_fidelity_minimum": min(reverse_fidelities),
            "corrected_ghz_fidelity_maximum": max(reverse_fidelities),
        },
        "measurement_outcome_postselection_required": False,
        "physical_fault_tolerance_certified": False,
        "all_checks_passed": True,
    }
