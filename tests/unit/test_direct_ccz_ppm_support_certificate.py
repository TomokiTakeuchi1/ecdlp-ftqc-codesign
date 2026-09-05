from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.compiler import (
    lower_oop_qcla_to_direct_ccz_events,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    lower_qcla_to_direct_ccz_events,
    lower_qcla_to_symbolic_direct_ccz_ppm,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    certify_qcla_direct_ccz_ppm_support,
    compare_support_certificate_to_symbolic_trace,
    qcla_ppm_support_certificate_aggregate_to_data,
    qcla_ppm_support_certificate_summary_to_data,
)
from ecdlp_ftqc.verification import replay_direct_ccz_ppm_support

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = load_direct_ccz_capability(
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)


@pytest.mark.parametrize("width", [5, 8])
@pytest.mark.parametrize("variant", ["oop", "ip"])
def test_exact_support_certificate_matches_materialized_anchor(
    width: int,
    variant: str,
) -> None:
    if variant == "oop":
        trace = build_oop_qcla_trace(width)
        events = lower_oop_qcla_to_direct_ccz_events(trace, CAPABILITY)
        symbolic = lower_oop_qcla_to_symbolic_direct_ccz_ppm(trace, CAPABILITY)
    else:
        trace = build_qcla_trace(width)
        events = lower_qcla_to_direct_ccz_events(trace, CAPABILITY)
        symbolic = lower_qcla_to_symbolic_direct_ccz_ppm(trace, CAPABILITY)

    certificate = certify_qcla_direct_ccz_ppm_support(
        trace,
        events,
        variant=variant,  # type: ignore[arg-type]
    )
    comparison = compare_support_certificate_to_symbolic_trace(
        certificate,
        symbolic,
    )

    assert comparison.all_checks_passed
    assert comparison.evidence_status is EvidenceStatus.NUMERICAL
    assert certificate.all_possible_supports_exact
    assert certificate.support_envelope_evidence_status is EvidenceStatus.PROVED
    assert (
        certificate.outcome_independent_support_evidence_status
        is EvidenceStatus.FALSIFIED
    )
    assert certificate.branch_dependence_witness is not None


def test_first_exact_counterexample_falsifies_outcome_independence() -> None:
    trace = build_oop_qcla_trace(5)
    events = lower_oop_qcla_to_direct_ccz_events(trace, CAPABILITY)
    certificate = certify_qcla_direct_ccz_ppm_support(
        trace,
        events,
        variant="oop",
    )

    witness = certificate.branch_dependence_witness
    assert witness is not None
    assert witness.operation_id == "direct-ccz:000005:ppm:zz_0"
    assert witness.source_gate_id == "qcla-oop:000008"
    assert witness.source_algorithmic_layer == 4
    assert witness.logical_value == "a:0"
    assert witness.anf_monomials == (
        ("direct-ccz:000000:outcome:zz_1",),
    )
    assert witness.zero_assignment == (
        ("direct-ccz:000000:outcome:zz_1", 0),
    )
    assert witness.one_assignment == (
        ("direct-ccz:000000:outcome:zz_1", 1),
    )


def test_ip_mode_switch_keeps_sound_evidence_labels() -> None:
    exact_trace = build_qcla_trace(8)
    exact = certify_qcla_direct_ccz_ppm_support(
        exact_trace,
        lower_qcla_to_direct_ccz_events(exact_trace, CAPABILITY),
        variant="ip",
    )
    sampled_trace = build_qcla_trace(9)
    sampled = certify_qcla_direct_ccz_ppm_support(
        sampled_trace,
        lower_qcla_to_direct_ccz_events(sampled_trace, CAPABILITY),
        variant="ip",
    )

    assert exact.deterministic_branch_sample_count == 0
    assert exact.exact_activity_monomial_count is not None
    assert sampled.deterministic_branch_sample_count == 512
    assert sampled.exact_activity_monomial_count is None
    assert sampled.support_envelope_evidence_status in {
        EvidenceStatus.PROVED,
        EvidenceStatus.CHECK,
    }


@pytest.fixture(scope="module")
def width_256_certificates() -> tuple[object, object]:
    oop_trace = build_oop_qcla_trace(256)
    oop = certify_qcla_direct_ccz_ppm_support(
        oop_trace,
        lower_oop_qcla_to_direct_ccz_events(oop_trace, CAPABILITY),
        variant="oop",
    )
    ip_trace = build_qcla_trace(256)
    ip = certify_qcla_direct_ccz_ppm_support(
        ip_trace,
        lower_qcla_to_direct_ccz_events(ip_trace, CAPABILITY),
        variant="ip",
    )
    return oop, ip


