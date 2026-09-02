import copy
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import (
    direct_ccz_backend_audit_to_data,
    direct_ccz_capability_to_data,
    load_direct_ccz_backend_audit,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace, qcla_metrics
from ecdlp_ftqc.compiler import (
    DirectCczPpmTraceError,
    dumps_symbolic_direct_ccz_ppm_trace,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    lower_qcla_to_direct_ccz_events,
    lower_qcla_to_symbolic_direct_ccz_ppm,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.scheduler import (
    analyze_direct_ccz_ppm_batches,
    finite_instance_admission_to_data,
    general_high_rate_candidate_to_data,
    low_rate_fallback_to_data,
    strategy_frontier_to_data,
)
from ecdlp_ftqc.verification import (
    DirectCczPpmReplayError,
    replay_direct_ccz_ppm_batching,
    replay_ip_qcla_symbolic_direct_ccz_ppm_trace,
)

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = (
    ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
)
AUDIT_PATH = (
    ROOT / "configs" / "architectures" / "direct_ccz_finite_backend_audit_v1.yaml"
)


@pytest.fixture(scope="module")
def phase_d() -> dict[str, object]:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    source = build_qcla_trace(5)
    event_trace = lower_qcla_to_direct_ccz_events(source, capability)
    trace = lower_qcla_to_symbolic_direct_ccz_ppm(source, capability)
    trace_data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    semantic_replay = replay_ip_qcla_symbolic_direct_ccz_ppm_trace(
        source,
        trace_data,
    )
    analysis = analyze_direct_ccz_ppm_batches(trace, capability, audit)
    general_data = general_high_rate_candidate_to_data(analysis.general)
    finite_data = finite_instance_admission_to_data(analysis.finite)
    fallback_data = low_rate_fallback_to_data(analysis.fallback)
    frontier_data = strategy_frontier_to_data(analysis.frontier)
    batching_replay = replay_direct_ccz_ppm_batching(
        trace_data,
        general_data,
        finite_data,
        fallback_data,
        frontier_data,
        direct_ccz_capability_to_data(capability),
        direct_ccz_backend_audit_to_data(audit),
    )
    return {
        "analysis": analysis,
        "batching_replay": batching_replay,
        "capability": capability,
        "event_trace": event_trace,
        "finite_data": finite_data,
        "general_data": general_data,
        "semantic_replay": semantic_replay,
        "source": source,
        "trace": trace,
        "trace_data": trace_data,
    }


def test_width_five_ip_source_and_event_projection_are_complete(
    phase_d: dict[str, object],
) -> None:
    source = phase_d["source"]
    event_trace = phase_d["event_trace"]
    metrics = qcla_metrics(source)  # type: ignore[arg-type]

    assert (
        metrics.gate_count,
        metrics.x_count,
        metrics.cnot_count,
        metrics.toffoli_count,
        metrics.source_layer_count,
        len(source.dependencies),  # type: ignore[union-attr]
    ) == (43, 8, 15, 20, 18, 75)
    assert len(event_trace.injection_events) == 20  # type: ignore[union-attr]
    assert len(event_trace.passthrough_clifford_gate_ids) == 23  # type: ignore[union-attr]
    assert event_trace.complete_native_schedule is False  # type: ignore[union-attr]


@pytest.mark.parametrize("width", [2, 3, 4])
def test_all_smaller_ip_widths_pass_independent_semantic_replay(width: int) -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    source = build_qcla_trace(width)
    trace = lower_qcla_to_symbolic_direct_ccz_ppm(source, capability)
    replay = replay_ip_qcla_symbolic_direct_ccz_ppm_trace(
        source,
        symbolic_direct_ccz_ppm_trace_to_data(trace),
    )

    assert replay.all_passed
    assert replay.source_basis_input_pairs_checked == 1 << (2 * width)
    assert replay.injection_count == qcla_metrics(source).toffoli_count
    assert replay.ppm_count == 6 * replay.injection_count
    assert replay.complete_native_schedule is False


def test_ip_lowering_uses_shared_direct_ccz_ir_without_seven_t(
    phase_d: dict[str, object],
) -> None:
    trace = phase_d["trace"]

    assert len(trace.source_operations) == 43  # type: ignore[union-attr]
    assert len(trace.injections) == 20  # type: ignore[union-attr]
    assert len(trace.ppms) == 120  # type: ignore[union-attr]
    assert len(trace.correction_updates) == 120  # type: ignore[union-attr]
    assert len(trace.macro_layer_frames) == 18  # type: ignore[union-attr]
    assert len(trace.source_dependencies) == 75  # type: ignore[union-attr]
    assert len(trace.logical_lifetimes) == 15  # type: ignore[union-attr]
    assert len(trace.resource_lifetimes) == 20  # type: ignore[union-attr]
    assert trace.compiler_ancilla_lifetimes == ()  # type: ignore[union-attr]
    roles = Counter(
        instruction.role for instruction in trace.clifford_instructions  # type: ignore[union-attr]
    )
    assert roles == Counter(
        {
            "injection_basis_change_before": 20,
            "injection_basis_change_after": 20,
            "passthrough_cnot": 15,
            "passthrough_x": 8,
        }
    )
    assert all("seven" not in item.lowering_kind for item in trace.source_operations)  # type: ignore[union-attr]


def test_independent_ip_replay_checks_frames_truth_tables_and_semantics(
    phase_d: dict[str, object],
) -> None:
    replay = phase_d["semantic_replay"]

    assert replay.all_passed  # type: ignore[union-attr]
    assert replay.correction_truth_table_rows_checked == 1280  # type: ignore[union-attr]
    assert replay.frame_transition_count_checked == 43  # type: ignore[union-attr]
    assert replay.frame_probe_assignment_count == 124  # type: ignore[union-attr]
    assert replay.presented_observable_checks == 14880  # type: ignore[union-attr]
    assert replay.source_basis_input_pairs_checked == 1024  # type: ignore[union-attr]
    assert replay.local_injection_branch_count == 64  # type: ignore[union-attr]
    assert replay.local_injection_maximum_operator_error == 0.0  # type: ignore[union-attr]


def test_ip_exact_relations_and_causal_bound_close_twenty_four_levels(
    phase_d: dict[str, object],
) -> None:
    analysis = phase_d["analysis"]
    general = analysis.general  # type: ignore[union-attr]
    schedule = general.optimized_schedule

    assert len(general.observable_profiles) == 120
    assert len(general.pair_relations) == 7140
    assert sum(profile.has_possible_y for profile in general.observable_profiles) == 0
    assert sum(not item.universally_commuting for item in general.pair_relations) == 60
    assert sum(
        not item.universally_axis_consistent for item in general.pair_relations
    ) == 60
    assert sum(item.causal_order != "none" for item in general.pair_relations) == 6012
    assert sum(item.reaction_dependent for item in general.pair_relations) == 5832
    assert schedule.candidate_batch_level_count == 24
    assert schedule.causal_critical_path_lower_bound == 24
    assert schedule.combined_batch_level_lower_bound == 24
    assert schedule.optimality_evidence_status.value == "PROVED"
    assert schedule.fallback_operation_count == 0
    assert [len(batch.operation_ids) for batch in schedule.batches] == [
        12,
        12,
        6,
        6,
        *([3] * 14),
        6,
        6,
        9,
        9,
        6,
        6,
    ]


def test_large_frame_weight_fields_are_explicit_conservative_bounds(
    phase_d: dict[str, object],
) -> None:
    analysis = phase_d["analysis"]
    profiles = analysis.general.observable_profiles  # type: ignore[union-attr]
    bounded = tuple(profile for profile in profiles if not profile.weight_bounds_exact)

    assert len(bounded) == 7
    assert max(len(profile.variables) for profile in profiles) == 42
    assert all(profile.distinct_branch_observables is None for profile in bounded)
    assert all(profile.minimum_weight == 1 for profile in bounded)
    assert max(profile.maximum_weight for profile in bounded) == 14
    assert all(
        "maximum_ppm_weight_is_conservative_support_union_upper_bound"
        in batch.unresolved_general_obligations
        for batch in analysis.general.optimized_schedule.batches  # type: ignore[union-attr]
        if any(operation_id in {item.operation_id for item in bounded} for operation_id in batch.operation_ids)
    )


def test_independent_batch_replay_and_finite_rejection(
    phase_d: dict[str, object],
) -> None:
    replay = phase_d["batching_replay"]
    finite = phase_d["finite_data"]

    assert replay.all_passed  # type: ignore[union-attr]
    assert replay.ppm_count == 120  # type: ignore[union-attr]
    assert replay.pair_relation_count == 7140  # type: ignore[union-attr]
    assert replay.optimized_candidate_batch_levels == 24  # type: ignore[union-attr]
    assert replay.causal_lower_bound == 24  # type: ignore[union-attr]
    assert replay.low_rate_singleton_count == 120  # type: ignore[union-attr]
    assert finite["verdict"] == (  # type: ignore[index]
        "REJECTED_MISSING_OR_INCOMPATIBLE_FINITE_BACKEND_EVIDENCE"
    )
    assert finite["schedule"] is None  # type: ignore[index]
    assert finite["runtime_seconds"] is None  # type: ignore[index]
    assert finite["physical_qubits"] is None  # type: ignore[index]
    assert finite["failure_probability"] is None  # type: ignore[index]


def test_ip_replay_rejects_tampered_x_passthrough(
    phase_d: dict[str, object],
) -> None:
    source = phase_d["source"]
    tampered = copy.deepcopy(phase_d["trace_data"])
    x_instruction = next(
        item
        for item in tampered["clifford_instructions"]  # type: ignore[index]
        if item["role"] == "passthrough_x"
    )
    x_instruction["logical_gate"]["kind"] = "Z"

    with pytest.raises(DirectCczPpmReplayError, match="pass-through Clifford"):
        replay_ip_qcla_symbolic_direct_ccz_ppm_trace(source, tampered)  # type: ignore[arg-type]


def test_ip_trace_is_deterministic_and_rejects_native_schedule(
    phase_d: dict[str, object],
) -> None:
    capability = phase_d["capability"]
    source = build_qcla_trace(5)
    first = lower_qcla_to_symbolic_direct_ccz_ppm(source, capability)  # type: ignore[arg-type]
    second = lower_qcla_to_symbolic_direct_ccz_ppm(source, capability)  # type: ignore[arg-type]

    assert dumps_symbolic_direct_ccz_ppm_trace(first) == (
        dumps_symbolic_direct_ccz_ppm_trace(second)
    )
    with pytest.raises(DirectCczPpmTraceError, match="cannot claim a native schedule"):
        replace(first, complete_native_schedule=True)


def test_oop_symbolic_trace_remains_byte_identical() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    trace = lower_oop_qcla_to_symbolic_direct_ccz_ppm(
        build_oop_qcla_trace(5),
        capability,
    )
    expected = (
        ROOT
        / "experiments"
        / "runs"
        / "T-20260901-006"
        / "qcla_oop_n5_symbolic_direct_ccz_ppm.json"
    ).read_text(encoding="utf-8")

    assert dumps_symbolic_direct_ccz_ppm_trace(trace) == expected
