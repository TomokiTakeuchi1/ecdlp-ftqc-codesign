"""Independent replay for the compact width-256 commutation-aware study."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
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
from ecdlp_ftqc.scheduler import direct_ccz_ppm_support_certificate as support_model

_SCHEMA = "ecdlp-ftqc/width256-commutation-aware-clean-oop-qcla"
_COORDINATE = (
    "architecture_independent_two_phase_direct_ccz_candidate_levels_not_time"
)


class Width256CommutationAwareReplayError(ValueError):
    """Raised when serialized width-256 evidence does not replay."""


@dataclass(frozen=True, slots=True)
class Width256CommutationAwareReplaySummary:
    """Auditable counts from a successful independent reconstruction."""

    width: int
    source_ccx_count: int
    source_cnot_count: int
    full_pair_count_checked: int
    compact_dependency_nodes_checked: int
    unitary_macro_depth: int
    unitary_candidate_levels: int
    candidate_support_levels_checked: int
    candidate_support_profiles_recomputed: int
    cleanup_candidates_checked: int
    cleanup_mixed_axis_witnesses_checked: int
    cleanup_candidates_admitted: int
    selected_variant: str
    native_outputs_null: bool
    all_passed: bool


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise Width256CommutationAwareReplayError(f"{label} must be a mapping")
    return value


def _sequence(value: object, *, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise Width256CommutationAwareReplayError(f"{label} must be a sequence")
    return value


def _strings(value: object, *, label: str) -> tuple[str, ...]:
    sequence = _sequence(value, label=label)
    if any(not isinstance(item, str) for item in sequence):
        raise Width256CommutationAwareReplayError(f"{label} must contain strings")
    return tuple(str(item) for item in sequence)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest().upper()


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


def _oracle_nodes_and_summary(
    trace: OopQclaTrace,
    gates: tuple[OopQclaGate, ...],
) -> tuple[list[dict[str, object]], list[list[str]], tuple[str, ...], dict[str, object]]:
    cnot_layers = _cnot_layers(trace)
    counts: Counter[str] = Counter()
    stream = hashlib.sha256()
    ranks: list[int] = []
    parents: list[int | None] = []
    nodes: list[dict[str, object]] = []
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
            stream.update(
                (
                    json.dumps(
                        (
                            left.gate_id,
                            right.gate_id,
                            overlap,
                            barriers,
                            dependency,
                        ),
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
            )
            if dependency:
                candidates.append(left_index)
        parent = max(candidates, key=lambda item: (ranks[item], -item), default=None)
        rank = 1 if parent is None else ranks[parent] + 1
        ranks.append(rank)
        parents.append(parent)
        barrier_witness = (
            ()
            if parent is None
            else tuple(
                layer
                for layer in cnot_layers
                if gates[parent].algorithmic_layer
                < layer
                < right.algorithmic_layer
            )
        )
        reasons: list[str] = []
        if parent is not None:
            parent_commutes, _ = _relation(gates[parent], right)
            if not parent_commutes:
                reasons.append("noncommuting_target_control")
            if barrier_witness:
                reasons.append("source_clifford_barrier")
        nodes.append(
            {
                "controls": list(right.controls),
                "macro_rank": rank,
                "segment_index": sum(
                    layer < right.algorithmic_layer for layer in cnot_layers
                ),
                "source_algorithmic_layer": right.algorithmic_layer,
                "source_gate_id": right.gate_id,
                "source_position": right_index,
                "source_stage": right.stage.value,
                "target": right.target,
                "witness_barrier_layers": list(barrier_witness),
                "witness_predecessor": (
                    None if parent is None else gates[parent].gate_id
                ),
                "witness_reasons": reasons,
            }
        )
    maximum = max(ranks)
    groups = [
        [gate.gate_id for index, gate in enumerate(gates) if ranks[index] == rank]
        for rank in range(1, maximum + 1)
    ]
    endpoint = max(range(len(gates)), key=lambda item: (ranks[item], -item))
    path: list[str] = []
    cursor: int | None = endpoint
    while cursor is not None:
        path.append(gates[cursor].gate_id)
        cursor = parents[cursor]
    path.reverse()
    overlap_counts = [
        [name, counts[name]]
        for name in (
            "disjoint",
            "shared_control",
            "shared_target",
            "left_target_right_control",
            "right_target_left_control",
            "bidirectional_target_control",
        )
    ]
    summary: dict[str, object] = {
        "admitted_pair_count": counts["admitted"],
        "barrier_pair_count": counts["barrier"],
        "compact_rank_match": True,
        "decision_stream_sha256": stream.hexdigest().upper(),
        "dependency_pair_count": counts["dependency"],
        "evidence_status": "PROVED",
        "noncommuting_pair_count": counts["noncommuting"],
        "operation_count": len(gates),
        "overlap_kind_counts": overlap_counts,
        "pair_count": counts["pairs"],
        "pair_records_materialized": False,
    }
    return nodes, groups, tuple(path), summary


def _support_levels(
    trace: OopQclaTrace,
    event_trace: DirectCczEventTrace,
    groups: Sequence[Sequence[str]],
) -> list[dict[str, object]]:
    gates_by_id = {gate.gate_id: gate for gate in trace.gates}
    events = {event.source_gate_id: event for event in event_trace.injection_events}
    logical_values = tuple(
        sorted({value for gate in trace.gates for value in gate.logical_support})
    )
    arena = support_model._AnfZddArena()
    columns: support_model.SupportMatrix = {
        value: {value: arena.ONE} for value in logical_values
    }
    cnot_by_layer: dict[int, list[OopQclaGate]] = defaultdict(list)
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            cnot_by_layer[gate.algorithmic_layer].append(gate)
    applied: set[int] = set()
    result: list[dict[str, object]] = []
    for macro_layer, raw_ids in enumerate(groups, start=1):
        gate_ids = tuple(str(item) for item in raw_ids)
        layer_gates = tuple(gates_by_id[item] for item in gate_ids)
        lower = min(gate.algorithmic_layer for gate in layer_gates)
        upper = max(gate.algorithmic_layer for gate in layer_gates)
        if any(lower <= layer <= upper for layer in cnot_by_layer):
            raise Width256CommutationAwareReplayError(
                "candidate macro layer crosses a CNOT barrier"
            )
        for layer in sorted(cnot_by_layer):
            if layer >= lower or layer in applied:
                continue
            for gate in cnot_by_layer[layer]:
                support_model._source_cnot_conjugate(
                    arena, columns, gate.controls[0], gate.target
                )
            applied.add(layer)
        by_phase: dict[int, list[support_model.PpmSupportProfile]] = {1: [], 2: []}
        for gate in layer_gates:
            event = events[gate.gate_id]
            for index, data_value in enumerate(event.data):
                ppm = event.ppms[index]
                by_phase[1].append(
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
                by_phase[2].append(
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
        targets = {gate.target for gate in layer_gates}
        for phase in (1, 2):
            candidate_level = 2 * macro_layer - (2 - phase)
            batch = support_model._batch(
                tuple(by_phase[phase]), batch_level=candidate_level
            )
            result.append(
                {
                    "axis": {1: "Z", 2: "X"}[phase],
                    "branch_dependent_profile_count": (
                        batch.branch_dependent_profile_count
                    ),
                    "candidate_level": candidate_level,
                    "coordinate": support_model.SUPPORT_COORDINATE,
                    "direct_ccz_event_count": len(layer_gates),
                    "evidence_status": "PROVED",
                    "fresh_ccz_resource_count": len(layer_gates),
                    "logical_ppm_count": batch.ppm_count,
                    "macro_layer": macro_layer,
                    "maximum_possible_contact_count": (
                        batch.maximum_possible_contact_count
                    ),
                    "maximum_possible_contact_logical_values": list(
                        batch.maximum_possible_contact_logical_values
                    ),
                    "maximum_ppm_weight_upper_bound": (
                        batch.maximum_ppm_weight_upper_bound
                    ),
                    "phase": phase,
                    "possible_support_exact": True,
                    "possible_support_union_sha256": (
                        batch.possible_support_union_sha256
                    ),
                    "possible_support_union_size": len(batch.possible_support_union),
                    "possible_union_is_simultaneous_weight": False,
                    "source_gate_ids": list(gate_ids),
                    "total_possible_support_incidence": (
                        batch.total_possible_support_incidence
                    ),
                    "unique_target_h_count": len(targets),
                }
            )
        for gate in layer_gates:
            event = events[gate.gate_id]
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
    return result


def _cleanup_rows(
    trace: OopQclaTrace,
    event_trace: DirectCczEventTrace,
    nodes: Sequence[Mapping[str, object]],
) -> tuple[list[dict[str, object]], int, int]:
    ranks = {
        str(node["source_gate_id"]): int(str(node["macro_rank"])) for node in nodes
    }
    events = {event.source_gate_id: event for event in event_trace.injection_events}
    positions = {gate.gate_id: index for index, gate in enumerate(trace.gates)}
    removed = tuple(
        gate
        for gate in trace.gates
        if gate.kind is QclaGateKind.TOFFOLI
        and gate.stage is OopQclaStage.PREFIX_UNCOMPUTE
    )
    removed_ids = {gate.gate_id for gate in removed}
    rows: list[dict[str, object]] = []
    supports: list[set[str]] = []
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
        retained_uses = tuple(
            gate
            for gate in between
            if gate.kind is QclaGateKind.TOFFOLI and gate.gate_id in ranks
        )
        last_use = retained_uses[-1]
        measurement_rank = max(ranks[gate.gate_id] for gate in retained_uses)
        suffix = tuple(
            gate
            for gate in trace.gates[index + 1 :]
            if gate.gate_id not in removed_ids
        )
        active = set(cleanup.controls)
        propagating: list[str] = []
        for gate in suffix:
            if active & set(gate.logical_support):
                propagating.append(gate.gate_id)
                active.update(gate.logical_support)
        later_ppm_ids = tuple(
            gate.gate_id for gate in suffix if gate.kind is QclaGateKind.TOFFOLI
        )
        released_target_uses = sum(
            cleanup.target in gate.logical_support
            for gate in suffix
            if gate.kind is QclaGateKind.TOFFOLI
        )
        event = events[last_use.gate_id]
        other_control = next(
            item for item in last_use.controls if item != cleanup.target
        )
        outcome = event.ppms[2].outcome_token
        token = f"width256:n{trace.width}:{cleanup.gate_id}:cleanup-x"
        rows.append(
            {
                "admitted_to_z_x_only_high_rate_ppm": False,
                "axis_witness": {
                    "evidence_status": "PROVED",
                    "incoming_frame_term": (
                        f"CZ({cleanup.target},{other_control})^{{{outcome}}}"
                    ),
                    "last_quantum_use_source_gate_id": last_use.gate_id,
                    "measured_target": cleanup.target,
                    "mixed_axis": True,
                    "other_control": other_control,
                    "outcome_token": outcome,
                    "presented_measurement": (
                        f"X({cleanup.target}) Z({other_control})"
                    ),
                },
                "candidate_level_if_axis_safe": 2 * measurement_rank,
                "conditional_frame_update": (
                    f"CZ({cleanup.controls[0]},{cleanup.controls[1]})^{{{token}}}"
                ),
                "controls": list(cleanup.controls),
                "evidence_status": "PROVED",
                "final_frame_support_upper_bound": sorted(active),
                "final_source_use": not any(
                    cleanup.target in gate.logical_support
                    for gate in trace.gates[index + 1 :]
                ),
                "frame_propagating_source_gate_count": len(propagating),
                "frame_propagating_source_gate_id_sha256": _digest(
                    tuple(propagating)
                ),
                "last_quantum_use_source_gate_id": last_use.gate_id,
                "later_ppm_count": len(later_ppm_ids),
                "later_ppm_source_gate_id_sha256": _digest(later_ppm_ids),
                "measured_target": cleanup.target,
                "measurement_after_macro_layer": measurement_rank,
                "producer_source_gate_id": producer.gate_id,
                "read_only_between_producer_and_cleanup": all(
                    cleanup.target in gate.controls for gate in between
                ),
                "release_count": 1,
                "released_target_later_ppm_use_count": released_target_uses,
                "source_gate_id_replaced": cleanup.gate_id,
            }
        )
        supports.append(active)
    pair_interactions = sum(
        bool(left & right)
        for left_index, left in enumerate(supports)
        for right in supports[left_index + 1 :]
    )
    contacts: Counter[str] = Counter()
    for support in supports:
        contacts.update(support)
    return rows, pair_interactions, max(contacts.values(), default=0)


def _live_value_data(
    trace: OopQclaTrace,
    nodes: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    ranks = {
        str(node["source_gate_id"]): int(str(node["macro_rank"])) for node in nodes
    }
    intervals: list[dict[str, object]] = []
    for source_interval in trace.ancilla_intervals:
        uses = tuple(
            gate
            for gate in trace.gates
            if source_interval.value_id in gate.logical_support and gate.gate_id in ranks
        )
        producer = next(
            gate
            for gate in uses
            if gate.target == source_interval.value_id
            and gate.stage is OopQclaStage.PREFIX_PROPAGATE
        )
        final = max(ranks[gate.gate_id] for gate in uses)
        intervals.append(
            {
                "birth_macro_layer": ranks[producer.gate_id],
                "final_quantum_use_macro_layer": final,
                "logical_value": source_interval.value_id,
                "release_kind": "coherent_prefix_uncompute",
                "release_macro_layer": final,
            }
        )
    maximum = max(ranks.values())
    persistent = 3 * trace.width
    demand = {
        layer: persistent
        + sum(
            int(
                int(str(item["birth_macro_layer"]))
                <= layer
                <= int(str(item["release_macro_layer"]))
            )
            for item in intervals
        )
        for layer in range(1, maximum + 1)
    }
    peak = max(demand.values())
    return {
        "coordinate": "logical_source_values_not_physical_qubits",
        "fully_resident_source_values": trace.expected_fully_resident_source_values,
        "intervals": intervals,
        "peak_live_macro_layers": [
            layer for layer, count in demand.items() if count == peak
        ],
        "peak_live_source_values": peak,
        "persistent_input_output_values": persistent,
        "prefix_scratch_values": len(intervals),
    }


def replay_width256_commutation_aware_study(
    raw: Mapping[str, object],
    event_trace: DirectCczEventTrace,
) -> Width256CommutationAwareReplaySummary:
    """Rebuild the full pair oracle, support envelopes, cleanup gate, and liveness."""

    trace = build_oop_qcla_trace(256)
    if event_trace.source_trace_id != trace.trace_id:
        raise Width256CommutationAwareReplayError("event trace source mismatch")
    source_ccx = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    source_cnot = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.CNOT
    )
    unitary = _mapping(raw.get("unitary"), label="unitary result")
    measured = _mapping(raw.get("measured_cleanup"), label="cleanup result")
    for variant in (unitary, measured):
        if (
            variant.get("complete_native_schedule") is not False
            or variant.get("native_cycles") is not None
            or variant.get("runtime_seconds") is not None
            or variant.get("physical_qubits") is not None
            or variant.get("failure_probability") is not None
        ):
            raise Width256CommutationAwareReplayError(
                "finite backend output is non-null"
            )
    for item in _sequence(
        measured.get("cleanup_certificates"), label="cleanup certificates"
    ):
        cleanup = _mapping(item, label="cleanup certificate")
        witness = _mapping(cleanup.get("axis_witness"), label="axis witness")
        if (
            cleanup.get("admitted_to_z_x_only_high_rate_ppm") is not False
            or witness.get("mixed_axis") is not True
        ):
            raise Width256CommutationAwareReplayError(
                "mixed-axis cleanup was incorrectly admitted"
            )
    nodes, groups, path, pair_summary = _oracle_nodes_and_summary(trace, source_ccx)
    if list(_sequence(unitary.get("dependency_nodes"), label="dependency nodes")) != nodes:
        raise Width256CommutationAwareReplayError("compact dependency nodes mismatch")
    if list(_sequence(unitary.get("macro_layers"), label="macro layers")) != groups:
        raise Width256CommutationAwareReplayError("macro grouping mismatch")
    if dict(_mapping(unitary.get("pair_oracle"), label="pair oracle")) != pair_summary:
        raise Width256CommutationAwareReplayError("full pair oracle summary mismatch")
    expected_support = _support_levels(trace, event_trace, groups)
    if list(_sequence(unitary.get("candidate_levels"), label="support levels")) != expected_support:
        raise Width256CommutationAwareReplayError("candidate support envelope mismatch")
    expected_live = _live_value_data(trace, nodes)
    if dict(_mapping(unitary.get("live_values"), label="live values")) != expected_live:
        raise Width256CommutationAwareReplayError("live-value envelope mismatch")
    macro_depth = len(groups)
    if (
        unitary.get("variant") != "commutation_aware_unitary"
        or unitary.get("scheduled_ccx_count") != len(source_ccx)
        or unitary.get("removed_cleanup_ccx_count") != 0
        or unitary.get("proposed_cleanup_count") != 0
        or unitary.get("macro_depth") != macro_depth
        or unitary.get("exact_lower_bound_macro_depth") != len(path)
        or _strings(
            unitary.get("critical_path_source_gate_ids"), label="critical path"
        )
        != path
        or unitary.get("direct_ccz_candidate_levels") != 2 * macro_depth
        or unitary.get("complete_logical_candidate_levels") != 2 * macro_depth
        or unitary.get("cleanup_axis_safe") is not True
        or unitary.get("selected_for_z_x_only_high_rate_analysis") is not True
        or unitary.get("fallback_variant") is not None
        or unitary.get("optimality_status") != "PROVED"
        or unitary.get("candidate_coordinate") != _COORDINATE
    ):
        raise Width256CommutationAwareReplayError("unitary headline mismatch")
    cleanup_rows, interactions, max_contact = _cleanup_rows(
        trace, event_trace, nodes
    )
    if list(
        _sequence(measured.get("cleanup_certificates"), label="cleanup certificates")
    ) != cleanup_rows:
        raise Width256CommutationAwareReplayError("cleanup certificate mismatch")
    fallback_equal_fields = (
        "scheduled_ccx_count",
        "dependency_nodes",
        "macro_layers",
        "macro_depth",
        "exact_lower_bound_macro_depth",
        "critical_path_source_gate_ids",
        "direct_ccz_candidate_levels",
        "complete_logical_candidate_levels",
        "candidate_levels",
        "pair_oracle",
        "live_values",
        "retained_inter_macro_outcome_count",
    )
    if any(measured.get(field) != unitary.get(field) for field in fallback_equal_fields):
        raise Width256CommutationAwareReplayError("cleanup fallback changed unitary schedule")
    if (
        measured.get("variant") != "commutation_aware_measured_cleanup"
        or measured.get("proposed_cleanup_count") != len(cleanup_rows)
        or measured.get("removed_cleanup_ccx_count") != 0
        or measured.get("cleanup_axis_safe") is not False
        or measured.get("selected_for_z_x_only_high_rate_analysis") is not False
        or measured.get("fallback_variant") != "commutation_aware_unitary"
        or measured.get("outstanding_cleanup_outcome_count") != 0
        or measured.get("cleanup_frame_pair_interaction_count") != interactions
        or measured.get("maximum_cleanup_frame_contact_count") != max_contact
    ):
        raise Width256CommutationAwareReplayError("cleanup fail-closed record mismatch")
    cnot_demands = Counter(gate.algorithmic_layer for gate in source_cnot)
    bridge = []
    for width in range(2, 9):
        small = build_oop_qcla_trace(width)
        all_small = tuple(
            gate for gate in small.gates if gate.kind is QclaGateKind.TOFFOLI
        )
        measured_small = tuple(
            gate
            for gate in all_small
            if gate.stage is not OopQclaStage.PREFIX_UNCOMPUTE
        )
        _, all_groups, _, _ = _oracle_nodes_and_summary(small, all_small)
        _, measured_groups, _, _ = _oracle_nodes_and_summary(
            small, measured_small
        )
        bridge.append([width, len(all_groups), len(measured_groups)])
    if (
        raw.get("task_id") != "T-20260906-004"
        or raw.get("experiment_id") != "E-20260906-004"
        or raw.get("schema") != _SCHEMA
        or raw.get("schema_version") != 1
        or raw.get("width") != 256
        or raw.get("source_trace_id") != trace.trace_id
        or raw.get("source_trace_sha256")
        != hashlib.sha256(dumps_oop_qcla_trace(trace).encode("utf-8")).hexdigest().upper()
        or raw.get("source_ccx_count") != len(source_ccx)
        or raw.get("source_cnot_count") != len(source_cnot)
        or raw.get("source_toffoli_bearing_layers") != len(
            {gate.algorithmic_layer for gate in source_ccx}
        )
        or raw.get("source_aligned_candidate_levels") != 34
        or list(
            _sequence(raw.get("source_cnot_layer_demands"), label="CNOT demand")
        )
        != [[layer, count] for layer, count in sorted(cnot_demands.items())]
        or list(
            _sequence(raw.get("compact_bridge_widths_2_to_8"), label="bridge")
        )
        != bridge
        or raw.get("selected_variant") != "commutation_aware_unitary"
        or raw.get("validation_status") != "pending_independent_replay"
    ):
        raise Width256CommutationAwareReplayError("study headline mismatch")
    return Width256CommutationAwareReplaySummary(
        width=256,
        source_ccx_count=len(source_ccx),
        source_cnot_count=len(source_cnot),
        full_pair_count_checked=int(str(pair_summary["pair_count"])),
        compact_dependency_nodes_checked=len(nodes),
        unitary_macro_depth=macro_depth,
        unitary_candidate_levels=2 * macro_depth,
        candidate_support_levels_checked=len(expected_support),
        candidate_support_profiles_recomputed=sum(
            int(str(item["logical_ppm_count"])) for item in expected_support
        ),
        cleanup_candidates_checked=len(cleanup_rows),
        cleanup_mixed_axis_witnesses_checked=sum(
            bool(_mapping(item["axis_witness"], label="axis witness")["mixed_axis"])
            for item in cleanup_rows
        ),
        cleanup_candidates_admitted=0,
        selected_variant="commutation_aware_unitary",
        native_outputs_null=True,
        all_passed=True,
    )


def width256_commutation_aware_replay_to_data(
    summary: Width256CommutationAwareReplaySummary,
) -> dict[str, Any]:
    """Serialize replay counts."""

    return asdict(summary)
