"""Hybrid-policy anchors, independent trace replay and fail-closed costs."""

import importlib.util
import json
from copy import deepcopy
from dataclasses import asdict
from itertools import product
from pathlib import Path

import numpy as np
import pytest

from ecdlp_ftqc.circuits.qcla import build_qcla_trace
from ecdlp_ftqc.compiler.h_tracked_bare_cnot_trace import build_hybrid_trace
from ecdlp_ftqc.compiler.low_rate_policy_trace import apply_bare, build_legacy_trace
from ecdlp_ftqc.compiler.parallel_low_rate_trace import (
    Frame,
    build_tracked_trace,
    diagonal_correction,
)
from ecdlp_ftqc.scheduler.parallel_low_rate import Limits, Timing, lower, schedule_macro
from ecdlp_ftqc.verification.h_tracked_bare_cnot_low_rate import (
    audit_comparison,
    audit_hybrid_trace,
    audit_summary,
)
from ecdlp_ftqc.verification.low_rate_break_even import audit_pair_alignment
from ecdlp_ftqc.verification.parallel_low_rate import pauli_matrix


def dense(kind, a, b=None, n=3):
    if kind == "h":
        return (pauli_matrix(1 << a, 0, 0, n) + pauli_matrix(0, 1 << a, 0, n)) / np.sqrt(2)
    if kind in ("x", "z"):
        return pauli_matrix(1 << a if kind == "x" else 0, 1 << a if kind == "z" else 0, 0, n)
    mat = np.zeros((1 << n, 1 << n), complex)
    for j in range(1 << n):
        k = j ^ ((1 << b) if kind == "cnot" and j >> a & 1 else 0)
        mat[k, j] = (-1) ** ((j >> a & 1) * (j >> b & 1)) if kind == "cz" else 1
    return mat


@pytest.mark.parametrize("x_policy", ["bare", "frame"])
@pytest.mark.parametrize("branch", [-2, -1, 0, 17])
def test_signed_source_plan_and_frame_replay(x_policy, branch):
    for width in (2, 5, 8):
        hybrid = build_hybrid_trace(width, branch, x_policy)
        source = [asdict(g) for g in build_qcla_trace(width).gates]
        assert audit_hybrid_trace(asdict(hybrid), source, x_policy) == sum(
            len(m.ppms) for m in hybrid.macros
        )
        audit_pair_alignment(asdict(build_tracked_trace("ip", width, branch)), asdict(hybrid))
        assert all((p.x & p.z).bit_count() % 2 == 0 for m in hybrid.macros for p in m.ppms)


@pytest.mark.parametrize("x_policy", ["bare", "frame"])
def test_dense_tracked_h_injection_after_bare_cnot_all_outcomes(x_policy):
    incoming = dense("h", 0) @ dense("cz", 0, 1) @ dense("cnot", 1, 2)
    baseline = Frame(3)
    for op in (("h", 0, None), ("cz", 0, 1), ("cnot", 1, 2)):
        baseline.append(*op)
    # This is not full tracking: both-sided bare conjugation is essential.
    u = dense("cnot", 0, 2)
    apply_bare(baseline, "cnot", 0, 2)
    entrance = u @ incoming @ u.conj().T
    x = dense("x", 1)
    if x_policy == "bare":
        apply_bare(baseline, "x", 1, None)
        entrance = x @ entrance @ x
    else:
        baseline.append("x", 1)
        entrance = entrance @ x
    h = dense("h", 2)
    ccx = np.zeros((8, 8), complex)
    for j in range(8):
        ccx[j ^ (4 if j & 3 == 3 else 0), j] = 1
    for bits in product((0, 1), repeat=6):
        frame = deepcopy(baseline)
        frame.append("h", 2)
        open_frame = entrance @ h
        for q in range(3):
            assert np.allclose(
                pauli_matrix(**asdict(frame.z[q]), n=3),
                open_frame @ dense("z", q) @ open_frame.conj().T,
            )
        amplitudes = []
        for j in range(8):
            r = [(j >> q & 1) ^ bits[q] for q in range(3)]
            amplitudes.append(
                (-1) ** (r[0] * r[1] * r[2] + sum(bits[q + 3] * r[q] for q in range(3))) / 8
            )
        raw = open_frame @ np.diag(amplitudes) @ h
        correction = np.eye(8, dtype=complex)
        for op in diagonal_correction((0, 1), 2, bits):
            frame.append(*op)
            correction = correction @ dense(*op)
        frame.append("h", 2)
        outgoing = entrance @ h @ correction @ h
        expected = outgoing @ ccx
        scalar = np.trace(expected.conj().T @ raw) / 8
        assert abs(abs(scalar) - 1 / 8) < 1e-12
        assert np.linalg.norm(raw - scalar * expected) < 1e-12
        for q in range(3):
            for axis, col in (("x", frame.x[q]), ("z", frame.z[q])):
                assert np.allclose(
                    pauli_matrix(**asdict(col), n=3), outgoing @ dense(axis, q) @ outgoing.conj().T
                )


