from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import generate_gidney_dag, load_gidney_oracle_dag
from ecdlp_ftqc.codes import (
    MittenImplementationKind,
    load_mitten_backend_config,
)
from ecdlp_ftqc.compiler import (
    LogicalPrimitive,
    LogicalPrimitiveKind,
    LogicalTrace,
    lower_gidney_phase_exact,
)
from ecdlp_ftqc.metadata import CircuitDag, EvidenceStatus
from ecdlp_ftqc.scheduler import (
    ProcessorCapacityError,
    UnsupportedMittenLoweringError,
    schedule_mitten_greedy,
    schedule_to_data,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "gidney_oracle"
CONFIG_PATH = REPOSITORY_ROOT / "configs" / "codes" / "mitten_j300_k60_d14_v1.yaml"


def _dag(width: int) -> CircuitDag:
    return load_gidney_oracle_dag(
        FIXTURE_ROOT / f"gidney_width{width}_oracle_v3.json"
    )


def _xx_trace(count: int) -> LogicalTrace:
    primitives = tuple(
        LogicalPrimitive(
            primitive_id=f"xx:{index:02d}",
            source_node_id=f"source:{index:02d}",
            kind=LogicalPrimitiveKind.MEASURE_XX,
            logical_support=(f"q:{2 * index}", f"q:{2 * index + 1}"),
            pauli_terms=(f"X:q:{2 * index}", f"X:q:{2 * index + 1}"),
            evidence_status=EvidenceStatus.NUMERICAL,
        )
        for index in range(count)
    )
    return LogicalTrace(
        trace_id=f"synthetic-disjoint-xx-{count}",
        source_circuit_id="synthetic-disjoint-xx",
        source_dag_schema_version=1,
        source_evidence_status=EvidenceStatus.NUMERICAL,
        peak_source_processor_occupancy=2 * count,
        primitives=primitives,
        dependencies=(),
    )


def test_mitten_configuration_preserves_table_counts_and_evidence() -> None:
    config = load_mitten_backend_config(CONFIG_PATH)

    assert config.logical_qubits == 60
    assert config.data_physical_qubits == 300
    assert config.syndrome_ancilla_qubits == 240
    assert config.known_base_physical_qubits == 540
    seed_x = config.cost(MittenImplementationKind.SEED_X_SURGERY)
    assert (seed_x.rounds, seed_x.added_physical_qubits) == (11, 87)
    assert seed_x.evidence_status is EvidenceStatus.LITERATURE
    high_rate = config.cost(MittenImplementationKind.HIGH_RATE_XX_10)
    assert (high_rate.rounds, high_rate.added_physical_qubits) == (13, 1212)
    assert high_rate.evidence_status is EvidenceStatus.LITERATURE
    assert config.cost(MittenImplementationKind.FULL_EXTRACTOR).evidence_status is (
        EvidenceStatus.CHECK
    )


def test_figure_3_lowering_is_phase_exact_and_retains_four_t_resources() -> None:
    trace = lower_gidney_phase_exact(_dag(2))
    counts = Counter(primitive.kind for primitive in trace.primitives)

    assert len(trace.primitives) == 18
    assert counts == {
        LogicalPrimitiveKind.PREPARE_T: 1,
        LogicalPrimitiveKind.CNOT: 9,
        LogicalPrimitiveKind.T: 1,
        LogicalPrimitiveKind.T_DAGGER: 2,
        LogicalPrimitiveKind.H: 1,
        LogicalPrimitiveKind.S: 1,
        LogicalPrimitiveKind.MEASURE_X: 1,
        LogicalPrimitiveKind.CONDITIONAL_CZ_FRAME: 1,
        LogicalPrimitiveKind.RELEASE: 1,
    }
    assert sum(primitive.resource_state_demand for primitive in trace.primitives) == 4
    dependency_endpoints = {
        (dependency.predecessor, dependency.successor)
        for dependency in trace.dependencies
    }
    compute_prefix = "op:0001:temporary_and_compute::logical:"
    for t_suffix in ("04_t_dagger_x", "05_t_dagger_y", "06_t_a"):
        assert (
            f"{compute_prefix}03_cnot_a_to_y",
            f"{compute_prefix}{t_suffix}",
        ) in dependency_endpoints
        assert (
            f"{compute_prefix}{t_suffix}",
            f"{compute_prefix}07_cnot_a_to_x",
        ) in dependency_endpoints


def test_width_four_primitive_counts_follow_the_general_construction() -> None:
    trace = lower_gidney_phase_exact(_dag(4))
    counts = Counter(primitive.kind for primitive in trace.primitives)

    assert len(trace.primitives) == 60
    assert counts[LogicalPrimitiveKind.CNOT] == 33
    assert counts[LogicalPrimitiveKind.PREPARE_T] == 3
    assert counts[LogicalPrimitiveKind.T] == 3
    assert counts[LogicalPrimitiveKind.T_DAGGER] == 6
    assert counts[LogicalPrimitiveKind.MEASURE_X] == 3
    assert sum(primitive.resource_state_demand for primitive in trace.primitives) == 12


def test_strict_mode_rejects_unresolved_intra_block_cqlu_lowering() -> None:
    config = load_mitten_backend_config(CONFIG_PATH)
    trace = lower_gidney_phase_exact(_dag(2))

    with pytest.raises(UnsupportedMittenLoweringError, match="cnot"):
        schedule_mitten_greedy(trace, config)


def test_provisional_schedule_is_deterministic_and_does_not_invent_high_rate_x() -> None:
    config = load_mitten_backend_config(CONFIG_PATH)
    trace = lower_gidney_phase_exact(_dag(2))

    first = schedule_mitten_greedy(trace, config, allow_check_assumptions=True)
    second = schedule_mitten_greedy(trace, config, allow_check_assumptions=True)

    assert schedule_to_data(first) == schedule_to_data(second)
    assert first.strict_executable is False
    assert first.high_rate_primitive_count == 0
    assert first.implementation_counts[MittenImplementationKind.SEED_X_SURGERY] == 1
    assert first.total_resource_state_demand == 4
    assert first.known_peak_physical_qubits_lower_bound == 627
    assert first.physical_qubit_total_complete is False


def test_exact_ten_disjoint_xx_measurements_use_one_high_rate_gadget() -> None:
    config = load_mitten_backend_config(CONFIG_PATH)
    schedule = schedule_mitten_greedy(_xx_trace(10), config)

    assert schedule.strict_executable is True
    assert len(schedule.events) == 1
    assert schedule.high_rate_primitive_count == 10
    assert schedule.sequential_rounds == 130
    assert schedule.dependency_only_critical_path_rounds == 13
    assert schedule.scheduled_rounds == 13
    assert schedule.known_peak_physical_qubits_lower_bound == 1752


def test_nine_disjoint_xx_measurements_fall_back_to_seed_surgery() -> None:
    config = load_mitten_backend_config(CONFIG_PATH)
    schedule = schedule_mitten_greedy(_xx_trace(9), config)

    assert schedule.high_rate_primitive_count == 0
    assert len(schedule.events) == 9
    assert schedule.implementation_counts[MittenImplementationKind.SEED_XX_SURGERY] == 9
    assert schedule.scheduled_rounds == 117


def test_overlapping_xx_support_is_not_batched_as_high_rate() -> None:
    config = load_mitten_backend_config(CONFIG_PATH)
    trace = _xx_trace(10)
    overlapping = tuple(
        LogicalPrimitive(
            primitive_id=primitive.primitive_id,
            source_node_id=primitive.source_node_id,
            kind=primitive.kind,
            logical_support=("q:shared", primitive.logical_support[1]),
            pauli_terms=("X:q:shared", primitive.pauli_terms[1]),
            evidence_status=primitive.evidence_status,
        )
        for primitive in trace.primitives
    )
    overlapping_trace = LogicalTrace(
        trace_id="synthetic-overlapping-xx-10",
        source_circuit_id=trace.source_circuit_id,
        source_dag_schema_version=trace.source_dag_schema_version,
        source_evidence_status=trace.source_evidence_status,
        peak_source_processor_occupancy=11,
        primitives=overlapping,
        dependencies=(),
    )

    schedule = schedule_mitten_greedy(overlapping_trace, config)

    assert schedule.high_rate_primitive_count == 0
    assert schedule.implementation_counts[MittenImplementationKind.SEED_XX_SURGERY] == 10


def test_width_59_is_source_capacity_boundary_and_width_60_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_repo = REPOSITORY_ROOT.parent / "runtime-metadata-benchmark"
    source_package = source_repo / "src" / "runtime_metadata_benchmark"
    if not source_package.is_dir():
        pytest.skip("pinned runtime-metadata-benchmark checkout is not available")
    observed_commit = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={source_repo.as_posix()}",
            "-C",
            str(source_repo),
            "rev-parse",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert observed_commit == "8c1638805e7246c30117a0251526661039df1369"
    monkeypatch.syspath_prepend(str(source_repo / "src"))
    config = load_mitten_backend_config(CONFIG_PATH)

    width_59 = lower_gidney_phase_exact(generate_gidney_dag(59))
    schedule = schedule_mitten_greedy(
        width_59, config, allow_check_assumptions=True
    )
    assert width_59.peak_source_processor_occupancy == 60
    assert schedule.peak_source_processor_occupancy == 60

    width_60 = lower_gidney_phase_exact(generate_gidney_dag(60))
    assert width_60.peak_source_processor_occupancy == 61
    with pytest.raises(ProcessorCapacityError, match="61.*60"):
        schedule_mitten_greedy(width_60, config, allow_check_assumptions=True)
