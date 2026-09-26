"""Independent structural replay for partial Clifford-frame clearing studies."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from ecdlp_ftqc.circuits import build_qcla_trace
from ecdlp_ftqc.circuits.qcla import QclaGateKind


class PartialFrameClearingReplayError(ValueError):
    """Raised when a stored partial-clearing study fails replay."""


@dataclass(frozen=True, slots=True)
class PartialFrameClearingReplaySummary:
    """Compact outcome of the independent structural replay."""

    widths: tuple[int, ...]
    source_ccx_counts: tuple[int, ...]
    macro_depths: tuple[int, ...]
    distribution_vectors_checked: int
    distribution_values_checked: int
    width5_projective_checks: int
    all_passed: bool


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PartialFrameClearingReplayError(message)


def _as_mapping(value: object, *, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} must be a mapping")
    return cast(Mapping[str, Any], value)


def _as_sequence(value: object, *, label: str) -> Sequence[Any]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes)),
        f"{label} must be a sequence",
    )
    return cast(Sequence[Any], value)


def _integer(value: object, *, label: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool), f"{label} must be integer")
    return cast(int, value)


def _nearest_rank(values: tuple[int, ...], probability: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def _replay_distribution(
    raw: object,
    *,
    count: int,
    label: str,
) -> tuple[int, ...]:
    row = _as_mapping(raw, label=label)
    values = tuple(
        _integer(item, label=f"{label}.values[]")
        for item in _as_sequence(row.get("values"), label=f"{label}.values")
    )
    _require(len(values) == count, f"{label} branch count changed")
    expected = {
        "minimum": min(values),
        "p50": _nearest_rank(values, 0.50),
        "p95": _nearest_rank(values, 0.95),
        "p99": _nearest_rank(values, 0.99),
        "maximum": max(values),
        "all_zero_branch": values[0],
        "all_one_branch": values[1],
        "sha256": hashlib.sha256(json.dumps(values, separators=(",", ":")).encode())
        .hexdigest()
        .upper(),
    }
    for key, value in expected.items():
        _require(row.get(key) == value, f"{label}.{key} changed")
    return values


def _independent_macro_layers(width: int) -> tuple[tuple[str, ...], ...]:
    """Complete-pair replay of the reviewed IP commutation/barrier rule."""

    trace = build_qcla_trace(width)
    gates = tuple(gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI)
    barrier_layers = tuple(
        sorted(
            {
                gate.algorithmic_layer
                for gate in trace.gates
                if gate.kind is not QclaGateKind.TOFFOLI
            }
        )
    )
    ranks: list[int] = []
    for right_index, right in enumerate(gates):
        predecessor_indices: list[int] = []
        for left_index, left in enumerate(gates[:right_index]):
            target_control_conflict = left.target in right.controls or right.target in left.controls
            crosses_barrier = any(
                left.algorithmic_layer < layer < right.algorithmic_layer for layer in barrier_layers
            )
            if target_control_conflict or crosses_barrier:
                predecessor_indices.append(left_index)
        rank = 1 + max(
            (ranks[index] for index in predecessor_indices),
            default=0,
        )
        ranks.append(rank)
    return tuple(
        tuple(gate.gate_id for gate, rank in zip(gates, ranks, strict=True) if rank == layer)
        for layer in range(1, max(ranks, default=0) + 1)
    )


_DISTRIBUTION_FIELDS = (
    "literal_cnot_occurrences",
    "literal_cz_occurrences",
    "literal_cnot_batches",
    "literal_two_qubit_batches",
    "serialized_logical_layer_envelope",
    "maximum_presented_ppm_weight",
    "incompatible_phase_one_ppm_count",
    "y_containing_phase_one_ppm_count",
    "maximum_frame_primitive_count",
    "final_frame_primitive_count",
)


def replay_partial_frame_clearing_studies(
    records: Sequence[Mapping[str, Any]],
) -> PartialFrameClearingReplaySummary:
    """Replay source schedules, distribution summaries, and claim boundaries."""

    _require(len(records) == 2, "replay requires width-5 and width-256 records")
    by_width = {_integer(row.get("width"), label="width"): row for row in records}
    _require(set(by_width) == {5, 256}, "width coverage changed")
    distribution_vectors = 0
    distribution_values = 0
    source_ccx_counts: list[int] = []
    macro_depths: list[int] = []
    width5_checks = 0
    expected_policies = {
        "full_frame_conjugation",
        "bare_h_frame_propagation",
        "h_frame_tracking",
        "full_frame_clearing",
        "target_component_partial_clearing",
    }

    for width in (5, 256):
        row = by_width[width]
        _require(row.get("task_id") == "T-20260909-001", "task ID changed")
        _require(row.get("experiment_id") == "E-20260909-001", "experiment ID changed")
        _require(
            row.get("schema") == "ecdlp-ftqc/qcla-partial-frame-clearing-study"
            and row.get("schema_version") == 1,
            "study schema changed",
        )
        _require(not bool(row.get("complete_native_schedule")), "native schedule appeared")
        _require(
            row.get("coordinate")
            == "logical_generator_ASAP_envelope_not_native_cycles_or_runtime",
            "logical/native coordinate changed",
        )
        _require(
            row.get("ordered_factorization_status") == "PROVED",
            "ordered factorization lost proved status",
        )
        _require(
            row.get("branch_sample_seed") == "T-20260903-002-support-witnesses-v1",
            "branch seed changed",
        )
        sample_count = _integer(row.get("branch_sample_count"), label="branch_sample_count")
        _require(sample_count >= 2, "forced branch witnesses disappeared")
        expected_layers = _independent_macro_layers(width)
        macro_depth = _integer(row.get("macro_depth"), label="macro_depth")
        _require(macro_depth == len(expected_layers), "macro depth changed")
        observed_sizes = tuple(
            _integer(item, label="macro_layer_sizes[]")
            for item in _as_sequence(row.get("macro_layer_sizes"), label="macro_layer_sizes")
        )
        _require(
            observed_sizes == tuple(len(layer) for layer in expected_layers),
            "macro layer sizes changed",
        )
        source_ccx_count = sum(observed_sizes)
        source_ccx_counts.append(source_ccx_count)
        macro_depths.append(macro_depth)

        policies = tuple(
            _as_mapping(item, label="policies[]")
            for item in _as_sequence(row.get("policies"), label="policies")
        )
        policy_by_name = {str(item.get("policy")): item for item in policies}
        _require(set(policy_by_name) == expected_policies, "policy coverage changed")
        policy_vectors: dict[str, dict[str, tuple[int, ...]]] = {}
        for name, policy in policy_by_name.items():
            _require(
                policy.get("candidate_ppm_levels") == 2 * macro_depth,
                f"{name} candidate depth changed",
            )
            _require(
                policy.get("native_scheduled_depth") is None
                and policy.get("runtime_seconds") is None,
                f"{name} acquired unsupported finite output",
            )
            _require(
                policy.get("evidence_status") == "NUMERICAL",
                f"{name} evidence status changed",
            )
            expected_h_batches = 0 if name == "h_frame_tracking" else 2 * macro_depth
            _require(
                policy.get("literal_h_batches") == expected_h_batches,
                f"{name} H batch count changed",
            )
            vectors: dict[str, tuple[int, ...]] = {}
            for field in _DISTRIBUTION_FIELDS:
                vectors[field] = _replay_distribution(
                    policy.get(field),
                    count=sample_count,
                    label=f"{width}.{name}.{field}",
                )
                distribution_vectors += 1
                distribution_values += sample_count
            admitted = max(vectors["incompatible_phase_one_ppm_count"]) == 0
            _require(
                bool(policy.get("z_x_only_high_rate_family_admitted")) == admitted,
                f"{name} axis admission changed",
            )
            policy_vectors[name] = vectors

        full_clear = policy_vectors["full_frame_clearing"]
        partial = policy_vectors["target_component_partial_clearing"]
        conjugated = policy_vectors["full_frame_conjugation"]
        _require(
            set(full_clear["maximum_presented_ppm_weight"]) == {2},
            "full clearing no longer presents weight-2 phase-one PPMs",
        )
        _require(
            max(partial["incompatible_phase_one_ppm_count"]) == 0,
            "partial clearing lost the Z-only invariant",
        )
        _require(
            all(
                candidate <= baseline
                for candidate, baseline in zip(
                    partial["maximum_presented_ppm_weight"],
                    conjugated["maximum_presented_ppm_weight"],
                    strict=True,
                )
            ),
            "partial clearing increased the sampled PPM maximum",
        )
        _require(
            all(
                candidate <= complete
                for candidate, complete in zip(
                    partial["literal_cnot_occurrences"],
                    full_clear["literal_cnot_occurrences"],
                    strict=True,
                )
            ),
            "partial clearing exceeded full-clearing CNOT count",
        )

        macro_rows = _as_sequence(row.get("partial_macro_profiles"), label="partial_macro_profiles")
        _require(len(macro_rows) == macro_depth, "partial macro coverage changed")
        for index, item in enumerate(macro_rows, start=1):
            macro = _as_mapping(item, label="partial_macro_profiles[]")
            _require(macro.get("macro_layer") == index, "macro order changed")
            _require(
                macro.get("ccx_count") == len(expected_layers[index - 1]),
                "macro CCX count changed",
            )
            for field in (
                "relevant_component_qubits",
                "materialized_cnot_occurrences",
                "retained_cnot_occurrences",
                "presented_ppm_maximum_weight",
            ):
                _replay_distribution(
                    macro.get(field),
                    count=sample_count,
                    label=f"{width}.macro{index}.{field}",
                )
                distribution_vectors += 1
                distribution_values += sample_count

        replay_branch_count = _integer(
            row.get("width5_replay_branch_count"),
            label="width5_replay_branch_count",
        )
        checks = _integer(
            row.get("width5_projective_clifford_checks"),
            label="width5_projective_clifford_checks",
        )
        mismatches = _integer(
            row.get("width5_projective_clifford_mismatches"),
            label="width5_projective_clifford_mismatches",
        )
        if width == 5:
            logical_count = len(
                {value for gate in build_qcla_trace(width).gates for value in gate.logical_support}
            )
            # Three projective Clifford identities are checked for both Pauli
            # axes on every logical qubit in every replayed macro layer.
            expected_checks = replay_branch_count * macro_depth * 3 * 2 * logical_count
            _require(checks == expected_checks, "width-5 exact-check count changed")
            _require(mismatches == 0, "width-5 projective identity failed")
            width5_checks = checks
        else:
            _require(
                replay_branch_count == checks == mismatches == 0,
                "width-5 replay fields leaked into width 256",
            )

    return PartialFrameClearingReplaySummary(
        widths=(5, 256),
        source_ccx_counts=tuple(source_ccx_counts),
        macro_depths=tuple(macro_depths),
        distribution_vectors_checked=distribution_vectors,
        distribution_values_checked=distribution_values,
        width5_projective_checks=width5_checks,
        all_passed=True,
    )


def partial_frame_clearing_replay_to_data(
    summary: PartialFrameClearingReplaySummary,
) -> dict[str, Any]:
    """Serialize the compact replay summary."""

    return {
        "all_passed": summary.all_passed,
        "distribution_values_checked": summary.distribution_values_checked,
        "distribution_vectors_checked": summary.distribution_vectors_checked,
        "macro_depths": list(summary.macro_depths),
        "source_ccx_counts": list(summary.source_ccx_counts),
        "width5_projective_checks": summary.width5_projective_checks,
        "widths": list(summary.widths),
    }