def test_width5_hybrid_is_neither_previous_policy():
    hybrid = build_hybrid_trace(5, 0)
    assert hybrid != build_tracked_trace("ip", 5, 0)
    assert hybrid != build_legacy_trace("ip", 5, 0)
    assert any(p.x and p.z for m in hybrid.macros for p in m.ppms)


def test_width5_rejects_previous_policies_and_wrong_x_mode():
    source = [asdict(g) for g in build_qcla_trace(5).gates]
    for wrong in (
        build_tracked_trace("ip", 5, 17),
        build_legacy_trace("ip", 5, 17),
        build_hybrid_trace(5, 17, "frame"),
    ):
        with pytest.raises(ValueError):
            audit_hybrid_trace(asdict(wrong), source, "bare")


@pytest.mark.parametrize("macro_index", [3, 6])
def test_width5_actual_shared_control_target_macros_all_4096_outcomes(macro_index):
    source = {g.gate_id: g for g in build_qcla_trace(5).gates}
    macro = build_hybrid_trace(5, 0).macros[macro_index - 1]
    group = [source[gid] for gid in macro.gate_ids]
    names = sorted({q for g in group for q in g.logical_support})
    ids = {q: i for i, q in enumerate(names)}
    events = [tuple(ids[q] for q in (*g.controls, g.target)) for g in group]
    assert len(events) == 2 and len(names) == 5
    n = len(names)
    dim = 1 << n
    identity = np.eye(dim, dtype=complex)
    frame = Frame(n)
    incoming = identity.copy()
    for op in (("h", 0, None), ("cz", 0, 1), ("cnot", 1, 2)):
        frame.append(*op)
        incoming = incoming @ dense(*op, n)
    u = dense("cnot", 0, 3, n)
    incoming = u @ incoming @ u
    apply_bare(frame, "cnot", 0, 3)
    h = identity.copy()
    for t in sorted({e[2] for e in events}):
        h = h @ dense("h", t, None, n)
    opened = incoming @ h
    ideal = identity.copy()
    records = []
    for a, b, t in events:
        ccx = np.zeros_like(identity)
        for j in range(dim):
            ccx[j ^ ((1 << t) if (j >> a & 1) and (j >> b & 1) else 0), j] = 1
        ideal = ccx @ ideal
        event_records = []
        for bits in product((0, 1), repeat=6):
            amplitudes = []
            for j in range(dim):
                r = [(j >> q & 1) ^ bits[k] for k, q in enumerate((a, b, t))]
                amplitudes.append(
                    (-1) ** (r[0] * r[1] * r[2] + sum(bits[k + 3] * r[k] for k in range(3))) / 8
                )
            correction = identity.copy()
            for op in diagonal_correction((a, b), t, bits):
                correction = correction @ dense(*op, n)
            event_records.append((np.diag(amplitudes), correction))
        records.append(event_records)
    for left, right in product(*records):
        raw = opened @ left[0] @ right[0] @ h
        outgoing = opened @ left[1] @ right[1] @ h
        expected = outgoing @ ideal
        scalar = np.trace(expected.conj().T @ raw) / dim
        assert abs(abs(scalar) - 1 / 64) < 1e-12
        assert np.linalg.norm(raw - scalar * expected) < 1e-12
    # Removing the tracked opening H must not pass the same channel check.
    wrong = incoming @ records[0][0][1] @ records[1][0][1] @ h @ ideal
    raw = opened @ records[0][0][0] @ records[1][0][0] @ h
    scalar = np.trace(wrong.conj().T @ raw) / dim
    assert np.linalg.norm(raw - scalar * wrong) > 1e-3


