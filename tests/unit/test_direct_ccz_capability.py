from __future__ import annotations

from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import (
    DIRECT_CCZ_FIGURE14_CORRECTION_MAP,
    DirectCczCapabilityError,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    direct_ccz_event_trace_to_data,
    lower_oop_qcla_to_direct_ccz_events,
)
from ecdlp_ftqc.metadata import EvidenceStatus

CAPABILITY_PATH = Path("configs/architectures/direct_ccz_high_rate_capability_v1.yaml")
EVENT_CAPABILITY_PATH = Path(
    "configs/architectures/direct_ccz_single_event_capability_v1.yaml"
)


def test_source_qualified_capability_is_fail_closed() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)

    assert not capability.event_lowering_admitted
    assert not capability.high_rate_schedule_admitted
    assert capability.missing_for_event_lowering == (
        "injection.correction.exact_boolean_map",
        "injection.correction.admissible_evidence",
    )
    assert "high_rate.admitted_batch_sizes" in capability.missing_for_high_rate_schedule
    assert "high_rate.decoder_measurements_per_second" in capability.missing_for_high_rate_schedule
    assert "factory.buffer_capacity" in capability.missing_for_high_rate_schedule


def test_source_record_separates_t_injection_from_direct_ccz() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    by_source = {source.source_id: source for source in capability.sources}

    assert any("resource-data ZZ" in item for item in by_source[
        "Cain et al., arXiv:2603.28627v1"
    ].establishes)
    assert any("T states, not direct CCZ" in item for item in by_source[
        "Bhardwaj et al., arXiv:2607.28795v1"
    ].establishes)
    assert any("does not admit batched direct-CCZ" in item for item in by_source[
        "Zheng et al., arXiv:2607.28605v1"
    ].establishes)


def test_incomplete_capability_rejects_before_emitting_any_event() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    trace = build_oop_qcla_trace(8)

    with pytest.raises(DirectCczCapabilityError, match="exact_boolean_map"):
        lower_oop_qcla_to_direct_ccz_events(trace, capability)


def test_source_qualified_single_event_capability_is_admitted_but_high_rate_is_not() -> None:
    capability = load_direct_ccz_capability(EVENT_CAPABILITY_PATH)

    assert capability.event_lowering_admitted
    assert not capability.high_rate_schedule_admitted
    assert capability.missing_for_event_lowering == ()
    assert capability.injection.correction.exact_boolean_map == (
        DIRECT_CCZ_FIGURE14_CORRECTION_MAP
    )
    assert "high_rate.admitted_batch_sizes" in capability.missing_for_high_rate_schedule
    assert "factory.delivery_latency_cycles" in capability.missing_for_high_rate_schedule


def test_source_qualified_capability_emits_typed_single_events() -> None:
    capability = load_direct_ccz_capability(EVENT_CAPABILITY_PATH)
    source = build_oop_qcla_trace(4)
    result = lower_oop_qcla_to_direct_ccz_events(
        source,
        capability,
    )

    assert len(result.injection_events) == 5
    assert not result.complete_native_schedule
    first = result.injection_events[0]
    assert first.evidence_status is EvidenceStatus.LITERATURE
    assert first.correction_frame[0].startswith("CZ(b:0,z:1)^direct-ccz:")
    assert first.correction_frame[5].startswith("X(z:1)^")
    assert len(result.source_dependencies) == len(source.dependencies)
    assert {
        (
            dependency.predecessor_source_gate_id,
            dependency.successor_source_gate_id,
            dependency.logical_values,
            dependency.reason,
        )
        for dependency in result.source_dependencies
    } == {
        (
            dependency.predecessor,
            dependency.successor,
            dependency.values,
            dependency.reason,
        )
        for dependency in source.dependencies
    }


def test_synthetic_complete_correction_contract_emits_typed_events() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH).with_exact_correction_map(
        DIRECT_CCZ_FIGURE14_CORRECTION_MAP,
        evidence_status=EvidenceStatus.PROVED,
    )
    source = build_oop_qcla_trace(4)

    result = lower_oop_qcla_to_direct_ccz_events(source, capability)
    data = direct_ccz_event_trace_to_data(result)

    assert len(result.injection_events) == 5
    assert len(result.passthrough_clifford_gate_ids) == 10
    first = result.injection_events[0]
    assert first.data == ("a:0", "b:0", "z:1")
    assert first.basis_changes_before == ("H(z:1)",)
    assert first.basis_changes_after == ("H(z:1)",)
    assert [ppm.layer for ppm in first.ppms] == [1, 1, 1, 2, 2, 2]
    assert first.ppms[0].logical_support == (first.resource[0], "a:0")
    assert first.ppms[0].pauli_terms == ("Z", "Z")
    assert first.ppms[3].logical_support == (first.resource[0],)
    assert len(first.correction_frame) == 6
    assert all("{" not in correction for correction in first.correction_frame)
    assert first.correction_frame[0].startswith("CZ(b:0,z:1)^direct-ccz:")
    assert first.correction_frame[3].startswith("Z(a:0)^")
    assert " XOR " in first.correction_frame[3]
    assert not result.complete_native_schedule
    assert data["schema"] == "ecdlp-ftqc/direct-ccz-injection-event-trace"
    assert data["schema_version"] == 2


def test_event_admission_does_not_admit_high_rate_schedule() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH).with_exact_correction_map(
        DIRECT_CCZ_FIGURE14_CORRECTION_MAP,
        evidence_status=EvidenceStatus.PROVED,
    )

    assert capability.event_lowering_admitted
    assert not capability.high_rate_schedule_admitted


def test_loader_rejects_forged_admission_flag(tmp_path: Path) -> None:
    contents = CAPABILITY_PATH.read_text(encoding="utf-8")
    forged = contents.replace(
        "event_lowering_admitted: false",
        "event_lowering_admitted: true",
    )
    path = tmp_path / "forged.yaml"
    path.write_text(forged, encoding="utf-8")

    with pytest.raises(DirectCczCapabilityError, match="recorded event admission"):
        load_direct_ccz_capability(path)


def test_loader_rejects_noncanonical_map_claiming_event_admission(tmp_path: Path) -> None:
    contents = EVENT_CAPABILITY_PATH.read_text(encoding="utf-8")
    forged = contents.replace(
        '"CZ(data_1,data_2)^{zz_0}"',
        '"CZ(data_0,data_1)^{zz_0}"',
    )
    path = tmp_path / "forged-map.yaml"
    path.write_text(forged, encoding="utf-8")

    with pytest.raises(DirectCczCapabilityError, match="recorded event admission"):
        load_direct_ccz_capability(path)
