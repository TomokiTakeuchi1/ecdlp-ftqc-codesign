"""Finite schedule and explicit Pauli-propagation checks for the bare baseline."""

from collections import Counter
from itertools import combinations
from random import Random
from typing import Any

import pytest

from ecdlp_ftqc.analysis.lp_ghz_preparation import (
    audit_preparation,
    audit_weight_two_signature,
    conjugate_cnot,
    hook_suffix,
    schedule_checks,
)


def test_schedule_collision_free_and_ordered() -> None:
    rows = (0b1011, 0b1110, 0b1111, 0b0101)
    schedule = schedule_checks(rows, 4, 3)
    seen: dict[int, list[int]] = {row: [] for row in range(len(rows))}
    for batch in schedule.batches:
        for layer in batch:
            assert len({row for row, _ in layer}) == len(layer)
            assert len({q for _, q in layer}) == len(layer)
            for row, q in layer:
                seen[row].append(q)
    assert seen == {0: [0, 1, 3], 1: [1, 2, 3], 2: [0, 1, 2, 3], 3: [0, 2]}
    assert schedule.summary() == schedule_checks(rows, 4, 3).summary()
    serial = schedule_checks(rows, 4, 1)
    assert serial.cnot_layers == sum(row.bit_count() for row in rows)
    assert schedule.ancilla_pool == 3
    assert schedule.summary()["batches"] == 2


@pytest.mark.parametrize(
    "rows,n,pool",
    [((), 1, 1), ((0,), 1, 1), ((4,), 2, 1), ((1,), 1, 0), ((1,), 0, 1), ((1,), 1, True)],
)
def test_schedule_rejects_invalid(rows: tuple[int, ...], n: int, pool: int) -> None:
    with pytest.raises(ValueError):
        schedule_checks(rows, n, pool)


@pytest.mark.parametrize("axis", ["X", "Z"])
def test_hook_suffix_matches_explicit_cnot_propagation(axis: str) -> None:
    support = (0, 2, 3, 5)
    ancilla = 6
    for after in range(len(support) + 1):
        x, z = (1 << ancilla, 0) if axis == "X" else (0, 1 << ancilla)
        for q in support[after:]:
            control, target = (ancilla, q) if axis == "X" else (q, ancilla)
            x, z = conjugate_cnot(x, z, control, target, 7)
        expected = hook_suffix(support, after)
        assert (x & 63, z & 63) == ((expected, 0) if axis == "X" else (0, expected))
        # Spreading Pauli commutes with the basis in which ancilla is measured.
        assert ((z if axis == "X" else x) >> ancilla) & 1 == 0


def test_cnot_all_two_qubit_paulis_and_involution() -> None:
    # Independent local table: Xc -> Xc Xt, Zt -> Zc Zt.
    for x in range(4):
        for z in range(4):
            actual = conjugate_cnot(x, z, 0, 1, 2)
            assert actual == ((x & 1) | ((((x >> 1) ^ x) & 1) << 1), ((z ^ (z >> 1)) & 1) | (z & 2))
            assert conjugate_cnot(*actual, 0, 1, 2) == (x, z)


def test_interface_directions_for_audited_faults() -> None:
    assert conjugate_cnot(0, 1, 0, 1, 2) == (0, 1)  # Q Z stays Q.
    assert conjugate_cnot(2, 0, 0, 1, 2) == (2, 0)  # M X stays M.
    assert conjugate_cnot(0, 2, 0, 1, 2) == (0, 3)  # Negative orientation.


@pytest.mark.parametrize("support,after", [((0, 0), 1), ((-1,), 0), ((), 0), ((0,), 2)])
def test_hook_rejects_invalid(support: tuple[int, ...], after: int) -> None:
    with pytest.raises(ValueError):
        hook_suffix(support, after)


