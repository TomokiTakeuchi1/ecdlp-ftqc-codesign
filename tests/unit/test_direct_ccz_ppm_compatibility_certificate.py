from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import (
    DirectCczBackendAudit,
    DirectCczCapability,
    load_direct_ccz_backend_audit,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.compiler import (
    DirectCczEventTrace,
    lower_oop_qcla_to_direct_ccz_events,
    lower_qcla_to_direct_ccz_events,
)
from ecdlp_ftqc.scheduler import (
    analyze_qcla_direct_ccz_exact_anchor,
    certify_qcla_direct_ccz_ppm_compatibility,
    compare_certificate_to_exact_anchor,
    exact_anchor_compatibility_equivalence_to_data,
    qcla_ppm_compatibility_certificate_to_data,
)
from ecdlp_ftqc.verification import (
    replay_direct_ccz_ppm_compatibility,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)
BACKEND_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_finite_backend_audit_v1.yaml"
)


@pytest.fixture(scope="module")
def capability() -> DirectCczCapability:
    return load_direct_ccz_capability(CAPABILITY_PATH)


@pytest.fixture(scope="module")
def backend_audit() -> DirectCczBackendAudit:
    return load_direct_ccz_backend_audit(BACKEND_PATH)


def _certificate_data(
    width: int,
    variant: str,
    capability: DirectCczCapability,
) -> dict[str, object]:
    if variant == "oop":
        trace = build_oop_qcla_trace(width)
        events = lower_oop_qcla_to_direct_ccz_events(trace, capability)
        certificate = certify_qcla_direct_ccz_ppm_compatibility(
            trace, events, variant="oop"
        )
    else:
        trace = build_qcla_trace(width)
        events = lower_qcla_to_direct_ccz_events(trace, capability)
        certificate = certify_qcla_direct_ccz_ppm_compatibility(
            trace, events, variant="ip"
        )
    return qcla_ppm_compatibility_certificate_to_data(certificate)


def test_width_256_certificates_close_the_structural_lower_bounds(
    capability: DirectCczCapability,
) -> None:
    oop = _certificate_data(256, "oop", capability)
    ip = _certificate_data(256, "ip", capability)

    assert oop["compatibility_evidence_status"] == "PROVED"
    assert oop["candidate_optimality_evidence_status"] == "PROVED"
    assert oop["candidate_batch_level_count"] == 34
    assert oop["weighted_causal_lower_bound"] == 34
    assert oop["direct_ccz_event_count"] == 1_229
    assert oop["ppm_count"] == 7_374
    assert oop["theoretical_global_pair_count"] == 27_184_251

    assert ip["compatibility_evidence_status"] == "PROVED"
    assert ip["candidate_optimality_evidence_status"] == "PROVED"
    assert ip["candidate_batch_level_count"] == 68
    assert ip["weighted_causal_lower_bound"] == 68
    assert ip["direct_ccz_event_count"] == 2_458
    assert ip["ppm_count"] == 14_748
    assert ip["theoretical_global_pair_count"] == 108_744_378

    for item in (oop, ip):
        assert item["materialized_pair_count"] == 0
        assert item["complete_native_schedule"] is False
        assert item["surgery_rounds"] is None
        assert item["runtime_seconds"] is None
        assert item["physical_qubits"] is None
        assert item["failure_probability"] is None


@pytest.mark.parametrize("width", [5, 8, 9, 16, 17, 32, 33, 256, 257])
@pytest.mark.parametrize("variant", ["oop", "ip"])
def test_boundary_widths_have_linear_proved_certificates(
    width: int,
    variant: str,
    capability: DirectCczCapability,
) -> None:
    data = _certificate_data(width, variant, capability)
    assert data["compatibility_evidence_status"] == "PROVED"
    assert data["candidate_optimality_evidence_status"] == "PROVED"
    assert data["candidate_equals_causal_lower_bound"] is True
    assert data["materialized_pair_count"] == 0
    assert data["asymptotic_certificate_size"] == (
        "O(source_gates + source_dependencies + PPMs)"
    )
    batches = data["batches"]
    assert isinstance(batches, list)
    assert all(batch["general_high_rate_compatible"] for batch in batches)
    assert all(not batch["pair_records_materialized"] for batch in batches)


@pytest.mark.parametrize("variant", ["oop", "ip"])
def test_exact_width_five_anchor_matches_every_compact_batch(
    variant: str,
    capability: DirectCczCapability,
    backend_audit: DirectCczBackendAudit,
) -> None:
    if variant == "oop":
        trace = build_oop_qcla_trace(5)
        events = lower_oop_qcla_to_direct_ccz_events(trace, capability)
        certificate = certify_qcla_direct_ccz_ppm_compatibility(
            trace, events, variant="oop"
        )
        _, exact = analyze_qcla_direct_ccz_exact_anchor(
            trace, capability, backend_audit, variant="oop"
        )
    else:
        trace = build_qcla_trace(5)
        events = lower_qcla_to_direct_ccz_events(trace, capability)
        certificate = certify_qcla_direct_ccz_ppm_compatibility(
            trace, events, variant="ip"
        )
        _, exact = analyze_qcla_direct_ccz_exact_anchor(
            trace, capability, backend_audit, variant="ip"
        )
    comparison = compare_certificate_to_exact_anchor(certificate, exact)
    assert comparison.all_checks_passed
    assert comparison.batch_membership_digest_match
    assert comparison.every_materialized_intra_batch_pair_compatible
    assert comparison.every_exact_profile_y_free


