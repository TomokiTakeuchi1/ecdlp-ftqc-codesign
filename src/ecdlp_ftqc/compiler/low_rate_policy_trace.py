"""Legacy policy on the SAME signed branch and macro contract as full tracking.

At a macro entrance F, BOTH physical H layers use F H_T F^dagger.
The coupling PPMs use F Z F^dagger, and the outgoing frame is F H_T D H_T.
It would be a different policy to conjugate the closing H by the post-D frame.
Source bare Cliffords U update F -> U F U^dagger. Their cost is NOT zero.
"""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Literal

from ecdlp_ftqc.circuits.qcla import build_qcla_trace
from ecdlp_ftqc.circuits.qcla_oop import build_oop_qcla_trace
from ecdlp_ftqc.compiler.parallel_low_rate_trace import (
    Frame,
    Pauli,
    TrackedTrace,
    branch_bits,
    build_tracked_trace,
    diagonal_correction,
)

Variant = Literal["oop", "ip"]


def physical_conjugate(p: Pauli, kind: str, a: int, b: int | None = None) -> Pauli:
    """Elementary LEFT conjugation, in the i^phase X^x Z^z convention."""
    if type(a) is not int or a < 0:
        raise ValueError("invalid physical Clifford operand")
    x, z, phase = p.x, p.z, p.phase
    xa, za = (x >> a) & 1, (z >> a) & 1
    if kind == "h":
        x ^= (xa ^ za) << a
        z ^= (xa ^ za) << a
        phase += 2 * xa * za
    elif kind == "x":
        phase += 2 * za
    elif kind == "z":
        phase += 2 * xa
    elif kind in ("cnot", "cz"):
        if type(b) is not int or b < 0 or a == b:
            raise ValueError("invalid two-qubit Clifford operands")
        if kind == "cnot":
            x ^= xa << b
            z ^= ((z >> b) & 1) << a
        else:
            xb = (x >> b) & 1
            z ^= (xa << b) | (xb << a)
            phase += 2 * xa * xb
    else:
        raise ValueError("unsupported physical Clifford")
    return Pauli(x, z, phase % 4)


def apply_bare(frame: Frame, kind: str, a: int, b: int | None) -> None:
    """Implement desired U physically, retaining F_out = U F U^dagger."""
    frame.append(kind, a, b)
    # Source traces contain only X/CNOT here. Avoid rebuilding unchanged
    # columns; the dense-matrix tests also cover this optimized left action.
    if kind == "cnot":
        assert b is not None
        ca, tb = 1 << a, 1 << b
        for columns in (frame.x, frame.z):
            for j, p in enumerate(columns):
                if p.x & ca or p.z & tb:
                    columns[j] = Pauli(
                        p.x ^ (tb if p.x & ca else 0), p.z ^ (ca if p.z & tb else 0), p.phase
                    )
        return
    if kind == "x":
        mask = 1 << a
        for columns in (frame.x, frame.z):
            for j, p in enumerate(columns):
                if p.z & mask:
                    columns[j] = Pauli(p.x, p.z, (p.phase + 2) % 4)
        return
    frame.x = [physical_conjugate(p, kind, a, b) for p in frame.x]
    frame.z = [physical_conjugate(p, kind, a, b) for p in frame.z]


@lru_cache(maxsize=16)
def _blueprint(variant: Variant, width: int) -> TrackedTrace:
    return build_tracked_trace(variant, width, -2)


def build_legacy_trace(variant: Variant, width: int, branch: int) -> TrackedTrace:
    """Signed conjugated-H/bare-source-Clifford trace; no native H/CNOT service."""
    if variant not in ("oop", "ip") or type(width) is not int or width < 2:
        raise ValueError("supported variant and integer width >= 2 required")
    if type(branch) is not int or branch < -2:
        raise ValueError("invalid branch index")
    plan = _blueprint(variant, width)
    source = build_oop_qcla_trace(width) if variant == "oop" else build_qcla_trace(width)
    gates = {g.gate_id: g for g in source.gates}
    ids = {q: i for i, q in enumerate(plan.data_names)}
    frame = Frame(len(ids))
    macros = []
    for macro in plan.macros:
        for op in macro.preceding_cliffords:
            apply_bare(frame, *op)
        group = [gates[gid] for gid in macro.gate_ids]
        outcomes = tuple(branch_bits(variant, g.gate_id, branch) for g in group)
        ppms = tuple(
            frame.z[ids[q]] * Pauli(z=1 << (macro.resource_start + j))
            for j, q in enumerate(q for g in group for q in g.logical_support)
        )
        if any(p.x for p in ppms):
            raise ValueError("legacy Z-family invariant failed")
        # Defer ALL updates until the common-frame coupling/readout has completed.
        for q in macro.opening_targets:
            frame.append("h", q)
        for g, bits in zip(group, outcomes, strict=True):
            for op in diagonal_correction(
                (ids[g.controls[0]], ids[g.controls[1]]), ids[g.target], bits
            ):
                frame.append(*op)
        for q in macro.opening_targets:
            frame.append("h", q)
        macros.append(replace(macro, ppms=ppms, outcomes=outcomes))
    for op in plan.trailing_cliffords:
        apply_bare(frame, *op)
    return replace(
        plan, branch=branch, macros=tuple(macros), final_x=tuple(frame.x), final_z=tuple(frame.z)
    )
