"""Exact small-width commutation-aware schedules for clean OOP-QCLA.

The scheduler operates in an architecture-independent coordinate.  One CCX
macro-layer contributes one resource-data ``ZZ`` candidate level and one
fresh-resource ``X`` readout level.  These levels are not QEC cycles or time.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import Enum
from itertools import pairwise
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGateKind
from ecdlp_ftqc.circuits.qcla_oop import (
    OopQclaGate,
    OopQclaStage,
    OopQclaTrace,
    build_oop_qcla_trace,
    dumps_oop_qcla_trace,
)
from ecdlp_ftqc.compiler.joint_direct_ccz import (
    CcxOperation,
    classify_ccx_pair,
)
from ecdlp_ftqc.metadata import EvidenceStatus

COMMUTATION_AWARE_QCLA_SCHEMA = (
    "ecdlp-ftqc/commutation-aware-clean-oop-qcla-small-width"
)
COMMUTATION_AWARE_QCLA_SCHEMA_VERSION = 1
COMMUTATION_AWARE_COORDINATE = (
    "architecture_independent_two_phase_direct_ccz_candidate_levels_not_time"
)


class CommutationAwareQclaError(ValueError):
    """Raised when a commutation-aware schedule violates its contract."""


class CommutationAwareVariant(str, Enum):
    """The two admitted alternatives to the immutable source baseline."""

    UNITARY = "commutation_aware_unitary"
    MEASURED_CLEANUP = "commutation_aware_measured_cleanup"


class DependencyReason(str, Enum):
    """Reasons that preserve source order between two CCX events."""

    NONCOMMUTING_TARGET_CONTROL = "noncommuting_target_control"
    SOURCE_CLIFFORD_BARRIER = "source_clifford_barrier"


@dataclass(frozen=True, slots=True)
class CcxPairDecision:
    """One exact pair decision in original source order."""

    left_source_gate_id: str
    right_source_gate_id: str
    overlap_kind: str
    commutes: bool
    shared_values: tuple[str, ...]
    source_clifford_barrier_layers: tuple[int, ...]
    dependency_reasons: tuple[str, ...]
    same_macro_admitted: bool
    truth_table_rows_checked: int
    evidence_status: EvidenceStatus = EvidenceStatus.PROVED

    def __post_init__(self) -> None:
        if not self.left_source_gate_id or not self.right_source_gate_id:
            raise CommutationAwareQclaError("pair decision requires gate IDs")
        if self.left_source_gate_id == self.right_source_gate_id:
            raise CommutationAwareQclaError("pair decision cannot be reflexive")
        if self.truth_table_rows_checked not in {8, 16, 32, 64}:
            raise CommutationAwareQclaError("unexpected CCX pair truth-table size")
        expected_reasons: set[str] = set()
        if not self.commutes:
            expected_reasons.add(DependencyReason.NONCOMMUTING_TARGET_CONTROL.value)
        if self.source_clifford_barrier_layers:
            expected_reasons.add(DependencyReason.SOURCE_CLIFFORD_BARRIER.value)
        if set(self.dependency_reasons) != expected_reasons:
            raise CommutationAwareQclaError("pair dependency reasons are incomplete")
        if self.same_macro_admitted != (not expected_reasons and self.commutes):
            raise CommutationAwareQclaError("same-macro admission is inconsistent")


@dataclass(frozen=True, slots=True)
class CcxDependency:
    """A directed dependency in the exact CCX macro-layer DAG."""

    predecessor: str
    successor: str
    reasons: tuple[str, ...]
    shared_values: tuple[str, ...]
    source_clifford_barrier_layers: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.predecessor or not self.successor:
            raise CommutationAwareQclaError("dependency endpoints are required")
        if self.predecessor == self.successor or not self.reasons:
            raise CommutationAwareQclaError("invalid CCX dependency")


@dataclass(frozen=True, slots=True)
class CcxMacroLayer:
    """One jointly executable set under the approved common-frame rule."""

    layer_index: int
    source_gate_ids: tuple[str, ...]
    common_incoming_frame: str
    phase_one_candidate_level: int
    phase_two_candidate_level: int
    phase_one_axis: str
    phase_two_axis: str
    resource_triples: tuple[tuple[str, str, str], ...]
    event_to_event_reaction_edges: tuple[tuple[str, str], ...] = ()
    evidence_status: EvidenceStatus = EvidenceStatus.PROVED

    def __post_init__(self) -> None:
        if self.layer_index < 1 or not self.source_gate_ids:
            raise CommutationAwareQclaError("macro-layer must be nonempty")
        if len(self.source_gate_ids) != len(set(self.source_gate_ids)):
            raise CommutationAwareQclaError("macro-layer event IDs must be unique")
        if self.common_incoming_frame != "macro_layer_entry_frame":
            raise CommutationAwareQclaError("unsupported common-frame convention")
        if (
            self.phase_one_candidate_level != 2 * self.layer_index - 1
            or self.phase_two_candidate_level != 2 * self.layer_index
            or self.phase_one_axis != "Z"
            or self.phase_two_axis != "X"
        ):
            raise CommutationAwareQclaError("invalid two-phase macro-layer record")
        if len(self.resource_triples) != len(self.source_gate_ids):
            raise CommutationAwareQclaError("one resource triple is required per CCX")
        flattened = tuple(value for triple in self.resource_triples for value in triple)
        if len(flattened) != len(set(flattened)):
            raise CommutationAwareQclaError("CCZ resource values must be globally fresh")
        if self.event_to_event_reaction_edges:
            raise CommutationAwareQclaError(
                "joint macro-layer cannot contain event-to-event reaction edges"
            )


@dataclass(frozen=True, slots=True)
class MeasurementCleanup:
    """One admitted destructive-X prefix-AND cleanup."""

    source_gate_id_replaced: str
    producer_source_gate_id: str
    last_quantum_use_source_gate_id: str
    controls: tuple[str, str]
    measured_target: str
    measurement_operation_id: str
    outcome_token: str
    conditional_frame_update: str
    later_source_gate_ids: tuple[str, ...]
    frame_propagating_gate_ids: tuple[str, ...]
    later_ppm_source_gate_ids: tuple[str, ...]
    final_frame_support_upper_bound: tuple[str, ...]
    release_count: int = 1
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL

    def __post_init__(self) -> None:
        if len(set(self.controls)) != 2 or self.measured_target in self.controls:
            raise CommutationAwareQclaError("cleanup support must contain three values")
        if not self.measured_target.startswith("p:"):
            raise CommutationAwareQclaError("cleanup target must be prefix scratch")
        if self.release_count != 1:
            raise CommutationAwareQclaError("cleanup target must be released once")
        expected = (
            f"CZ({self.controls[0]},{self.controls[1]})^{{{self.outcome_token}}}"
        )
        if self.conditional_frame_update != expected:
            raise CommutationAwareQclaError("cleanup correction is noncanonical")
        if self.later_ppm_source_gate_ids:
            raise CommutationAwareQclaError(
                "small-width cleanup must follow the final CCX use"
            )
        if not set(self.controls) <= set(self.final_frame_support_upper_bound):
            raise CommutationAwareQclaError("cleanup frame lost a control")


@dataclass(frozen=True, slots=True)
class MacroReactionBoundary:
    """Conservative classical frontier between consecutive macro-layers."""

    after_macro_layer: int
    before_macro_layer: int
    predecessor_source_gate_ids: tuple[str, ...]
    predecessor_outcome_tokens: tuple[str, ...]
    successor_source_gate_ids: tuple[str, ...]
    reason: str = "common_frame_update_required_before_next_macro_entry"
    outcome_subset_status: EvidenceStatus = EvidenceStatus.CHECK
    duration_seconds: None = None

    def __post_init__(self) -> None:
        if self.before_macro_layer != self.after_macro_layer + 1:
            raise CommutationAwareQclaError("reaction boundary must join adjacent layers")
        if not self.predecessor_source_gate_ids or not self.successor_source_gate_ids:
            raise CommutationAwareQclaError("reaction boundary endpoints are required")
        if len(self.predecessor_outcome_tokens) != 6 * len(
            self.predecessor_source_gate_ids
        ):
            raise CommutationAwareQclaError("reaction frontier must retain six outcomes per CCX")
        if self.outcome_subset_status is not EvidenceStatus.CHECK:
            raise CommutationAwareQclaError("reaction frontier is conservative, not minimal")
        if self.duration_seconds is not None:
            raise CommutationAwareQclaError("reaction duration remains unresolved")


@dataclass(frozen=True, slots=True)
class ExactCcxSchedule:
    """One exact unlimited-capacity logical CCX schedule."""

    variant: CommutationAwareVariant
    width: int
    scheduled_ccx_count: int
    measured_cleanup_count: int
    pair_decisions: tuple[CcxPairDecision, ...]
    dependencies: tuple[CcxDependency, ...]
    macro_layers: tuple[CcxMacroLayer, ...]
    reaction_boundaries: tuple[MacroReactionBoundary, ...]
    cleanup_records: tuple[MeasurementCleanup, ...]
    macro_depth: int
    direct_ccz_candidate_levels: int
    exact_lower_bound_macro_depth: int
    critical_path_source_gate_ids: tuple[str, ...]
    optimality_status: EvidenceStatus
    candidate_level_coordinate: str = COMMUTATION_AWARE_COORDINATE
    complete_native_schedule: bool = False
    native_cycles: int | None = None
    runtime_seconds: float | None = None
    physical_qubits: int | None = None
    failure_probability: float | None = None

    def __post_init__(self) -> None:
        if not 2 <= self.width <= 8:
            raise CommutationAwareQclaError("exact study is restricted to widths 2--8")
        if self.scheduled_ccx_count != sum(
            len(layer.source_gate_ids) for layer in self.macro_layers
        ):
            raise CommutationAwareQclaError("scheduled CCX membership is incomplete")
        if self.measured_cleanup_count != len(self.cleanup_records):
            raise CommutationAwareQclaError("cleanup count mismatch")
        if self.macro_depth != len(self.macro_layers):
            raise CommutationAwareQclaError("macro-depth mismatch")
        if len(self.reaction_boundaries) != max(0, self.macro_depth - 1):
            raise CommutationAwareQclaError("reaction boundary count mismatch")
        if self.direct_ccz_candidate_levels != 2 * self.macro_depth:
            raise CommutationAwareQclaError("two-phase candidate-level count changed")
        if (
            self.exact_lower_bound_macro_depth != self.macro_depth
            or self.optimality_status is not EvidenceStatus.PROVED
        ):
            raise CommutationAwareQclaError("exact schedule must meet its lower bound")
        if self.candidate_level_coordinate != COMMUTATION_AWARE_COORDINATE:
            raise CommutationAwareQclaError("candidate coordinate changed")
        finite = (
            self.native_cycles,
            self.runtime_seconds,
            self.physical_qubits,
            self.failure_probability,
        )
        if self.complete_native_schedule or any(value is not None for value in finite):
            raise CommutationAwareQclaError("finite-backend outputs must remain null")


@dataclass(frozen=True, slots=True)
class WidthScheduleComparison:
    """Immutable baseline and two exact alternatives for one width."""

    width: int
    source_trace_id: str
    source_trace_sha256: str
    source_ccx_count: int
    source_toffoli_bearing_layers: int
    source_aligned_candidate_levels: int
    source_aligned_macro_layers: tuple[tuple[str, ...], ...]
    source_clifford_barriers: tuple[tuple[int, tuple[str, ...]], ...]
    unitary: ExactCcxSchedule
    measured_cleanup: ExactCcxSchedule

    def __post_init__(self) -> None:
        if self.width != self.unitary.width or self.width != self.measured_cleanup.width:
            raise CommutationAwareQclaError("comparison width mismatch")
        if self.source_ccx_count != self.unitary.scheduled_ccx_count:
            raise CommutationAwareQclaError("unitary schedule changed the CCX count")
        if self.source_aligned_candidate_levels != 2 * self.source_toffoli_bearing_layers:
            raise CommutationAwareQclaError("source-aligned two-phase count changed")
        if len(self.source_trace_sha256) != 64:
            raise CommutationAwareQclaError("source trace hash must be SHA-256")


@dataclass(frozen=True, slots=True)
class SmallWidthCommutationAwareStudy:
    """Canonical deterministic result for widths 2--8."""

    task_id: str
    experiment_id: str
    widths: tuple[int, ...]
    comparisons: tuple[WidthScheduleComparison, ...]
    schema: str = COMMUTATION_AWARE_QCLA_SCHEMA
    schema_version: int = COMMUTATION_AWARE_QCLA_SCHEMA_VERSION
    validation_status: str = "pending_independent_replay"

    def __post_init__(self) -> None:
        if self.task_id != "T-20260906-003" or self.experiment_id != "E-20260906-003":
            raise CommutationAwareQclaError("task or experiment ID changed")
        if self.widths != tuple(range(2, 9)):
            raise CommutationAwareQclaError("study must cover every width 2--8")
        if tuple(item.width for item in self.comparisons) != self.widths:
            raise CommutationAwareQclaError("comparison coverage changed")
        if (
            self.schema != COMMUTATION_AWARE_QCLA_SCHEMA
            or self.schema_version != COMMUTATION_AWARE_QCLA_SCHEMA_VERSION
        ):
            raise CommutationAwareQclaError("unsupported study schema")


def _operation(gate: OopQclaGate) -> CcxOperation:
    if gate.kind is not QclaGateKind.TOFFOLI:
        raise CommutationAwareQclaError("only Toffoli gates map to CCX events")
    return CcxOperation(
        source_gate_id=gate.gate_id,
        controls=(gate.controls[0], gate.controls[1]),
        target=gate.target,
        source_algorithmic_layer=gate.algorithmic_layer,
        source_stage=gate.stage.value,
    )


def _clifford_barriers(trace: OopQclaTrace) -> tuple[tuple[int, tuple[str, ...]], ...]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            grouped[gate.algorithmic_layer].append(gate.gate_id)
    return tuple((layer, tuple(grouped[layer])) for layer in sorted(grouped))


def _pair_decisions(
    trace: OopQclaTrace,
    operations: tuple[CcxOperation, ...],
) -> tuple[CcxPairDecision, ...]:
    cnot_layers = tuple(layer for layer, _ in _clifford_barriers(trace))
    decisions: list[CcxPairDecision] = []
    for left_index, left in enumerate(operations):
        for right in operations[left_index + 1 :]:
            certificate = classify_ccx_pair(left, right)
            barriers = tuple(
                layer
                for layer in cnot_layers
                if left.source_algorithmic_layer < layer < right.source_algorithmic_layer
            )
            reasons: list[str] = []
            if not certificate.commutes:
                reasons.append(DependencyReason.NONCOMMUTING_TARGET_CONTROL.value)
            if barriers:
                reasons.append(DependencyReason.SOURCE_CLIFFORD_BARRIER.value)
            decisions.append(
                CcxPairDecision(
                    left_source_gate_id=left.source_gate_id,
                    right_source_gate_id=right.source_gate_id,
                    overlap_kind=certificate.overlap_kind.value,
                    commutes=certificate.commutes,
                    shared_values=tuple(
                        sorted(set(left.logical_support) & set(right.logical_support))
                    ),
                    source_clifford_barrier_layers=barriers,
                    dependency_reasons=tuple(reasons),
                    same_macro_admitted=not reasons and certificate.commutes,
                    truth_table_rows_checked=certificate.truth_table_rows_checked,
                )
            )
    return tuple(decisions)


def _dependencies(
    decisions: Iterable[CcxPairDecision],
) -> tuple[CcxDependency, ...]:
    return tuple(
        CcxDependency(
            predecessor=decision.left_source_gate_id,
            successor=decision.right_source_gate_id,
            reasons=decision.dependency_reasons,
            shared_values=decision.shared_values,
            source_clifford_barrier_layers=(
                decision.source_clifford_barrier_layers
            ),
        )
        for decision in decisions
        if decision.dependency_reasons
    )


def _exact_layers(
    operations: tuple[CcxOperation, ...],
    dependencies: tuple[CcxDependency, ...],
) -> tuple[tuple[tuple[CcxOperation, ...], ...], tuple[str, ...]]:
    by_id = {operation.source_gate_id: operation for operation in operations}
    predecessors: dict[str, list[str]] = defaultdict(list)
    for dependency in dependencies:
        predecessors[dependency.successor].append(dependency.predecessor)
    depth: dict[str, int] = {}
    witness_parent: dict[str, str | None] = {}
    position = {operation.source_gate_id: index for index, operation in enumerate(operations)}
    for operation in operations:
        candidates = predecessors[operation.source_gate_id]
        if not candidates:
            depth[operation.source_gate_id] = 1
            witness_parent[operation.source_gate_id] = None
            continue
        parent = max(candidates, key=lambda item: (depth[item], -position[item]))
        depth[operation.source_gate_id] = depth[parent] + 1
        witness_parent[operation.source_gate_id] = parent
    maximum = max(depth.values(), default=0)
    grouped = tuple(
        tuple(
            operation
            for operation in operations
            if depth[operation.source_gate_id] == layer
        )
        for layer in range(1, maximum + 1)
    )
    if any(not group for group in grouped):
        raise CommutationAwareQclaError("exact schedule contains an empty layer")
    if not operations:
        return (), ()
    endpoint = max(
        operations,
        key=lambda item: (depth[item.source_gate_id], -position[item.source_gate_id]),
    ).source_gate_id
    path: list[str] = []
    cursor: str | None = endpoint
    while cursor is not None:
        path.append(cursor)
        cursor = witness_parent[cursor]
    path.reverse()
    if len(path) != maximum or any(item not in by_id for item in path):
        raise CommutationAwareQclaError("critical-path witness is invalid")
    return grouped, tuple(path)


def _resource_triple(width: int, gate_id: str) -> tuple[str, str, str]:
    prefix = f"commutation-aware:n{width}:{gate_id}:ccz-resource"
    return (f"{prefix}:0", f"{prefix}:1", f"{prefix}:2")


def _macro_layers(
    width: int,
    groups: tuple[tuple[CcxOperation, ...], ...],
    decisions: tuple[CcxPairDecision, ...],
) -> tuple[CcxMacroLayer, ...]:
    decision_by_pair = {
        (decision.left_source_gate_id, decision.right_source_gate_id): decision
        for decision in decisions
    }
    result: list[CcxMacroLayer] = []
    for index, group in enumerate(groups, start=1):
        for left_index, left in enumerate(group):
            for right in group[left_index + 1 :]:
                decision = decision_by_pair[(left.source_gate_id, right.source_gate_id)]
                if not decision.same_macro_admitted:
                    raise CommutationAwareQclaError(
                        "exact layer contains a non-admitted CCX pair"
                    )
        result.append(
            CcxMacroLayer(
                layer_index=index,
                source_gate_ids=tuple(item.source_gate_id for item in group),
                common_incoming_frame="macro_layer_entry_frame",
                phase_one_candidate_level=2 * index - 1,
                phase_two_candidate_level=2 * index,
                phase_one_axis="Z",
                phase_two_axis="X",
                resource_triples=tuple(
                    _resource_triple(width, operation.source_gate_id)
                    for operation in group
                ),
            )
        )
    flattened = tuple(
        value
        for layer in result
        for triple in layer.resource_triples
        for value in triple
    )
    if len(flattened) != len(set(flattened)):
        raise CommutationAwareQclaError("resource values were reused across layers")
    return tuple(result)


def _cleanup_records(
    trace: OopQclaTrace,
    removed: tuple[OopQclaGate, ...],
) -> tuple[MeasurementCleanup, ...]:
    positions = {gate.gate_id: index for index, gate in enumerate(trace.gates)}
    removed_ids = {gate.gate_id for gate in removed}
    result: list[MeasurementCleanup] = []
    for cleanup in removed:
        producer = next(
            (
                gate
                for gate in trace.gates[: positions[cleanup.gate_id]]
                if gate.kind is QclaGateKind.TOFFOLI
                and gate.stage is OopQclaStage.PREFIX_PROPAGATE
                and gate.controls == cleanup.controls
                and gate.target == cleanup.target
            ),
            None,
        )
        if producer is None:
            raise CommutationAwareQclaError("cleanup has no matching producer")
        prior_uses = tuple(
            gate
            for gate in trace.gates[: positions[cleanup.gate_id]]
            if cleanup.target in gate.logical_support and gate.gate_id != producer.gate_id
        )
        if not prior_uses:
            raise CommutationAwareQclaError("cleanup target has no intervening use")
        later_uses = tuple(
            gate
            for gate in trace.gates[positions[cleanup.gate_id] + 1 :]
            if cleanup.target in gate.logical_support
        )
        if later_uses:
            raise CommutationAwareQclaError("cleanup is not the final target use")
        suffix = tuple(
            gate
            for gate in trace.gates[positions[cleanup.gate_id] + 1 :]
            if gate.gate_id not in removed_ids
        )
        active_support = set(cleanup.controls)
        propagating: list[str] = []
        for gate in suffix:
            support = set(gate.logical_support)
            if support & active_support:
                propagating.append(gate.gate_id)
                active_support.update(support)
        token = f"commutation-aware:n{trace.width}:{cleanup.gate_id}:outcome:x"
        result.append(
            MeasurementCleanup(
                source_gate_id_replaced=cleanup.gate_id,
                producer_source_gate_id=producer.gate_id,
                last_quantum_use_source_gate_id=prior_uses[-1].gate_id,
                controls=(cleanup.controls[0], cleanup.controls[1]),
                measured_target=cleanup.target,
                measurement_operation_id=(
                    f"commutation-aware:n{trace.width}:{cleanup.gate_id}:measure-x"
                ),
                outcome_token=token,
                conditional_frame_update=(
                    f"CZ({cleanup.controls[0]},{cleanup.controls[1]})^{{{token}}}"
                ),
                later_source_gate_ids=tuple(gate.gate_id for gate in suffix),
                frame_propagating_gate_ids=tuple(propagating),
                later_ppm_source_gate_ids=tuple(
                    gate.gate_id
                    for gate in suffix
                    if gate.kind is QclaGateKind.TOFFOLI
                ),
                final_frame_support_upper_bound=tuple(sorted(active_support)),
            )
        )
    return tuple(result)


def _outcome_tokens(width: int, gate_id: str) -> tuple[str, ...]:
    roles = ("zz_0", "zz_1", "zz_2", "x_0", "x_1", "x_2")
    return tuple(
        f"commutation-aware:n{width}:{gate_id}:outcome:{role}" for role in roles
    )


def _reaction_boundaries(
    width: int, layers: tuple[CcxMacroLayer, ...]
) -> tuple[MacroReactionBoundary, ...]:
    return tuple(
        MacroReactionBoundary(
            after_macro_layer=left.layer_index,
            before_macro_layer=right.layer_index,
            predecessor_source_gate_ids=left.source_gate_ids,
            predecessor_outcome_tokens=tuple(
                token
                for gate_id in left.source_gate_ids
                for token in _outcome_tokens(width, gate_id)
            ),
            successor_source_gate_ids=right.source_gate_ids,
        )
        for left, right in pairwise(layers)
    )


def _build_schedule(
    trace: OopQclaTrace,
    variant: CommutationAwareVariant,
) -> ExactCcxSchedule:
    source_ccx = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    removed = (
        tuple(gate for gate in source_ccx if gate.stage is OopQclaStage.PREFIX_UNCOMPUTE)
        if variant is CommutationAwareVariant.MEASURED_CLEANUP
        else ()
    )
    removed_ids = {gate.gate_id for gate in removed}
    operations = tuple(_operation(gate) for gate in source_ccx if gate.gate_id not in removed_ids)
    decisions = _pair_decisions(trace, operations)
    dependencies = _dependencies(decisions)
    groups, critical_path = _exact_layers(operations, dependencies)
    layers = _macro_layers(trace.width, groups, decisions)
    cleanups = _cleanup_records(trace, removed)
    return ExactCcxSchedule(
        variant=variant,
        width=trace.width,
        scheduled_ccx_count=len(operations),
        measured_cleanup_count=len(cleanups),
        pair_decisions=decisions,
        dependencies=dependencies,
        macro_layers=layers,
        reaction_boundaries=_reaction_boundaries(trace.width, layers),
        cleanup_records=cleanups,
        macro_depth=len(layers),
        direct_ccz_candidate_levels=2 * len(layers),
        exact_lower_bound_macro_depth=len(critical_path),
        critical_path_source_gate_ids=critical_path,
        optimality_status=EvidenceStatus.PROVED,
    )


def build_width_schedule_comparison(width: int) -> WidthScheduleComparison:
    """Build one exact comparison without changing the source trace."""

    if not 2 <= width <= 8:
        raise CommutationAwareQclaError("exact comparison requires width 2--8")
    trace = build_oop_qcla_trace(width)
    source_ccx = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    by_layer: dict[int, list[str]] = defaultdict(list)
    for gate in source_ccx:
        by_layer[gate.algorithmic_layer].append(gate.gate_id)
    source_layers = tuple(tuple(by_layer[layer]) for layer in sorted(by_layer))
    source_dump = dumps_oop_qcla_trace(trace)
    return WidthScheduleComparison(
        width=width,
        source_trace_id=trace.trace_id,
        source_trace_sha256=hashlib.sha256(source_dump.encode("utf-8")).hexdigest(),
        source_ccx_count=len(source_ccx),
        source_toffoli_bearing_layers=len(source_layers),
        source_aligned_candidate_levels=2 * len(source_layers),
        source_aligned_macro_layers=source_layers,
        source_clifford_barriers=_clifford_barriers(trace),
        unitary=_build_schedule(trace, CommutationAwareVariant.UNITARY),
        measured_cleanup=_build_schedule(
            trace, CommutationAwareVariant.MEASURED_CLEANUP
        ),
    )


def build_small_width_commutation_aware_study() -> SmallWidthCommutationAwareStudy:
    """Build the complete deterministic widths-2--8 study."""

    widths = tuple(range(2, 9))
    return SmallWidthCommutationAwareStudy(
        task_id="T-20260906-003",
        experiment_id="E-20260906-003",
        widths=widths,
        comparisons=tuple(build_width_schedule_comparison(width) for width in widths),
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def small_width_commutation_aware_study_to_data(
    study: SmallWidthCommutationAwareStudy,
) -> dict[str, Any]:
    """Return canonical JSON-compatible study data."""

    data = _jsonable(asdict(study))
    if not isinstance(data, dict):
        raise CommutationAwareQclaError("study serialization failed")
    return data


def dumps_small_width_commutation_aware_study(
    study: SmallWidthCommutationAwareStudy,
) -> str:
    """Serialize the study deterministically."""

    return json.dumps(
        small_width_commutation_aware_study_to_data(study),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
