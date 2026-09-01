"""Build and render a deterministic audit atlas for direct-CCZ PPM batching.

The renderer consumes only serialized, already-reviewed Phase-A and Phase-B
artifacts.  It does not schedule operations.  Candidate batch levels are
unitless logical groupings and are deliberately labelled as non-temporal in
every generated document.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


class DirectCczPpmAtlasError(ValueError):
    """Raised when atlas inputs are inconsistent or incomplete."""


_BATCH_COLORS = (
    "#1D4ED8",
    "#6D28D9",
    "#BE185D",
    "#C2410C",
    "#A16207",
    "#15803D",
    "#0F766E",
    "#0E7490",
    "#4338CA",
    "#7E22CE",
    "#BE123C",
    "#4D7C0F",
)
_BATCH_UNIT = "candidate_batch_level_not_time"
_NON_TEMPORAL_NOTICE = (
    "AUDIT COORDINATE ONLY — candidate batch levels are not time, surgery rounds, "
    "or native simultaneous execution."
)


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DirectCczPpmAtlasError(f"{path} must be a mapping")
    return value


def _sequence(value: object, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise DirectCczPpmAtlasError(f"{path} must be a sequence")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczPpmAtlasError(f"{path} must be a non-empty string")
    return value


def _integer(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DirectCczPpmAtlasError(f"{path} must be an integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DirectCczPpmAtlasError(f"{path} must be a boolean")
    return value


def _strings(value: object, path: str) -> tuple[str, ...]:
    return tuple(_string(item, f"{path}[]") for item in _sequence(value, path))


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _short_identifier(value: str) -> str:
    if value.startswith("direct-ccz:"):
        fields = value.split(":")
        if len(fields) >= 3:
            event = fields[1].lstrip("0") or "0"
            suffix = ":".join(fields[2:])
            return f"e{event}:{suffix}"
    if value.startswith("qcla-oop:"):
        return "g" + (value.rsplit(":", 1)[-1].lstrip("0") or "0")
    return value


def _short_signature(value: str) -> str:
    return f"{value[:8]}…{value[-6:]}"


def _short_condition(expression: str, event_id: str) -> str:
    prefix = f"{event_id}:outcome:"
    return (
        expression.replace(prefix, "m_")
        .replace(" XOR ", " xor ")
        .replace(" AND ", " and ")
        .replace("(", "")
        .replace(")", "")
    )


def _observable_label(ppm: Mapping[str, Any]) -> str:
    observable = _mapping(ppm.get("presented_observable"), "ppm.presented_observable")
    labels: list[str] = []
    for axis, key in (("X", "x_components"), ("Z", "z_components")):
        for raw_component in _sequence(observable.get(key), f"presented_observable.{key}"):
            component = _mapping(raw_component, f"presented_observable.{key}[]")
            logical = _string(component.get("logical_value"), "component.logical_value")
            coefficient = _mapping(component.get("coefficient"), "component.coefficient")
            expression = _string(coefficient.get("expression"), "coefficient.expression")
            labels.append(
                f"{axis}({logical})" if expression == "1" else f"[{expression}]{axis}({logical})"
            )
    sign = _mapping(observable.get("sign"), "presented_observable.sign")
    sign_expression = _string(sign.get("expression"), "presented_observable.sign.expression")
    prefix = "" if sign_expression == "0" else f"(-1)^({sign_expression}) "
    return prefix + " ".join(labels)


def _gate_label(frame_term: Mapping[str, Any]) -> str:
    labels: list[str] = []
    for raw_gate in _sequence(frame_term.get("circuit"), "frame_term.circuit"):
        gate = _mapping(raw_gate, "frame_term.circuit[]")
        kind = _string(gate.get("kind"), "frame_gate.kind")
        support = _strings(gate.get("support"), "frame_gate.support")
        labels.append(f"{kind}({','.join(support)})")
    return " · ".join(labels)


def _relation_reasons(relation: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    if _string(relation.get("causal_order"), "pair.causal_order") != "none":
        reasons.append("causal_dependency")
    if _boolean(relation.get("reaction_dependent"), "pair.reaction_dependent"):
        reasons.append("reaction_dependency")
    if not _boolean(relation.get("universally_commuting"), "pair.universally_commuting"):
        reasons.append("symplectic_noncommutation")
    if not _boolean(
        relation.get("universally_axis_consistent"),
        "pair.universally_axis_consistent",
    ):
        reasons.append("logical_axis_conflict")
    if _boolean(relation.get("resource_reuse_conflict"), "pair.resource_reuse_conflict"):
        reasons.append("resource_reuse")
    return tuple(reasons)


def _batch_maps(
    general: Mapping[str, Any],
) -> tuple[dict[str, int], dict[int, Mapping[str, Any]], tuple[int, ...]]:
    schedule = _mapping(general.get("optimized_schedule"), "general.optimized_schedule")
    if _string(schedule.get("unit"), "optimized_schedule.unit") != _BATCH_UNIT:
        raise DirectCczPpmAtlasError("optimized schedule must use the non-temporal batch unit")
    if _boolean(
        schedule.get("complete_native_schedule"),
        "optimized_schedule.complete_native_schedule",
    ):
        raise DirectCczPpmAtlasError("atlas refuses a claimed native schedule")

    operation_to_level: dict[str, int] = {}
    batches: dict[int, Mapping[str, Any]] = {}
    batch_sizes: list[int] = []
    for raw_batch in _sequence(schedule.get("batches"), "optimized_schedule.batches"):
        batch = _mapping(raw_batch, "optimized_schedule.batches[]")
        level = _integer(batch.get("batch_level"), "batch.batch_level")
        if level in batches:
            raise DirectCczPpmAtlasError(f"duplicate batch level {level}")
        batches[level] = batch
        operation_ids = _strings(batch.get("operation_ids"), "batch.operation_ids")
        batch_sizes.append(len(operation_ids))
        for operation_id in operation_ids:
            if operation_id in operation_to_level:
                raise DirectCczPpmAtlasError(f"duplicate scheduled PPM {operation_id}")
            operation_to_level[operation_id] = level
    expected_levels = tuple(range(1, len(batches) + 1))
    if tuple(sorted(batches)) != expected_levels:
        raise DirectCczPpmAtlasError("batch levels must be contiguous and one-based")
    return operation_to_level, batches, tuple(batch_sizes)


def _separation_certificates(
    general: Mapping[str, Any],
    operation_to_level: Mapping[str, int],
) -> dict[str, list[dict[str, Any]]]:
    by_later_operation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw_relation in _sequence(general.get("pair_relations"), "general.pair_relations"):
        relation = _mapping(raw_relation, "general.pair_relations[]")
        left = _string(relation.get("left_operation_id"), "pair.left_operation_id")
        right = _string(relation.get("right_operation_id"), "pair.right_operation_id")
        if left not in operation_to_level or right not in operation_to_level:
            raise DirectCczPpmAtlasError("pair relation references an unscheduled PPM")
        left_level = operation_to_level[left]
        right_level = operation_to_level[right]
        if left_level == right_level:
            if not _boolean(
                relation.get("general_high_rate_compatible"),
                "pair.general_high_rate_compatible",
            ):
                raise DirectCczPpmAtlasError("incompatible PPM pair appears in one batch")
            continue
        earlier, later = (left, right) if left_level < right_level else (right, left)
        reasons = _relation_reasons(relation)
        if not reasons:
            reasons = ("deterministic_frontier_partition",)
        by_later_operation[later].append(
            {
                "earlier_batch_level": operation_to_level[earlier],
                "earlier_operation_id": earlier,
                "reasons": list(reasons),
            }
        )
    for certificates in by_later_operation.values():
        certificates.sort(
            key=lambda item: (
                _integer(item["earlier_batch_level"], "certificate.earlier_batch_level"),
                _string(item["earlier_operation_id"], "certificate.earlier_operation_id"),
            )
        )
    return by_later_operation


def build_direct_ccz_ppm_atlas(
    trace_data: Mapping[str, Any],
    general_data: Mapping[str, Any],
    finite_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the canonical atlas data model from reviewed serialized artifacts."""

    trace_id = _string(trace_data.get("trace_id"), "trace.trace_id")
    if _string(general_data.get("trace_id"), "general.trace_id") != trace_id:
        raise DirectCczPpmAtlasError("Phase-A and Phase-B trace identities disagree")
    if _string(finite_data.get("trace_id"), "finite.trace_id") != trace_id:
        raise DirectCczPpmAtlasError("finite-admission trace identity disagrees")
    if _boolean(trace_data.get("complete_native_schedule"), "trace.complete_native_schedule"):
        raise DirectCczPpmAtlasError("atlas refuses a trace claiming a native schedule")

    operation_to_level, batches, batch_sizes = _batch_maps(general_data)
    profiles = {
        _string(profile.get("operation_id"), "profile.operation_id"): profile
        for profile in (
            _mapping(raw_profile, "general.observable_profiles[]")
            for raw_profile in _sequence(
                general_data.get("observable_profiles"),
                "general.observable_profiles",
            )
        )
    }
    ppms = {
        _string(ppm.get("operation_id"), "ppm.operation_id"): ppm
        for ppm in (
            _mapping(raw_ppm, "trace.ppms[]")
            for raw_ppm in _sequence(trace_data.get("ppms"), "trace.ppms")
        )
    }
    if set(ppms) != set(operation_to_level) or set(ppms) != set(profiles):
        raise DirectCczPpmAtlasError(
            "trace, profiles, and optimized schedule must cover the same PPMs"
        )

    source_operations = tuple(
        _mapping(item, "trace.source_operations[]")
        for item in _sequence(trace_data.get("source_operations"), "trace.source_operations")
    )
    source_by_id = {
        _string(operation.get("source_gate_id"), "source_operation.source_gate_id"): operation
        for operation in source_operations
    }
    if len(source_by_id) != len(source_operations):
        raise DirectCczPpmAtlasError("source gate IDs must be unique")

    injections = {
        _string(injection.get("source_gate_id"), "injection.source_gate_id"): injection
        for injection in (
            _mapping(item, "trace.injections[]")
            for item in _sequence(trace_data.get("injections"), "trace.injections")
        )
    }
    updates_by_source: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for raw_update in _sequence(trace_data.get("correction_updates"), "trace.correction_updates"):
        update = _mapping(raw_update, "trace.correction_updates[]")
        source_id = _string(update.get("source_gate_id"), "correction_update.source_gate_id")
        updates_by_source[source_id].append(update)
    for updates in updates_by_source.values():
        updates.sort(key=lambda update: _string(update.get("update_id"), "update.update_id"))

    dependencies = tuple(
        _mapping(item, "trace.source_dependencies[]")
        for item in _sequence(trace_data.get("source_dependencies"), "trace.source_dependencies")
    )
    dependencies_by_successor: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for dependency in dependencies:
        successor = _string(
            dependency.get("successor_source_gate_id"),
            "source_dependency.successor_source_gate_id",
        )
        dependencies_by_successor[successor].append(dependency)

    certificates = _separation_certificates(general_data, operation_to_level)
    macro_frames = tuple(
        _mapping(item, "trace.macro_layer_frames[]")
        for item in _sequence(trace_data.get("macro_layer_frames"), "trace.macro_layer_frames")
    )
    layers = tuple(
        sorted(
            _integer(frame.get("source_algorithmic_layer"), "macro_frame.layer")
            for frame in macro_frames
        )
    )
    if layers != tuple(range(1, len(layers) + 1)):
        raise DirectCczPpmAtlasError("macro layers must be contiguous and one-based")
    frames_by_layer = {
        _integer(frame.get("source_algorithmic_layer"), "macro_frame.layer"): frame
        for frame in macro_frames
    }

    atlas_panels: list[dict[str, Any]] = []
    all_update_ids: set[str] = set()
    for layer in layers:
        frame = frames_by_layer[layer]
        raw_frame_in = _mapping(frame.get("frame_in"), "macro_frame.frame_in")
        raw_frame_out = _mapping(frame.get("frame_out"), "macro_frame.frame_out")
        panel_source_operations: list[dict[str, Any]] = []
        panel_ppm_ids: list[str] = []
        panel_update_ids: list[str] = []
        panel_reason_counts: Counter[str] = Counter()

        layer_operations = sorted(
            (
                operation
                for operation in source_operations
                if _integer(
                    operation.get("source_algorithmic_layer"),
                    "source_operation.source_algorithmic_layer",
                )
                == layer
            ),
            key=lambda operation: _string(
                operation.get("source_gate_id"),
                "source_operation.source_gate_id",
            ),
        )
        for operation in layer_operations:
            source_id = _string(operation.get("source_gate_id"), "source_operation.source_gate_id")
            source_kind = _string(operation.get("source_kind"), "source_operation.source_kind")
            injection = injections.get(source_id)
            ppm_rows: list[dict[str, Any]] = []
            if injection is not None:
                event_id = _string(injection.get("event_id"), "injection.event_id")
                for ppm_id in _strings(
                    injection.get("ppm_operation_ids"), "injection.ppm_operation_ids"
                ):
                    ppm = ppms[ppm_id]
                    profile = profiles[ppm_id]
                    operation_certificates = certificates.get(ppm_id, [])
                    for certificate in operation_certificates:
                        panel_reason_counts.update(
                            _strings(certificate.get("reasons"), "certificate.reasons")
                        )
                    ppm_rows.append(
                        {
                            "batch_level": operation_to_level[ppm_id],
                            "candidate_unit": _BATCH_UNIT,
                            "maximum_weight": _integer(
                                profile.get("maximum_weight"),
                                "profile.maximum_weight",
                            ),
                            "minimum_weight": _integer(
                                profile.get("minimum_weight"),
                                "profile.minimum_weight",
                            ),
                            "operation_id": ppm_id,
                            "outcome_token": _string(
                                ppm.get("outcome_token"),
                                "ppm.outcome_token",
                            ),
                            "presented_observable": _observable_label(ppm),
                            "possible_logical_support": list(
                                _strings(
                                    profile.get("possible_logical_support"),
                                    "profile.possible_logical_support",
                                )
                            ),
                            "separation_certificates_from_earlier_levels": (operation_certificates),
                            "short_label": _short_identifier(ppm_id),
                            "variable_count": len(
                                _strings(profile.get("variables"), "profile.variables")
                            ),
                        }
                    )
                    panel_ppm_ids.append(ppm_id)
            correction_rows: list[dict[str, Any]] = []
            for update in updates_by_source.get(source_id, []):
                update_id = _string(update.get("update_id"), "update.update_id")
                if update_id in all_update_ids:
                    raise DirectCczPpmAtlasError(f"duplicate correction update {update_id}")
                all_update_ids.add(update_id)
                frame_term = _mapping(update.get("frame_term"), "update.frame_term")
                condition = _mapping(frame_term.get("condition"), "frame_term.condition")
                event_id = _string(frame_term.get("origin_event_id"), "frame_term.origin_event_id")
                correction_rows.append(
                    {
                        "condition": _short_condition(
                            _string(condition.get("expression"), "condition.expression"),
                            event_id,
                        ),
                        "frame_gate": _gate_label(frame_term),
                        "outcome_dependencies": list(
                            _strings(
                                update.get("outcome_dependencies"),
                                "update.outcome_dependencies",
                            )
                        ),
                        "resulting_frame_signature": _string(
                            update.get("resulting_frame_signature"),
                            "update.resulting_frame_signature",
                        ),
                        "update_id": update_id,
                    }
                )
                panel_update_ids.append(update_id)

            source_dependencies = [
                {
                    "dependency_id": (
                        f"{_string(dep.get('predecessor_source_gate_id'), 'dependency.predecessor')}"
                        f"->{_string(dep.get('successor_source_gate_id'), 'dependency.successor')}"
                    ),
                    "logical_values": list(
                        _strings(dep.get("logical_values"), "dependency.logical_values")
                    ),
                    "predecessor_source_gate_id": _string(
                        dep.get("predecessor_source_gate_id"),
                        "dependency.predecessor_source_gate_id",
                    ),
                    "reason": _string(dep.get("reason"), "dependency.reason"),
                    "successor_source_gate_id": source_id,
                }
                for dep in sorted(
                    dependencies_by_successor.get(source_id, []),
                    key=lambda item: _string(
                        item.get("predecessor_source_gate_id"),
                        "dependency.predecessor_source_gate_id",
                    ),
                )
            ]
            panel_source_operations.append(
                {
                    "correction_updates": correction_rows,
                    "frame_in_signature": _string(
                        operation.get("frame_in_signature"),
                        "source_operation.frame_in_signature",
                    ),
                    "frame_out_signature": _string(
                        operation.get("frame_out_signature"),
                        "source_operation.frame_out_signature",
                    ),
                    "injection_event_id": (
                        None
                        if injection is None
                        else _string(injection.get("event_id"), "injection.event_id")
                    ),
                    "logical_support": list(
                        _strings(
                            operation.get("logical_support"), "source_operation.logical_support"
                        )
                    ),
                    "lowering_kind": _string(
                        operation.get("lowering_kind"),
                        "source_operation.lowering_kind",
                    ),
                    "ppm_measurements": ppm_rows,
                    "source_dependencies": source_dependencies,
                    "source_gate_id": source_id,
                    "source_kind": source_kind,
                    "source_stage": _string(
                        operation.get("source_stage"),
                        "source_operation.source_stage",
                    ),
                }
            )

        panel_batches: list[dict[str, Any]] = []
        panel_ppm_set = set(panel_ppm_ids)
        for batch_level, batch in sorted(batches.items()):
            operation_ids = tuple(
                operation_id
                for operation_id in _strings(batch.get("operation_ids"), "batch.operation_ids")
                if operation_id in panel_ppm_set
            )
            if not operation_ids:
                continue
            panel_batches.append(
                {
                    "batch_level": batch_level,
                    "candidate_unit": _BATCH_UNIT,
                    "maximum_ppm_weight": _integer(
                        batch.get("maximum_ppm_weight"),
                        "batch.maximum_ppm_weight",
                    ),
                    "operation_ids": list(operation_ids),
                    "ppm_count_in_panel": len(operation_ids),
                    "source_algorithmic_layers": list(
                        _sequence(
                            batch.get("source_algorithmic_layers"),
                            "batch.source_algorithmic_layers",
                        )
                    ),
                }
            )

        atlas_panels.append(
            {
                "batch_groups": panel_batches,
                "correction_update_ids": panel_update_ids,
                "frame_in_signature": _string(
                    raw_frame_in.get("signature"),
                    "macro_frame.frame_in.signature",
                ),
                "frame_in_term_count": len(
                    _sequence(raw_frame_in.get("terms"), "macro_frame.frame_in.terms")
                ),
                "frame_out_signature": _string(
                    raw_frame_out.get("signature"),
                    "macro_frame.frame_out.signature",
                ),
                "frame_out_term_count": len(
                    _sequence(raw_frame_out.get("terms"), "macro_frame.frame_out.terms")
                ),
                "panel_id": f"macro-layer-{layer:02d}",
                "ppm_operation_ids": panel_ppm_ids,
                "separation_reason_counts": dict(sorted(panel_reason_counts.items())),
                "source_algorithmic_layer": layer,
                "source_operations": panel_source_operations,
            }
        )

    finite_admitted = _boolean(
        finite_data.get("finite_backend_admitted"),
        "finite.finite_backend_admitted",
    )
    native_emitted = _boolean(
        finite_data.get("native_schedule_emitted"),
        "finite.native_schedule_emitted",
    )
    forbidden_outputs = {
        "failure_probability": finite_data.get("failure_probability"),
        "physical_qubits": finite_data.get("physical_qubits"),
        "runtime_seconds": finite_data.get("runtime_seconds"),
        "schedule": finite_data.get("schedule"),
    }
    if (
        finite_admitted
        or native_emitted
        or any(value is not None for value in forbidden_outputs.values())
    ):
        raise DirectCczPpmAtlasError("finite backend must remain rejected with null outputs")

    kind_counts = Counter(
        _string(operation.get("source_kind"), "source_operation.source_kind")
        for operation in source_operations
    )
    schedule = _mapping(general_data.get("optimized_schedule"), "general.optimized_schedule")
    atlas = {
        "backend_status": {
            "backend_incompatible_fields": list(
                _strings(
                    finite_data.get("backend_incompatible_fields"),
                    "finite.backend_incompatible_fields",
                )
            ),
            "backend_missing_fields": list(
                _strings(
                    finite_data.get("backend_missing_fields"),
                    "finite.backend_missing_fields",
                )
            ),
            "capability_missing_fields": list(
                _strings(
                    finite_data.get("capability_missing_fields"),
                    "finite.capability_missing_fields",
                )
            ),
            "finite_backend_admitted": False,
            "general_high_rate_candidate": True,
            "native_mapper_missing_fields": list(
                _strings(
                    finite_data.get("native_mapper_missing_fields"),
                    "finite.native_mapper_missing_fields",
                )
            ),
            "native_schedule_emitted": False,
            "null_finite_outputs": forbidden_outputs,
            "verdict": _string(finite_data.get("verdict"), "finite.verdict"),
        },
        "batch_legend": [
            {
                "batch_level": level,
                "color": _BATCH_COLORS[(level - 1) % len(_BATCH_COLORS)],
                "ppm_count": batch_sizes[level - 1],
                "unit": _BATCH_UNIT,
            }
            for level in range(1, len(batch_sizes) + 1)
        ],
        "evidence_boundary": {
            "atlas": "NUMERICAL deterministic projection of reviewed serialized artifacts",
            "candidate_optimality": _string(
                schedule.get("optimality_evidence_status"),
                "optimized_schedule.optimality_evidence_status",
            ),
            "finite_backend": "OPEN and rejected",
            "non_temporal_notice": _NON_TEMPORAL_NOTICE,
        },
        "input_fingerprints": {
            "finite_admission_sha256": _canonical_sha256(finite_data),
            "general_candidate_sha256": _canonical_sha256(general_data),
            "symbolic_trace_sha256": _canonical_sha256(trace_data),
        },
        "overview": {
            "batch_sizes": list(batch_sizes),
            "candidate_batch_level_count": len(batch_sizes),
            "correction_update_count": len(all_update_ids),
            "injection_count": len(injections),
            "macro_layer_count": len(layers),
            "maximum_ppm_weight": _integer(
                schedule.get("maximum_ppm_weight"),
                "optimized_schedule.maximum_ppm_weight",
            ),
            "peak_live_logical_requirement": _integer(
                schedule.get("peak_live_logical_requirement"),
                "optimized_schedule.peak_live_logical_requirement",
            ),
            "peak_resource_state_count": _integer(
                schedule.get("peak_resource_state_count"),
                "optimized_schedule.peak_resource_state_count",
            ),
            "ppm_count": len(ppms),
            "source_kind_counts": dict(sorted(kind_counts.items())),
            "source_operation_count": len(source_operations),
        },
        "panels": atlas_panels,
        "schema": "ecdlp-ftqc/direct-ccz-ppm-atlas",
        "schema_version": 1,
        "task_id": "T-20260901-008",
        "trace_id": trace_id,
        "units": {
            "batch": _BATCH_UNIT,
            "source_layer": "source_algorithmic_layer_not_time",
        },
    }
    return atlas


