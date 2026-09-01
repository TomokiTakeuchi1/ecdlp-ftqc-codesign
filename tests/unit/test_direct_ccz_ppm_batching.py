from __future__ import annotations

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
from ecdlp_ftqc.circuits import build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    BooleanPolynomial,
    SymbolicPauliWord,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.scheduler import (
    DirectCczPpmBatchingError,
    analyze_direct_ccz_ppm_batches,
    dumps_phase_b_artifact,
    finite_instance_admission_to_data,
    general_high_rate_candidate_to_data,
    low_rate_fallback_to_data,
    strategy_frontier_to_data,
    symbolic_axis_conflicts,
    symbolic_symplectic_polynomial,
    symbolic_y_content,
)
from ecdlp_ftqc.verification import (
    DirectCczPpmBatchingReplayError,
    replay_direct_ccz_ppm_batching,
)

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = (
    ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
)
AUDIT_PATH = (
    ROOT / "configs" / "architectures" / "direct_ccz_finite_backend_audit_v1.yaml"
)


@pytest.fixture(scope="module")
def phase_b() -> dict[str, object]:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    trace = lower_oop_qcla_to_symbolic_direct_ccz_ppm(
        build_oop_qcla_trace(5),
        capability,
    )
    analysis = analyze_direct_ccz_ppm_batches(trace, capability, audit)
    trace_data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    general_data = general_high_rate_candidate_to_data(analysis.general)
    finite_data = finite_instance_admission_to_data(analysis.finite)
    fallback_data = low_rate_fallback_to_data(analysis.fallback)
    frontier_data = strategy_frontier_to_data(analysis.frontier)
    replay = replay_direct_ccz_ppm_batching(
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
        "audit": audit,
        "capability": capability,
        "fallback_data": fallback_data,
        "finite_data": finite_data,
        "frontier_data": frontier_data,
        "general_data": general_data,
        "replay": replay,
        "trace": trace,
        "trace_data": trace_data,
    }


def test_exact_symplectic_screen_separates_global_commutation_from_axis_conflict() -> None:
    xx = SymbolicPauliWord.from_terms(("q0", "q1"), ("X", "X"))
    zz = SymbolicPauliWord.from_terms(("q0", "q1"), ("Z", "Z"))

    assert symbolic_symplectic_polynomial(xx, zz).is_zero
    assert symbolic_axis_conflicts(xx, zz) == (
        ("q0", BooleanPolynomial.one()),
        ("q1", BooleanPolynomial.one()),
    )


def test_same_axis_overlap_is_not_a_conflict_and_symbolic_y_is_exact() -> None:
    x = SymbolicPauliWord.from_terms(("q0",), ("X",))
    branch_y = SymbolicPauliWord(
        x_components=(("q0", BooleanPolynomial.one()),),
        z_components=(("q0", BooleanPolynomial.variable("m")),),
        sign=BooleanPolynomial.zero(),
    )

    assert symbolic_symplectic_polynomial(x, x).is_zero
    assert symbolic_axis_conflicts(x, x) == ()
    assert symbolic_y_content(branch_y) == (
        ("q0", BooleanPolynomial.variable("m")),
    )


def test_width_five_profiles_and_pair_relations_are_exact(phase_b: dict[str, object]) -> None:
    analysis = phase_b["analysis"]
    general = analysis.general  # type: ignore[union-attr]

    assert len(general.observable_profiles) == 60
    assert len(general.pair_relations) == 1770
    assert Counter(
        (profile.minimum_weight, profile.maximum_weight)
        for profile in general.observable_profiles
    ) == Counter({(1, 1): 30, (2, 2): 20, (2, 4): 7, (2, 7): 3})
    assert Counter(len(profile.variables) for profile in general.observable_profiles) == (
        Counter({0: 50, 3: 7, 9: 3})
    )
    assert not any(profile.has_possible_y for profile in general.observable_profiles)
    assert sum(not relation.universally_commuting for relation in general.pair_relations) == 30
    assert sum(
        not relation.universally_axis_consistent for relation in general.pair_relations
    ) == 30


