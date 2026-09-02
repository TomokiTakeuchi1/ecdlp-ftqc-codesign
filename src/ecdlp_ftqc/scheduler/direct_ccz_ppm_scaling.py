"""Scalable structural analysis for direct-CCZ QCLA workloads.

The all-pairs symbolic batching analysis is intentionally retained only for
explicit exact anchors.  Larger widths use source-DAG and admitted injection
semantics without materializing a quadratic PPM relation table.  None of the
reported level coordinates is a surgery round or a time coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ecdlp_ftqc.architectures import DirectCczBackendAudit, DirectCczCapability
from ecdlp_ftqc.circuits import (
    OopQclaTrace,
    QclaGateKind,
    QclaTrace,
    oop_qcla_metrics,
    qcla_metrics,
)
from ecdlp_ftqc.compiler import (
    lower_oop_qcla_to_direct_ccz_events,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    lower_qcla_to_direct_ccz_events,
    lower_qcla_to_symbolic_direct_ccz_ppm,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler.direct_ccz_ppm_batching import (
    FINITE_NATIVE_MAPPER_OBLIGATIONS,
    DirectCczPpmBatchAnalysis,
    analyze_direct_ccz_ppm_batches,
)

DIRECT_CCZ_PPM_SCALING_SCHEMA = "ecdlp-ftqc/direct-ccz-qcla-scaling"
DIRECT_CCZ_PPM_SCALING_SCHEMA_VERSION = 1
DIRECT_CCZ_PPM_EXACT_ANCHOR_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-exact-anchor"
)
DIRECT_CCZ_PPM_FINITE_SCALING_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-finite-scaling-admission"
)

QclaVariant = Literal["oop", "ip"]


class DirectCczPpmScalingError(ValueError):
    """Raised when a scaling record would overstate or corrupt its evidence."""


@dataclass(frozen=True, slots=True)
class SourceLayerInjectionDemand:
    """Aggregate direct-injection demand attached to one source layer."""

    source_algorithmic_layer: int
    source_steps: tuple[int, ...]
    source_stages: tuple[str, ...]
    toffoli_count: int
    ccz_state_count: int
    zz_ppm_count: int
    resource_x_ppm_count: int
    total_ppm_count: int


@dataclass(frozen=True, slots=True)
class QclaDirectCczStructuralPoint:
    """One exact source/event count point with no all-pairs table."""

    variant: QclaVariant
    width: int
    source_trace_id: str
    event_trace_id: str
    source_gate_count: int
    source_x_count: int
    source_cnot_count: int
    source_toffoli_count: int
    source_dependency_count: int
    source_layer_count: int
    nonclifford_source_layer_count: int
    weighted_causal_ppm_level_lower_bound: int
    source_two_phase_injection_envelope_levels: int
    direct_ccz_event_count: int
    consumed_ccz_state_count: int
    resource_logical_demand: int
    ppm_count: int
    conditional_frame_update_count: int
    theoretical_pair_count: int
    pair_table_materialized: bool
    singleton_semantic_order_count: int
    cleanup_operation_count: int
    cleanup_toffoli_count: int
    source_storage_count_kind: str
    source_storage_count: int
    peak_source_toffoli_per_layer: int
    peak_source_layer_ppm_demand: int
    layer_demand: tuple[SourceLayerInjectionDemand, ...]
    structural_evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL
    causal_lower_bound_evidence_status: EvidenceStatus = EvidenceStatus.PROVED
    source_two_phase_envelope_status: EvidenceStatus = EvidenceStatus.CHECK
    candidate_compatibility_status: EvidenceStatus = EvidenceStatus.OPEN


@dataclass(frozen=True, slots=True)
class QclaDirectCczExactAnchor:
    """Summary of an explicitly materialized exact symbolic batching run."""

    variant: QclaVariant
    width: int
    trace_id: str
    ppm_count: int
    materialized_pair_count: int
    candidate_batch_level_count: int
    causal_critical_path_lower_bound: int
    conflict_clique_lower_bound: int
    combined_batch_level_lower_bound: int
    fallback_operation_count: int
    possible_y_ppm_count: int
    nonexact_weight_profile_count: int
    peak_live_logical_requirement: int
    peak_resource_state_count: int
    candidate_optimality_evidence_status: EvidenceStatus
    finite_native_schedule_emitted: bool


@dataclass(frozen=True, slots=True)
class QclaDirectCczFiniteScalingAdmission:
    """Fail-closed finite-resource gate shared by the scaling points."""

    capability_id: str
    backend_audit_id: str
    backend_candidate_id: str
    event_lowering_admitted: bool
    high_rate_capability_admitted: bool
    finite_backend_admitted: bool
    scaling_native_mapper_admitted: bool
    capability_missing_fields: tuple[str, ...]
    backend_missing_fields: tuple[str, ...]
    backend_incompatible_fields: tuple[str, ...]
    native_mapper_missing_fields: tuple[str, ...]
    verdict: str
    evidence_status: EvidenceStatus
    native_schedule: None = None
    surgery_rounds: None = None
    memory_traffic: None = None
    routing_cost: None = None
    reaction_latency_seconds: None = None
    decoder_service: None = None
    ccz_buffer_trajectory: None = None
    runtime_seconds: None = None
    physical_qubits: None = None
    failure_probability: None = None


def _weighted_causal_ppm_level_lower_bound(
    trace: QclaTrace | OopQclaTrace,
) -> int:
    """Longest source-DAG path with weight two on every Toffoli.

    Each admitted direct-CCZ event has a causally ordered ZZ layer followed by
    a resource-X layer.  Clifford source gates have zero weight in this PPM
    coordinate.  Therefore this is a lower bound, not a realizable batch count.
    """

    predecessors: dict[str, list[str]] = {}
    for dependency in trace.dependencies:
        predecessors.setdefault(dependency.successor, []).append(
            dependency.predecessor
        )
    gates = {gate.gate_id: gate for gate in trace.gates}
    longest: dict[str, int] = {}
    for gate_id in trace.topological_order():
        gate = gates[gate_id]
        weight = 2 if gate.kind is QclaGateKind.TOFFOLI else 0
        longest[gate_id] = weight + max(
            (longest[item] for item in predecessors.get(gate_id, ())),
            default=0,
        )
    return max(longest.values(), default=0)


def _layer_demand(
    trace: QclaTrace | OopQclaTrace,
) -> tuple[SourceLayerInjectionDemand, ...]:
    by_layer: dict[int, list[Any]] = {}
    for gate in trace.gates:
        if gate.kind is QclaGateKind.TOFFOLI:
            by_layer.setdefault(gate.algorithmic_layer, []).append(gate)
    return tuple(
        SourceLayerInjectionDemand(
            source_algorithmic_layer=layer,
            source_steps=tuple(sorted({gate.source_step for gate in gates})),
            source_stages=tuple(sorted({gate.stage.value for gate in gates})),
            toffoli_count=len(gates),
            ccz_state_count=len(gates),
            zz_ppm_count=3 * len(gates),
            resource_x_ppm_count=3 * len(gates),
            total_ppm_count=6 * len(gates),
        )
        for layer, gates in sorted(by_layer.items())
    )


def analyze_qcla_direct_ccz_structural_point(
    trace: QclaTrace | OopQclaTrace,
    capability: DirectCczCapability,
    *,
    variant: QclaVariant,
) -> QclaDirectCczStructuralPoint:
    """Analyze one width without creating symbolic ANFs or a PPM pair table."""

    if variant == "ip":
        if not isinstance(trace, QclaTrace):
            raise DirectCczPpmScalingError("IP variant requires a QclaTrace")
        ip_metrics = qcla_metrics(trace)
        event_trace = lower_qcla_to_direct_ccz_events(trace, capability)
        source_gate_count = ip_metrics.gate_count
        source_x_count = ip_metrics.x_count
        source_cnot_count = ip_metrics.cnot_count
        source_toffoli_count = ip_metrics.toffoli_count
        source_layer_count = ip_metrics.source_layer_count
        source_storage_count_kind = "source_ancillas"
        source_storage_count = ip_metrics.source_ancilla_count
        cleanup_operation_count = sum(
            gate.source_step >= 7 for gate in trace.gates
        )
        cleanup_toffoli_count = sum(
            gate.source_step >= 7 and gate.kind is QclaGateKind.TOFFOLI
            for gate in trace.gates
        )
    else:
        if not isinstance(trace, OopQclaTrace):
            raise DirectCczPpmScalingError("OOP variant requires an OopQclaTrace")
        oop_metrics = oop_qcla_metrics(trace)
        event_trace = lower_oop_qcla_to_direct_ccz_events(trace, capability)
        source_gate_count = oop_metrics.gate_count
        source_x_count = 0
        source_cnot_count = oop_metrics.cnot_count
        source_toffoli_count = oop_metrics.toffoli_count
        source_layer_count = oop_metrics.source_layer_count
        source_storage_count_kind = "fully_resident_source_values"
        source_storage_count = oop_metrics.fully_resident_source_values
        cleanup_operation_count = sum(
            gate.stage.value in {"input_restore", "prefix_uncompute"}
            for gate in trace.gates
        )
        cleanup_toffoli_count = sum(
            gate.stage.value in {"input_restore", "prefix_uncompute"}
            and gate.kind is QclaGateKind.TOFFOLI
            for gate in trace.gates
        )

    layer_demand = _layer_demand(trace)
    event_count = len(event_trace.injection_events)
    ppm_count = sum(
        len(event.ppms) for event in event_trace.injection_events
    )
    update_count = sum(
        len(event.correction_frame) for event in event_trace.injection_events
    )
    if event_count != source_toffoli_count:
        raise DirectCczPpmScalingError("source Toffolis did not map one-to-one")
    if ppm_count != 6 * event_count or update_count != 6 * event_count:
        raise DirectCczPpmScalingError("direct-CCZ event arity is not six")
    if sum(item.toffoli_count for item in layer_demand) != event_count:
        raise DirectCczPpmScalingError("source-layer demand lost an event")

    causal_lower_bound = _weighted_causal_ppm_level_lower_bound(trace)
    nonclifford_layers = len(layer_demand)
    return QclaDirectCczStructuralPoint(
        variant=variant,
        width=trace.width,
        source_trace_id=trace.trace_id,
        event_trace_id=event_trace.trace_id,
        source_gate_count=source_gate_count,
        source_x_count=source_x_count,
        source_cnot_count=source_cnot_count,
        source_toffoli_count=source_toffoli_count,
        source_dependency_count=len(trace.dependencies),
        source_layer_count=source_layer_count,
        nonclifford_source_layer_count=nonclifford_layers,
        weighted_causal_ppm_level_lower_bound=causal_lower_bound,
        source_two_phase_injection_envelope_levels=2 * nonclifford_layers,
        direct_ccz_event_count=event_count,
        consumed_ccz_state_count=event_count,
        resource_logical_demand=3 * event_count,
        ppm_count=ppm_count,
        conditional_frame_update_count=update_count,
        theoretical_pair_count=ppm_count * (ppm_count - 1) // 2,
        pair_table_materialized=False,
        singleton_semantic_order_count=ppm_count,
        cleanup_operation_count=cleanup_operation_count,
        cleanup_toffoli_count=cleanup_toffoli_count,
        source_storage_count_kind=source_storage_count_kind,
        source_storage_count=source_storage_count,
        peak_source_toffoli_per_layer=max(
            (item.toffoli_count for item in layer_demand), default=0
        ),
        peak_source_layer_ppm_demand=max(
            (item.total_ppm_count for item in layer_demand), default=0
        ),
        layer_demand=layer_demand,
    )


def analyze_qcla_direct_ccz_exact_anchor(
    trace: QclaTrace | OopQclaTrace,
    capability: DirectCczCapability,
    backend_audit: DirectCczBackendAudit,
    *,
    variant: QclaVariant,
) -> tuple[QclaDirectCczExactAnchor, DirectCczPpmBatchAnalysis]:
    """Run the quadratic exact analysis for one explicitly chosen anchor."""

    structural = analyze_qcla_direct_ccz_structural_point(
        trace,
        capability,
        variant=variant,
    )
    if variant == "ip":
        if not isinstance(trace, QclaTrace):
            raise DirectCczPpmScalingError("IP variant requires a QclaTrace")
        symbolic = lower_qcla_to_symbolic_direct_ccz_ppm(trace, capability)
    else:
        if not isinstance(trace, OopQclaTrace):
            raise DirectCczPpmScalingError("OOP variant requires an OopQclaTrace")
        symbolic = lower_oop_qcla_to_symbolic_direct_ccz_ppm(trace, capability)
    analysis = analyze_direct_ccz_ppm_batches(
        symbolic,
        capability,
        backend_audit,
    )
    schedule = analysis.general.optimized_schedule
    profiles = analysis.general.observable_profiles
    relations = analysis.general.pair_relations
    if len(symbolic.ppms) != structural.ppm_count:
        raise DirectCczPpmScalingError("exact and structural PPM counts disagree")
    if len(relations) != structural.theoretical_pair_count:
        raise DirectCczPpmScalingError("exact pair table is incomplete")
    if (
        schedule.causal_critical_path_lower_bound
        != structural.weighted_causal_ppm_level_lower_bound
    ):
        raise DirectCczPpmScalingError(
            "source-DAG and symbolic causal lower bounds disagree"
        )
    anchor = QclaDirectCczExactAnchor(
        variant=variant,
        width=trace.width,
        trace_id=symbolic.trace_id,
        ppm_count=len(symbolic.ppms),
        materialized_pair_count=len(relations),
        candidate_batch_level_count=schedule.candidate_batch_level_count,
        causal_critical_path_lower_bound=(
            schedule.causal_critical_path_lower_bound
        ),
        conflict_clique_lower_bound=schedule.conflict_clique_lower_bound,
        combined_batch_level_lower_bound=schedule.combined_batch_level_lower_bound,
        fallback_operation_count=schedule.fallback_operation_count,
        possible_y_ppm_count=sum(profile.has_possible_y for profile in profiles),
        nonexact_weight_profile_count=sum(
            not profile.weight_bounds_exact for profile in profiles
        ),
        peak_live_logical_requirement=schedule.peak_live_logical_requirement,
        peak_resource_state_count=schedule.peak_resource_state_count,
        candidate_optimality_evidence_status=(
            schedule.optimality_evidence_status
        ),
        finite_native_schedule_emitted=analysis.finite.native_schedule_emitted,
    )
    return anchor, analysis


def assess_qcla_direct_ccz_finite_scaling_admission(
    capability: DirectCczCapability,
    backend_audit: DirectCczBackendAudit,
) -> QclaDirectCczFiniteScalingAdmission:
    """Return a negative finite-resource gate until a native mapper exists."""

    event_admitted = capability.event_lowering_admitted
    high_rate_admitted = capability.high_rate_schedule_admitted
    backend_admitted = backend_audit.candidate.backend_admitted
    mapper_missing = FINITE_NATIVE_MAPPER_OBLIGATIONS
    admitted = event_admitted and high_rate_admitted and backend_admitted and not mapper_missing
    if admitted:
        raise DirectCczPpmScalingError(
            "finite admission cannot close before a scaling native mapper exists"
        )
    return QclaDirectCczFiniteScalingAdmission(
        capability_id=capability.capability_id,
        backend_audit_id=backend_audit.audit_id,
        backend_candidate_id=backend_audit.candidate.candidate_id,
        event_lowering_admitted=event_admitted,
        high_rate_capability_admitted=high_rate_admitted,
        finite_backend_admitted=backend_admitted,
        scaling_native_mapper_admitted=False,
        capability_missing_fields=capability.missing_for_high_rate_schedule,
        backend_missing_fields=backend_audit.candidate.missing_fields,
        backend_incompatible_fields=backend_audit.candidate.incompatible_fields,
        native_mapper_missing_fields=mapper_missing,
        verdict="rejected_missing_coherent_finite_backend_and_native_mapper",
        evidence_status=EvidenceStatus.OPEN,
    )


def _layer_demand_to_data(item: SourceLayerInjectionDemand) -> dict[str, Any]:
    return {
        "ccz_state_count": item.ccz_state_count,
        "resource_x_ppm_count": item.resource_x_ppm_count,
        "source_algorithmic_layer": item.source_algorithmic_layer,
        "source_stages": list(item.source_stages),
        "source_steps": list(item.source_steps),
        "toffoli_count": item.toffoli_count,
        "total_ppm_count": item.total_ppm_count,
        "zz_ppm_count": item.zz_ppm_count,
    }


def qcla_direct_ccz_structural_point_to_data(
    point: QclaDirectCczStructuralPoint,
) -> dict[str, Any]:
    """Serialize one compact scaling point with explicit evidence boundaries."""

    return {
        "candidate_compatibility_status": point.candidate_compatibility_status.value,
        "causal_lower_bound_evidence_status": (
            point.causal_lower_bound_evidence_status.value
        ),
        "cleanup_operation_count": point.cleanup_operation_count,
        "cleanup_toffoli_count": point.cleanup_toffoli_count,
        "conditional_frame_update_count": point.conditional_frame_update_count,
        "consumed_ccz_state_count": point.consumed_ccz_state_count,
        "coordinate": "ppm_level_not_time",
        "direct_ccz_event_count": point.direct_ccz_event_count,
        "event_trace_id": point.event_trace_id,
        "layer_demand": [_layer_demand_to_data(item) for item in point.layer_demand],
        "nonclifford_source_layer_count": point.nonclifford_source_layer_count,
        "pair_table_materialized": point.pair_table_materialized,
        "peak_source_layer_ppm_demand": point.peak_source_layer_ppm_demand,
        "peak_source_toffoli_per_layer": point.peak_source_toffoli_per_layer,
        "ppm_count": point.ppm_count,
        "resource_logical_demand": point.resource_logical_demand,
        "schema": DIRECT_CCZ_PPM_SCALING_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_SCALING_SCHEMA_VERSION,
        "singleton_semantic_order_count": point.singleton_semantic_order_count,
        "source_cnot_count": point.source_cnot_count,
        "source_dependency_count": point.source_dependency_count,
        "source_gate_count": point.source_gate_count,
        "source_layer_count": point.source_layer_count,
        "source_storage_count": point.source_storage_count,
        "source_storage_count_kind": point.source_storage_count_kind,
        "source_toffoli_count": point.source_toffoli_count,
        "source_trace_id": point.source_trace_id,
        "source_two_phase_envelope_status": (
            point.source_two_phase_envelope_status.value
        ),
        "source_two_phase_injection_envelope_levels": (
            point.source_two_phase_injection_envelope_levels
        ),
        "source_x_count": point.source_x_count,
        "structural_evidence_status": point.structural_evidence_status.value,
        "theoretical_pair_count": point.theoretical_pair_count,
        "variant": point.variant,
        "weighted_causal_ppm_level_lower_bound": (
            point.weighted_causal_ppm_level_lower_bound
        ),
        "width": point.width,
    }


def qcla_direct_ccz_exact_anchor_to_data(
    anchor: QclaDirectCczExactAnchor,
) -> dict[str, Any]:
    """Serialize an exact anchor summary without duplicating its pair table."""

    return {
        "candidate_batch_level_count": anchor.candidate_batch_level_count,
        "candidate_optimality_evidence_status": (
            anchor.candidate_optimality_evidence_status.value
        ),
        "causal_critical_path_lower_bound": (
            anchor.causal_critical_path_lower_bound
        ),
        "combined_batch_level_lower_bound": anchor.combined_batch_level_lower_bound,
        "conflict_clique_lower_bound": anchor.conflict_clique_lower_bound,
        "coordinate": "candidate_batch_level_not_time",
        "fallback_operation_count": anchor.fallback_operation_count,
        "finite_native_schedule_emitted": anchor.finite_native_schedule_emitted,
        "materialized_pair_count": anchor.materialized_pair_count,
        "nonexact_weight_profile_count": anchor.nonexact_weight_profile_count,
        "peak_live_logical_requirement": anchor.peak_live_logical_requirement,
        "peak_resource_state_count": anchor.peak_resource_state_count,
        "possible_y_ppm_count": anchor.possible_y_ppm_count,
        "ppm_count": anchor.ppm_count,
        "schema": DIRECT_CCZ_PPM_EXACT_ANCHOR_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_SCALING_SCHEMA_VERSION,
        "trace_id": anchor.trace_id,
        "variant": anchor.variant,
        "width": anchor.width,
    }


def qcla_direct_ccz_finite_scaling_admission_to_data(
    admission: QclaDirectCczFiniteScalingAdmission,
) -> dict[str, Any]:
    """Serialize finite rejection with every prohibited output visibly null."""

    return {
        "backend_audit_id": admission.backend_audit_id,
        "backend_candidate_id": admission.backend_candidate_id,
        "backend_incompatible_fields": list(admission.backend_incompatible_fields),
        "backend_missing_fields": list(admission.backend_missing_fields),
        "capability_id": admission.capability_id,
        "capability_missing_fields": list(admission.capability_missing_fields),
        "ccz_buffer_trajectory": admission.ccz_buffer_trajectory,
        "decoder_service": admission.decoder_service,
        "event_lowering_admitted": admission.event_lowering_admitted,
        "evidence_status": admission.evidence_status.value,
        "failure_probability": admission.failure_probability,
        "finite_backend_admitted": admission.finite_backend_admitted,
        "high_rate_capability_admitted": admission.high_rate_capability_admitted,
        "memory_traffic": admission.memory_traffic,
        "native_mapper_missing_fields": list(admission.native_mapper_missing_fields),
        "native_schedule": admission.native_schedule,
        "physical_qubits": admission.physical_qubits,
        "reaction_latency_seconds": admission.reaction_latency_seconds,
        "routing_cost": admission.routing_cost,
        "runtime_seconds": admission.runtime_seconds,
        "scaling_native_mapper_admitted": admission.scaling_native_mapper_admitted,
        "schema": DIRECT_CCZ_PPM_FINITE_SCALING_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_SCALING_SCHEMA_VERSION,
        "surgery_rounds": admission.surgery_rounds,
        "verdict": admission.verdict,
    }
