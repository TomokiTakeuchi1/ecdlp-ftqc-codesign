"""Independent small-state retained-block GHZ preparation replay.

No construction module is imported. A literal ten-qubit circuit retains six
output modes (one canonical quartet and two residual modes) and Z-measures
four mask modes. This checks all sixteen logical branches of this model, not
all physical errors or the full LP instance (checked by exact algebra).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

_Array = NDArray[np.complex128]
_TOL = 1e-12
# An independent gate decomposition of the approved computational g^T action.
_AUTO_CNOTS = ((1, 0), (2, 0), (3, 0), (3, 1), (3, 2))


@dataclass(frozen=True)
class IdealProjectionRecovery:
    """Linear ideal CSS projection-sign recovery, NOT a noisy decoder.

    Each pivot stores a syndrome and a physical same-axis correction. For Q's
    Z projection the correction is X; for M's X projection it is Z. Inconsistent
    measurement signs are rejected, not silently decoded or postselected.
    """

    physical_qubits: int
    check_count: int
    pivots: tuple[tuple[int, int, int], ...]

    def recover(self, outcome: int) -> int:
        if type(outcome) is not int or outcome < 0 or outcome.bit_length() > self.check_count:
            raise ValueError("Invalid check outcome")
        correction = 0
        for pivot, syndrome, support in self.pivots:
            if outcome >> pivot & 1:
                outcome ^= syndrome
                correction ^= support
        if outcome:
            raise ValueError("Inconsistent ideal check outcomes; noisy decoding is OPEN")
        return correction


def projection_recovery(rows: tuple[int, ...], physical_qubits: int) -> IdealProjectionRecovery:
    """Build a deterministic right inverse on the allowed syndrome image."""
    if (
        type(physical_qubits) is not int or physical_qubits <= 0
        or type(rows) is not tuple
        or any(type(r) is not int or r < 0 or r.bit_length() > physical_qubits for r in rows)
    ):
        raise ValueError("Invalid projection matrix")
    columns = [0] * physical_qubits
    for row_index, original in enumerate(rows):
        row = original
        while row:
            bit = row & -row
            columns[bit.bit_length() - 1] |= 1 << row_index
            row ^= bit
    basis: dict[int, tuple[int, int]] = {}
    for qubit, column in enumerate(columns):
        syndrome, support = column, 1 << qubit
        while syndrome:
            pivot = syndrome.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = syndrome, support
                break
            other_syndrome, other_support = basis[pivot]
            syndrome ^= other_syndrome
            support ^= other_support
    # Independent multiplication verifies every recorded spanning identity.
    for syndrome, support in basis.values():
        actual = 0
        while support:
            bit = support & -support
            actual ^= columns[bit.bit_length() - 1]
            support ^= bit
        if actual != syndrome:
            raise ValueError("Projection-recovery identity failed")
    return IdealProjectionRecovery(
        physical_qubits, len(rows),
        tuple((pivot, *basis[pivot]) for pivot in sorted(basis, reverse=True)),
    )


def audit_projection_recovery(
    q_z_checks: tuple[int, ...], m_x_checks: tuple[int, ...], q_n: int, m_n: int
) -> dict[str, Any]:
    """Verify ideal preparation signs separately from later mask outcomes."""
    reports = {}
    for name, rows, n, axis in (
        ("Q_Z_projection", q_z_checks, q_n, "X"),
        ("M_X_projection", m_x_checks, m_n, "Z"),
    ):
        recovery = projection_recovery(rows, n)
        digest = hashlib.sha256()
        support_union = 0
        for pivot, syndrome, support in recovery.pivots:
            if recovery.recover(syndrome) != support:
                raise ValueError("Recovery map is not a right inverse on its basis")
            support_union |= support
            digest.update(f"{pivot}:{syndrome:x}:{support:x}\n".encode())
        reports[name] = {
            "check_rows": len(rows),
            "independent_ideal_sign_bits": len(recovery.pivots),
            "physical_correction_axis": axis,
            "linear_recovery_basis_sha256": digest.hexdigest(),
            "correction_support_union_size": support_union.bit_count(),
            "all_allowed_ideal_syndromes_covered": True,
        }
    return {
        "evidence": "NUMERICAL",
        "maps": reports,
        "default": "ideal physical correction before Q->M matching",
        "state_identity_argument": "X recovery preserves all Q logical X plus signs; Z recovery preserves all M logical Z zero signs",
        "tracking_alternative": "Q X frame also flips M Z readout; M Z frame propagates to retained Q, so both must be propagated",
        "noisy_decoder": False,
        "inconsistent_syndromes": "reject as outside ideal model; not a claimed FT acceptance protocol",
    }


def _cnot(state: _Array, control: int, target: int) -> _Array:
    indices = np.arange(state.size)
    permutation = indices ^ (((indices >> control) & 1) << target)
    return np.asarray(state[permutation], dtype=np.complex128)


def _auto(state: _Array, *, transposed_wrong: bool = False) -> _Array:
    gates = tuple((t, c) for c, t in reversed(_AUTO_CNOTS)) if transposed_wrong else _AUTO_CNOTS
    for control, target in gates:
        state = _cnot(state, control, target)
    return state


def _x(state: _Array, support: int) -> _Array:
    return np.asarray(state[np.arange(state.size) ^ support], dtype=np.complex128)


def _frame_image(support: int) -> int:
    for control, target in _AUTO_CNOTS:
        if support >> control & 1:
            support ^= 1 << target
    return support


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def dense_direct_ghz_audit() -> dict[str, Any]:
    """Replay all canonical/residual branches with pre/post-auto corrections.

    Bits 0..3 are the canonical quartet; residual bit 4 is Z-fixed and bit 5
    remains +. Mask bits 6..9 couple respectively to output bits 0,1,2,4.
    Residual factorization in the physical LP code is a separate certificate;
    this independent replay tests its claimed reduced signed-state semantics.
    """
    state = np.zeros(1024, dtype=np.complex128)
    state[:64] = 1 / 8  # uniform + on six output qubits; mask all zero
    reverse = state.copy()
    for target, control in enumerate((0, 1, 2, 4), start=6):
        state = _cnot(state, control, target)
        reverse = _cnot(reverse, target, control)
    ghz_residual = np.zeros(64, dtype=np.complex128)
    ghz_residual[[0, 15, 32, 47]] = 0.5  # GHZ_0123 tensor |0>_4 |+>_5
    residuals: list[float] = []
    probabilities: list[float] = []
    omitted: list[float] = []
    stale: list[float] = []
    wrong: list[float] = []
    canonical_purity: list[float] = []
    for outcome in range(16):
        raw = state[64 * outcome : 64 * (outcome + 1)]
        probability = float(np.vdot(raw, raw).real)
        _require(probability > _TOL, "Unexpected zero ideal branch")
        probabilities.append(probability)
        raw = raw / np.sqrt(probability)
        frame = (outcome & 7) | ((outcome >> 3) << 4)
        before = _auto(_x(raw, frame))
        after = _x(_auto(raw), _frame_image(frame))
        residuals += [
            float(np.max(np.abs(before - ghz_residual))),
            float(np.max(np.abs(after - ghz_residual))),
        ]
        # Keep the residual frame in every negative control, varying canonical
        # frame handling only. This avoids conflating residual and GHZ failure.
        residual_corrected = _x(raw, frame & 16)
        omitted.append(float(abs(np.vdot(ghz_residual, _auto(residual_corrected))) ** 2))
        stale_state = _x(_auto(raw), frame)
        stale.append(float(abs(np.vdot(ghz_residual, stale_state)) ** 2))
        wrong_state = _auto(_x(raw, frame), transposed_wrong=True)
        wrong.append(float(abs(np.vdot(ghz_residual, wrong_state)) ** 2))
        bipartition = after.reshape(4, 16)
        reduced = bipartition.conj().T @ bipartition
        canonical_purity.append(float(np.trace(reduced @ reduced).real))
    _require(max(residuals) < _TOL, "A direct corrected GHZ branch failed")
    _require(max(abs(p - 1 / 16) for p in probabilities) < _TOL,
             "Branch probabilities differ from uniform ideal input")
    _require(min(canonical_purity) > 1 - _TOL, "Residual modes did not factor")
    _require(abs(float(np.mean(omitted)) - 1 / 8) < _TOL,
             "Omitted-frame negative control failed")
    _require(abs(float(np.mean(stale)) - 1 / 2) < _TOL,
             "Untransformed-frame negative control failed")
    _require(max(abs(f - 1 / 4) for f in wrong) < _TOL,
             "Wrong-automorphism negative control failed")
    nonzero_reverse = [
        m for m in range(16)
        if float(np.vdot(reverse[64*m:64*(m+1)], reverse[64*m:64*(m+1)]).real) > _TOL
    ]
    _require(nonzero_reverse == [0], "Wrong-direction negative control changed")
    return {
        "evidence": "NUMERICAL",
        "scope": "ten ideal logical qubits; not a full physical LP simulation",
        "state_preparation_only_not_arbitrary_input_channel": True,
        "independent_of_construction_imports": True,
        "retained_output_modes": 6,
        "canonical_output_modes": 4,
        "fixed_residual_z_modes": 1,
        "retained_residual_x_modes": 1,
        "mask_outcome_bits": 4,
        "nonzero_branches": len(probabilities),
        "branch_probability": probabilities[0],
        "total_probability": sum(probabilities),
        "pre_and_post_automorphism_frame_max_residual": max(residuals),
        "canonical_reduced_purity_minimum": min(canonical_purity),
        "omitted_canonical_frame_mean_ghz_fidelity": float(np.mean(omitted)),
        "untransformed_output_frame_mean_ghz_fidelity": float(np.mean(stale)),
        "wrong_auto_mean_ghz_fidelity": float(np.mean(wrong)),
        "reversed_matching_nonzero_branches": len(nonzero_reverse),
        "outcome_postselection": False,
        "physical_fault_tolerance_certified": False,
        "all_checks_passed": True,
    }
