from __future__ import annotations

import json
import random
from dataclasses import replace

import pytest

from ecdlp_ftqc.circuits import (
    QCLA_SCHEMA,
    QCLA_SOURCE_ID,
    QCLA_SOURCE_PDF_SHA256,
    QclaDirection,
    QclaGateKind,
    QclaStage,
    QclaTraceError,
    build_qcla_trace,
    dumps_qcla_trace,
    qcla_metrics,
    replay_qcla,
)


def _floor_log2(value: int) -> int:
    return value.bit_length() - 1


@pytest.mark.parametrize("width", range(2, 7))
def test_replay_matches_modular_addition_exhaustively(width: int) -> None:
    trace = build_qcla_trace(width)
    limit = 1 << width

    for input_a in range(limit):
        for input_b in range(limit):
            result = replay_qcla(trace, input_a, input_b)
            assert result.passed
            assert result.output_a == input_a
            assert result.output_b == (input_a + input_b) % limit
            assert result.final_nonzero_ancillas == ()


@pytest.mark.parametrize("width", [7, 8, 9, 16])
def test_seeded_larger_width_replay(width: int) -> None:
    trace = build_qcla_trace(width)
    generator = random.Random(20260824 + width)

    for _ in range(128):
        replay_qcla(
            trace,
            generator.randrange(1 << width),
            generator.randrange(1 << width),
        )


@pytest.mark.parametrize("width", range(2, 34))
def test_gate_and_ancilla_counts_match_source_formulas(width: int) -> None:
    trace = build_qcla_trace(width)
    metrics = qcla_metrics(trace)
    length = width - 1

    assert metrics.toffoli_count == (
        10 * width - 6 * length.bit_count() - 6 * _floor_log2(length) - 12
    )
    assert metrics.cnot_count == 4 * width - 5
    assert metrics.x_count == 2 * width - 2
    assert metrics.source_ancilla_count == (
        2 * width - 2 - length.bit_count() - _floor_log2(length)
    )
    assert metrics.peak_live_ancillas == metrics.source_ancilla_count
    assert metrics.prefix_scratch_count == (
        length - length.bit_count() - _floor_log2(length)
    )


