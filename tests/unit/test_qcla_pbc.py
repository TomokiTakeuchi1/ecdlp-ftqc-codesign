from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import build_qcla_trace, qcla_metrics
from ecdlp_ftqc.codes import load_pbc_mitten_backend_config
from ecdlp_ftqc.compiler import (
    SELINGER_CCX_DECOMPOSITION_ID,
    LogicalPrimitiveKind,
    lower_qcla_phase_exact,
    lower_qcla_to_adaptive_pbc,
    qcla_logical_lowering_to_data,
    verify_selinger_ccx_channel,
)
from ecdlp_ftqc.scheduler import (
    QclaResidentCapacityError,
    assess_qcla_resident_capacity,
    schedule_qcla_resident_pbc,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONFIG = REPOSITORY_ROOT / "configs" / "codes" / "mitten_j300_pbc_v2.yaml"


def _backend():
    return load_pbc_mitten_backend_config(BACKEND_CONFIG)


def test_selected_seven_t_circuit_matches_ccx_channel() -> None:
    verification = verify_selinger_ccx_channel()

    assert verification.decomposition_id == SELINGER_CCX_DECOMPOSITION_ID
    assert verification.passed
    assert verification.maximum_absolute_error < 1e-12
    assert verification.evidence_status.value == "NUMERICAL"


@pytest.mark.parametrize("width", [2, 8, 16, 256])
def test_logical_counts_are_exact_functions_of_source_gate_counts(width: int) -> None:
    source = build_qcla_trace(width)
    metrics = qcla_metrics(source)
    lowering = lower_qcla_phase_exact(source)
    counts = lowering.primitive_counts

    assert counts == Counter(
        {
            LogicalPrimitiveKind.X: metrics.x_count,
            LogicalPrimitiveKind.CNOT: metrics.cnot_count + 6 * metrics.toffoli_count,
            LogicalPrimitiveKind.H: 2 * metrics.toffoli_count,
            LogicalPrimitiveKind.S: metrics.toffoli_count,
            LogicalPrimitiveKind.T: 3 * metrics.toffoli_count,
            LogicalPrimitiveKind.T_DAGGER: 4 * metrics.toffoli_count,
        }
    )
    assert sum(
        primitive.resource_state_demand
        for primitive in lowering.logical_trace.primitives
    ) == 7 * metrics.toffoli_count
    assert lowering.logical_trace.peak_source_processor_occupancy == (
        2 * width + metrics.source_ancilla_count
    )


def test_ccx_source_columns_preserve_two_disjoint_parallel_pairs() -> None:
    lowering = lower_qcla_phase_exact(build_qcla_trace(2))
    first_ccx = next(
        gate_id
        for gate_id in (record.source_gate_id for record in lowering.provenance)
        if sum(record.source_gate_id == gate_id for record in lowering.provenance) == 16
    )
    records = [
        record for record in lowering.provenance if record.source_gate_id == first_ccx
    ]

    assert Counter(record.local_column for record in records) == Counter(
        {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 2,
         9: 1, 10: 1, 11: 1, 12: 1, 13: 2}
    )
    assert all(record.decomposition_id == SELINGER_CCX_DECOMPOSITION_ID for record in records)


def test_qcla_adaptive_pbc_demand_and_summary_are_deterministic() -> None:
    source = build_qcla_trace(4)
    lowering = lower_qcla_to_adaptive_pbc(source)
    expected_t = 7 * qcla_metrics(source).toffoli_count

    assert lowering.pbc_trace.resource_state_demand == expected_t
    assert lowering.pbc_trace.peak_source_processor_occupancy == 11
    assert lowering.pbc_trace.minimum_reusable_compiler_scratch_slots == 1
    assert qcla_logical_lowering_to_data(lowering.logical) == qcla_logical_lowering_to_data(
        lower_qcla_phase_exact(source)
    )


@pytest.mark.parametrize(
    ("width", "scratch", "required", "fits"),
    ((14, 10, 58, True), (15, 10, 62, False), (16, 1, 56, True), (17, 1, 62, False)),
)
def test_resident_capacity_boundaries(
    width: int, scratch: int, required: int, fits: bool
) -> None:
    assessment = assess_qcla_resident_capacity(
        build_qcla_trace(width), _backend(), scratch_slot_count=scratch
    )

    assert assessment.total_required_slots == required
    assert assessment.processor_capacity == 60
    assert assessment.fits is fits


def test_width256_fails_closed_before_memory_partitioning() -> None:
    source = build_qcla_trace(256)
    assessment = assess_qcla_resident_capacity(
        source, _backend(), scratch_slot_count=1
    )

    assert assessment.source_processor_occupancy == 1007
    assert assessment.total_required_slots == 1008
    assert not assessment.fits
    with pytest.raises(QclaResidentCapacityError, match="memory partitioning is outside"):
        schedule_qcla_resident_pbc(
            source,
            _backend(),
            scratch_slot_count=1,
            allow_check_assumptions=True,
        )


def test_width14_exposes_real_high_rate_batches_with_ten_scratch_slots() -> None:
    result = schedule_qcla_resident_pbc(
        build_qcla_trace(14),
        _backend(),
        scratch_slot_count=10,
        enable_high_rate=True,
        allow_check_assumptions=True,
    )

    assert result.capacity.total_required_slots == 58
    assert result.schedule.high_rate_batch_count > 0
    assert result.schedule.high_rate_operation_count == (
        10 * result.schedule.high_rate_batch_count
    )
    assert result.schedule.factory_mode == "ideal_supply_no_stalls"
    assert not result.schedule.strict_executable
