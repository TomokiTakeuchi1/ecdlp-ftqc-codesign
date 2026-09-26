"""Branch-aware partial Clifford-frame clearing for direct-CCZ IP-QCLA.

The reviewed direct-CCZ compiler stores a recovery ``C`` satisfying
``physical = C^dagger logical``.  This module exposes the equivalent and more
usual byproduct frame ``F = C^dagger`` satisfying ``physical = F logical``.

For an incoming byproduct frame ``F_in``, desired logical Clifford ``U``, and
chosen outgoing frame ``F_out``, the physical Clifford is

    G = F_out U F_in^dagger.

The partial policy below is deliberately conservative.  It partitions the
active branch circuit for ``F_in`` into disconnected interaction components.
Every component touching a target of a simultaneous H layer is materialized;
all disjoint components remain in the outgoing frame.  Consequently
``F_in = A R`` with disjoint support and ``[R, U] = 0``, so the physical action
``G = U A^dagger`` is exact and leaves ``F_out = R``.

All reported primitive counts and ASAP depths are circuit-level generator
envelopes.  They are not native qLDPC cycles or wall-clock schedules.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGate, QclaGateKind, QclaTrace
from ecdlp_ftqc.compiler.direct_ccz import (
    DirectCczEventTrace,
    DirectCczInjectionEvent,
)
from ecdlp_ftqc.compiler.direct_ccz_ppm import (
    BooleanPolynomial,
    FrameGate,
    FrameGateKind,
    parse_boolean_expression,
)
from ecdlp_ftqc.metadata import EvidenceStatus

TASK_ID = "T-20260909-001"
EXPERIMENT_ID = "E-20260909-001"
SCHEMA = "ecdlp-ftqc/qcla-partial-frame-clearing-study"
SCHEMA_VERSION = 1
BRANCH_SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"


class PartialFrameClearingError(ValueError):
    """Raised when the frame-clearing study violates its contract."""


class FramePolicy(str, Enum):
    """Logical H handling policies compared by this study."""

    FULL_CONJUGATION = "full_frame_conjugation"
    BARE_PROPAGATION = "bare_h_frame_propagation"
    FRAME_TRACKING = "h_frame_tracking"
    FULL_CLEARING = "full_frame_clearing"
    PARTIAL_CLEARING = "target_component_partial_clearing"


@dataclass(frozen=True, slots=True)
class IntegerDistribution:
    """Complete deterministic branch vector plus nearest-rank summaries."""

    values: tuple[int, ...]
    minimum: int
    p50: int
    p95: int
    p99: int
    maximum: int
    all_zero_branch: int
    all_one_branch: int
    sha256: str

    def __post_init__(self) -> None:
        if len(self.values) < 2:
            raise PartialFrameClearingError("at least two branch witnesses are required")
        if self.all_zero_branch != self.values[0] or self.all_one_branch != self.values[1]:
            raise PartialFrameClearingError("forced branch summaries changed")
        if not (self.minimum <= self.p50 <= self.p95 <= self.p99 <= self.maximum):
            raise PartialFrameClearingError("distribution quantiles are not ordered")


@dataclass(frozen=True, slots=True)
class FramePolicyProfile:
    """One strategy's logical-generator and presented-PPM profile."""

    policy: FramePolicy
    candidate_ppm_levels: int
    literal_h_gate_occurrences: int
    literal_h_batches: int
    literal_cnot_occurrences: IntegerDistribution
    literal_cz_occurrences: IntegerDistribution
    literal_cnot_batches: IntegerDistribution
    literal_two_qubit_batches: IntegerDistribution
    serialized_logical_layer_envelope: IntegerDistribution
    maximum_presented_ppm_weight: IntegerDistribution
    incompatible_phase_one_ppm_count: IntegerDistribution
    y_containing_phase_one_ppm_count: IntegerDistribution
    maximum_frame_primitive_count: IntegerDistribution
    final_frame_primitive_count: IntegerDistribution
    z_x_only_high_rate_family_admitted: bool
    native_scheduled_depth: None = None
    runtime_seconds: None = None
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL

    def __post_init__(self) -> None:
        if self.candidate_ppm_levels <= 0:
            raise PartialFrameClearingError("candidate depth must be positive")
        if self.native_scheduled_depth is not None or self.runtime_seconds is not None:
            raise PartialFrameClearingError("native schedule and runtime remain open")
        observed_admission = self.incompatible_phase_one_ppm_count.maximum == 0
        if self.z_x_only_high_rate_family_admitted != observed_admission:
            raise PartialFrameClearingError("axis admission disagrees with branch witnesses")