def test_logical_overlap_alone_does_not_serialize(phase_b: dict[str, object]) -> None:
    analysis = phase_b["analysis"]
    relations = analysis.general.pair_relations  # type: ignore[union-attr]
    compatible_overlaps = tuple(
        relation
        for relation in relations
        if relation.general_high_rate_compatible and relation.shared_logical_values
    )

    assert len(compatible_overlaps) == 6
    assert all(not relation.shared_resource_values for relation in compatible_overlaps)


def test_exact_lower_bound_matches_constructive_twelve_level_schedule(
    phase_b: dict[str, object],
) -> None:
    analysis = phase_b["analysis"]
    schedule = analysis.general.optimized_schedule  # type: ignore[union-attr]

    assert schedule.candidate_batch_level_count == 12
    assert [len(batch.operation_ids) for batch in schedule.batches] == [
        12,
        12,
        6,
        6,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
    ]
    assert schedule.causal_critical_path_lower_bound == 12
    assert schedule.conflict_clique_lower_bound == 12
    assert schedule.combined_batch_level_lower_bound == 12
    assert schedule.optimality_evidence_status.value == "PROVED"
    assert schedule.fallback_operation_count == 0
    assert schedule.complete_native_schedule is False
    assert schedule.peak_live_logical_requirement == 26
    assert schedule.peak_resource_state_count == 4


def test_source_aligned_and_dynamic_batching_agree_for_this_instance(
    phase_b: dict[str, object],
) -> None:
    analysis = phase_b["analysis"]
    source = analysis.general.source_layer_aligned_schedule  # type: ignore[union-attr]
    optimized = analysis.general.optimized_schedule  # type: ignore[union-attr]

    assert source.candidate_batch_level_count == optimized.candidate_batch_level_count == 12
    assert all(len(batch.source_algorithmic_layers) == 1 for batch in source.batches)
    assert source.peak_live_logical_requirement == optimized.peak_live_logical_requirement


def test_finite_instance_is_rejected_with_null_outputs(phase_b: dict[str, object]) -> None:
    finite = phase_b["finite_data"]
    assert finite["verdict"] == "REJECTED_MISSING_OR_INCOMPATIBLE_FINITE_BACKEND_EVIDENCE"  # type: ignore[index]
    assert finite["schedule"] is None  # type: ignore[index]
    assert finite["runtime_seconds"] is None  # type: ignore[index]
    assert finite["physical_qubits"] is None  # type: ignore[index]
    assert finite["failure_probability"] is None  # type: ignore[index]
    assert len(finite["capability_missing_fields"]) == 13  # type: ignore[arg-type,index]
    assert len(finite["backend_missing_fields"]) == 13  # type: ignore[arg-type,index]
    assert finite["backend_incompatible_fields"] == [  # type: ignore[index]
        "factory.batch_size",
        "factory.production_cycles",
        "factory.output_error_probability",
    ]
    assert finite["native_mapper_missing_fields"] == [  # type: ignore[index]
        "consumer.native_operation_family",
        "consumer.logical_basis_mapping",
        "consumer.physical_support_overlap_rule",
        "consumer.ancilla_and_check_construction",
    ]


def test_low_rate_fallback_is_semantic_singleton_order_only(
    phase_b: dict[str, object],
) -> None:
    fallback = phase_b["fallback_data"]
    assert fallback["operation_count"] == 60  # type: ignore[index]
    assert fallback["unit"] == "semantic_singleton_order_not_time"  # type: ignore[index]
    assert fallback["finite_cost_status"] == "OPEN"  # type: ignore[index]
    assert fallback["complete_native_schedule"] is False  # type: ignore[index]
    assert all(
        "start_round" not in operation and "duration_rounds" not in operation
        for operation in fallback["operations"]  # type: ignore[union-attr,index]
    )


