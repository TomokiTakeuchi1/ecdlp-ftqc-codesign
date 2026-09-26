"""Signed full-Clifford tracking for frozen, reviewed joint-CCZ QCLA macros.

Convention: physical = F ideal; presented(P) = F P F dagger. Tracked U
updates F -> F U dagger. Integers encode i**phase X**x Z**z (little endian).
No physical scratch release, gate synthesis, or native timing is implied.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from ecdlp_ftqc.circuits.qcla import QclaGate, QclaGateKind, build_qcla_trace
from ecdlp_ftqc.circuits.qcla_oop import OopQclaGate, build_oop_qcla_trace
from ecdlp_ftqc.scheduler.width256_commutation_aware_qcla import (
    _streaming_nodes as oop_nodes,
)
from ecdlp_ftqc.scheduler.width256_ip_commutation_aware_qcla import (
    _streaming_nodes as ip_nodes,
)

SEED = "T-20260926-001-full-frame-v1"


@dataclass(frozen=True, slots=True)
class Pauli:
    """Possibly non-Hermitian Pauli for phase-exact multiplication."""

    x: int = 0
    z: int = 0
    phase: int = 0

    def __post_init__(self) -> None:
        if (
            any(type(v) is not int for v in (self.x, self.z, self.phase))
            or self.x < 0
            or self.z < 0
            or self.phase not in range(4)
        ):
            raise ValueError("invalid Pauli")

    def __mul__(self, other: Pauli) -> Pauli:
        return Pauli(
            self.x ^ other.x,
            self.z ^ other.z,
            (self.phase + other.phase + 2 * (self.z & other.x).bit_count()) % 4,
        )

    @property
    def weight(self) -> int:
        return (self.x | self.z).bit_count()

    @property
    def sign(self) -> int:
        phase = (self.phase - (self.x & self.z).bit_count()) % 4
        if phase % 2:
            raise ValueError("measurement must be Hermitian")
        return phase // 2

    def commutes(self, other: Pauli) -> bool:
        return ((self.x & other.z).bit_count() + (self.z & other.x).bit_count()) % 2 == 0

    def qwc(self, other: Pauli) -> bool:
        shared = (self.x | self.z) & (other.x | other.z)
        return not shared & ((self.x ^ other.x) | (self.z ^ other.z))

    def negated(self) -> Pauli:
        return Pauli(self.x, self.z, (self.phase + 2) % 4)


class Frame:
    """Images of canonical X/Z under F, updated by right multiplication."""

    def __init__(self, size: int) -> None:
        if type(size) is not int or size < 0:
            raise ValueError("nonnegative frame size required")
        self.x = [Pauli(x=1 << q) for q in range(size)]
        self.z = [Pauli(z=1 << q) for q in range(size)]

    def append(self, kind: str, a: int, b: int | None = None) -> None:
        if not 0 <= a < len(self.x) or (
            kind in ("cnot", "cz") and (b is None or not 0 <= b < len(self.x))
        ):
            raise ValueError("Clifford operand out of range")
        if kind == "h":
            self.x[a], self.z[a] = self.z[a], self.x[a]
        elif kind == "x":
            self.z[a] = self.z[a].negated()
        elif kind == "z":
            self.x[a] = self.x[a].negated()
        elif kind == "cnot" and b is not None and a != b:
            self.x[a] = self.x[a] * self.x[b]
            self.z[b] = self.z[b] * self.z[a]
        elif kind == "cz" and b is not None and a != b:
            self.x[a], self.x[b] = self.x[a] * self.z[b], self.x[b] * self.z[a]
        else:
            raise ValueError("unsupported Clifford generator")

    def present(self, p: Pauli) -> Pauli:
        result = Pauli(phase=p.phase)
        for mask, columns in ((p.x, self.x), (p.z, self.z)):
            while mask:
                bit = mask & -mask
                result = result * columns[bit.bit_length() - 1]
                mask ^= bit
        return result


@dataclass(frozen=True, slots=True)
class Macro:
    index: int
    gate_ids: tuple[str, ...]
    ppms: tuple[Pauli, ...]
    outcomes: tuple[tuple[int, ...], ...]
    opening_targets: tuple[int, ...]
    preceding_cliffords: tuple[tuple[str, int, int | None], ...]
    required_previous_macro: int | None
    resource_start: int
    resource_end: int


@dataclass(frozen=True, slots=True)
class TrackedTrace:
    variant: str
    width: int
    branch: int
    data_names: tuple[str, ...]
    macros: tuple[Macro, ...]
    trailing_cliffords: tuple[tuple[str, int, int | None], ...]
    final_x: tuple[Pauli, ...]
    final_z: tuple[Pauli, ...]


def branch_bits(variant: str, gate_id: str, branch: int) -> tuple[int, ...]:
    """-2/-1 are forced zero/one; nonnegative indices are seeded witnesses."""
    if branch < -2:
        raise ValueError("invalid branch index")
    if branch < 0:
        return (branch + 2,) * 6
    data = f"{SEED}|{variant}|{gate_id}|{branch}".encode()
    value = hashlib.shake_256(data).digest(1)[0]
    return tuple((value >> j) & 1 for j in range(6))


def diagonal_correction(
    controls: tuple[int, int],
    target: int,
    bits: tuple[int, ...],
) -> tuple[tuple[str, int, int | None], ...]:
    """Figure 14(a) correction before the closing target H."""
    if len(bits) != 6 or any(bit not in (0, 1) for bit in bits):
        raise ValueError("six binary outcomes required")
    a, b, c, x, y, z = bits
    u, v = controls
    candidates = (
        (a, "cz", v, target),
        (b, "cz", u, target),
        (c, "cz", u, v),
        (x ^ (b & c), "z", u, None),
        (y ^ (a & c), "z", v, None),
        (z ^ (a & b), "z", target, None),
    )
    return tuple((kind, q, r) for enabled, kind, q, r in candidates if enabled)


def build_tracked_trace(
    variant: Literal["oop", "ip"],
    width: int,
    branch: int,
) -> TrackedTrace:
    """Preserve reviewed source barriers and common incoming macro frame."""
    gates: tuple[OopQclaGate | QclaGate, ...]
    if variant == "oop":
        source_oop = build_oop_qcla_trace(width)
        gates = source_oop.gates
        nodes = oop_nodes(
            source_oop, tuple(g for g in source_oop.gates if g.kind is QclaGateKind.TOFFOLI)
        )
        ranks = {n.source_gate_id: n.macro_rank for n in nodes}
    elif variant == "ip":
        source_ip = build_qcla_trace(width)
        gates = source_ip.gates
        nodes_ip = ip_nodes(
            source_ip, tuple(g for g in source_ip.gates if g.kind is QclaGateKind.TOFFOLI)
        )
        ranks = {n.source_gate_id: n.macro_rank for n in nodes_ip}
    else:
        raise ValueError("variant must be oop or ip")
    names = tuple(sorted({q for g in gates for q in g.logical_support}))
    ids = {name: i for i, name in enumerate(names)}
    frame = Frame(len(names))
    barriers = sorted({g.algorithmic_layer for g in gates if g.kind is not QclaGateKind.TOFFOLI})
    used_barriers: set[int] = set()
    macros: list[Macro] = []

    def cliffords(layers: list[int]) -> tuple[tuple[str, int, int | None], ...]:
        result = []
        for g in gates:
            if g.algorithmic_layer in layers and g.kind is not QclaGateKind.TOFFOLI:
                op = (
                    ("cnot", ids[g.controls[0]], ids[g.target])
                    if g.controls
                    else ("x", ids[g.target], None)
                )
                frame.append(*op)
                result.append(op)
        used_barriers.update(layers)
        return tuple(result)

    resource_next = len(names)
    for rank in sorted(set(ranks.values())):
        group = tuple(g for g in gates if ranks.get(g.gate_id) == rank)
        before = cliffords(
            [
                layer
                for layer in barriers
                if layer not in used_barriers and layer < min(g.algorithmic_layer for g in group)
            ]
        )
        targets = tuple(sorted({ids[g.target] for g in group}))
        for target in targets:
            frame.append("h", target)
        ppms: list[Pauli] = []
        start = resource_next
        outcomes = tuple(branch_bits(variant, g.gate_id, branch) for g in group)
        for g in group:
            for name in g.logical_support:
                ppms.append(frame.z[ids[name]] * Pauli(z=1 << resource_next))
                resource_next += 1
        # Corrections are inserted only AFTER every common-frame PPM and readout.
        for g, bits in zip(group, outcomes, strict=True):
            for op in diagonal_correction(
                (ids[g.controls[0]], ids[g.controls[1]]), ids[g.target], bits
            ):
                frame.append(*op)
        for target in targets:
            frame.append("h", target)
        macros.append(
            Macro(
                rank,
                tuple(g.gate_id for g in group),
                tuple(ppms),
                outcomes,
                targets,
                before,
                rank - 1 if rank > 1 else None,
                start,
                resource_next,
            )
        )
    trailing = cliffords([layer for layer in barriers if layer not in used_barriers])
    return TrackedTrace(
        variant, width, branch, names, tuple(macros), trailing, tuple(frame.x), tuple(frame.z)
    )
