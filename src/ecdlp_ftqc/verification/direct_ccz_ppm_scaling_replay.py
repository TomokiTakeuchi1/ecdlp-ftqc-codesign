"""Independent replay of serialized direct-CCZ QCLA scaling summaries.

This module deliberately imports neither the direct-CCZ compiler nor any
scheduler.  It rebuilds source traces and recomputes the compact structural
invariants directly from the source DAG.
"""

from __future__ import annotations

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

SCALING_SCHEMA = "ecdlp-ftqc/direct-ccz-qcla-scaling"
EXACT_ANCHOR_SCHEMA = "ecdlp-ftqc/direct-ccz-qcla-exact-anchor"
FINITE_SCHEMA = "ecdlp-ftqc/direct-ccz-qcla-finite-scaling-admission"


class DirectCczPpmScalingReplayError(ValueError):
    """Raised when a serialized scaling record is malformed."""


@dataclass(frozen=True, slots=True)
class DirectCczPpmScalingReplaySummary:
    """Independent replay result for one complete width sweep."""

    widths: tuple[int, ...]
    structural_point_count: int
    exact_anchor_count: int
    checks: tuple[tuple[str, bool], ...]

    @property
    def all_passed(self) -> bool:
        return all(passed for _, passed in self.checks)


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) for key in value
    ):
        raise DirectCczPpmScalingReplayError(
            f"{path} must be a string-keyed mapping"
        )
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DirectCczPpmScalingReplayError(f"{path} must be a sequence")
    return value


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DirectCczPpmScalingReplayError(f"{path} must be an integer")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczPpmScalingReplayError(
            f"{path} must be a nonempty string"
        )
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DirectCczPpmScalingReplayError(f"{path} must be Boolean")
    return value


def _required(item: Mapping[str, object], key: str, path: str) -> object:
    if key not in item:
        raise DirectCczPpmScalingReplayError(f"{path} is missing {key!r}")
    return item[key]


def _weighted_depth(trace: QclaTrace | OopQclaTrace) -> int:
    predecessors: dict[str, list[str]] = {}
    for dependency in trace.dependencies:
        predecessors.setdefault(dependency.successor, []).append(
            dependency.predecessor
        )
    gates = {gate.gate_id: gate for gate in trace.gates}
    depth: dict[str, int] = {}
    for gate_id in trace.topological_order():
        gate = gates[gate_id]
        weight = 2 if gate.kind is QclaGateKind.TOFFOLI else 0
        depth[gate_id] = weight + max(
            (depth[item] for item in predecessors.get(gate_id, ())),
            default=0,
        )
    return max(depth.values(), default=0)


def _expected_layer_data(
    trace: QclaTrace | OopQclaTrace,
) -> list[dict[str, Any]]:
    by_layer: dict[int, list[Any]] = {}
    for gate in trace.gates:
        if gate.kind is QclaGateKind.TOFFOLI:
            by_layer.setdefault(gate.algorithmic_layer, []).append(gate)
    return [
        {
            "ccz_state_count": len(gates),
            "resource_x_ppm_count": 3 * len(gates),
            "source_algorithmic_layer": layer,
            "source_stages": sorted({gate.stage.value for gate in gates}),
            "source_steps": sorted({gate.source_step for gate in gates}),
            "toffoli_count": len(gates),
            "total_ppm_count": 6 * len(gates),
            "zz_ppm_count": 3 * len(gates),
        }
        for layer, gates in sorted(by_layer.items())
    ]


