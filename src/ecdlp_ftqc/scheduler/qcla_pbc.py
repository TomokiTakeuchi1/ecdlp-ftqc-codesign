"""Resident-capacity gate for QCLA adaptive-PBC scheduling on finite J300."""

from __future__ import annotations

from dataclasses import dataclass

from ecdlp_ftqc.circuits.qcla import QclaTrace
from ecdlp_ftqc.codes import PbcMittenBackendConfig
from ecdlp_ftqc.compiler.qcla_pbc import (
    QclaAdaptivePbcLowering,
    lower_qcla_to_adaptive_pbc,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler.adaptive_pbc import (
    AdaptivePbcSchedule,
    schedule_adaptive_pbc_greedy,
)


class QclaResidentCapacityError(ValueError):
    """Raised before lowering when a fully resident QCLA cannot fit."""


@dataclass(frozen=True, slots=True)
class QclaResidentCapacityAssessment:
    """Necessary logical-slot capacity check for the selected resident model."""

    width: int
    data_register_slots: int
    source_ancilla_slots: int
    source_processor_occupancy: int
    compiler_scratch_slots: int
    total_required_slots: int
    processor_capacity: int
    fits: bool
    evidence_status: EvidenceStatus = EvidenceStatus.PROVED


@dataclass(frozen=True, slots=True)
class QclaResidentPbcSchedule:
    """Accepted QCLA lowering and its sensitivity schedule."""

    capacity: QclaResidentCapacityAssessment
    lowering: QclaAdaptivePbcLowering
    schedule: AdaptivePbcSchedule


def assess_qcla_resident_capacity(
    trace: QclaTrace,
    config: PbcMittenBackendConfig,
    *,
    scratch_slot_count: int,
) -> QclaResidentCapacityAssessment:
    """Evaluate the exact slot inequality without constructing a PBC trace."""

    if scratch_slot_count < 1:
        raise ValueError("QCLA adaptive-PBC lowering requires at least one scratch slot")
    data = 2 * trace.width
    source_ancillas = trace.source_ancilla_count
    source = data + source_ancillas
    total = source + scratch_slot_count
    return QclaResidentCapacityAssessment(
        width=trace.width,
        data_register_slots=data,
        source_ancilla_slots=source_ancillas,
        source_processor_occupancy=source,
        compiler_scratch_slots=scratch_slot_count,
        total_required_slots=total,
        processor_capacity=config.logical_qubits,
        fits=total <= config.logical_qubits,
    )


def schedule_qcla_resident_pbc(
    trace: QclaTrace,
    config: PbcMittenBackendConfig,
    *,
    scratch_slot_count: int,
    enable_high_rate: bool = True,
    allow_check_assumptions: bool = False,
) -> QclaResidentPbcSchedule:
    """Fail closed on capacity, then lower and invoke the reviewed scheduler."""

    capacity = assess_qcla_resident_capacity(
        trace,
        config,
        scratch_slot_count=scratch_slot_count,
    )
    if not capacity.fits:
        raise QclaResidentCapacityError(
            f"resident QCLA width {trace.width} needs {capacity.total_required_slots} "
            f"logical slots ({capacity.source_processor_occupancy} source + "
            f"{scratch_slot_count} scratch), exceeding capacity "
            f"{capacity.processor_capacity}; memory partitioning is outside this model"
        )
    lowering = lower_qcla_to_adaptive_pbc(trace)
    schedule = schedule_adaptive_pbc_greedy(
        lowering.pbc_trace,
        config,
        scratch_slot_count=scratch_slot_count,
        enable_high_rate=enable_high_rate,
        allow_check_assumptions=allow_check_assumptions,
    )
    return QclaResidentPbcSchedule(
        capacity=capacity,
        lowering=lowering,
        schedule=schedule,
    )


def qcla_capacity_assessment_to_data(
    assessment: QclaResidentCapacityAssessment,
) -> dict[str, int | bool | str]:
    """Convert a resident-capacity assessment to deterministic JSON data."""

    return {
        "compiler_scratch_slots": assessment.compiler_scratch_slots,
        "data_register_slots": assessment.data_register_slots,
        "evidence_status": assessment.evidence_status.value,
        "fits": assessment.fits,
        "processor_capacity": assessment.processor_capacity,
        "source_ancilla_slots": assessment.source_ancilla_slots,
        "source_processor_occupancy": assessment.source_processor_occupancy,
        "total_required_slots": assessment.total_required_slots,
        "width": assessment.width,
    }