@dataclass(frozen=True, slots=True)
class PartialMacroProfile:
    """Per-macro statistics for the target-component policy."""

    macro_layer: int
    ccx_count: int
    distinct_h_target_count: int
    relevant_component_qubits: IntegerDistribution
    materialized_cnot_occurrences: IntegerDistribution
    retained_cnot_occurrences: IntegerDistribution
    presented_ppm_maximum_weight: IntegerDistribution


@dataclass(frozen=True, slots=True)
class PartialFrameClearingStudy:
    """Deterministic study for one IP-QCLA width."""

    width: int
    source_trace_id: str
    macro_depth: int
    macro_layer_sizes: tuple[int, ...]
    branch_sample_count: int
    branch_sample_seed: str
    policies: tuple[FramePolicyProfile, ...]
    partial_macro_profiles: tuple[PartialMacroProfile, ...]
    ordered_factorization_status: EvidenceStatus
    width5_replay_branch_count: int
    width5_projective_clifford_checks: int
    width5_projective_clifford_mismatches: int
    exact_identity_argument: str
    coordinate: str = "logical_generator_ASAP_envelope_not_native_cycles_or_runtime"
    complete_native_schedule: bool = False
    schema: str = SCHEMA
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.width < 2 or self.macro_depth != len(self.macro_layer_sizes):
            raise PartialFrameClearingError("width or macro schedule is invalid")
        if self.branch_sample_count < 2 or len(self.policies) != len(FramePolicy):
            raise PartialFrameClearingError("branch or policy coverage is incomplete")
        if len(self.partial_macro_profiles) != self.macro_depth:
            raise PartialFrameClearingError("partial macro coverage is incomplete")
        if self.ordered_factorization_status is not EvidenceStatus.PROVED:
            raise PartialFrameClearingError("component factorization must be proved")
        if self.width == 5:
            if not 2 <= self.width5_replay_branch_count <= self.branch_sample_count:
                raise PartialFrameClearingError("width-5 replay coverage is invalid")
            if self.width5_projective_clifford_checks <= 0:
                raise PartialFrameClearingError("width-5 exact checks are required")
            if self.width5_projective_clifford_mismatches:
                raise PartialFrameClearingError("width-5 Clifford identity failed")
        elif self.width5_replay_branch_count or self.width5_projective_clifford_checks:
            raise PartialFrameClearingError("width-5 checks leaked into another width")
        if self.complete_native_schedule:
            raise PartialFrameClearingError("study cannot claim a native schedule")


@dataclass(slots=True)
class _PolicyAccumulator:
    cnot_occurrences: list[int]
    cz_occurrences: list[int]
    cnot_batches: list[int]
    two_qubit_batches: list[int]
    layer_envelope: list[int]
    max_ppm_weight: list[int]
    incompatible_ppms: list[int]
    y_ppms: list[int]
    max_frame_primitives: list[int]
    final_frame_primitives: list[int]


@dataclass(frozen=True, slots=True)
class _CompiledCorrection:
    activation_mask: int
    circuit: tuple[FrameGate, ...]


_CORRECTION_RE = re.compile(r"^(CZ|X|Z)\(([^)]*)\)\^(.*)$")


def _sample_mask(variable: str, *, count: int, seed: str) -> int:
    byte_count = (count + 7) // 8
    raw = int.from_bytes(
        hashlib.shake_256(f"{seed}|{variable}".encode()).digest(byte_count),
        "little",
    )
    raw &= (1 << count) - 1
    raw &= ~1
    raw |= 1 << 1
    return raw


def _polynomial_mask(
    polynomial: BooleanPolynomial,
    *,
    count: int,
    seed: str,
) -> int:
    all_mask = (1 << count) - 1
    result = 0
    cache: dict[str, int] = {}
    for monomial in polynomial.monomials:
        term = all_mask
        for variable in monomial:
            term &= cache.setdefault(
                variable,
                _sample_mask(variable, count=count, seed=seed),
            )
        result ^= term
    return result


