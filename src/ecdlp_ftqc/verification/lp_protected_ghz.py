"""Independent, complete weight-one/two audit of a binary CSS code.

No construction module is imported.  Columns of the opposite-type check matrix
are error syndromes.  An undetected pair has equal columns; it is a stabilizer
exactly when its two unit vectors have equal remainders modulo the same-type
stabilizer row space.  Grouping both signatures counts every pair without a
quadratic pair scan.  This is a code-capacity algebraic check, not a preparation,
measurement-circuit, decoder, or fault-tolerance certificate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _validate_matrix(n: int, rows: tuple[int, ...], name: str) -> None:
    if not isinstance(rows, tuple):
        raise TypeError(f"{name} must be a tuple of binary integer rows")
    for row in rows:
        if type(row) is not int or row < 0 or row.bit_length() > n:
            raise ValueError(f"{name} contains an invalid {n}-column binary row")


def _columns(n: int, rows: tuple[int, ...]) -> list[int]:
    result = [0] * n
    for row_index, original in enumerate(rows):
        row = original
        row_bit = 1 << row_index
        while row:
            bit = row & -row
            result[bit.bit_length() - 1] |= row_bit
            row ^= bit
    return result


def _stabilizer_basis(rows: tuple[int, ...]) -> dict[int, int]:
    pivots: dict[int, int] = {}
    for row in rows:
        while row:
            column = row.bit_length() - 1
            pivot = pivots.get(column)
            if pivot is None:
                pivots[column] = row
                break
            row ^= pivot
    return pivots


def _coset_signature(coordinate: int, pivots: dict[int, int]) -> int:
    """Canonical remainder of one unit vector modulo a triangular row basis."""
    remaining = 1 << coordinate
    signature = 0
    while remaining:
        column = remaining.bit_length() - 1
        pivot = pivots.get(column)
        if pivot is None:
            bit = 1 << column
            signature |= bit
            remaining ^= bit
        else:
            remaining ^= pivot
    return signature


def _pair_count(size: int) -> int:
    return size * (size - 1) // 2


def _audit_axis(
    n: int, syndromes: list[int], stabilizers: tuple[int, ...]
) -> dict[str, Any]:
    groups: dict[int, list[int]] = defaultdict(list)
    for coordinate, syndrome in enumerate(syndromes):
        groups[syndrome].append(coordinate)
    candidates = {
        syndrome: coordinates
        for syndrome, coordinates in groups.items()
        if syndrome == 0 or len(coordinates) > 1
    }
    pivots = _stabilizer_basis(stabilizers) if candidates else {}
    single_undetected = len(groups.get(0, ()))
    single_stabilizer = 0
    pair_undetected = 0
    pair_stabilizer = 0
    single_witness: list[int] | None = None
    pair_witness: list[int] | None = None
    for syndrome, coordinates in candidates.items():
        signatures = [_coset_signature(coordinate, pivots) for coordinate in coordinates]
        counts = Counter(signatures)
        pair_undetected += _pair_count(len(coordinates))
        pair_stabilizer += sum(_pair_count(count) for count in counts.values())
        if syndrome == 0:
            single_stabilizer = counts.get(0, 0)
            single_witness = next(
                ([coordinate] for coordinate, signature in zip(coordinates, signatures, strict=True)
                 if signature),
                None,
            )
        if pair_witness is None and len(counts) > 1:
            second = next(
                coordinate for coordinate, signature in zip(coordinates, signatures, strict=True)
                if signature != signatures[0]
            )
            pair_witness = [coordinates[0], second]
    single_logical = single_undetected - single_stabilizer
    pair_logical = pair_undetected - pair_stabilizer
    minimum_found = 1 if single_logical else 2 if pair_logical else None
    return {
        "weight_1": {
            "total_physical_errors": n,
            "undetected_errors": single_undetected,
            "stabilizer_errors": single_stabilizer,
            "logical_errors": single_logical,
            "logical_witness_support_zero_based": single_witness,
        },
        "weight_2": {
            "total_physical_errors": _pair_count(n),
            "undetected_errors": pair_undetected,
            "stabilizer_errors": pair_stabilizer,
            "logical_errors": pair_logical,
            "logical_witness_support_zero_based": pair_witness,
        },
        "no_nontrivial_logical_through_weight_2": minimum_found is None,
        "certified_distance_lower_bound": minimum_found if minimum_found is not None else 3,
        "logical_witness_upper_bound": minimum_found,
        "syndrome_column_classes": len(groups),
    }


def audit_low_weight(n: int, hx: tuple[int, ...], hz: tuple[int, ...]) -> dict[str, Any]:
    """Count all pure-X/pure-Z logical errors of weights one and two exactly.

    ``hx`` and ``hz`` are nonnegative integer rows with bit ``i`` denoting qubit
    ``i``.  Redundant and zero rows are permitted.  Invalid dimensions, noninteger
    rows, and anticommuting CSS checks are rejected.  Counts are physical Pauli
    supports, NOT counts of distinct logical cosets.  Each witness uses zero-based
    qubit indices.  A lower bound of three means only that the complete search
    through weight two is empty; it makes no claim about errors of larger weight.
    For a zero-logical-qubit code this empty-search statement remains valid, but
    should not be interpreted as a finite code distance.

    For CSS codes, absence of pure-X and pure-Z logicals through weight two also
    excludes mixed logicals through weight two: a nontrivial CSS logical Pauli
    has at least one nontrivial pure component of no larger support.
    """
    if type(n) is not int or n <= 0:
        raise ValueError("n must be a positive integer")
    _validate_matrix(n, hx, "hx")
    _validate_matrix(n, hz, "hz")
    x_error_syndromes = _columns(n, hz)
    z_error_syndromes = _columns(n, hx)
    for original in hx:
        syndrome = 0
        row = original
        while row:
            bit = row & -row
            syndrome ^= x_error_syndromes[bit.bit_length() - 1]
            row ^= bit
        if syndrome:
            raise ValueError("hx and hz do not commute")
    x_report = _audit_axis(n, x_error_syndromes, hx)
    z_report = _audit_axis(n, z_error_syndromes, hz)
    return {
        "evidence": "NUMERICAL",
        "method": "complete zero/equal syndrome columns and stabilizer cosets",
        "physical_qubits": n,
        "supplied_x_checks": len(hx),
        "supplied_z_checks": len(hz),
        "css_commutation_verified": True,
        "maximum_error_weight_checked": 2,
        "X": x_report,
        "Z": z_report,
        "both_distances_at_least_3_certified": (
            x_report["no_nontrivial_logical_through_weight_2"]
            and z_report["no_nontrivial_logical_through_weight_2"]
        ),
        "full_distance_computed": False,
        "circuit_fault_tolerance_certified": False,
    }
