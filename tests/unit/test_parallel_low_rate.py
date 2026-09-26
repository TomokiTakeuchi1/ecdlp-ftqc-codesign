"""Semantic, phase, resource, and mutation anchors for low-rate profiling."""

from dataclasses import asdict, replace
from itertools import product
from random import Random

import numpy as np
import pytest

from ecdlp_ftqc.circuits.qcla import build_qcla_trace
from ecdlp_ftqc.circuits.qcla_oop import build_oop_qcla_trace
from ecdlp_ftqc.compiler.parallel_low_rate_trace import (
    Frame,
    Pauli,
    build_tracked_trace,
    diagonal_correction,
)
from ecdlp_ftqc.scheduler.parallel_low_rate import (
    Limits,
    Timing,
    lower,
    pack,
    rebase_measurement_bit,
    recover_original_outcomes,
    regularize,
    schedule_macro,
    twist_gadget,
)
from ecdlp_ftqc.verification.parallel_low_rate import (
    audit_gadget,
    audit_joint_instrument,
    audit_lowering,
    audit_packing,
    audit_service,
    audit_trace,
    pauli_matrix,
)


def test_all_signed_three_qubit_gadget_instruments() -> None:
    for x, z, sign in product(range(8), range(8), range(2)):
        if not (x | z):
            continue
        p = Pauli(x, z, ((x & z).bit_count() + 2 * sign) % 4)
        gadget = twist_gadget(p, 0, 3, 4)
        assert audit_gadget(asdict(p), asdict(gadget), 3) < 1e-12


def test_gadget_sign_mutation_rejected() -> None:
    p = Pauli(1, 1, 1)
    gadget = twist_gadget(p, 0, 1, 2)
    with pytest.raises(ValueError, match="instrument mismatch"):
        audit_gadget(asdict(p), asdict(replace(gadget, outcome_xor=1 - gadget.outcome_xor)), 1)


@pytest.mark.parametrize(
    "ppms", [(Pauli(1, 2), Pauli(2, 1)), (Pauli(3, 2, 1), Pauli(2, 1)), (Pauli(3), Pauli(z=3))]
)
def test_full_joint_measurement_instrument(ppms: tuple[Pauli, ...]) -> None:
    lowering = lower(ppms, "general")
    assert audit_joint_instrument([asdict(p) for p in ppms], asdict(lowering), 2) < 1e-12


def test_signed_regularization_and_outcome_recovery() -> None:
    # Globally commuting, not regular; includes an odd-Y diagonal pivot case.
    for ppms in (
        (Pauli(1, 2), Pauli(2, 1)),
        (Pauli(3, 2, 1), Pauli(2, 1)),
        (Pauli(3, 3, 2), Pauli(3, 0), Pauli(0, 3)),
    ):
        reg = regularize(ppms)
        lowered = lower(ppms, "general")
        audit_lowering([asdict(p) for p in ppms], asdict(lowered))
        for bits in product((0, 1), repeat=len(ppms)):
            encoded = tuple(
                sum(bits[j] for j in range(len(bits)) if mask >> j & 1) % 2
                for mask in reg.combinations
            )
            assert recover_original_outcomes(reg.combinations, encoded) == bits
        for stage in lowered.stages:
            assert all(p.qwc(q) for i, p in enumerate(stage.ppms) for q in stage.ppms[:i])


def test_capacity_checked_after_lowering_and_overlap_allowed() -> None:
    ppms = (Pauli(1, 2), Pauli(2, 1))
    assert all(p.commutes(q) for p in ppms for q in ppms)
    assert len(pack(ppms, Limits())) == 2
    assert len(pack((Pauli(z=3), Pauli(z=6)), Limits())) == 1
    lowered = lower((Pauli(3, 2, 1), Pauli(2, 1)), "general")
    sched = schedule_macro(lowered, Limits(weight=2), Timing(), 0)
    assert not sched.feasible  # odd-Y gadget needs an additional catalyst term
    audit_packing(asdict(lowered), asdict(sched), asdict(Limits(weight=2)))
    sched = schedule_macro(lowered, Limits(1, 10, 10), Timing(readout=0.2), 3)
    assert sched.feasible
    assert audit_packing(asdict(lowered), asdict(sched), asdict(Limits(1, 10, 10))) > 0
    assert len(pack((Pauli(z=3), Pauli(z=6)), Limits(total_support=3))) == 2


