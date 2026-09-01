"""Independent replay of serialized direct-CCZ PPM atlas data and SVGs.

This module intentionally imports neither the visualization renderer nor the
Phase-A compiler or Phase-B scheduler.  It reconstructs the atlas projection
from serialized artifacts and parses every SVG as XML.
"""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class DirectCczPpmAtlasReplayError(ValueError):
    """Raised when atlas data or rendered SVGs fail independent replay."""


@dataclass(frozen=True, slots=True)
class DirectCczPpmAtlasReplaySummary:
    """Counts reconstructed independently from atlas inputs and SVG documents."""

    all_passed: bool
    atlas_panel_count: int
    batch_membership_checks: int
    correction_update_checks: int
    finite_backend_rejected: bool
    non_temporal_document_checks: int
    ppm_checks: int
    separation_certificate_checks: int
    source_dependency_checks: int
    source_operation_checks: int
    svg_document_checks: int
    svg_ppm_id_checks: int
    svg_source_operation_id_checks: int
    svg_update_id_checks: int


_ATLAS_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-atlas"
_SVG_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-atlas-svg"
_BATCH_UNIT = "candidate_batch_level_not_time"
_NOTICE_FRAGMENT = "candidate batch levels are not time, surgery rounds"
_SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DirectCczPpmAtlasReplayError(f"{path} must be a mapping")
    return value


