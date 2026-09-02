from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import (
    load_direct_ccz_backend_audit,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.scheduler import (
    DirectCczPpmScalingError,
    analyze_qcla_direct_ccz_exact_anchor,
    analyze_qcla_direct_ccz_structural_point,
    assess_qcla_direct_ccz_finite_scaling_admission,
    qcla_direct_ccz_exact_anchor_to_data,
    qcla_direct_ccz_finite_scaling_admission_to_data,
    qcla_direct_ccz_structural_point_to_data,
)
from ecdlp_ftqc.verification import replay_direct_ccz_ppm_scaling

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = (
    ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
)
AUDIT_PATH = (
    ROOT / "configs" / "architectures" / "direct_ccz_finite_backend_audit_v1.yaml"
)


@pytest.fixture(scope="module")
def scaling_data() -> dict[str, object]:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    widths = (2, 5, 256)
    points = []
    anchors = []
    for width in widths:
        for variant in ("oop", "ip"):
            source = (
                build_oop_qcla_trace(width)
                if variant == "oop"
                else build_qcla_trace(width)
            )
            point = analyze_qcla_direct_ccz_structural_point(
                source,
                capability,
                variant=variant,
            )
            points.append(qcla_direct_ccz_structural_point_to_data(point))
            if width == 2:
                anchor, _ = analyze_qcla_direct_ccz_exact_anchor(
                    source,
                    capability,
                    audit,
                    variant=variant,
                )
                anchors.append(qcla_direct_ccz_exact_anchor_to_data(anchor))
    finite = qcla_direct_ccz_finite_scaling_admission_to_data(
        assess_qcla_direct_ccz_finite_scaling_admission(capability, audit)
    )
    replay = replay_direct_ccz_ppm_scaling(
        points,
        anchors,
        finite,
        expected_widths=widths,
        expected_exact_widths=(2,),
    )
    return {
        "anchors": anchors,
        "finite": finite,
        "points": points,
        "replay": replay,
    }


def test_width_five_structural_points_match_reviewed_counts() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    oop = analyze_qcla_direct_ccz_structural_point(
        build_oop_qcla_trace(5), capability, variant="oop"
    )
    ip = analyze_qcla_direct_ccz_structural_point(
        build_qcla_trace(5), capability, variant="ip"
    )

    assert (
        oop.source_gate_count,
        oop.source_toffoli_count,
        oop.ppm_count,
        oop.weighted_causal_ppm_level_lower_bound,
        oop.theoretical_pair_count,
    ) == (23, 10, 60, 12, 1770)
    assert (
        ip.source_gate_count,
        ip.source_toffoli_count,
        ip.ppm_count,
        ip.weighted_causal_ppm_level_lower_bound,
        ip.theoretical_pair_count,
    ) == (43, 20, 120, 24, 7140)
    assert (oop.cleanup_operation_count, oop.cleanup_toffoli_count) == (5, 1)
    assert (ip.cleanup_operation_count, ip.cleanup_toffoli_count) == (17, 10)


def test_width_256_is_compact_and_does_not_claim_a_schedule(
    scaling_data: dict[str, object],
) -> None:
    points = scaling_data["points"]
    oop = points[-2]  # type: ignore[index]
    ip = points[-1]  # type: ignore[index]

    assert oop["direct_ccz_event_count"] == 1229  # type: ignore[index]
    assert oop["ppm_count"] == 7374  # type: ignore[index]
    assert oop["theoretical_pair_count"] == 27_184_251  # type: ignore[index]
    assert oop["weighted_causal_ppm_level_lower_bound"] == 34  # type: ignore[index]
    assert ip["direct_ccz_event_count"] == 2458  # type: ignore[index]
    assert ip["ppm_count"] == 14_748  # type: ignore[index]
    assert ip["theoretical_pair_count"] == 108_744_378  # type: ignore[index]
    assert ip["weighted_causal_ppm_level_lower_bound"] == 68  # type: ignore[index]
    for point in (oop, ip):
        assert point["pair_table_materialized"] is False  # type: ignore[index]
        assert point["candidate_compatibility_status"] == "OPEN"  # type: ignore[index]
        assert point["source_two_phase_envelope_status"] == "CHECK"  # type: ignore[index]


def test_exact_anchor_closes_only_the_explicit_width(
    scaling_data: dict[str, object],
) -> None:
    anchors = scaling_data["anchors"]

    assert [(item["variant"], item["width"]) for item in anchors] == [  # type: ignore[union-attr]
        ("oop", 2),
        ("ip", 2),
    ]
    assert [item["candidate_batch_level_count"] for item in anchors] == [2, 4]  # type: ignore[union-attr]
    assert all(item["candidate_optimality_evidence_status"] == "PROVED" for item in anchors)  # type: ignore[union-attr]


def test_finite_scaling_admission_keeps_all_native_outputs_null(
    scaling_data: dict[str, object],
) -> None:
    finite = scaling_data["finite"]
    prohibited = (
        "ccz_buffer_trajectory",
        "decoder_service",
        "failure_probability",
        "memory_traffic",
        "native_schedule",
        "physical_qubits",
        "reaction_latency_seconds",
        "routing_cost",
        "runtime_seconds",
        "surgery_rounds",
    )

    assert finite["event_lowering_admitted"] is True  # type: ignore[index]
    assert finite["high_rate_capability_admitted"] is False  # type: ignore[index]
    assert finite["finite_backend_admitted"] is False  # type: ignore[index]
    assert finite["scaling_native_mapper_admitted"] is False  # type: ignore[index]
    assert all(finite[name] is None for name in prohibited)  # type: ignore[index]


def test_independent_replay_rebuilds_every_source_point(
    scaling_data: dict[str, object],
) -> None:
    replay = scaling_data["replay"]

    assert replay.all_passed  # type: ignore[union-attr]
    assert replay.structural_point_count == 6  # type: ignore[union-attr]
    assert replay.exact_anchor_count == 2  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("target", "field", "replacement"),
    [
        ("points", "theoretical_pair_count", 1),
        ("anchors", "candidate_batch_level_count", 999),
        ("finite", "runtime_seconds", 1.0),
    ],
)
def test_independent_replay_detects_tampering(
    scaling_data: dict[str, object],
    target: str,
    field: str,
    replacement: object,
) -> None:
    points = copy.deepcopy(scaling_data["points"])
    anchors = copy.deepcopy(scaling_data["anchors"])
    finite = copy.deepcopy(scaling_data["finite"])
    if target == "points":
        points[0][field] = replacement
    elif target == "anchors":
        anchors[0][field] = replacement
    else:
        finite[field] = replacement

    replay = replay_direct_ccz_ppm_scaling(
        points,
        anchors,
        finite,
        expected_widths=(2, 5, 256),
        expected_exact_widths=(2,),
    )
    assert not replay.all_passed


def test_variant_mismatch_is_rejected() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)

    with pytest.raises(DirectCczPpmScalingError, match="IP variant"):
        analyze_qcla_direct_ccz_structural_point(
            build_oop_qcla_trace(5), capability, variant="ip"
        )


def test_independent_replay_has_no_compiler_or_scheduler_import() -> None:
    source = (
        ROOT
        / "src"
        / "ecdlp_ftqc"
        / "verification"
        / "direct_ccz_ppm_scaling_replay.py"
    ).read_text(encoding="utf-8")

    assert "from ecdlp_ftqc.compiler" not in source
    assert "from ecdlp_ftqc.scheduler" not in source