@pytest.mark.parametrize("variant", ["oop", "ip"])
@pytest.mark.parametrize("branch", [-2, -1, 0, 7])
def test_full_signed_history_replay(variant: str, branch: int) -> None:
    trace = build_tracked_trace(variant, 5, branch)
    source = build_oop_qcla_trace(5) if variant == "oop" else build_qcla_trace(5)
    data = asdict(trace)
    assert audit_trace(data, [asdict(g) for g in source.gates]) == sum(
        len(m.ppms) for m in trace.macros
    )
    data["macros"][1]["ppms"][0]["phase"] ^= 2
    with pytest.raises(ValueError, match="trace mismatch"):
        audit_trace(data, [asdict(g) for g in source.gates])


def test_arbitrary_frame_direct_ccz_all_64_branches() -> None:
    n = 3
    identity = np.eye(8, dtype=complex)
    h = (pauli_matrix(4, 0, 0, n) + pauli_matrix(0, 4, 0, n)) / np.sqrt(2)
    cz = np.diag([(-1) ** (((j >> 0) & 1) * ((j >> 1) & 1)) for j in range(8)])
    ccz = np.diag([(-1) ** (j == 7) for j in range(8)])
    hx = (pauli_matrix(1, 0, 0, n) + pauli_matrix(0, 1, 0, n)) / np.sqrt(2)
    incoming = hx @ cz @ h
    opening = incoming @ h
    resource = np.array([(-1) ** (j == 7) for j in range(8)]) / np.sqrt(8)
    embedding = np.kron(resource[:, None], incoming)
    observables = [
        np.kron(
            pauli_matrix(0, 1 << q, 0, 3),
            opening @ pauli_matrix(0, 1 << q, 0, 3) @ opening.conj().T,
        )
        for q in range(3)
    ]
    for bits in product((0, 1), repeat=6):
        state = embedding.copy()
        for bit, observable in zip(bits[:3], observables, strict=True):
            state = (state + (-1) ** bit * observable @ state) / 2
        bra = np.array(
            [(-1) ** sum(bits[q + 3] * (r >> q & 1) for q in range(3)) for r in range(8)]
        ) / np.sqrt(8)
        raw = np.einsum("r,rdj->dj", bra, state.reshape(8, 8, 8))
        correction = identity.copy()
        for kind, a, b in diagonal_correction((0, 1), 2, bits):
            if kind == "z":
                correction = correction @ pauli_matrix(0, 1 << a, 0, 3)
            else:
                correction = correction @ np.diag(
                    [(-1) ** ((j >> a & 1) * (j >> b & 1)) for j in range(8)]
                )
        outgoing = opening @ correction @ h
        expected = outgoing @ h @ ccz @ h
        scalar = np.trace(expected.conj().T @ raw) / 8
        assert abs(abs(scalar) - 1 / 8) < 1e-12
        assert np.linalg.norm(raw - scalar * expected) < 1e-12


def test_frame_updates_against_dense_unitary() -> None:
    n = 3
    frame = Frame(n)
    unitary = np.eye(1 << n, dtype=complex)
    for kind, a, b in (
        ("h", 0, None),
        ("cz", 0, 1),
        ("h", 1, None),
        ("cnot", 1, 2),
        ("x", 0, None),
        ("z", 2, None),
    ):
        if kind == "h":
            gate = (pauli_matrix(1 << a, 0, 0, n) + pauli_matrix(0, 1 << a, 0, n)) / np.sqrt(2)
        elif kind in ("x", "z"):
            gate = pauli_matrix(1 << a if kind == "x" else 0, 1 << a if kind == "z" else 0, 0, n)
        else:
            gate = np.zeros_like(unitary)
            for j in range(1 << n):
                k = j ^ ((1 << b) if kind == "cnot" and j >> a & 1 else 0)
                gate[k, j] = (-1) ** ((j >> a & 1) * (j >> b & 1)) if kind == "cz" else 1
        unitary = unitary @ gate
        frame.append(kind, a, b)
        for x, z in product(range(8), repeat=2):
            p = Pauli(x, z, (x & z).bit_count() % 4)
            expected = unitary @ pauli_matrix(**asdict(p), n=n) @ unitary.conj().T
            assert np.linalg.norm(pauli_matrix(**asdict(frame.present(p)), n=n) - expected) < 1e-12


