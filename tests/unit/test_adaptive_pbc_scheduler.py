from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.codes import (
    PbcMittenImplementationKind,
    load_pbc_mitten_backend_config,
)
from ecdlp_ftqc.compiler import (
    FrameUpdate,
    LogicalPrimitive,
    LogicalPrimitiveKind,
    LogicalTrace,
    PbcDependency,
    PbcDependencyKind,
    PbcOperation,
    PbcOperationKind,
    PbcTrace,
    lower_to_adaptive_pauli_measurements,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    AdaptivePbcProcessorCapacityError,
    UnsupportedAdaptivePbcScheduleError,
    adaptive_pbc_schedule_to_data,
    schedule_adaptive_pbc_greedy,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPOSITORY_ROOT / "configs" / "codes" / "mitten_j300_pbc_v2.yaml"


def _ten_independent_cnot_trace() -> PbcTrace:
    primitives = tuple(
        LogicalPrimitive(
            primitive_id=f"cnot:{index:02d}",
            source_node_id=f"source:{index:02d}",
            kind=LogicalPrimitiveKind.CNOT,
            logical_support=(f"q:{2 * index}", f"q:{2 * index + 1}"),
            evidence_status=EvidenceStatus.LITERATURE,
        )
        for index in range(10)
    )
    logical = LogicalTrace(
        trace_id="synthetic-ten-independent-cnot",
        source_circuit_id="gidney-ripple-adder-width-synthetic",
        source_dag_schema_version=1,
        source_evidence_status=EvidenceStatus.LITERATURE,
        peak_source_processor_occupancy=20,
        primitives=primitives,
        dependencies=(),
    )
    return lower_to_adaptive_pauli_measurements(logical)


def _classically_adaptive_trace() -> PbcTrace:
    measurement = PbcOperation(
        operation_id="measure-x",
        source_primitive_id="source-measure",
        kind=PbcOperationKind.MEASURE_PAULI,
        logical_support=("q",),
        carrier_support=("carrier:q",),
        pauli_terms=("X:carrier:q",),
        classical_outputs=("bit:x",),
        semantic_evidence_status=EvidenceStatus.LITERATURE,
    )
    frame = PbcOperation(
        operation_id="frame-z",
        source_primitive_id="source-frame",
        kind=PbcOperationKind.PAULI_FRAME_UPDATE,
        logical_support=("q",),
        carrier_support=("carrier:q",),
        classical_inputs=("bit:x",),
        frame_updates=(FrameUpdate("carrier:q", "Z", ("bit:x",)),),
        semantic_evidence_status=EvidenceStatus.LITERATURE,
    )
    return PbcTrace(
        trace_id="synthetic-classical-reaction",
        source_trace_id="synthetic-source",
        source_evidence_status=EvidenceStatus.LITERATURE,
        peak_source_processor_occupancy=1,
        minimum_reusable_compiler_scratch_slots=0,
        operations=(measurement, frame),
        dependencies=(
            PbcDependency(
                predecessor="measure-x",
                successor="frame-z",
                kind=PbcDependencyKind.CLASSICAL_FEED_FORWARD,
                reason="measurement outcome bit:x",
            ),
        ),
        compiler_ancillas=(),
        final_carriers=(("q", "carrier:q"),),
    )


def _single_zx_trace() -> PbcTrace:
    operation = PbcOperation(
        operation_id="measure-zx",
        source_primitive_id="source-zx",
        kind=PbcOperationKind.MEASURE_PAULI,
        logical_support=("a", "b"),
        carrier_support=("carrier:a", "carrier:b"),
        pauli_terms=("Z:carrier:a", "X:carrier:b"),
        classical_outputs=("bit:zx",),
        semantic_evidence_status=EvidenceStatus.LITERATURE,
    )
    return PbcTrace(
        trace_id="synthetic-zx",
        source_trace_id="synthetic-source",
        source_evidence_status=EvidenceStatus.LITERATURE,
        peak_source_processor_occupancy=2,
        minimum_reusable_compiler_scratch_slots=0,
        operations=(operation,),
        dependencies=(),
        compiler_ancillas=(),
        final_carriers=(("a", "carrier:a"), ("b", "carrier:b")),
    )


def test_configuration_separates_time_and_space_evidence() -> None:
    config = load_pbc_mitten_backend_config(CONFIG_PATH)

    assert config.known_base_physical_qubits == 540
    seed_x = config.cost(PbcMittenImplementationKind.SEED_X)
    assert (seed_x.rounds, seed_x.added_physical_qubits) == (11, 87)
    assert seed_x.timing_evidence_status is EvidenceStatus.LITERATURE
    seed_z = config.cost(PbcMittenImplementationKind.SEED_Z)
    assert seed_z.timing_evidence_status is EvidenceStatus.CHECK
    assert seed_z.space_evidence_status is EvidenceStatus.LITERATURE
    high_rate = config.cost(PbcMittenImplementationKind.HIGH_RATE_XX_10)
    assert (high_rate.rounds, high_rate.added_physical_qubits) == (13, 1212)


def test_strict_mode_rejects_unreported_pbc_costs_and_reaction() -> None:
    config = load_pbc_mitten_backend_config(CONFIG_PATH)

    with pytest.raises(UnsupportedAdaptivePbcScheduleError, match="classical_reaction"):
        schedule_adaptive_pbc_greedy(_classically_adaptive_trace(), config)


def test_classical_feed_forward_adds_explicit_reaction_round() -> None:
    config = load_pbc_mitten_backend_config(CONFIG_PATH)
    schedule = schedule_adaptive_pbc_greedy(
        _classically_adaptive_trace(), config, allow_check_assumptions=True
    )

    frame = next(
        event
        for event in schedule.events
        if event.implementation is PbcMittenImplementationKind.PAULI_FRAME_UPDATE
    )
    assert frame.start_round == 12
    assert frame.classical_ready_round == 12
    assert schedule.dependency_only_critical_path_rounds == 12


def test_mixed_zx_uses_full_extractor_without_inventing_a_seed_gadget() -> None:
    config = load_pbc_mitten_backend_config(CONFIG_PATH)
    schedule = schedule_adaptive_pbc_greedy(
        _single_zx_trace(), config, allow_check_assumptions=True
    )

    assert schedule.events[0].implementation is PbcMittenImplementationKind.FULL_EXTRACTOR
    assert schedule.events[0].space_evidence_status is EvidenceStatus.LITERATURE
    assert schedule.events[0].timing_evidence_status is EvidenceStatus.CHECK
    assert schedule.known_peak_physical_qubits_lower_bound == 2074


def test_ten_scratch_slots_enable_only_the_source_supported_exact_batch() -> None:
    config = load_pbc_mitten_backend_config(CONFIG_PATH)
    trace = _ten_independent_cnot_trace()

    one_scratch = schedule_adaptive_pbc_greedy(
        trace,
        config,
        scratch_slot_count=1,
        allow_check_assumptions=True,
    )
    ten_scratch_serial = schedule_adaptive_pbc_greedy(
        trace,
        config,
        scratch_slot_count=10,
        enable_high_rate=False,
        allow_check_assumptions=True,
    )
    ten_scratch_high_rate = schedule_adaptive_pbc_greedy(
        trace,
        config,
        scratch_slot_count=10,
        enable_high_rate=True,
        allow_check_assumptions=True,
    )

    assert one_scratch.high_rate_batch_count == 0
    assert ten_scratch_serial.high_rate_batch_count == 0
    assert ten_scratch_high_rate.high_rate_batch_count == 1
    assert ten_scratch_high_rate.high_rate_operation_count == 10
    batch = next(
        event
        for event in ten_scratch_high_rate.events
        if event.implementation is PbcMittenImplementationKind.HIGH_RATE_XX_10
    )
    assert batch.scratch_slots == tuple(range(10))
    assert ten_scratch_high_rate.scheduled_rounds == 433
    assert ten_scratch_serial.scheduled_rounds == 550


def test_schedule_is_deterministic_and_serial_scratch_capacity_is_explicit() -> None:
    config = load_pbc_mitten_backend_config(CONFIG_PATH)
    trace = _ten_independent_cnot_trace()

    first = schedule_adaptive_pbc_greedy(
        trace, config, scratch_slot_count=10, allow_check_assumptions=True
    )
    second = schedule_adaptive_pbc_greedy(
        trace, config, scratch_slot_count=10, allow_check_assumptions=True
    )
    assert adaptive_pbc_schedule_to_data(first) == adaptive_pbc_schedule_to_data(second)

    boundary = replace(trace, peak_source_processor_occupancy=59)
    assert schedule_adaptive_pbc_greedy(
        boundary, config, scratch_slot_count=1, allow_check_assumptions=True
    ).peak_total_logical_occupancy == 60
    over_capacity = replace(trace, peak_source_processor_occupancy=60)
    with pytest.raises(AdaptivePbcProcessorCapacityError, match="60 plus 1.*60"):
        schedule_adaptive_pbc_greedy(
            over_capacity, config, scratch_slot_count=1, allow_check_assumptions=True
        )
