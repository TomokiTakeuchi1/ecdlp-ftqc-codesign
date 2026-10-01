"""All-outcome, ideal retained-block LP GHZ preparation certificate.

This module specializes the approved Q->M masking interface to state
preparation: the masked Q is retained and permuted, not used to measure a
second data block. Packed integers describe binary supports, not fault-free
physical implementations of the potentially large Pauli frame representatives.
No distance search, syndrome decoder, circuit-FT or native-time claim is made.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from ecdlp_ftqc.code_constructions.lp_ghz import (
    CSSCode,
    apply_rows,
    automorphism_permutation,
    base_seed,
    bits,
    canonical_logicals,
    completed_seed,
    echelon,
    kernel,
    lifted_product,
    matrix_digest,
    permute,
    remainder,
)
from ecdlp_ftqc.code_constructions.lp_protected_ghz import punctured_mask, restrict


def _validate_vector(vector: int, width: int, name: str) -> None:
    if type(vector) is not int or vector < 0 or vector.bit_length() > width:
        raise ValueError(f"{name} must be a nonnegative {width}-bit integer")


def _xor_selected(rows: tuple[int, ...], selector: int) -> int:
    result = 0
    for index in bits(selector):
        result ^= rows[index]
    return result


def _solve_columns(
    rows: tuple[int, ...], rhs: tuple[int, ...], width: int, count: int
) -> tuple[int, ...]:
    """Solve several exact GF(2) systems together, with all free variables zero.

    Each rhs row packs ``count`` right-hand sides. Inconsistency fails closed.
    This supplies convenient Pauli representatives, not low-weight corrections.
    """
    if len(rows) != len(rhs) or width < 0 or count < 0:
        raise ValueError("Invalid simultaneous binary systems")
    basis: dict[int, tuple[int, int]] = {}
    for original, original_rhs in zip(rows, rhs, strict=True):
        _validate_vector(original, width, "System row")
        _validate_vector(original_rhs, count, "Right-hand side")
        row, value = original, original_rhs
        while row:
            pivot = row.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = row, value
                break
            other, other_rhs = basis[pivot]
            row ^= other
            value ^= other_rhs
        if not row and value:
            raise ValueError("Inconsistent simultaneous binary systems")
    coordinate_values = [0] * width
    for pivot in sorted(basis):
        row, value = basis[pivot]
        for coordinate in bits(row ^ (1 << pivot)):
            value ^= coordinate_values[coordinate]
        coordinate_values[pivot] = value
    result = [0] * count
    for coordinate, value in enumerate(coordinate_values):
        for index in bits(value):
            result[index] |= 1 << coordinate
    return tuple(result)


@dataclass(frozen=True)
class DirectGHZCertificate:
    """Explicit linear decoder and Pauli frame for an ideal mask readout.

    ``measured_z`` starts with 12*lift unwanted canonical Zs, followed by
    canonical-central residual Zs. ``correction_x`` is its symplectic dual
    inside Q's X normalizers. The measurement results may be arbitrary; raw
    ideal readouts must obey M's Z checks. No noisy-readout decoder is implied.
    """

    lift: int
    output_code: CSSCode
    mask_code: CSSCode
    coordinates: tuple[int, ...]
    canonical_x: tuple[int, ...]
    canonical_z: tuple[int, ...]
    measured_z: tuple[int, ...]
    readout_sign_rows: tuple[int, ...]
    correction_x: tuple[int, ...]
    retained_x: tuple[int, ...]
    residual_z: tuple[int, ...]
    permutation: tuple[int, ...]
    ghz_x: tuple[int, ...]
    ghz_z: tuple[int, ...]
    raw_ghz_sign_rows: tuple[int, ...]

    def decode_readout(self, readout: int) -> int:
        """Return all logical Z signs; reject an invalid *ideal* raw readout."""
        _validate_vector(readout, self.mask_code.n, "Mask readout")
        if apply_rows(self.mask_code.hz, readout):
            raise ValueError("Mask readout violates ideal Z checks; noisy decoding is OPEN")
        return apply_rows(self.readout_sign_rows, readout)

    def frame_from_outcomes(self, outcomes: int, *, after_automorphism: bool = False) -> int:
        """Pack an X Pauli frame; optionally propagate it through the permutation."""
        _validate_vector(outcomes, len(self.measured_z), "Logical outcomes")
        frame = _xor_selected(self.correction_x, outcomes)
        return permute(frame, self.permutation) if after_automorphism else frame

    def frame_from_readout(self, readout: int, *, after_automorphism: bool = False) -> int:
        """Decode an ideal physical readout and return the associated X frame."""
        return self.frame_from_outcomes(
            self.decode_readout(readout), after_automorphism=after_automorphism
        )


@lru_cache(maxsize=2)
def build_direct_certificate(lift: int = 75) -> DirectGHZCertificate:
    """Construct the complete measured basis and physical dual corrections.

    The mask normalizer quotient is explicitly completed after the desired
    canonical Z basis. Centering the extra generators against all canonical
    Xs exhibits an independent residual sector, rather than inferring that
    sector is harmless solely from a dimension subtraction.
    """
    if type(lift) is not int or lift <= 0 or lift % 2 == 0:
        raise ValueError("An odd positive integer lift is required")
    output = lifted_product(completed_seed(lift), base_seed(lift).adjoint())
    mask, coordinates = punctured_mask(lift)
    xs, zs = canonical_logicals(lift)
    unwanted = zs[: 12 * lift]
    measured_rank = mask.n - len(echelon(mask.hx)) - len(echelon(mask.hz))
    wanted_residual = measured_rank - len(unwanted)
    if wanted_residual < 0:
        raise ValueError("Mask cannot contain the claimed canonical measured space")
    basis = echelon(output.hz + unwanted)
    residual: list[int] = []
    for vector in kernel(mask.hx, mask.n):
        embedded = permute(vector, coordinates)
        reduced = remainder(embedded, basis)
        if not reduced:
            continue
        centered = embedded ^ _xor_selected(zs, apply_rows(xs, embedded))
        # The centering removes only unwanted canonical Zs: the selected Xs
        # live on the omitted strip and therefore cannot pair with this image.
        if (apply_rows(xs, centered)
                or permute(restrict(centered, coordinates), coordinates) != centered):
            raise ValueError("Residual centralization failed")
        residual.append(centered)
        basis[reduced.bit_length() - 1] = reduced
        if len(residual) == wanted_residual:
            break
    if len(residual) != wanted_residual:
        raise ValueError("Could not complete the entire mask logical Z space")
    residual_z = tuple(residual)
    constraints = output.hz + zs + residual_z
    rhs = (0,) * (len(output.hz) + len(zs)) + tuple(1 << i for i in range(len(residual_z)))
    residual_duals = _solve_columns(constraints, rhs, output.n, len(residual_z))
    measured = unwanted + residual_z
    duals = xs[: 12 * lift] + residual_duals
    start = 42 * lift
    omega = (1 << lift) - 1
    residual_x = (
        (omega | (omega << lift)) << start,
        (omega | (omega << (4 * lift))) << start,
    )
    ghz_x = tuple(
        xs[j] ^ xs[4 * lift + j] ^ xs[8 * lift + j] ^ xs[12 * lift + j]
        for j in range(4 * lift)
    )
    ghz_z = tuple(zs[i * 4 * lift + j] ^ zs[12 * lift + j]
                  for i in range(3) for j in range(4 * lift))
    readout_rows = tuple(restrict(z, coordinates) for z in measured)
    # g^T sends the first three input Zs to ZZZZ, IZIZ and IIZZ.
    # Consequently the conventional output ZZ(0,3) sign is m0 xor m1 xor m2.
    ghz_sign_rows = tuple(
        readout_rows[j] ^ readout_rows[4 * lift + j] ^ readout_rows[8 * lift + j]
        for j in range(4 * lift)
    ) + readout_rows[4 * lift : 12 * lift]
    return DirectGHZCertificate(
        lift, output, mask, coordinates, xs, zs, measured, readout_rows, duals,
        xs[12 * lift :] + residual_x, residual_z, automorphism_permutation(lift),
        ghz_x, ghz_z, ghz_sign_rows,
    )


def audit_direct_instance(lift: int = 75) -> dict[str, Any]:
    """Numerically certify every ideal outcome using linear generator identities.

    Pairing identities prove the frame rule for 2**938 logical outcomes of
    the fixed instance. They are not a sample of 938 branches. The gauge
    quotient checks cover every allowed physical readout as well.
    """
    c = build_direct_certificate(lift)
    q, m = c.output_code, c.mask_code
    bx, bz = echelon(q.hx), echelon(q.hz)
    mx, mz = echelon(m.hx), echelon(m.hz)
    post_z = echelon(q.hz + tuple(permute(z, c.permutation) for z in c.measured_z))
    post_x = echelon(q.hx + tuple(permute(x, c.permutation) for x in c.retained_x))
    residual_x = c.retained_x[4 * lift :]
    qx_set, qz_set = set(q.hx), set(q.hz)
    raw_readout_representatives = tuple(restrict(x, c.coordinates) for x in c.correction_x)
    checks = {
        "measured_z_not_normalizer": sum(bool(apply_rows(q.hx, z)) for z in c.measured_z),
        "measured_z_not_fully_supported": sum(
            permute(r, c.coordinates) != z
            for r, z in zip(c.readout_sign_rows, c.measured_z, strict=True)
        ),
        "readout_gauge_failures": sum(bool(apply_rows(m.hx, z)) for z in c.readout_sign_rows),
        "correction_not_normalizer": sum(bool(apply_rows(q.hz, x)) for x in c.correction_x),
        "correction_pairing_failures": sum(
            apply_rows(c.measured_z, x) != 1 << i for i, x in enumerate(c.correction_x)
        ),
        "outcome_representative_not_valid_readout": sum(
            bool(apply_rows(m.hz, r)) for r in raw_readout_representatives
        ),
        "physical_readout_decoder_pairing_failures": sum(
            apply_rows(c.readout_sign_rows, r) != 1 << i
            for i, r in enumerate(raw_readout_representatives)
        ),
        "residual_z_canonical_pairing_failures": sum(
            bool(apply_rows(c.canonical_x, z)) for z in c.residual_z
        ),
        "residual_x_canonical_pairing_failures": sum(
            bool(apply_rows(c.canonical_z, x)) for x in residual_x
        ),
        "retained_x_not_normalizer": sum(bool(apply_rows(q.hz, x)) for x in c.retained_x),
        "retained_x_measured_z_pairings": sum(
            bool(apply_rows(c.measured_z, x)) for x in c.retained_x
        ),
        "retained_x_rank_defect": len(c.retained_x)
        - (len(echelon(q.hx + c.retained_x)) - len(bx)),
        "complete_pure_output_stabilizer_defect": q.n - len(bx) - len(bz)
        - len(c.measured_z) - len(c.retained_x),
        "automorphism_x_check_failures": sum(
            permute(x, c.permutation) not in qx_set for x in q.hx
        ),
        "automorphism_z_check_failures": sum(
            permute(z, c.permutation) not in qz_set for z in q.hz
        ),
        "ghz_x_stabilizer_failures": sum(bool(remainder(x, post_x)) for x in c.ghz_x),
        "ghz_z_stabilizer_failures": sum(bool(remainder(z, post_z)) for z in c.ghz_z),
        "ghz_x_rank_defect": len(c.ghz_x) - (len(echelon(q.hx + c.ghz_x)) - len(bx)),
        "ghz_z_rank_defect": len(c.ghz_z) - (len(echelon(q.hz + c.ghz_z)) - len(bz)),
        "post_residual_z_canonical_pairing_failures": sum(
            bool(apply_rows(c.canonical_x, permute(z, c.permutation))) for z in c.residual_z
        ),
        "post_residual_x_canonical_pairing_failures": sum(
            bool(apply_rows(c.canonical_z, permute(x, c.permutation))) for x in residual_x
        ),
        "post_frame_signed_ghz_failures": sum(
            apply_rows(c.ghz_z, permute(x, c.permutation)) != apply_rows(c.raw_ghz_sign_rows, r)
            for x, r in zip(c.correction_x, raw_readout_representatives, strict=True)
        ),
        "complete_readout_gauge_dimension_defect":
            m.n - len(mz) - len(c.measured_z) - len(mx),
    }
    if any(checks.values()):
        raise ValueError(f"Direct LP GHZ certificate failed: {checks}")
    # Omitting all mask frames leaves exactly the 900 independent canonical
    # GHZ signs random. Residual-only outcomes never alter canonical signs.
    missing_frame_bad_generators = sum(
        bool(apply_rows(c.raw_ghz_sign_rows, r)) for r in raw_readout_representatives
    )
    no_auto_x = echelon(q.hx + c.retained_x)
    no_auto_z = echelon(q.hz + c.measured_z)
    return {
        "schema": "lp-direct-ghz-certificate-v1",
        "task_id": "T-20261001-006",
        "evidence": "NUMERICAL",
        "lift": lift,
        "checks": checks,
        "output": {
            "physical_carriers": q.n,
            "logical_qubits": q.n - len(bx) - len(bz),
            "canonical_logical_qubits": len(c.canonical_x),
            "ghz4_count": len(c.ghz_x),
            "verified_canonical_ghz_stabilizers": len(c.ghz_x) + len(c.ghz_z),
            "residual_z_fixed": len(c.residual_z),
            "residual_x_retained": len(residual_x),
            "canonical_residual_factorization": True,
            "preserves_arbitrary_residual_input": False,
        },
        "readout_map": {
            "physical_Z_readout_bits": m.n,
            "allowed_ideal_readout_space_dimension": m.n - len(mz),
            "readout_gauge_dimension": len(mx),
            "independent_logical_outcome_bits": len(c.measured_z),
            "logical_outcome_count": f"2**{len(c.measured_z)}",
            "all_outcomes_covered_by": "exact dual pairing and readout-gauge quotient",
            "canonical_sign_bits": 12 * lift,
            "residual_sign_bits": len(c.residual_z),
            "logical_outcomes_uniform": True,
            "postselection_on_logical_outcomes": False,
            "noisy_readout_decoding": "OPEN",
            "measured_z_sha256": matrix_digest(c.measured_z, q.n),
            "readout_sign_rows_sha256": matrix_digest(c.readout_sign_rows, m.n),
            "physical_x_duals_sha256": matrix_digest(c.correction_x, q.n),
            "output_ghz_z_sign_map_sha256": matrix_digest(c.raw_ghz_sign_rows, m.n),
            "physical_x_dual_weight_min": min(x.bit_count() for x in c.correction_x),
            "physical_x_dual_weight_max": max(x.bit_count() for x in c.correction_x),
            "dual_weight_is_physical_correction_cost": False,
        },
        "negative_controls": {
            "omitted_frame_bad_outcome_generators": missing_frame_bad_generators,
            "omitted_frame_canonical_good_fraction": f"2**{-12 * lift}",
            "omitted_automorphism_missing_ghz_x_stabilizers": sum(
                bool(remainder(x, no_auto_x)) for x in c.ghz_x
            ),
            "omitted_automorphism_missing_ghz_z_stabilizers": sum(
                bool(remainder(z, no_auto_z)) for z in c.ghz_z
            ),
        },
        "admission": {
            "ideal_direct_state_preparation": True,
            "general_arbitrary_data_measurement_equivalence": False,
            "complete_known_pauli_frame_required": True,
            "fault_tolerant_factory": False,
            "native_runtime_seconds": None,
            "logical_failure_probability": None,
        },
    }