@pytest.mark.parametrize("invalid", [0, -1, True, 1.5])
def test_invalid_capacity_rejected(invalid: int) -> None:
    with pytest.raises(ValueError):
        Limits(parallel=invalid)


def test_anticommuting_input_rejected() -> None:
    with pytest.raises(ValueError, match="commuting"):
        lower((Pauli(x=1), Pauli(z=1)), "general")


def test_invalid_operands_and_service_count() -> None:
    with pytest.raises(ValueError, match="operand"):
        Frame(3).append("h", -1)
    with pytest.raises(ValueError, match="operand"):
        Frame(3).append("cnot", 1, 3)
    with pytest.raises(ValueError, match="readout"):
        schedule_macro(lower((Pauli(z=1),), "qwc"), Limits(), Timing(), -1)


def test_service_and_virtual_pauli_signs() -> None:
    for p, correction, raw in product(
        (Pauli(1), Pauli(z=1), Pauli(1, 1, 1)), (Pauli(1), Pauli(z=1), Pauli(1, 1, 1)), (0, 1)
    ):
        m = pauli_matrix(**asdict(p), n=1)
        c = pauli_matrix(**asdict(correction), n=1)
        corrected = rebase_measurement_bit(p, correction, raw)
        assert np.allclose(
            c @ ((np.eye(2) + (-1) ** raw * m) / 2) @ c.conj().T,
            (np.eye(2) + (-1) ** corrected * m) / 2,
        )
    lo = lower((Pauli(3, 2, 1), Pauli(2, 1)), "general")
    timing = Timing(prepare_zero=0.25, readout=0.2, reaction=0.1, prepare_lanes=1, readout_lanes=2)
    sched = schedule_macro(lo, Limits(4), timing, 9)
    audit_service(asdict(lo), asdict(sched), asdict(timing), 9)
    assert sched.duration is not None
    with pytest.raises(ValueError, match="time mismatch"):
        audit_service(
            asdict(lo), asdict(replace(sched, duration=sched.duration + 1)), asdict(timing), 9
        )


def test_small_exact_packing_oracle() -> None:
    ppms = (Pauli(1, 2), Pauli(2, 1), Pauli(4, 1), Pauli(z=3), Pauli(z=5), Pauli(x=6))
    limits = Limits(3, 2, 5)
    # Independent exhaustive set partition oracle on six ready measurements.
    best = len(ppms)

    def visit(i: int, bins: list[list[int]]) -> None:
        nonlocal best
        if i == len(ppms):
            best = min(best, len(bins))
            return
        if len(bins) >= best:
            return
        for bucket in bins:
            if (
                len(bucket) < 3
                and sum(ppms[j].weight for j in bucket) + ppms[i].weight <= 5
                and all(ppms[i].qwc(ppms[j]) for j in bucket)
            ):
                bucket.append(i)
                visit(i + 1, bins)
                bucket.pop()
        visit(i + 1, [*bins, [i]])

    visit(0, [])
    assert best == 4
    assert len(pack(ppms, limits)) >= best


def test_randomized_signed_regularization_and_mutations() -> None:
    rng = Random(20260926)
    for _ in range(40):
        frame = Frame(8)
        for _ in range(80):
            a, b = rng.sample(range(8), 2)
            frame.append(rng.choice(("h", "x", "z", "cz", "cnot")), a, b)
        ppms = tuple(frame.z)
        assert all((p.x & p.z).bit_count() % 2 == 0 for p in ppms)
        lo = lower(ppms, "general")
        assert lo.y_catalysts == 0
        audit_lowering([asdict(p) for p in ppms], asdict(lo))
        for stage in lo.stages:
            assert all(p.qwc(q) for i, p in enumerate(stage.ppms) for q in stage.ppms[:i])
        if lo.gadgets:
            corrupted = asdict(lo)
            corrupted["gadgets"][0]["outcome_xor"] ^= 1
            with pytest.raises(ValueError, match="gadget contract"):
                audit_lowering([asdict(p) for p in ppms], corrupted)
