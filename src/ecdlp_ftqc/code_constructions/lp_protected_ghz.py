"""Finite, ideal two-stage LP masking certificate; not a native FT factory.

The mask punctures a column of the first seed and is a *target* of CNOT.
Its Z readout prepares a mixed full-size auxiliary; that auxiliary controls
the subsequent X measurement. All ranks use the full binary lifted matrices.
"""

from __future__ import annotations

from typing import Any

from ecdlp_ftqc.code_constructions.lp_ghz import (
    INFORMATION,
    CSSCode,
    RingMatrix,
    apply_rows,
    base_seed,
    canonical_logicals,
    completed_seed,
    echelon,
    homomorphic_css_failures,
    lifted_product,
    matrix_digest,
    permute,
    remainder,
    transpose,
)
from ecdlp_ftqc.verification.lp_protected_ghz import audit_low_weight


def restrict(vector: int, coordinates: tuple[int, ...]) -> int:
    """Restrict a nonnegative support to a validated coordinate list."""
    if vector < 0 or any(i < 0 for i in coordinates) or len(set(coordinates)) != len(coordinates):
        raise ValueError("Invalid restriction")
    return sum(((vector >> p) & 1) << j for j, p in enumerate(coordinates))


def punctured_mask(lift: int = 75, selected_row: int = 3) -> tuple[CSSCode, tuple[int, ...]]:
    """Return the Z-mask and its injection into Q_one coordinates.

    selected_row is zero-based in the four canonical first-factor labels.
    All second-summand coordinates are retained. The physical gate is Q->mask,
    not mask->Q; exchanging this direction is an intentional negative control.
    """
    if selected_row not in range(4):
        raise ValueError("Selected canonical row must be in range(4)")
    first = completed_seed(lift)
    excluded = INFORMATION[selected_row]
    kept = tuple(p for p in range(14) if p != excluded)
    reduced = RingMatrix(lift, tuple(tuple(row[p] for p in kept) for row in first.rows))
    mask = lifted_product(reduced, base_seed(lift).adjoint())
    coordinates = tuple((p * 7 + k) * lift + a for p in kept for k in range(7) for a in range(lift))
    coordinates += tuple(range(98 * lift, 128 * lift))
    return mask, coordinates


def code_statistics(code: CSSCode) -> dict[str, Any]:
    result: dict[str, Any] = {"physical_qubits": code.n}
    for name, rows in (("hx", code.hx), ("hz", code.hz)):
        columns = transpose(rows, code.n)
        result[name] = {
            "rows": len(rows),
            "rank": len(echelon(rows)),
            "edges": sum(row.bit_count() for row in rows),
            "max_row_weight": max((row.bit_count() for row in rows), default=0),
            "max_column_degree": max((col.bit_count() for col in columns), default=0),
            "sha256": matrix_digest(rows, code.n),
        }
    result["logical_qubits"] = code.n - result["hx"]["rank"] - result["hz"]["rank"]
    return result