def dumps_direct_ccz_ppm_atlas(atlas: Mapping[str, Any]) -> str:
    """Serialize atlas data deterministically."""

    return json.dumps(atlas, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _svg_text(
    x: int,
    y: int,
    value: object,
    *,
    css_class: str = "body",
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x}" y="{y}" class="{css_class}" text-anchor="{anchor}">'
        f"{html.escape(str(value))}</text>"
    )


def _svg_rect(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    css_class: str,
    fill: str | None = None,
    rx: int = 12,
) -> str:
    fill_attribute = "" if fill is None else f' style="fill:{fill}"'
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{rx}" class="{css_class}"{fill_attribute}/>'
    )


def _svg_document_start(
    *,
    width: int,
    height: int,
    panel_id: str,
    layer: int | None,
    fingerprint: str,
) -> list[str]:
    layer_attribute = "" if layer is None else f' data-layer="{layer}"'
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'data-schema="ecdlp-ftqc/direct-ccz-ppm-atlas-svg" '
            f'data-panel-id="{html.escape(panel_id, quote=True)}"{layer_attribute} '
            f'data-batch-unit="{_BATCH_UNIT}" '
            f'data-atlas-fingerprint="{fingerprint}">'
        ),
        f"<title>{html.escape(panel_id)} — direct-CCZ PPM audit atlas</title>",
        f"<desc>{html.escape(_NON_TEMPORAL_NOTICE)}</desc>",
        "<defs>",
        (
            '<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" '
            'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#38BDF8"/></marker>'
        ),
        "<style>",
        "text{font-family:Inter,Segoe UI,Arial,sans-serif}",
        ".bg{fill:#07111F}.panel{fill:#0F1F33;stroke:#29425F;stroke-width:1.5}",
        ".panel2{fill:#102A3D;stroke:#31546F;stroke-width:1.2}",
        ".title{fill:#F8FAFC;font-size:28px;font-weight:700}",
        ".subtitle{fill:#93C5FD;font-size:15px;font-weight:600;letter-spacing:.6px}",
        ".heading{fill:#E2E8F0;font-size:17px;font-weight:700}",
        ".body{fill:#CBD5E1;font-size:13px}.small{fill:#94A3B8;font-size:11px}",
        ".mono{fill:#BAE6FD;font-size:11px;font-family:Consolas,monospace}",
        ".notice{fill:#FDE68A;font-size:12px;font-weight:700}",
        ".good{fill:#86EFAC;font-size:14px;font-weight:700}",
        ".bad{fill:#FDA4AF;font-size:14px;font-weight:700}",
        ".arrow{stroke:#38BDF8;stroke-width:1.5;fill:none;marker-end:url(#arrow)}",
        "</style>",
        "</defs>",
        f'<rect width="{width}" height="{height}" class="bg"/>',
    ]