def test_width_256_support_brackets_and_no_native_outputs(
    width_256_certificates: tuple[object, object],
) -> None:
    oop, ip = width_256_certificates

    assert oop.ppm_count == 7_374  # type: ignore[attr-defined]
    assert oop.branch_dependent_profile_count == 1_924  # type: ignore[attr-defined]
    assert oop.maximum_ppm_weight_upper_bound == 1_003  # type: ignore[attr-defined]
    assert oop.maximum_witnessed_support_union_size == 1_003  # type: ignore[attr-defined]
    assert oop.maximum_sampled_branch_weight is None  # type: ignore[attr-defined]
    assert oop.maximum_batch_possible_contact_count == 129  # type: ignore[attr-defined]
    assert oop.all_possible_supports_exact  # type: ignore[attr-defined]

    assert ip.ppm_count == 14_748  # type: ignore[attr-defined]
    assert ip.branch_dependent_profile_count == 5_355  # type: ignore[attr-defined]
    assert ip.maximum_ppm_weight_upper_bound == 1_006  # type: ignore[attr-defined]
    assert ip.maximum_witnessed_support_union_size == 935  # type: ignore[attr-defined]
    assert ip.maximum_sampled_branch_weight == 509  # type: ignore[attr-defined]
    assert ip.maximum_batch_possible_contact_count == 567  # type: ignore[attr-defined]
    assert ip.maximum_batch_witnessed_contact_count == 523  # type: ignore[attr-defined]
    assert not ip.all_possible_supports_exact  # type: ignore[attr-defined]
    assert ip.support_envelope_evidence_status is EvidenceStatus.CHECK  # type: ignore[attr-defined]

    for certificate in (oop, ip):
        assert certificate.complete_native_schedule is False  # type: ignore[attr-defined]
        assert certificate.surgery_rounds is None  # type: ignore[attr-defined]
        assert certificate.runtime_seconds is None  # type: ignore[attr-defined]
        assert certificate.physical_qubits is None  # type: ignore[attr-defined]
        assert certificate.failure_probability is None  # type: ignore[attr-defined]


def test_independent_replay_detects_hypergraph_tampering(
    width_256_certificates: tuple[object, object],
) -> None:
    oop, ip = width_256_certificates
    aggregates = [
        qcla_ppm_support_certificate_aggregate_to_data(oop),  # type: ignore[arg-type]
        qcla_ppm_support_certificate_aggregate_to_data(ip),  # type: ignore[arg-type]
    ]
    hypergraphs = [
        qcla_ppm_support_certificate_summary_to_data(oop),  # type: ignore[arg-type]
        qcla_ppm_support_certificate_summary_to_data(ip),  # type: ignore[arg-type]
    ]

    replay = replay_direct_ccz_ppm_support(
        aggregates,
        hypergraphs,
        expected_widths=(256,),
    )
    assert replay.all_passed

    tampered = deepcopy(hypergraphs)
    tampered[0]["profiles"][0]["possible_logical_support"].append("tampered")
    tampered_replay = replay_direct_ccz_ppm_support(
        aggregates,
        tampered,
        expected_widths=(256,),
    )
    assert not tampered_replay.all_passed


def test_noncanonical_correction_map_fails_closed() -> None:
    trace = build_oop_qcla_trace(5)
    events = lower_oop_qcla_to_direct_ccz_events(trace, CAPABILITY)
    first = events.injection_events[0]
    mutated_first = replace(
        first,
        correction_frame=(
            first.correction_frame[1],
            first.correction_frame[0],
            *first.correction_frame[2:],
        ),
    )
    mutated = replace(
        events,
        injection_events=(mutated_first, *events.injection_events[1:]),
    )

    certificate = certify_qcla_direct_ccz_ppm_support(
        trace,
        mutated,
        variant="oop",
    )

    assert certificate.support_envelope_evidence_status is EvidenceStatus.FALSIFIED
    assert certificate.validation_counterexample is not None
    assert (
        certificate.validation_counterexample.obligation
        == "canonical_support_changing_correction_map"
    )
    assert certificate.profiles == ()
    assert certificate.candidate_batch_level_count is None