def audit_masked_instance(lift: int = 75) -> dict[str, Any]:
    """Audit the complete measured algebra without expanding a dense kernel.

    If S is retained and R removed, zero-extension of ker(HX_mask) is exactly
    ker(HX_Q) intersect vectors supported on S. The stabilizers in this space
    have dimension rank(HZ_Q)-rank(HZ_Q restricted to R). Equality with the
    embedded mask Z-stabilizer rank certifies injectivity on Z homology.
    A containment plus dimension argument then certifies the ENTIRE final
    X measurement space, rather than checking only 300 desired generators.
    """
    data = lifted_product(completed_seed(lift), base_seed(lift).adjoint())
    mask, coordinates = punctured_mask(lift)
    start = INFORMATION[3] * 7 * lift
    removed = tuple(range(start, start + 7 * lift))
    # The retained positions omit one contiguous first-summand strip.
    low = (1 << start) - 1

    def compact(row: int) -> int:
        return (row & low) | ((row >> (start + 7 * lift)) << start)

    def strip(row: int) -> int:
        return (row >> start) & ((1 << (7 * lift)) - 1)

    data_stats, mask_stats = code_statistics(data), code_statistics(mask)
    bx, bz = echelon(data.hx), echelon(data.hz)
    xs, zs = canonical_logicals(lift)
    selected = xs[12 * lift :]
    unwanted_z = zs[: 12 * lift]
    # These are the same two seed residuals audited in T-20261001-001.
    omega = (1 << lift) - 1
    residual_x = ((omega | (omega << lift)) << start, (omega | (omega << (4 * lift))) << start)
    final_x = selected + residual_x
    embedded_hz = tuple(permute(row, coordinates) for row in mask.hz)
    rank_restricted_hz = len(echelon(tuple(strip(row) for row in data.hz)))
    supported_z_stabilizer_rank = len(bz) - rank_restricted_hz
    supported_z_normalizer_rank = mask.n - mask_stats["hx"]["rank"]
    measured_z_rank = supported_z_normalizer_rank - supported_z_stabilizer_rank
    effective_k = data_stats["logical_qubits"] - measured_z_rank
    final_x_rank = len(echelon(data.hx + final_x)) - len(bx)
    # CSS duality reuses the approved inclusion checker in the correct direction.
    mask_inclusions = homomorphic_css_failures(
        CSSCode(data.n, data.hz, data.hx), CSSCode(mask.n, mask.hz, mask.hx), coordinates
    )
    wrong_direction = homomorphic_css_failures(data, mask, coordinates)
    checks = {
        "mask_x_equals_restricted_data_x": int(mask.hx != tuple(compact(row) for row in data.hx)),
        "embedded_mask_z_stabilizer_failures": sum(bool(remainder(z, bz)) for z in embedded_hz),
        "mask_z_homology_kernel_dimension": supported_z_stabilizer_rank - mask_stats["hz"]["rank"],
        "mask_cnot_z_inclusion_failures": mask_inclusions[0],
        "mask_cnot_x_inclusion_failures": mask_inclusions[1],
        "unwanted_canonical_z_not_supported": sum(bool(strip(z)) for z in unwanted_z),
        "unwanted_canonical_z_not_normalizer": sum(
            bool(apply_rows(data.hx, z)) for z in unwanted_z
        ),
        "unwanted_canonical_z_rank_defect": len(unwanted_z)
        - (len(echelon(data.hz + unwanted_z)) - len(bz)),
        "final_x_not_supported_on_removed_strip": sum(bool(compact(x)) for x in final_x),
        "final_x_not_normalizer": sum(bool(apply_rows(data.hz, x)) for x in final_x),
        "residual_x_canonical_pairing_failures": sum(bool(apply_rows(zs, x)) for x in residual_x),
        "final_x_rank_defect": len(final_x) - final_x_rank,
        "complete_final_x_space_dimension_defect": effective_k - final_x_rank,
        "unwanted_z_selected_x_pairings": sum(bool(apply_rows(unwanted_z, x)) for x in selected),
        "negative_control_wrong_cnot_direction_not_rejected": int(sum(wrong_direction) == 0),
    }
    if any(checks.values()):
        raise ValueError(f"Masked LP certificate failed: {checks}")
    data_distance = audit_low_weight(data.n, data.hx, data.hz)
    mask_distance = audit_low_weight(mask.n, mask.hx, mask.hz)
    return {
        "schema": "lp-protected-ghz-certificate-v1",
        "task_id": "T-20261001-004",
        "lift": lift,
        "evidence": "NUMERICAL",
        "data_and_full_auxiliary": data_stats,
        "mask": mask_stats,
        "checks": checks,
        "distance_audits": {"data_and_full_auxiliary": data_distance, "mask": mask_distance},
        "measured_algebra": {
            "removed_coordinates": {
                "first": removed[0],
                "last": removed[-1],
                "count": len(removed),
            },
            "mask_z_normalizer_dimension": supported_z_normalizer_rank,
            "data_z_restriction_rank": rank_restricted_hz,
            "supported_data_z_stabilizer_dimension": supported_z_stabilizer_rank,
            "mask_independent_z_measurements": measured_z_rank,
            "unwanted_canonical_z_fixed": len(unwanted_z),
            "additional_residual_z_fixed": measured_z_rank - len(unwanted_z),
            "effective_auxiliary_logical_qubits": effective_k,
            "final_independent_x_measurements": final_x_rank,
            "final_canonical_x_measurements": len(selected),
            "final_residual_x_measurements": len(residual_x),
            "final_x_basis_sha256": matrix_digest(final_x, data.n),
            "preserves_arbitrary_residual_state": False,
            "strict_300_without_residual_measurement": "OPEN",
        },
        "structural_cost": {
            "ghz4_outputs": 4 * lift,
            "mask_preparation_matching_cnots": mask.n,
            "data_measurement_matching_cnots": data.n,
            "total_interface_cnots": mask.n + data.n,
            "ordered_interface_matching_layers": 2,
            "max_interface_degree_per_stage": 1,
            "resource_preparation_peak_carriers_excluding_qec": mask.n + data.n,
            "online_data_plus_prepared_auxiliary_carriers_excluding_qec": 2 * data.n,
            "resident_data_plus_preparation_peak_carriers_excluding_qec": 2 * data.n + mask.n,
            "uniform_auxiliary_preparation": ["Q_one: all logical +", "mask: all logical 0"],
            "destructive_readout_qubits": {"mask_Z": mask.n, "auxiliary_X": data.n},
            "supplied_auxiliary_checks_not_a_ft_schedule": len(data.hx)
            + len(data.hz)
            + len(mask.hx)
            + len(mask.hz),
            "native_initialization_rounds": None,
            "native_runtime_seconds": None,
            "logical_failure_probability": None,
        },
        "inherited_distance_arguments": {
            "evidence": "PROVED",
            "effective_auxiliary": "HX unchanged; HZ enlarged by commuting logical Zs, hence dX_eff>=dX_Q and dZ_eff>=dZ_Q",
            "mask_Z_only": "weight-preserving injection on Z homology gives dZ_mask>=dZ_Q",
            "mask_X_relative_to_data": "OPEN; only the separately emitted finite low-weight certificate is admitted",
        },
        "negative_control": {"reversed_mask_cnot_inclusion_failures": list(wrong_direction)},
        "admission": {
            "ideal_two_stage_measurement": True,
            "signed_outcomes_require_x_frame_correction_or_propagation": True,
            "postselection_on_logical_outcomes": False,
            "fault_tolerant_factory": False,
            "native_speedup": False,
            "review_status": "PENDING",
        },
    }
