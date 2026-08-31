from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import (
    REQUIRED_DIRECT_CCZ_BACKEND_FIELDS,
    DirectCczBackendAuditError,
    load_direct_ccz_backend_audit,
)
from ecdlp_ftqc.metadata import EvidenceStatus

AUDIT_PATH = Path("configs/architectures/direct_ccz_finite_backend_audit_v1.yaml")


def test_real_candidate_is_complete_as_an_audit_but_not_admitted() -> None:
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)

    assert tuple(item.field_id for item in audit.candidate.field_evidence) == (
        REQUIRED_DIRECT_CCZ_BACKEND_FIELDS
    )
    assert not audit.candidate.backend_admitted
    assert audit.candidate.missing_fields == (
        "consumer.batch_size",
        "consumer.parallel_ppm_layers",
        "consumer.duration_rounds",
        "consumer.logical_error_per_batch",
        "controller.decoder_throughput",
        "controller.reaction_latency",
        "processor.injection_port_capacity",
        "processor.logical_capacity",
        "processor.routing_model",
        "factory.delivery_latency",
        "factory.buffer_capacity",
        "factory.storage_error_per_cycle",
        "compatibility.factory_to_consumer_adapter",
    )
    assert audit.candidate.incompatible_fields == (
        "factory.batch_size",
        "factory.production_cycles",
        "factory.output_error_probability",
    )


def test_portable_event_contract_does_not_inherit_physical_admission() -> None:
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    event = audit.candidate.field_evidence[0]

    assert event.field_id == "consumer.event_semantics"
    assert event.admitted_value == "figure14-six-ppm-direct-ccz-event-v1"
    assert event.compatibility_domain != audit.candidate.compatibility_domain
    assert event.field_id not in audit.candidate.incompatible_fields
    assert not audit.candidate.backend_admitted


def test_finite_values_from_another_architecture_are_not_composed() -> None:
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    fields = {item.field_id: item for item in audit.candidate.field_evidence}

    assert fields["factory.batch_size"].admitted_value == "10"
    assert fields["factory.production_cycles"].admitted_value == "120"
    assert fields["factory.batch_size"].compatibility_domain == (
        "cain-bb18-space-balanced-v1"
    )
    assert fields["factory.batch_size"].compatibility_domain != (
        audit.candidate.compatibility_domain
    )
    assert not audit.candidate.backend_admitted


def test_synthetic_complete_coherent_candidate_is_admitted() -> None:
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    source_id = audit.sources[0].source_id
    candidate = replace(
        audit.candidate,
        field_evidence=tuple(
            replace(
                item,
                reported_value=item.reported_value or "synthetic finite value",
                admitted_value=item.admitted_value or "synthetic finite value",
                evidence_status=EvidenceStatus.LITERATURE,
                source_ids=item.source_ids or (source_id,),
                compatibility_domain=(
                    item.compatibility_domain
                    if item.field_id == "consumer.event_semantics"
                    else audit.candidate.compatibility_domain
                ),
            )
            for item in audit.candidate.field_evidence
        ),
        evidence_status=EvidenceStatus.LITERATURE,
    )
    admitted = replace(
        audit,
        candidate=candidate,
        recorded_backend_admitted=True,
    )

    assert admitted.candidate.missing_fields == ()
    assert admitted.candidate.incompatible_fields == ()
    assert admitted.candidate.backend_admitted


def test_complete_mixed_domain_candidate_is_rejected() -> None:
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    source_id = audit.sources[0].source_id
    fields = tuple(
        replace(
            item,
            reported_value=item.reported_value or "synthetic finite value",
            admitted_value=item.admitted_value or "synthetic finite value",
            evidence_status=EvidenceStatus.LITERATURE,
            source_ids=item.source_ids or (source_id,),
            compatibility_domain=(
                "other-backend-v1"
                if item.field_id == "processor.routing_model"
                else (
                    item.compatibility_domain
                    if item.field_id == "consumer.event_semantics"
                    else audit.candidate.compatibility_domain
                )
            ),
        )
        for item in audit.candidate.field_evidence
    )
    mixed = replace(audit.candidate, field_evidence=fields)

    assert mixed.missing_fields == ()
    assert mixed.incompatible_fields == ("processor.routing_model",)
    assert not mixed.backend_admitted


def test_loader_rejects_forged_admission_flag(tmp_path: Path) -> None:
    contents = AUDIT_PATH.read_text(encoding="utf-8")
    path = tmp_path / "forged.yaml"
    path.write_text(
        contents.replace("recorded_backend_admitted: false", "recorded_backend_admitted: true"),
        encoding="utf-8",
    )

    with pytest.raises(DirectCczBackendAuditError, match="recorded backend admission"):
        load_direct_ccz_backend_audit(path)


def test_loader_rejects_omitted_required_field(tmp_path: Path) -> None:
    contents = AUDIT_PATH.read_text(encoding="utf-8")
    start = contents.index("    - field_id: factory.buffer_capacity\n")
    end = contents.index("    - field_id: factory.storage_error_per_cycle\n")
    path = tmp_path / "missing-field.yaml"
    path.write_text(contents[:start] + contents[end:], encoding="utf-8")

    with pytest.raises(DirectCczBackendAuditError, match="every required field"):
        load_direct_ccz_backend_audit(path)


def test_screened_finite_ports_do_not_claim_direct_ccz() -> None:
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    components = {item.component_id: item for item in audit.screened_components}

    assert "T states" in components["mitten-parallel-t-port"].exclusion
    assert "T-state" in components["canonical-lp-column-t-port"].contribution
    assert "Y states" in components["in-situ-css-injection"].exclusion
    assert "target-code gate teleportation" in components["tricycle-ccz-source"].exclusion
