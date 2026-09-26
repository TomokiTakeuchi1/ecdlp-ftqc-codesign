"""Independent replay of the width-256 in-place commutation-aware study."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
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
from ecdlp_ftqc.scheduler import direct_ccz_ppm_support_certificate as support_model

_SCHEMA = "ecdlp-ftqc/width256-commutation-aware-inplace-mod2n-qcla"
_COORDINATE = (
    "architecture_independent_two_phase_direct_ccz_candidate_levels_not_time"
)
_SAMPLE_COUNT = 512
_SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"


class Width256IpCommutationAwareReplayError(ValueError):
    """Raised when serialized IP evidence does not replay."""


@dataclass(frozen=True, slots=True)
class Width256IpCommutationAwareReplaySummary:
    """Counts independently reconstructed from source and event traces."""

    width: int
    source_gate_count: int
    source_ccx_count: int
    source_cnot_count: int
    source_x_count: int
    full_pair_count_checked: int
    dependency_nodes_checked: int
    macro_depth: int
    candidate_levels: int
    candidate_support_profiles_recomputed: int
    bounded_support_level_count: int
    coherent_cleanup_ccx_count: int
    small_width_basis_rows_checked: int
    deterministic_branch_sample_count: int
    native_outputs_null: bool
    all_passed: bool


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise Width256IpCommutationAwareReplayError(f"{label} must be a mapping")
    return value


def _sequence(value: object, *, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise Width256IpCommutationAwareReplayError(f"{label} must be a sequence")
    return value


def _strings(value: object, *, label: str) -> tuple[str, ...]:
    sequence = _sequence(value, label=label)
    if any(not isinstance(item, str) for item in sequence):
        raise Width256IpCommutationAwareReplayError(f"{label} must contain strings")
    return tuple(str(item) for item in sequence)


def _barriers(trace: QclaTrace) -> tuple[tuple[int, tuple[str, ...]], ...]:
    grouped: dict[int, set[str]] = defaultdict(set)
    for gate in trace.gates:
        if gate.kind is not QclaGateKind.TOFFOLI:
            grouped[gate.algorithmic_layer].add(gate.kind.value)
    return tuple((layer, tuple(sorted(grouped[layer]))) for layer in sorted(grouped))


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


def _oracle(
    trace: QclaTrace,
    gates: tuple[QclaGate, ...],
) -> tuple[list[dict[str, object]], list[list[str]], tuple[str, ...], dict[str, object]]:
    barriers = _barriers(trace)
    counts: Counter[str] = Counter()
    stream = hashlib.sha256()
    ranks: list[int] = []
    parents: list[int | None] = []
    nodes: list[dict[str, object]] = []
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
            stream.update(
                (
                    f"{left.gate_id}|{right.gate_id}|{overlap}|"
                    f"{','.join(str(layer) for layer, _ in crossed)}|"
                    f"{','.join(sorted(kinds))}|{int(dependency)}\n"
                ).encode()
            )
            if dependency:
                candidates.append(left_index)
        parent = max(candidates, key=lambda item: (ranks[item], -item), default=None)
        rank = 1 if parent is None else ranks[parent] + 1
        ranks.append(rank)
        parents.append(parent)
        crossed = (
            ()
            if parent is None
            else tuple(
                (layer, kinds)
                for layer, kinds in barriers
                if gates[parent].algorithmic_layer
                < layer
                < right.algorithmic_layer
            )
        )
        reasons: list[str] = []
        if parent is not None:
            commutes, _ = _relation(gates[parent], right)
            if not commutes:
                reasons.append("noncommuting_target_control")
            if crossed:
                reasons.append("source_clifford_barrier")
        nodes.append(
            {
                "controls": list(right.controls),
                "macro_rank": rank,
                "segment_index": sum(
                    layer < right.algorithmic_layer for layer, _ in barriers
                ),
                "source_algorithmic_layer": right.algorithmic_layer,
                "source_direction": right.direction.value,
                "source_gate_id": right.gate_id,
                "source_position": right_index,
                "source_stage": right.stage.value,
                "source_step": right.source_step,
                "target": right.target,
                "witness_barrier_kinds": sorted(
                    {kind for _, kinds in crossed for kind in kinds}
                ),
                "witness_barrier_layers": [layer for layer, _ in crossed],
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
    summary: dict[str, object] = {
        "admitted_pair_count": counts["admitted"],
        "barrier_pair_count": counts["barrier"],
        "both_kind_barrier_pair_count": counts["both_barrier"],
        "cnot_barrier_pair_count": counts["cnot_barrier"],
        "compact_rank_match": True,
        "decision_stream_sha256": stream.hexdigest().upper(),
        "dependency_pair_count": counts["dependency"],
        "evidence_status": "PROVED",
        "noncommuting_pair_count": counts["noncommuting"],
        "operation_count": len(gates),
        "overlap_kind_counts": [
            [name, counts[name]]
            for name in (
                "disjoint",
                "shared_control",
                "shared_target",
                "left_target_right_control",
                "right_target_left_control",
                "bidirectional_target_control",
            )
        ],
        "pair_count": counts["pairs"],
        "pair_records_materialized": False,
        "x_barrier_pair_count": counts["x_barrier"],
    }
    return nodes, groups, tuple(path), summary


def _support_levels(
    trace: QclaTrace,
    event_trace: DirectCczEventTrace,
    groups: Sequence[Sequence[str]],
) -> list[dict[str, object]]:
    gates_by_id = {gate.gate_id: gate for gate in trace.gates}
    events = {event.source_gate_id: event for event in event_trace.injection_events}
    logical_values = tuple(
        sorted({value for gate in trace.gates for value in gate.logical_support})
    )
    all_mask = (1 << _SAMPLE_COUNT) - 1
    sampled = {value: {value: all_mask} for value in logical_values}
    may = {value: {value} for value in logical_values}
    cnot_by_layer: dict[int, list[QclaGate]] = defaultdict(list)
    barrier_layers = {layer for layer, _ in _barriers(trace)}
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            cnot_by_layer[gate.algorithmic_layer].append(gate)
    applied: set[int] = set()
    result: list[dict[str, object]] = []
    previous_lower = 0
    for macro_layer, raw_ids in enumerate(groups, start=1):
        gate_ids = tuple(str(item) for item in raw_ids)
        layer_gates = tuple(gates_by_id[item] for item in gate_ids)
        lower = min(gate.algorithmic_layer for gate in layer_gates)
        upper = max(gate.algorithmic_layer for gate in layer_gates)
        if lower < previous_lower or any(
            lower <= layer <= upper for layer in barrier_layers
        ):
            raise Width256IpCommutationAwareReplayError(
                "macro layer crosses or reverses a source barrier"
            )
        previous_lower = lower
        for layer in sorted(cnot_by_layer):
            if layer >= lower or layer in applied:
                continue
            for gate in cnot_by_layer[layer]:
                support_model._sampled_source_cnot_conjugate(
                    sampled, may, gate.controls[0], gate.target
                )
            applied.add(layer)
        by_phase: dict[int, list[support_model.PpmSupportProfile]] = {1: [], 2: []}
        maximum_sampled_weight = {1: 1, 2: 1}
        for gate in layer_gates:
            event = events[gate.gate_id]
            for index, data_value in enumerate(event.data):
                ppm = event.ppms[index]
                possible = tuple(sorted({event.resource[index], *may[data_value]}))
                masks = dict(sampled[data_value])
                masks[event.resource[index]] = all_mask
                maximum_sampled_weight[1] = max(
                    maximum_sampled_weight[1],
                    support_model._maximum_parallel_mask_weight(
                        tuple(masks.get(value, 0) for value in possible),
                        count=_SAMPLE_COUNT,
                    ),
                )
                exact = all(masks.get(value, 0) != 0 for value in possible)
                by_phase[1].append(
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
                                count=_SAMPLE_COUNT,
                            )
                            for value in possible
                        ),
                        possible_support_exact=exact,
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
                        activities=(support_model._constant_activity(resource_value),),
                    )
                )
        for phase in (1, 2):
            candidate_level = 2 * macro_layer - (2 - phase)
            batch = support_model._batch(
                tuple(by_phase[phase]), batch_level=candidate_level
            )
            exact = batch.evidence_status.value == "PROVED"
            result.append(
                {
                    "axis": {1: "Z", 2: "X"}[phase],
                    "branch_dependent_profile_count": (
                        batch.branch_dependent_profile_count
                    ),
                    "candidate_level": candidate_level,
                    "coordinate": support_model.SUPPORT_COORDINATE,
                    "deterministic_branch_sample_count": _SAMPLE_COUNT,
                    "deterministic_branch_sample_seed": _SAMPLE_SEED,
                    "direct_ccz_event_count": len(layer_gates),
                    "distinct_target_h_count": len(
                        {gate.target for gate in layer_gates}
                    ),
                    "evidence_status": "PROVED" if exact else "CHECK",
                    "fresh_ccz_resource_count": len(layer_gates),
                    "logical_ppm_count": batch.ppm_count,
                    "macro_layer": macro_layer,
                    "maximum_may_contact_count": (
                        batch.maximum_possible_contact_count
                    ),
                    "maximum_ppm_weight_upper_bound": (
                        batch.maximum_ppm_weight_upper_bound
                    ),
                    "maximum_sampled_branch_weight": (
                        maximum_sampled_weight[phase]
                    ),
                    "maximum_witnessed_contact_count": (
                        batch.maximum_witnessed_contact_count
                    ),
                    "may_support_union_sha256": (
                        batch.possible_support_union_sha256
                    ),
                    "may_support_union_upper_bound_size": len(
                        batch.possible_support_union
                    ),
                    "may_union_is_simultaneous_branch_weight": False,
                    "phase": phase,
                    "possible_support_exact": exact,
                    "source_algorithmic_layer_max": upper,
                    "source_algorithmic_layer_min": lower,
                    "source_gate_ids": list(gate_ids),
                    "total_may_support_incidence": (
                        batch.total_possible_support_incidence
                    ),
                    "total_witnessed_support_incidence": (
                        batch.total_witnessed_support_incidence
                    ),
                    "unwitnessed_may_incidence_count": (
                        batch.total_possible_support_incidence
                        - batch.total_witnessed_support_incidence
                    ),
                    "witnessed_support_union_lower_bound_size": len(
                        batch.witnessed_support_union
                    ),
                }
            )
        for gate in layer_gates:
            event = events[gate.gate_id]
            c0, c1, target = event.data
            support_model._sampled_conditional_column_xor(
                sampled,
                may,
                target,
                c1,
                support_model._sample_mask(
                    event.ppms[0].outcome_token,
                    count=_SAMPLE_COUNT,
                    seed=_SAMPLE_SEED,
                ),
            )
            support_model._sampled_conditional_column_xor(
                sampled,
                may,
                target,
                c0,
                support_model._sample_mask(
                    event.ppms[1].outcome_token,
                    count=_SAMPLE_COUNT,
                    seed=_SAMPLE_SEED,
                ),
            )
    return result


def _live_ancilla_data(trace: QclaTrace) -> dict[str, object]:
    metrics = qcla_metrics(trace)
    peak_layers = [
        layer
        for layer in range(1, metrics.source_layer_count + 1)
        if sum(
            interval.start_layer <= layer <= interval.end_layer
            for interval in trace.ancilla_intervals
        )
        == metrics.peak_live_ancillas
    ]
    return {
        "allocation_interval_count": len(trace.ancilla_intervals),
        "coordinate": "source_algorithmic_layer_liveness_not_macro_schedule",
        "fully_resident_source_values": 2 * trace.width + metrics.source_ancilla_count,
        "peak_live_source_ancillas": metrics.peak_live_ancillas,
        "peak_live_source_layers": peak_layers,
        "persistent_input_values": 2 * trace.width,
        "prefix_scratch_values": metrics.prefix_scratch_count,
        "source_ancilla_values": metrics.source_ancilla_count,
    }


def _verify_small_width_arithmetic() -> int:
    """Exhaustively replay widths 2--8 in the independently rebuilt gate order."""

    rows = 0
    for width in range(2, 9):
        trace = build_qcla_trace(width)
        ccx = tuple(
            gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
        )
        _, groups, _, _ = _oracle(trace, ccx)
        gate_by_id = {gate.gate_id: gate for gate in trace.gates}
        barriers = tuple(
            gate for gate in trace.gates if gate.kind is not QclaGateKind.TOFFOLI
        )
        applied_barriers: set[str] = set()
        reordered: list[QclaGate] = []
        for raw_group in groups:
            group = tuple(gate_by_id[gate_id] for gate_id in raw_group)
            lower = min(gate.algorithmic_layer for gate in group)
            for gate in barriers:
                if (
                    gate.algorithmic_layer < lower
                    and gate.gate_id not in applied_barriers
                ):
                    reordered.append(gate)
                    applied_barriers.add(gate.gate_id)
            reordered.extend(group)
        reordered.extend(
            gate for gate in barriers if gate.gate_id not in applied_barriers
        )
        if len(reordered) != len(trace.gates):
            raise Width256IpCommutationAwareReplayError(
                "small-width reordered trace lost a source gate"
            )
        values = {
            value
            for gate in trace.gates
            for value in gate.logical_support
        }
        for input_a in range(1 << width):
            for input_b in range(1 << width):
                state = {value: 0 for value in values}
                for bit in range(width):
                    state[f"a:{bit}"] = (input_a >> bit) & 1
                    state[f"b:{bit}"] = (input_b >> bit) & 1
                for gate in reordered:
                    if gate.kind is QclaGateKind.X:
                        state[gate.target] ^= 1
                    elif gate.kind is QclaGateKind.CNOT:
                        state[gate.target] ^= state[gate.controls[0]]
                    else:
                        state[gate.target] ^= (
                            state[gate.controls[0]] & state[gate.controls[1]]
                        )
                output_a = sum(state[f"a:{bit}"] << bit for bit in range(width))
                output_b = sum(state[f"b:{bit}"] << bit for bit in range(width))
                dirty = tuple(
                    value
                    for value, bit_value in state.items()
                    if not value.startswith(("a:", "b:")) and bit_value
                )
                if (
                    output_a != input_a
                    or output_b != (input_a + input_b) % (1 << width)
                    or dirty
                ):
                    raise Width256IpCommutationAwareReplayError(
                        "small-width reordered arithmetic replay failed"
                    )
                rows += 1
    return rows


def replay_width256_ip_commutation_aware_study(
    raw: Mapping[str, object],
    event_trace: DirectCczEventTrace,
) -> Width256IpCommutationAwareReplaySummary:
    """Rebuild the full pair oracle, sampled support envelopes, and source demand."""

    finite = (
        raw.get("native_cycles"),
        raw.get("runtime_seconds"),
        raw.get("physical_qubits"),
        raw.get("failure_probability"),
    )
    if raw.get("complete_native_schedule") is not False or any(
        value is not None for value in finite
    ):
        raise Width256IpCommutationAwareReplayError(
            "finite backend output must remain null"
        )
    trace = build_qcla_trace(256)
    if event_trace.source_trace_id != trace.trace_id:
        raise Width256IpCommutationAwareReplayError("event trace source mismatch")
    ccx = tuple(gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI)
    cnot = tuple(gate for gate in trace.gates if gate.kind is QclaGateKind.CNOT)
    x_gates = tuple(gate for gate in trace.gates if gate.kind is QclaGateKind.X)
    nodes, groups, path, pair_summary = _oracle(trace, ccx)
    if list(_sequence(raw.get("dependency_nodes"), label="dependency nodes")) != nodes:
        raise Width256IpCommutationAwareReplayError("dependency nodes mismatch")
    if list(_sequence(raw.get("macro_layers"), label="macro layers")) != groups:
        raise Width256IpCommutationAwareReplayError("macro grouping mismatch")
    if dict(_mapping(raw.get("pair_oracle"), label="pair oracle")) != pair_summary:
        raise Width256IpCommutationAwareReplayError("pair oracle mismatch")
    expected_levels = _support_levels(trace, event_trace, groups)
    raw_levels = list(_sequence(raw.get("candidate_levels"), label="support levels"))
    if raw_levels != expected_levels:
        raise Width256IpCommutationAwareReplayError("support envelope mismatch")
    if dict(_mapping(raw.get("live_ancillas"), label="live ancillas")) != _live_ancilla_data(trace):
        raise Width256IpCommutationAwareReplayError("source liveness mismatch")
    macro_depth = len(groups)
    bridge: list[list[int]] = []
    for width in range(2, 9):
        small = build_qcla_trace(width)
        small_ccx = tuple(
            gate for gate in small.gates if gate.kind is QclaGateKind.TOFFOLI
        )
        _, small_groups, _, _ = _oracle(small, small_ccx)
        bridge.append(
            [
                width,
                len({gate.algorithmic_layer for gate in small_ccx}),
                len(small_groups),
            ]
        )
    clifford_demands = Counter(
        (gate.algorithmic_layer, gate.kind.value)
        for gate in trace.gates
        if gate.kind is not QclaGateKind.TOFFOLI
    )
    expected_cliffords = [
        [layer, kind, count]
        for (layer, kind), count in sorted(clifford_demands.items())
    ]
    metrics = qcla_metrics(trace)
    peak_events = max(len(group) for group in groups)
    peak_targets = max(
        len({next(gate for gate in ccx if gate.gate_id == gate_id).target for gate_id in group})
        for group in groups
    )
    bounded_levels = sum(
        _mapping(item, label="support level").get("possible_support_exact") is False
        for item in raw_levels
    )
    if (
        raw.get("task_id") != "T-20260907-001"
        or raw.get("experiment_id") != "E-20260907-001"
        or raw.get("schema") != _SCHEMA
        or raw.get("schema_version") != 1
        or raw.get("validation_status") != "pending_independent_replay"
        or raw.get("width") != 256
        or raw.get("arithmetic_contract") != trace.arithmetic_contract
        or raw.get("source_trace_id") != trace.trace_id
        or raw.get("source_trace_sha256")
        != hashlib.sha256(dumps_qcla_trace(trace).encode("utf-8")).hexdigest().upper()
        or raw.get("source_gate_count") != metrics.gate_count
        or raw.get("source_ccx_count") != len(ccx)
        or raw.get("source_cnot_count") != len(cnot)
        or raw.get("source_x_count") != len(x_gates)
        or raw.get("source_layer_count") != metrics.source_layer_count
        or raw.get("source_toffoli_bearing_layers") != 34
        or raw.get("source_aligned_candidate_levels") != 68
        or raw.get("coherent_cleanup_ccx_count")
        != sum(gate.source_step >= 7 for gate in ccx)
        or list(
            _sequence(
                raw.get("source_clifford_layer_demands"),
                label="Clifford demand",
            )
        )
        != expected_cliffords
        or list(
            _sequence(raw.get("compact_bridge_widths_2_to_8"), label="bridge")
        )
        != bridge
        or raw.get("macro_depth") != macro_depth
        or raw.get("exact_lower_bound_macro_depth") != len(path)
        or _strings(raw.get("critical_path_source_gate_ids"), label="critical path")
        != path
        or raw.get("direct_ccz_candidate_levels") != 2 * macro_depth
        or raw.get("retained_inter_macro_outcome_count")
        != sum(6 * len(group) for group in groups[:-1])
        or raw.get("total_target_h_count") != 2 * len(ccx)
        or raw.get("peak_distinct_target_h_count") != peak_targets
        or raw.get("peak_fresh_ccz_resource_count") != peak_events
        or raw.get("cleanup_policy") != "coherent_reverse_network_retained"
        or raw.get("support_envelope_status")
        != ("CHECK" if bounded_levels else "PROVED")
        or raw.get("optimality_status") != "PROVED"
        or raw.get("candidate_coordinate") != _COORDINATE
    ):
        raise Width256IpCommutationAwareReplayError("study headline mismatch")
    small_width_rows = _verify_small_width_arithmetic()
    return Width256IpCommutationAwareReplaySummary(
        width=256,
        source_gate_count=metrics.gate_count,
        source_ccx_count=len(ccx),
        source_cnot_count=len(cnot),
        source_x_count=len(x_gates),
        full_pair_count_checked=int(str(pair_summary["pair_count"])),
        dependency_nodes_checked=len(nodes),
        macro_depth=macro_depth,
        candidate_levels=2 * macro_depth,
        candidate_support_profiles_recomputed=6 * len(ccx),
        bounded_support_level_count=bounded_levels,
        coherent_cleanup_ccx_count=sum(gate.source_step >= 7 for gate in ccx),
        small_width_basis_rows_checked=small_width_rows,
        deterministic_branch_sample_count=_SAMPLE_COUNT,
        native_outputs_null=True,
        all_passed=True,
    )


def width256_ip_commutation_aware_replay_to_data(
    replay: Width256IpCommutationAwareReplaySummary,
) -> dict[str, Any]:
    """Serialize the independent replay summary."""

    return asdict(replay)
