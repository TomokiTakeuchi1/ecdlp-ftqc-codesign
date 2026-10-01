"""One-pass, cat-free LP preparation baseline and a bounded hook diagnostic.

This is an explicitly scheduled *ideal projection pass*, not FT initialization.
The fault census contains one spreading-axis ancilla Pauli after each check
CNOT, plus one bit flip at each final mask readout. It deliberately does not
claim coverage of every circuit fault, a decoder, or fault-tolerant admission.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import Any

from ecdlp_ftqc.code_constructions.lp_ghz import (
    CSSCode,
    base_seed,
    bits,
    canonical_logicals,
    completed_seed,
    echelon,
    lifted_product,
    remainder,
    transpose,
)
from ecdlp_ftqc.code_constructions.lp_protected_ghz import punctured_mask, restrict

# An edge is (global check-row index, data coordinate). Each layer contains
# distinct row indices and distinct data coordinates. A batch reuses its pool.
Layer = tuple[tuple[int, int], ...]
Batch = tuple[Layer, ...]


@dataclass(frozen=True)
class CheckSchedule:
    """Row-batched schedule with increasing-coordinate order within each row."""

    data_qubits: int
    check_rows: tuple[int, ...]
    ancilla_pool: int
    batches: tuple[Batch, ...]

    @property
    def cnot_layers(self) -> int:
        return sum(len(batch) for batch in self.batches)

    def summary(self) -> dict[str, Any]:
        digest = hashlib.sha256()
        for batch_index, batch in enumerate(self.batches):
            for layer_index, layer in enumerate(batch):
                digest.update(f"{batch_index}:{layer_index}:".encode("ascii"))
                for row, coordinate in layer:
                    digest.update(f"{row},{coordinate};".encode("ascii"))
                digest.update(b"\n")
        return {
            "data_qubits": self.data_qubits,
            "supplied_checks": len(self.check_rows),
            "syndrome_ancilla_pool": self.ancilla_pool,
            "batches": len(self.batches),
            "cnot_count": sum(row.bit_count() for row in self.check_rows),
            "cnot_layers": self.cnot_layers,
            "ancilla_preparations": len(self.check_rows),
            "ancilla_measurements": len(self.check_rows),
            "batch_cnot_layers": [len(batch) for batch in self.batches],
            "schedule_sha256": digest.hexdigest(),
            "schedule_rule": "contiguous row batches; ascending support; greedy ascending-row frontier",
            "connectivity": "unrestricted data-to-pool-ancilla coupling; no routing duration",
        }


def schedule_checks(
    rows: tuple[int, ...], data_qubits: int, ancilla_pool: int = 64
) -> CheckSchedule:
    """Construct a deterministic, collision-free CNOT schedule, not an optimum.

    Each batch first prepares its ancillas, runs the returned layers, and then
    measures all its ancillas. All checks have the same Pauli type. The pool is
    reused only after measurement/reset; zero or invalid check rows are rejected.
    """
    if type(data_qubits) is not int or data_qubits <= 0:
        raise ValueError("A positive integer data-qubit count is required")
    if type(ancilla_pool) is not int or ancilla_pool <= 0:
        raise ValueError("A positive integer syndrome-ancilla pool is required")
    if not isinstance(rows, tuple) or not rows:
        raise ValueError("A nonempty tuple of nonzero check rows is required")
    if any(type(row) is not int or row <= 0 or row.bit_length() > data_qubits for row in rows):
        raise ValueError("Invalid check support")
    pool = min(ancilla_pool, len(rows))
    batches: list[Batch] = []
    for first in range(0, len(rows), pool):
        supports = [tuple(bits(row)) for row in rows[first : first + pool]]
        positions = [0] * len(supports)
        layers: list[Layer] = []
        while any(position < len(support) for position, support in zip(positions, supports)):
            used: set[int] = set()
            layer: list[tuple[int, int]] = []
            for local_row, support in enumerate(supports):
                position = positions[local_row]
                if position == len(support) or support[position] in used:
                    continue
                coordinate = support[position]
                used.add(coordinate)
                layer.append((first + local_row, coordinate))
                positions[local_row] += 1
            layers.append(tuple(layer))
        batches.append(tuple(layers))
    return CheckSchedule(data_qubits, rows, pool, tuple(batches))


def conjugate_cnot(x: int, z: int, control: int, target: int, width: int) -> tuple[int, int]:
    """Propagate a phase-free Pauli through one CNOT (integer supports)."""
    if type(width) is not int or width <= 0:
        raise ValueError("Positive width required")
    if any(type(value) is not int or value < 0 or value.bit_length() > width for value in (x, z)):
        raise ValueError("Invalid Pauli support")
    if any(type(q) is not int or q not in range(width) for q in (control, target)):
        raise ValueError("CNOT coordinate outside the register")
    if control == target:
        raise ValueError("CNOT control and target coincide")
    return x ^ (((x >> control) & 1) << target), z ^ (((z >> target) & 1) << control)


def hook_suffix(support: tuple[int, ...], after_gates: int) -> int:
    """Data support of the spreading ancilla Pauli after ``after_gates`` CNOTs.

    Z-check circuit: data controls ancilla |0>, ancilla Z spreads to later data.
    X-check circuit: ancilla |+> controls data, ancilla X spreads to later data.
    The ancilla measurement in either circuit is NOT flipped by this fault.
    """
    if not isinstance(support, tuple) or not support:
        raise ValueError("Nonempty ordered support required")
    if any(type(q) is not int or q < 0 for q in support) or len(set(support)) != len(support):
        raise ValueError("Invalid or repeated data coordinate")
    if type(after_gates) is not int or after_gates not in range(len(support) + 1):
        raise ValueError("Hook position is outside the check circuit")
    return sum(1 << q for q in support[after_gates:])


def _xor_columns(columns: tuple[int, ...], support: int) -> int:
    value = 0
    for coordinate in bits(support):
        value ^= columns[coordinate]
    return value


def audit_weight_two_signature(
    data_qubits: int, x_constraints: tuple[int, ...], z_error: int
) -> dict[str, Any]:
    """Exhaustively test whether an X-constraint signature has support <=2.

    All single columns and all unordered column pairs are covered by a
    complement lookup. A mixed Pauli of weight <=2 has a Z component of weight
    <=2, so absence of such a binary support also excludes mixed Paulis. This
    is a constraint-signature statement, not a general code-distance claim.
    """
    if type(data_qubits) is not int or data_qubits <= 0:
        raise ValueError("Positive integer data-qubit count required")
    if not isinstance(x_constraints, tuple) or any(
        type(row) is not int or row < 0 or row.bit_length() > data_qubits for row in x_constraints
    ):
        raise ValueError("Invalid X constraint matrix")
    if type(z_error) is not int or z_error < 0 or z_error.bit_length() > data_qubits:
        raise ValueError("Invalid Z error support")
    columns = transpose(x_constraints, data_qubits)
    target = _xor_columns(columns, z_error)
    single = next((q for q, column in enumerate(columns) if column == target), None)
    previous: dict[int, int] = {}
    pair: list[int] | None = None
    for q, column in enumerate(columns):
        partner = previous.get(target ^ column)
        if partner is not None and pair is None:
            pair = [partner, q]
        previous[column] = q
    return {
        "constraint_rows": len(x_constraints),
        "signature_set_rows_zero_based": list(bits(target)),
        "zero_support_matches": target == 0,
        "single_support_matching_witness": None if single is None else [single],
        "pair_support_matching_witness": pair,
        "covered_single_supports": data_qubits,
        "covered_unordered_pair_supports": data_qubits * (data_qubits - 1) // 2,
        "no_representative_of_weight_at_most_two": target != 0 and single is None and pair is None,
        "scope": "X-constraint signature only; includes necessary signatures of mixed Paulis",
    }


def _record_blind_obstruction(q: CSSCode, retained_x: tuple[int, ...]) -> dict[str, Any]:
    # One explicit physical fault suffices. Enumerating all hook-pair combinations
    # is neither required nor claimed by this stronger bounded witness.
    row = q.hz[0]
    ordered = tuple(bits(row))
    if len(ordered) < 3:
        raise ValueError("The selected check does not contain the required three gates")
    fault = hook_suffix(ordered, 3)
    prefix = row ^ fault
    signature = audit_weight_two_signature(q.n, q.hx + retained_x, fault)
    certified = bool(signature["no_representative_of_weight_at_most_two"])
    return {
        "evidence": "FALSIFIED" if certified else "INCONCLUSIVE",
        "claim_under_test": "This bare baseline has an actually-record-conditioned Pauli recovery leaving at most one residual physical error, modulo harmless operators, for every no-fault or covered one-fault branch.",
        "check_row_zero_based": 0,
        "fault": "Z on Q Z-check ancilla immediately after its third CNOT",
        "check_support_zero_based": list(ordered),
        "fault_output_support_zero_based": list(bits(fault)),
        "equivalent_prefix_support_zero_based": list(bits(prefix)),
        "difference_is_supplied_Z_check": fault ^ prefix == row,
        "signature_audit": signature,
        "harmless_coset_minimum_weight": 3 if certified and prefix.bit_count() == 3 else None,
        "no_fault_and_fault_actual_record_deltas_identical": True,
        "actual_record": "Q Z-check outcomes, M X-check outcomes, final M physical Z outcomes; same ideal branch and same noiseless sign corrections",
        "branchwise_record_argument": "The propagated ancilla Z contributes only a phase (-1)^outcome to its Z readout. The Q Z suffix commutes with later Q Z projections, control-side Q->M matching and all M Z readouts. Ideal conditional Pauli corrections alter only a global phase when moved across this suffix. Thus the no-fault and faulty histories share every actually collected random outcome branch; ideal known HX signs are not an observed noisy syndrome.",
        "harmless_operators": "code stabilizers, canonical target-state stabilizers, arbitrary residual-logical Paulis; all commute with Q HX and retained canonical X",
        "no_common_record_conditioned_Pauli_recovery_under_stated_criterion": certified,
        "proof": "If a common recovery leaves both identity and this fault equivalent to errors of weight <=1, their product is equivalent to a Pauli of weight <=2. Every harmless operator commutes with the tested X constraints. Exhaustive absence of a <=2 signature representative contradicts that implication. The three-site prefix supplies the upper bound, modulo one Q Z check.",
        "scope_limit": "Falsifies only this bare baseline with no extra Q X-syndrome/flag record and the stated residual-weight criterion; not LP fault tolerance, flagged preparation, or preparation followed by additional QEC.",
        "automorphism": "ideal physical permutation transports the harmless group and preserves weight, so cannot remove the obstruction",
    }


def _hook_census(
    code: CSSCode,
    checks: tuple[int, ...],
    opposite: tuple[int, ...],
    observed_parities: tuple[int, ...],
) -> dict[str, Any]:
    syndromes = transpose(opposite, code.n)
    parities = transpose(observed_parities, code.n)
    same_type_basis = echelon(checks)
    support_weights: Counter[int] = Counter()
    complementary_weights: Counter[int] = Counter()
    raw_parity_flips: Counter[int] = Counter()
    zero_syndrome = 0
    zero_syndrome_stabilizer = 0
    witness: dict[str, Any] | None = None
    for row_index, row in enumerate(checks):
        ordered = tuple(bits(row))
        suffix = row
        for after_gates, coordinate in enumerate(ordered, start=1):
            suffix ^= 1 << coordinate
            syndrome = _xor_columns(syndromes, suffix)
            flips = _xor_columns(parities, suffix).bit_count()
            weight = suffix.bit_count()
            complementary_weight = min(weight, len(ordered) - weight)
            support_weights[weight] += 1
            complementary_weights[complementary_weight] += 1
            raw_parity_flips[flips] += 1
            if syndrome == 0:
                zero_syndrome += 1
                zero_syndrome_stabilizer += int(remainder(suffix, same_type_basis) == 0)
            if complementary_weight > 1 and syndrome and witness is None:
                witness = {
                    "check_row_zero_based": row_index,
                    "after_cnot_count": after_gates,
                    "check_support_zero_based": list(ordered),
                    "data_error_support_zero_based": list(bits(suffix)),
                    "support_weight": weight,
                    "weight_after_optional_complement_by_measured_check": complementary_weight,
                    "opposite_check_syndrome_rows_zero_based": list(bits(syndrome)),
                    "raw_canonical_parity_flips": flips,
                    "not_a_logical_failure_witness": True,
                }
    total = sum(support_weights.values())
    return {
        "fault_locations": total,
        "one_pauli_per_location": True,
        "same_type_preparation_record_delta_is_zero": True,
        "raw_data_support_weight_histogram": dict(sorted(support_weights.items())),
        "support_or_measured_check_complement_weight_histogram": dict(
            sorted(complementary_weights.items())
        ),
        "complement_is_only_an_upper_bound_on_coset_minimum": True,
        "raw_canonical_parity_flip_count_histogram": dict(sorted(raw_parity_flips.items())),
        "opposite_check_syndrome_nonzero": total - zero_syndrome,
        "opposite_check_syndrome_zero": zero_syndrome,
        "zero_syndrome_same_type_stabilizer": zero_syndrome_stabilizer,
        "zero_syndrome_nonstabilizer": zero_syndrome - zero_syndrome_stabilizer,
        "multi_support_diagnostic_witness": witness,
        "weight_not_a_decoder_or_failure_classification": True,
    }


def audit_preparation(
    lift: int = 75,
    ancilla_pool: int = 64,
    *,
    ancilla_caps: tuple[int, ...] = (1, 64, 256, 5250),
) -> dict[str, Any]:
    """Report one explicit direct-factory baseline; no FT/native-time admission.

    ``ancilla_pool`` is per block, with Q and M prepared concurrently. The
    default lift is the reviewed instance; other odd lifts are structural toys.
    ``ancilla_caps`` supplies additional scheduling sensitivity cases without
    repeating the hook census. The masks and logical generators are inherited
    unchanged. Noiseless physical preparation-sign corrections are assumed:
    X_Q and Z_M, applied before matching, after ideal classical processing.
    """
    if not isinstance(ancilla_caps, tuple) or any(
        type(cap) is not int or cap <= 0 for cap in ancilla_caps
    ):
        raise ValueError("Ancilla sensitivity caps must be a tuple of positive integers")
    if len(set(ancilla_caps)) != len(ancilla_caps):
        raise ValueError("Duplicate ancilla sensitivity cap")
    q = lifted_product(completed_seed(lift), base_seed(lift).adjoint())
    mask, coordinates = punctured_mask(lift)
    q_schedule = schedule_checks(q.hz, q.n, ancilla_pool)
    mask_schedule = schedule_checks(mask.hx, mask.n, ancilla_pool)
    sensitivity: list[dict[str, Any]] = []
    for cap in ancilla_caps:
        qs = q_schedule if cap == ancilla_pool else schedule_checks(q.hz, q.n, cap)
        ms = mask_schedule if cap == ancilla_pool else schedule_checks(mask.hx, mask.n, cap)
        sensitivity.append(
            {
                "requested_ancillas_per_block": cap,
                "actual_concurrent_syndrome_ancillas": qs.ancilla_pool + ms.ancilla_pool,
                "explicit_baseline_peak_qubits": q.n + mask.n + qs.ancilla_pool + ms.ancilla_pool,
                "Q": qs.summary(),
                "M": ms.summary(),
                "preparation_duration": "max(tau_plus + B_Q*(tau_anc0+tau_measureZ)+D_Q*tau_CNOT, tau_zero+B_M*(tau_ancplus+tau_measureX)+D_M*tau_CNOT)",
                "B_and_D": "B is batch count; D is CNOT layers for the corresponding block",
            }
        )
    xs, zs = canonical_logicals(lift)
    retained_x = xs[12 * lift :]
    canonical_mask_z = tuple(restrict(z, coordinates) for z in zs[: 12 * lift])
    q_hooks = _hook_census(q, q.hz, q.hx, retained_x)
    mask_hooks = _hook_census(mask, mask.hx, mask.hz, canonical_mask_z)
    q_hooks["fault"] = "ancilla Z immediately after each Q Z-check CNOT"
    q_hooks["interface_propagation"] = "Q-control Z stays on Q; mask Z-readout delta zero"
    q_hooks["opposite_check_syndrome_is_actual_record"] = False
    q_hooks["all_collected_preparation_and_mask_record_deltas_zero"] = True
    q_hooks["syndrome_interpretation"] = (
        "hypothetical perfect terminal Q X-check diagnostic; not present in baseline"
    )
    mask_hooks["fault"] = "ancilla X immediately after each M X-check CNOT"
    mask_hooks["interface_propagation"] = (
        "M-target X stays on M; suffix flips final physical Z-readout bits"
    )
    mask_hooks["opposite_check_syndrome_is_actual_record"] = True
    mask_hooks["syndrome_interpretation"] = (
        "HZ_M parity of final physical Z-readout; detection only, no noisy decoder"
    )
    readout_syndromes = transpose(mask.hz, mask.n)
    readout_parities = transpose(canonical_mask_z, mask.n)
    syndrome_hist = Counter(syndrome.bit_count() for syndrome in readout_syndromes)
    parity_hist = Counter(parity.bit_count() for parity in readout_parities)
    physical_checks = len(q.hz) + len(mask.hx)
    prep_cnots = sum(row.bit_count() for row in q.hz + mask.hx)
    return {
        "schema": "lp-direct-ghz-preparation-v1",
        "evidence": "NUMERICAL",
        "lift": lift,
        "ghz4_outputs": 4 * lift,
        "preparation": {
            "Q": {
                "initialization": "all physical +; project supplied Z checks",
                **q_schedule.summary(),
            },
            "M": {
                "initialization": "all physical 0; project supplied X checks",
                **mask_schedule.summary(),
            },
            "check_circuit": "bare ancilla: data->ancilla0 for Z; ancilla+->data for X",
            "projection_passes": 1,
            "projection_pass_is_ft_initialization": False,
            "preparation_sign_correction": {
                "operations": "physical X_Q and Z_M before matching; noiseless baseline",
                "single_qubit_parallel_layers_upper_bound": 1,
                "physical_paulis_branch_dependent_count_upper_bound": q.n + mask.n,
                "count_bound_scope": "generic support bound; the separately verified pivot right inverse can tighten this",
                "classical_syndrome_processing_required": True,
                "if_instead_tracked": "Z_M propagates onto Q through Q->M CNOT; it cannot be dropped",
            },
            "postselect_random_logical_outcomes": False,
        },
        "ancilla_pool_sensitivity": sensitivity,
        "structural_resources": {
            "output_code_carriers": q.n,
            "mask_code_carriers": mask.n,
            "concurrent_code_carriers": q.n + mask.n,
            "concurrent_syndrome_ancilla_pool": q_schedule.ancilla_pool
            + mask_schedule.ancilla_pool,
            "explicit_baseline_peak_qubits": q.n
            + mask.n
            + q_schedule.ancilla_pool
            + mask_schedule.ancilla_pool,
            "peak_excludes": ["verification or flags", "routing storage", "terminal QEC ancillas"],
            "physical_data_initializations": q.n + mask.n,
            "syndrome_ancilla_preparations_and_measurements_each": physical_checks,
            "preparation_check_cnots": prep_cnots,
            "interface_cnots": mask.n,
            "total_cnots_before_automorphism": prep_cnots + mask.n,
            "interface_matching_layers": 1,
            "interface_matching_layer_is_qec_cycle": False,
            "destructive_mask_z_readouts": mask.n,
            "destructive_output_readouts": 0,
            "post_matching_mask_outcome_correction": "track logical Pauli frame through automorphism; no physical correction gate in this baseline",
            "second_data_block_required": False,
            "carrier_lifetimes": {
                "Q": "physical initialization through retained GHZ output and subsequent storage",
                "M": "physical initialization through final mask Z-readout; then releasable",
                "syndrome_pool": "allocated during each block's preparation; reusable after each batch measurement/reset",
            },
        },
        "symbolic_time": {
            "Q_preparation": f"tau_plus + {len(q_schedule.batches)}*(tau_anc0 + tau_measureZ) + {q_schedule.cnot_layers}*tau_CNOT",
            "M_preparation": f"tau_zero + {len(mask_schedule.batches)}*(tau_ancplus + tau_measureX) + {mask_schedule.cnot_layers}*tau_CNOT",
            "complete": "max(T_Qprep,T_Mprep) + tau_prep_syndrome_processing + tau_parallel_prep_Paulis + tau_matching_CNOT + tau_mask_Z_readout + tau_mask_frame_processing + tau_automorphism",
            "ancilla_preparation_includes_reset": True,
            "matching_assumes_all_9075_pairs_simultaneously_available_at_lift75": True,
            "routing_and_idle_error_model": "OPEN; idle exposure exists but is not a fault location in this census",
            "native_seconds": None,
            "qec_rounds": None,
        },
        "bounded_fault_diagnostic": {
            "Q_preparation_Z_hooks": q_hooks,
            "M_preparation_X_hooks": mask_hooks,
            "M_single_readout_bit_flips": {
                "locations": mask.n,
                "nonzero_HZ_M_parity": sum(bool(s) for s in readout_syndromes),
                "distinct_HZ_M_syndrome_columns": len(set(readout_syndromes)),
                "HZ_M_parity_weight_histogram": dict(sorted(syndrome_hist.items())),
                "raw_canonical_mask_sign_flip_count_histogram": dict(sorted(parity_hist.items())),
                "raw_canonical_mask_sign_flips_range": [min(parity_hist), max(parity_hist)],
                "no_decoding_or_postselection_implemented": True,
            },
            "record_blind_common_recovery_obstruction": _record_blind_obstruction(q, retained_x),
            "total_enumerated_fault_events": prep_cnots + mask.n,
            "fault_free_other_operations_and_frame_processing": True,
            "covered": [
                "one spreading-axis ancilla Pauli after each check CNOT",
                "one bit flip at each final mask Z-readout",
            ],
            "excluded": [
                "other 14 nonidentity two-qubit Paulis per check CNOT",
                "initialization faults",
                "check readout faults",
                "physical preparation-sign correction faults",
                "idle faults",
                "interface CNOT faults",
                "automorphism faults",
                "classical processing faults",
                "multiple faults",
            ],
            "no_logical_error_rate_or_ft_certificate": True,
            "common_recovery_obligation": "A FT claim requires a common recovery for every candidate sharing the actually available record; neither nonzero syndrome nor raw weight establishes this.",
            "automorphism_error_transport": "ideal physical permutation preserves Pauli weight; canonical signs must be interpreted in the transformed GHZ basis",
        },
        "admission": {
            "fault_tolerant_factory": False,
            "native_speedup": False,
            "logical_failure_probability": None,
        },
    }