def _render_overview(atlas: Mapping[str, Any], fingerprint: str) -> str:
    width, height = 1600, 1180
    output = _svg_document_start(
        width=width,
        height=height,
        panel_id="overview",
        layer=None,
        fingerprint=fingerprint,
    )
    overview = _mapping(atlas.get("overview"), "atlas.overview")
    backend = _mapping(atlas.get("backend_status"), "atlas.backend_status")
    panels = tuple(
        _mapping(item, "atlas.panels[]") for item in _sequence(atlas.get("panels"), "atlas.panels")
    )
    output.extend(
        [
            _svg_text(55, 62, "Direct-CCZ PPM audit atlas", css_class="title"),
            _svg_text(
                55,
                90,
                "Clean OOP-QCLA n=5 • reviewed symbolic trace → reviewed candidate batches",
                css_class="subtitle",
            ),
            _svg_text(55, 116, _NON_TEMPORAL_NOTICE, css_class="notice"),
        ]
    )

    metrics = (
        ("SOURCE OPS", overview.get("source_operation_count"), "10 CCX + 13 CX"),
        ("PPMs", overview.get("ppm_count"), "60 outcome tokens"),
        ("CANDIDATE LEVELS", overview.get("candidate_batch_level_count"), _BATCH_UNIT),
        ("PEAK SEMANTIC LIVE", overview.get("peak_live_logical_requirement"), "4 CCZ states"),
    )
    for index, (label, value, detail) in enumerate(metrics):
        x = 55 + index * 382
        output.append(_svg_rect(x, 145, 350, 118, css_class="panel"))
        output.append(_svg_text(x + 20, 174, label, css_class="small"))
        output.append(_svg_text(x + 20, 222, value, css_class="title"))
        output.append(_svg_text(x + 110, 220, detail, css_class="body"))

    output.append(_svg_text(55, 305, "Nine source macro-layers", css_class="heading"))
    for index, panel in enumerate(panels):
        row, column = divmod(index, 3)
        x = 55 + column * 505
        y = 330 + row * 150
        layer = _integer(panel.get("source_algorithmic_layer"), "panel.layer")
        source_ops = _sequence(panel.get("source_operations"), "panel.source_operations")
        ppm_ids = _sequence(panel.get("ppm_operation_ids"), "panel.ppm_operation_ids")
        frame_in_terms = _integer(panel.get("frame_in_term_count"), "panel.frame_in_term_count")
        frame_out_terms = _integer(
            panel.get("frame_out_term_count"),
            "panel.frame_out_term_count",
        )
        levels = [
            _integer(group.get("batch_level"), "batch_group.batch_level")
            for group in (
                _mapping(item, "panel.batch_groups[]")
                for item in _sequence(panel.get("batch_groups"), "panel.batch_groups")
            )
        ]
        output.append(
            f'<g data-overview-layer="{layer}" data-source-count="{len(source_ops)}" '
            f'data-ppm-count="{len(ppm_ids)}">'
        )
        output.append(_svg_rect(x, y, 470, 122, css_class="panel"))
        output.append(_svg_text(x + 18, y + 30, f"LAYER {layer:02d}", css_class="heading"))
        output.append(
            _svg_text(
                x + 18,
                y + 56,
                f"{len(source_ops)} source ops • {len(ppm_ids)} PPMs • batches "
                + (",".join(f"B{level:02d}" for level in levels) if levels else "none"),
                css_class="body",
            )
        )
        output.append(
            _svg_text(
                x + 18,
                y + 82,
                f"frame terms {frame_in_terms} → {frame_out_terms}",
                css_class="mono",
            )
        )
        output.append("</g>")

    batch_y = 805
    output.append(_svg_text(55, batch_y, "Candidate batching certificate", css_class="heading"))
    for index, raw_legend in enumerate(_sequence(atlas.get("batch_legend"), "atlas.batch_legend")):
        legend = _mapping(raw_legend, "atlas.batch_legend[]")
        row, column = divmod(index, 6)
        x = 55 + column * 248
        y = batch_y + 25 + row * 67
        level = _integer(legend.get("batch_level"), "legend.batch_level")
        color = _string(legend.get("color"), "legend.color")
        ppm_count = _integer(legend.get("ppm_count"), "legend.ppm_count")
        output.append(f'<g data-batch-level="{level}" data-ppm-count="{ppm_count}">')
        output.append(_svg_rect(x, y, 220, 48, css_class="panel2", fill=color, rx=8))
        output.append(
            _svg_text(x + 16, y + 30, f"B{level:02d}  {ppm_count} PPM", css_class="heading")
        )
        output.append("</g>")

    status_y = 985
    output.append(_svg_rect(55, status_y, 720, 125, css_class="panel"))
    output.append(_svg_text(75, status_y + 31, "GENERAL LOGICAL CANDIDATE", css_class="good"))
    output.append(
        _svg_text(
            75,
            status_y + 60,
            "12-level construction meets causal and conflict-clique lower bounds.",
            css_class="body",
        )
    )
    output.append(
        _svg_text(
            75, status_y + 86, "Scope: stated logical candidate model only.", css_class="small"
        )
    )
    output.append(_svg_rect(805, status_y, 740, 125, css_class="panel"))
    output.append(_svg_text(825, status_y + 31, "FINITE BACKEND REJECTED", css_class="bad"))
    output.append(
        _svg_text(
            825,
            status_y + 60,
            f"missing capability/backend/native fields: "
            f"{len(_sequence(backend.get('capability_missing_fields'), 'backend.capability_missing_fields'))}/"
            f"{len(_sequence(backend.get('backend_missing_fields'), 'backend.backend_missing_fields'))}/"
            f"{len(_sequence(backend.get('native_mapper_missing_fields'), 'backend.native_mapper_missing_fields'))}",
            css_class="body",
        )
    )
    output.append(
        _svg_text(
            825,
            status_y + 86,
            "schedule = runtime = physical qubits = failure probability = null",
            css_class="small",
        )
    )
    output.append("</svg>")
    return "\n".join(output) + "\n"


