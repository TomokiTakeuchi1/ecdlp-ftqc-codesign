from __future__ import annotations

import json
from dataclasses import replace

import pytest

from ecdlp_ftqc.circuits import (
    OOP_QCLA_SCHEMA,
    OopQclaTraceError,
    build_oop_qcla_trace,
    dumps_oop_qcla_trace,
    oop_qcla_metrics,
    replay_oop_qcla,
)


@pytest.mark.parametrize("width", range(2, 7))
def test_clean_oop_qcla_exhaustively_preserves_inputs_and_writes_sum(width: int) -> None:
    trace = build_oop_qcla_trace(width)
    limit = 1 << width

    for input_a in range(limit):
        for input_b in range(limit):
            result = replay_oop_qcla(trace, input_a, input_b)
            assert result.output_a == input_a
            assert result.output_b == input_b
            assert result.output_sum == (input_a + input_b) % limit
            assert result.final_nonzero_ancillas == ()


@pytest.mark.parametrize("width", [2, 3, 4, 5, 8, 16, 17, 32, 256])
def test_source_counts_match_draper_closed_forms(width: int) -> None:
    trace = build_oop_qcla_trace(width)
    metrics = oop_qcla_metrics(trace)
    length = width - 1

    assert metrics.toffoli_count == (
        5 * width - 3 * length.bit_count() - 3 * (length.bit_length() - 1) - 6
    )
    assert metrics.cnot_count == 3 * width - 2
    assert metrics.source_auxiliary_count == (
        length - length.bit_count() - (length.bit_length() - 1)
    )
    assert metrics.fully_resident_source_values == 3 * width + metrics.source_auxiliary_count


def test_width256_reproduces_reviewed_workload_ladder() -> None:
    trace = build_oop_qcla_trace(256)
    metrics = oop_qcla_metrics(trace)

    assert trace.schema == OOP_QCLA_SCHEMA
    assert metrics.gate_count == 1995
    assert metrics.toffoli_count == 1229
    assert metrics.cnot_count == 766
    assert metrics.source_layer_count == 20
    assert metrics.dependency_critical_path_gates == 20
    assert metrics.source_auxiliary_count == 240
    assert metrics.fully_resident_source_values == 1008
    assert metrics.peak_toffoli_per_layer == 255
    assert metrics.peak_toffoli_layer == 1
    assert sum(demand for _, demand in metrics.toffoli_demand_by_layer) == 1229
    assert trace.gates[0].stage.value == "initial_generate"


def test_j300_source_value_boundary_is_visible_without_claiming_injection_capacity() -> None:
    width16 = oop_qcla_metrics(build_oop_qcla_trace(16))
    width17 = oop_qcla_metrics(build_oop_qcla_trace(17))

    assert width16.fully_resident_source_values == 56
    assert width17.fully_resident_source_values == 62
    assert width16.fully_resident_source_values <= 60
    assert width17.fully_resident_source_values > 60


def test_serialization_is_deterministic_and_contains_no_backend_timing() -> None:
    trace = build_oop_qcla_trace(8)

    first = dumps_oop_qcla_trace(trace)
    second = dumps_oop_qcla_trace(trace)
    data = json.loads(first)

    assert first == second
    assert data["arithmetic_contract"] == "(A,B,0)->(A,B,A+B mod 2^n)"
    assert data["source"]["semantic_evidence_status"] == "LITERATURE"
    assert "rounds" not in data["metrics"]
    assert "seconds" not in data["metrics"]


def test_validation_rejects_missing_nearest_wire_dependency() -> None:
    trace = build_oop_qcla_trace(8)

    with pytest.raises(OopQclaTraceError, match="exact nearest-wire"):
        replace(trace, dependencies=trace.dependencies[1:])


@pytest.mark.parametrize(("input_a", "input_b"), [(-1, 0), (0, -1), (16, 0), (0, 16)])
def test_replay_rejects_out_of_range_inputs(input_a: int, input_b: int) -> None:
    with pytest.raises(OopQclaTraceError, match="fit the trace width"):
        replay_oop_qcla(build_oop_qcla_trace(4), input_a, input_b)


def test_invalid_width_is_rejected() -> None:
    with pytest.raises(OopQclaTraceError, match="at least two"):
        build_oop_qcla_trace(1)
