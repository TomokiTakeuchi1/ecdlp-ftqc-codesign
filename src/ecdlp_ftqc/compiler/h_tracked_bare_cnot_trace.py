"""Tracked target H, bare source CNOT, explicit bare/virtual source-X policy.

Only logical semantics live here. No automorphism, timing or addressability is
admitted by emitting this trace. Approved baseline implementations are reused
unchanged; the source macro/barrier plan is frozen across policies.
"""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Literal

from ecdlp_ftqc.circuits.qcla import QclaGate, build_qcla_trace
from ecdlp_ftqc.compiler.low_rate_policy_trace import apply_bare
from ecdlp_ftqc.compiler.parallel_low_rate_trace import (
    Frame,
    Pauli,
    TrackedTrace,
    branch_bits,
    build_tracked_trace,
    diagonal_correction,
)

XPolicy = Literal["bare", "frame"]


@lru_cache(maxsize=8)
def _plan(width: int) -> tuple[TrackedTrace, dict[str, QclaGate]]:
    return build_tracked_trace("ip", width, -2), {
        g.gate_id: g for g in build_qcla_trace(width).gates
    }


def build_hybrid_trace(width: int, branch: int, x_policy: XPolicy = "bare") -> TrackedTrace:
    """Return the signed hybrid IP trace in the convention physical = F ideal."""
    if type(width) is not int or width < 2:
        raise ValueError("integer width >= 2 required")
    if type(branch) is not int or branch < -2:
        raise ValueError("integer branch >= -2 required")
    if x_policy not in ("bare", "frame"):
        raise ValueError("X policy must be bare or frame")
    plan, gates = _plan(width)
    ids = {q: i for i, q in enumerate(plan.data_names)}
    frame = Frame(len(ids))

    def source_ops(ops: tuple[tuple[str, int, int | None], ...]) -> None:
        for op in ops:
            if op[0] == "x" and x_policy == "frame":
                frame.append(*op)
            else:
                apply_bare(frame, *op)

    macros = []
    for macro in plan.macros:
        source_ops(macro.preceding_cliffords)
        for q in macro.opening_targets:
            frame.append("h", q)
        group = [gates[gid] for gid in macro.gate_ids]
        outcomes = tuple(branch_bits("ip", g.gate_id, branch) for g in group)
        ppms = tuple(
            frame.z[ids[q]] * Pauli(z=1 << (macro.resource_start + j))
            for j, q in enumerate(q for g in group for q in g.logical_support)
        )
        if any((p.x & p.z).bit_count() % 2 for p in ppms):
            raise ValueError("real-Clifford even-Y invariant failed")
        # Common frame: no outcome from this macro modifies its own PPM list.
        for g, bits in zip(group, outcomes, strict=True):
            for op in diagonal_correction(
                (ids[g.controls[0]], ids[g.controls[1]]), ids[g.target], bits
            ):
                frame.append(*op)
        for q in macro.opening_targets:
            frame.append("h", q)
        macros.append(replace(macro, ppms=ppms, outcomes=outcomes))
    source_ops(plan.trailing_cliffords)
    return replace(
        plan, branch=branch, macros=tuple(macros), final_x=tuple(frame.x), final_z=tuple(frame.z)
    )
