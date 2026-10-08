"""Exact single-Pauli audit of two-pass, postselected uniform CSS preparation.

All computation is in the Z-check / physical-plus convention. The X-check /
physical-zero circuit is its global H dual, including fault labels. No H gate
is inserted in either physical circuit. Backward Pauli maps retain actual
syndrome and flag records, and the COMPLETE uniform-state stabilizer quotient.
Idle positions between consecutive operations on a wire have identical maps;
their multiplicities are counted exactly, not sampled or omitted.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from ecdlp_ftqc.analysis.lp_ghz_preparation import schedule_checks
from ecdlp_ftqc.code_constructions.lp_ghz import bits, echelon, remainder, transpose


@dataclass(frozen=True)
class Operation:
    """An operation in a discrete, collision-free abstract time layer."""

    tick: int
    kind: str
    qubits: tuple[int, ...]
    record: int = -1


@dataclass(frozen=True)
class FlagCircuit:
    data_qubits: int
    checks: tuple[int, ...]
    axis: str
    pool: int
    operations: tuple[Operation, ...]
    ticks: int
    batches_per_pass: int
    data_cnot_layers_per_pass: int


def build_circuit(
    checks: tuple[int, ...], data_qubits: int, axis: str, pool: int = 64,
) -> FlagCircuit:
    """Bracket ALL data CNOTs with one flag pair, and repeat complete passes.

    Each batch: prepare (one tick), open flag (one), greedy data-CNOT layers,
    close flag (one), measure syndrome and flag (one). Pool pairs are inactive
    outside their batches. Reset is incorporated in each fresh preparation.
    Data are live from initial preparation to the final measurement boundary.
    """
    if axis not in ("Z", "X"):
        raise ValueError("Check axis must be Z or X")
    schedule = schedule_checks(checks, data_qubits, pool)
    operations = [Operation(0, "prep_data", (q,)) for q in range(data_qubits)]
    tick = 1
    for pass_index in range(2):
        for batch in schedule.batches:
            rows = sorted({row for layer in batch for row, _ in layer})
            slots = {row: data_qubits + 2 * local for local, row in enumerate(rows)}
            for row in rows:
                syndrome = slots[row]
                operations.append(Operation(tick, "prep_syndrome", (syndrome,)))
                operations.append(Operation(tick, "prep_flag", (syndrome + 1,)))
            tick += 1
            for row in rows:
                syndrome = slots[row]
                operations.append(Operation(tick, "cnot", (syndrome + 1, syndrome)))
            tick += 1
            for layer in batch:
                for row, q in layer:
                    operations.append(Operation(tick, "cnot", (q, slots[row])))
                tick += 1
            for row in rows:
                syndrome = slots[row]
                operations.append(Operation(tick, "cnot", (syndrome + 1, syndrome)))
            tick += 1
            for row in rows:
                syndrome = slots[row]
                record = pass_index * len(checks) + row
                operations.append(Operation(tick, "read_syndrome", (syndrome,), record))
                operations.append(Operation(tick, "read_flag", (syndrome + 1,), record))
            tick += 1
    return FlagCircuit(
        data_qubits, checks, axis, schedule.ancilla_pool, tuple(operations), tick,
        len(schedule.batches), schedule.cnot_layers,
    )


def structural_resources(circuit: FlagCircuit) -> dict[str, Any]:
    """Per-attempt counts; a layer is NOT a native cycle or duration."""
    counts = Counter(op.kind for op in circuit.operations)
    digest = hashlib.sha256()
    for op in circuit.operations:
        digest.update(f"{op.tick}:{op.kind}:{op.qubits}:{op.record}\n".encode("ascii"))
    last = [-1] * (circuit.data_qubits + 2 * circuit.pool)
    idles: Counter[str] = Counter()
    for op in circuit.operations:
        for q in op.qubits:
            kind = "data" if q < circuit.data_qubits else (
                "syndrome" if (q - circuit.data_qubits) % 2 == 0 else "flag"
            )
            if not op.kind.startswith("prep_"):
                if last[q] < 0 or op.tick <= last[q]:
                    raise ValueError("Invalid wire lifetime")
                idles[kind] += op.tick - last[q] - 1
            elif last[q] != -1:
                raise ValueError("Preparation on a live wire")
            last[q] = -1 if op.kind.startswith("read_") else op.tick
    idles["data"] += sum(circuit.ticks - 1 - last[q] for q in range(circuit.data_qubits))
    return {
        "data_qubits": circuit.data_qubits,
        "supplied_checks": len(circuit.checks),
        "concurrent_check_flag_pairs": circuit.pool,
        "ancillas": 2 * circuit.pool,
        "qubit_peak": circuit.data_qubits + 2 * circuit.pool,
        "batches_per_pass": circuit.batches_per_pass,
        "data_cnot_layers_per_pass": circuit.data_cnot_layers_per_pass,
        "total_cnot_layers": 2 * (
            circuit.data_cnot_layers_per_pass + 2 * circuit.batches_per_pass
        ),
        "abstract_ticks": circuit.ticks,
        "operation_counts": dict(sorted(counts.items())),
        "idle_locations": dict(sorted(idles.items())),
        "total_idle_locations": sum(idles.values()),
        "schedule_sha256": digest.hexdigest(),
        "axis": circuit.axis,
        "symbolic_attempt_time": (
            "t_data_prep + 2*B*(t_pair_prep + 2*t_flag_CNOT + t_pair_read)"
            " + 2*D*t_data_CNOT + t_classical_accept_and_frame"
        ),
        "native_seconds": None,
        "qec_cycles": None,
        "routing_included": False,
        "boundary": "each block ends at its own final ancilla measurement; no cross-block waiting",
    }


class _Quotient:
    """Pack (H*x, z mod row(H), first, second, flags) in one exact integer."""

    def __init__(self, checks: tuple[int, ...], n: int) -> None:
        self.n = n
        self.m = len(checks)
        self.columns = transpose(checks, n)
        self.row_basis = echelon(checks)
        self.image_basis = echelon(self.columns)
        self.z_columns = tuple(remainder(1 << q, self.row_basis) for q in range(n))
        self.output_width = n + self.m
        self.output_mask = (1 << self.output_width) - 1
        self.record_mask = (1 << self.m) - 1
        self.flag_shift = self.output_width + 2 * self.m
        self.allowed = {0}
        for x, z in zip(self.columns, self.z_columns):
            self.allowed.update((x, z << self.m, x ^ (z << self.m)))
        self.valid_deltas: dict[int, bool] = {0: True}

    def classify(self, effect: int) -> str:
        if effect >> self.flag_shift:
            return "reject_flag"
        first = (effect >> self.output_width) & self.record_mask
        second = (effect >> (self.output_width + self.m)) & self.record_mask
        if first != second:
            return "reject_disagreement"
        valid = self.valid_deltas.get(first)
        if valid is None:
            valid = remainder(first, self.image_basis) == 0
            self.valid_deltas[first] = valid
        if not valid:
            return "reject_inconsistent"
        residual = (effect & self.output_mask) ^ first
        if residual == 0:
            return "accept_target"
        return "accept_weight_one" if residual in self.allowed else "accept_bad"


def audit_single_faults(circuit: FlagCircuit) -> dict[str, Any]:
    """Cover every declared one-fault location and Pauli, with exact idle weights.

    Gate noise: 15 nonidentity two-qubit Paulis AFTER the CNOT. Preparation /
    reset and idle: X,Y,Z AFTER their layer. Readout: one classical outcome
    flip (pre-readout Paulis reduce to this or a harmless phase). No physical
    frame-correction gates: accepted frame is recorded and interpreted ideally.
    Arbitrary initial random valid syndromes cancel by linearity; see contract.
    """
    n, m = circuit.data_qubits, len(circuit.checks)
    quotient = _Quotient(circuit.checks, n)
    width = n + 2 * circuit.pool
    x_maps = [0] * width
    z_maps = [0] * width
    next_tick = [-1] * width
    for q in range(n):
        x_maps[q] = quotient.columns[q]
        z_maps[q] = quotient.z_columns[q] << m
        next_tick[q] = circuit.ticks
    counts: dict[str, Counter[str]] = {}
    locations: Counter[str] = Counter()
    representatives = 0
    bad: dict[str, Any] | None = None
    hook_witness: dict[str, Any] | None = None
    first_row_support = tuple(bits(circuit.checks[0]))
    first_read_tick = next(op.tick for op in circuit.operations
                           if op.kind == "read_syndrome" and op.record == 0)

    def add(kind: str, effect: int, multiplicity: int, op: Operation, pauli: str) -> None:
        nonlocal representatives, bad
        if not multiplicity:
            return
        representatives += 1
        result = quotient.classify(effect)
        counts.setdefault(kind, Counter())[result] += multiplicity
        if result == "accept_bad" and bad is None:
            bad = {
                "kind": kind, "tick": op.tick, "qubits": list(op.qubits),
                "canonical_Z_convention_pauli": pauli,
                "physical_axis_dual_required": circuit.axis == "X",
                "packed_effect_hex": hex(effect),
            }

    def idle_gap(q: int, op: Operation) -> None:
        if next_tick[q] < 0:
            raise ValueError("Use of an inactive ancilla")
        gap = next_tick[q] - op.tick - 1
        if gap < 0:
            raise ValueError("Wire collision or reversed time")
        kind = "idle_data" if q < n else (
            "idle_syndrome" if (q - n) % 2 == 0 else "idle_flag"
        )
        locations[kind] += gap
        for pauli, effect in (("X", x_maps[q]), ("Z", z_maps[q]),
                              ("Y", x_maps[q] ^ z_maps[q])):
            add(kind, effect, gap, op, pauli)

    for op in reversed(circuit.operations):
        if op.kind.startswith("read_"):
            q = op.qubits[0]
            if next_tick[q] != -1:
                raise ValueError("Ancilla lifetime overlaps reset")
            bit = 1 << (
                quotient.output_width + op.record if op.kind == "read_syndrome"
                else quotient.flag_shift + op.record
            )
            x_maps[q], z_maps[q] = (bit, 0) if op.kind == "read_syndrome" else (0, bit)
            next_tick[q] = op.tick
            locations[op.kind] += 1
            add(op.kind, bit, 1, op, "outcome_flip")
            continue
        for q in op.qubits:
            idle_gap(q, op)
        locations[op.kind] += 1
        if op.kind == "cnot":
            c, t = op.qubits
            if (len(first_row_support) >= 3 and c == first_row_support[2] and t == n
                    and op.tick < first_read_tick):
                hook_witness = {
                    "row_zero_based": 0, "after_data_cnot": 3,
                    "tick": op.tick,
                    "physical_fault": "syndrome_Z" if circuit.axis == "Z" else "syndrome_X",
                    "actual_flag_indices": list(bits(z_maps[t] >> quotient.flag_shift)),
                    "classification": quotient.classify(z_maps[t]),
                }
            left = (0, x_maps[c], z_maps[c], x_maps[c] ^ z_maps[c])
            right = (0, x_maps[t], z_maps[t], x_maps[t] ^ z_maps[t])
            for a in range(4):
                for b in range(4):
                    if a or b:
                        add("cnot", left[a] ^ right[b], 1, op, "IXZY"[a] + "IXZY"[b])
            x_maps[c] ^= x_maps[t]
            z_maps[t] ^= z_maps[c]
        elif op.kind.startswith("prep_"):
            q = op.qubits[0]
            for pauli, effect in (("X", x_maps[q]), ("Z", z_maps[q]),
                                  ("Y", x_maps[q] ^ z_maps[q])):
                add(op.kind, effect, 1, op, pauli)
            # A Pauli stabilizing the fresh state must have no physical effect,
            # though on data it can relabel the random ideal projection branch.
            stabilizing = z_maps[q] if op.kind == "prep_syndrome" else x_maps[q]
            if quotient.classify(stabilizing) != "accept_target":
                raise ValueError("Noiseless preparation-state identity failed")
            x_maps[q] = z_maps[q] = 0
        else:
            raise ValueError("Unknown operation")
        for q in op.qubits:
            next_tick[q] = -1 if op.kind.startswith("prep_") else op.tick
    if any(t != -1 for t in next_tick):
        raise ValueError("Unclosed wire lifetime")
    totals: Counter[str] = Counter()
    rows: dict[str, Any] = {}
    for kind in sorted(locations):
        distribution = counts.get(kind, Counter())
        multiplicity = 15 if kind == "cnot" else 1 if kind.startswith("read_") else 3
        if sum(distribution.values()) != multiplicity * locations[kind]:
            raise ValueError("Incomplete fault-location coverage")
        rejected = sum(value for key, value in distribution.items() if key.startswith("reject_"))
        coefficient = Fraction(rejected, multiplicity)
        rows[kind] = {
            "locations": locations[kind], "paulis_per_location": multiplicity,
            "fault_cases": sum(distribution.values()), "outcomes": dict(sorted(distribution.items())),
            "linear_rejection_coefficient": str(coefficient),
        }
        totals.update(distribution)
    syndrome_rank = len(quotient.image_basis)
    return {
        "evidence": "NUMERICAL" if bad is None else "FALSIFIED",
        "single_fault_residual_weight_at_most_one": bad is None,
        "first_accepted_counterexample": bad,
        "row0_third_data_cnot_hook": hook_witness,
        "all_valid_ideal_projection_branches": True,
        "ideal_independent_sign_bits": syndrome_rank,
        "uniform_state_stabilizer_dimension": len(quotient.row_basis) + n - syndrome_rank,
        "target_group": "Z row(H) and X ker(H), globally H-dual for X checks",
        "fault_classes": rows,
        "total_locations": sum(locations.values()),
        "total_pauli_fault_cases": sum(totals.values()),
        "evaluated_map_cases_before_idle_multiplicity": representatives,
        "total_outcomes": dict(sorted(totals.items())),
        "idle_aggregation": "exact unchanged Pauli-transfer map between consecutive operations on one live wire",
        "noise_model": "15 equiprobable nonidentity CNOT Paulis; 3 for reset/preparation/idle; one readout bit flip",
        "rejection_expansion": "P(reject) = sum_kind coefficient_kind * p_kind + O(p^2) at fixed circuit size; not a finite-p estimate when location_count*p is large",
        "full_factory_ft": False,
        "native_seconds": None,
        "logical_failure_probability": None,
    }


def retry_bounds(check_count: int, readout_error_rates: tuple[float, ...]) -> dict[str, Any]:
    """Rigorous per-block acceptance ceiling from independent flag readout flips.

    For p<=1/2, any true flag string is recorded all-zero with probability at
    most (1-p)^(2R). This remains an upper bound in the presence of other noise
    independent of these readout flips; it is not an estimated actual yield.
    """
    if type(check_count) is not int or check_count <= 0:
        raise ValueError("Positive number of checks required")
    if any(type(p) not in (float, int) or not 0 <= p <= 0.5 for p in readout_error_rates):
        raise ValueError("Independent readout-flip probabilities must be in [0,1/2]")
    return {
        "flag_readouts_per_attempt": 2 * check_count,
        "independent_flag_readout_only_acceptance_upper_bounds": [
            {"p_measure": p, "acceptance_upper_bound": (1 - p) ** (2 * check_count)}
            for p in readout_error_rates
        ],
        "independent_all_readout_acceptance_upper_bounds": [
            {"p_measure": p,
             "acceptance_upper_bound": (1 - p) ** (2 * check_count)
             * ((1 - p) ** 2 + p ** 2) ** check_count}
            for p in readout_error_rates
        ],
        "all_readout_bound_argument": "Condition on any true readout pattern independent of classical readout flips. Each flag is recorded zero with probability <=1-p; each pair of syndrome readouts agrees with probability <=(1-p)^2+p^2. All these flip variables are disjoint. Dependent-check consistency can only reduce acceptance.",
        "separate_retries": "For independent identical attempts of one block, E[attempts]=1/P_accept; actual P_accept is OPEN. Do not multiply Q/M acceptance probabilities unless both restart together.",
        "buffering": "Separately successful Q/M blocks need storage, QEC and synchronization; these are not free or included in the preparation certificate.",
        "finite_p_acceptance_estimate": None,
    }
