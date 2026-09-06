from __future__ import annotations

import copy
from itertools import product

import pytest

from ecdlp_ftqc.analysis import (
    analyze_qcla_clifford_demand,
    build_execution_options,
    build_strategy_matrix,
    execution_option_to_data,
    strategy_effect_to_data,
    variant_clifford_demand_to_data,
)
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.compiler import (
    BooleanPolynomial,
    FrameGate,
    FrameGateKind,
    SymbolicFrameTerm,
    SymbolicPauliWord,
)
from ecdlp_ftqc.verification import (
    QclaCliffordStrategyReplayError,
    replay_qcla_clifford_strategy,
    verify_one_bit_h_teleportation_channel,
)


def _unconditional_term(index: int, gate: FrameGate) -> SymbolicFrameTerm:
    return SymbolicFrameTerm(
        term_id=f"term-{index}",
        origin_event_id="test",
        condition=BooleanPolynomial.one(),
        circuit=(gate,),
        correction_role="test",
    )


def _presented(
    pauli: SymbolicPauliWord,
    gates_in_stored_order: tuple[FrameGate, ...],
) -> tuple[int, tuple[tuple[str, str], ...]]:
    terms = tuple(
        _unconditional_term(index, gate)
        for index, gate in enumerate(gates_in_stored_order)
    )
    return pauli.presented_under_correction_frame(terms).evaluate({})


def test_h_bare_and_tracking_have_explicit_mixed_axis_y_witness() -> None:
    h_t = FrameGate(FrameGateKind.H, ("t",))
    cnot_t_c = FrameGate(FrameGateKind.CNOT, ("t", "c"))
    cz_c_t = FrameGate(FrameGateKind.CZ, ("c", "t"))
    z_t = SymbolicPauliWord.from_terms(("t",), ("Z",))

    tracking = _presented(z_t, (cnot_t_c, cz_c_t, h_t))
    bare = _presented(z_t, (h_t, cnot_t_c, cz_c_t, h_t))

    assert {axis for _, axis in tracking[1]} == {"Y"}
    assert {axis for _, axis in bare[1]} == {"Y"}


def test_all_cnot_modes_preserve_z_type_under_frame_generator_closure() -> None:
    generators = (
        FrameGate(FrameGateKind.X, ("a",)),
        FrameGate(FrameGateKind.Z, ("b",)),
        FrameGate(FrameGateKind.CNOT, ("a", "b")),
        FrameGate(FrameGateKind.CNOT, ("b", "c")),
        FrameGate(FrameGateKind.CZ, ("a", "c")),
    )
    logical_cnot = FrameGate(FrameGateKind.CNOT, ("a", "c"))
    frames = ((), *tuple(product(generators, repeat=2)))
    for support_size in (1, 2, 3):
        support = ("a", "b", "c")[:support_size]
        z_word = SymbolicPauliWord.from_terms(support, ("Z",) * support_size)
        for frame in frames:
            frame_conjugated = _presented(z_word, frame)
            bare = _presented(z_word, (logical_cnot, *frame, logical_cnot))
            tracked = _presented(z_word, (*frame, logical_cnot))
            for _, terms in (frame_conjugated, bare, tracked):
                assert {axis for _, axis in terms} <= {"Z"}


def test_width_256_demands_match_reviewed_source_layers() -> None:
    oop = analyze_qcla_clifford_demand(build_oop_qcla_trace(256), variant="oop")
    ip = analyze_qcla_clifford_demand(build_qcla_trace(256), variant="ip")

    assert (
        oop.source_cnot_gate_count,
        oop.source_toffoli_gate_count,
        oop.cnot_bearing_source_layer_count,
        oop.toffoli_bearing_source_layer_count,
        oop.h_gate_count,
        oop.h_parallel_layer_count,
    ) == (766, 1229, 3, 17, 2458, 34)
    assert (
        ip.source_cnot_gate_count,
        ip.source_toffoli_gate_count,
        ip.cnot_bearing_source_layer_count,
        ip.toffoli_bearing_source_layer_count,
        ip.h_gate_count,
        ip.h_parallel_layer_count,
    ) == (1019, 2458, 4, 34, 4916, 68)
    assert oop.mixed_cnot_toffoli_source_layer_count == 0
    assert ip.mixed_cnot_toffoli_source_layer_count == 0
    assert oop.cnot_teleport_strict_added_ppm_layers == 9
    assert ip.cnot_teleport_strict_added_ppm_layers == 12


def test_execution_options_keep_current_finite_backend_open() -> None:
    options = build_execution_options()

    assert len(options) == 7
    assert not any(option.applies_to_current_high_rate_backend for option in options)
    h_teleport = next(
        option for option in options if option.option_id == "one_bit_h_teleportation"
    )
    assert h_teleport.evidence_status.value == "NUMERICAL"
    assert "Xu" not in h_teleport.source
    assert next(option for option in options if option.option_id == "simd_h_swap").reported_execution_seconds == 0.0019
    assert next(option for option in options if option.option_id == "simd_transversal_cnot").reported_execution_seconds == 0.003


def test_self_derived_h_teleportation_matches_ideal_h_on_all_branches() -> None:
    verification = verify_one_bit_h_teleportation_channel()

    assert verification.all_passed
    assert verification.branch_count == 4
    assert verification.nonzero_branch_count == 4
    assert verification.expected_branch_probability == pytest.approx(0.25)
    assert verification.minimum_branch_probability == pytest.approx(0.25)
    assert verification.maximum_branch_probability == pytest.approx(0.25)
    assert verification.maximum_probability_error <= verification.tolerance
    assert verification.maximum_operator_frobenius_error <= verification.tolerance
    assert verification.branch_corrections == ("I", "X", "Z", "ZX_up_to_phase_Y")


def test_independent_replay_rebuilds_source_demand_and_rejects_mutation() -> None:
    strategy = [strategy_effect_to_data(item) for item in build_strategy_matrix()]
    demands = [
        variant_clifford_demand_to_data(
            analyze_qcla_clifford_demand(build_oop_qcla_trace(256), variant="oop")
        ),
        variant_clifford_demand_to_data(
            analyze_qcla_clifford_demand(build_qcla_trace(256), variant="ip")
        ),
    ]
    execution = [execution_option_to_data(item) for item in build_execution_options()]

    assert replay_qcla_clifford_strategy(strategy, demands, execution).all_passed
    mutated = copy.deepcopy(demands)
    mutated[0]["h_parallel_layer_count"] += 1
    with pytest.raises(QclaCliffordStrategyReplayError, match="h_parallel_layer_count"):
        replay_qcla_clifford_strategy(strategy, mutated, execution)

    miscited_execution = copy.deepcopy(execution)
    next(
        row
        for row in miscited_execution
        if row["option_id"] == "one_bit_h_teleportation"
    )["source"] = "Xu et al. 2024, Figure 11"
    with pytest.raises(QclaCliffordStrategyReplayError, match="cannot cite Xu"):
        replay_qcla_clifford_strategy(strategy, demands, miscited_execution)
