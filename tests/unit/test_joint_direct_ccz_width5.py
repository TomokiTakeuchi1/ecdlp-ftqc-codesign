from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    CcxOverlapKind,
    JointDirectCczPlanError,
    build_width5_joint_ccx_validation_plan,
    dumps_symbolic_direct_ccz_ppm_trace,
    dumps_width5_joint_ccx_validation_plan,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    width5_joint_ccx_validation_plan_to_data,
)
from ecdlp_ftqc.verification import (
    JointDirectCczReplayError,
    replay_width5_joint_direct_ccz,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def width5_cycle() -> dict[str, object]:
    source = build_oop_qcla_trace(5)
    plan = build_width5_joint_ccx_validation_plan(source)
    data = width5_joint_ccx_validation_plan_to_data(plan)
    replay = replay_width5_joint_direct_ccz(source, data)
    return {"source": source, "plan": plan, "data": data, "replay": replay}


def test_all_source_pairs_and_overlap_orientations_are_exact(
    width5_cycle: dict[str, object],
) -> None:
    plan = width5_cycle["plan"]
    replay = width5_cycle["replay"]

    assert len(plan.all_pair_certificates) == 45  # type: ignore[union-attr]
    assert replay.commuting_source_pair_count == 36  # type: ignore[union-attr]
    assert replay.noncommuting_source_pair_count == 9  # type: ignore[union-attr]
    assert replay.source_pair_truth_table_rows_checked == 2040  # type: ignore[union-attr]
    synthetic = plan.synthetic_overlap_certificates  # type: ignore[union-attr]
    assert [item.overlap_kind for item in synthetic] == [
        CcxOverlapKind.DISJOINT,
        CcxOverlapKind.SHARED_CONTROL,
        CcxOverlapKind.SHARED_TARGET,
        CcxOverlapKind.LEFT_TARGET_RIGHT_CONTROL,
        CcxOverlapKind.RIGHT_TARGET_LEFT_CONTROL,
        CcxOverlapKind.BIDIRECTIONAL_TARGET_CONTROL,
    ]
    assert [item.commutes for item in synthetic] == [True, True, True, False, False, False]
    assert all(
        item.witness_input is not None for item in synthetic if not item.commutes
    )


def test_width5_macro_layers_use_one_frame_and_fresh_resources(
    width5_cycle: dict[str, object],
) -> None:
    plan = width5_cycle["plan"]
    replay = width5_cycle["replay"]
    layers = plan.unitary_macro_layers  # type: ignore[union-attr]

    assert [len(layer.operations) for layer in layers] == [4, 3, 2, 1]
    assert [len(layer.pair_certificates) for layer in layers] == [6, 3, 1, 0]
    assert all(layer.common_incoming_frame == "macro_layer_entry_frame" for layer in layers)
    assert all(not layer.event_to_event_reaction_edges for layer in layers)
    assert replay.admitted_macro_pair_count == 10  # type: ignore[union-attr]
    assert replay.common_frame_factorization_proofs == 4  # type: ignore[union-attr]
    assert replay.factorized_two_event_branches_covered == 45056  # type: ignore[union-attr]
    assert replay.resource_triples_checked == 10  # type: ignore[union-attr]
    assert replay.resource_values_checked == 30  # type: ignore[union-attr]


def test_joint_injection_channel_anchors_pass(
    width5_cycle: dict[str, object],
) -> None:
    replay = width5_cycle["replay"]

    assert replay.single_event_branches_checked == 64  # type: ignore[union-attr]
    assert replay.single_event_maximum_probability_error < 1e-14  # type: ignore[union-attr]
    assert replay.single_event_maximum_operator_frobenius_error < 1e-14  # type: ignore[union-attr]
    shared_control = replay.shared_control_anchor  # type: ignore[union-attr]
    shared_target = replay.shared_target_anchor  # type: ignore[union-attr]
    assert (shared_control.pair_count, shared_control.branch_anchors_per_pair) == (2, 16)
    assert (shared_target.pair_count, shared_target.branch_anchors_per_pair) == (1, 16)
    assert shared_control.maximum_probability_error < 1e-14
    assert shared_control.maximum_operator_frobenius_error < 1e-14
    assert shared_target.maximum_probability_error < 1e-14
    assert shared_target.maximum_operator_frobenius_error < 1e-14


def test_measurement_uncompute_matches_complete_width5_channel(
    width5_cycle: dict[str, object],
) -> None:
    replay = width5_cycle["replay"]
    cleanup = replay.measurement_uncompute  # type: ignore[union-attr]

    assert cleanup.local_control_assignments_checked == 4
    assert cleanup.local_measurement_branches_checked == 8
    assert cleanup.width5_input_basis_columns_checked == 1024
    assert cleanup.width5_measurement_branches_checked == 2048
    assert cleanup.phase_sensitive_relative_pairs_checked == 2046
    assert cleanup.maximum_probability_error < 1e-14
    assert cleanup.maximum_corrected_amplitude_error < 1e-14
    assert cleanup.output_basis_mismatches == 0
    assert cleanup.dirty_ancilla_mismatches == 0
    assert cleanup.lifecycle_checks_passed
    assert cleanup.frame_propagating_gate_count == 4
    assert cleanup.later_ppm_dependency_count == 0
    assert cleanup.final_frame_support_upper_bound == (
        "a:2",
        "a:3",
        "b:2",
        "b:3",
        "z:2",
        "z:3",
    )
    assert cleanup.outcome_dependency_persists_to_output
    assert cleanup.all_passed
    assert replay.all_passed  # type: ignore[union-attr]


def test_candidates_remain_logical_and_finite_outputs_are_null(
    width5_cycle: dict[str, object],
) -> None:
    plan = width5_cycle["plan"]
    data = width5_cycle["data"]

    assert (plan.baseline_ccx_count, plan.baseline_candidate_levels) == (10, 12)  # type: ignore[union-attr]
    assert (
        plan.unitary_candidate_ccx_count,  # type: ignore[union-attr]
        plan.unitary_candidate_macro_depth,  # type: ignore[union-attr]
        plan.unitary_candidate_levels,  # type: ignore[union-attr]
    ) == (10, 4, 8)
    assert (
        plan.measured_candidate_ccx_count,  # type: ignore[union-attr]
        plan.measured_candidate_macro_depth,  # type: ignore[union-attr]
        plan.measured_candidate_levels,  # type: ignore[union-attr]
    ) == (9, 3, 6)
    assert data["complete_native_schedule"] is False  # type: ignore[index]
    assert all(value is None for value in data["finite_outputs"].values())  # type: ignore[index,union-attr]
    assert data["unitary_candidate"]["candidate_level_status"] == (  # type: ignore[index]
        "CHECK_PENDING_T-20260906-003"
    )
    assert data["measured_cleanup_candidate"]["candidate_level_coordinate"] == (  # type: ignore[index]
        "two_phase_macro_envelope_not_schedule_or_time"
    )


def test_plan_is_deterministic_and_baseline_trace_is_unchanged(
    width5_cycle: dict[str, object],
) -> None:
    source = build_oop_qcla_trace(5)
    first = build_width5_joint_ccx_validation_plan(source)
    second = build_width5_joint_ccx_validation_plan(source)
    expected_baseline = (
        ROOT
        / "experiments"
        / "runs"
        / "T-20260901-006"
        / "qcla_oop_n5_symbolic_direct_ccz_ppm.json"
    )

    assert dumps_width5_joint_ccx_validation_plan(first) == (
        dumps_width5_joint_ccx_validation_plan(second)
    )
    capability = load_direct_ccz_capability(
        ROOT
        / "configs"
        / "architectures"
        / "direct_ccz_single_event_capability_v1.yaml"
    )
    regenerated_baseline = lower_oop_qcla_to_symbolic_direct_ccz_ppm(
        source, capability
    )
    assert dumps_symbolic_direct_ccz_ppm_trace(regenerated_baseline) == (
        expected_baseline.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("resource_reuse", "resource"),
        ("correction", "correction"),
        ("pair_certificate", "pair certificate"),
        ("outcome", "phase-one"),
        ("event_order", "macro grouping"),
        ("reaction_edge", "reaction edge"),
        ("cleanup", "last use"),
    ],
)
def test_replay_rejects_semantic_mutations(
    width5_cycle: dict[str, object],
    mutation: str,
    message: str,
) -> None:
    source = width5_cycle["source"]
    tampered = copy.deepcopy(width5_cycle["data"])
    if mutation == "resource_reuse":
        resources = tampered["unitary_candidate"]["macro_layers"][1]["resources"]
        resources[1]["resource_values"] = list(resources[0]["resource_values"])
    elif mutation == "correction":
        correction = tampered["unitary_candidate"]["macro_layers"][2][
            "correction_maps"
        ][0]["expressions"]
        correction[0] = correction[0].replace("CZ", "Z", 1)
    elif mutation == "pair_certificate":
        pair = tampered["unitary_candidate"]["macro_layers"][1][
            "pair_certificates"
        ][0]
        pair["commutes"] = not pair["commutes"]
    elif mutation == "outcome":
        tampered["unitary_candidate"]["macro_layers"][0]["phase_one_ppms"][0][
            "outcome_token"
        ] += ":tampered"
    elif mutation == "event_order":
        unitary_layers = tampered["unitary_candidate"]["macro_layers"]
        measured_layers = tampered["measured_cleanup_candidate"]["macro_layers"]
        unitary_layers[0], unitary_layers[1] = unitary_layers[1], unitary_layers[0]
        measured_layers[0], measured_layers[1] = (
            measured_layers[1],
            measured_layers[0],
        )
    elif mutation == "reaction_edge":
        tampered["unitary_candidate"]["macro_layers"][1][
            "event_to_event_reaction_edges"
        ] = [["event:0", "event:1"]]
    else:
        tampered["measured_cleanup_candidate"]["measurement_uncompute"][
            "last_quantum_use_source_gate_id"
        ] = "qcla-oop:000011"

    with pytest.raises(JointDirectCczReplayError, match=message):
        replay_width5_joint_direct_ccz(source, tampered)  # type: ignore[arg-type]


def test_wrong_width_is_rejected() -> None:
    with pytest.raises(JointDirectCczPlanError, match="width five"):
        build_width5_joint_ccx_validation_plan(build_oop_qcla_trace(4))