def test_unverified_rewrites_and_materialization_are_not_admitted(
    phase_b: dict[str, object],
) -> None:
    frontier = phase_b["frontier_data"]
    strategies = {
        item["strategy_id"]: item
        for item in frontier["strategies"]  # type: ignore[union-attr,index]
    }

    for strategy_id in (
        "measured_operator_product_rewrites",
        "selective_clifford_materialization",
    ):
        assert strategies[strategy_id]["disposition"] == "SCREENED_NOT_ADMITTED"
        assert strategies[strategy_id]["admitted_transform_count"] == 0
        assert strategies[strategy_id]["candidate_batch_levels"] is None
    assert frontier["ppm_count_is_objective"] is False  # type: ignore[index]


def test_independent_replay_reconstructs_every_relation_and_output_class(
    phase_b: dict[str, object],
) -> None:
    replay = phase_b["replay"]

    assert replay.all_passed  # type: ignore[union-attr]
    assert replay.symbolic_commutation_checks == 1770  # type: ignore[union-attr]
    assert replay.symbolic_axis_checks == 1770  # type: ignore[union-attr]
    assert replay.causal_pair_count == 1206  # type: ignore[union-attr]
    assert replay.reaction_pair_count == 1116  # type: ignore[union-attr]
    assert replay.compatible_overlap_pair_count == 6  # type: ignore[union-attr]
    assert replay.optimized_candidate_batch_levels == 12  # type: ignore[union-attr]
    assert replay.finite_schedule_rejected  # type: ignore[union-attr]


def test_independent_replay_rejects_tampered_commutator(
    phase_b: dict[str, object],
) -> None:
    general = copy.deepcopy(phase_b["general_data"])
    relation = general["pair_relations"][0]
    relation["symplectic_commutator"] = {
        "anf_monomials": [[]],
        "expression": "1",
        "variables": [],
    }

    with pytest.raises(DirectCczPpmBatchingReplayError, match="exact ANF replay"):
        replay_direct_ccz_ppm_batching(
            phase_b["trace_data"],  # type: ignore[arg-type]
            general,
            phase_b["finite_data"],  # type: ignore[arg-type]
            phase_b["fallback_data"],  # type: ignore[arg-type]
            phase_b["frontier_data"],  # type: ignore[arg-type]
            direct_ccz_capability_to_data(phase_b["capability"]),  # type: ignore[arg-type]
            direct_ccz_backend_audit_to_data(phase_b["audit"]),  # type: ignore[arg-type]
        )


def test_independent_replay_rejects_forged_finite_schedule(
    phase_b: dict[str, object],
) -> None:
    finite = copy.deepcopy(phase_b["finite_data"])
    finite["schedule"] = {"forged": True}

    with pytest.raises(DirectCczPpmBatchingReplayError, match="schedule and runtime null"):
        replay_direct_ccz_ppm_batching(
            phase_b["trace_data"],  # type: ignore[arg-type]
            phase_b["general_data"],  # type: ignore[arg-type]
            finite,
            phase_b["fallback_data"],  # type: ignore[arg-type]
            phase_b["frontier_data"],  # type: ignore[arg-type]
            direct_ccz_capability_to_data(phase_b["capability"]),  # type: ignore[arg-type]
            direct_ccz_backend_audit_to_data(phase_b["audit"]),  # type: ignore[arg-type]
        )


def test_trace_and_capability_identity_mismatch_fails_closed(
    phase_b: dict[str, object],
) -> None:
    trace = phase_b["trace"]
    with pytest.raises(DirectCczPpmBatchingError, match="identities disagree"):
        analyze_direct_ccz_ppm_batches(
            replace(trace, capability_id="forged"),  # type: ignore[arg-type]
            phase_b["capability"],  # type: ignore[arg-type]
            phase_b["audit"],  # type: ignore[arg-type]
        )


def test_phase_b_serialization_is_deterministic(phase_b: dict[str, object]) -> None:
    for name in ("general_data", "finite_data", "fallback_data", "frontier_data"):
        value = phase_b[name]
        assert dumps_phase_b_artifact(value) == dumps_phase_b_artifact(  # type: ignore[arg-type]
            copy.deepcopy(value)  # type: ignore[arg-type]
        )
