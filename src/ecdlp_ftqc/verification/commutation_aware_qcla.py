"""Independent replay for the widths-2--8 commutation-aware QCLA study.

This module deliberately imports neither the commutation-aware scheduler nor
the joint direct-CCZ compiler.  It reconstructs pair commutation, barriers,
the exact longest-path schedule, cleanup lifetimes, and arithmetic semantics
from the reviewed source trace and serialized data.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations, pairwise, product
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGateKind
from ecdlp_ftqc.circuits.qcla_oop import (
    OopQclaGate,
    OopQclaStage,
    OopQclaTrace,
    build_oop_qcla_trace,
    dumps_oop_qcla_trace,
)

_SCHEMA = "ecdlp-ftqc/commutation-aware-clean-oop-qcla-small-width"
_SCHEMA_VERSION = 1
_COORDINATE = (
    "architecture_independent_two_phase_direct_ccz_candidate_levels_not_time"
)


class CommutationAwareQclaReplayError(ValueError):
    """Raised when serialized scheduling evidence fails independent replay."""


@dataclass(frozen=True, slots=True)
class VariantReplaySummary:
    """Independent results for one width and one variant."""

    variant: str
    width: int
    scheduled_ccx_count: int
    pair_count_checked: int
    pair_truth_table_rows_checked: int
    dependency_count_checked: int
    reaction_boundary_count: int
    retained_reaction_outcome_token_count: int
    macro_depth: int
    direct_ccz_candidate_levels: int
    exact_lower_bound_macro_depth: int
    arithmetic_inputs_checked: int
    arithmetic_mismatches: int
    measured_cleanup_count: int
    measurement_branch_columns_checked: int
    phase_sensitive_relative_pairs_checked: int
    cleanup_lifecycle_checks: int
    cleanup_frame_propagating_gate_count: int
    cleanup_final_support_union: tuple[str, ...]
    all_passed: bool


@dataclass(frozen=True, slots=True)
class WidthReplaySummary:
    """Source baseline and both alternatives for one width."""

    width: int
    source_ccx_count: int
    source_toffoli_bearing_layers: int
    source_aligned_candidate_levels: int
    source_trace_hash_matched: bool
    unitary: VariantReplaySummary
    measured_cleanup: VariantReplaySummary
    all_passed: bool


@dataclass(frozen=True, slots=True)
class SmallWidthCommutationAwareReplaySummary:
    """Aggregate independent replay result."""

    widths_checked: tuple[int, ...]
    width_summaries: tuple[WidthReplaySummary, ...]
    total_pair_decisions_checked: int
    total_pair_truth_table_rows_checked: int
    total_arithmetic_inputs_checked: int
    total_measurement_branch_columns_checked: int
    total_phase_sensitive_relative_pairs_checked: int
    width5_source_aligned_candidate_levels: int
    width5_unitary_macro_depth: int
    width5_unitary_candidate_levels: int
    width5_measured_macro_depth: int
    width5_measured_candidate_levels: int
    complete_native_schedule: bool
    native_cycles: None
    runtime_seconds: None
    physical_qubits: None
    failure_probability: None
    all_passed: bool


@dataclass(frozen=True, slots=True)
class _Operation:
    gate_id: str
    controls: tuple[str, str]
    target: str
    source_layer: int
    stage: str

    @property
    def support(self) -> tuple[str, str, str]:
        return (*self.controls, self.target)


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CommutationAwareQclaReplayError(f"{label} must be an object")
    return value


def _sequence(value: object, *, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CommutationAwareQclaReplayError(f"{label} must be an array")
    return value


def _strings(value: object, *, label: str) -> tuple[str, ...]:
    items = _sequence(value, label=label)
    if any(not isinstance(item, str) for item in items):
        raise CommutationAwareQclaReplayError(f"{label} must contain strings")
    return tuple(item for item in items if isinstance(item, str))


def _integer(value: object, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CommutationAwareQclaReplayError(f"{label} must be an integer")
    return value


def _operation(gate: OopQclaGate) -> _Operation:
    if gate.kind is not QclaGateKind.TOFFOLI:
        raise CommutationAwareQclaReplayError("non-CCX gate in operation set")
    return _Operation(
        gate_id=gate.gate_id,
        controls=(gate.controls[0], gate.controls[1]),
        target=gate.target,
        source_layer=gate.algorithmic_layer,
        stage=gate.stage.value,
    )


def _apply(operation: _Operation, state: dict[str, int]) -> None:
    state[operation.target] ^= state[operation.controls[0]] & state[operation.controls[1]]


def _overlap_kind(left: _Operation, right: _Operation) -> str:
    left_target_in_right = left.target in right.controls
    right_target_in_left = right.target in left.controls
    if left_target_in_right and right_target_in_left:
        return "bidirectional_target_control"
    if left_target_in_right:
        return "left_target_right_control"
    if right_target_in_left:
        return "right_target_left_control"
    if left.target == right.target:
        return "shared_target"
    if set(left.controls) & set(right.controls):
        return "shared_control"
    return "disjoint"


def _commutation_truth_table(
    left: _Operation, right: _Operation
) -> tuple[bool, int]:
    names = tuple(sorted(set(left.support) | set(right.support)))
    commutes = True
    for bits in product((0, 1), repeat=len(names)):
        initial = dict(zip(names, bits, strict=True))
        left_then_right = dict(initial)
        _apply(left, left_then_right)
        _apply(right, left_then_right)
        right_then_left = dict(initial)
        _apply(right, right_then_left)
        _apply(left, right_then_left)
        if left_then_right != right_then_left:
            commutes = False
    return commutes, 1 << len(names)


def _barriers(trace: OopQclaTrace) -> tuple[tuple[int, tuple[str, ...]], ...]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            grouped[gate.algorithmic_layer].append(gate.gate_id)
    return tuple((layer, tuple(grouped[layer])) for layer in sorted(grouped))


def _expected_pair_rows(
    trace: OopQclaTrace, operations: tuple[_Operation, ...]
) -> tuple[list[dict[str, object]], int]:
    cnot_layers = tuple(layer for layer, _ in _barriers(trace))
    result: list[dict[str, object]] = []
    truth_rows = 0
    for left, right in combinations(operations, 2):
        commutes, checked = _commutation_truth_table(left, right)
        truth_rows += checked
        barrier_layers = tuple(
            layer
            for layer in cnot_layers
            if left.source_layer < layer < right.source_layer
        )
        reasons: list[str] = []
        if not commutes:
            reasons.append("noncommuting_target_control")
        if barrier_layers:
            reasons.append("source_clifford_barrier")
        result.append(
            {
                "commutes": commutes,
                "dependency_reasons": reasons,
                "evidence_status": "PROVED",
                "left_source_gate_id": left.gate_id,
                "overlap_kind": _overlap_kind(left, right),
                "right_source_gate_id": right.gate_id,
                "same_macro_admitted": not reasons and commutes,
                "shared_values": sorted(set(left.support) & set(right.support)),
                "source_clifford_barrier_layers": list(barrier_layers),
                "truth_table_rows_checked": checked,
            }
        )
    return result, truth_rows


def _expected_dependencies(
    pair_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "predecessor": row["left_source_gate_id"],
            "reasons": row["dependency_reasons"],
            "shared_values": row["shared_values"],
            "source_clifford_barrier_layers": row[
                "source_clifford_barrier_layers"
            ],
            "successor": row["right_source_gate_id"],
        }
        for row in pair_rows
        if row["dependency_reasons"]
    ]


def _exact_groups_and_path(
    operations: tuple[_Operation, ...],
    dependencies: Sequence[Mapping[str, object]],
) -> tuple[tuple[tuple[str, ...], ...], tuple[str, ...]]:
    predecessor_map: dict[str, list[str]] = defaultdict(list)
    for dependency in dependencies:
        predecessor = dependency["predecessor"]
        successor = dependency["successor"]
        if not isinstance(predecessor, str) or not isinstance(successor, str):
            raise CommutationAwareQclaReplayError("dependency IDs must be strings")
        predecessor_map[successor].append(predecessor)
    position = {operation.gate_id: index for index, operation in enumerate(operations)}
    depth: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    for operation in operations:
        predecessors = predecessor_map[operation.gate_id]
        if not predecessors:
            depth[operation.gate_id] = 1
            parent[operation.gate_id] = None
        else:
            selected = max(
                predecessors, key=lambda item: (depth[item], -position[item])
            )
            depth[operation.gate_id] = depth[selected] + 1
            parent[operation.gate_id] = selected
    maximum = max(depth.values(), default=0)
    groups = tuple(
        tuple(
            operation.gate_id
            for operation in operations
            if depth[operation.gate_id] == layer
        )
        for layer in range(1, maximum + 1)
    )
    if not operations:
        return groups, ()
    endpoint = max(
        operations,
        key=lambda item: (depth[item.gate_id], -position[item.gate_id]),
    ).gate_id
    path: list[str] = []
    cursor: str | None = endpoint
    while cursor is not None:
        path.append(cursor)
        cursor = parent[cursor]
    path.reverse()
    return groups, tuple(path)


def _expected_cleanup_rows(
    trace: OopQclaTrace, removed: tuple[OopQclaGate, ...]
) -> list[dict[str, object]]:
    positions = {gate.gate_id: index for index, gate in enumerate(trace.gates)}
    removed_ids = {gate.gate_id for gate in removed}
    rows: list[dict[str, object]] = []
    for cleanup in removed:
        index = positions[cleanup.gate_id]
        producer = next(
            (
                gate
                for gate in trace.gates[:index]
                if gate.kind is QclaGateKind.TOFFOLI
                and gate.stage is OopQclaStage.PREFIX_PROPAGATE
                and gate.controls == cleanup.controls
                and gate.target == cleanup.target
            ),
            None,
        )
        if producer is None:
            raise CommutationAwareQclaReplayError("cleanup producer is missing")
        prior_uses = tuple(
            gate
            for gate in trace.gates[:index]
            if cleanup.target in gate.logical_support and gate.gate_id != producer.gate_id
        )
        later_target_uses = tuple(
            gate
            for gate in trace.gates[index + 1 :]
            if cleanup.target in gate.logical_support
        )
        if not prior_uses or later_target_uses:
            raise CommutationAwareQclaReplayError("cleanup lifetime is invalid")
        suffix = tuple(
            gate
            for gate in trace.gates[index + 1 :]
            if gate.gate_id not in removed_ids
        )
        support = set(cleanup.controls)
        propagating: list[str] = []
        for gate in suffix:
            gate_support = set(gate.logical_support)
            if gate_support & support:
                propagating.append(gate.gate_id)
                support.update(gate_support)
        token = f"commutation-aware:n{trace.width}:{cleanup.gate_id}:outcome:x"
        rows.append(
            {
                "conditional_frame_update": (
                    f"CZ({cleanup.controls[0]},{cleanup.controls[1]})^{{{token}}}"
                ),
                "controls": list(cleanup.controls),
                "evidence_status": "NUMERICAL",
                "final_frame_support_upper_bound": sorted(support),
                "frame_propagating_gate_ids": propagating,
                "last_quantum_use_source_gate_id": prior_uses[-1].gate_id,
                "later_ppm_source_gate_ids": [
                    gate.gate_id
                    for gate in suffix
                    if gate.kind is QclaGateKind.TOFFOLI
                ],
                "later_source_gate_ids": [gate.gate_id for gate in suffix],
                "measured_target": cleanup.target,
                "measurement_operation_id": (
                    f"commutation-aware:n{trace.width}:{cleanup.gate_id}:measure-x"
                ),
                "outcome_token": token,
                "producer_source_gate_id": producer.gate_id,
                "release_count": 1,
                "source_gate_id_replaced": cleanup.gate_id,
            }
        )
    return rows


def _expected_reaction_boundaries(
    width: int, groups: tuple[tuple[str, ...], ...]
) -> list[dict[str, object]]:
    roles = ("zz_0", "zz_1", "zz_2", "x_0", "x_1", "x_2")
    return [
        {
            "after_macro_layer": index,
            "before_macro_layer": index + 1,
            "duration_seconds": None,
            "outcome_subset_status": "CHECK",
            "predecessor_outcome_tokens": [
                f"commutation-aware:n{width}:{gate_id}:outcome:{role}"
                for gate_id in left
                for role in roles
            ],
            "predecessor_source_gate_ids": list(left),
            "reason": "common_frame_update_required_before_next_macro_entry",
            "successor_source_gate_ids": list(right),
        }
        for index, (left, right) in enumerate(
            pairwise(groups), start=1
        )
    ]


def _initial_state(trace: OopQclaTrace, input_a: int, input_b: int) -> dict[str, int]:
    state: dict[str, int] = {}
    for index in range(trace.width):
        state[f"a:{index}"] = (input_a >> index) & 1
        state[f"b:{index}"] = (input_b >> index) & 1
        state[f"z:{index}"] = 0
    for interval in trace.ancilla_intervals:
        state[interval.value_id] = 0
    return state


def _apply_gate(gate: OopQclaGate, state: dict[str, int]) -> None:
    fire = 1
    for control in gate.controls:
        fire &= state[control]
    state[gate.target] ^= fire


def _execute_reordered(
    trace: OopQclaTrace,
    macro_groups: tuple[tuple[str, ...], ...],
    removed: tuple[OopQclaGate, ...],
    input_a: int,
    input_b: int,
) -> tuple[dict[str, int], tuple[tuple[int, int], ...]]:
    by_id = {gate.gate_id: gate for gate in trace.gates}
    cnot_barriers = _barriers(trace)
    cnot_layers = tuple(layer for layer, _ in cnot_barriers)
    grouped_by_segment: dict[int, list[tuple[str, ...]]] = defaultdict(list)
    for group in macro_groups:
        segments = {
            sum(layer < by_id[gate_id].algorithmic_layer for layer in cnot_layers)
            for gate_id in group
        }
        if len(segments) != 1:
            raise CommutationAwareQclaReplayError(
                "macro-layer crosses a source Clifford barrier"
            )
        grouped_by_segment[segments.pop()].append(group)
    state = _initial_state(trace, input_a, input_b)
    cleanup_values: tuple[tuple[int, int], ...] = ()
    removed_ids = {gate.gate_id for gate in removed}
    cleanup_layer = max((gate.algorithmic_layer for gate in removed), default=None)
    cleanup_captured = False
    for segment in range(len(cnot_layers) + 1):
        for group in grouped_by_segment[segment]:
            for gate_id in group:
                _apply_gate(by_id[gate_id], state)
        if segment < len(cnot_layers):
            barrier_layer, barrier_gate_ids = cnot_barriers[segment]
            if (
                cleanup_layer is not None
                and not cleanup_captured
                and cleanup_layer < barrier_layer
            ):
                cleanup_values = tuple(
                    (
                        state[gate.target],
                        state[gate.controls[0]] & state[gate.controls[1]],
                    )
                    for gate in removed
                )
                cleanup_captured = True
            for gate_id in barrier_gate_ids:
                if gate_id not in removed_ids:
                    _apply_gate(by_id[gate_id], state)
    if removed and not cleanup_captured:
        cleanup_values = tuple(
            (
                state[gate.target],
                state[gate.controls[0]] & state[gate.controls[1]],
            )
            for gate in removed
        )
    return state, cleanup_values


def _check_semantics(
    trace: OopQclaTrace,
    groups: tuple[tuple[str, ...], ...],
    removed: tuple[OopQclaGate, ...],
) -> tuple[int, int, int, int]:
    limit = 1 << trace.width
    input_count = 0
    mismatches = 0
    branch_columns = 0
    measured_targets = {gate.target for gate in removed}
    for input_a in range(limit):
        for input_b in range(limit):
            input_count += 1
            state, cleanup_values = _execute_reordered(
                trace, groups, removed, input_a, input_b
            )
            output_a = sum(state[f"a:{i}"] << i for i in range(trace.width))
            output_b = sum(state[f"b:{i}"] << i for i in range(trace.width))
            output_z = sum(state[f"z:{i}"] << i for i in range(trace.width))
            dirty = tuple(
                interval.value_id
                for interval in trace.ancilla_intervals
                if interval.value_id not in measured_targets and state[interval.value_id]
            )
            if (
                output_a != input_a
                or output_b != input_b
                or output_z != (input_a + input_b) % limit
                or dirty
            ):
                mismatches += 1
            if removed:
                for target_value, predicate in cleanup_values:
                    if target_value != predicate:
                        mismatches += 1
                for outcomes in product((0, 1), repeat=len(removed)):
                    phase = 0
                    for outcome, (target_value, predicate) in zip(
                        outcomes, cleanup_values, strict=True
                    ):
                        phase ^= outcome & target_value
                        phase ^= outcome & predicate
                    branch_columns += 1
                    if phase:
                        mismatches += 1
    relative_pairs = (
        (1 << len(removed)) * (input_count - 1) if removed else 0
    )
    return input_count, mismatches, branch_columns, relative_pairs


def _replay_variant(
    trace: OopQclaTrace,
    raw: Mapping[str, object],
    *,
    variant: str,
) -> VariantReplaySummary:
    source_ccx = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    removed = (
        tuple(gate for gate in source_ccx if gate.stage is OopQclaStage.PREFIX_UNCOMPUTE)
        if variant == "commutation_aware_measured_cleanup"
        else ()
    )
    removed_ids = {gate.gate_id for gate in removed}
    operations = tuple(_operation(gate) for gate in source_ccx if gate.gate_id not in removed_ids)
    pair_rows, truth_rows = _expected_pair_rows(trace, operations)
    serialized_pairs = [
        dict(_mapping(item, label="pair decision"))
        for item in _sequence(raw.get("pair_decisions"), label="pair decisions")
    ]
    if serialized_pairs != pair_rows:
        raise CommutationAwareQclaReplayError("pair decision mismatch")
    dependencies = _expected_dependencies(pair_rows)
    serialized_dependencies = [
        dict(_mapping(item, label="dependency"))
        for item in _sequence(raw.get("dependencies"), label="dependencies")
    ]
    if serialized_dependencies != dependencies:
        raise CommutationAwareQclaReplayError("dependency mismatch")
    expected_groups, expected_path = _exact_groups_and_path(operations, dependencies)
    layers = _sequence(raw.get("macro_layers"), label="macro layers")
    if len(layers) != len(expected_groups):
        raise CommutationAwareQclaReplayError("macro-depth mismatch")
    seen_resources: set[str] = set()
    serialized_groups: list[tuple[str, ...]] = []
    pair_lookup = {
        (str(row["left_source_gate_id"]), str(row["right_source_gate_id"])): row
        for row in pair_rows
    }
    positions = {operation.gate_id: index for index, operation in enumerate(operations)}
    for layer_index, (layer_value, expected_group) in enumerate(
        zip(layers, expected_groups, strict=True), start=1
    ):
        layer = _mapping(layer_value, label="macro layer")
        group = _strings(layer.get("source_gate_ids"), label="macro event IDs")
        if group != expected_group:
            raise CommutationAwareQclaReplayError("macro grouping mismatch")
        serialized_groups.append(group)
        for left, right in combinations(group, 2):
            ordered = (left, right) if positions[left] < positions[right] else (right, left)
            if not bool(pair_lookup[ordered]["same_macro_admitted"]):
                raise CommutationAwareQclaReplayError("illegal pair in macro-layer")
        if (
            layer.get("layer_index") != layer_index
            or layer.get("common_incoming_frame") != "macro_layer_entry_frame"
            or layer.get("phase_one_candidate_level") != 2 * layer_index - 1
            or layer.get("phase_two_candidate_level") != 2 * layer_index
            or layer.get("phase_one_axis") != "Z"
            or layer.get("phase_two_axis") != "X"
            or list(
                _sequence(
                    layer.get("event_to_event_reaction_edges"),
                    label="reaction edges",
                )
            )
        ):
            raise CommutationAwareQclaReplayError("macro-layer metadata mismatch")
        triples = _sequence(layer.get("resource_triples"), label="resource triples")
        if len(triples) != len(group):
            raise CommutationAwareQclaReplayError("resource triple count mismatch")
        for gate_id, triple_value in zip(group, triples, strict=True):
            triple = _strings(triple_value, label="resource triple")
            prefix = f"commutation-aware:n{trace.width}:{gate_id}:ccz-resource"
            if triple != (f"{prefix}:0", f"{prefix}:1", f"{prefix}:2"):
                raise CommutationAwareQclaReplayError("resource identity mismatch")
            if seen_resources & set(triple):
                raise CommutationAwareQclaReplayError("resource reuse detected")
            seen_resources.update(triple)
    if tuple(serialized_groups) != expected_groups:
        raise CommutationAwareQclaReplayError("schedule witness changed")
    reaction_rows = _expected_reaction_boundaries(trace.width, expected_groups)
    serialized_reactions = [
        dict(_mapping(item, label="reaction boundary"))
        for item in _sequence(
            raw.get("reaction_boundaries"), label="reaction boundaries"
        )
    ]
    if serialized_reactions != reaction_rows:
        raise CommutationAwareQclaReplayError("reaction boundary mismatch")
    cleanup_rows = _expected_cleanup_rows(trace, removed)
    serialized_cleanups = [
        dict(_mapping(item, label="cleanup"))
        for item in _sequence(raw.get("cleanup_records"), label="cleanup records")
    ]
    if serialized_cleanups != cleanup_rows:
        raise CommutationAwareQclaReplayError("cleanup record mismatch")
    macro_depth = len(expected_groups)
    if (
        raw.get("variant") != variant
        or raw.get("width") != trace.width
        or raw.get("scheduled_ccx_count") != len(operations)
        or raw.get("measured_cleanup_count") != len(removed)
        or raw.get("macro_depth") != macro_depth
        or raw.get("direct_ccz_candidate_levels") != 2 * macro_depth
        or raw.get("exact_lower_bound_macro_depth") != len(expected_path)
        or _strings(
            raw.get("critical_path_source_gate_ids"), label="critical path"
        )
        != expected_path
        or raw.get("optimality_status") != "PROVED"
        or raw.get("candidate_level_coordinate") != _COORDINATE
    ):
        raise CommutationAwareQclaReplayError("schedule headline mismatch")
    if (
        raw.get("complete_native_schedule") is not False
        or raw.get("native_cycles") is not None
        or raw.get("runtime_seconds") is not None
        or raw.get("physical_qubits") is not None
        or raw.get("failure_probability") is not None
    ):
        raise CommutationAwareQclaReplayError("finite-backend output must remain null")
    inputs, mismatches, branch_columns, relative_pairs = _check_semantics(
        trace, expected_groups, removed
    )
    frame_union = tuple(
        sorted(
            {
                value
                for row in cleanup_rows
                for value in _strings(
                    row["final_frame_support_upper_bound"], label="frame support"
                )
            }
        )
    )
    propagating_count = sum(
        len(_strings(row["frame_propagating_gate_ids"], label="propagating gates"))
        for row in cleanup_rows
    )
    all_passed = mismatches == 0
    return VariantReplaySummary(
        variant=variant,
        width=trace.width,
        scheduled_ccx_count=len(operations),
        pair_count_checked=len(pair_rows),
        pair_truth_table_rows_checked=truth_rows,
        dependency_count_checked=len(dependencies),
        reaction_boundary_count=len(reaction_rows),
        retained_reaction_outcome_token_count=sum(
            len(
                _strings(
                    row["predecessor_outcome_tokens"], label="reaction outcomes"
                )
            )
            for row in reaction_rows
        ),
        macro_depth=macro_depth,
        direct_ccz_candidate_levels=2 * macro_depth,
        exact_lower_bound_macro_depth=len(expected_path),
        arithmetic_inputs_checked=inputs,
        arithmetic_mismatches=mismatches,
        measured_cleanup_count=len(removed),
        measurement_branch_columns_checked=branch_columns,
        phase_sensitive_relative_pairs_checked=relative_pairs,
        cleanup_lifecycle_checks=len(cleanup_rows),
        cleanup_frame_propagating_gate_count=propagating_count,
        cleanup_final_support_union=frame_union,
        all_passed=all_passed,
    )


def _replay_width(raw: Mapping[str, object], expected_width: int) -> WidthReplaySummary:
    trace = build_oop_qcla_trace(expected_width)
    source_ccx = tuple(
        gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    grouped: dict[int, list[str]] = defaultdict(list)
    for gate in source_ccx:
        grouped[gate.algorithmic_layer].append(gate.gate_id)
    baseline_layers = tuple(tuple(grouped[layer]) for layer in sorted(grouped))
    digest = hashlib.sha256(dumps_oop_qcla_trace(trace).encode("utf-8")).hexdigest()
    serialized_baseline = tuple(
        _strings(item, label="source-aligned macro-layer")
        for item in _sequence(
            raw.get("source_aligned_macro_layers"), label="source-aligned layers"
        )
    )
    serialized_barriers = tuple(
        (
            _integer(
                _sequence(item, label="barrier row")[0], label="barrier layer"
            ),
            _strings(
                _sequence(item, label="barrier row")[1], label="barrier gate IDs"
            ),
        )
        for item in _sequence(
            raw.get("source_clifford_barriers"), label="source Clifford barriers"
        )
    )
    if (
        raw.get("width") != expected_width
        or raw.get("source_trace_id") != trace.trace_id
        or raw.get("source_trace_sha256") != digest
        or raw.get("source_ccx_count") != len(source_ccx)
        or raw.get("source_toffoli_bearing_layers") != len(baseline_layers)
        or raw.get("source_aligned_candidate_levels") != 2 * len(baseline_layers)
        or serialized_baseline != baseline_layers
        or serialized_barriers != _barriers(trace)
    ):
        raise CommutationAwareQclaReplayError("source baseline mismatch")
    unitary = _replay_variant(
        trace,
        _mapping(raw.get("unitary"), label="unitary schedule"),
        variant="commutation_aware_unitary",
    )
    measured = _replay_variant(
        trace,
        _mapping(raw.get("measured_cleanup"), label="measured schedule"),
        variant="commutation_aware_measured_cleanup",
    )
    all_passed = unitary.all_passed and measured.all_passed
    return WidthReplaySummary(
        width=expected_width,
        source_ccx_count=len(source_ccx),
        source_toffoli_bearing_layers=len(baseline_layers),
        source_aligned_candidate_levels=2 * len(baseline_layers),
        source_trace_hash_matched=True,
        unitary=unitary,
        measured_cleanup=measured,
        all_passed=all_passed,
    )


def replay_small_width_commutation_aware_study(
    data: Mapping[str, object],
) -> SmallWidthCommutationAwareReplaySummary:
    """Independently replay the complete serialized widths-2--8 study."""

    if (
        data.get("schema") != _SCHEMA
        or data.get("schema_version") != _SCHEMA_VERSION
        or data.get("task_id") != "T-20260906-003"
        or data.get("experiment_id") != "E-20260906-003"
    ):
        raise CommutationAwareQclaReplayError("study identity changed")
    widths = tuple(
        _integer(item, label="width")
        for item in _sequence(data.get("widths"), label="widths")
    )
    if widths != tuple(range(2, 9)):
        raise CommutationAwareQclaReplayError("width coverage changed")
    comparison_rows = _sequence(data.get("comparisons"), label="comparisons")
    if len(comparison_rows) != len(widths):
        raise CommutationAwareQclaReplayError("comparison count mismatch")
    summaries = tuple(
        _replay_width(_mapping(row, label="width comparison"), width)
        for width, row in zip(widths, comparison_rows, strict=True)
    )
    width5 = summaries[3]
    total_pairs = sum(
        row.unitary.pair_count_checked + row.measured_cleanup.pair_count_checked
        for row in summaries
    )
    total_truth_rows = sum(
        row.unitary.pair_truth_table_rows_checked
        + row.measured_cleanup.pair_truth_table_rows_checked
        for row in summaries
    )
    total_inputs = sum(
        row.unitary.arithmetic_inputs_checked
        + row.measured_cleanup.arithmetic_inputs_checked
        for row in summaries
    )
    total_branches = sum(
        row.measured_cleanup.measurement_branch_columns_checked for row in summaries
    )
    total_relative = sum(
        row.measured_cleanup.phase_sensitive_relative_pairs_checked
        for row in summaries
    )
    all_passed = all(row.all_passed for row in summaries)
    return SmallWidthCommutationAwareReplaySummary(
        widths_checked=widths,
        width_summaries=summaries,
        total_pair_decisions_checked=total_pairs,
        total_pair_truth_table_rows_checked=total_truth_rows,
        total_arithmetic_inputs_checked=total_inputs,
        total_measurement_branch_columns_checked=total_branches,
        total_phase_sensitive_relative_pairs_checked=total_relative,
        width5_source_aligned_candidate_levels=(
            width5.source_aligned_candidate_levels
        ),
        width5_unitary_macro_depth=width5.unitary.macro_depth,
        width5_unitary_candidate_levels=width5.unitary.direct_ccz_candidate_levels,
        width5_measured_macro_depth=width5.measured_cleanup.macro_depth,
        width5_measured_candidate_levels=(
            width5.measured_cleanup.direct_ccz_candidate_levels
        ),
        complete_native_schedule=False,
        native_cycles=None,
        runtime_seconds=None,
        physical_qubits=None,
        failure_probability=None,
        all_passed=all_passed,
    )


def commutation_aware_qcla_replay_to_data(
    summary: SmallWidthCommutationAwareReplaySummary,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible replay data."""

    return asdict(summary)
