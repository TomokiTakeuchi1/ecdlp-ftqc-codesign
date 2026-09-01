from __future__ import annotations

import copy
from dataclasses import replace
from itertools import product
from pathlib import Path

import numpy as np
import pytest

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import OopQclaTrace, build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    BooleanPolynomial,
    DirectCczPpmTraceError,
    FrameGate,
    FrameGateKind,
    SymbolicDirectCczPpmTrace,
    SymbolicFrameTerm,
    SymbolicPauliWord,
    dumps_symbolic_direct_ccz_ppm_trace,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    parse_boolean_expression,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.verification import (
    DirectCczPpmReplayError,
    replay_symbolic_direct_ccz_ppm_trace,
)

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = (
    ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
)


def _compiled() -> tuple[OopQclaTrace, SymbolicDirectCczPpmTrace]:
    source = build_oop_qcla_trace(5)
    trace = lower_oop_qcla_to_symbolic_direct_ccz_ppm(
        source,
        load_direct_ccz_capability(CAPABILITY),
    )
    return source, trace


def _pauli_matrix(sign: int, support: tuple[tuple[str, str], ...]) -> np.ndarray:
    single = {
        "I": np.eye(2, dtype=np.complex128),
        "X": np.array([[0, 1], [1, 0]], dtype=np.complex128),
        "Y": np.array([[0, -1j], [1j, 0]], dtype=np.complex128),
        "Z": np.array([[1, 0], [0, -1]], dtype=np.complex128),
    }
    terms = dict(support)
    return ((-1) ** sign) * np.kron(single[terms.get("q0", "I")], single[terms.get("q1", "I")])


def test_boolean_anf_is_canonical_and_evaluates_exact_map_expression() -> None:
    expression = parse_boolean_expression("x XOR (a AND b)")

    assert expression.monomials == (("x",), ("a", "b"))
    assert expression.to_expression() == "x XOR (a AND b)"
    assert expression.evaluate({"a": 1, "b": 1, "x": 0}) == 1
    assert expression.evaluate({"a": 1, "b": 1, "x": 1}) == 0
    assert expression.xor(expression) == BooleanPolynomial.zero()


def test_noncanonical_boolean_polynomial_is_rejected() -> None:
    with pytest.raises(DirectCczPpmTraceError, match="canonical order"):
        BooleanPolynomial((("z",), ("a",)))
    with pytest.raises(DirectCczPpmTraceError, match="sorted unique"):
        BooleanPolynomial((("b", "a"),))


@pytest.mark.parametrize(
    ("gate", "unitary"),
    [
        (
            FrameGate(FrameGateKind.CNOT, ("q0", "q1")),
            np.array(
                [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
                dtype=np.complex128,
            ),
        ),
        (
            FrameGate(FrameGateKind.CZ, ("q0", "q1")),
            np.diag([1, 1, 1, -1]).astype(np.complex128),
        ),
    ],
)
def test_two_qubit_clifford_conjugation_tracks_hermitian_signs(
    gate: FrameGate,
    unitary: np.ndarray,
) -> None:
    for terms in product(("I", "X", "Y", "Z"), repeat=2):
        if terms == ("I", "I"):
            continue
        logical_support = tuple(
            logical for logical, term in zip(("q0", "q1"), terms, strict=True) if term != "I"
        )
        pauli_terms = tuple(term for term in terms if term != "I")
        original = SymbolicPauliWord.from_terms(logical_support, pauli_terms)
        transformed = original.apply_gate(gate)
        actual_sign, actual_support = transformed.evaluate({})
        expected = unitary @ _pauli_matrix(0, tuple(zip(logical_support, pauli_terms, strict=True))) @ unitary.conj().T

        assert np.allclose(_pauli_matrix(actual_sign, actual_support), expected)


def test_presented_observable_uses_inverse_correction_order() -> None:
    cnot = FrameGate(FrameGateKind.CNOT, ("q0", "q1"))
    z_target = FrameGate(FrameGateKind.Z, ("q1",))
    frame = (
        SymbolicFrameTerm("t0", "event", BooleanPolynomial.one(), (cnot,), "test"),
        SymbolicFrameTerm(
            "t1", "event", BooleanPolynomial.one(), (z_target,), "test"
        ),
    )
    bare = SymbolicPauliWord.from_terms(("q0",), ("X",))
    presented = bare.presented_under_correction_frame(frame)
    actual_sign, actual_support = presented.evaluate({})
    cnot_matrix = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
        dtype=np.complex128,
    )
    z_target_matrix = _pauli_matrix(0, (("q1", "Z"),))
    correction = z_target_matrix @ cnot_matrix
    expected = correction.conj().T @ _pauli_matrix(0, (("q0", "X"),)) @ correction

    assert np.allclose(_pauli_matrix(actual_sign, actual_support), expected)


def test_width_five_symbolic_trace_conserves_source_operations() -> None:
    source, trace = _compiled()
    assert len(source.gates) == 23
    assert len(trace.source_operations) == 23
    assert len(trace.injections) == 10
    assert len(trace.ppms) == 60
    assert len(trace.correction_updates) == 60
    assert len(trace.macro_layer_frames) == 9
    assert len(trace.logical_lifetimes) == 16
    assert len(trace.resource_lifetimes) == 10
    assert trace.compiler_ancilla_lifetimes == ()
    assert trace.complete_native_schedule is False


