"""Paired-policy semantics, accounting, conditional feasibility and mutations."""

from copy import deepcopy
from dataclasses import asdict
from itertools import product

import numpy as np
import pytest

from ecdlp_ftqc.analysis.low_rate_break_even import (
    Services,
    paired_budget,
    scheduled_services,
    summarize_pairs,
)
from ecdlp_ftqc.circuits.qcla import build_qcla_trace
from ecdlp_ftqc.circuits.qcla_oop import build_oop_qcla_trace
from ecdlp_ftqc.compiler.low_rate_policy_trace import (
    apply_bare,
    build_legacy_trace,
    physical_conjugate,
)
from ecdlp_ftqc.compiler.parallel_low_rate_trace import (
    Frame,
    Pauli,
    build_tracked_trace,
    diagonal_correction,
)
from ecdlp_ftqc.scheduler.parallel_low_rate import Limits, Timing, lower
from ecdlp_ftqc.verification.low_rate_break_even import (
    audit_aggregate,
    audit_legacy_trace,
    audit_pair,
    audit_pair_alignment,
)
from ecdlp_ftqc.verification.parallel_low_rate import pauli_matrix


def dense(kind, a, b, n):
    if kind == "h":
        return (pauli_matrix(1 << a, 0, 0, n) + pauli_matrix(0, 1 << a, 0, n)) / np.sqrt(2)
    if kind in ("x", "z"):
        return pauli_matrix(1 << a if kind == "x" else 0, 1 << a if kind == "z" else 0, 0, n)
    matrix = np.zeros((1 << n, 1 << n), dtype=complex)
    for j in range(1 << n):
        k = j ^ ((1 << b) if kind == "cnot" and j >> a & 1 else 0)
        matrix[k, j] = (-1) ** ((j >> a & 1) * (j >> b & 1)) if kind == "cz" else 1
    return matrix


@pytest.mark.parametrize(
    "kind,a,b", [("h", 1, None), ("x", 0, None), ("z", 2, None), ("cnot", 0, 2), ("cz", 2, 1)]
)
def test_left_physical_conjugation_dense(kind, a, b):
    unitary = dense(kind, a, b, 3)
    for x, z, sign in product(range(8), range(8), range(2)):
        p = Pauli(x, z, ((x & z).bit_count() + 2 * sign) % 4)
        actual = pauli_matrix(**asdict(physical_conjugate(p, kind, a, b)), n=3)
        assert np.allclose(actual, unitary @ pauli_matrix(**asdict(p), n=3) @ unitary.conj().T)


def test_bare_updates_are_two_sided_not_tracking():
    frame = Frame(3)
    unitary = np.eye(8, dtype=complex)
    for op in (("h", 0, None), ("cz", 0, 1), ("cnot", 1, 2)):
        frame.append(*op)
        unitary = unitary @ dense(*op, 3)
    for op in (("cnot", 0, 2), ("x", 1, None), ("cnot", 2, 1)):
        apply_bare(frame, *op)
        gate = dense(*op, 3)
        unitary = gate @ unitary @ gate.conj().T
        for q in range(3):
            for p, actual in ((Pauli(1 << q), frame.x[q]), (Pauli(z=1 << q), frame.z[q])):
                assert np.allclose(
                    pauli_matrix(**asdict(actual), n=3),
                    unitary @ pauli_matrix(**asdict(p), n=3) @ unitary.conj().T,
                )


@pytest.mark.parametrize("variant", ["oop", "ip"])
@pytest.mark.parametrize("branch", [-2, -1, 0, 17])
def test_legacy_signed_trace_and_pairing(variant, branch):
    for width in (2, 5, 8):
        trace = build_legacy_trace(variant, width, branch)
        tracked = build_tracked_trace(variant, width, branch)
        source = build_oop_qcla_trace(width) if variant == "oop" else build_qcla_trace(width)
        data = asdict(trace)
        assert audit_legacy_trace(data, [asdict(g) for g in source.gates]) == sum(
            len(m.ppms) for m in trace.macros
        )
        audit_pair_alignment(asdict(tracked), data)
        assert all(p.x == 0 for m in trace.macros for p in m.ppms)
        for m in trace.macros:
            assert lower(m.ppms, "general").stages == lower(m.ppms, "qwc").stages


def test_mutated_legacy_and_branch_pairing_rejected():
    trace = asdict(build_legacy_trace("oop", 5, 0))
    source = [asdict(g) for g in build_oop_qcla_trace(5).gates]
    for field in ("phase", "z"):
        bad = deepcopy(trace)
        bad["macros"][1]["ppms"][0][field] ^= 2
        with pytest.raises(ValueError, match="PPM mismatch"):
            audit_legacy_trace(bad, source)
    bad = deepcopy(trace)
    bad["final_z"][0]["phase"] ^= 2
    with pytest.raises(ValueError, match="retained frame"):
        audit_legacy_trace(bad, source)
    with pytest.raises(ValueError, match="pairing"):
        audit_pair_alignment(asdict(build_tracked_trace("oop", 5, 1)), trace)


