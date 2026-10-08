"""Independent forward fault replay against the backward, idle-compressed audit."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Any

import pytest

from ecdlp_ftqc.analysis.lp_flag_preparation import (
    FlagCircuit,
    Operation,
    audit_single_faults,
    build_circuit,
    retry_bounds,
    structural_resources,
)
from ecdlp_ftqc.code_constructions.lp_ghz import (
    base_seed,
    completed_seed,
    lifted_product,
)
from ecdlp_ftqc.code_constructions.lp_protected_ghz import punctured_mask


@dataclass(frozen=True)
class _Fault:
    kind: str
    after_index: int
    tick: int
    x: int = 0
    z: int = 0
    read_flip: bool = False


def _physical_faults(circuit: FlagCircuit) -> tuple[list[_Fault], Counter[str]]:
    """Enumerate actual ticks, without using transfer maps or idle-gap counts."""
    faults: list[_Fault] = []
    locations: Counter[str] = Counter(idle_data=0, idle_syndrome=0, idle_flag=0)
    layers: dict[int, list[Operation]] = defaultdict(list)
    for index, op in enumerate(circuit.operations):
        layers[op.tick].append(op)
        locations[op.kind] += 1
        if op.kind.startswith("read_"):
            faults.append(_Fault(op.kind, index, op.tick, read_flip=True))
            continue
        for paulis in product(range(4), repeat=len(op.qubits)):
            if not any(paulis):
                continue
            x = sum((p & 1) << q for p, q in zip(paulis, op.qubits))
            z = sum((p >> 1) << q for p, q in zip(paulis, op.qubits))
            faults.append(_Fault(op.kind, index, op.tick, x, z))

    live: set[int] = set()
    for tick in range(circuit.ticks):
        layer = layers[tick]
        touched = [q for op in layer for q in op.qubits]
        assert len(set(touched)) == len(touched)
        for op in layer:
            if op.kind.startswith("prep_"):
                assert op.qubits[0] not in live
                live.add(op.qubits[0])
        assert set(touched) <= live
        for q in sorted(live - set(touched)):
            kind = "idle_data" if q < circuit.data_qubits else (
                "idle_syndrome" if (q - circuit.data_qubits) % 2 == 0 else "idle_flag"
            )
            locations[kind] += 1
            for x, z in ((1 << q, 0), (0, 1 << q), (1 << q, 1 << q)):
                faults.append(_Fault(kind, -1, tick, x, z))
        for op in layer:
            if op.kind.startswith("read_"):
                live.remove(op.qubits[0])
    assert live == set(range(circuit.data_qubits))
    return faults, locations


def _forward_effect(circuit: FlagCircuit, fault: _Fault) -> tuple[int, int, int, int, int]:
    """Propagate a physical Pauli chronologically; X circuits reverse each CNOT."""
    x = z = syndromes = flags = 0
    for index, op in enumerate(circuit.operations):
        if op.kind.startswith("prep_"):
            bit = 1 << op.qubits[0]
            x &= ~bit
            z &= ~bit
        elif op.kind == "cnot":
            control, target = op.qubits if circuit.axis == "Z" else op.qubits[::-1]
            if x & (1 << control):
                x ^= 1 << target
            if z & (1 << target):
                z ^= 1 << control
        else:
            q = op.qubits[0]
            read_z = (op.kind == "read_syndrome") == (circuit.axis == "Z")
            flip = ((x if read_z else z) >> q) & 1
            flip ^= int(fault.read_flip and index == fault.after_index)
            if op.kind == "read_syndrome":
                syndromes ^= flip << op.record
            else:
                flags ^= flip << op.record
            x &= ~(1 << q)
            z &= ~(1 << q)
        if not fault.read_flip and index == fault.after_index:
            x ^= fault.x
            z ^= fault.z
        last_in_tick = index + 1 == len(circuit.operations) or (
            circuit.operations[index + 1].tick != op.tick
        )
        if last_in_tick and fault.after_index == -1 and fault.tick == op.tick:
            x ^= fault.x
            z ^= fault.z
    mask = (1 << circuit.data_qubits) - 1
    x, z = x & mask, z & mask
    if circuit.axis == "X":
        x, z = z, x  # Only classification returns to the shared Z convention.
    m = len(circuit.checks)
    return x, z, syndromes & ((1 << m) - 1), syndromes >> m, flags


def _brute_classifier(circuit: FlagCircuit) -> Any:
    """Enumerate complete target stabilizers and preparation corrections at n<=4."""
    n = circuit.data_qubits
    row_space = {0}
    for row in circuit.checks:
        row_space |= {old ^ row for old in tuple(row_space)}
    corrections: dict[int, int] = {}
    kernel = set()
    for x in range(1 << n):
        syndrome = sum(((x & row).bit_count() % 2) << i
                       for i, row in enumerate(circuit.checks))
        corrections.setdefault(syndrome, x)
        if not syndrome:
            kernel.add(x)
    harmless = {(x, z) for x in kernel for z in row_space}
    allowed = set(harmless)
    for x, z in harmless:
        for q in range(n):
            allowed.update(((x ^ (1 << q), z), (x, z ^ (1 << q)),
                            (x ^ (1 << q), z ^ (1 << q))))

    def classify(effect: tuple[int, int, int, int, int]) -> str:
        x, z, first, second, flags = effect
        if flags:
            return "reject_flag"
        if first != second:
            return "reject_disagreement"
        if first not in corrections:
            return "reject_inconsistent"
        residual = (x ^ corrections[first], z)
        if residual in harmless:
            return "accept_target"
        return "accept_weight_one" if residual in allowed else "accept_bad"

    return classify


@pytest.mark.parametrize("axis", ["Z", "X"])
@pytest.mark.parametrize("checks,pool", [((15, 5, 10), 2), ((3, 6, 9), 2), ((15, 5, 10), 1)])
def test_every_small_physical_fault_matches_independent_forward_replay(
    checks: tuple[int, ...], pool: int, axis: str,
) -> None:
    circuit = build_circuit(checks, 4, axis, pool)
    faults, locations = _physical_faults(circuit)
    classify = _brute_classifier(circuit)
    outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    for fault in faults:
        outcomes[fault.kind][classify(_forward_effect(circuit, fault))] += 1
    actual = audit_single_faults(circuit)
    assert actual["total_locations"] == sum(locations.values())
    assert actual["total_pauli_fault_cases"] == len(faults)
    assert set(actual["fault_classes"]) == set(locations)
    for kind, count in locations.items():
        row = actual["fault_classes"][kind]
        assert row["locations"] == count
        assert row["outcomes"] == dict(outcomes[kind])
        rejected = sum(value for key, value in outcomes[kind].items()
                       if key.startswith("reject_"))
        assert Fraction(row["linear_rejection_coefficient"]) == Fraction(
            rejected, row["paulis_per_location"]
        )
    assert actual["single_fault_residual_weight_at_most_one"]
    assert actual["first_accepted_counterexample"] is None
    # The third check is dependent in the first example: 15 xor 5 = 10.
    assert actual["ideal_independent_sign_bits"] == (2 if checks[0] == 15 else 3)


def test_brute_target_classifier_distinguishes_records_and_cosets() -> None:
    classify = _brute_classifier(build_circuit((15, 5, 10), 4, "Z", 2))
    assert classify((0, 0, 0, 0, 1)) == "reject_flag"
    assert classify((0, 0, 1, 0, 0)) == "reject_disagreement"
    assert classify((0, 0, 1, 1, 0)) == "reject_inconsistent"
    assert classify((0, 15, 0, 0, 0)) == "accept_target"
    assert classify((0, 1, 0, 0, 0)) == "accept_weight_one"
    assert classify((0, 3, 0, 0, 0)) == "accept_bad"


def test_explicit_idle_lifetimes_include_read_boundary_but_not_inactive_pool() -> None:
    circuit = build_circuit((15, 5, 10), 4, "Z", 2)
    faults, counts = _physical_faults(circuit)
    assert circuit.batches_per_pass == 2
    assert circuit.ticks == 29
    assert counts["idle_data"] == 96
    assert counts["idle_syndrome"] == 4
    assert counts["idle_flag"] == 20
    assert not any(f.kind.startswith("idle_") and f.tick == 0 for f in faults)
    last_idles = [f for f in faults if f.tick == circuit.ticks - 1 and f.kind == "idle_data"]
    assert len(last_idles) == 3 * circuit.data_qubits
    assert all(f.tick < circuit.ticks for f in faults)


@pytest.mark.parametrize(
    "checks,n,axis,pool",
    [((), 1, "Z", 1), ((0,), 1, "X", 1), ((4,), 2, "Z", 1),
     ((1,), 0, "Z", 1), ((1,), 1, "Y", 1), ((1,), 1, "z", 1),
     ((1,), 1, "X", 0), ((1,), 1, "Z", True), ((True,), 1, "Z", 1)],
)
def test_circuit_rejects_invalid_inputs(
    checks: tuple[int, ...], n: int, axis: str, pool: int,
) -> None:
    with pytest.raises(ValueError):
        build_circuit(checks, n, axis, pool)


def test_primary_full_instance_resources_without_repeating_fault_audit() -> None:
    q = lifted_product(completed_seed(75), base_seed(75).adjoint())
    m, _ = punctured_mask(75)
    resources = [structural_resources(build_circuit(rows, code.n, axis, 64))
                 for code, rows, axis in ((q, q.hz, "Z"), (m, m.hx, "X"))]
    qs, ms = resources
    assert (qs["abstract_ticks"], ms["abstract_ticks"]) == (1571, 2131)
    assert (qs["batches_per_pass"], ms["batches_per_pass"]) == (50, 83)
    assert (qs["data_cnot_layers_per_pass"], ms["data_cnot_layers_per_pass"]) == (585, 733)
    assert (qs["operation_counts"]["cnot"], ms["operation_counts"]["cnot"]) == (81900, 106050)
    assert sum(row["qubit_peak"] for row in resources) == 18931
    assert sum(row["operation_counts"]["read_flag"] for row in resources) == 16800
    assert all(row["native_seconds"] is None and row["qec_cycles"] is None for row in resources)


def test_retry_bound_exact_endpoints_and_separate_block_scope() -> None:
    bounds = retry_bounds(3, (0.0, 0.25, 0.5))
    assert bounds["flag_readouts_per_attempt"] == 6
    rows = bounds["independent_flag_readout_only_acceptance_upper_bounds"]
    assert [row["acceptance_upper_bound"] for row in rows] == [1.0, 0.75**6, 1 / 64]
    assert bounds["finite_p_acceptance_estimate"] is None
    assert "Do not multiply" in bounds["separate_retries"]


@pytest.mark.parametrize("count,rates", [(0, (0.1,)), (True, (0.1,)), (1, (-0.1,)),
                                        (1, (0.51,)), (1, (float("nan"),)), (1, (True,))])
def test_retry_bound_rejects_invalid_inputs(count: int, rates: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        retry_bounds(count, rates)