def _nearest_rank(values: tuple[int, ...], probability: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def _distribution(values: Iterable[int]) -> IntegerDistribution:
    vector = tuple(values)
    if len(vector) < 2:
        raise PartialFrameClearingError("distribution is missing forced branches")
    payload = json.dumps(vector, separators=(",", ":")).encode()
    return IntegerDistribution(
        values=vector,
        minimum=min(vector),
        p50=_nearest_rank(vector, 0.50),
        p95=_nearest_rank(vector, 0.95),
        p99=_nearest_rank(vector, 0.99),
        maximum=max(vector),
        all_zero_branch=vector[0],
        all_one_branch=vector[1],
        sha256=hashlib.sha256(payload).hexdigest().upper(),
    )


def _normalize(circuit: Iterable[FrameGate]) -> tuple[FrameGate, ...]:
    stack: list[FrameGate] = []
    for gate in circuit:
        if stack and stack[-1] == gate:
            stack.pop()
        else:
            stack.append(gate)
    return tuple(stack)


def _gate_from_source(gate: QclaGate) -> FrameGate:
    if gate.kind is QclaGateKind.CNOT:
        return FrameGate(FrameGateKind.CNOT, (gate.controls[0], gate.target))
    if gate.kind is QclaGateKind.X:
        return FrameGate(FrameGateKind.X, (gate.target,))
    raise PartialFrameClearingError("only source Clifford barriers can enter the frame")


def _compile_corrections(
    event: DirectCczInjectionEvent,
    *,
    sample_count: int,
) -> tuple[_CompiledCorrection, ...]:
    result: list[_CompiledCorrection] = []
    target = event.data[2]
    for index, expression in enumerate(event.correction_frame):
        match = _CORRECTION_RE.fullmatch(expression)
        if match is None:
            raise PartialFrameClearingError("unsupported direct-CCZ correction")
        raw_kind, raw_support, raw_condition = match.groups()
        support = tuple(value.strip() for value in raw_support.split(","))
        kind = FrameGateKind(raw_kind)
        if index < 3:
            if kind is not FrameGateKind.CZ:
                raise PartialFrameClearingError("first three corrections must be CZ")
            if target in support:
                control = support[0] if support[1] == target else support[1]
                kind = FrameGateKind.CNOT
                support = (control, target)
        polynomial = parse_boolean_expression(raw_condition)
        result.append(
            _CompiledCorrection(
                activation_mask=_polynomial_mask(
                    polynomial,
                    count=sample_count,
                    seed=BRANCH_SAMPLE_SEED,
                ),
                circuit=(FrameGate(kind, support),),
            )
        )
    return tuple(result)


def _commutation_aware_groups(trace: QclaTrace) -> tuple[tuple[QclaGate, ...], ...]:
    """Reproduce the reviewed compact IP recurrence without its pair oracle."""

    gates = tuple(gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI)
    barriers = tuple(
        sorted(
            {
                gate.algorithmic_layer
                for gate in trace.gates
                if gate.kind is not QclaGateKind.TOFFOLI
            }
        )
    )
    target_best: dict[str, tuple[int, int]] = {}
    control_best: dict[str, tuple[int, int]] = {}
    ranks: list[int] = []
    previous_segment = -1
    prior_segment_best: tuple[int, int] | None = None
    for position, gate in enumerate(gates):
        segment = sum(layer < gate.algorithmic_layer for layer in barriers)
        if segment != previous_segment:
            if ranks:
                prior_position = max(range(len(ranks)), key=lambda index: (ranks[index], -index))
                prior_segment_best = (ranks[prior_position], prior_position)
            target_best = {}
            control_best = {}
            previous_segment = segment
        candidates: list[tuple[int, int]] = []
        if prior_segment_best is not None:
            candidates.append(prior_segment_best)
        for control in gate.controls:
            if control in target_best:
                candidates.append(target_best[control])
        if gate.target in control_best:
            candidates.append(control_best[gate.target])
        parent = max(candidates, key=lambda item: (item[0], -item[1]), default=None)
        rank = 1 if parent is None else parent[0] + 1
        ranks.append(rank)
        current = (rank, position)
        if gate.target not in target_best or (rank, -position) > (
            target_best[gate.target][0],
            -target_best[gate.target][1],
        ):
            target_best[gate.target] = current
        for control in gate.controls:
            if control not in control_best or (rank, -position) > (
                control_best[control][0],
                -control_best[control][1],
            ):
                control_best[control] = current
    depth = max(ranks, default=0)
    return tuple(
        tuple(gate for gate, rank in zip(gates, ranks, strict=True) if rank == layer)
        for layer in range(1, depth + 1)
    )


def _conjugate_by_source_layer(
    frame: tuple[FrameGate, ...],
    layer: tuple[FrameGate, ...],
) -> tuple[FrameGate, ...]:
    # Mathematical factor order: B F B^dagger.
    return _normalize((*layer, *frame, *reversed(layer)))


def _append_active_corrections(
    frame: tuple[FrameGate, ...],
    events: tuple[DirectCczInjectionEvent, ...],
    corrections: dict[str, tuple[_CompiledCorrection, ...]],
    *,
    branch: int,
) -> tuple[FrameGate, ...]:
    result = list(frame)
    branch_bit = 1 << branch
    # The reviewed correction terms are stored in correction-to-apply circuit
    # order.  Flattening active terms in that order gives the mathematical
    # factor order of the inverse/byproduct contribution.
    for event in events:
        for term in corrections[event.source_gate_id]:
            if term.activation_mask & branch_bit:
                result.extend(term.circuit)
    return _normalize(result)


def _split_target_components(
    frame: tuple[FrameGate, ...],
    targets: tuple[str, ...],
) -> tuple[tuple[FrameGate, ...], tuple[FrameGate, ...], int]:
    parent: dict[str, str] = {}

    def find(value: str) -> str:
        parent.setdefault(value, value)
        root = value
        while parent[root] != root:
            root = parent[root]
        while parent[value] != value:
            following = parent[value]
            parent[value] = root
            value = following
        return root

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for gate in frame:
        for value in gate.support:
            find(value)
        if len(gate.support) == 2:
            union(gate.support[0], gate.support[1])
    relevant_roots = {find(target) for target in targets if target in parent}
    relevant_values = {value for value in parent if find(value) in relevant_roots}
    materialized: list[FrameGate] = []
    retained: list[FrameGate] = []
    for gate in frame:
        destination = materialized if set(gate.support) & relevant_values else retained
        destination.append(gate)
    materialized_result = _normalize(materialized)
    retained_result = _normalize(retained)
    materialized_support = {value for gate in materialized_result for value in gate.support}
    retained_support = {value for gate in retained_result for value in gate.support}
    if materialized_support & retained_support:
        raise PartialFrameClearingError("component partition has overlapping support")
    if set(targets) & retained_support:
        raise PartialFrameClearingError("residual frame still touches an H target")
    return materialized_result, retained_result, len(materialized_support)


def _primitive_counts(circuit: tuple[FrameGate, ...]) -> dict[FrameGateKind, int]:
    result = {kind: 0 for kind in FrameGateKind}
    for gate in circuit:
        result[gate.kind] += 1
    return result


def _asap_metrics(
    chronological: tuple[FrameGate, ...],
) -> tuple[int, int, int]:
    """Return total, CNOT-containing, and two-qubit-containing layer counts."""

    last_layer: dict[str, int] = {}
    kinds_by_layer: dict[int, set[FrameGateKind]] = defaultdict(set)
    for gate in chronological:
        if gate.kind in {FrameGateKind.X, FrameGateKind.Z}:
            continue
        layer = 1 + max((last_layer.get(value, 0) for value in gate.support), default=0)
        for value in gate.support:
            last_layer[value] = layer
        kinds_by_layer[layer].add(gate.kind)
    depth = max(kinds_by_layer, default=0)
    cnot_layers = sum(FrameGateKind.CNOT in kinds for kinds in kinds_by_layer.values())
    two_qubit_layers = sum(
        bool({FrameGateKind.CNOT, FrameGateKind.CZ} & kinds) for kinds in kinds_by_layer.values()
    )
    return depth, cnot_layers, two_qubit_layers


@dataclass(slots=True)
class _Tableau:
    x_images: list[tuple[int, int]]
    z_images: list[tuple[int, int]]


def _tableau(
    logical_values: tuple[str, ...],
    circuit: tuple[FrameGate, ...],
) -> _Tableau:
    index = {value: position for position, value in enumerate(logical_values)}
    x_images = [(1 << position, 0) for position in range(len(logical_values))]
    z_images = [(0, 1 << position) for position in range(len(logical_values))]
    for gate in circuit:
        if gate.kind in {FrameGateKind.X, FrameGateKind.Z}:
            continue
        if gate.kind is FrameGateKind.H:
            qubit = index[gate.support[0]]
            x_images[qubit], z_images[qubit] = z_images[qubit], x_images[qubit]
            continue
        left = index[gate.support[0]]
        right = index[gate.support[1]]
        if gate.kind is FrameGateKind.CNOT:
            x_images[left] = (
                x_images[left][0] ^ x_images[right][0],
                x_images[left][1] ^ x_images[right][1],
            )
            z_images[right] = (
                z_images[left][0] ^ z_images[right][0],
                z_images[left][1] ^ z_images[right][1],
            )
        elif gate.kind is FrameGateKind.CZ:
            x_images[left] = (
                x_images[left][0] ^ z_images[right][0],
                x_images[left][1] ^ z_images[right][1],
            )
            x_images[right] = (
                z_images[left][0] ^ x_images[right][0],
                z_images[left][1] ^ x_images[right][1],
            )
        else:  # pragma: no cover - enum exhaustiveness
            raise PartialFrameClearingError("unsupported tableau primitive")
    return _Tableau(x_images=x_images, z_images=z_images)


def _swap_axes_on_mask(x_bits: int, z_bits: int, mask: int) -> tuple[int, int]:
    return (
        (x_bits & ~mask) | (z_bits & mask),
        (z_bits & ~mask) | (x_bits & mask),
    )


def _ppm_metrics(
    policy: FramePolicy,
    tableau: _Tableau,
    group: tuple[QclaGate, ...],
    logical_index: dict[str, int],
    target_mask: int,
) -> tuple[int, int, int]:
    maximum_weight = 1
    incompatible = 0
    y_count = 0
    targets = {gate.target for gate in group}
    for gate in group:
        for logical in (*gate.controls, gate.target):
            position = logical_index[logical]
            if policy is FramePolicy.FRAME_TRACKING and logical in targets:
                x_bits, z_bits = tableau.x_images[position]
            else:
                x_bits, z_bits = tableau.z_images[position]
            if policy is FramePolicy.BARE_PROPAGATION:
                if logical in targets:
                    x_bits, z_bits = tableau.x_images[position]
                x_bits, z_bits = _swap_axes_on_mask(x_bits, z_bits, target_mask)
            maximum_weight = max(maximum_weight, 1 + (x_bits | z_bits).bit_count())
            if x_bits:
                incompatible += 1
            if x_bits & z_bits:
                y_count += 1
    return maximum_weight, incompatible, y_count


def _exact_pauli_image(
    logical: str,
    axis: str,
    factors: tuple[FrameGate, ...],
) -> tuple[int, tuple[tuple[str, str], ...]]:
    from ecdlp_ftqc.compiler.direct_ccz_ppm import SymbolicPauliWord

    word = SymbolicPauliWord.from_terms((logical,), (axis,))
    for gate in reversed(factors):
        word = word.apply_gate(gate)
    return word.evaluate({})


def _verify_projective_identity(
    logical_values: tuple[str, ...],
    left_factors: tuple[FrameGate, ...],
    right_factors: tuple[FrameGate, ...],
) -> tuple[int, int]:
    checks = 0
    mismatches = 0
    for logical in logical_values:
        for axis in ("X", "Z"):
            checks += 1
            if _exact_pauli_image(logical, axis, left_factors) != _exact_pauli_image(
                logical, axis, right_factors
            ):
                mismatches += 1
    return checks, mismatches


def _empty_accumulator() -> _PolicyAccumulator:
    return _PolicyAccumulator([], [], [], [], [], [], [], [], [], [])


def build_partial_frame_clearing_study(
    trace: QclaTrace,
    event_trace: DirectCczEventTrace,
    *,
    branch_sample_count: int = 512,
) -> PartialFrameClearingStudy:
    """Build the deterministic partial-frame study for one IP-QCLA trace."""

    if event_trace.source_trace_id != trace.trace_id:
        raise PartialFrameClearingError("source and direct-CCZ traces disagree")
    if branch_sample_count < 2:
        raise PartialFrameClearingError("forced all-zero/all-one branches are required")
    groups = _commutation_aware_groups(trace)
    event_by_source = {event.source_gate_id: event for event in event_trace.injection_events}
    correction_by_source = {
        event.source_gate_id: _compile_corrections(event, sample_count=branch_sample_count)
        for event in event_trace.injection_events
    }
    logical_values = tuple(
        sorted({value for gate in trace.gates for value in gate.logical_support})
    )
    logical_index = {value: index for index, value in enumerate(logical_values)}
    source_cliffords: dict[int, tuple[FrameGate, ...]] = {}
    for layer in sorted({gate.algorithmic_layer for gate in trace.gates}):
        layer_gates = tuple(
            _gate_from_source(gate)
            for gate in trace.gates
            if gate.algorithmic_layer == layer and gate.kind is not QclaGateKind.TOFFOLI
        )
        if layer_gates:
            source_cliffords[layer] = layer_gates

    accumulators = {policy: _empty_accumulator() for policy in FramePolicy}
    macro_values: list[dict[str, list[int]]] = [defaultdict(list) for _ in groups]
    exact_checks = 0
    exact_mismatches = 0

    for branch in range(branch_sample_count):
        baseline_frame: tuple[FrameGate, ...] = ()
        partial_frame: tuple[FrameGate, ...] = ()
        clearing_frame: tuple[FrameGate, ...] = ()
        applied_clifford_layers: set[int] = set()
        branch_totals = {
            policy: {
                "cnot": 0,
                "cz": 0,
                "cnot_batches": 0,
                "two_qubit_batches": 0,
                "depth": 0,
                "max_ppm": 1,
                "incompatible": 0,
                "y": 0,
                "max_frame": 0,
            }
            for policy in FramePolicy
        }
        for macro_index, group in enumerate(groups, start=1):
            lower = min(gate.algorithmic_layer for gate in group)
            for layer in sorted(source_cliffords):
                if layer >= lower or layer in applied_clifford_layers:
                    continue
                clifford_layer = source_cliffords[layer]
                baseline_frame = _conjugate_by_source_layer(baseline_frame, clifford_layer)
                partial_frame = _conjugate_by_source_layer(partial_frame, clifford_layer)
                clearing_frame = _conjugate_by_source_layer(clearing_frame, clifford_layer)
                applied_clifford_layers.add(layer)

            targets = tuple(sorted({gate.target for gate in group}))
            h_layer = tuple(FrameGate(FrameGateKind.H, (target,)) for target in targets)
            target_mask = sum(1 << logical_index[target] for target in targets)
            baseline_a, _, _ = _split_target_components(baseline_frame, targets)
            partial_in = partial_frame
            partial_a, partial_r, component_qubits = _split_target_components(partial_in, targets)
            partial_frame = partial_r

            policy_circuits = {
                FramePolicy.FULL_CONJUGATION: (
                    (*baseline_a, *h_layer, *reversed(baseline_a)),
                    (*baseline_a, *h_layer, *reversed(baseline_a)),
                ),
                FramePolicy.BARE_PROPAGATION: (h_layer, h_layer),
                FramePolicy.FRAME_TRACKING: ((), ()),
                FramePolicy.FULL_CLEARING: (
                    (*h_layer, *reversed(clearing_frame)),
                    h_layer,
                ),
                FramePolicy.PARTIAL_CLEARING: (
                    (*h_layer, *reversed(partial_a)),
                    h_layer,
                ),
            }
            for policy, circuits in policy_circuits.items():
                counts = {kind: 0 for kind in FrameGateKind}
                depth = 0
                cnot_batches = 0
                two_qubit_batches = 0
                for circuit in circuits:
                    current = _primitive_counts(tuple(circuit))
                    for kind, value in current.items():
                        counts[kind] += value
                    batch_depth, cnot_depth, two_qubit_depth = _asap_metrics(tuple(circuit))
                    depth += batch_depth
                    cnot_batches += cnot_depth
                    two_qubit_batches += two_qubit_depth
                branch_totals[policy]["cnot"] += counts[FrameGateKind.CNOT]
                branch_totals[policy]["cz"] += counts[FrameGateKind.CZ]
                branch_totals[policy]["cnot_batches"] += cnot_batches
                branch_totals[policy]["two_qubit_batches"] += two_qubit_batches
                branch_totals[policy]["depth"] += depth

            baseline_tableau = _tableau(logical_values, baseline_frame)
            partial_tableau = _tableau(logical_values, partial_frame)
            identity_tableau = _tableau(logical_values, ())
            tableau_by_policy = {
                FramePolicy.FULL_CONJUGATION: baseline_tableau,
                FramePolicy.BARE_PROPAGATION: baseline_tableau,
                FramePolicy.FRAME_TRACKING: baseline_tableau,
                FramePolicy.FULL_CLEARING: identity_tableau,
                FramePolicy.PARTIAL_CLEARING: partial_tableau,
            }
            for policy, tableau in tableau_by_policy.items():
                maximum, incompatible, y_count = _ppm_metrics(
                    policy, tableau, group, logical_index, target_mask
                )
                branch_totals[policy]["max_ppm"] = max(branch_totals[policy]["max_ppm"], maximum)
                branch_totals[policy]["incompatible"] += incompatible
                branch_totals[policy]["y"] += y_count
                frame_for_policy = {
                    FramePolicy.FULL_CONJUGATION: baseline_frame,
                    FramePolicy.BARE_PROPAGATION: baseline_frame,
                    FramePolicy.FRAME_TRACKING: baseline_frame,
                    FramePolicy.FULL_CLEARING: (),
                    FramePolicy.PARTIAL_CLEARING: partial_frame,
                }[policy]
                branch_totals[policy]["max_frame"] = max(
                    branch_totals[policy]["max_frame"], len(frame_for_policy)
                )

            partial_counts = _primitive_counts(partial_a)
            retained_counts = _primitive_counts(partial_frame)
            macro_values[macro_index - 1]["component_qubits"].append(component_qubits)
            macro_values[macro_index - 1]["materialized_cnot"].append(
                partial_counts[FrameGateKind.CNOT]
            )
            macro_values[macro_index - 1]["retained_cnot"].append(
                retained_counts[FrameGateKind.CNOT]
            )
            partial_ppm = _ppm_metrics(
                FramePolicy.PARTIAL_CLEARING,
                partial_tableau,
                group,
                logical_index,
                target_mask,
            )[0]
            macro_values[macro_index - 1]["ppm_max"].append(partial_ppm)

            if trace.width == 5 and branch < min(16, branch_sample_count):
                # Exact Clifford equality up to global phase.  Component
                # separation proves the identity for every branch; these
                # Pauli-generator checks separately replay the factorization,
                # the physical partial-clearing action, and commutation of the
                # retained component with the simultaneous H layer.
                identities = (
                    (partial_in, (*partial_a, *partial_r)),
                    (
                        (*h_layer, *reversed(partial_a), *partial_in),
                        (*partial_r, *h_layer),
                    ),
                    ((*h_layer, *partial_r), (*partial_r, *h_layer)),
                )
                for left, right in identities:
                    checked, mismatched = _verify_projective_identity(
                        logical_values, tuple(left), tuple(right)
                    )
                    exact_checks += checked
                    exact_mismatches += mismatched

            macro_events = tuple(event_by_source[gate.gate_id] for gate in group)
            baseline_frame = _append_active_corrections(
                baseline_frame,
                macro_events,
                correction_by_source,
                branch=branch,
            )
            partial_frame = _append_active_corrections(
                partial_frame,
                macro_events,
                correction_by_source,
                branch=branch,
            )
            clearing_frame = _append_active_corrections(
                (),
                macro_events,
                correction_by_source,
                branch=branch,
            )

        # Complete trailing source Clifford layers before recording final frames.
        for layer in sorted(source_cliffords):
            if layer in applied_clifford_layers:
                continue
            clifford_layer = source_cliffords[layer]
            baseline_frame = _conjugate_by_source_layer(baseline_frame, clifford_layer)
            partial_frame = _conjugate_by_source_layer(partial_frame, clifford_layer)
            clearing_frame = _conjugate_by_source_layer(clearing_frame, clifford_layer)

        final_frame_by_policy = {
            FramePolicy.FULL_CONJUGATION: baseline_frame,
            FramePolicy.BARE_PROPAGATION: baseline_frame,
            FramePolicy.FRAME_TRACKING: baseline_frame,
            FramePolicy.FULL_CLEARING: clearing_frame,
            FramePolicy.PARTIAL_CLEARING: partial_frame,
        }
        candidate_levels = 2 * len(groups)
        for policy in FramePolicy:
            totals = branch_totals[policy]
            accumulator = accumulators[policy]
            accumulator.cnot_occurrences.append(totals["cnot"])
            accumulator.cz_occurrences.append(totals["cz"])
            accumulator.cnot_batches.append(totals["cnot_batches"])
            accumulator.two_qubit_batches.append(totals["two_qubit_batches"])
            accumulator.layer_envelope.append(candidate_levels + totals["depth"])
            accumulator.max_ppm_weight.append(totals["max_ppm"])
            accumulator.incompatible_ppms.append(totals["incompatible"])
            accumulator.y_ppms.append(totals["y"])
            accumulator.max_frame_primitives.append(totals["max_frame"])
            accumulator.final_frame_primitives.append(len(final_frame_by_policy[policy]))

    h_target_total = sum(len({gate.target for gate in group}) for group in groups)
    policies = tuple(
        FramePolicyProfile(
            policy=policy,
            candidate_ppm_levels=2 * len(groups),
            literal_h_gate_occurrences=(
                0 if policy is FramePolicy.FRAME_TRACKING else 2 * h_target_total
            ),
            literal_h_batches=(0 if policy is FramePolicy.FRAME_TRACKING else 2 * len(groups)),
            literal_cnot_occurrences=_distribution(accumulators[policy].cnot_occurrences),
            literal_cz_occurrences=_distribution(accumulators[policy].cz_occurrences),
            literal_cnot_batches=_distribution(accumulators[policy].cnot_batches),
            literal_two_qubit_batches=_distribution(accumulators[policy].two_qubit_batches),
            serialized_logical_layer_envelope=_distribution(accumulators[policy].layer_envelope),
            maximum_presented_ppm_weight=_distribution(accumulators[policy].max_ppm_weight),
            incompatible_phase_one_ppm_count=_distribution(accumulators[policy].incompatible_ppms),
            y_containing_phase_one_ppm_count=_distribution(accumulators[policy].y_ppms),
            maximum_frame_primitive_count=_distribution(accumulators[policy].max_frame_primitives),
            final_frame_primitive_count=_distribution(accumulators[policy].final_frame_primitives),
            z_x_only_high_rate_family_admitted=(max(accumulators[policy].incompatible_ppms) == 0),
        )
        for policy in FramePolicy
    )
    partial_macros = tuple(
        PartialMacroProfile(
            macro_layer=index,
            ccx_count=len(group),
            distinct_h_target_count=len({gate.target for gate in group}),
            relevant_component_qubits=_distribution(values["component_qubits"]),
            materialized_cnot_occurrences=_distribution(values["materialized_cnot"]),
            retained_cnot_occurrences=_distribution(values["retained_cnot"]),
            presented_ppm_maximum_weight=_distribution(values["ppm_max"]),
        )
        for index, (group, values) in enumerate(zip(groups, macro_values, strict=True), start=1)
    )
    return PartialFrameClearingStudy(
        width=trace.width,
        source_trace_id=trace.trace_id,
        macro_depth=len(groups),
        macro_layer_sizes=tuple(len(group) for group in groups),
        branch_sample_count=branch_sample_count,
        branch_sample_seed=BRANCH_SAMPLE_SEED,
        policies=policies,
        partial_macro_profiles=partial_macros,
        ordered_factorization_status=EvidenceStatus.PROVED,
        width5_replay_branch_count=(min(16, branch_sample_count) if trace.width == 5 else 0),
        width5_projective_clifford_checks=exact_checks,
        width5_projective_clifford_mismatches=exact_mismatches,
        exact_identity_argument=(
            "For every resolved branch, the interaction-component partition has "
            "F_in = A R with disjoint support and [R,U_H]=0. Therefore "
            "(U_H A^dagger)F_in = U_H R = R U_H."
        ),
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {name: _jsonable(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def partial_frame_clearing_study_to_data(
    study: PartialFrameClearingStudy,
) -> dict[str, Any]:
    """Return a deterministic JSON-compatible representation."""

    return {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        **_jsonable(study),
    }


def dumps_partial_frame_clearing_study(study: PartialFrameClearingStudy) -> str:
    """Serialize the study deterministically."""

    return (
        json.dumps(
            partial_frame_clearing_study_to_data(study),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