def _render_layer_panel(panel: Mapping[str, Any], fingerprint: str) -> str:
    source_operations = tuple(
        _mapping(item, "panel.source_operations[]")
        for item in _sequence(panel.get("source_operations"), "panel.source_operations")
    )
    operation_heights = [
        252
        if _string(operation.get("source_kind"), "source_operation.source_kind") == "toffoli"
        else 108
        for operation in source_operations
    ]
    height = max(900, 330 + sum(operation_heights) + 28 * len(source_operations))
    width = 1600
    layer = _integer(panel.get("source_algorithmic_layer"), "panel.source_algorithmic_layer")
    panel_id = _string(panel.get("panel_id"), "panel.panel_id")
    output = _svg_document_start(
        width=width,
        height=height,
        panel_id=panel_id,
        layer=layer,
        fingerprint=fingerprint,
    )
    output.extend(
        [
            _svg_text(50, 56, f"Macro-layer {layer:02d}", css_class="title"),
            _svg_text(
                50,
                85,
                "source operations • presented PPMs • outcome-to-frame updates • candidate membership",
                css_class="subtitle",
            ),
            _svg_text(50, 112, _NON_TEMPORAL_NOTICE, css_class="notice"),
        ]
    )
    frame_in = _string(panel.get("frame_in_signature"), "panel.frame_in_signature")
    frame_out = _string(panel.get("frame_out_signature"), "panel.frame_out_signature")
    output.append(
        f'<g data-frame-role="in" data-frame-signature="{html.escape(frame_in, quote=True)}">'
    )
    output.append(_svg_rect(50, 136, 1070, 62, css_class="panel2"))
    output.append(
        _svg_text(
            70,
            162,
            f"FRAME-IN  {_short_signature(frame_in)}",
            css_class="heading",
        )
    )
    output.append(
        _svg_text(
            70,
            184,
            f"{_integer(panel.get('frame_in_term_count'), 'panel.frame_in_term_count')} conditional terms",
            css_class="small",
        )
    )
    output.append("</g>")

    y = 226
    for operation, card_height in zip(source_operations, operation_heights, strict=True):
        source_id = _string(operation.get("source_gate_id"), "source_operation.source_gate_id")
        source_kind = _string(operation.get("source_kind"), "source_operation.source_kind")
        support = _strings(operation.get("logical_support"), "source_operation.logical_support")
        stage = _string(operation.get("source_stage"), "source_operation.source_stage")
        output.append(
            f'<g data-source-gate-id="{html.escape(source_id, quote=True)}" '
            f'data-source-kind="{html.escape(source_kind, quote=True)}">'
        )
        output.append(_svg_rect(50, y, 1070, card_height, css_class="panel"))
        output.append(
            _svg_text(
                72,
                y + 31,
                f"{_short_identifier(source_id)}  {source_kind.upper()}  [{', '.join(support)}]",
                css_class="heading",
            )
        )
        output.append(_svg_text(780, y + 31, stage, css_class="small"))
        dependencies = tuple(
            _mapping(item, "source_operation.source_dependencies[]")
            for item in _sequence(
                operation.get("source_dependencies"),
                "source_operation.source_dependencies",
            )
        )
        if dependencies:
            dependency_text = "; ".join(
                f"{_short_identifier(_string(dep.get('predecessor_source_gate_id'), 'dependency.predecessor'))}"
                f" via {','.join(_strings(dep.get('logical_values'), 'dependency.logical_values'))}"
                for dep in dependencies
            )
        else:
            dependency_text = "no source predecessor"
        output.append(
            _svg_text(72, y + 54, f"source dependency: {dependency_text}", css_class="small")
        )

        ppm_rows = tuple(
            _mapping(item, "source_operation.ppm_measurements[]")
            for item in _sequence(
                operation.get("ppm_measurements"),
                "source_operation.ppm_measurements",
            )
        )
        corrections = tuple(
            _mapping(item, "source_operation.correction_updates[]")
            for item in _sequence(
                operation.get("correction_updates"),
                "source_operation.correction_updates",
            )
        )
        if ppm_rows:
            for index, ppm in enumerate(ppm_rows):
                row, column = divmod(index, 3)
                chip_x = 72 + column * 338
                chip_y = y + 72 + row * 52
                operation_id = _string(ppm.get("operation_id"), "ppm.operation_id")
                outcome = _string(ppm.get("outcome_token"), "ppm.outcome_token")
                batch_level = _integer(ppm.get("batch_level"), "ppm.batch_level")
                observable = _string(ppm.get("presented_observable"), "ppm.presented_observable")
                color = _BATCH_COLORS[(batch_level - 1) % len(_BATCH_COLORS)]
                output.append(
                    f'<g data-ppm-id="{html.escape(operation_id, quote=True)}" '
                    f'data-outcome-token="{html.escape(outcome, quote=True)}" '
                    f'data-batch-level="{batch_level}">'
                )
                output.append(
                    _svg_rect(chip_x, chip_y, 316, 43, css_class="panel2", fill=color, rx=7)
                )
                output.append(
                    _svg_text(
                        chip_x + 10,
                        chip_y + 18,
                        f"B{batch_level:02d}  {_short_identifier(operation_id)}",
                        css_class="heading",
                    )
                )
                clipped = observable if len(observable) <= 49 else observable[:46] + "…"
                output.append(_svg_text(chip_x + 10, chip_y + 35, clipped, css_class="small"))
                output.append("</g>")
            arrow_y = y + 180
            output.append(f'<path d="M 585 {y + 167} L 585 {arrow_y}" class="arrow"/>')
            output.append(
                _svg_text(600, arrow_y - 2, "outcomes update symbolic frame", css_class="small")
            )
            for index, correction in enumerate(corrections):
                column = index % 3
                row = index // 3
                correction_x = 72 + column * 338
                correction_y = y + 196 + row * 21
                update_id = _string(correction.get("update_id"), "correction.update_id")
                outcomes = _strings(
                    correction.get("outcome_dependencies"),
                    "correction.outcome_dependencies",
                )
                label = (
                    f"{_string(correction.get('frame_gate'), 'correction.frame_gate')} ← "
                    f"{_string(correction.get('condition'), 'correction.condition')}"
                )
                if len(label) > 47:
                    label = label[:44] + "…"
                output.append(
                    f'<g data-update-id="{html.escape(update_id, quote=True)}" '
                    f'data-outcomes="{html.escape("|".join(outcomes), quote=True)}">'
                )
                output.append(_svg_text(correction_x, correction_y, label, css_class="mono"))
                output.append("</g>")
        else:
            output.append(
                _svg_text(
                    72,
                    y + 82,
                    "Implementation-neutral pass-through CNOT • finite cost OPEN",
                    css_class="body",
                )
            )
        output.append("</g>")
        y += card_height + 28

    frame_out_y = y
    output.append(
        f'<g data-frame-role="out" data-frame-signature="{html.escape(frame_out, quote=True)}">'
    )
    output.append(_svg_rect(50, frame_out_y, 1070, 62, css_class="panel2"))
    output.append(
        _svg_text(
            70,
            frame_out_y + 26,
            f"FRAME-OUT  {_short_signature(frame_out)}",
            css_class="heading",
        )
    )
    output.append(
        _svg_text(
            70,
            frame_out_y + 48,
            f"{_integer(panel.get('frame_out_term_count'), 'panel.frame_out_term_count')} conditional terms",
            css_class="small",
        )
    )
    output.append("</g>")

    output.append(_svg_rect(1145, 136, 405, max(620, height - 186), css_class="panel"))
    output.append(_svg_text(1167, 171, "Candidate groups in this layer", css_class="heading"))
    side_y = 202
    for raw_group in _sequence(panel.get("batch_groups"), "panel.batch_groups"):
        group = _mapping(raw_group, "panel.batch_groups[]")
        level = _integer(group.get("batch_level"), "batch_group.batch_level")
        ppm_count = _integer(group.get("ppm_count_in_panel"), "batch_group.ppm_count_in_panel")
        maximum_weight = _integer(group.get("maximum_ppm_weight"), "batch_group.maximum_ppm_weight")
        color = _BATCH_COLORS[(level - 1) % len(_BATCH_COLORS)]
        output.append(f'<g data-panel-batch-level="{level}" data-panel-ppm-count="{ppm_count}">')
        output.append(_svg_rect(1167, side_y, 360, 43, css_class="panel2", fill=color, rx=7))
        output.append(
            _svg_text(
                1182,
                side_y + 27,
                f"B{level:02d} • {ppm_count} PPM • batch max weight {maximum_weight}",
                css_class="heading",
            )
        )
        output.append("</g>")
        side_y += 54
    if side_y == 202:
        output.append(_svg_text(1167, side_y + 22, "No PPM candidate groups", css_class="body"))
        side_y += 48

    side_y += 18
    output.append(_svg_text(1167, side_y, "Separation certificates", css_class="heading"))
    side_y += 28
    reason_counts = _mapping(
        panel.get("separation_reason_counts"),
        "panel.separation_reason_counts",
    )
    reason_labels = {
        "causal_dependency": "causal order",
        "reaction_dependency": "reaction edge",
        "symplectic_noncommutation": "symplectic noncommutation",
        "logical_axis_conflict": "logical-axis conflict",
        "resource_reuse": "resource reuse",
        "deterministic_frontier_partition": "frontier partition",
    }
    for reason in sorted(reason_counts):
        count = _integer(reason_counts[reason], f"reason_counts.{reason}")
        output.append(
            _svg_text(
                1167, side_y, f"{reason_labels.get(reason, reason)}: {count}", css_class="body"
            )
        )
        side_y += 23
    if not reason_counts:
        output.append(_svg_text(1167, side_y, "none in this layer", css_class="body"))
        side_y += 23

    side_y += 22
    output.append(_svg_text(1167, side_y, "Interpretation", css_class="heading"))
    side_y += 28
    for line in (
        "Color = candidate batch membership.",
        "Arrows = measured outcomes update frame.",
        "Frame signatures are exact serialized hashes.",
        "No physical placement or duration is shown.",
        "Finite backend remains rejected.",
    ):
        output.append(_svg_text(1167, side_y, line, css_class="body"))
        side_y += 23
    output.append("</svg>")
    return "\n".join(output) + "\n"


def render_direct_ccz_ppm_atlas_svgs(atlas: Mapping[str, Any]) -> dict[str, str]:
    """Render the overview and all macro-layer panels as standalone SVGs."""

    if _string(atlas.get("schema"), "atlas.schema") != "ecdlp-ftqc/direct-ccz-ppm-atlas":
        raise DirectCczPpmAtlasError("unexpected atlas schema")
    fingerprint = _canonical_sha256(atlas)
    documents = {"overview.svg": _render_overview(atlas, fingerprint)}
    for raw_panel in _sequence(atlas.get("panels"), "atlas.panels"):
        panel = _mapping(raw_panel, "atlas.panels[]")
        layer = _integer(panel.get("source_algorithmic_layer"), "panel.layer")
        documents[f"macro-layer-{layer:02d}.svg"] = _render_layer_panel(panel, fingerprint)
    return documents