def test_independent_replay_rebuilds_certificates_without_scheduler_or_compiler(
    capability: DirectCczCapability,
    backend_audit: DirectCczBackendAudit,
) -> None:
    certificates: list[dict[str, object]] = []
    equivalences: list[dict[str, object]] = []
    for variant in ("oop", "ip"):
        if variant == "oop":
            trace = build_oop_qcla_trace(5)
            events = lower_oop_qcla_to_direct_ccz_events(trace, capability)
            certificate = certify_qcla_direct_ccz_ppm_compatibility(
                trace, events, variant="oop"
            )
            _, exact = analyze_qcla_direct_ccz_exact_anchor(
                trace, capability, backend_audit, variant="oop"
            )
        else:
            trace = build_qcla_trace(5)
            events = lower_qcla_to_direct_ccz_events(trace, capability)
            certificate = certify_qcla_direct_ccz_ppm_compatibility(
                trace, events, variant="ip"
            )
            _, exact = analyze_qcla_direct_ccz_exact_anchor(
                trace, capability, backend_audit, variant="ip"
            )
        certificates.append(qcla_ppm_compatibility_certificate_to_data(certificate))
        equivalences.append(
            exact_anchor_compatibility_equivalence_to_data(
                compare_certificate_to_exact_anchor(certificate, exact)
            )
        )

    replay = replay_direct_ccz_ppm_compatibility(
        certificates,
        equivalences,
        expected_widths=(5,),
        expected_exact_widths=(5,),
    )
    assert replay.all_passed

    mutated = copy.deepcopy(certificates)
    batches = mutated[0]["batches"]
    assert isinstance(batches, list)
    batches[0]["ppm_operation_id_sha256"] = "0" * 64
    tampered = replay_direct_ccz_ppm_compatibility(
        mutated,
        equivalences,
        expected_widths=(5,),
        expected_exact_widths=(5,),
    )
    assert not tampered.all_passed
    assert not dict(tampered.checks)["independent_linear_certificate_match"]


def test_replay_rejects_a_fabricated_finite_runtime(
    capability: DirectCczCapability,
) -> None:
    certificates = [
        _certificate_data(5, variant, capability) for variant in ("oop", "ip")
    ]
    certificates[0]["runtime_seconds"] = 1.0
    replay = replay_direct_ccz_ppm_compatibility(
        certificates,
        (),
        expected_widths=(5,),
        expected_exact_widths=(),
    )
    assert not replay.all_passed
    checks = dict(replay.checks)
    assert not checks["independent_linear_certificate_match"]
    assert not checks["all_finite_outputs_null"]


def test_certifier_emits_a_minimal_witness_for_an_axis_contract_mutation(
    capability: DirectCczCapability,
) -> None:
    trace = build_oop_qcla_trace(5)
    events = lower_oop_qcla_to_direct_ccz_events(trace, capability)
    first_event = events.injection_events[0]
    bad_ppm = replace(first_event.ppms[0], pauli_terms=("X", "Z"))
    bad_event = replace(
        first_event,
        ppms=(bad_ppm, *first_event.ppms[1:]),
    )
    bad_trace = replace(
        events,
        injection_events=(bad_event, *events.injection_events[1:]),
    )
    assert isinstance(bad_trace, DirectCczEventTrace)

    certificate = certify_qcla_direct_ccz_ppm_compatibility(
        trace, bad_trace, variant="oop"
    )
    assert certificate.compatibility_evidence_status.value == "FALSIFIED"
    assert certificate.candidate_batch_level_count is None
    assert certificate.counterexample is not None
    assert certificate.counterexample.obligation == "canonical_ppm_shape"
    assert certificate.counterexample.event_id == first_event.event_id


def test_certifier_rejects_a_non_css_frame_generator(
    capability: DirectCczCapability,
) -> None:
    trace = build_oop_qcla_trace(5)
    events = lower_oop_qcla_to_direct_ccz_events(trace, capability)
    first_event = events.injection_events[0]
    bad_event = replace(
        first_event,
        correction_frame=("H(a)^x", *first_event.correction_frame[1:]),
    )
    bad_trace = replace(
        events,
        injection_events=(bad_event, *events.injection_events[1:]),
    )
    certificate = certify_qcla_direct_ccz_ppm_compatibility(
        trace, bad_trace, variant="oop"
    )
    assert certificate.counterexample is not None
    assert certificate.counterexample.obligation == (
        "computational_basis_preserving_frame"
    )
