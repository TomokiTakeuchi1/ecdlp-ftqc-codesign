"""Independent replay for scalable direct-CCZ PPM compatibility certificates.

This module imports neither the direct-CCZ compiler nor any scheduler.  It
rebuilds the certificate from the source QCLA traces and the pinned six-PPM
event naming contract.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ecdlp_ftqc.circuits import (
    OopQclaTrace,
    QclaGateKind,
    QclaTrace,
    build_oop_qcla_trace,
    build_qcla_trace,
)

CERTIFICATE_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-scalable-compatibility-certificate"
)
EXACT_EQUIVALENCE_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-exact-compatibility-equivalence"
)
CAPABILITY_ID = "architecture-direct-ccz-single-event-figure14-v1"
FRAME_NORMAL_FORM = "ordered-conditional-cliffords-with-anf-conditions-v1"
PROOF_SCOPE = (
    "logical_same-axis_no-Y_no-causal-order_no-resource-reuse_screen"
)
MEASUREMENT_IDS = ("zz_0", "zz_1", "zz_2", "x_0", "x_1", "x_2")


class DirectCczPpmCompatibilityReplayError(ValueError):
    """Raised when serialized compatibility data is malformed."""


@dataclass(frozen=True, slots=True)
class DirectCczPpmCompatibilityReplaySummary:
    """Independent replay result for a complete certificate sweep."""

    widths: tuple[int, ...]
    certificate_count: int
    exact_equivalence_count: int
    checks: tuple[tuple[str, bool], ...]

    @property
    def all_passed(self) -> bool:
        return all(passed for _, passed in self.checks)


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) for key in value
    ):
        raise DirectCczPpmCompatibilityReplayError(
            f"{path} must be a string-keyed mapping"
        )
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DirectCczPpmCompatibilityReplayError(f"{path} must be a sequence")
    return value


def _required(item: Mapping[str, object], key: str, path: str) -> object:
    if key not in item:
        raise DirectCczPpmCompatibilityReplayError(f"{path} is missing {key!r}")
    return item[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczPpmCompatibilityReplayError(
            f"{path} must be a nonempty string"
        )
    return value


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DirectCczPpmCompatibilityReplayError(f"{path} must be an integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DirectCczPpmCompatibilityReplayError(f"{path} must be Boolean")
    return value


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


def _expected_certificate(
    trace: QclaTrace | OopQclaTrace,
    variant: str,
) -> dict[str, object]:
    toffolis = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    ordinal_by_gate = {gate.gate_id: index for index, gate in enumerate(toffolis)}
    by_layer: dict[int, list[Any]] = {}
    for gate in trace.gates:
        by_layer.setdefault(gate.algorithmic_layer, []).append(gate)
    nonclifford_layers = tuple(
        layer
        for layer, gates in sorted(by_layer.items())
        if any(gate.kind is QclaGateKind.TOFFOLI for gate in gates)
    )
    batches: list[dict[str, object]] = []
    for source_layer in nonclifford_layers:
        gates = tuple(
            gate
            for gate in by_layer[source_layer]
            if gate.kind is QclaGateKind.TOFFOLI
        )
        source_ids = tuple(gate.gate_id for gate in gates)
        for injection_layer in (1, 2):
            measurement_ids = (
                MEASUREMENT_IDS[:3] if injection_layer == 1 else MEASUREMENT_IDS[3:]
            )
            operation_ids = tuple(
                f"direct-ccz:{ordinal_by_gate[gate.gate_id]:06d}:ppm:{measurement_id}"
                for gate in gates
                for measurement_id in measurement_ids
            )
            ppm_count = len(operation_ids)
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
                {
                    "batch_level": len(batches) + 1,
                    "branch_possible_y": False,
                    "causally_independent": True,
                    "event_count": len(gates),
                    "evidence_status": "PROVED",
                    "first_operation_id": operation_ids[0],
                    "general_high_rate_compatible": True,
                    "implicit_pair_count": ppm_count * (ppm_count - 1) // 2,
                    "injection_layer": injection_layer,
                    "last_operation_id": operation_ids[-1],
                    "pair_records_materialized": False,
                    "ppm_count": ppm_count,
                    "ppm_operation_id_sha256": _digest_ids(operation_ids),
                    "presented_axis_class": axis_class,
                    "proof_rule": rule,
                    "resource_reuse_free": True,
                    "source_algorithmic_layer": source_layer,
                    "source_gate_count": len(gates),
                    "source_gate_id_sha256": _digest_ids(source_ids),
                    "universally_axis_consistent": True,
                    "universally_commuting": True,
                }
            )
    ppm_count = 6 * len(toffolis)
    lower_bound = _weighted_causal_depth(trace)
    candidate_count = len(batches)
    passthrough_generators = sorted(
        {
            gate.kind.name
            for gate in trace.gates
            if gate.kind is not QclaGateKind.TOFFOLI
        }
    )
    return {
        "asymptotic_certificate_size": "O(source_gates + source_dependencies + PPMs)",
        "batches": batches,
        "candidate_batch_level_count": candidate_count,
        "candidate_equals_causal_lower_bound": candidate_count == lower_bound,
        "candidate_optimality_evidence_status": (
            "PROVED" if candidate_count == lower_bound else "OPEN"
        ),
        "capability_id": CAPABILITY_ID,
        "compatibility_evidence_status": "PROVED",
        "complete_native_schedule": False,
        "coordinate": "candidate_batch_level_not_time",
        "counterexample": None,
        "direct_ccz_event_count": len(toffolis),
        "event_trace_id": f"{trace.trace_id}:direct-ccz-events-v2",
        "failure_probability": None,
        "frame_closure": {
            "allowed_frame_generators": ["CNOT", "CZ", "X", "Z"],
            "event_correction_generators": ["CZ", "X", "Z"],
            "evidence_status": "PROVED",
            "frame_normal_form": FRAME_NORMAL_FORM,
            "proof_rule": (
                "X/Z do not change Pauli support axes; CNOT maps Z type to Z type; "
                "CZ fixes Z type. Conditional selection therefore preserves branchwise "
                "Z type, and fresh resource values never enter the deferred frame."
            ),
            "resource_values_absent_from_every_frame_generator": True,
            "source_passthrough_generators": passthrough_generators,
            "z_subspace_closed_under_every_generator": True,
        },
        "implicit_within_batch_pair_count": sum(
            _integer(batch["implicit_pair_count"], "batch.implicit_pair_count")
            for batch in batches
        ),
        "materialized_pair_count": 0,
        "nonclifford_source_layers": list(nonclifford_layers),
        "physical_qubits": None,
        "ppm_count": ppm_count,
        "proof_scope": PROOF_SCOPE,
        "records_checked": (
            len(trace.gates) + len(trace.dependencies) + len(toffolis) + ppm_count
        ),
        "runtime_seconds": None,
        "schema": CERTIFICATE_SCHEMA,
        "schema_version": 1,
        "source_dependency_count": len(trace.dependencies),
        "source_gate_count": len(trace.gates),
        "source_trace_id": trace.trace_id,
        "surgery_rounds": None,
        "theoretical_global_pair_count": ppm_count * (ppm_count - 1) // 2,
        "variant": variant,
        "weighted_causal_lower_bound": lower_bound,
        "width": trace.width,
    }


def replay_direct_ccz_ppm_compatibility(
    certificates_data: object,
    exact_equivalences_data: object,
    *,
    expected_widths: tuple[int, ...],
    expected_exact_widths: tuple[int, ...],
) -> DirectCczPpmCompatibilityReplaySummary:
    """Rebuild every certificate and validate exact-anchor bridge records."""

    if (
        not expected_widths
        or tuple(sorted(set(expected_widths))) != expected_widths
        or tuple(sorted(set(expected_exact_widths))) != expected_exact_widths
        or not set(expected_exact_widths) <= set(expected_widths)
    ):
        raise DirectCczPpmCompatibilityReplayError(
            "expected widths must be sorted, unique, and nested"
        )
    certificate_items = _sequence(certificates_data, "$.certificates")
    expected_order = tuple(
        (variant, width)
        for width in expected_widths
        for variant in ("oop", "ip")
    )
    observed_order: list[tuple[str, int]] = []
    certificate_by_key: dict[tuple[str, int], Mapping[str, object]] = {}
    certificate_match = True
    for index, raw_item in enumerate(certificate_items):
        path = f"$.certificates[{index}]"
        item = _mapping(raw_item, path)
        variant = _string(_required(item, "variant", path), f"{path}.variant")
        width = _integer(_required(item, "width", path), f"{path}.width")
        if variant not in {"oop", "ip"}:
            raise DirectCczPpmCompatibilityReplayError(
                f"{path}.variant is unsupported"
            )
        key = (variant, width)
        if key in certificate_by_key:
            raise DirectCczPpmCompatibilityReplayError(
                f"duplicate compatibility certificate: {key}"
            )
        trace = (
            build_oop_qcla_trace(width)
            if variant == "oop"
            else build_qcla_trace(width)
        )
        certificate_match &= dict(item) == _expected_certificate(trace, variant)
        certificate_by_key[key] = item
        observed_order.append(key)

    exact_items = _sequence(exact_equivalences_data, "$.exact_equivalences")
    expected_exact_order = tuple(
        (variant, width)
        for width in expected_exact_widths
        for variant in ("oop", "ip")
    )
    observed_exact_order: list[tuple[str, int]] = []
    exact_match = True
    for index, raw_item in enumerate(exact_items):
        path = f"$.exact_equivalences[{index}]"
        item = _mapping(raw_item, path)
        variant = _string(_required(item, "variant", path), f"{path}.variant")
        width = _integer(_required(item, "width", path), f"{path}.width")
        key = (variant, width)
        observed_exact_order.append(key)
        if key not in certificate_by_key:
            raise DirectCczPpmCompatibilityReplayError(
                f"exact equivalence has no compact certificate: {key}"
            )
        certificate = certificate_by_key[key]
        candidate_count = _integer(
            _required(certificate, "candidate_batch_level_count", "certificate"),
            "certificate.candidate_batch_level_count",
        )
        lower_bound = _integer(
            _required(certificate, "weighted_causal_lower_bound", "certificate"),
            "certificate.weighted_causal_lower_bound",
        )
        ppm_count = _integer(
            _required(certificate, "ppm_count", "certificate"),
            "certificate.ppm_count",
        )
        implicit_pairs = _integer(
            _required(
                certificate,
                "implicit_within_batch_pair_count",
                "certificate",
            ),
            "certificate.implicit_within_batch_pair_count",
        )
        exact_match &= (
            _string(_required(item, "schema", path), f"{path}.schema")
            == EXACT_EQUIVALENCE_SCHEMA
            and _integer(
                _required(item, "schema_version", path), f"{path}.schema_version"
            )
            == 1
            and _boolean(
                _required(item, "all_checks_passed", path),
                f"{path}.all_checks_passed",
            )
            and _boolean(
                _required(item, "batch_membership_digest_match", path),
                f"{path}.batch_membership_digest_match",
            )
            and _boolean(
                _required(item, "candidate_level_count_match", path),
                f"{path}.candidate_level_count_match",
            )
            and _boolean(
                _required(item, "causal_lower_bound_match", path),
                f"{path}.causal_lower_bound_match",
            )
            and _boolean(
                _required(
                    item,
                    "every_materialized_intra_batch_pair_compatible",
                    path,
                ),
                f"{path}.every_materialized_intra_batch_pair_compatible",
            )
            and _boolean(
                _required(item, "every_exact_profile_y_free", path),
                f"{path}.every_exact_profile_y_free",
            )
            and _string(
                _required(item, "evidence_status", path),
                f"{path}.evidence_status",
            )
            == "NUMERICAL"
            and _integer(
                _required(item, "certificate_batch_level_count", path),
                f"{path}.certificate_batch_level_count",
            )
            == candidate_count
            and _integer(
                _required(item, "exact_source_aligned_batch_level_count", path),
                f"{path}.exact_source_aligned_batch_level_count",
            )
            == candidate_count
            and _integer(
                _required(item, "exact_optimized_batch_level_count", path),
                f"{path}.exact_optimized_batch_level_count",
            )
            == candidate_count
            and _integer(
                _required(item, "exact_causal_lower_bound", path),
                f"{path}.exact_causal_lower_bound",
            )
            == lower_bound
            and _integer(
                _required(item, "global_materialized_pair_count", path),
                f"{path}.global_materialized_pair_count",
            )
            == ppm_count * (ppm_count - 1) // 2
            and _integer(
                _required(item, "materialized_intra_batch_pair_count", path),
                f"{path}.materialized_intra_batch_pair_count",
            )
            == implicit_pairs
        )

    checks = (
        ("canonical_certificate_order", tuple(observed_order) == expected_order),
        ("independent_linear_certificate_match", certificate_match),
        (
            "canonical_exact_equivalence_order",
            tuple(observed_exact_order) == expected_exact_order,
        ),
        ("exact_anchor_bridge_consistent", exact_match),
        (
            "all_large_width_pair_tables_absent",
            all(
                _integer(
                    _required(item, "materialized_pair_count", "certificate"),
                    "certificate.materialized_pair_count",
                )
                == 0
                for item in certificate_by_key.values()
            ),
        ),
        (
            "all_finite_outputs_null",
            all(
                _required(item, field, "certificate") is None
                for item in certificate_by_key.values()
                for field in (
                    "failure_probability",
                    "physical_qubits",
                    "runtime_seconds",
                    "surgery_rounds",
                )
            ),
        ),
    )
    return DirectCczPpmCompatibilityReplaySummary(
        widths=expected_widths,
        certificate_count=len(certificate_items),
        exact_equivalence_count=len(exact_items),
        checks=checks,
    )


def direct_ccz_ppm_compatibility_replay_to_data(
    summary: DirectCczPpmCompatibilityReplaySummary,
) -> dict[str, Any]:
    """Return a deterministic JSON-compatible replay summary."""

    return {
        "all_passed": summary.all_passed,
        "certificate_count": summary.certificate_count,
        "checks": [
            {"check": name, "passed": passed} for name, passed in summary.checks
        ],
        "exact_equivalence_count": summary.exact_equivalence_count,
        "method": (
            "independent source-trace reconstruction with no compiler or scheduler import"
        ),
        "widths": list(summary.widths),
    }