@pytest.mark.parametrize("events", [((0, 1, 2), (0, 1, 3)), ((0, 1, 3), (0, 2, 3))])
def test_shared_control_or_target_macro_all_4096_branches(events):
    n = 4
    ident = np.eye(1 << n, dtype=complex)
    incoming = dense("h", 0, None, n) @ dense("cz", 0, 1, n) @ dense("cnot", 1, 2, n)
    h = ident.copy()
    for t in sorted({event[2] for event in events}):
        h = h @ dense("h", t, None, n)
    physical_h = incoming @ h @ incoming.conj().T
    ideal = ident.copy()
    # Independently build the product of CCX matrices, not H V H.
    for u, v, t in events:
        ccx = np.zeros_like(ident)
        for j in range(1 << n):
            ccx[j ^ ((1 << t) if (j >> u & 1) and (j >> v & 1) else 0), j] = 1
        ideal = ccx @ ideal
    event_branches = []
    for u, v, t in events:
        records = []
        for bits in product((0, 1), repeat=6):
            # ZZ fixes r_j = d_j XOR a_j; resource amplitudes and X bras give K.
            amplitudes = []
            for d in range(1 << n):
                r = tuple((d >> q & 1) ^ bits[j] for j, q in enumerate((u, v, t)))
                amplitudes.append(
                    (-1) ** (r[0] * r[1] * r[2] + sum(bits[j + 3] * r[j] for j in range(3))) / 8
                )
            correction = ident.copy()
            for op in diagonal_correction((u, v), t, bits):
                correction = correction @ dense(*op, n)
            records.append((np.diag(amplitudes), correction))
        event_branches.append(records)
    for left, right in product(*event_branches):
        kernel, correction = left[0] @ right[0], left[1] @ right[1]
        raw = physical_h @ incoming @ kernel @ incoming.conj().T @ physical_h @ incoming
        outgoing = incoming @ h @ correction @ h
        expected = outgoing @ ideal
        scalar = np.trace(expected.conj().T @ raw) / (1 << n)
        assert abs(abs(scalar) - 1 / 64) < 1e-12
        assert np.linalg.norm(raw - scalar * expected) < 1e-12
        # Tracking the Hs instead implements the same raw channel at this entrance F.
        tracked = incoming @ h @ kernel @ h
        assert np.allclose(raw, tracked)


@pytest.mark.parametrize(
    "left,right",
    [
        (Services(3), Services(2)),
        (Services(2), Services(3)),
        (None, Services(1)),
        (Services(1), None),
        (None, None),
    ],
)
def test_pair_cost_and_infeasible_cases(left, right):
    timing = Timing(prepare_zero=0.25, readout=0.25, reaction=0.1)
    row = paired_budget(left, right, timing)
    audit_pair(row, asdict(timing))
    if left is not None and right is not None:
        assert row["b_crit_units"] == left.surgery - right.surgery
        row["b_crit_units"] += 1
    else:
        assert row["b_crit_units"] is None
        row["b_crit_units"] = 0
    with pytest.raises(ValueError):
        audit_pair(row, asdict(timing))


def test_paired_quantiles_not_difference_of_medians():
    timing = Timing()
    rows = [
        paired_budget(Services(a), Services(b), timing) for a, b in ((1, 0), (2, 100), (100, 1))
    ]
    result = summarize_pairs(rows)
    assert result["b_crit_units"]["p50"] == 1
    # Stronger counterexample: median deltas 10, difference of marginal medians -10.
    rows = [
        paired_budget(Services(a), Services(b), timing) for a, b in ((10, 0), (20, 100), (100, 30))
    ]
    result = summarize_pairs(rows)
    assert result["b_crit_units"]["p50"] == 10
    assert result["tracked_common_units"]["p50"] - result["legacy_ppm_common_units"]["p50"] == -10
    audit_aggregate(rows, result)
    result["b_crit_units"]["p50"] = -10
    with pytest.raises(ValueError, match="quantile"):
        audit_aggregate(rows, result)


def test_preparation_readout_and_no_free_overweight_fallback():
    ppms = (Pauli(3, 2, 1), Pauli(2, 1))
    lo = lower(ppms, "general")
    timing = Timing(prepare_zero=0.25, readout=0.25, reaction=0.1, prepare_lanes=1, readout_lanes=1)
    assert scheduled_services([lo], [6], Limits(weight=2), timing) is None
    result = scheduled_services([lo], [6], Limits(), timing)
    assert result is not None and result.prepare > 0 and result.readout > 6 and result.reaction > 1
    assert paired_budget(result, None, timing)["legacy_complete_duration"] is None


@pytest.mark.parametrize(
    "variant,width,branch",
    [("invalid", 5, 0), ("oop", True, 0), ("oop", 1, 0), ("ip", 5, -3), ("ip", 5, True)],
)
def test_bad_policy_inputs_rejected(variant, width, branch):
    with pytest.raises(ValueError):
        build_legacy_trace(variant, width, branch)
