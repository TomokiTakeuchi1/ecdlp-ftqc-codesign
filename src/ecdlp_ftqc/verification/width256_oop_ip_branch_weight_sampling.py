"""Independent scalar replay of width-256 OOP/IP branch-weight samples.

This module intentionally does not import the task scheduler.  It evaluates
one branch at a time with integer support bitsets, unlike the scheduler's
sample-packed bit-plane implementation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from ecdlp_ftqc.circuits import (
    OopQclaGate,
    OopQclaTrace,
    QclaGate,
    QclaGateKind,
    QclaTrace,
)
from ecdlp_ftqc.compiler import DirectCczEventTrace

_SCHEMA = "ecdlp-ftqc/width256-oop-ip-branch-maximum-ppm-weight-sampling"
_SAMPLE_COUNT = 512
_SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"
_QUANTILE_METHOD = "nearest_rank_order_statistic"


class Width256BranchWeightReplayError(ValueError):
    """Raised when replay disagrees with the serialized sampling study."""


@dataclass(frozen=True, slots=True)
class VariantBranchWeightReplay:
    """Independent replay totals for one QCLA variant."""

    variant: Literal["oop", "ip"]
    candidate_level_count: int
    sampled_level_vector_count: int
    sampled_level_value_count: int
    evaluated_branch_ppm_instance_count: int
    support_relevant_assignment_sha256: str
    sampled_level_matrix_sha256: str
    level_vectors_match: bool
    quantiles_match: bool
    upper_bounds_respected: bool
    x_phase_exact: bool
    all_passed: bool


@dataclass(frozen=True, slots=True)
class Width256BranchWeightReplay:
    """Independent OOP/IP replay result."""

    task_id: str
    experiment_id: str
    sample_count: int
    oop: VariantBranchWeightReplay
    ip: VariantBranchWeightReplay
    total_sampled_level_values_checked: int
    total_evaluated_branch_ppm_instances_checked: int
    non_null_native_output_count: int
    all_passed: bool


Gate = OopQclaGate | QclaGate
Trace = OopQclaTrace | QclaTrace


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest().upper()


def _sample_mask(variable: str) -> int:
    byte_count = (_SAMPLE_COUNT + 7) // 8
    raw = int.from_bytes(
        hashlib.shake_256(f"{_SAMPLE_SEED}|{variable}".encode()).digest(
            byte_count
        ),
        "little",
    )
    raw &= (1 << _SAMPLE_COUNT) - 1
    raw &= ~1
    raw |= 1 << 1
    return raw


def _assignment_digest(token_masks: dict[str, int]) -> str:
    width = (_SAMPLE_COUNT + 7) // 8
    return _digest(
        tuple(
            (token, mask.to_bytes(width, "little").hex())
            for token, mask in sorted(token_masks.items())
        )
    )


def _nearest_rank(values: tuple[int, ...], percentile: int) -> int:
    ordered = tuple(sorted(values))
    index = (percentile * len(ordered) + 99) // 100 - 1
    return ordered[index]


def _scalar_source_cnot(
    columns: dict[str, int],
    logical_index: dict[str, int],
    control: str,
    target: str,
) -> None:
    columns[target] ^= columns[control]
    target_bit = 1 << logical_index[target]
    control_bit = 1 << logical_index[control]
    for value, column in columns.items():
        if column & target_bit:
            columns[value] = column ^ control_bit


def _scalar_variant_vectors(
    *,
    trace: Trace,
    event_trace: DirectCczEventTrace,
    macro_layers: tuple[tuple[str, ...], ...],
) -> tuple[tuple[tuple[int, ...], ...], str]:
    gate_by_id: dict[str, Gate] = {gate.gate_id: gate for gate in trace.gates}
    event_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    groups = tuple(
        tuple(gate_by_id[gate_id] for gate_id in layer)
        for layer in macro_layers
    )
    logical_values = tuple(
        sorted({value for gate in trace.gates for value in gate.logical_support})
    )
    logical_index = {value: index for index, value in enumerate(logical_values)}
    cnot_by_layer: dict[int, list[Gate]] = {}
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            cnot_by_layer.setdefault(gate.algorithmic_layer, []).append(gate)
    relevant_tokens = tuple(
        sorted(
            {
                event.ppms[index].outcome_token
                for event in event_trace.injection_events
                for index in (0, 1)
            }
        )
    )
    token_masks = {token: _sample_mask(token) for token in relevant_tokens}
    matrix = [[0] * _SAMPLE_COUNT for _ in range(2 * len(groups))]
    for sample in range(_SAMPLE_COUNT):
        columns = {
            value: 1 << logical_index[value] for value in logical_values
        }
        applied_cnot_layers: set[int] = set()
        for macro_layer, group in enumerate(groups, start=1):
            lower = min(gate.algorithmic_layer for gate in group)
            upper = max(gate.algorithmic_layer for gate in group)
            if any(lower <= layer <= upper for layer in cnot_by_layer):
                raise Width256BranchWeightReplayError(
                    "macro layer crosses a CNOT barrier"
                )
            for layer in sorted(cnot_by_layer):
                if layer >= lower or layer in applied_cnot_layers:
                    continue
                for gate in cnot_by_layer[layer]:
                    _scalar_source_cnot(
                        columns,
                        logical_index,
                        gate.controls[0],
                        gate.target,
                    )
                applied_cnot_layers.add(layer)
            branch_maximum = 1
            for gate in group:
                event = event_by_source[gate.gate_id]
                branch_maximum = max(
                    branch_maximum,
                    *(columns[data_value].bit_count() + 1 for data_value in event.data),
                )
            matrix[2 * macro_layer - 2][sample] = branch_maximum
            matrix[2 * macro_layer - 1][sample] = 1
            for gate in group:
                event = event_by_source[gate.gate_id]
                c0, c1, target = event.data
                for source, ppm_index in ((c1, 0), (c0, 1)):
                    token = event.ppms[ppm_index].outcome_token
                    if (token_masks[token] >> sample) & 1:
                        columns[target] ^= columns[source]
    return tuple(tuple(level) for level in matrix), _assignment_digest(token_masks)


def _parse_macro_layers(data: dict[str, Any]) -> tuple[tuple[str, ...], ...]:
    raw = data.get("macro_layer_source_gate_ids")
    if not isinstance(raw, list):
        raise Width256BranchWeightReplayError("macro layers are missing")
    return tuple(tuple(str(gate_id) for gate_id in layer) for layer in raw)


def _parse_recorded_vectors(
    data: dict[str, Any],
) -> tuple[tuple[tuple[int, ...], ...], tuple[dict[str, Any], ...]]:
    raw_levels = data.get("levels")
    if not isinstance(raw_levels, list):
        raise Width256BranchWeightReplayError("sample levels are missing")
    records: list[dict[str, Any]] = []
    vectors: list[tuple[int, ...]] = []
    for raw in raw_levels:
        if not isinstance(raw, dict):
            raise Width256BranchWeightReplayError("invalid sample level")
        vector = raw.get("branch_maximum_weights")
        if not isinstance(vector, list):
            raise Width256BranchWeightReplayError("sample vector is missing")
        records.append(raw)
        vectors.append(tuple(int(value) for value in vector))
    return tuple(vectors), tuple(records)


def _replay_variant(
    *,
    variant: Literal["oop", "ip"],
    data: dict[str, Any],
    trace: Trace,
    event_trace: DirectCczEventTrace,
) -> VariantBranchWeightReplay:
    if data.get("variant") != variant:
        raise Width256BranchWeightReplayError("variant label changed")
    macro_layers = _parse_macro_layers(data)
    recorded, records = _parse_recorded_vectors(data)
    replayed, assignment_digest = _scalar_variant_vectors(
        trace=trace,
        event_trace=event_trace,
        macro_layers=macro_layers,
    )
    vectors_match = recorded == replayed
    quantiles_match = True
    bounds_respected = True
    x_phase_exact = True
    for index, (vector, record) in enumerate(zip(replayed, records, strict=True)):
        quantiles_match &= (
            int(record.get("minimum", -1)) == min(vector)
            and int(record.get("forced_all_zero_weight", -1)) == vector[0]
            and int(record.get("forced_all_one_weight", -1)) == vector[1]
            and int(record.get("hashed_branch_maximum", -1))
            == max(vector[2:])
            and int(record.get("hashed_branch_sample_count", -1))
            == _SAMPLE_COUNT - 2
            and int(record.get("p50", -1)) == _nearest_rank(vector, 50)
            and int(record.get("p95", -1)) == _nearest_rank(vector, 95)
            and int(record.get("p99", -1)) == _nearest_rank(vector, 99)
            and int(record.get("sampled_maximum", -1)) == max(vector)
            and record.get("quantile_method") == _QUANTILE_METHOD
            and record.get("sample_vector_sha256") == _digest(vector)
        )
        upper = int(record.get("support_weight_upper_bound", -1))
        bounds_respected &= max(vector) <= upper
        if index % 2 == 1:
            x_phase_exact &= (
                set(vector) == {1}
                and record.get("sampled_maximum_is_true_maximum") is True
                and record.get("evidence_status") == "PROVED"
            )
        else:
            x_phase_exact &= (
                record.get("sampled_maximum_is_true_maximum") is False
                and record.get("evidence_status") == "NUMERICAL"
            )
    matrix_digest = _digest(replayed)
    metadata_match = (
        int(data.get("candidate_level_count", -1)) == len(replayed)
        and int(data.get("sample_count", -1)) == _SAMPLE_COUNT
        and data.get("sample_seed") == _SAMPLE_SEED
        and data.get("support_relevant_assignment_sha256") == assignment_digest
        and data.get("sampled_level_matrix_sha256") == matrix_digest
        and int(data.get("sampled_outcome_token_count", -1))
        == 2 * len(event_trace.injection_events)
    )
    all_passed = (
        vectors_match
        and quantiles_match
        and bounds_respected
        and x_phase_exact
        and metadata_match
    )
    if not all_passed:
        raise Width256BranchWeightReplayError(
            f"{variant} independent branch-weight replay failed"
        )
    ppm_count = int(data.get("ppm_count", -1))
    evaluated = _SAMPLE_COUNT * ppm_count
    if int(data.get("evaluated_branch_ppm_instance_count", -1)) != evaluated:
        raise Width256BranchWeightReplayError("evaluated PPM count changed")
    return VariantBranchWeightReplay(
        variant=variant,
        candidate_level_count=len(replayed),
        sampled_level_vector_count=len(replayed),
        sampled_level_value_count=len(replayed) * _SAMPLE_COUNT,
        evaluated_branch_ppm_instance_count=evaluated,
        support_relevant_assignment_sha256=assignment_digest,
        sampled_level_matrix_sha256=matrix_digest,
        level_vectors_match=True,
        quantiles_match=True,
        upper_bounds_respected=True,
        x_phase_exact=True,
        all_passed=True,
    )


def replay_width256_oop_ip_branch_weight_study(
    data: dict[str, Any],
    *,
    oop_source: OopQclaTrace,
    oop_events: DirectCczEventTrace,
    ip_source: QclaTrace,
    ip_events: DirectCczEventTrace,
) -> Width256BranchWeightReplay:
    """Replay every sampled level vector with a scalar implementation."""

    if (
        data.get("schema") != _SCHEMA
        or data.get("schema_version") != 1
        or data.get("task_id") != "T-20260907-002"
        or data.get("experiment_id") != "E-20260907-002"
        or data.get("sample_count") != _SAMPLE_COUNT
        or data.get("sample_seed") != _SAMPLE_SEED
        or data.get("sampled_maximum_is_global_true_maximum") is not False
    ):
        raise Width256BranchWeightReplayError("study header changed")
    non_null_native = sum(
        data.get(field) is not None
        for field in (
            "native_cycles",
            "runtime_seconds",
            "physical_qubits",
            "failure_probability",
        )
    ) + int(data.get("complete_native_schedule") is not False)
    if non_null_native:
        raise Width256BranchWeightReplayError("native output must remain null")
    oop_data = data.get("oop")
    ip_data = data.get("ip")
    if not isinstance(oop_data, dict) or not isinstance(ip_data, dict):
        raise Width256BranchWeightReplayError("variant records are missing")
    oop = _replay_variant(
        variant="oop",
        data=oop_data,
        trace=oop_source,
        event_trace=oop_events,
    )
    ip = _replay_variant(
        variant="ip",
        data=ip_data,
        trace=ip_source,
        event_trace=ip_events,
    )
    total_values = oop.sampled_level_value_count + ip.sampled_level_value_count
    total_ppm = (
        oop.evaluated_branch_ppm_instance_count
        + ip.evaluated_branch_ppm_instance_count
    )
    if int(data.get("total_evaluated_branch_ppm_instance_count", -1)) != total_ppm:
        raise Width256BranchWeightReplayError("combined PPM count changed")
    return Width256BranchWeightReplay(
        task_id="T-20260907-002",
        experiment_id="E-20260907-002",
        sample_count=_SAMPLE_COUNT,
        oop=oop,
        ip=ip,
        total_sampled_level_values_checked=total_values,
        total_evaluated_branch_ppm_instances_checked=total_ppm,
        non_null_native_output_count=0,
        all_passed=True,
    )


def width256_oop_ip_branch_weight_replay_to_data(
    replay: Width256BranchWeightReplay,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible replay data."""

    data = asdict(replay)
    if not isinstance(data, dict):  # pragma: no cover - dataclass invariant
        raise Width256BranchWeightReplayError("replay serialization failed")
    return data
