"""Commutation-aware structural certificate for width-256 in-place QCLA.

The source implements addition modulo ``2**n``.  Macro layers and the two
direct-CCZ phases are architecture-independent logical coordinates, not QEC
cycles, physical simultaneity, or elapsed time.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from ecdlp_ftqc.circuits import (
    QclaGate,
    QclaGateKind,
    QclaTrace,
    build_qcla_trace,
    dumps_qcla_trace,
    qcla_metrics,
)
from ecdlp_ftqc.compiler import DirectCczEventTrace
from ecdlp_ftqc.metadata import EvidenceStatus

from . import direct_ccz_ppm_support_certificate as support_model

WIDTH256_IP_COMMUTATION_AWARE_SCHEMA = (
    "ecdlp-ftqc/width256-commutation-aware-inplace-mod2n-qcla"
)
WIDTH256_IP_COMMUTATION_AWARE_SCHEMA_VERSION = 1
IP_CANDIDATE_COORDINATE = (
    "architecture_independent_two_phase_direct_ccz_candidate_levels_not_time"
)
IP_SUPPORT_SAMPLE_COUNT = 512
IP_SUPPORT_SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"


class Width256IpCommutationAwareError(ValueError):
    """Raised when the IP structural certificate violates its contract."""


@dataclass(frozen=True, slots=True)
class IpCompactDependencyNode:
    """One linear-size longest-path record in source CCX order."""

    source_gate_id: str
    source_position: int
    source_algorithmic_layer: int
    source_step: int
    source_stage: str
    source_direction: str
    segment_index: int
    controls: tuple[str, str]
    target: str
    macro_rank: int
    witness_predecessor: str | None
    witness_reasons: tuple[str, ...]
    witness_barrier_layers: tuple[int, ...]
    witness_barrier_kinds: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.source_gate_id
            or self.source_position < 0
            or self.source_algorithmic_layer < 1
            or not 1 <= self.source_step <= 10
            or self.segment_index < 0
            or len(set(self.controls)) != 2
            or self.target in self.controls
            or self.macro_rank < 1
        ):
            raise Width256IpCommutationAwareError("invalid dependency node")
        if (self.witness_predecessor is None) != (not self.witness_reasons):
            raise Width256IpCommutationAwareError(
                "dependency witness endpoint and reasons disagree"
            )
        if bool(self.witness_barrier_layers) != bool(self.witness_barrier_kinds):
            raise Width256IpCommutationAwareError(
                "barrier layers and kinds must be present together"
            )


@dataclass(frozen=True, slots=True)
class IpPairOracleSummary:
    """Complete CCX-pair audit summarized without serializing every pair."""

    operation_count: int
    pair_count: int
    dependency_pair_count: int
    admitted_pair_count: int
    noncommuting_pair_count: int
    barrier_pair_count: int
    cnot_barrier_pair_count: int
    x_barrier_pair_count: int
    both_kind_barrier_pair_count: int
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
            or self.noncommuting_pair_count > self.dependency_pair_count
            or self.barrier_pair_count > self.dependency_pair_count
            or len(self.decision_stream_sha256) != 64
            or self.pair_records_materialized
            or not self.compact_rank_match
            or self.evidence_status is not EvidenceStatus.PROVED
        ):
            raise Width256IpCommutationAwareError("invalid pair-oracle summary")


@dataclass(frozen=True, slots=True)
class IpCandidateLevelEnvelope:
    """Logical PPM demand with sampled lower and sound may-support upper bounds."""

    candidate_level: int
    macro_layer: int
    phase: int
    axis: str
    source_gate_ids: tuple[str, ...]
    source_algorithmic_layer_min: int
    source_algorithmic_layer_max: int
    direct_ccz_event_count: int
    fresh_ccz_resource_count: int
    logical_ppm_count: int
    distinct_target_h_count: int
    may_support_union_upper_bound_size: int
    may_support_union_sha256: str
    witnessed_support_union_lower_bound_size: int
    maximum_ppm_weight_upper_bound: int
    maximum_sampled_branch_weight: int
    total_may_support_incidence: int
    total_witnessed_support_incidence: int
    maximum_may_contact_count: int
    maximum_witnessed_contact_count: int
    branch_dependent_profile_count: int
    unwitnessed_may_incidence_count: int
    possible_support_exact: bool
    may_union_is_simultaneous_branch_weight: bool
    deterministic_branch_sample_count: int
    deterministic_branch_sample_seed: str
    coordinate: str = support_model.SUPPORT_COORDINATE
    evidence_status: EvidenceStatus = EvidenceStatus.CHECK

    def __post_init__(self) -> None:
        expected_level = 2 * self.macro_layer - (2 - self.phase)
        if (
            self.phase not in {1, 2}
            or self.axis != {1: "Z", 2: "X"}[self.phase]
            or self.candidate_level != expected_level
            or self.direct_ccz_event_count != len(self.source_gate_ids)
            or self.fresh_ccz_resource_count != self.direct_ccz_event_count
            or self.logical_ppm_count != 3 * self.direct_ccz_event_count
            or self.source_algorithmic_layer_min > self.source_algorithmic_layer_max
            or self.may_support_union_upper_bound_size
            < self.witnessed_support_union_lower_bound_size
            or self.maximum_ppm_weight_upper_bound
            < self.maximum_sampled_branch_weight
            or self.maximum_may_contact_count
            < self.maximum_witnessed_contact_count
            or self.unwitnessed_may_incidence_count
            != self.total_may_support_incidence
            - self.total_witnessed_support_incidence
            or self.may_union_is_simultaneous_branch_weight
            or self.deterministic_branch_sample_count != IP_SUPPORT_SAMPLE_COUNT
            or self.deterministic_branch_sample_seed != IP_SUPPORT_SAMPLE_SEED
            or len(self.may_support_union_sha256) != 64
        ):
            raise Width256IpCommutationAwareError("invalid candidate-level envelope")
        expected_status = (
            EvidenceStatus.PROVED if self.possible_support_exact else EvidenceStatus.CHECK
        )
        if self.evidence_status is not expected_status:
            raise Width256IpCommutationAwareError("support evidence label is inconsistent")


@dataclass(frozen=True, slots=True)
class IpLiveAncillaEnvelope:
    """Reviewed source-lifecycle demand, kept distinct from macro scheduling."""

    persistent_input_values: int
    source_ancilla_values: int
    prefix_scratch_values: int
    allocation_interval_count: int
    peak_live_source_ancillas: int
    peak_live_source_layers: tuple[int, ...]
    fully_resident_source_values: int
    coordinate: str = "source_algorithmic_layer_liveness_not_macro_schedule"

    def __post_init__(self) -> None:
        if (
            self.persistent_input_values + self.source_ancilla_values
            != self.fully_resident_source_values
            or self.peak_live_source_ancillas > self.source_ancilla_values
            or self.allocation_interval_count < self.source_ancilla_values
            or not self.peak_live_source_layers
        ):
            raise Width256IpCommutationAwareError("invalid source-liveness envelope")


@dataclass(frozen=True, slots=True)
class Width256IpCommutationAwareStudy:
    """Canonical width-256 IP structural result."""

    task_id: str
    experiment_id: str
    width: int
    arithmetic_contract: str
    source_trace_id: str
    source_trace_sha256: str
    source_gate_count: int
    source_ccx_count: int
    source_cnot_count: int
    source_x_count: int
    source_layer_count: int
    source_toffoli_bearing_layers: int
    source_aligned_candidate_levels: int
    coherent_cleanup_ccx_count: int
    source_clifford_layer_demands: tuple[tuple[int, str, int], ...]
    compact_bridge_widths_2_to_8: tuple[tuple[int, int, int], ...]
    dependency_nodes: tuple[IpCompactDependencyNode, ...]
    macro_layers: tuple[tuple[str, ...], ...]
    macro_depth: int
    exact_lower_bound_macro_depth: int
    critical_path_source_gate_ids: tuple[str, ...]
    direct_ccz_candidate_levels: int
    candidate_levels: tuple[IpCandidateLevelEnvelope, ...]
    pair_oracle: IpPairOracleSummary
    live_ancillas: IpLiveAncillaEnvelope
    retained_inter_macro_outcome_count: int
    total_target_h_count: int
    peak_distinct_target_h_count: int
    peak_fresh_ccz_resource_count: int
    cleanup_policy: str
    support_envelope_status: EvidenceStatus
    optimality_status: EvidenceStatus
    candidate_coordinate: str = IP_CANDIDATE_COORDINATE
    complete_native_schedule: bool = False
    native_cycles: int | None = None
    runtime_seconds: float | None = None
    physical_qubits: int | None = None
    failure_probability: float | None = None
    validation_status: str = "pending_independent_replay"
    schema: str = WIDTH256_IP_COMMUTATION_AWARE_SCHEMA
    schema_version: int = WIDTH256_IP_COMMUTATION_AWARE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            self.task_id != "T-20260907-001"
            or self.experiment_id != "E-20260907-001"
            or self.width != 256
            or self.arithmetic_contract != "(A,B)->(A,A+B mod 2^n)"
            or self.source_gate_count != 3987
            or self.source_ccx_count != 2458
            or self.source_cnot_count != 1019
            or self.source_x_count != 510
            or self.source_toffoli_bearing_layers != 34
            or self.source_aligned_candidate_levels != 68
            or self.coherent_cleanup_ccx_count != 1229
            or len(self.dependency_nodes) != self.source_ccx_count
            or self.macro_depth != len(self.macro_layers)
            or self.macro_depth != self.exact_lower_bound_macro_depth
            or self.macro_depth != len(self.critical_path_source_gate_ids)
            or self.direct_ccz_candidate_levels != 2 * self.macro_depth
            or len(self.candidate_levels) != self.direct_ccz_candidate_levels
            or self.total_target_h_count != 2 * self.source_ccx_count
            or self.cleanup_policy != "coherent_reverse_network_retained"
            or self.optimality_status is not EvidenceStatus.PROVED
            or self.candidate_coordinate != IP_CANDIDATE_COORDINATE
            or self.schema != WIDTH256_IP_COMMUTATION_AWARE_SCHEMA
            or self.schema_version != WIDTH256_IP_COMMUTATION_AWARE_SCHEMA_VERSION
        ):
            raise Width256IpCommutationAwareError("width-256 IP headline changed")
        finite = (
            self.native_cycles,
            self.runtime_seconds,
            self.physical_qubits,
            self.failure_probability,
        )
        if self.complete_native_schedule or any(value is not None for value in finite):
            raise Width256IpCommutationAwareError("finite outputs must remain null")


def _barrier_layers(trace: QclaTrace) -> tuple[tuple[int, tuple[str, ...]], ...]:
    grouped: dict[int, set[str]] = defaultdict(set)
    for gate in trace.gates:
        if gate.kind is not QclaGateKind.TOFFOLI:
            grouped[gate.algorithmic_layer].add(gate.kind.value)
    return tuple((layer, tuple(sorted(grouped[layer]))) for layer in sorted(grouped))


def _segment(source_layer: int, barriers: tuple[tuple[int, tuple[str, ...]], ...]) -> int:
    return sum(layer < source_layer for layer, _ in barriers)


def _relation(left: QclaGate, right: QclaGate) -> tuple[bool, str]:
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
    candidate: IpCompactDependencyNode,
    incumbent: IpCompactDependencyNode | None,
) -> IpCompactDependencyNode:
    if incumbent is None:
        return candidate
    if (candidate.macro_rank, -candidate.source_position) > (
        incumbent.macro_rank,
        -incumbent.source_position,
    ):
        return candidate
    return incumbent


def _streaming_nodes(
    trace: QclaTrace, gates: tuple[QclaGate, ...]
) -> tuple[IpCompactDependencyNode, ...]:
    barriers = _barrier_layers(trace)
    gate_by_id = {gate.gate_id: gate for gate in gates}
    target_best: dict[str, IpCompactDependencyNode] = {}
    control_best: dict[str, IpCompactDependencyNode] = {}
    result: list[IpCompactDependencyNode] = []
    previous_segment = -1
    prior_segment_best: IpCompactDependencyNode | None = None
    for position, gate in enumerate(gates):
        segment = _segment(gate.algorithmic_layer, barriers)
        if segment != previous_segment:
            if result:
                prior_segment_best = max(
                    result,
                    key=lambda item: (item.macro_rank, -item.source_position),
                )
            target_best = {}
            control_best = {}
            previous_segment = segment
        candidates: dict[str, IpCompactDependencyNode] = {}
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
        barrier_rows = (
            ()
            if parent is None
            else tuple(
                (layer, kinds)
                for layer, kinds in barriers
                if parent.source_algorithmic_layer < layer < gate.algorithmic_layer
            )
        )
        reasons: list[str] = []
        if parent is not None:
            commutes, _ = _relation(gate_by_id[parent.source_gate_id], gate)
            if not commutes:
                reasons.append("noncommuting_target_control")
            if barrier_rows:
                reasons.append("source_clifford_barrier")
        node = IpCompactDependencyNode(
            source_gate_id=gate.gate_id,
            source_position=position,
            source_algorithmic_layer=gate.algorithmic_layer,
            source_step=gate.source_step,
            source_stage=gate.stage.value,
            source_direction=gate.direction.value,
            segment_index=segment,
            controls=(gate.controls[0], gate.controls[1]),
            target=gate.target,
            macro_rank=1 if parent is None else parent.macro_rank + 1,
            witness_predecessor=None if parent is None else parent.source_gate_id,
            witness_reasons=tuple(reasons),
            witness_barrier_layers=tuple(layer for layer, _ in barrier_rows),
            witness_barrier_kinds=tuple(
                sorted({kind for _, kinds in barrier_rows for kind in kinds})
            ),
        )
        result.append(node)
        target_best[gate.target] = _better(node, target_best.get(gate.target))
        for control in gate.controls:
            control_best[control] = _better(node, control_best.get(control))
    return tuple(result)


def _pair_oracle(
    trace: QclaTrace,
    gates: tuple[QclaGate, ...],
    nodes: tuple[IpCompactDependencyNode, ...],
) -> IpPairOracleSummary:
    barriers = _barrier_layers(trace)
    counts: Counter[str] = Counter()
    digest = hashlib.sha256()
    expected_rank: list[int] = []
    expected_parent: list[str | None] = []
    for right_index, right in enumerate(gates):
        candidates: list[int] = []
        for left_index, left in enumerate(gates[:right_index]):
            commutes, overlap = _relation(left, right)
            crossed = tuple(
                (layer, kinds)
                for layer, kinds in barriers
                if left.algorithmic_layer < layer < right.algorithmic_layer
            )
            kinds = {kind for _, row_kinds in crossed for kind in row_kinds}
            dependency = not commutes or bool(crossed)
            counts["pairs"] += 1
            counts[overlap] += 1
            counts["noncommuting"] += int(not commutes)
            counts["barrier"] += int(bool(crossed))
            counts["cnot_barrier"] += int("cnot" in kinds)
            counts["x_barrier"] += int("x" in kinds)
            counts["both_barrier"] += int({"cnot", "x"} <= kinds)
            counts["dependency"] += int(dependency)
            counts["admitted"] += int(not dependency)
            digest.update(
                (
                    f"{left.gate_id}|{right.gate_id}|{overlap}|"
                    f"{','.join(str(layer) for layer, _ in crossed)}|"
                    f"{','.join(sorted(kinds))}|{int(dependency)}\n"
                ).encode()
            )
            if dependency:
                candidates.append(left_index)
        if candidates:
            parent = max(
                candidates,
                key=lambda index: (expected_rank[index], -index),
            )
            expected_rank.append(expected_rank[parent] + 1)
            expected_parent.append(gates[parent].gate_id)
        else:
            expected_rank.append(1)
            expected_parent.append(None)
    rank_match = all(
        node.macro_rank == expected_rank[index]
        and node.witness_predecessor == expected_parent[index]
        for index, node in enumerate(nodes)
    )
    if not rank_match:
        raise Width256IpCommutationAwareError(
            "streaming recurrence disagrees with complete pair oracle"
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
    return IpPairOracleSummary(
        operation_count=len(gates),
        pair_count=counts["pairs"],
        dependency_pair_count=counts["dependency"],
        admitted_pair_count=counts["admitted"],
        noncommuting_pair_count=counts["noncommuting"],
        barrier_pair_count=counts["barrier"],
        cnot_barrier_pair_count=counts["cnot_barrier"],
        x_barrier_pair_count=counts["x_barrier"],
        both_kind_barrier_pair_count=counts["both_barrier"],
        overlap_kind_counts=overlap_counts,
        decision_stream_sha256=digest.hexdigest().upper(),
        pair_records_materialized=False,
        compact_rank_match=True,
        evidence_status=EvidenceStatus.PROVED,
    )


def _groups(
    gates: tuple[QclaGate, ...], nodes: tuple[IpCompactDependencyNode, ...]
) -> tuple[tuple[QclaGate, ...], ...]:
    by_id = {gate.gate_id: gate for gate in gates}
    maximum = max((node.macro_rank for node in nodes), default=0)
    groups = tuple(
        tuple(
            by_id[node.source_gate_id]
            for node in nodes
            if node.macro_rank == rank
        )
        for rank in range(1, maximum + 1)
    )
    if any(not group for group in groups):
        raise Width256IpCommutationAwareError("macro schedule contains an empty layer")
    return groups


def _critical_path(nodes: tuple[IpCompactDependencyNode, ...]) -> tuple[str, ...]:
    by_id = {node.source_gate_id: node for node in nodes}
    endpoint = max(nodes, key=lambda item: (item.macro_rank, -item.source_position))
    path: list[str] = []
    cursor: IpCompactDependencyNode | None = endpoint
    while cursor is not None:
        path.append(cursor.source_gate_id)
        cursor = (
            None
            if cursor.witness_predecessor is None
            else by_id[cursor.witness_predecessor]
        )
    path.reverse()
    return tuple(path)


def _support_levels(
    trace: QclaTrace,
    event_trace: DirectCczEventTrace,
    groups: tuple[tuple[QclaGate, ...], ...],
) -> tuple[IpCandidateLevelEnvelope, ...]:
    event_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    logical_values = tuple(
        sorted({value for gate in trace.gates for value in gate.logical_support})
    )
    sample_count = IP_SUPPORT_SAMPLE_COUNT
    all_mask = (1 << sample_count) - 1
    sampled = {logical: {logical: all_mask} for logical in logical_values}
    may = {logical: {logical} for logical in logical_values}
    cnot_by_layer: dict[int, list[QclaGate]] = defaultdict(list)
    barrier_layers = {layer for layer, _ in _barrier_layers(trace)}
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            cnot_by_layer[gate.algorithmic_layer].append(gate)
    applied_cnot_layers: set[int] = set()
    result: list[IpCandidateLevelEnvelope] = []
    previous_lower = 0
    for macro_index, group in enumerate(groups, start=1):
        lower = min(gate.algorithmic_layer for gate in group)
        upper = max(gate.algorithmic_layer for gate in group)
        if lower < previous_lower:
            raise Width256IpCommutationAwareError(
                "macro schedule reverses a source barrier segment"
            )
        previous_lower = lower
        if any(lower <= layer <= upper for layer in barrier_layers):
            raise Width256IpCommutationAwareError(
                "one macro layer crossed an X/CNOT source barrier"
            )
        for layer in sorted(cnot_by_layer):
            if layer >= lower or layer in applied_cnot_layers:
                continue
            for gate in cnot_by_layer[layer]:
                support_model._sampled_source_cnot_conjugate(
                    sampled, may, gate.controls[0], gate.target
                )
            applied_cnot_layers.add(layer)
        profiles_by_phase: dict[int, list[support_model.PpmSupportProfile]] = {
            1: [],
            2: [],
        }
        sampled_weight_by_phase = {1: 1, 2: 1}
        for gate in group:
            event = event_by_source[gate.gate_id]
            for index, data_value in enumerate(event.data):
                ppm = event.ppms[index]
                possible = tuple(sorted({event.resource[index], *may[data_value]}))
                masks = dict(sampled[data_value])
                masks[event.resource[index]] = all_mask
                sampled_weight_by_phase[1] = max(
                    sampled_weight_by_phase[1],
                    support_model._maximum_parallel_mask_weight(
                        tuple(masks.get(value, 0) for value in possible),
                        count=sample_count,
                    ),
                )
                possible_exact = all(masks.get(value, 0) != 0 for value in possible)
                profiles_by_phase[1].append(
                    support_model._profile(
                        operation_id=ppm.event_id,
                        source_gate_id=gate.gate_id,
                        injection_event_id=event.event_id,
                        source_algorithmic_layer=gate.algorithmic_layer,
                        injection_layer=1,
                        axis="Z",
                        activities=tuple(
                            support_model._constant_activity(value)
                            if value == event.resource[index]
                            else support_model._sampled_activity(
                                value,
                                masks.get(value, 0),
                                all_mask=all_mask,
                                possible_witnessed=masks.get(value, 0) != 0,
                                count=sample_count,
                            )
                            for value in possible
                        ),
                        possible_support_exact=possible_exact,
                    )
                )
            for index, resource_value in enumerate(event.resource):
                ppm = event.ppms[index + 3]
                profiles_by_phase[2].append(
                    support_model._profile(
                        operation_id=ppm.event_id,
                        source_gate_id=gate.gate_id,
                        injection_event_id=event.event_id,
                        source_algorithmic_layer=gate.algorithmic_layer,
                        injection_layer=2,
                        axis="X",
                        activities=(support_model._constant_activity(resource_value),),
                    )
                )
        for phase in (1, 2):
            batch = support_model._batch(
                tuple(profiles_by_phase[phase]),
                batch_level=2 * macro_index - (2 - phase),
            )
            exact = batch.evidence_status is EvidenceStatus.PROVED
            result.append(
                IpCandidateLevelEnvelope(
                    candidate_level=2 * macro_index - (2 - phase),
                    macro_layer=macro_index,
                    phase=phase,
                    axis={1: "Z", 2: "X"}[phase],
                    source_gate_ids=tuple(gate.gate_id for gate in group),
                    source_algorithmic_layer_min=lower,
                    source_algorithmic_layer_max=upper,
                    direct_ccz_event_count=len(group),
                    fresh_ccz_resource_count=len(group),
                    logical_ppm_count=batch.ppm_count,
                    distinct_target_h_count=len({gate.target for gate in group}),
                    may_support_union_upper_bound_size=len(
                        batch.possible_support_union
                    ),
                    may_support_union_sha256=batch.possible_support_union_sha256,
                    witnessed_support_union_lower_bound_size=len(
                        batch.witnessed_support_union
                    ),
                    maximum_ppm_weight_upper_bound=(
                        batch.maximum_ppm_weight_upper_bound
                    ),
                    maximum_sampled_branch_weight=sampled_weight_by_phase[phase],
                    total_may_support_incidence=(
                        batch.total_possible_support_incidence
                    ),
                    total_witnessed_support_incidence=(
                        batch.total_witnessed_support_incidence
                    ),
                    maximum_may_contact_count=(
                        batch.maximum_possible_contact_count
                    ),
                    maximum_witnessed_contact_count=(
                        batch.maximum_witnessed_contact_count
                    ),
                    branch_dependent_profile_count=(
                        batch.branch_dependent_profile_count
                    ),
                    unwitnessed_may_incidence_count=(
                        batch.total_possible_support_incidence
                        - batch.total_witnessed_support_incidence
                    ),
                    possible_support_exact=exact,
                    may_union_is_simultaneous_branch_weight=False,
                    deterministic_branch_sample_count=sample_count,
                    deterministic_branch_sample_seed=IP_SUPPORT_SAMPLE_SEED,
                    evidence_status=(
                        EvidenceStatus.PROVED if exact else EvidenceStatus.CHECK
                    ),
                )
            )
        for gate in group:
            event = event_by_source[gate.gate_id]
            c0, c1, target = event.data
            support_model._sampled_conditional_column_xor(
                sampled,
                may,
                target,
                c1,
                support_model._sample_mask(
                    event.ppms[0].outcome_token,
                    count=sample_count,
                    seed=IP_SUPPORT_SAMPLE_SEED,
                ),
            )
            support_model._sampled_conditional_column_xor(
                sampled,
                may,
                target,
                c0,
                support_model._sample_mask(
                    event.ppms[1].outcome_token,
                    count=sample_count,
                    seed=IP_SUPPORT_SAMPLE_SEED,
                ),
            )
    return tuple(result)


def _live_ancillas(trace: QclaTrace) -> IpLiveAncillaEnvelope:
    metrics = qcla_metrics(trace)
    peak_layers = tuple(
        layer
        for layer in range(1, metrics.source_layer_count + 1)
        if sum(
            interval.start_layer <= layer <= interval.end_layer
            for interval in trace.ancilla_intervals
        )
        == metrics.peak_live_ancillas
    )
    return IpLiveAncillaEnvelope(
        persistent_input_values=2 * trace.width,
        source_ancilla_values=metrics.source_ancilla_count,
        prefix_scratch_values=metrics.prefix_scratch_count,
        allocation_interval_count=len(trace.ancilla_intervals),
        peak_live_source_ancillas=metrics.peak_live_ancillas,
        peak_live_source_layers=peak_layers,
        fully_resident_source_values=2 * trace.width + metrics.source_ancilla_count,
    )


def _compact_bridge() -> tuple[tuple[int, int, int], ...]:
    rows: list[tuple[int, int, int]] = []
    for width in range(2, 9):
        trace = build_qcla_trace(width)
        gates = tuple(
            gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
        )
        nodes = _streaming_nodes(trace, gates)
        _pair_oracle(trace, gates, nodes)
        source_depth = len({gate.algorithmic_layer for gate in gates})
        macro_depth = max(node.macro_rank for node in nodes)
        rows.append((width, source_depth, macro_depth))
    return tuple(rows)


def build_width256_ip_commutation_aware_study(
    event_trace: DirectCczEventTrace,
) -> Width256IpCommutationAwareStudy:
    """Build the deterministic width-256 IP logical structural study."""

    trace = build_qcla_trace(256)
    if event_trace.source_trace_id != trace.trace_id:
        raise Width256IpCommutationAwareError("direct-CCZ event source mismatch")
    ccx = tuple(gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI)
    nodes = _streaming_nodes(trace, ccx)
    oracle = _pair_oracle(trace, ccx, nodes)
    groups = _groups(ccx, nodes)
    path = _critical_path(nodes)
    levels = _support_levels(trace, event_trace, groups)
    clifford_demands = Counter(
        (gate.algorithmic_layer, gate.kind.value)
        for gate in trace.gates
        if gate.kind is not QclaGateKind.TOFFOLI
    )
    metrics = qcla_metrics(trace)
    return Width256IpCommutationAwareStudy(
        task_id="T-20260907-001",
        experiment_id="E-20260907-001",
        width=trace.width,
        arithmetic_contract=trace.arithmetic_contract,
        source_trace_id=trace.trace_id,
        source_trace_sha256=hashlib.sha256(
            dumps_qcla_trace(trace).encode("utf-8")
        ).hexdigest().upper(),
        source_gate_count=metrics.gate_count,
        source_ccx_count=metrics.toffoli_count,
        source_cnot_count=metrics.cnot_count,
        source_x_count=metrics.x_count,
        source_layer_count=metrics.source_layer_count,
        source_toffoli_bearing_layers=len(
            {gate.algorithmic_layer for gate in ccx}
        ),
        source_aligned_candidate_levels=2
        * len({gate.algorithmic_layer for gate in ccx}),
        coherent_cleanup_ccx_count=sum(
            gate.source_step >= 7 for gate in ccx
        ),
        source_clifford_layer_demands=tuple(
            (layer, kind, count)
            for (layer, kind), count in sorted(clifford_demands.items())
        ),
        compact_bridge_widths_2_to_8=_compact_bridge(),
        dependency_nodes=nodes,
        macro_layers=tuple(tuple(gate.gate_id for gate in group) for group in groups),
        macro_depth=len(groups),
        exact_lower_bound_macro_depth=len(path),
        critical_path_source_gate_ids=path,
        direct_ccz_candidate_levels=2 * len(groups),
        candidate_levels=levels,
        pair_oracle=oracle,
        live_ancillas=_live_ancillas(trace),
        retained_inter_macro_outcome_count=sum(6 * len(group) for group in groups[:-1]),
        total_target_h_count=2 * len(ccx),
        peak_distinct_target_h_count=max(
            len({gate.target for gate in group}) for group in groups
        ),
        peak_fresh_ccz_resource_count=max(len(group) for group in groups),
        cleanup_policy="coherent_reverse_network_retained",
        support_envelope_status=(
            EvidenceStatus.PROVED
            if all(level.possible_support_exact for level in levels)
            else EvidenceStatus.CHECK
        ),
        optimality_status=EvidenceStatus.PROVED,
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


def width256_ip_commutation_aware_study_to_data(
    study: Width256IpCommutationAwareStudy,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible study data."""

    data = _jsonable(asdict(study))
    if not isinstance(data, dict):  # pragma: no cover - asdict invariant
        raise Width256IpCommutationAwareError("study serialization failed")
    return data


def dumps_width256_ip_commutation_aware_study(
    study: Width256IpCommutationAwareStudy,
) -> str:
    """Serialize the study deterministically."""

    return json.dumps(
        width256_ip_commutation_aware_study_to_data(study),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