def _expected_point(
    trace: QclaTrace | OopQclaTrace,
    variant: str,
) -> dict[str, object]:
    toffolis = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    cnot_count = sum(gate.kind is QclaGateKind.CNOT for gate in trace.gates)
    x_count = sum(gate.kind is QclaGateKind.X for gate in trace.gates)
    layer_data = _expected_layer_data(trace)
    if variant == "ip":
        if not isinstance(trace, QclaTrace):
            raise DirectCczPpmScalingReplayError("IP replay requires QclaTrace")
        source_storage_count_kind = "source_ancillas"
        source_storage_count = trace.source_ancilla_count
        cleanup_operation_count = sum(
            gate.source_step >= 7 for gate in trace.gates
        )
        cleanup_toffoli_count = sum(
            gate.source_step >= 7 and gate.kind is QclaGateKind.TOFFOLI
            for gate in trace.gates
        )
    elif variant == "oop":
        if not isinstance(trace, OopQclaTrace):
            raise DirectCczPpmScalingReplayError("OOP replay requires OopQclaTrace")
        source_storage_count_kind = "fully_resident_source_values"
        source_storage_count = trace.expected_fully_resident_source_values
        cleanup_operation_count = sum(
            gate.stage.value in {"input_restore", "prefix_uncompute"}
            for gate in trace.gates
        )
        cleanup_toffoli_count = sum(
            gate.stage.value in {"input_restore", "prefix_uncompute"}
            and gate.kind is QclaGateKind.TOFFOLI
            for gate in trace.gates
        )
    else:
        raise DirectCczPpmScalingReplayError(f"unknown variant: {variant}")
    ppm_count = 6 * len(toffolis)
    return {
        "candidate_compatibility_status": "OPEN",
        "causal_lower_bound_evidence_status": "PROVED",
        "cleanup_operation_count": cleanup_operation_count,
        "cleanup_toffoli_count": cleanup_toffoli_count,
        "conditional_frame_update_count": ppm_count,
        "consumed_ccz_state_count": len(toffolis),
        "coordinate": "ppm_level_not_time",
        "direct_ccz_event_count": len(toffolis),
        "event_trace_id": f"{trace.trace_id}:direct-ccz-events-v2",
        "layer_demand": layer_data,
        "nonclifford_source_layer_count": len(layer_data),
        "pair_table_materialized": False,
        "peak_source_layer_ppm_demand": max(
            (int(item["total_ppm_count"]) for item in layer_data), default=0
        ),
        "peak_source_toffoli_per_layer": max(
            (int(item["toffoli_count"]) for item in layer_data), default=0
        ),
        "ppm_count": ppm_count,
        "resource_logical_demand": 3 * len(toffolis),
        "schema": SCALING_SCHEMA,
        "schema_version": 1,
        "singleton_semantic_order_count": ppm_count,
        "source_cnot_count": cnot_count,
        "source_dependency_count": len(trace.dependencies),
        "source_gate_count": len(trace.gates),
        "source_layer_count": max(
            gate.algorithmic_layer for gate in trace.gates
        ),
        "source_storage_count": source_storage_count,
        "source_storage_count_kind": source_storage_count_kind,
        "source_toffoli_count": len(toffolis),
        "source_trace_id": trace.trace_id,
        "source_two_phase_envelope_status": "CHECK",
        "source_two_phase_injection_envelope_levels": 2 * len(layer_data),
        "source_x_count": x_count,
        "structural_evidence_status": "NUMERICAL",
        "theoretical_pair_count": ppm_count * (ppm_count - 1) // 2,
        "variant": variant,
        "weighted_causal_ppm_level_lower_bound": _weighted_depth(trace),
        "width": trace.width,
    }