@pytest.mark.parametrize(
    "width",
    [5, 6, 7, 8, 9, 15, 16, 17, 31, 32, 33, 255, 256, 257],
)
def test_source_layer_count_matches_normal_size_formula(width: int) -> None:
    trace = build_qcla_trace(width)
    metrics = qcla_metrics(trace)
    length = width - 1

    assert metrics.source_layer_count == (
        2 * _floor_log2(length) + 2 * _floor_log2(length // 3) + 14
    )
    assert metrics.dependency_critical_path_gates <= metrics.source_layer_count


@pytest.mark.parametrize(
    ("width", "expected_layers"), [(2, 6), (3, 10), (4, 12)]
)
def test_small_widths_remove_empty_or_source_overcounted_slices(
    width: int, expected_layers: int
) -> None:
    trace = build_qcla_trace(width)

    assert trace.expected_source_layer_count is None
    assert qcla_metrics(trace).source_layer_count == expected_layers


def test_source_permitted_round_overlaps_are_explicit_and_disjoint() -> None:
    trace = build_qcla_trace(17)
    by_layer: dict[int, list[object]] = {}
    for gate in trace.gates:
        by_layer.setdefault(gate.algorithmic_layer, []).append(gate)

    assert any(
        {gate.stage for gate in gates}
        >= {QclaStage.PREFIX_PROPAGATE, QclaStage.PREFIX_GENERATE}
        for gates in by_layer.values()
    )
    assert any(
        {gate.stage for gate in gates}
        >= {QclaStage.PREFIX_CARRY, QclaStage.PREFIX_UNCOMPUTE}
        for gates in by_layer.values()
    )
    for gates in by_layer.values():
        support: set[str] = set()
        for gate in gates:
            assert support.isdisjoint(gate.logical_support)
            support.update(gate.logical_support)


def test_reverse_carry_is_layer_reversal_of_forward_carry() -> None:
    trace = build_qcla_trace(16)
    forward = [
        gate for gate in trace.gates if gate.direction is QclaDirection.FORWARD
    ]
    reverse = [
        gate for gate in trace.gates if gate.direction is QclaDirection.REVERSE
    ]

    forward_signatures = sorted(
        (gate.kind, gate.controls, gate.target, gate.stage, gate.round_index)
        for gate in forward
    )
    reverse_signatures = sorted(
        (gate.kind, gate.controls, gate.target, gate.stage, gate.round_index)
        for gate in reverse
    )
    assert forward_signatures == reverse_signatures
    forward_layers = sorted({gate.algorithmic_layer for gate in forward})
    reverse_layers = sorted({gate.algorithmic_layer for gate in reverse})
    for gate in forward:
        matching = [
            candidate
            for candidate in reverse
            if (
                candidate.kind,
                candidate.controls,
                candidate.target,
                candidate.stage,
                candidate.round_index,
            )
            == (
                gate.kind,
                gate.controls,
                gate.target,
                gate.stage,
                gate.round_index,
            )
        ]
        assert len(matching) == 1
        assert forward_layers.index(gate.algorithmic_layer) + reverse_layers.index(
            matching[0].algorithmic_layer
        ) == len(forward_layers) - 1


def test_dependencies_are_wire_causal_not_source_list_adjacency() -> None:
    trace = build_qcla_trace(9)
    gates = trace.gate_by_id()

    for dependency in trace.dependencies:
        predecessor = gates[dependency.predecessor]
        successor = gates[dependency.successor]
        assert predecessor.algorithmic_layer < successor.algorithmic_layer
        assert set(dependency.values) <= (
            set(predecessor.logical_support) & set(successor.logical_support)
        )
    assert len(trace.topological_order()) == len(trace.gates)
    assert len(trace.dependencies) < len(trace.gates) * 3


def test_validation_rejects_non_nearest_dependency_mutation() -> None:
    trace = build_qcla_trace(5)

    with pytest.raises(QclaTraceError, match="exact nearest-wire"):
        replace(trace, dependencies=trace.dependencies[1:])


def test_validation_rejects_same_layer_support_conflict() -> None:
    trace = build_qcla_trace(5)
    first, second, *remaining = trace.gates
    conflicting = replace(second, target=first.target)

    with pytest.raises(QclaTraceError, match="must be disjoint"):
        replace(trace, gates=(first, conflicting, *remaining))


def test_prefix_scratch_is_cleaned_and_reused_in_two_epochs() -> None:
    trace = build_qcla_trace(17)
    scratch: dict[str, list[object]] = {}
    for interval in trace.ancilla_intervals:
        if interval.family == "prefix_scratch":
            scratch.setdefault(interval.value_id, []).append(interval)

    assert scratch
    for intervals in scratch.values():
        assert [interval.reuse_epoch for interval in intervals] == [1, 2]
        assert intervals[0].end_layer < intervals[1].start_layer
    replay_qcla(trace, 0xFFFF, 1)


def test_width256_exposes_layerwise_toffoli_demand_without_backend_timing() -> None:
    trace = build_qcla_trace(256)
    metrics = qcla_metrics(trace)

    assert trace.schema == QCLA_SCHEMA
    assert trace.source.source_id == QCLA_SOURCE_ID
    assert trace.source.pdf_sha256 == QCLA_SOURCE_PDF_SHA256
    assert metrics.toffoli_count == 2458
    assert metrics.cnot_count == 1019
    assert metrics.x_count == 510
    assert metrics.source_ancilla_count == 495
    assert metrics.prefix_scratch_count == 240
    assert metrics.source_layer_count == 40
    assert sum(demand for _, demand in metrics.toffoli_demand_by_layer) == 2458
    assert metrics.peak_toffoli_per_layer == 255


def test_serialization_is_deterministic_and_evidence_qualified() -> None:
    trace = build_qcla_trace(8)

    first = dumps_qcla_trace(trace)
    second = dumps_qcla_trace(trace)
    data = json.loads(first)

    assert first == second
    assert data["source"]["semantic_evidence_status"] == "LITERATURE"
    assert data["arithmetic_contract"] == "(A,B)->(A,A+B mod 2^n)"
    assert data["metrics"]["toffoli_demand_by_layer"]
    assert all(gate["read_values"] for gate in data["gates"])
    assert all(len(gate["write_values"]) == 1 for gate in data["gates"])


@pytest.mark.parametrize(("input_a", "input_b"), [(-1, 0), (0, -1), (16, 0), (0, 16)])
def test_replay_rejects_out_of_range_inputs(input_a: int, input_b: int) -> None:
    with pytest.raises(QclaTraceError, match="fit the trace width"):
        replay_qcla(build_qcla_trace(4), input_a, input_b)


def test_invalid_width_is_rejected() -> None:
    with pytest.raises(QclaTraceError, match="at least two"):
        build_qcla_trace(1)


def test_every_gate_uses_the_reversible_classical_instruction_set() -> None:
    trace = build_qcla_trace(32)

    assert {gate.kind for gate in trace.gates} == {
        QclaGateKind.X,
        QclaGateKind.CNOT,
        QclaGateKind.TOFFOLI,
    }