def test_width_five_source_macro_layers_have_disjoint_logical_supports() -> None:
    source, _ = _compiled()
    for layer in range(1, 10):
        gates = tuple(gate for gate in source.gates if gate.algorithmic_layer == layer)
        supports = [logical for gate in gates for logical in gate.logical_support]

        assert len(supports) == len(set(supports))


def test_event_boundary_corrections_include_post_h_cnot_conversion() -> None:
    _, trace = _compiled()
    first = trace.injections[0]
    updates = {
        update.update_id: update for update in trace.correction_updates
    }
    gates = [updates[update_id].frame_term.circuit[0] for update_id in first.correction_update_ids]

    assert [gate.kind for gate in gates] == [
        FrameGateKind.CNOT,
        FrameGateKind.CNOT,
        FrameGateKind.CZ,
        FrameGateKind.Z,
        FrameGateKind.Z,
        FrameGateKind.X,
    ]
    assert gates[0].support == (first.data[1], first.data[2])
    assert gates[1].support == (first.data[0], first.data[2])


def test_event_corrections_append_in_correction_circuit_order() -> None:
    _, trace = _compiled()
    first_layer_terms = trace.macro_layer_frames[0].frame_out.terms
    expected_origins = tuple(
        injection.event_id
        for injection in trace.injections[:4]
        for _ in range(6)
    )

    assert tuple(term.origin_event_id for term in first_layer_terms) == expected_origins


def test_later_ppms_record_frame_conjugated_observables() -> None:
    _, trace = _compiled()
    changed = []
    for ppm in trace.ppms:
        bare = SymbolicPauliWord.from_terms(ppm.logical_support, ppm.pauli_terms)
        if ppm.presented_observable != bare:
            changed.append(ppm)

    assert changed
    assert any(
        ppm.presented_observable.sign.variables
        or any(poly.variables for _, poly in ppm.presented_observable.x_components)
        or any(poly.variables for _, poly in ppm.presented_observable.z_components)
        for ppm in changed
    )


def test_independent_replay_checks_frames_truth_tables_and_semantics() -> None:
    source, trace = _compiled()
    data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    summary = replay_symbolic_direct_ccz_ppm_trace(source, data)

    assert summary.all_passed
    assert summary.source_operation_count == 23
    assert summary.injection_count == 10
    assert summary.ppm_count == 60
    assert summary.passthrough_cnot_count == 13
    assert summary.correction_truth_table_rows_checked == 640
    assert summary.frame_transition_count_checked == 23
    assert summary.frame_probe_assignment_count == 64
    assert summary.presented_observable_checks == 3840
    assert summary.source_basis_input_pairs_checked == 1024
    assert summary.local_injection_branch_count == 64
    assert summary.local_injection_maximum_operator_error == 0.0


def test_symbolic_trace_serialization_is_deterministic() -> None:
    _, first = _compiled()
    _, second = _compiled()

    assert dumps_symbolic_direct_ccz_ppm_trace(first) == dumps_symbolic_direct_ccz_ppm_trace(second)


def test_trace_rejects_forged_native_schedule() -> None:
    _, trace = _compiled()

    with pytest.raises(DirectCczPpmTraceError, match="native schedule"):
        replace(trace, complete_native_schedule=True)


def test_trace_rejects_missing_ppm() -> None:
    _, trace = _compiled()

    with pytest.raises(DirectCczPpmTraceError, match="six PPMs"):
        replace(trace, ppms=trace.ppms[:-1])


def test_replay_rejects_tampered_source_provenance() -> None:
    source, trace = _compiled()
    data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    tampered = copy.deepcopy(data)
    tampered["source_operations"][0]["logical_support"][0] = "forged"

    with pytest.raises(DirectCczPpmReplayError, match="provenance"):
        replay_symbolic_direct_ccz_ppm_trace(source, tampered)


def test_replay_rejects_tampered_correction_condition() -> None:
    source, trace = _compiled()
    data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    tampered = copy.deepcopy(data)
    condition = tampered["correction_updates"][0]["frame_term"]["condition"]
    condition["anf_monomials"] = []
    condition["variables"] = []
    condition["expression"] = "0"

    with pytest.raises(DirectCczPpmReplayError, match="truth table"):
        replay_symbolic_direct_ccz_ppm_trace(source, tampered)


def test_replay_rejects_tampered_operation_dependency() -> None:
    source, trace = _compiled()
    tampered = copy.deepcopy(symbolic_direct_ccz_ppm_trace_to_data(trace))
    tampered["clifford_instructions"][1]["predecessor_operation_ids"] = []

    with pytest.raises(DirectCczPpmReplayError, match="basis-after dependency"):
        replay_symbolic_direct_ccz_ppm_trace(source, tampered)


def test_replay_rejects_tampered_presented_observable() -> None:
    source, trace = _compiled()
    data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    tampered = copy.deepcopy(data)
    changed = next(
        ppm
        for ppm in tampered["ppms"]
        if ppm["presented_observable"]["sign"]["anf_monomials"]
    )
    changed["presented_observable"]["sign"] = {
        "anf_monomials": [],
        "expression": "0",
        "variables": [],
    }

    with pytest.raises(DirectCczPpmReplayError, match="presented Pauli"):
        replay_symbolic_direct_ccz_ppm_trace(source, tampered)


def test_replay_rejects_forged_complete_schedule() -> None:
    source, trace = _compiled()
    data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    data["complete_native_schedule"] = True

    with pytest.raises(DirectCczPpmReplayError, match="native schedule"):
        replay_symbolic_direct_ccz_ppm_trace(source, data)