def test_x_policy_changes_signs_not_axes_or_services():
    bare, virtual = (build_hybrid_trace(5, 17, p) for p in ("bare", "frame"))
    assert bare != virtual
    for left, right in zip(bare.macros, virtual.macros, strict=True):
        assert [(p.x, p.z) for p in left.ppms] == [(p.x, p.z) for p in right.ppms]
        for mode in ("qwc", "general"):
            a, b = lower(left.ppms, mode), lower(right.ppms, mode)
            assert schedule_macro(a, Limits(4), Timing(), len(left.ppms)) == schedule_macro(
                b, Limits(4), Timing(), len(right.ppms)
            )


@pytest.mark.parametrize("x_policy", ["bare", "frame"])
def test_full_to_hybrid_is_physical_source_clifford_prefix(x_policy):
    def image(p, physical_prefix):
        # Independent scalar i^phase X^x Z^z action, not a frame tableau.
        x, z, phase = p.x, p.z, p.phase
        for kind, a, b in physical_prefix:
            if kind == "x":
                phase = (phase + 2 * (z >> a & 1)) % 4
            else:
                x ^= ((x >> a) & 1) << b
                z ^= ((z >> b) & 1) << a
        return (x, z, phase)

    for width in (2, 5, 8):
        for branch in (-2, -1, 0, 17):
            full = build_tracked_trace("ip", width, branch)
            hybrid = build_hybrid_trace(width, branch, x_policy)
            prefix = []
            for a, b in zip(full.macros, hybrid.macros, strict=True):
                prefix.extend(
                    op for op in a.preceding_cliffords if op[0] == "cnot" or x_policy == "bare"
                )
                assert [image(p, prefix) for p in a.ppms] == [(p.x, p.z, p.phase) for p in b.ppms]
                # CNOT preserves the full x_i dot z_j bilinear form, not QWC.
                assert [[(p.x & q.z).bit_count() % 2 for q in a.ppms] for p in a.ppms] == [
                    [(p.x & q.z).bit_count() % 2 for q in b.ppms] for p in b.ppms
                ]
            prefix.extend(
                op for op in full.trailing_cliffords if op[0] == "cnot" or x_policy == "bare"
            )
            assert [image(p, prefix) for p in (*full.final_x, *full.final_z)] == [
                (p.x, p.z, p.phase) for p in (*hybrid.final_x, *hybrid.final_z)
            ]


@pytest.mark.parametrize(
    "mutation",
    ["phase", "axis", "frame", "outcome", "resource", "barrier", "macro", "target", "reaction"],
)
def test_trace_mutations_fail(mutation):
    trace = asdict(build_hybrid_trace(5, 17))
    source = [asdict(g) for g in build_qcla_trace(5).gates]
    m = trace["macros"][1]
    if mutation == "phase":
        m["ppms"][0]["phase"] ^= 2
    elif mutation == "axis":
        m["ppms"][0]["x"] ^= 1
    elif mutation == "frame":
        trace["final_x"][0]["phase"] ^= 2
    elif mutation == "outcome":
        m["outcomes"] = tuple((0,) * 6 for _ in m["outcomes"])
    elif mutation == "resource":
        m["resource_start"] -= 3
    elif mutation == "barrier":
        trace["macros"][0]["preceding_cliffords"] = (("x", 0, None),)
    elif mutation == "macro":
        trace["macros"] = trace["macros"][::-1]
    elif mutation == "target":
        m["opening_targets"] = ()
    else:
        m["required_previous_macro"] = None
    with pytest.raises(ValueError):
        audit_hybrid_trace(trace, source, "bare")


@pytest.mark.parametrize(
    "width,branch,policy",
    [(True, 0, "bare"), (1, 0, "bare"), (5, -3, "bare"), (5, True, "bare"), (5, 0, "wrong")],
)
def test_invalid_inputs(width, branch, policy):
    with pytest.raises(ValueError):
        build_hybrid_trace(width, branch, policy)


