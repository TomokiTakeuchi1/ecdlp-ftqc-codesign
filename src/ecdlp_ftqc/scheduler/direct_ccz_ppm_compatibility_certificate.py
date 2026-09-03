"""Linear-size compatibility certificates for source-aligned direct-CCZ PPMs.

The certificate is deliberately architecture independent.  It proves a
logical sufficient-condition screen for the reviewed Figure-14(a) injection
and QCLA source traces; it does not construct a native surgery schedule or a
time coordinate.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Literal

from ecdlp_ftqc.circuits import OopQclaTrace, QclaGateKind, QclaTrace
from ecdlp_ftqc.compiler import DirectCczEventTrace
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler.direct_ccz_ppm_batching import DirectCczPpmBatchAnalysis

DIRECT_CCZ_PPM_COMPATIBILITY_CERTIFICATE_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-scalable-compatibility-certificate"
)
DIRECT_CCZ_PPM_COMPATIBILITY_CERTIFICATE_SCHEMA_VERSION = 1
DIRECT_CCZ_PPM_EXACT_EQUIVALENCE_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-exact-compatibility-equivalence"
)
COMPATIBILITY_COORDINATE = "candidate_batch_level_not_time"
FRAME_NORMAL_FORM = "ordered-conditional-cliffords-with-anf-conditions-v1"
FRAME_GENERATORS = ("CNOT", "CZ", "X", "Z")
PROOF_SCOPE = (
    "logical_same-axis_no-Y_no-causal-order_no-resource-reuse_screen"
)

QclaVariant = Literal["oop", "ip"]


class DirectCczPpmCompatibilityCertificateError(ValueError):
    """Raised when certificate inputs are inconsistent rather than falsified."""


@dataclass(frozen=True, slots=True)
class CompatibilityCounterexample:
    """The first deterministic witness to a failed proof obligation."""

    obligation: str
    source_algorithmic_layer: int | None
    source_gate_id: str | None
    event_id: str | None
    detail: str


@dataclass(frozen=True, slots=True)
class FrameClosureCertificate:
    """Generator-level proof that branchwise Z observables remain Z type."""

    frame_normal_form: str
    allowed_frame_generators: tuple[str, ...]
    source_passthrough_generators: tuple[str, ...]
    event_correction_generators: tuple[str, ...]
    z_subspace_closed_under_every_generator: bool
    resource_values_absent_from_every_frame_generator: bool
    proof_rule: str
    evidence_status: EvidenceStatus


@dataclass(frozen=True, slots=True)
class SourceAlignedBatchCertificate:
    """One linear-size certificate for a batch whose pairs are not enumerated."""

    batch_level: int
    source_algorithmic_layer: int
    injection_layer: int
    source_gate_count: int
    event_count: int
    ppm_count: int
    implicit_pair_count: int
    source_gate_id_sha256: str
    ppm_operation_id_sha256: str
    first_operation_id: str
    last_operation_id: str
    presented_axis_class: str
    branch_possible_y: bool
    universally_commuting: bool
    universally_axis_consistent: bool
    causally_independent: bool
    resource_reuse_free: bool
    general_high_rate_compatible: bool
    pair_records_materialized: bool
    proof_rule: str
    evidence_status: EvidenceStatus


@dataclass(frozen=True, slots=True)
class QclaPpmCompatibilityCertificate:
    """A source/event certificate for one QCLA variant and width."""

    variant: QclaVariant
    width: int
    source_trace_id: str
    event_trace_id: str
    capability_id: str
    frame_closure: FrameClosureCertificate | None
    batches: tuple[SourceAlignedBatchCertificate, ...]
    source_gate_count: int
    source_dependency_count: int
    direct_ccz_event_count: int
    ppm_count: int
    nonclifford_source_layers: tuple[int, ...]
    candidate_batch_level_count: int | None
    weighted_causal_lower_bound: int
    candidate_equals_causal_lower_bound: bool
    implicit_within_batch_pair_count: int
    theoretical_global_pair_count: int
    materialized_pair_count: int
    records_checked: int
    asymptotic_certificate_size: str
    proof_scope: str
    compatibility_evidence_status: EvidenceStatus
    candidate_optimality_evidence_status: EvidenceStatus
    counterexample: CompatibilityCounterexample | None
    complete_native_schedule: bool = False
    surgery_rounds: None = None
    runtime_seconds: None = None
    physical_qubits: None = None
    failure_probability: None = None

    @property
    def compatibility_proved(self) -> bool:
        return self.compatibility_evidence_status is EvidenceStatus.PROVED


@dataclass(frozen=True, slots=True)
class ExactAnchorCompatibilityEquivalence:
    """Full-ANF comparison for one bounded exact anchor."""

    variant: QclaVariant
    width: int
    certificate_batch_level_count: int
    exact_source_aligned_batch_level_count: int
    exact_optimized_batch_level_count: int
    exact_causal_lower_bound: int
    global_materialized_pair_count: int
    materialized_intra_batch_pair_count: int
    batch_membership_digest_match: bool
    every_materialized_intra_batch_pair_compatible: bool
    every_exact_profile_y_free: bool
    candidate_level_count_match: bool
    causal_lower_bound_match: bool
    all_checks_passed: bool
    evidence_status: EvidenceStatus


_CORRECTION_RE = re.compile(r"^(CZ|X|Z)\(([^)]*)\)\^(.+)$")


def _digest_ids(values: tuple[str, ...]) -> str:
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _weighted_causal_depth(trace: QclaTrace | OopQclaTrace) -> int:
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


def _counterexample(
    obligation: str,
    detail: str,
    *,
    layer: int | None = None,
    gate_id: str | None = None,
    event_id: str | None = None,
) -> CompatibilityCounterexample:
    return CompatibilityCounterexample(
        obligation=obligation,
        source_algorithmic_layer=layer,
        source_gate_id=gate_id,
        event_id=event_id,
        detail=detail,
    )


def _falsified_certificate(
    trace: QclaTrace | OopQclaTrace,
    event_trace: DirectCczEventTrace,
    *,
    variant: QclaVariant,
    witness: CompatibilityCounterexample,
) -> QclaPpmCompatibilityCertificate:
    ppm_count = sum(len(event.ppms) for event in event_trace.injection_events)
    nonclifford_layers = tuple(
        sorted(
            {
                gate.algorithmic_layer
                for gate in trace.gates
                if gate.kind is QclaGateKind.TOFFOLI
            }
        )
    )
    return QclaPpmCompatibilityCertificate(
        variant=variant,
        width=trace.width,
        source_trace_id=trace.trace_id,
        event_trace_id=event_trace.trace_id,
        capability_id=event_trace.capability_id,
        frame_closure=None,
        batches=(),
        source_gate_count=len(trace.gates),
        source_dependency_count=len(trace.dependencies),
        direct_ccz_event_count=len(event_trace.injection_events),
        ppm_count=ppm_count,
        nonclifford_source_layers=nonclifford_layers,
        candidate_batch_level_count=None,
        weighted_causal_lower_bound=_weighted_causal_depth(trace),
        candidate_equals_causal_lower_bound=False,
        implicit_within_batch_pair_count=0,
        theoretical_global_pair_count=ppm_count * (ppm_count - 1) // 2,
        materialized_pair_count=0,
        records_checked=0,
        asymptotic_certificate_size="O(source_gates + source_dependencies + PPMs)",
        proof_scope=PROOF_SCOPE,
        compatibility_evidence_status=EvidenceStatus.FALSIFIED,
        candidate_optimality_evidence_status=EvidenceStatus.OPEN,
        counterexample=witness,
    )


def _validate_variant(
    trace: QclaTrace | OopQclaTrace,
    variant: QclaVariant,
) -> None:
    if variant == "oop" and not isinstance(trace, OopQclaTrace):
        raise DirectCczPpmCompatibilityCertificateError(
            "OOP compatibility requires OopQclaTrace"
        )
    if variant == "ip" and not isinstance(trace, QclaTrace):
        raise DirectCczPpmCompatibilityCertificateError(
            "IP compatibility requires QclaTrace"
        )


def certify_qcla_direct_ccz_ppm_compatibility(
    trace: QclaTrace | OopQclaTrace,
    event_trace: DirectCczEventTrace,
    *,
    variant: QclaVariant,
) -> QclaPpmCompatibilityCertificate:
    """Prove or falsify source-aligned two-phase logical compatibility.

    The proof is linear in the source/event representation.  It checks the
    premises of a generator-closure argument and never creates a PPM-pair
    relation table.
    """

    _validate_variant(trace, variant)
    if event_trace.complete_native_schedule:
        raise DirectCczPpmCompatibilityCertificateError(
            "event input must remain architecture independent"
        )
    if event_trace.source_trace_id != trace.trace_id:
        return _falsified_certificate(
            trace,
            event_trace,
            variant=variant,
            witness=_counterexample(
                "source_event_binding",
                "event trace source ID does not match the supplied source trace",
            ),
        )

    gate_by_id = {gate.gate_id: gate for gate in trace.gates}
    toffolis = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    expected_passthrough = tuple(
        gate.gate_id for gate in trace.gates if gate.kind is not QclaGateKind.TOFFOLI
    )
    if event_trace.passthrough_clifford_gate_ids != expected_passthrough:
        return _falsified_certificate(
            trace,
            event_trace,
            variant=variant,
            witness=_counterexample(
                "source_gate_partition",
                "passthrough Clifford IDs do not equal all non-Toffoli source gates",
            ),
        )
    if len(event_trace.injection_events) != len(toffolis):
        return _falsified_certificate(
            trace,
            event_trace,
            variant=variant,
            witness=_counterexample(
                "one_event_per_toffoli",
                "direct-CCZ event count differs from source Toffoli count",
            ),
        )

    source_dependency_rows = tuple(
        (
            item.predecessor,
            item.successor,
            item.values,
            item.reason,
        )
        for item in trace.dependencies
    )
    event_dependency_rows = tuple(
        (
            item.predecessor_source_gate_id,
            item.successor_source_gate_id,
            item.logical_values,
            item.reason,
        )
        for item in event_trace.source_dependencies
    )
    if event_dependency_rows != source_dependency_rows:
        return _falsified_certificate(
            trace,
            event_trace,
            variant=variant,
            witness=_counterexample(
                "source_dependency_preservation",
                "event dependencies do not reproduce the source DAG exactly",
            ),
        )
    for dependency in trace.dependencies:
        predecessor = gate_by_id[dependency.predecessor]
        successor = gate_by_id[dependency.successor]
        if predecessor.algorithmic_layer >= successor.algorithmic_layer:
            return _falsified_certificate(
                trace,
                event_trace,
                variant=variant,
                witness=_counterexample(
                    "strict_layered_causality",
                    "a source dependency does not advance the algorithmic layer",
                    layer=successor.algorithmic_layer,
                    gate_id=successor.gate_id,
                ),
            )

    by_layer: dict[int, list[Any]] = {}
    for gate in trace.gates:
        by_layer.setdefault(gate.algorithmic_layer, []).append(gate)
    for layer, gates in sorted(by_layer.items()):
        occupied: set[str] = set()
        for gate in gates:
            overlap = occupied & set(gate.logical_support)
            if overlap:
                return _falsified_certificate(
                    trace,
                    event_trace,
                    variant=variant,
                    witness=_counterexample(
                        "source_layer_disjoint_support",
                        "source layer reuses logical support: " + ", ".join(sorted(overlap)),
                        layer=layer,
                        gate_id=gate.gate_id,
                    ),
                )
            occupied.update(gate.logical_support)

    expected_shapes = (
        (1, ("Z", "Z"), 0),
        (1, ("Z", "Z"), 1),
        (1, ("Z", "Z"), 2),
        (2, ("X",), 0),
        (2, ("X",), 1),
        (2, ("X",), 2),
    )
    expected_correction_kinds = ("CZ", "CZ", "CZ", "Z", "Z", "X")
    all_resources: set[str] = set()
    source_logical_values = frozenset(
        logical
        for source_gate in trace.gates
        for logical in source_gate.logical_support
    )
    event_by_gate: dict[str, Any] = {}
    observed_correction_kinds: set[str] = set()
    for ordinal, (gate, event) in enumerate(
        zip(toffolis, event_trace.injection_events, strict=True)
    ):
        expected_event_id = f"direct-ccz:{ordinal:06d}"
        if (
            event.event_id != expected_event_id
            or event.source_gate_id != gate.gate_id
            or event.source_algorithmic_layer != gate.algorithmic_layer
            or event.data != (*gate.controls, gate.target)
        ):
            return _falsified_certificate(
                trace,
                event_trace,
                variant=variant,
                witness=_counterexample(
                    "event_source_mapping",
                    "event identity, layer, or data support differs from its source Toffoli",
                    layer=gate.algorithmic_layer,
                    gate_id=gate.gate_id,
                    event_id=event.event_id,
                ),
            )
        if set(event.resource) & all_resources:
            return _falsified_certificate(
                trace,
                event_trace,
                variant=variant,
                witness=_counterexample(
                    "globally_fresh_resources",
                    "a CCZ resource logical is reused by multiple events",
                    layer=gate.algorithmic_layer,
                    gate_id=gate.gate_id,
                    event_id=event.event_id,
                ),
            )
        if set(event.resource) & source_logical_values:
            return _falsified_certificate(
                trace,
                event_trace,
                variant=variant,
                witness=_counterexample(
                    "resource_source_disjointness",
                    "a CCZ resource aliases source logical support",
                    layer=gate.algorithmic_layer,
                    gate_id=gate.gate_id,
                    event_id=event.event_id,
                ),
            )
        all_resources.update(event.resource)
        if len(event.ppms) != 6:
            return _falsified_certificate(
                trace,
                event_trace,
                variant=variant,
                witness=_counterexample(
                    "canonical_six_ppm_event",
                    "event does not contain exactly six PPMs",
                    layer=gate.algorithmic_layer,
                    gate_id=gate.gate_id,
                    event_id=event.event_id,
                ),
            )
        for ppm, (injection_layer, paulis, index) in zip(
            event.ppms, expected_shapes, strict=True
        ):
            expected_support = (
                (event.resource[index], event.data[index])
                if injection_layer == 1
                else (event.resource[index],)
            )
            if (
                ppm.layer != injection_layer
                or ppm.pauli_terms != paulis
                or ppm.logical_support != expected_support
            ):
                return _falsified_certificate(
                    trace,
                    event_trace,
                    variant=variant,
                    witness=_counterexample(
                        "canonical_ppm_shape",
                        f"{ppm.event_id} is not the required ZZ/resource-X measurement",
                        layer=gate.algorithmic_layer,
                        gate_id=gate.gate_id,
                        event_id=event.event_id,
                    ),
                )
        correction_kinds: list[str] = []
        for expression in event.correction_frame:
            match = _CORRECTION_RE.fullmatch(expression)
            if match is None:
                return _falsified_certificate(
                    trace,
                    event_trace,
                    variant=variant,
                    witness=_counterexample(
                        "computational_basis_preserving_frame",
                        "correction is not a conditional CZ/X/Z generator",
                        layer=gate.algorithmic_layer,
                        gate_id=gate.gate_id,
                        event_id=event.event_id,
                    ),
                )
            kind, raw_support, _ = match.groups()
            support = tuple(item.strip() for item in raw_support.split(","))
            if not set(support) <= set(event.data):
                return _falsified_certificate(
                    trace,
                    event_trace,
                    variant=variant,
                    witness=_counterexample(
                        "resources_absent_from_frame",
                        "a deferred correction acts outside the event data support",
                        layer=gate.algorithmic_layer,
                        gate_id=gate.gate_id,
                        event_id=event.event_id,
                    ),
                )
            correction_kinds.append(kind)
            observed_correction_kinds.add(kind)
        if tuple(correction_kinds) != expected_correction_kinds:
            return _falsified_certificate(
                trace,
                event_trace,
                variant=variant,
                witness=_counterexample(
                    "canonical_correction_generator_order",
                    "correction generator order differs from three CZ then Z/Z/X",
                    layer=gate.algorithmic_layer,
                    gate_id=gate.gate_id,
                    event_id=event.event_id,
                ),
            )
        event_by_gate[gate.gate_id] = event

    passthrough_kinds = tuple(
        sorted(
            {
                gate.kind.name
                for gate in trace.gates
                if gate.kind is not QclaGateKind.TOFFOLI
            }
        )
    )
    if not set(passthrough_kinds) <= {"CNOT", "X"}:
        return _falsified_certificate(
            trace,
            event_trace,
            variant=variant,
            witness=_counterexample(
                "computational_basis_preserving_passthrough",
                "source contains a passthrough Clifford outside X/CNOT",
            ),
        )

    frame_closure = FrameClosureCertificate(
        frame_normal_form=FRAME_NORMAL_FORM,
        allowed_frame_generators=FRAME_GENERATORS,
        source_passthrough_generators=passthrough_kinds,
        event_correction_generators=tuple(sorted(observed_correction_kinds)),
        z_subspace_closed_under_every_generator=True,
        resource_values_absent_from_every_frame_generator=True,
        proof_rule=(
            "X/Z do not change Pauli support axes; CNOT maps Z type to Z type; "
            "CZ fixes Z type. Conditional selection therefore preserves branchwise "
            "Z type, and fresh resource values never enter the deferred frame."
        ),
        evidence_status=EvidenceStatus.PROVED,
    )

    batches: list[SourceAlignedBatchCertificate] = []
    nonclifford_layers = tuple(
        layer
        for layer, gates in sorted(by_layer.items())
        if any(gate.kind is QclaGateKind.TOFFOLI for gate in gates)
    )
    for source_layer in nonclifford_layers:
        layer_gates = tuple(
            gate
            for gate in by_layer[source_layer]
            if gate.kind is QclaGateKind.TOFFOLI
        )
        layer_events = tuple(event_by_gate[gate.gate_id] for gate in layer_gates)
        source_ids = tuple(gate.gate_id for gate in layer_gates)
        for injection_layer in (1, 2):
            operation_ids = tuple(
                ppm.event_id
                for event in layer_events
                for ppm in event.ppms
                if ppm.layer == injection_layer
            )
            ppm_count = len(operation_ids)
            if ppm_count != 3 * len(layer_events):
                return _falsified_certificate(
                    trace,
                    event_trace,
                    variant=variant,
                    witness=_counterexample(
                        "three_ppms_per_event_phase",
                        "a source-aligned phase does not contain three PPMs per event",
                        layer=source_layer,
                    ),
                )
            if injection_layer == 1:
                axis_class = "BRANCHWISE_Z_ONLY_UNDER_FRAME_GENERATOR_CLOSURE"
                rule = (
                    "Every bare resource-data ZZ PPM remains branchwise Z type; "
                    "overlap can therefore only use the same Z axis."
                )
            else:
                axis_class = "FRESH_RESOURCE_SINGLE_X_ONLY"
                rule = (
                    "Every resource readout is a single X on a globally unique fresh "
                    "resource excluded from the deferred frame."
                )
            batches.append(
                SourceAlignedBatchCertificate(
                    batch_level=len(batches) + 1,
                    source_algorithmic_layer=source_layer,
                    injection_layer=injection_layer,
                    source_gate_count=len(source_ids),
                    event_count=len(layer_events),
                    ppm_count=ppm_count,
                    implicit_pair_count=ppm_count * (ppm_count - 1) // 2,
                    source_gate_id_sha256=_digest_ids(source_ids),
                    ppm_operation_id_sha256=_digest_ids(operation_ids),
                    first_operation_id=operation_ids[0],
                    last_operation_id=operation_ids[-1],
                    presented_axis_class=axis_class,
                    branch_possible_y=False,
                    universally_commuting=True,
                    universally_axis_consistent=True,
                    causally_independent=True,
                    resource_reuse_free=True,
                    general_high_rate_compatible=True,
                    pair_records_materialized=False,
                    proof_rule=rule,
                    evidence_status=EvidenceStatus.PROVED,
                )
            )

    ppm_count = sum(len(event.ppms) for event in event_trace.injection_events)
    candidate_levels = len(batches)
    causal_lower_bound = _weighted_causal_depth(trace)
    equals_lower_bound = candidate_levels == causal_lower_bound
    return QclaPpmCompatibilityCertificate(
        variant=variant,
        width=trace.width,
        source_trace_id=trace.trace_id,
        event_trace_id=event_trace.trace_id,
        capability_id=event_trace.capability_id,
        frame_closure=frame_closure,
        batches=tuple(batches),
        source_gate_count=len(trace.gates),
        source_dependency_count=len(trace.dependencies),
        direct_ccz_event_count=len(event_trace.injection_events),
        ppm_count=ppm_count,
        nonclifford_source_layers=nonclifford_layers,
        candidate_batch_level_count=candidate_levels,
        weighted_causal_lower_bound=causal_lower_bound,
        candidate_equals_causal_lower_bound=equals_lower_bound,
        implicit_within_batch_pair_count=sum(
            batch.implicit_pair_count for batch in batches
        ),
        theoretical_global_pair_count=ppm_count * (ppm_count - 1) // 2,
        materialized_pair_count=0,
        records_checked=(
            len(trace.gates)
            + len(trace.dependencies)
            + len(event_trace.injection_events)
            + ppm_count
        ),
        asymptotic_certificate_size="O(source_gates + source_dependencies + PPMs)",
        proof_scope=PROOF_SCOPE,
        compatibility_evidence_status=EvidenceStatus.PROVED,
        candidate_optimality_evidence_status=(
            EvidenceStatus.PROVED if equals_lower_bound else EvidenceStatus.OPEN
        ),
        counterexample=None,
    )


def compare_certificate_to_exact_anchor(
    certificate: QclaPpmCompatibilityCertificate,
    exact_analysis: DirectCczPpmBatchAnalysis,
) -> ExactAnchorCompatibilityEquivalence:
    """Compare a compact certificate with a fully materialized ANF anchor."""

    if not certificate.compatibility_proved or certificate.candidate_batch_level_count is None:
        raise DirectCczPpmCompatibilityCertificateError(
            "only a proved compact certificate can be compared to an exact anchor"
        )
    schedule = exact_analysis.general.source_layer_aligned_schedule
    optimized = exact_analysis.general.optimized_schedule
    relation_by_pair = {
        frozenset((item.left_operation_id, item.right_operation_id)): item
        for item in exact_analysis.general.pair_relations
    }
    profile_by_id = {
        item.operation_id: item for item in exact_analysis.general.observable_profiles
    }
    digest_match = len(schedule.batches) == len(certificate.batches)
    compatible = True
    y_free = True
    intra_pair_count = 0
    for compact, exact in zip(certificate.batches, schedule.batches, strict=False):
        digest_match &= compact.ppm_operation_id_sha256 == _digest_ids(
            exact.operation_ids
        )
        y_free &= all(not profile_by_id[item].has_possible_y for item in exact.operation_ids)
        for left, right in combinations(exact.operation_ids, 2):
            intra_pair_count += 1
            compatible &= relation_by_pair[frozenset((left, right))].general_high_rate_compatible
    level_match = (
        certificate.candidate_batch_level_count
        == schedule.candidate_batch_level_count
        == optimized.candidate_batch_level_count
    )
    causal_match = (
        certificate.weighted_causal_lower_bound
        == schedule.causal_critical_path_lower_bound
        == optimized.causal_critical_path_lower_bound
    )
    all_passed = digest_match and compatible and y_free and level_match and causal_match
    return ExactAnchorCompatibilityEquivalence(
        variant=certificate.variant,
        width=certificate.width,
        certificate_batch_level_count=certificate.candidate_batch_level_count,
        exact_source_aligned_batch_level_count=schedule.candidate_batch_level_count,
        exact_optimized_batch_level_count=optimized.candidate_batch_level_count,
        exact_causal_lower_bound=schedule.causal_critical_path_lower_bound,
        global_materialized_pair_count=len(exact_analysis.general.pair_relations),
        materialized_intra_batch_pair_count=intra_pair_count,
        batch_membership_digest_match=digest_match,
        every_materialized_intra_batch_pair_compatible=compatible,
        every_exact_profile_y_free=y_free,
        candidate_level_count_match=level_match,
        causal_lower_bound_match=causal_match,
        all_checks_passed=all_passed,
        evidence_status=(
            EvidenceStatus.NUMERICAL if all_passed else EvidenceStatus.FALSIFIED
        ),
    )


def _counterexample_to_data(item: CompatibilityCounterexample) -> dict[str, Any]:
    return {
        "detail": item.detail,
        "event_id": item.event_id,
        "obligation": item.obligation,
        "source_algorithmic_layer": item.source_algorithmic_layer,
        "source_gate_id": item.source_gate_id,
    }


def qcla_ppm_compatibility_certificate_to_data(
    certificate: QclaPpmCompatibilityCertificate,
) -> dict[str, Any]:
    """Return a deterministic JSON-compatible compact certificate."""

    frame = certificate.frame_closure
    return {
        "asymptotic_certificate_size": certificate.asymptotic_certificate_size,
        "batches": [
            {
                "batch_level": batch.batch_level,
                "branch_possible_y": batch.branch_possible_y,
                "causally_independent": batch.causally_independent,
                "event_count": batch.event_count,
                "evidence_status": batch.evidence_status.value,
                "first_operation_id": batch.first_operation_id,
                "general_high_rate_compatible": batch.general_high_rate_compatible,
                "implicit_pair_count": batch.implicit_pair_count,
                "injection_layer": batch.injection_layer,
                "last_operation_id": batch.last_operation_id,
                "pair_records_materialized": batch.pair_records_materialized,
                "ppm_count": batch.ppm_count,
                "ppm_operation_id_sha256": batch.ppm_operation_id_sha256,
                "presented_axis_class": batch.presented_axis_class,
                "proof_rule": batch.proof_rule,
                "resource_reuse_free": batch.resource_reuse_free,
                "source_algorithmic_layer": batch.source_algorithmic_layer,
                "source_gate_count": batch.source_gate_count,
                "source_gate_id_sha256": batch.source_gate_id_sha256,
                "universally_axis_consistent": batch.universally_axis_consistent,
                "universally_commuting": batch.universally_commuting,
            }
            for batch in certificate.batches
        ],
        "candidate_batch_level_count": certificate.candidate_batch_level_count,
        "candidate_equals_causal_lower_bound": (
            certificate.candidate_equals_causal_lower_bound
        ),
        "candidate_optimality_evidence_status": (
            certificate.candidate_optimality_evidence_status.value
        ),
        "capability_id": certificate.capability_id,
        "compatibility_evidence_status": (
            certificate.compatibility_evidence_status.value
        ),
        "complete_native_schedule": certificate.complete_native_schedule,
        "coordinate": COMPATIBILITY_COORDINATE,
        "counterexample": (
            None
            if certificate.counterexample is None
            else _counterexample_to_data(certificate.counterexample)
        ),
        "direct_ccz_event_count": certificate.direct_ccz_event_count,
        "event_trace_id": certificate.event_trace_id,
        "failure_probability": certificate.failure_probability,
        "frame_closure": (
            None
            if frame is None
            else {
                "allowed_frame_generators": list(frame.allowed_frame_generators),
                "event_correction_generators": list(
                    frame.event_correction_generators
                ),
                "evidence_status": frame.evidence_status.value,
                "frame_normal_form": frame.frame_normal_form,
                "proof_rule": frame.proof_rule,
                "resource_values_absent_from_every_frame_generator": (
                    frame.resource_values_absent_from_every_frame_generator
                ),
                "source_passthrough_generators": list(
                    frame.source_passthrough_generators
                ),
                "z_subspace_closed_under_every_generator": (
                    frame.z_subspace_closed_under_every_generator
                ),
            }
        ),
        "implicit_within_batch_pair_count": (
            certificate.implicit_within_batch_pair_count
        ),
        "materialized_pair_count": certificate.materialized_pair_count,
        "nonclifford_source_layers": list(certificate.nonclifford_source_layers),
        "physical_qubits": certificate.physical_qubits,
        "ppm_count": certificate.ppm_count,
        "proof_scope": certificate.proof_scope,
        "records_checked": certificate.records_checked,
        "runtime_seconds": certificate.runtime_seconds,
        "schema": DIRECT_CCZ_PPM_COMPATIBILITY_CERTIFICATE_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_COMPATIBILITY_CERTIFICATE_SCHEMA_VERSION,
        "source_dependency_count": certificate.source_dependency_count,
        "source_gate_count": certificate.source_gate_count,
        "source_trace_id": certificate.source_trace_id,
        "surgery_rounds": certificate.surgery_rounds,
        "theoretical_global_pair_count": certificate.theoretical_global_pair_count,
        "variant": certificate.variant,
        "weighted_causal_lower_bound": certificate.weighted_causal_lower_bound,
        "width": certificate.width,
    }


def exact_anchor_compatibility_equivalence_to_data(
    equivalence: ExactAnchorCompatibilityEquivalence,
) -> dict[str, Any]:
    """Return a deterministic JSON-compatible exact-anchor comparison."""

    return {
        "all_checks_passed": equivalence.all_checks_passed,
        "batch_membership_digest_match": equivalence.batch_membership_digest_match,
        "candidate_level_count_match": equivalence.candidate_level_count_match,
        "causal_lower_bound_match": equivalence.causal_lower_bound_match,
        "certificate_batch_level_count": equivalence.certificate_batch_level_count,
        "evidence_status": equivalence.evidence_status.value,
        "every_exact_profile_y_free": equivalence.every_exact_profile_y_free,
        "every_materialized_intra_batch_pair_compatible": (
            equivalence.every_materialized_intra_batch_pair_compatible
        ),
        "exact_causal_lower_bound": equivalence.exact_causal_lower_bound,
        "exact_optimized_batch_level_count": (
            equivalence.exact_optimized_batch_level_count
        ),
        "exact_source_aligned_batch_level_count": (
            equivalence.exact_source_aligned_batch_level_count
        ),
        "global_materialized_pair_count": equivalence.global_materialized_pair_count,
        "materialized_intra_batch_pair_count": (
            equivalence.materialized_intra_batch_pair_count
        ),
        "schema": DIRECT_CCZ_PPM_EXACT_EQUIVALENCE_SCHEMA,
        "schema_version": 1,
        "variant": equivalence.variant,
        "width": equivalence.width,
    }
