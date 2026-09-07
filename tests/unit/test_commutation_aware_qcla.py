from __future__ import annotations

import copy

import pytest

from ecdlp_ftqc.circuits import build_oop_qcla_trace, dumps_oop_qcla_trace
from ecdlp_ftqc.compiler import build_width5_joint_ccx_validation_plan
from ecdlp_ftqc.scheduler import (
    COMMUTATION_AWARE_COORDINATE,
    CommutationAwareQclaError,
    SmallWidthCommutationAwareStudy,
    build_small_width_commutation_aware_study,
    build_width_schedule_comparison,
    dumps_small_width_commutation_aware_study,
    small_width_commutation_aware_study_to_data,
)
from ecdlp_ftqc.verification import (
    CommutationAwareQclaReplayError,
    SmallWidthCommutationAwareReplaySummary,
    replay_small_width_commutation_aware_study,
)


@pytest.fixture(scope="module")
def cycle() -> tuple[
    SmallWidthCommutationAwareStudy,
    dict[str, object],
    SmallWidthCommutationAwareReplaySummary,
]:
    study = build_small_width_commutation_aware_study()
    data = small_width_commutation_aware_study_to_data(study)
    replay = replay_small_width_commutation_aware_study(data)
    return study, data, replay


def test_widths_two_through_eight_have_exact_schedule_table(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    study, _, replay = cycle

    assert replay.all_passed
    assert [
        (
            row.width,
            row.source_ccx_count,
            row.source_toffoli_bearing_layers,
            row.source_aligned_candidate_levels,
            row.unitary.macro_depth,
            row.unitary.direct_ccz_candidate_levels,
            row.measured_cleanup.scheduled_ccx_count,
            row.measured_cleanup.measured_cleanup_count,
            row.measured_cleanup.macro_depth,
            row.measured_cleanup.direct_ccz_candidate_levels,
        )
        for row in replay.width_summaries
    ] == [
        (2, 1, 1, 2, 1, 2, 1, 0, 1, 2),
        (3, 3, 2, 4, 2, 4, 3, 0, 2, 4),
        (4, 5, 3, 6, 3, 6, 5, 0, 3, 6),
        (5, 10, 6, 12, 4, 8, 9, 1, 3, 6),
        (6, 12, 6, 12, 4, 8, 11, 1, 4, 8),
        (7, 17, 7, 14, 5, 10, 15, 2, 4, 8),
        (8, 19, 7, 14, 5, 10, 17, 2, 5, 10),
    ]
    assert all(
        row.unitary.macro_depth == row.unitary.exact_lower_bound_macro_depth
        and row.measured_cleanup.macro_depth
        == row.measured_cleanup.exact_lower_bound_macro_depth
        for row in replay.width_summaries
    )
    assert study.widths == tuple(range(2, 9))


def test_width5_exact_groups_match_the_approved_semantic_gate(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    study, _, replay = cycle
    width5 = study.comparisons[3]
    approved = build_width5_joint_ccx_validation_plan(build_oop_qcla_trace(5))

    assert tuple(layer.source_gate_ids for layer in width5.unitary.macro_layers) == tuple(
        tuple(operation.source_gate_id for operation in layer.operations)
        for layer in approved.unitary_macro_layers
    )
    assert tuple(
        layer.source_gate_ids for layer in width5.measured_cleanup.macro_layers
    ) == tuple(
        tuple(operation.source_gate_id for operation in layer.operations)
        for layer in approved.measured_cleanup_macro_layers
    )
    assert (
        replay.width5_source_aligned_candidate_levels,
        replay.width5_unitary_macro_depth,
        replay.width5_unitary_candidate_levels,
        replay.width5_measured_macro_depth,
        replay.width5_measured_candidate_levels,
    ) == (12, 4, 8, 3, 6)


def test_macro_layers_contain_only_jointly_admitted_pairs(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    study, _, _ = cycle

    for comparison in study.comparisons:
        for schedule in (comparison.unitary, comparison.measured_cleanup):
            admitted = {
                (pair.left_source_gate_id, pair.right_source_gate_id)
                for pair in schedule.pair_decisions
                if pair.same_macro_admitted
            }
            positions = {
                gate_id: index
                for index, layer in enumerate(schedule.macro_layers)
                for gate_id in layer.source_gate_ids
            }
            for layer in schedule.macro_layers:
                for left_index, left in enumerate(layer.source_gate_ids):
                    for right in layer.source_gate_ids[left_index + 1 :]:
                        assert (left, right) in admitted
            for dependency in schedule.dependencies:
                assert positions[dependency.predecessor] < positions[dependency.successor]


def test_source_clifford_barriers_and_reaction_frontiers_are_retained(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    study, _, replay = cycle

    for comparison in study.comparisons:
        for schedule in (comparison.unitary, comparison.measured_cleanup):
            assert len(schedule.reaction_boundaries) == max(0, schedule.macro_depth - 1)
            assert all(
                boundary.duration_seconds is None
                and boundary.outcome_subset_status.value == "CHECK"
                and len(boundary.predecessor_outcome_tokens)
                == 6 * len(boundary.predecessor_source_gate_ids)
                for boundary in schedule.reaction_boundaries
            )
            assert all(
                not layer.event_to_event_reaction_edges
                for layer in schedule.macro_layers
            )
    assert [
        row.unitary.reaction_boundary_count for row in replay.width_summaries
    ] == [0, 1, 2, 3, 3, 4, 4]


def test_measurement_cleanup_lifetimes_and_frame_support_are_explicit(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    study, _, replay = cycle
    expected_cleanup_counts = [0, 0, 0, 1, 1, 2, 2]

    assert [
        row.measured_cleanup.measured_cleanup_count for row in replay.width_summaries
    ] == expected_cleanup_counts
    for comparison in study.comparisons:
        for cleanup in comparison.measured_cleanup.cleanup_records:
            assert cleanup.release_count == 1
            assert cleanup.later_ppm_source_gate_ids == ()
            assert cleanup.frame_propagating_gate_ids
            assert set(cleanup.controls) <= set(cleanup.final_frame_support_upper_bound)
    width5 = study.comparisons[3].measured_cleanup.cleanup_records[0]
    assert width5.source_gate_id_replaced == "qcla-oop:000012"
    assert width5.last_quantum_use_source_gate_id == "qcla-oop:000010"
    assert width5.final_frame_support_upper_bound == (
        "a:2",
        "a:3",
        "b:2",
        "b:3",
        "z:2",
        "z:3",
    )


def test_independent_replay_exhausts_semantics_and_phase_columns(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    _, _, replay = cycle

    assert replay.total_pair_decisions_checked == 776
    assert replay.total_pair_truth_table_rows_checked == 39824
    assert replay.total_arithmetic_inputs_checked == 174752
    assert replay.total_measurement_branch_columns_checked == 337920
    assert replay.total_phase_sensitive_relative_pairs_checked == 337908
    assert all(
        row.unitary.arithmetic_mismatches == 0
        and row.measured_cleanup.arithmetic_mismatches == 0
        for row in replay.width_summaries
    )


def test_cleanup_does_not_claim_a_depth_reduction_when_another_path_dominates(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    _, _, replay = cycle
    rows = {row.width: row for row in replay.width_summaries}

    assert rows[5].measured_cleanup.macro_depth < rows[5].unitary.macro_depth
    assert rows[7].measured_cleanup.macro_depth < rows[7].unitary.macro_depth
    assert rows[6].measured_cleanup.macro_depth == rows[6].unitary.macro_depth
    assert rows[8].measured_cleanup.macro_depth == rows[8].unitary.macro_depth


def test_outputs_remain_unitless_and_finite_fields_are_null(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    study, _, replay = cycle

    for comparison in study.comparisons:
        for schedule in (comparison.unitary, comparison.measured_cleanup):
            assert schedule.candidate_level_coordinate == COMMUTATION_AWARE_COORDINATE
            assert not schedule.complete_native_schedule
            assert schedule.native_cycles is None
            assert schedule.runtime_seconds is None
            assert schedule.physical_qubits is None
            assert schedule.failure_probability is None
    assert replay.complete_native_schedule is False
    assert replay.native_cycles is None
    assert replay.runtime_seconds is None
    assert replay.physical_qubits is None
    assert replay.failure_probability is None


def test_generation_is_deterministic_and_source_baselines_are_unchanged(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
) -> None:
    study, _, _ = cycle
    regenerated = build_small_width_commutation_aware_study()

    assert dumps_small_width_commutation_aware_study(study) == (
        dumps_small_width_commutation_aware_study(regenerated)
    )
    for comparison in study.comparisons:
        source = build_oop_qcla_trace(comparison.width)
        assert comparison.source_trace_id == source.trace_id
        assert len(dumps_oop_qcla_trace(source)) > 0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("pair", "pair decision"),
        ("dependency", "dependency"),
        ("macro", "macro grouping"),
        ("resource", "resource"),
        ("reaction", "reaction boundary"),
        ("cleanup", "cleanup record"),
        ("finite", "finite-backend"),
        ("baseline", "source baseline"),
    ],
)
def test_independent_replay_rejects_mutations(
    cycle: tuple[
        SmallWidthCommutationAwareStudy,
        dict[str, object],
        SmallWidthCommutationAwareReplaySummary,
    ],
    mutation: str,
    message: str,
) -> None:
    _, data, _ = cycle
    tampered = copy.deepcopy(data)
    width5 = tampered["comparisons"][3]  # type: ignore[index]
    unitary = width5["unitary"]  # type: ignore[index]
    if mutation == "pair":
        unitary["pair_decisions"][0]["commutes"] = not unitary["pair_decisions"][0][  # type: ignore[index]
            "commutes"
        ]
    elif mutation == "dependency":
        unitary["dependencies"].pop()  # type: ignore[union-attr]
    elif mutation == "macro":
        unitary["macro_layers"][1]["source_gate_ids"].reverse()  # type: ignore[index,union-attr]
    elif mutation == "resource":
        unitary["macro_layers"][1]["resource_triples"][0][0] += ":tampered"  # type: ignore[index,operator]
    elif mutation == "reaction":
        unitary["reaction_boundaries"][0]["predecessor_outcome_tokens"].pop()  # type: ignore[index,union-attr]
    elif mutation == "cleanup":
        width5["measured_cleanup"]["cleanup_records"][0][  # type: ignore[index]
            "last_quantum_use_source_gate_id"
        ] = "qcla-oop:000009"
    elif mutation == "finite":
        unitary["runtime_seconds"] = 1.0  # type: ignore[index]
    else:
        width5["source_trace_sha256"] = "0" * 64  # type: ignore[index]

    with pytest.raises(CommutationAwareQclaReplayError, match=message):
        replay_small_width_commutation_aware_study(tampered)


def test_invalid_width_is_rejected() -> None:
    with pytest.raises(CommutationAwareQclaError, match="width 2--8"):
        build_width_schedule_comparison(9)