@pytest.mark.parametrize(
    "args", [(0, 0, 0, 0, 1), (0, 0, 0, 2, 2), (-1, 0, 0, 1, 2), (4, 0, 0, 1, 2)]
)
def test_pauli_rejects_invalid(args: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        conjugate_cnot(*args)


@pytest.fixture(scope="module")
def audit() -> dict[str, Any]:
    return audit_preparation()


def test_reviewed_instance_counts(audit: dict[str, Any]) -> None:
    resource = audit["structural_resources"]
    assert resource["output_code_carriers"] == 9600
    assert resource["mask_code_carriers"] == 9075
    assert resource["concurrent_code_carriers"] == 18675
    assert resource["explicit_baseline_peak_qubits"] == 18803
    assert resource["preparation_check_cnots"] == 77175
    assert resource["total_cnots_before_automorphism"] == 86250
    assert resource["interface_matching_layers"] == 1
    assert resource["destructive_output_readouts"] == 0
    assert audit["preparation"]["Q"]["cnot_count"] == 34650
    assert audit["preparation"]["M"]["cnot_count"] == 42525
    assert audit["preparation"]["Q"]["supplied_checks"] == 3150
    assert audit["preparation"]["M"]["supplied_checks"] == 5250
    sweep = audit["ancilla_pool_sensitivity"]
    assert [row["requested_ancillas_per_block"] for row in sweep] == [1, 64, 256, 5250]
    assert [row["actual_concurrent_syndrome_ancillas"] for row in sweep] == [2, 128, 512, 8400]
    assert sweep[0]["Q"]["cnot_layers"] == 34650
    assert sweep[0]["M"]["cnot_layers"] == 42525
    assert sweep[-1]["Q"]["batches"] == sweep[-1]["M"]["batches"] == 1
    correction = audit["preparation"]["preparation_sign_correction"]
    assert correction["single_qubit_parallel_layers_upper_bound"] == 1
    assert correction["physical_paulis_branch_dependent_count_upper_bound"] == 18675


def test_finite_fault_coverage_and_no_ft_admission(audit: dict[str, Any]) -> None:
    fault = audit["bounded_fault_diagnostic"]
    assert fault["total_enumerated_fault_events"] == 86250
    for name, count in (("Q_preparation_Z_hooks", 34650), ("M_preparation_X_hooks", 42525)):
        hook = fault[name]
        assert hook["fault_locations"] == count
        assert sum(hook["raw_data_support_weight_histogram"].values()) == count
        assert (
            hook["opposite_check_syndrome_zero"] + hook["opposite_check_syndrome_nonzero"] == count
        )
        assert hook["multi_support_diagnostic_witness"]["not_a_logical_failure_witness"]
    qhook = fault["Q_preparation_Z_hooks"]
    assert qhook["all_collected_preparation_and_mask_record_deltas_zero"]
    assert not qhook["opposite_check_syndrome_is_actual_record"]
    readout = fault["M_single_readout_bit_flips"]
    assert readout["nonzero_HZ_M_parity"] == readout["locations"] == 9075
    assert readout["distinct_HZ_M_syndrome_columns"] == 9075
    assert sum(Counter(readout["raw_canonical_mask_sign_flip_count_histogram"]).values()) == 9075
    assert not audit["admission"]["fault_tolerant_factory"]
    assert audit["symbolic_time"]["native_seconds"] is None
    assert audit["symbolic_time"]["qec_rounds"] is None
    obstruction = fault["record_blind_common_recovery_obstruction"]
    assert obstruction["evidence"] == "FALSIFIED"
    assert obstruction["fault_output_support_zero_based"] == [232, 342, 400, 478, 7350, 7613, 7873]
    assert obstruction["equivalent_prefix_support_zero_based"] == [0, 79, 152]
    assert obstruction["harmless_coset_minimum_weight"] == 3
    assert obstruction["no_common_record_conditioned_Pauli_recovery_under_stated_criterion"]
    signature = obstruction["signature_audit"]
    assert signature["covered_single_supports"] == 9600
    assert signature["covered_unordered_pair_supports"] == 46075200
    assert len(signature["signature_set_rows_zero_based"]) == 9


def test_signature_exclusion_matches_independent_brute_force() -> None:
    rng = Random(601006)
    for _ in range(30):
        n = rng.randrange(1, 8)
        rows = tuple(rng.randrange(1 << n) for _ in range(5))
        error = rng.randrange(1 << n)
        expected_signature = tuple((row & error).bit_count() % 2 for row in rows)
        matches = []
        for weight in range(3):
            for support in combinations(range(n), weight):
                candidate = sum(1 << q for q in support)
                if tuple((row & candidate).bit_count() % 2 for row in rows) == expected_signature:
                    matches.append(support)
        result = audit_weight_two_signature(n, rows, error)
        assert result["no_representative_of_weight_at_most_two"] == (not matches)


def test_signature_obstruction_negative_controls() -> None:
    rows = (1, 2, 4, 8)
    assert audit_weight_two_signature(4, rows, 7)["no_representative_of_weight_at_most_two"]
    assert not audit_weight_two_signature(4, rows, 3)["no_representative_of_weight_at_most_two"]
    assert not audit_weight_two_signature(4, rows, 1)["no_representative_of_weight_at_most_two"]
    assert not audit_weight_two_signature(4, rows, 0)["no_representative_of_weight_at_most_two"]
    # Removing a necessary observation lets the same weight-three error look weight two.
    assert not audit_weight_two_signature(4, rows[1:], 7)["no_representative_of_weight_at_most_two"]


@pytest.mark.parametrize("n,rows,error", [(0, (), 0), (2, (4,), 0), (2, (1,), 4), (2, (1,), -1)])
def test_signature_rejects_invalid(n: int, rows: tuple[int, ...], error: int) -> None:
    with pytest.raises(ValueError):
        audit_weight_two_signature(n, rows, error)


@pytest.mark.parametrize("caps", [(1, 1), (0,), (True,)])
def test_preparation_rejects_invalid_caps(caps: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        audit_preparation(ancilla_caps=caps)
