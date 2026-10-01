from __future__ import annotations

import json
import random
from itertools import combinations
from typing import Any

import pytest

from ecdlp_ftqc.verification.lp_protected_ghz import audit_low_weight


def _span(rows: tuple[int, ...]) -> set[int]:
    values = {0}
    for row in rows:
        values |= {value ^ row for value in values}
    return values


def _brute_force(
    n: int, syndrome_rows: tuple[int, ...], stabilizer_rows: tuple[int, ...], weight: int
) -> dict[str, int]:
    stabilizers = _span(stabilizer_rows)
    undetected = stabilizer = logical = 0
    for coordinates in combinations(range(n), weight):
        error = sum(1 << coordinate for coordinate in coordinates)
        if any((error & row).bit_count() % 2 for row in syndrome_rows):
            continue
        undetected += 1
        if error in stabilizers:
            stabilizer += 1
        else:
            logical += 1
    return {
        "undetected_errors": undetected,
        "stabilizer_errors": stabilizer,
        "logical_errors": logical,
    }


def _check_witnesses(
    report: dict[str, Any], syndrome_rows: tuple[int, ...], stabilizer_rows: tuple[int, ...]
) -> None:
    stabilizers = _span(stabilizer_rows)
    for weight in (1, 2):
        item = report[f"weight_{weight}"]
        witness = item["logical_witness_support_zero_based"]
        assert (witness is not None) == bool(item["logical_errors"])
        if witness is not None:
            assert len(witness) == weight
            assert len(set(witness)) == weight
            error = sum(1 << coordinate for coordinate in witness)
            assert not any((error & row).bit_count() % 2 for row in syndrome_rows)
            assert error not in stabilizers


def test_steane_certifies_lower_bound_but_not_full_distance() -> None:
    checks = (0b1010101, 0b1100110, 0b1111000)
    report = audit_low_weight(7, checks, checks)
    assert report["both_distances_at_least_3_certified"]
    for axis in ("X", "Z"):
        assert report[axis]["certified_distance_lower_bound"] == 3
        assert report[axis]["logical_witness_upper_bound"] is None
        assert report[axis]["weight_1"]["undetected_errors"] == 0
        assert report[axis]["weight_2"]["undetected_errors"] == 0
    assert not report["full_distance_computed"]
    assert not report["circuit_fault_tolerance_certified"]
    assert json.loads(json.dumps(report, sort_keys=True)) == report


def test_z_only_repetition_rejects_single_phase_errors() -> None:
    report = audit_low_weight(3, (), (0b011, 0b110))
    assert report["X"]["certified_distance_lower_bound"] == 3
    assert report["Z"]["certified_distance_lower_bound"] == 1
    assert report["Z"]["weight_1"]["logical_errors"] == 3
    assert report["Z"]["weight_2"]["undetected_errors"] == 3
    assert report["Z"]["weight_2"]["stabilizer_errors"] == 3
    assert report["Z"]["weight_2"]["logical_errors"] == 0
    assert not report["both_distances_at_least_3_certified"]


def test_weight_two_stabilizers_are_not_mistaken_for_logicals() -> None:
    report = audit_low_weight(4, (0b1111,), (0b1111,))
    for axis in ("X", "Z"):
        assert report[axis]["certified_distance_lower_bound"] == 2
        assert report[axis]["weight_1"]["logical_errors"] == 0
        assert report[axis]["weight_2"]["logical_errors"] == 6
    bell = audit_low_weight(2, (0b11,), (0b11,))
    for axis in ("X", "Z"):
        assert bell[axis]["weight_2"]["undetected_errors"] == 1
        assert bell[axis]["weight_2"]["stabilizer_errors"] == 1
        assert bell[axis]["weight_2"]["logical_errors"] == 0
    assert bell["both_distances_at_least_3_certified"]


def test_redundant_checks_do_not_change_error_counts() -> None:
    hx, hz = (0b0011, 0b1100), (0b1111,)
    first = audit_low_weight(4, hx, hz)
    second = audit_low_weight(4, hx + (0, 0b1111, 0b0011), hz + (0, 0b1111))
    assert first["X"] == second["X"]
    assert first["Z"] == second["Z"]


def test_no_checks_counts_every_error_as_logical() -> None:
    report = audit_low_weight(10000, (), ())
    for axis in ("X", "Z"):
        assert report[axis]["weight_1"]["logical_errors"] == 10000
        assert report[axis]["weight_2"]["logical_errors"] == 49995000
        assert report[axis]["weight_2"]["logical_witness_support_zero_based"] == [0, 1]


@pytest.mark.parametrize("seed", range(20))
def test_exact_grouping_matches_exhaustive_small_css_codes(seed: int) -> None:
    rng = random.Random(seed)
    n = 8
    hx = tuple(rng.randrange(1 << n) for _ in range(3))
    z_kernel = [
        value for value in range(1 << n)
        if all((value & row).bit_count() % 2 == 0 for row in hx)
    ]
    hz = tuple(rng.choice(z_kernel) for _ in range(3))
    report = audit_low_weight(n, hx, hz)
    for axis, syndrome_rows, stabilizer_rows in (("X", hz, hx), ("Z", hx, hz)):
        for weight in (1, 2):
            expected = _brute_force(n, syndrome_rows, stabilizer_rows, weight)
            assert {key: report[axis][f"weight_{weight}"][key] for key in expected} == expected
        _check_witnesses(report[axis], syndrome_rows, stabilizer_rows)


@pytest.mark.parametrize("n", (0, -1, True, 1.5))
def test_invalid_dimensions_rejected(n: Any) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        audit_low_weight(n, (), ())


@pytest.mark.parametrize("rows", ((-1,), (8,), (1.0,), (True,), [1]))
def test_invalid_rows_rejected(rows: Any) -> None:
    with pytest.raises((ValueError, TypeError), match="hx"):
        audit_low_weight(3, rows, ())
    with pytest.raises((ValueError, TypeError), match="hz"):
        audit_low_weight(3, (), rows)


def test_anticommuting_checks_fail_closed() -> None:
    with pytest.raises(ValueError, match="do not commute"):
        audit_low_weight(2, (0b01,), (0b11,))


def test_single_qubit_boundary_distinguishes_logical_and_stabilizer() -> None:
    free = audit_low_weight(1, (), ())
    assert free["X"]["weight_1"]["logical_errors"] == 1
    assert free["Z"]["weight_2"]["total_physical_errors"] == 0
    fixed = audit_low_weight(1, (1,), ())
    assert fixed["X"]["weight_1"]["stabilizer_errors"] == 1
    assert fixed["X"]["weight_1"]["logical_errors"] == 0
    assert fixed["Z"]["weight_1"]["undetected_errors"] == 0