def cycle_module():
    path = Path(__file__).resolve().parents[2] / "scripts/run_h_tracked_bare_cnot_low_rate_cycle.py"
    spec = importlib.util.spec_from_file_location("hybrid_cycle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generator_exact_audits_reproduction_and_mutations(tmp_path):
    cycle = cycle_module()
    config = json.loads(cycle.MANIFEST.read_text())
    config.update(width=5, hashed_branches=1)
    hashes = cycle.source_hashes()
    job = (0, config, str(tmp_path), hashes)
    first = cycle.cached_job(job)
    assert cycle.cached_job(job) == first
    assert len(first["grid"]) == 441
    assert len(first["comparisons"]) == 504
    assert sum(r["count"] for r in first["cnot_layers"]) == 15
    assert first["source_x_count"] == 8
    repeat = tmp_path / "repeat"
    repeat.mkdir()
    fresh = cycle.profile(0, config, repeat)
    assert fresh == first
    assert (repeat / fresh["artifact"]).read_bytes() == (tmp_path / first["artifact"]).read_bytes()
    forced = [cycle.profile(b, config, tmp_path) for b in (-2, -1)]
    branches = [*forced, first]
    summary = {
        "config": config,
        "branches": branches,
        "complete_native_schedule": False,
        **cycle.aggregate(branches, 1),
    }
    audit_summary(summary)
    for mutate in ("quantile", "duplicate", "missing", "cost", "native", "legacy", "auto"):
        bad = deepcopy(summary)
        if mutate == "quantile":
            next(r for r in bad["comparisons"] if r["delta_units"] is not None)["delta_units"][
                "p50"
            ] += 1
        elif mutate == "duplicate":
            bad["branches"].append(bad["branches"][0])
        elif mutate == "missing":
            bad["branches"][0]["grid"].pop()
        elif mutate == "cost":
            next(r for r in bad["branches"][0]["grid"] if r["feasible"])["units_exact"][0] += 1
        elif mutate == "native":
            bad["physical_qubits"] = 123
        elif mutate == "legacy":
            next(r for r in bad["branches"][0]["comparisons"] if r["reference_policy"] == "legacy")[
                "absolute_hybrid_budget"
            ] = 0
        else:
            bad["branches"][0]["cnot_layers"][0]["native_call_count"] = 1
        with pytest.raises(ValueError):
            audit_summary(bad)
    changed = deepcopy(config)
    changed["timing"]["surgery"] = 2
    with pytest.raises(ValueError, match="stale checkpoint"):
        cycle.cached_job((0, changed, str(tmp_path), hashes))
    (tmp_path / first["artifact"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="artifact hash"):
        cycle.cached_job(job)
    with pytest.raises(ValueError, match="missing or duplicate"):
        cycle.aggregate([first, first], 1)


@pytest.mark.parametrize("a,b", [(1, 5), (5, 1), (3, 3), (None, 1), (1, None), (None, None)])
def test_signed_budgets_and_feasibility(a, b):
    cycle = cycle_module()

    def row(value, policy):
        return {
            "policy": policy,
            "mode": "qwc",
            "parallel": 64,
            "weight": None,
            "total_support": None,
            "width": 256,
            "feasible": value is not None,
            "units_exact": [value, 1] if value is not None else None,
            "services": {"surgery": value, "prepare": 0, "readout": 0, "reaction": 0}
            if value is not None
            else None,
        }

    ref, hyb = row(a, "full"), row(b, "hybrid_bare")
    comparison = cycle.pair(ref, hyb)
    audit_comparison(comparison, ref, hyb)
    if a is not None and b is not None:
        assert comparison["delta_units"] == a - b
        assert comparison["equal_auto_call_allowance_if_four_calls_and_tx_zero"] == (a - b) / 4
    else:
        assert comparison["delta_units"] is None
    ref["policy"] = "legacy"
    comparison = cycle.pair(ref, hyb)
    assert comparison["absolute_hybrid_budget"] is None
    assert comparison["condition"] == "B_hybrid - B_legacy < delta"
