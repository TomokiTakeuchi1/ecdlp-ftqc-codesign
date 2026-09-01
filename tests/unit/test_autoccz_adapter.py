from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import (
    REQUIRED_AUTOCCZ_SERVICE_FIELDS,
    AutoCczAdapterError,
    load_autoccz_service_audit,
)
from ecdlp_ftqc.metadata import EvidenceStatus

AUDIT_PATH = Path("configs/architectures/autoccz_surface_code_adapter_v1.yaml")


def test_real_candidate_admits_adapter_but_rejects_complete_service() -> None:
    audit = load_autoccz_service_audit(AUDIT_PATH)

    assert tuple(item.field_id for item in audit.candidate.field_evidence) == (
        REQUIRED_AUTOCCZ_SERVICE_FIELDS
    )
    assert audit.candidate.adapter_admitted
    assert not audit.candidate.service_admitted
    assert audit.candidate.missing_fields == (
        "consumer.consumption_interval_cycles",
        "consumer.logical_error_per_event",
        "controller.decoder_throughput",
        "controller.reaction_latency_seconds",
        "processor.logical_capacity",
        "factory.delivery_latency_cycles",
        "factory.buffer_capacity",
        "factory.storage_error_per_cycle",
        "compatibility.same_domain_failure_budget",
    )
    assert audit.candidate.incompatible_fields == (
        "factory.output_error_probability",
    )


def test_source_example_arithmetic_is_recomputed() -> None:
    model = load_autoccz_service_audit(AUDIT_PATH).model

    assert model.level_1_effective_cycles_per_ccz == pytest.approx(
        130.33333333333334
    )
    assert model.level_2_cycles_per_ccz == 135
    assert model.level_1_rate_hz == pytest.approx(7672.634271099743)
    assert model.level_2_rate_hz == pytest.approx(7407.407407407407)
    assert model.factory_rate_hz == model.level_2_rate_hz
    assert model.bottleneck == "level_2"
    assert model.reaction_demand_rate_hz == pytest.approx(100000.0)
    assert model.factories_for_reaction_limited_demand == 14


def test_assumed_reaction_loop_is_reported_but_not_admitted() -> None:
    audit = load_autoccz_service_audit(AUDIT_PATH)
    fields = {item.field_id: item for item in audit.candidate.field_evidence}

    reaction = fields["controller.reaction_latency_seconds"]
    interval = fields["consumer.consumption_interval_cycles"]
    assert reaction.reported_value == "0.00001"
    assert reaction.evidence_status is EvidenceStatus.CHECK
    assert reaction.admitted_value is None
    assert interval.reported_value == "10"
    assert interval.evidence_status is EvidenceStatus.CHECK
    assert interval.admitted_value is None


def test_official_calculator_error_is_kept_in_its_original_domain() -> None:
    audit = load_autoccz_service_audit(AUDIT_PATH)
    fields = {item.field_id: item for item in audit.candidate.field_evidence}
    output_error = fields["factory.output_error_probability"]

    assert output_error.reported_value == "0.0000000000533332000000001"
    assert output_error.compatibility_domain == (
        "gidney-fowler-ccz-factory-d15-d31-v3"
    )
    assert output_error.compatibility_domain != audit.candidate.compatibility_domain
    assert "factory.output_error_probability" in audit.candidate.incompatible_fields


def test_adapter_and_source_assets_remain_in_one_domain() -> None:
    audit = load_autoccz_service_audit(AUDIT_PATH)
    fields = {item.field_id: item for item in audit.candidate.field_evidence}
    adapter = fields["compatibility.factory_to_consumer_adapter"]

    assert adapter.admitted_value == (
        "ccz-output-to-autoccz-fixup-to-toffoli-consumer-v1"
    )
    assert adapter.compatibility_domain == audit.candidate.compatibility_domain
    assert len(audit.source_assets) == 4
    assert {asset.asset_id for asset in audit.source_assets} == {
        "autoccz-ccz-factory-layout",
        "autoccz-fixup-layout",
        "base-ccz-factory-calculator",
        "base-ccz-factory-layout",
    }


def test_synthetic_complete_same_domain_service_is_admitted() -> None:
    audit = load_autoccz_service_audit(AUDIT_PATH)
    source_id = audit.sources[0].source_id
    fields = tuple(
        replace(
            item,
            reported_value=item.reported_value or "synthetic finite value",
            admitted_value=item.admitted_value or "synthetic finite value",
            evidence_status=EvidenceStatus.LITERATURE,
            source_ids=item.source_ids or (source_id,),
            compatibility_domain=audit.candidate.compatibility_domain,
        )
        for item in audit.candidate.field_evidence
    )
    candidate = replace(audit.candidate, field_evidence=fields)
    admitted = replace(audit, candidate=candidate, recorded_service_admitted=True)

    assert admitted.candidate.missing_fields == ()
    assert admitted.candidate.incompatible_fields == ()
    assert admitted.candidate.adapter_admitted
    assert admitted.candidate.service_admitted


def test_loader_rejects_forged_service_admission(tmp_path: Path) -> None:
    contents = AUDIT_PATH.read_text(encoding="utf-8")
    path = tmp_path / "forged-service.yaml"
    path.write_text(
        contents.replace(
            "recorded_service_admitted: false",
            "recorded_service_admitted: true",
        ),
        encoding="utf-8",
    )

    with pytest.raises(AutoCczAdapterError, match="recorded service admission"):
        load_autoccz_service_audit(path)


def test_loader_rejects_forged_adapter_admission(tmp_path: Path) -> None:
    contents = AUDIT_PATH.read_text(encoding="utf-8")
    path = tmp_path / "forged-adapter.yaml"
    path.write_text(
        contents.replace(
            "recorded_adapter_admitted: true",
            "recorded_adapter_admitted: false",
        ),
        encoding="utf-8",
    )

    with pytest.raises(AutoCczAdapterError, match="recorded adapter admission"):
        load_autoccz_service_audit(path)


def test_loader_rejects_forged_derived_factory_count(tmp_path: Path) -> None:
    contents = AUDIT_PATH.read_text(encoding="utf-8")
    path = tmp_path / "forged-count.yaml"
    path.write_text(
        contents.replace(
            "factories_for_reaction_limited_demand: 14",
            "factories_for_reaction_limited_demand: 13",
        ),
        encoding="utf-8",
    )

    with pytest.raises(AutoCczAdapterError, match="recorded factory count"):
        load_autoccz_service_audit(path)


def test_loader_rejects_omitted_required_field(tmp_path: Path) -> None:
    contents = AUDIT_PATH.read_text(encoding="utf-8")
    start = contents.index("    - field_id: factory.buffer_capacity\n")
    end = contents.index("    - field_id: factory.storage_error_per_cycle\n")
    path = tmp_path / "missing-field.yaml"
    path.write_text(contents[:start] + contents[end:], encoding="utf-8")

    with pytest.raises(AutoCczAdapterError, match="every AutoCCZ service field"):
        load_autoccz_service_audit(path)
