"""Compact commutation-aware scaling certificate for width-256 clean OOP-QCLA.

The result is architecture independent.  Macro layers and their two direct-CCZ
phases are logical candidate coordinates, never QEC cycles or elapsed time.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGateKind
from ecdlp_ftqc.circuits.qcla_oop import (
    OopQclaGate,
    OopQclaStage,
    OopQclaTrace,
    build_oop_qcla_trace,
    dumps_oop_qcla_trace,
)
from ecdlp_ftqc.compiler.direct_ccz import DirectCczEventTrace
from ecdlp_ftqc.metadata import EvidenceStatus

from . import direct_ccz_ppm_support_certificate as support_model

WIDTH256_COMMUTATION_AWARE_SCHEMA = (
    "ecdlp-ftqc/width256-commutation-aware-clean-oop-qcla"
)
WIDTH256_COMMUTATION_AWARE_SCHEMA_VERSION = 1
CANDIDATE_COORDINATE = (
    "architecture_independent_two_phase_direct_ccz_candidate_levels_not_time"
)


class Width256CommutationAwareError(ValueError):
    """Raised when the compact scaling certificate violates its contract."""


class ScalingVariant(str, Enum):
    """The two structural schedules compared with the source baseline."""

    UNITARY = "commutation_aware_unitary"
    MEASURED_CLEANUP = "commutation_aware_measured_cleanup"


@dataclass(frozen=True, slots=True)
class CompactDependencyNode:
    """One linear-size longest-path record in source CCX order."""

    source_gate_id: str
    source_position: int
    source_algorithmic_layer: int
    source_stage: str
    segment_index: int
    controls: tuple[str, str]
    target: str
    macro_rank: int
    witness_predecessor: str | None
    witness_reasons: tuple[str, ...]
    witness_barrier_layers: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            not self.source_gate_id
            or self.source_position < 0
            or self.source_algorithmic_layer < 1
            or self.segment_index < 0
            or len(set(self.controls)) != 2
            or self.target in self.controls
            or self.macro_rank < 1
        ):
            raise Width256CommutationAwareError("invalid compact dependency node")
        if (self.witness_predecessor is None) != (not self.witness_reasons):
            raise Width256CommutationAwareError("witness endpoint and reasons disagree")


@dataclass(frozen=True, slots=True)
class PairOracleSummary:
    """All-pair validation counts without a quadratic serialized table."""

    operation_count: int
    pair_count: int
    dependency_pair_count: int
    admitted_pair_count: int
    noncommuting_pair_count: int
    barrier_pair_count: int
    overlap_kind_counts: tuple[tuple[str, int], ...]
    decision_stream_sha256: str
    pair_records_materialized: bool
    compact_rank_match: bool
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        expected = self.operation_count * (self.operation_count - 1) // 2
        if (
            self.pair_count != expected
            or self.dependency_pair_count + self.admitted_pair_count != expected
            or len(self.decision_stream_sha256) != 64
            or self.pair_records_materialized
            or not self.compact_rank_match
            or self.evidence_status is not EvidenceStatus.PROVED
        ):
            raise Width256CommutationAwareError("invalid full-pair oracle summary")


@dataclass(frozen=True, slots=True)
class CleanupAxisWitness:
    """One branch proving that tracked cleanup X is not X-only."""

    measured_target: str
    last_quantum_use_source_gate_id: str
    other_control: str
    outcome_token: str
    incoming_frame_term: str
    presented_measurement: str
    mixed_axis: bool = True
    evidence_status: EvidenceStatus = EvidenceStatus.PROVED

    def __post_init__(self) -> None:
        if (
            not self.measured_target.startswith("p:")
            or not self.last_quantum_use_source_gate_id
            or not self.other_control
            or not self.outcome_token
            or self.incoming_frame_term
            != f"CZ({self.measured_target},{self.other_control})^{{{self.outcome_token}}}"
            or self.presented_measurement
            != f"X({self.measured_target}) Z({self.other_control})"
            or not self.mixed_axis
        ):
            raise Width256CommutationAwareError("invalid cleanup mixed-axis witness")


@dataclass(frozen=True, slots=True)
class CleanupCertificate:
    """Lifecycle and axis-admission result for one removed prefix uncompute."""

    source_gate_id_replaced: str
    producer_source_gate_id: str
    last_quantum_use_source_gate_id: str
    controls: tuple[str, str]
    measured_target: str
    measurement_after_macro_layer: int
    candidate_level_if_axis_safe: int
    conditional_frame_update: str
    final_frame_support_upper_bound: tuple[str, ...]
    frame_propagating_source_gate_count: int
    frame_propagating_source_gate_id_sha256: str
    later_ppm_count: int
    later_ppm_source_gate_id_sha256: str
    released_target_later_ppm_use_count: int
    read_only_between_producer_and_cleanup: bool
    final_source_use: bool
    release_count: int
    axis_witness: CleanupAxisWitness
    admitted_to_z_x_only_high_rate_ppm: bool
    evidence_status: EvidenceStatus = EvidenceStatus.PROVED

    def __post_init__(self) -> None:
        if (
            self.measurement_after_macro_layer < 1
            or self.candidate_level_if_axis_safe != 2 * self.measurement_after_macro_layer
            or len(set(self.controls)) != 2
            or self.measured_target in self.controls
            or not self.read_only_between_producer_and_cleanup
            or not self.final_source_use
            or self.release_count != 1
            or self.frame_propagating_source_gate_count < 0
            or len(self.frame_propagating_source_gate_id_sha256) != 64
            or self.later_ppm_count < 0
            or len(self.later_ppm_source_gate_id_sha256) != 64
            or self.released_target_later_ppm_use_count != 0
            or self.axis_witness.measured_target != self.measured_target
            or self.admitted_to_z_x_only_high_rate_ppm
        ):
            raise Width256CommutationAwareError("invalid cleanup certificate")


@dataclass(frozen=True, slots=True)
class CandidateLevelEnvelope:
    """Exact logical demand and support envelope for one candidate level."""

    candidate_level: int
    macro_layer: int
    phase: int
    axis: str
    source_gate_ids: tuple[str, ...]
    direct_ccz_event_count: int
    fresh_ccz_resource_count: int
    logical_ppm_count: int
    unique_target_h_count: int
    possible_support_union_size: int
    possible_support_union_sha256: str
    maximum_ppm_weight_upper_bound: int
    total_possible_support_incidence: int
    maximum_possible_contact_count: int
    maximum_possible_contact_logical_values: tuple[str, ...]
    branch_dependent_profile_count: int
    possible_support_exact: bool
    possible_union_is_simultaneous_weight: bool
    coordinate: str = support_model.SUPPORT_COORDINATE
    evidence_status: EvidenceStatus = EvidenceStatus.PROVED

    def __post_init__(self) -> None:
        if (
            self.phase not in {1, 2}
            or self.axis != {1: "Z", 2: "X"}[self.phase]
            or self.candidate_level != 2 * self.macro_layer - (2 - self.phase)
            or self.direct_ccz_event_count != len(self.source_gate_ids)
            or self.fresh_ccz_resource_count != self.direct_ccz_event_count
            or self.logical_ppm_count != 3 * self.direct_ccz_event_count
            or self.unique_target_h_count < 0
            or self.possible_support_union_size < self.maximum_ppm_weight_upper_bound
            or len(self.possible_support_union_sha256) != 64
            or not self.possible_support_exact
            or self.possible_union_is_simultaneous_weight
        ):
            raise Width256CommutationAwareError("invalid candidate-level envelope")


@dataclass(frozen=True, slots=True)
class LiveValueInterval:
    """One prefix scratch lifetime in macro-layer coordinates."""

    logical_value: str
    birth_macro_layer: int
    final_quantum_use_macro_layer: int
    release_macro_layer: int
    release_kind: str


@dataclass(frozen=True, slots=True)
class LiveValueEnvelope:
    """Source-value live demand, excluding fresh per-event CCZ resources."""

    persistent_input_output_values: int
    prefix_scratch_values: int
    fully_resident_source_values: int
    peak_live_source_values: int
    peak_live_macro_layers: tuple[int, ...]
    intervals: tuple[LiveValueInterval, ...]
    coordinate: str = "logical_source_values_not_physical_qubits"

    def __post_init__(self) -> None:
        if (
            self.fully_resident_source_values
            != self.persistent_input_output_values + self.prefix_scratch_values
            or self.peak_live_source_values > self.fully_resident_source_values
            or len(self.intervals) != self.prefix_scratch_values
        ):
            raise Width256CommutationAwareError("invalid live-value envelope")


@dataclass(frozen=True, slots=True)
class Width256VariantResult:
    """One compact exact CCX schedule and its qualified PPM implications."""

    variant: ScalingVariant
    scheduled_ccx_count: int
    removed_cleanup_ccx_count: int
    proposed_cleanup_count: int
    dependency_nodes: tuple[CompactDependencyNode, ...]
    macro_layers: tuple[tuple[str, ...], ...]
    macro_depth: int
    exact_lower_bound_macro_depth: int
    critical_path_source_gate_ids: tuple[str, ...]
    direct_ccz_candidate_levels: int
    complete_logical_candidate_levels: int | None
    candidate_levels: tuple[CandidateLevelEnvelope, ...]
    cleanup_certificates: tuple[CleanupCertificate, ...]
    cleanup_axis_safe: bool
    selected_for_z_x_only_high_rate_analysis: bool
    fallback_variant: str | None
    pair_oracle: PairOracleSummary
    live_values: LiveValueEnvelope
    retained_inter_macro_outcome_count: int
    outstanding_cleanup_outcome_count: int
    cleanup_frame_pair_interaction_count: int
    maximum_cleanup_frame_contact_count: int
    optimality_status: EvidenceStatus
    candidate_coordinate: str = CANDIDATE_COORDINATE
    complete_native_schedule: bool = False
    native_cycles: int | None = None
    runtime_seconds: float | None = None
    physical_qubits: int | None = None
    failure_probability: float | None = None

    def __post_init__(self) -> None:
        if (
            self.scheduled_ccx_count != len(self.dependency_nodes)
            or self.macro_depth != len(self.macro_layers)
            or self.exact_lower_bound_macro_depth != self.macro_depth
            or self.direct_ccz_candidate_levels != 2 * self.macro_depth
            or len(self.candidate_levels) != self.direct_ccz_candidate_levels
            or self.proposed_cleanup_count != len(self.cleanup_certificates)
            or self.outstanding_cleanup_outcome_count
            != self.removed_cleanup_ccx_count
            or self.optimality_status is not EvidenceStatus.PROVED
            or self.candidate_coordinate != CANDIDATE_COORDINATE
        ):
            raise Width256CommutationAwareError("invalid width-256 variant result")
        finite = (
            self.native_cycles,
            self.runtime_seconds,
            self.physical_qubits,
            self.failure_probability,
        )
        if self.complete_native_schedule or any(item is not None for item in finite):
            raise Width256CommutationAwareError("finite backend outputs must remain null")
        if self.variant is ScalingVariant.UNITARY:
            if (
                self.cleanup_certificates
                or not self.cleanup_axis_safe
                or not self.selected_for_z_x_only_high_rate_analysis
                or self.fallback_variant is not None
                or self.complete_logical_candidate_levels
                != self.direct_ccz_candidate_levels
            ):
                raise Width256CommutationAwareError("unitary selection metadata changed")
        elif (
            self.cleanup_axis_safe
            or self.selected_for_z_x_only_high_rate_analysis
            or self.fallback_variant != ScalingVariant.UNITARY.value
            or self.complete_logical_candidate_levels
            != self.direct_ccz_candidate_levels
            or self.removed_cleanup_ccx_count != 0
        ):
            raise Width256CommutationAwareError("unsafe cleanup must fail closed")


@dataclass(frozen=True, slots=True)
class Width256CommutationAwareStudy:
    """Canonical width-256 comparison and bounded compact-recurrence bridge."""

    task_id: str
    experiment_id: str
    width: int
    source_trace_id: str
    source_trace_sha256: str
    source_ccx_count: int
    source_cnot_count: int
    source_toffoli_bearing_layers: int
    source_aligned_candidate_levels: int
    source_cnot_layer_demands: tuple[tuple[int, int], ...]
    compact_bridge_widths_2_to_8: tuple[tuple[int, int, int], ...]
    unitary: Width256VariantResult
    measured_cleanup: Width256VariantResult
    selected_variant: str
    validation_status: str
    schema: str = WIDTH256_COMMUTATION_AWARE_SCHEMA
    schema_version: int = WIDTH256_COMMUTATION_AWARE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            self.task_id != "T-20260906-004"
            or self.experiment_id != "E-20260906-004"
            or self.width != 256
            or self.source_ccx_count != 1229
            or self.source_toffoli_bearing_layers != 17
            or self.source_aligned_candidate_levels != 34
            or self.selected_variant != ScalingVariant.UNITARY.value
            or self.schema != WIDTH256_COMMUTATION_AWARE_SCHEMA
            or self.schema_version != WIDTH256_COMMUTATION_AWARE_SCHEMA_VERSION
        ):
            raise Width256CommutationAwareError("width-256 study headline changed")


def _cnot_layers(trace: OopQclaTrace) -> tuple[int, ...]:
    return tuple(
        sorted(
            {
                gate.algorithmic_layer
                for gate in trace.gates
                if gate.kind is QclaGateKind.CNOT
            }
        )
    )


def _ccx_gates(trace: OopQclaTrace, *, measured: bool) -> tuple[OopQclaGate, ...]:
    return tuple(
        gate
        for gate in trace.gates
        if gate.kind is QclaGateKind.TOFFOLI
        and not (measured and gate.stage is OopQclaStage.PREFIX_UNCOMPUTE)
    )


def _segment(source_layer: int, cnot_layers: tuple[int, ...]) -> int:
    return sum(layer < source_layer for layer in cnot_layers)


def _relation(left: OopQclaGate, right: OopQclaGate) -> tuple[bool, str]:
    left_cross = left.target in right.controls
    right_cross = right.target in left.controls
    if left_cross and right_cross:
        return False, "bidirectional_target_control"
    if left_cross:
        return False, "left_target_right_control"
    if right_cross:
        return False, "right_target_left_control"
    if left.target == right.target:
        return True, "shared_target"
    if set(left.controls) & set(right.controls):
        return True, "shared_control"
    return True, "disjoint"


def _better(
    candidate: CompactDependencyNode,
    incumbent: CompactDependencyNode | None,
) -> CompactDependencyNode:
    if incumbent is None:
        return candidate
    if (candidate.macro_rank, -candidate.source_position) > (
        incumbent.macro_rank,
        -incumbent.source_position,
    ):
        return candidate
    return incumbent


def _streaming_nodes(
    trace: OopQclaTrace,
    gates: tuple[OopQclaGate, ...],
) -> tuple[CompactDependencyNode, ...]:
    cnot_layers = _cnot_layers(trace)
    target_best: dict[str, CompactDependencyNode] = {}
    control_best: dict[str, CompactDependencyNode] = {}
    result: list[CompactDependencyNode] = []
    previous_segment = -1
    prior_segment_best: CompactDependencyNode | None = None
    for position, gate in enumerate(gates):
        segment = _segment(gate.algorithmic_layer, cnot_layers)
        if segment != previous_segment:
            if result:
                prior_segment_best = max(
                    result,
                    key=lambda item: (item.macro_rank, -item.source_position),
                )
            target_best = {}
            control_best = {}
            previous_segment = segment
        candidates: dict[str, CompactDependencyNode] = {}
        if prior_segment_best is not None:
            candidates[prior_segment_best.source_gate_id] = prior_segment_best
        for control in gate.controls:
            item = target_best.get(control)
            if item is not None:
                candidates[item.source_gate_id] = item
        item = control_best.get(gate.target)
        if item is not None:
            candidates[item.source_gate_id] = item
        parent = max(
            candidates.values(),
            key=lambda item: (item.macro_rank, -item.source_position),
            default=None,
        )
        barriers: tuple[int, ...] = ()
        reasons: list[str] = []
        if parent is not None:
            barriers = tuple(
                layer
                for layer in cnot_layers
                if parent.source_algorithmic_layer
                < layer
                < gate.algorithmic_layer
            )
            commutes, _ = _relation(
                next(item for item in gates if item.gate_id == parent.source_gate_id),
                gate,
            )
            if not commutes:
                reasons.append("noncommuting_target_control")
            if barriers:
                reasons.append("source_clifford_barrier")
        node = CompactDependencyNode(
            source_gate_id=gate.gate_id,
            source_position=position,
            source_algorithmic_layer=gate.algorithmic_layer,
            source_stage=gate.stage.value,
            segment_index=segment,
            controls=(gate.controls[0], gate.controls[1]),
            target=gate.target,
            macro_rank=1 if parent is None else parent.macro_rank + 1,
            witness_predecessor=None if parent is None else parent.source_gate_id,
            witness_reasons=tuple(reasons),
            witness_barrier_layers=barriers,
        )
        result.append(node)
        target_best[gate.target] = _better(node, target_best.get(gate.target))
        for control in gate.controls:
            control_best[control] = _better(node, control_best.get(control))
    return tuple(result)


def _oracle_summary(
    trace: OopQclaTrace,
    gates: tuple[OopQclaGate, ...],
    nodes: tuple[CompactDependencyNode, ...],
) -> PairOracleSummary:
    cnot_layers = _cnot_layers(trace)
    counts: Counter[str] = Counter()
    digest = hashlib.sha256()
    expected_rank: list[int] = []
    expected_parent: list[str | None] = []
    for right_index, right in enumerate(gates):
        candidates: list[int] = []
        for left_index, left in enumerate(gates[:right_index]):
            commutes, overlap = _relation(left, right)
            barriers = tuple(
                layer
                for layer in cnot_layers
                if left.algorithmic_layer < layer < right.algorithmic_layer
            )
            dependency = not commutes or bool(barriers)
            counts["pairs"] += 1
            counts[overlap] += 1
            counts["noncommuting"] += int(not commutes)
            counts["barrier"] += int(bool(barriers))
            counts["dependency"] += int(dependency)
            counts["admitted"] += int(not dependency)
            row = (
                left.gate_id,
                right.gate_id,
                overlap,
                barriers,
                dependency,
            )
            digest.update(
                (json.dumps(row, separators=(",", ":")) + "\n").encode("utf-8")
            )
            if dependency:
                candidates.append(left_index)
        parent_index = max(
            candidates,
            key=lambda item: (expected_rank[item], -item),
            default=None,
        )
        expected_rank.append(
            1 if parent_index is None else expected_rank[parent_index] + 1
        )
        expected_parent.append(
            None if parent_index is None else gates[parent_index].gate_id
        )
    compact_match = all(
        node.macro_rank == expected_rank[index]
        and node.witness_predecessor == expected_parent[index]
        for index, node in enumerate(nodes)
    )
    if not compact_match:
        raise Width256CommutationAwareError(
            "streaming recurrence disagrees with full pair oracle"
        )
    overlap_counts = tuple(
        (name, counts[name])
        for name in (
            "disjoint",
            "shared_control",
            "shared_target",
            "left_target_right_control",
            "right_target_left_control",
            "bidirectional_target_control",
        )
    )
    return PairOracleSummary(
        operation_count=len(gates),
        pair_count=counts["pairs"],
        dependency_pair_count=counts["dependency"],
        admitted_pair_count=counts["admitted"],
        noncommuting_pair_count=counts["noncommuting"],
        barrier_pair_count=counts["barrier"],
        overlap_kind_counts=overlap_counts,
        decision_stream_sha256=digest.hexdigest().upper(),
        pair_records_materialized=False,
        compact_rank_match=True,
        evidence_status=EvidenceStatus.PROVED,
    )


def _groups(
    gates: tuple[OopQclaGate, ...], nodes: tuple[CompactDependencyNode, ...]
) -> tuple[tuple[OopQclaGate, ...], ...]:
    by_id = {gate.gate_id: gate for gate in gates}
    maximum = max((node.macro_rank for node in nodes), default=0)
    return tuple(
        tuple(
            by_id[node.source_gate_id]
            for node in nodes
            if node.macro_rank == rank
        )
        for rank in range(1, maximum + 1)
    )


def _critical_path(nodes: tuple[CompactDependencyNode, ...]) -> tuple[str, ...]:
    by_id = {node.source_gate_id: node for node in nodes}
    endpoint = max(
        nodes,
        key=lambda item: (item.macro_rank, -item.source_position),
    )
    result: list[str] = []
    cursor: CompactDependencyNode | None = endpoint
    while cursor is not None:
        result.append(cursor.source_gate_id)
        cursor = (
            None
            if cursor.witness_predecessor is None
            else by_id[cursor.witness_predecessor]
        )
    result.reverse()
    return tuple(result)


def _support_envelope(
    *,
    batch: support_model.PpmSupportBatch,
    macro_layer: int,
    phase: int,
    gates: tuple[OopQclaGate, ...],
) -> CandidateLevelEnvelope:
    targets = {gate.target for gate in gates}
    return CandidateLevelEnvelope(
        candidate_level=2 * macro_layer - (2 - phase),
        macro_layer=macro_layer,
        phase=phase,
        axis={1: "Z", 2: "X"}[phase],
        source_gate_ids=tuple(gate.gate_id for gate in gates),
        direct_ccz_event_count=len(gates),
        fresh_ccz_resource_count=len(gates),
        logical_ppm_count=batch.ppm_count,
        unique_target_h_count=len(targets),
        possible_support_union_size=len(batch.possible_support_union),
        possible_support_union_sha256=batch.possible_support_union_sha256,
        maximum_ppm_weight_upper_bound=batch.maximum_ppm_weight_upper_bound,
        total_possible_support_incidence=batch.total_possible_support_incidence,
        maximum_possible_contact_count=batch.maximum_possible_contact_count,
        maximum_possible_contact_logical_values=(
            batch.maximum_possible_contact_logical_values
        ),
        branch_dependent_profile_count=batch.branch_dependent_profile_count,
        possible_support_exact=(batch.evidence_status is EvidenceStatus.PROVED),
        possible_union_is_simultaneous_weight=False,
    )


def _support_levels(
    trace: OopQclaTrace,
    event_trace: DirectCczEventTrace,
    groups: tuple[tuple[OopQclaGate, ...], ...],
) -> tuple[CandidateLevelEnvelope, ...]:
    event_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    logical_values = tuple(
        sorted({value for gate in trace.gates for value in gate.logical_support})
    )
    arena = support_model._AnfZddArena()
    columns: support_model.SupportMatrix = {
        logical: {logical: arena.ONE} for logical in logical_values
    }
    cnot_by_layer: dict[int, list[OopQclaGate]] = defaultdict(list)
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            cnot_by_layer[gate.algorithmic_layer].append(gate)
    applied_cnot_layers: set[int] = set()
    result: list[CandidateLevelEnvelope] = []
    for macro_index, group in enumerate(groups, start=1):
        lower = min(gate.algorithmic_layer for gate in group)
        upper = max(gate.algorithmic_layer for gate in group)
        crossed = [layer for layer in cnot_by_layer if lower <= layer <= upper]
        if crossed:
            raise Width256CommutationAwareError(
                "one macro-layer crossed a source CNOT barrier"
            )
        for layer in sorted(cnot_by_layer):
            if layer >= lower or layer in applied_cnot_layers:
                continue
            for gate in cnot_by_layer[layer]:
                support_model._source_cnot_conjugate(
                    arena, columns, gate.controls[0], gate.target
                )
            applied_cnot_layers.add(layer)
        phase_profiles: dict[int, list[support_model.PpmSupportProfile]] = {
            1: [],
            2: [],
        }
        for gate in group:
            event = event_by_source[gate.gate_id]
            for index, data_value in enumerate(event.data):
                ppm = event.ppms[index]
                phase_profiles[1].append(
                    support_model._profile(
                        operation_id=ppm.event_id,
                        source_gate_id=gate.gate_id,
                        injection_event_id=event.event_id,
                        source_algorithmic_layer=gate.algorithmic_layer,
                        injection_layer=1,
                        axis="Z",
                        activities=support_model._activities_from_column(
                            arena,
                            columns[data_value],
                            extra_constant=event.resource[index],
                        ),
                    )
                )
            for index, resource_value in enumerate(event.resource):
                ppm = event.ppms[index + 3]
                phase_profiles[2].append(
                    support_model._profile(
                        operation_id=ppm.event_id,
                        source_gate_id=gate.gate_id,
                        injection_event_id=event.event_id,
                        source_algorithmic_layer=gate.algorithmic_layer,
                        injection_layer=2,
                        axis="X",
                        activities=(
                            support_model._activity_from_root(
                                arena, resource_value, arena.ONE
                            ),
                        ),
                    )
                )
        for phase in (1, 2):
            batch = support_model._batch(
                tuple(phase_profiles[phase]),
                batch_level=2 * macro_index - (2 - phase),
            )
            result.append(
                _support_envelope(
                    batch=batch,
                    macro_layer=macro_index,
                    phase=phase,
                    gates=group,
                )
            )
        for gate in group:
            event = event_by_source[gate.gate_id]
            c0, c1, target = event.data
            support_model._column_xor(
                arena,
                columns,
                target,
                c1,
                condition_variable=event.ppms[0].outcome_token,
            )
            support_model._column_xor(
                arena,
                columns,
                target,
                c0,
                condition_variable=event.ppms[1].outcome_token,
            )
    return tuple(result)


def _cleanup_certificates(
    trace: OopQclaTrace,
    retained_nodes: tuple[CompactDependencyNode, ...],
    event_trace: DirectCczEventTrace,
) -> tuple[CleanupCertificate, ...]:
    removed = tuple(
        gate
        for gate in trace.gates
        if gate.kind is QclaGateKind.TOFFOLI
        and gate.stage is OopQclaStage.PREFIX_UNCOMPUTE
    )
    positions = {gate.gate_id: index for index, gate in enumerate(trace.gates)}
    rank_by_id = {node.source_gate_id: node.macro_rank for node in retained_nodes}
    event_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    removed_ids = {gate.gate_id for gate in removed}
    result: list[CleanupCertificate] = []
    for cleanup in removed:
        index = positions[cleanup.gate_id]
        producer = next(
            gate
            for gate in trace.gates[:index]
            if gate.kind is QclaGateKind.TOFFOLI
            and gate.stage is OopQclaStage.PREFIX_PROPAGATE
            and gate.controls == cleanup.controls
            and gate.target == cleanup.target
        )
        between = tuple(
            gate
            for gate in trace.gates[positions[producer.gate_id] + 1 : index]
            if cleanup.target in gate.logical_support
        )
        if not between:
            raise Width256CommutationAwareError("cleanup target has no quantum use")
        read_only = all(cleanup.target in gate.controls for gate in between)
        later_target_uses = tuple(
            gate
            for gate in trace.gates[index + 1 :]
            if cleanup.target in gate.logical_support
        )
        final_use = not later_target_uses
        retained_uses = tuple(
            gate
            for gate in between
            if gate.kind is QclaGateKind.TOFFOLI and gate.gate_id in rank_by_id
        )
        last_use = retained_uses[-1]
        measurement_rank = max(rank_by_id[gate.gate_id] for gate in retained_uses)
        suffix = tuple(
            gate
            for gate in trace.gates[index + 1 :]
            if gate.gate_id not in removed_ids
        )
        active_support = set(cleanup.controls)
        propagating: list[str] = []
        for gate in suffix:
            if set(gate.logical_support) & active_support:
                propagating.append(gate.gate_id)
                active_support.update(gate.logical_support)
        later_ppm_ids = tuple(
            gate.gate_id for gate in suffix if gate.kind is QclaGateKind.TOFFOLI
        )
        later_target_ppm_uses = sum(
            cleanup.target in gate.logical_support
            for gate in suffix
            if gate.kind is QclaGateKind.TOFFOLI
        )
        event = event_by_source[last_use.gate_id]
        other_control = next(
            control for control in last_use.controls if control != cleanup.target
        )
        control_control_outcome = event.ppms[2].outcome_token
        axis_witness = CleanupAxisWitness(
            measured_target=cleanup.target,
            last_quantum_use_source_gate_id=last_use.gate_id,
            other_control=other_control,
            outcome_token=control_control_outcome,
            incoming_frame_term=(
                f"CZ({cleanup.target},{other_control})^{{{control_control_outcome}}}"
            ),
            presented_measurement=f"X({cleanup.target}) Z({other_control})",
        )
        token = f"width256:n{trace.width}:{cleanup.gate_id}:cleanup-x"
        result.append(
            CleanupCertificate(
                source_gate_id_replaced=cleanup.gate_id,
                producer_source_gate_id=producer.gate_id,
                last_quantum_use_source_gate_id=last_use.gate_id,
                controls=(cleanup.controls[0], cleanup.controls[1]),
                measured_target=cleanup.target,
                measurement_after_macro_layer=measurement_rank,
                candidate_level_if_axis_safe=2 * measurement_rank,
                conditional_frame_update=(
                    f"CZ({cleanup.controls[0]},{cleanup.controls[1]})^{{{token}}}"
                ),
                final_frame_support_upper_bound=tuple(sorted(active_support)),
                frame_propagating_source_gate_count=len(propagating),
                frame_propagating_source_gate_id_sha256=support_model._digest(
                    tuple(propagating)
                ),
                later_ppm_count=len(later_ppm_ids),
                later_ppm_source_gate_id_sha256=support_model._digest(later_ppm_ids),
                released_target_later_ppm_use_count=later_target_ppm_uses,
                read_only_between_producer_and_cleanup=read_only,
                final_source_use=final_use,
                release_count=1,
                axis_witness=axis_witness,
                admitted_to_z_x_only_high_rate_ppm=False,
            )
        )
    return tuple(result)


def _live_values(
    trace: OopQclaTrace,
    nodes: tuple[CompactDependencyNode, ...],
    cleanups: tuple[CleanupCertificate, ...],
    *,
    measured: bool,
) -> LiveValueEnvelope:
    rank_by_id = {node.source_gate_id: node.macro_rank for node in nodes}
    cleanup_by_target = {item.measured_target: item for item in cleanups}
    intervals: list[LiveValueInterval] = []
    for source_interval in trace.ancilla_intervals:
        uses = tuple(
            gate
            for gate in trace.gates
            if source_interval.value_id in gate.logical_support
            and gate.gate_id in rank_by_id
        )
        producer = next(
            gate
            for gate in uses
            if gate.target == source_interval.value_id
            and gate.stage is OopQclaStage.PREFIX_PROPAGATE
        )
        birth = rank_by_id[producer.gate_id]
        final_use = max(rank_by_id[gate.gate_id] for gate in uses)
        if measured:
            cleanup = cleanup_by_target[source_interval.value_id]
            release = cleanup.measurement_after_macro_layer
            release_kind = "destructive_x_measurement_not_axis_safe"
        else:
            release = final_use
            release_kind = "coherent_prefix_uncompute"
        intervals.append(
            LiveValueInterval(
                logical_value=source_interval.value_id,
                birth_macro_layer=birth,
                final_quantum_use_macro_layer=final_use,
                release_macro_layer=release,
                release_kind=release_kind,
            )
        )
    maximum_rank = max(node.macro_rank for node in nodes)
    persistent = 3 * trace.width
    live_by_layer = {
        rank: persistent
        + sum(
            interval.birth_macro_layer <= rank <= interval.release_macro_layer
            for interval in intervals
        )
        for rank in range(1, maximum_rank + 1)
    }
    peak = max(live_by_layer.values())
    return LiveValueEnvelope(
        persistent_input_output_values=persistent,
        prefix_scratch_values=len(intervals),
        fully_resident_source_values=trace.expected_fully_resident_source_values,
        peak_live_source_values=peak,
        peak_live_macro_layers=tuple(
            rank for rank, count in live_by_layer.items() if count == peak
        ),
        intervals=tuple(intervals),
    )


def _cleanup_interactions(
    cleanups: tuple[CleanupCertificate, ...]
) -> tuple[int, int]:
    pair_count = 0
    contact: Counter[str] = Counter()
    supports = [set(item.final_frame_support_upper_bound) for item in cleanups]
    for support in supports:
        contact.update(support)
    for left_index, left in enumerate(supports):
        for right in supports[left_index + 1 :]:
            pair_count += int(bool(left & right))
    return pair_count, max(contact.values(), default=0)


def _build_unitary_variant(
    trace: OopQclaTrace,
    event_trace: DirectCczEventTrace,
) -> Width256VariantResult:
    gates = _ccx_gates(trace, measured=False)
    nodes = _streaming_nodes(trace, gates)
    oracle = _oracle_summary(trace, gates, nodes)
    grouped = _groups(gates, nodes)
    path = _critical_path(nodes)
    levels = _support_levels(trace, event_trace, grouped)
    cleanups: tuple[CleanupCertificate, ...] = ()
    interactions, maximum_contact = _cleanup_interactions(cleanups)
    retained_outcomes = sum(
        6 * len(group) for group in grouped[:-1]
    )
    return Width256VariantResult(
        variant=ScalingVariant.UNITARY,
        scheduled_ccx_count=len(gates),
        removed_cleanup_ccx_count=0,
        proposed_cleanup_count=0,
        dependency_nodes=nodes,
        macro_layers=tuple(
            tuple(gate.gate_id for gate in group) for group in grouped
        ),
        macro_depth=len(grouped),
        exact_lower_bound_macro_depth=len(path),
        critical_path_source_gate_ids=path,
        direct_ccz_candidate_levels=2 * len(grouped),
        complete_logical_candidate_levels=2 * len(grouped),
        candidate_levels=levels,
        cleanup_certificates=cleanups,
        cleanup_axis_safe=True,
        selected_for_z_x_only_high_rate_analysis=True,
        fallback_variant=None,
        pair_oracle=oracle,
        live_values=_live_values(
            trace,
            nodes,
            cleanups,
            measured=False,
        ),
        retained_inter_macro_outcome_count=retained_outcomes,
        outstanding_cleanup_outcome_count=len(cleanups),
        cleanup_frame_pair_interaction_count=interactions,
        maximum_cleanup_frame_contact_count=maximum_contact,
        optimality_status=EvidenceStatus.PROVED,
    )


def _build_measured_fallback(
    trace: OopQclaTrace,
    event_trace: DirectCczEventTrace,
    unitary: Width256VariantResult,
) -> Width256VariantResult:
    """Fail closed to the unitary schedule after cleanup-axis rejection."""

    cleanups = _cleanup_certificates(trace, unitary.dependency_nodes, event_trace)
    interactions, maximum_contact = _cleanup_interactions(cleanups)
    return Width256VariantResult(
        variant=ScalingVariant.MEASURED_CLEANUP,
        scheduled_ccx_count=unitary.scheduled_ccx_count,
        removed_cleanup_ccx_count=0,
        proposed_cleanup_count=len(cleanups),
        dependency_nodes=unitary.dependency_nodes,
        macro_layers=unitary.macro_layers,
        macro_depth=unitary.macro_depth,
        exact_lower_bound_macro_depth=unitary.exact_lower_bound_macro_depth,
        critical_path_source_gate_ids=unitary.critical_path_source_gate_ids,
        direct_ccz_candidate_levels=unitary.direct_ccz_candidate_levels,
        complete_logical_candidate_levels=unitary.direct_ccz_candidate_levels,
        candidate_levels=unitary.candidate_levels,
        cleanup_certificates=cleanups,
        cleanup_axis_safe=False,
        selected_for_z_x_only_high_rate_analysis=False,
        fallback_variant=ScalingVariant.UNITARY.value,
        pair_oracle=unitary.pair_oracle,
        live_values=unitary.live_values,
        retained_inter_macro_outcome_count=(
            unitary.retained_inter_macro_outcome_count
        ),
        outstanding_cleanup_outcome_count=0,
        cleanup_frame_pair_interaction_count=interactions,
        maximum_cleanup_frame_contact_count=maximum_contact,
        optimality_status=EvidenceStatus.PROVED,
    )


def _compact_bridge() -> tuple[tuple[int, int, int], ...]:
    result = []
    for width in range(2, 9):
        trace = build_oop_qcla_trace(width)
        unitary = _streaming_nodes(trace, _ccx_gates(trace, measured=False))
        measured = _streaming_nodes(trace, _ccx_gates(trace, measured=True))
        _oracle_summary(trace, _ccx_gates(trace, measured=False), unitary)
        _oracle_summary(trace, _ccx_gates(trace, measured=True), measured)
        result.append(
            (
                width,
                max(node.macro_rank for node in unitary),
                max(node.macro_rank for node in measured),
            )
        )
    expected = (
        (2, 1, 1),
        (3, 2, 2),
        (4, 3, 3),
        (5, 4, 3),
        (6, 4, 4),
        (7, 5, 4),
        (8, 5, 5),
    )
    if tuple(result) != expected:
        raise Width256CommutationAwareError("compact recurrence broke the reviewed bridge")
    return tuple(result)


def build_width256_commutation_aware_study(
    event_trace: DirectCczEventTrace,
) -> Width256CommutationAwareStudy:
    """Build the deterministic width-256 structural comparison."""

    trace = build_oop_qcla_trace(256)
    if event_trace.source_trace_id != trace.trace_id:
        raise Width256CommutationAwareError("direct-CCZ event trace source mismatch")
    source_ccx = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    source_cnot = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.CNOT
    )
    source_ccx_layers = {gate.algorithmic_layer for gate in source_ccx}
    cnot_demands = Counter(gate.algorithmic_layer for gate in source_cnot)
    unitary = _build_unitary_variant(trace, event_trace)
    measured = _build_measured_fallback(trace, event_trace, unitary)
    return Width256CommutationAwareStudy(
        task_id="T-20260906-004",
        experiment_id="E-20260906-004",
        width=256,
        source_trace_id=trace.trace_id,
        source_trace_sha256=hashlib.sha256(
            dumps_oop_qcla_trace(trace).encode("utf-8")
        ).hexdigest().upper(),
        source_ccx_count=len(source_ccx),
        source_cnot_count=len(source_cnot),
        source_toffoli_bearing_layers=len(source_ccx_layers),
        source_aligned_candidate_levels=2 * len(source_ccx_layers),
        source_cnot_layer_demands=tuple(sorted(cnot_demands.items())),
        compact_bridge_widths_2_to_8=_compact_bridge(),
        unitary=unitary,
        measured_cleanup=measured,
        selected_variant=ScalingVariant.UNITARY.value,
        validation_status="pending_independent_replay",
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


def width256_commutation_aware_study_to_data(
    study: Width256CommutationAwareStudy,
) -> dict[str, Any]:
    """Return a deterministic JSON-compatible record."""

    result = _jsonable(asdict(study))
    if not isinstance(result, dict):  # pragma: no cover - asdict invariant
        raise Width256CommutationAwareError("study serialization is not a mapping")
    return result


def dumps_width256_commutation_aware_study(
    study: Width256CommutationAwareStudy,
) -> str:
    """Serialize the study deterministically."""

    return json.dumps(
        width256_commutation_aware_study_to_data(study),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