def _sequence(value: object, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise DirectCczPpmAtlasReplayError(f"{path} must be a sequence")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczPpmAtlasReplayError(f"{path} must be a non-empty string")
    return value


def _integer(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DirectCczPpmAtlasReplayError(f"{path} must be an integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DirectCczPpmAtlasReplayError(f"{path} must be a boolean")
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


def _assert_equal(actual: object, expected: object, path: str) -> None:
    if actual != expected:
        raise DirectCczPpmAtlasReplayError(
            f"{path} mismatch: expected {expected!r}, observed {actual!r}"
        )


def _relation_reasons(relation: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    if _string(relation.get("causal_order"), "relation.causal_order") != "none":
        reasons.append("causal_dependency")
    if _boolean(relation.get("reaction_dependent"), "relation.reaction_dependent"):
        reasons.append("reaction_dependency")
    if not _boolean(
        relation.get("universally_commuting"),
        "relation.universally_commuting",
    ):
        reasons.append("symplectic_noncommutation")
    if not _boolean(
        relation.get("universally_axis_consistent"),
        "relation.universally_axis_consistent",
    ):
        reasons.append("logical_axis_conflict")
    if _boolean(relation.get("resource_reuse_conflict"), "relation.resource_reuse_conflict"):
        reasons.append("resource_reuse")
    return tuple(reasons)


def _expected_batch_map(
    general: Mapping[str, Any],
) -> tuple[dict[str, int], dict[int, tuple[str, ...]]]:
    schedule = _mapping(general.get("optimized_schedule"), "general.optimized_schedule")
    _assert_equal(schedule.get("unit"), _BATCH_UNIT, "optimized_schedule.unit")
    _assert_equal(
        schedule.get("complete_native_schedule"),
        False,
        "optimized_schedule.complete_native_schedule",
    )
    operation_to_level: dict[str, int] = {}
    by_level: dict[int, tuple[str, ...]] = {}
    for raw_batch in _sequence(schedule.get("batches"), "optimized_schedule.batches"):
        batch = _mapping(raw_batch, "optimized_schedule.batches[]")
        level = _integer(batch.get("batch_level"), "batch.batch_level")
        operation_ids = _strings(batch.get("operation_ids"), "batch.operation_ids")
        if level in by_level:
            raise DirectCczPpmAtlasReplayError(f"duplicate batch level {level}")
        by_level[level] = operation_ids
        for operation_id in operation_ids:
            if operation_id in operation_to_level:
                raise DirectCczPpmAtlasReplayError(f"duplicate batch membership {operation_id}")
            operation_to_level[operation_id] = level
    _assert_equal(tuple(sorted(by_level)), tuple(range(1, len(by_level) + 1)), "batch levels")
    return operation_to_level, by_level


def _expected_certificates(
    general: Mapping[str, Any],
    operation_to_level: Mapping[str, int],
) -> dict[str, tuple[tuple[int, str, tuple[str, ...]], ...]]:
    certificates: dict[str, list[tuple[int, str, tuple[str, ...]]]] = defaultdict(list)
    for raw_relation in _sequence(general.get("pair_relations"), "general.pair_relations"):
        relation = _mapping(raw_relation, "general.pair_relations[]")
        left = _string(relation.get("left_operation_id"), "relation.left_operation_id")
        right = _string(relation.get("right_operation_id"), "relation.right_operation_id")
        left_level = operation_to_level[left]
        right_level = operation_to_level[right]
        if left_level == right_level:
            _assert_equal(
                relation.get("general_high_rate_compatible"),
                True,
                f"same-level compatibility {left}/{right}",
            )
            continue
        earlier, later = (left, right) if left_level < right_level else (right, left)
        reasons = _relation_reasons(relation) or ("deterministic_frontier_partition",)
        certificates[later].append((operation_to_level[earlier], earlier, reasons))
    return {operation_id: tuple(sorted(items)) for operation_id, items in certificates.items()}


def _atlas_certificate_tuple(
    value: object, path: str
) -> tuple[tuple[int, str, tuple[str, ...]], ...]:
    records: list[tuple[int, str, tuple[str, ...]]] = []
    for raw_certificate in _sequence(value, path):
        certificate = _mapping(raw_certificate, f"{path}[]")
        records.append(
            (
                _integer(
                    certificate.get("earlier_batch_level"),
                    "certificate.earlier_batch_level",
                ),
                _string(
                    certificate.get("earlier_operation_id"),
                    "certificate.earlier_operation_id",
                ),
                _strings(certificate.get("reasons"), "certificate.reasons"),
            )
        )
    return tuple(records)


def _source_dependency_key(dependency: Mapping[str, Any]) -> tuple[str, str, tuple[str, ...], str]:
    return (
        _string(
            dependency.get("predecessor_source_gate_id"),
            "dependency.predecessor_source_gate_id",
        ),
        _string(
            dependency.get("successor_source_gate_id"),
            "dependency.successor_source_gate_id",
        ),
        _strings(dependency.get("logical_values"), "dependency.logical_values"),
        _string(dependency.get("reason"), "dependency.reason"),
    )


def _validate_svg_documents(
    atlas: Mapping[str, Any],
    svg_documents: Mapping[str, str],
    expected_source_ids: frozenset[str],
    expected_ppm_ids: frozenset[str],
    expected_update_ids: frozenset[str],
) -> tuple[int, int, int, int, int]:
    panels = tuple(
        _mapping(item, "atlas.panels[]") for item in _sequence(atlas.get("panels"), "atlas.panels")
    )
    expected_names = {"overview.svg"} | {
        f"macro-layer-{_integer(panel.get('source_algorithmic_layer'), 'panel.layer'):02d}.svg"
        for panel in panels
    }
    _assert_equal(set(svg_documents), expected_names, "SVG document names")
    fingerprint = _canonical_sha256(atlas)
    source_ids: list[str] = []
    ppm_ids: list[str] = []
    update_ids: list[str] = []
    non_temporal_checks = 0

    for name in sorted(svg_documents):
        document = _string(svg_documents[name], f"svg_documents[{name}]")
        try:
            root = ET.fromstring(document)
        except ET.ParseError as exc:
            raise DirectCczPpmAtlasReplayError(f"invalid SVG XML in {name}: {exc}") from exc
        if root.tag != f"{_SVG_NAMESPACE}svg":
            raise DirectCczPpmAtlasReplayError(f"{name} root is not SVG")
        _assert_equal(root.attrib.get("data-schema"), _SVG_SCHEMA, f"{name} data-schema")
        _assert_equal(
            root.attrib.get("data-batch-unit"),
            _BATCH_UNIT,
            f"{name} data-batch-unit",
        )
        _assert_equal(
            root.attrib.get("data-atlas-fingerprint"),
            fingerprint,
            f"{name} atlas fingerprint",
        )
        if _NOTICE_FRAGMENT not in "".join(root.itertext()):
            raise DirectCczPpmAtlasReplayError(f"{name} omits the non-temporal notice")
        non_temporal_checks += 1
        if root.findall(f".//{_SVG_NAMESPACE}script"):
            raise DirectCczPpmAtlasReplayError(f"{name} must be a static SVG")
        for element in root.iter():
            if any(key.endswith("href") for key in element.attrib):
                raise DirectCczPpmAtlasReplayError(f"{name} contains an external reference")
            source_id = element.attrib.get("data-source-gate-id")
            ppm_id = element.attrib.get("data-ppm-id")
            update_id = element.attrib.get("data-update-id")
            if source_id is not None:
                source_ids.append(source_id)
            if ppm_id is not None:
                ppm_ids.append(ppm_id)
            if update_id is not None:
                update_ids.append(update_id)

    _assert_equal(len(source_ids), len(set(source_ids)), "duplicate SVG source operation IDs")
    _assert_equal(len(ppm_ids), len(set(ppm_ids)), "duplicate SVG PPM IDs")
    _assert_equal(len(update_ids), len(set(update_ids)), "duplicate SVG update IDs")
    _assert_equal(frozenset(source_ids), expected_source_ids, "SVG source operation coverage")
    _assert_equal(frozenset(ppm_ids), expected_ppm_ids, "SVG PPM coverage")
    _assert_equal(frozenset(update_ids), expected_update_ids, "SVG update coverage")
    return len(svg_documents), non_temporal_checks, len(source_ids), len(ppm_ids), len(update_ids)


def replay_direct_ccz_ppm_atlas(
    trace_data: Mapping[str, Any],
    general_data: Mapping[str, Any],
    finite_data: Mapping[str, Any],
    atlas_data: Mapping[str, Any],
    svg_documents: Mapping[str, str],
) -> DirectCczPpmAtlasReplaySummary:
    """Independently verify the atlas projection and every rendered SVG."""

    _assert_equal(atlas_data.get("schema"), _ATLAS_SCHEMA, "atlas.schema")
    _assert_equal(atlas_data.get("schema_version"), 1, "atlas.schema_version")
    trace_id = _string(trace_data.get("trace_id"), "trace.trace_id")
    _assert_equal(atlas_data.get("trace_id"), trace_id, "atlas.trace_id")
    _assert_equal(general_data.get("trace_id"), trace_id, "general.trace_id")
    _assert_equal(finite_data.get("trace_id"), trace_id, "finite.trace_id")

    fingerprints = _mapping(atlas_data.get("input_fingerprints"), "atlas.input_fingerprints")
    _assert_equal(
        fingerprints.get("symbolic_trace_sha256"),
        _canonical_sha256(trace_data),
        "symbolic trace fingerprint",
    )
    _assert_equal(
        fingerprints.get("general_candidate_sha256"),
        _canonical_sha256(general_data),
        "general candidate fingerprint",
    )
    _assert_equal(
        fingerprints.get("finite_admission_sha256"),
        _canonical_sha256(finite_data),
        "finite admission fingerprint",
    )

    operation_to_level, batches = _expected_batch_map(general_data)
    expected_ppms = {
        _string(ppm.get("operation_id"), "ppm.operation_id"): ppm
        for ppm in (
            _mapping(item, "trace.ppms[]")
            for item in _sequence(trace_data.get("ppms"), "trace.ppms")
        )
    }
    _assert_equal(set(operation_to_level), set(expected_ppms), "scheduled PPM set")
    expected_profiles = {
        _string(profile.get("operation_id"), "profile.operation_id"): profile
        for profile in (
            _mapping(item, "general.observable_profiles[]")
            for item in _sequence(
                general_data.get("observable_profiles"),
                "general.observable_profiles",
            )
        )
    }
    _assert_equal(set(expected_profiles), set(expected_ppms), "profile PPM set")
    expected_certificates = _expected_certificates(general_data, operation_to_level)

    expected_sources = {
        _string(operation.get("source_gate_id"), "source_operation.source_gate_id"): operation
        for operation in (
            _mapping(item, "trace.source_operations[]")
            for item in _sequence(trace_data.get("source_operations"), "trace.source_operations")
        )
    }
    expected_injections = {
        _string(injection.get("source_gate_id"), "injection.source_gate_id"): injection
        for injection in (
            _mapping(item, "trace.injections[]")
            for item in _sequence(trace_data.get("injections"), "trace.injections")
        )
    }
    expected_updates = {
        _string(update.get("update_id"), "update.update_id"): update
        for update in (
            _mapping(item, "trace.correction_updates[]")
            for item in _sequence(
                trace_data.get("correction_updates"),
                "trace.correction_updates",
            )
        )
    }
    expected_dependencies = {
        _source_dependency_key(dependency)
        for dependency in (
            _mapping(item, "trace.source_dependencies[]")
            for item in _sequence(
                trace_data.get("source_dependencies"),
                "trace.source_dependencies",
            )
        )
    }
    expected_frames = {
        _integer(frame.get("source_algorithmic_layer"), "macro_frame.layer"): frame
        for frame in (
            _mapping(item, "trace.macro_layer_frames[]")
            for item in _sequence(
                trace_data.get("macro_layer_frames"),
                "trace.macro_layer_frames",
            )
        )
    }

    overview = _mapping(atlas_data.get("overview"), "atlas.overview")
    _assert_equal(
        overview.get("source_operation_count"), len(expected_sources), "overview source count"
    )
    _assert_equal(overview.get("ppm_count"), len(expected_ppms), "overview PPM count")
    _assert_equal(
        overview.get("correction_update_count"), len(expected_updates), "overview update count"
    )
    _assert_equal(
        overview.get("injection_count"), len(expected_injections), "overview injection count"
    )
    _assert_equal(overview.get("macro_layer_count"), len(expected_frames), "overview layer count")
    _assert_equal(overview.get("candidate_batch_level_count"), len(batches), "overview batch count")
    _assert_equal(
        tuple(_sequence(overview.get("batch_sizes"), "overview.batch_sizes")),
        tuple(len(batches[level]) for level in sorted(batches)),
        "overview batch sizes",
    )

    observed_source_ids: list[str] = []
    observed_ppm_ids: list[str] = []
    observed_update_ids: list[str] = []
    observed_dependencies: set[tuple[str, str, tuple[str, ...], str]] = set()
    separation_checks = 0
    batch_membership_checks = 0
    panels = tuple(
        _mapping(item, "atlas.panels[]")
        for item in _sequence(atlas_data.get("panels"), "atlas.panels")
    )
    observed_layers: list[int] = []

    for panel in panels:
        layer = _integer(panel.get("source_algorithmic_layer"), "panel.layer")
        observed_layers.append(layer)
        frame = expected_frames.get(layer)
        if frame is None:
            raise DirectCczPpmAtlasReplayError(f"unexpected atlas layer {layer}")
        frame_in = _mapping(frame.get("frame_in"), "macro_frame.frame_in")
        frame_out = _mapping(frame.get("frame_out"), "macro_frame.frame_out")
        _assert_equal(
            panel.get("frame_in_signature"), frame_in.get("signature"), f"layer {layer} frame-in"
        )
        _assert_equal(
            panel.get("frame_out_signature"), frame_out.get("signature"), f"layer {layer} frame-out"
        )
        _assert_equal(
            panel.get("frame_in_term_count"),
            len(_sequence(frame_in.get("terms"), "frame_in.terms")),
            f"layer {layer} frame-in terms",
        )
        _assert_equal(
            panel.get("frame_out_term_count"),
            len(_sequence(frame_out.get("terms"), "frame_out.terms")),
            f"layer {layer} frame-out terms",
        )

        panel_reason_counts: Counter[str] = Counter()
        panel_ppms: list[str] = []
        for raw_operation in _sequence(panel.get("source_operations"), "panel.source_operations"):
            operation = _mapping(raw_operation, "panel.source_operations[]")
            source_id = _string(operation.get("source_gate_id"), "atlas_source.source_gate_id")
            observed_source_ids.append(source_id)
            source = expected_sources.get(source_id)
            if source is None:
                raise DirectCczPpmAtlasReplayError(f"unknown atlas source operation {source_id}")
            _assert_equal(
                _integer(source.get("source_algorithmic_layer"), "source.layer"),
                layer,
                f"source layer {source_id}",
            )
            for field in (
                "source_kind",
                "source_stage",
                "logical_support",
                "lowering_kind",
                "frame_in_signature",
                "frame_out_signature",
            ):
                _assert_equal(
                    operation.get(field), source.get(field), f"source {source_id} {field}"
                )

            injection = expected_injections.get(source_id)
            expected_ppm_ids = (
                ()
                if injection is None
                else _strings(
                    injection.get("ppm_operation_ids"),
                    "injection.ppm_operation_ids",
                )
            )
            atlas_ppm_rows = tuple(
                _mapping(item, "atlas_source.ppm_measurements[]")
                for item in _sequence(
                    operation.get("ppm_measurements"),
                    "atlas_source.ppm_measurements",
                )
            )
            _assert_equal(
                tuple(
                    _string(row.get("operation_id"), "atlas_ppm.operation_id")
                    for row in atlas_ppm_rows
                ),
                expected_ppm_ids,
                f"source {source_id} PPM order",
            )
            for row in atlas_ppm_rows:
                ppm_id = _string(row.get("operation_id"), "atlas_ppm.operation_id")
                observed_ppm_ids.append(ppm_id)
                panel_ppms.append(ppm_id)
                ppm = expected_ppms[ppm_id]
                profile = expected_profiles[ppm_id]
                _assert_equal(
                    row.get("outcome_token"), ppm.get("outcome_token"), f"PPM {ppm_id} outcome"
                )
                _assert_equal(
                    row.get("batch_level"), operation_to_level[ppm_id], f"PPM {ppm_id} batch"
                )
                _assert_equal(row.get("candidate_unit"), _BATCH_UNIT, f"PPM {ppm_id} unit")
                _assert_equal(
                    row.get("minimum_weight"),
                    profile.get("minimum_weight"),
                    f"PPM {ppm_id} min weight",
                )
                _assert_equal(
                    row.get("maximum_weight"),
                    profile.get("maximum_weight"),
                    f"PPM {ppm_id} max weight",
                )
                expected = expected_certificates.get(ppm_id, ())
                observed = _atlas_certificate_tuple(
                    row.get("separation_certificates_from_earlier_levels"),
                    f"PPM {ppm_id} certificates",
                )
                _assert_equal(observed, expected, f"PPM {ppm_id} separation certificates")
                for _, _, reasons in observed:
                    panel_reason_counts.update(reasons)
                separation_checks += len(observed)
                batch_membership_checks += 1

            expected_source_update_ids = tuple(
                sorted(
                    update_id
                    for update_id, update in expected_updates.items()
                    if _string(update.get("source_gate_id"), "update.source_gate_id") == source_id
                )
            )
            atlas_updates = tuple(
                _mapping(item, "atlas_source.correction_updates[]")
                for item in _sequence(
                    operation.get("correction_updates"),
                    "atlas_source.correction_updates",
                )
            )
            _assert_equal(
                tuple(
                    _string(update.get("update_id"), "atlas_update.update_id")
                    for update in atlas_updates
                ),
                expected_source_update_ids,
                f"source {source_id} update order",
            )
            for atlas_update in atlas_updates:
                update_id = _string(atlas_update.get("update_id"), "atlas_update.update_id")
                observed_update_ids.append(update_id)
                expected_update = expected_updates[update_id]
                _assert_equal(
                    atlas_update.get("outcome_dependencies"),
                    expected_update.get("outcome_dependencies"),
                    f"update {update_id} outcomes",
                )
                _assert_equal(
                    atlas_update.get("resulting_frame_signature"),
                    expected_update.get("resulting_frame_signature"),
                    f"update {update_id} frame signature",
                )

            for raw_dependency in _sequence(
                operation.get("source_dependencies"),
                "atlas_source.source_dependencies",
            ):
                observed_dependencies.add(
                    _source_dependency_key(_mapping(raw_dependency, "atlas dependency"))
                )

        _assert_equal(
            tuple(_strings(panel.get("ppm_operation_ids"), "panel.ppm_operation_ids")),
            tuple(panel_ppms),
            f"layer {layer} PPM index",
        )
        _assert_equal(
            dict(_mapping(panel.get("separation_reason_counts"), "panel.reason_counts")),
            dict(sorted(panel_reason_counts.items())),
            f"layer {layer} separation counts",
        )
        atlas_groups = {
            _integer(group.get("batch_level"), "atlas_batch_group.batch_level"): tuple(
                _strings(group.get("operation_ids"), "atlas_batch_group.operation_ids")
            )
            for group in (
                _mapping(item, "panel.batch_groups[]")
                for item in _sequence(panel.get("batch_groups"), "panel.batch_groups")
            )
        }
        expected_groups = {
            level: tuple(
                operation_id for operation_id in batches[level] if operation_id in panel_ppms
            )
            for level in sorted(batches)
            if any(operation_id in panel_ppms for operation_id in batches[level])
        }
        _assert_equal(atlas_groups, expected_groups, f"layer {layer} batch groups")

    _assert_equal(tuple(observed_layers), tuple(sorted(expected_frames)), "atlas panel layer order")
    _assert_equal(
        len(observed_source_ids), len(set(observed_source_ids)), "duplicate atlas source IDs"
    )
    _assert_equal(len(observed_ppm_ids), len(set(observed_ppm_ids)), "duplicate atlas PPM IDs")
    _assert_equal(
        len(observed_update_ids), len(set(observed_update_ids)), "duplicate atlas update IDs"
    )
    _assert_equal(
        frozenset(observed_source_ids), frozenset(expected_sources), "atlas source coverage"
    )
    _assert_equal(frozenset(observed_ppm_ids), frozenset(expected_ppms), "atlas PPM coverage")
    _assert_equal(
        frozenset(observed_update_ids), frozenset(expected_updates), "atlas update coverage"
    )
    _assert_equal(observed_dependencies, expected_dependencies, "atlas source dependency coverage")

    backend = _mapping(atlas_data.get("backend_status"), "atlas.backend_status")
    _assert_equal(backend.get("finite_backend_admitted"), False, "atlas finite admission")
    _assert_equal(backend.get("native_schedule_emitted"), False, "atlas native schedule")
    _assert_equal(backend.get("verdict"), finite_data.get("verdict"), "atlas finite verdict")
    for field in (
        "capability_missing_fields",
        "backend_missing_fields",
        "backend_incompatible_fields",
        "native_mapper_missing_fields",
    ):
        _assert_equal(backend.get(field), finite_data.get(field), f"atlas backend {field}")
    null_outputs = _mapping(backend.get("null_finite_outputs"), "backend.null_finite_outputs")
    for field in ("schedule", "runtime_seconds", "physical_qubits", "failure_probability"):
        _assert_equal(null_outputs.get(field), None, f"atlas null finite output {field}")
        _assert_equal(finite_data.get(field), None, f"finite null output {field}")

    svg_counts = _validate_svg_documents(
        atlas_data,
        svg_documents,
        frozenset(expected_sources),
        frozenset(expected_ppms),
        frozenset(expected_updates),
    )
    return DirectCczPpmAtlasReplaySummary(
        all_passed=True,
        atlas_panel_count=len(panels),
        batch_membership_checks=batch_membership_checks,
        correction_update_checks=len(observed_update_ids),
        finite_backend_rejected=True,
        non_temporal_document_checks=svg_counts[1],
        ppm_checks=len(observed_ppm_ids),
        separation_certificate_checks=separation_checks,
        source_dependency_checks=len(observed_dependencies),
        source_operation_checks=len(observed_source_ids),
        svg_document_checks=svg_counts[0],
        svg_ppm_id_checks=svg_counts[3],
        svg_source_operation_id_checks=svg_counts[2],
        svg_update_id_checks=svg_counts[4],
    )


def direct_ccz_ppm_atlas_replay_to_data(
    replay: DirectCczPpmAtlasReplaySummary,
) -> dict[str, Any]:
    """Serialize an atlas replay summary."""

    return {
        "all_passed": replay.all_passed,
        "atlas_panel_count": replay.atlas_panel_count,
        "batch_membership_checks": replay.batch_membership_checks,
        "correction_update_checks": replay.correction_update_checks,
        "finite_backend_rejected": replay.finite_backend_rejected,
        "non_temporal_document_checks": replay.non_temporal_document_checks,
        "ppm_checks": replay.ppm_checks,
        "separation_certificate_checks": replay.separation_certificate_checks,
        "source_dependency_checks": replay.source_dependency_checks,
        "source_operation_checks": replay.source_operation_checks,
        "svg_document_checks": replay.svg_document_checks,
        "svg_ppm_id_checks": replay.svg_ppm_id_checks,
        "svg_source_operation_id_checks": replay.svg_source_operation_id_checks,
        "svg_update_id_checks": replay.svg_update_id_checks,
    }