def replay_direct_ccz_ppm_scaling(
    structural_points_data: object,
    exact_anchors_data: object,
    finite_admission_data: object,
    *,
    expected_widths: tuple[int, ...],
    expected_exact_widths: tuple[int, ...],
) -> DirectCczPpmScalingReplaySummary:
    """Rebuild and compare every structural point and admission boundary."""

    if (
        not expected_widths
        or tuple(sorted(set(expected_widths))) != expected_widths
        or tuple(sorted(set(expected_exact_widths))) != expected_exact_widths
        or not set(expected_exact_widths) <= set(expected_widths)
    ):
        raise DirectCczPpmScalingReplayError(
            "expected widths must be sorted, unique, and nested"
        )
    point_items = _sequence(structural_points_data, "$.structural_points")
    expected_order = tuple(
        (variant, width)
        for width in expected_widths
        for variant in ("oop", "ip")
    )
    observed_order: list[tuple[str, int]] = []
    point_by_key: dict[tuple[str, int], Mapping[str, object]] = {}
    structural_match = True
    for index, raw_item in enumerate(point_items):
        path = f"$.structural_points[{index}]"
        item = _mapping(raw_item, path)
        variant = _string(_required(item, "variant", path), f"{path}.variant")
        width = _integer(_required(item, "width", path), f"{path}.width")
        key = (variant, width)
        if key in point_by_key:
            raise DirectCczPpmScalingReplayError(f"duplicate scaling point: {key}")
        point_by_key[key] = item
        observed_order.append(key)
        trace = build_oop_qcla_trace(width) if variant == "oop" else build_qcla_trace(width)
        expected = _expected_point(trace, variant)
        structural_match &= dict(item) == expected

    anchors = _sequence(exact_anchors_data, "$.exact_anchors")
    expected_anchor_order = tuple(
        (variant, width)
        for width in expected_exact_widths
        for variant in ("oop", "ip")
    )
    observed_anchor_order: list[tuple[str, int]] = []
    anchor_match = True
    for index, raw_anchor in enumerate(anchors):
        path = f"$.exact_anchors[{index}]"
        anchor = _mapping(raw_anchor, path)
        variant = _string(
            _required(anchor, "variant", path), f"{path}.variant"
        )
        width = _integer(_required(anchor, "width", path), f"{path}.width")
        key = (variant, width)
        observed_anchor_order.append(key)
        if key not in point_by_key:
            raise DirectCczPpmScalingReplayError(
                f"exact anchor has no structural point: {key}"
            )
        point = point_by_key[key]
        causal = _integer(
            _required(point, "weighted_causal_ppm_level_lower_bound", "point"),
            "point.weighted_causal_ppm_level_lower_bound",
        )
        anchor_match &= (
            _string(_required(anchor, "schema", path), f"{path}.schema")
            == EXACT_ANCHOR_SCHEMA
            and _integer(
                _required(anchor, "schema_version", path),
                f"{path}.schema_version",
            )
            == 1
            and _integer(
                _required(anchor, "ppm_count", path), f"{path}.ppm_count"
            )
            == _integer(_required(point, "ppm_count", "point"), "point.ppm_count")
            and _integer(
                _required(anchor, "materialized_pair_count", path),
                f"{path}.materialized_pair_count",
            )
            == _integer(
                _required(point, "theoretical_pair_count", "point"),
                "point.theoretical_pair_count",
            )
            and _integer(
                _required(anchor, "candidate_batch_level_count", path),
                f"{path}.candidate_batch_level_count",
            )
            == causal
            and _integer(
                _required(anchor, "causal_critical_path_lower_bound", path),
                f"{path}.causal_critical_path_lower_bound",
            )
            == causal
            and _integer(
                _required(anchor, "combined_batch_level_lower_bound", path),
                f"{path}.combined_batch_level_lower_bound",
            )
            == causal
            and _integer(
                _required(anchor, "fallback_operation_count", path),
                f"{path}.fallback_operation_count",
            )
            == 0
            and _integer(
                _required(anchor, "possible_y_ppm_count", path),
                f"{path}.possible_y_ppm_count",
            )
            == 0
            and _string(
                _required(anchor, "candidate_optimality_evidence_status", path),
                f"{path}.candidate_optimality_evidence_status",
            )
            == "PROVED"
            and not _boolean(
                _required(anchor, "finite_native_schedule_emitted", path),
                f"{path}.finite_native_schedule_emitted",
            )
        )

    finite = _mapping(finite_admission_data, "$.finite_admission")
    null_fields = (
        "ccz_buffer_trajectory",
        "decoder_service",
        "failure_probability",
        "memory_traffic",
        "native_schedule",
        "physical_qubits",
        "reaction_latency_seconds",
        "routing_cost",
        "runtime_seconds",
        "surgery_rounds",
    )
    finite_match = (
        _string(_required(finite, "schema", "$.finite_admission"), "$.finite_admission.schema")
        == FINITE_SCHEMA
        and _boolean(
            _required(finite, "event_lowering_admitted", "$.finite_admission"),
            "$.finite_admission.event_lowering_admitted",
        )
        and not _boolean(
            _required(finite, "high_rate_capability_admitted", "$.finite_admission"),
            "$.finite_admission.high_rate_capability_admitted",
        )
        and not _boolean(
            _required(finite, "finite_backend_admitted", "$.finite_admission"),
            "$.finite_admission.finite_backend_admitted",
        )
        and not _boolean(
            _required(finite, "scaling_native_mapper_admitted", "$.finite_admission"),
            "$.finite_admission.scaling_native_mapper_admitted",
        )
        and _string(
            _required(finite, "evidence_status", "$.finite_admission"),
            "$.finite_admission.evidence_status",
        )
        == "OPEN"
        and bool(
            _sequence(
                _required(finite, "capability_missing_fields", "$.finite_admission"),
                "$.finite_admission.capability_missing_fields",
            )
        )
        and bool(
            _sequence(
                _required(finite, "backend_missing_fields", "$.finite_admission"),
                "$.finite_admission.backend_missing_fields",
            )
        )
        and bool(
            _sequence(
                _required(finite, "native_mapper_missing_fields", "$.finite_admission"),
                "$.finite_admission.native_mapper_missing_fields",
            )
        )
        and all(_required(finite, field, "$.finite_admission") is None for field in null_fields)
    )

    checks = (
        ("canonical_structural_point_order", tuple(observed_order) == expected_order),
        ("independent_source_dag_structural_match", structural_match),
        (
            "canonical_exact_anchor_order",
            tuple(observed_anchor_order) == expected_anchor_order,
        ),
        ("exact_anchor_matches_structural_invariants", anchor_match),
        ("finite_outputs_fail_closed", finite_match),
    )
    return DirectCczPpmScalingReplaySummary(
        widths=expected_widths,
        structural_point_count=len(point_items),
        exact_anchor_count=len(anchors),
        checks=checks,
    )


def direct_ccz_ppm_scaling_replay_to_data(
    summary: DirectCczPpmScalingReplaySummary,
) -> dict[str, Any]:
    """Serialize an independent replay summary."""

    return {
        "all_passed": summary.all_passed,
        "checks": [
            {"check": name, "passed": passed} for name, passed in summary.checks
        ],
        "exact_anchor_count": summary.exact_anchor_count,
        "method": (
            "independent source-trace rebuild; no compiler or scheduler import"
        ),
        "structural_point_count": summary.structural_point_count,
        "widths": list(summary.widths),
    }
