"""Parameterized parallel low-rate surgery macros, NOT a native code mapper."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ecdlp_ftqc.compiler.parallel_low_rate_trace import Pauli


@dataclass(frozen=True, slots=True)
class Limits:
    parallel: int | None = None
    weight: int | None = None
    total_support: int | None = None

    def __post_init__(self) -> None:
        if any(
            v is not None and (type(v) is not int or v < 1)
            for v in (self.parallel, self.weight, self.total_support)
        ):
            raise ValueError("limits must be positive integers or None")


@dataclass(frozen=True, slots=True)
class Timing:
    """CHECK sensitivity, in units of one base measurement service time.

    Readout/preparation lanes are separate from PPM lanes. None means unlimited.
    Reaction includes decoding/sign rebasing; every regular subset is a barrier.
    """

    surgery: float = 1.0
    prepare_zero: float = 0.0
    readout: float = 0.0
    reaction: float = 0.0
    prepare_lanes: int | None = None
    readout_lanes: int | None = None
    seconds_per_unit: float | None = None

    def __post_init__(self) -> None:
        if self.surgery <= 0 or any(
            not math.isfinite(v) or v < 0
            for v in (self.surgery, self.prepare_zero, self.readout, self.reaction)
        ):
            raise ValueError("durations must be finite and nonnegative; surgery positive")
        Limits(self.prepare_lanes)
        Limits(self.readout_lanes)
        if self.seconds_per_unit is not None and (
            not math.isfinite(self.seconds_per_unit) or self.seconds_per_unit <= 0
        ):
            raise ValueError("invalid sensitivity seconds conversion")


@dataclass(frozen=True, slots=True)
class Regularization:
    generators: tuple[Pauli, ...]
    combinations: tuple[int, ...]
    groups: tuple[tuple[int, ...], ...]


def rebase_measurement_bit(observable: Pauli, pending_pauli: Pauli, raw_bit: int) -> int:
    """Interpret a physical outcome in the canonically corrected coordinate."""
    if raw_bit not in (0, 1):
        raise ValueError("binary measurement outcome required")
    return raw_bit ^ int(not observable.commutes(pending_pauli))


def regularize(ppms: tuple[Pauli, ...]) -> Regularization:
    """Symmetric GF(2) congruence: 1x1 and hyperbolic 2x2 blocks.

    Each new signed generator is an EXACT product of original generators.
    Split hyperbolic pairs across two regular sets; no row is discarded.
    """
    if not ppms:
        return Regularization((), (), ())
    for p in ppms:
        _ = p.sign
    bilinear_rows = [
        sum(((p.x & q.z).bit_count() % 2) << j for j, q in enumerate(ppms)) if p.x else 0
        for p in ppms
    ]
    if any(
        ((bilinear_rows[i] >> j) ^ (bilinear_rows[j] >> i)) & 1
        for i in range(len(ppms))
        for j in range(i)
    ):
        raise ValueError("joint measurement requires commuting observables")
    rows = list(ppms)
    masks = [1 << i for i in range(len(rows))]
    active = list(range(len(rows)))
    first: list[int] = []
    second: list[int] = []

    def add(dst: int, src: int) -> None:
        rows[dst] = rows[dst] * rows[src]
        masks[dst] ^= masks[src]

    while active:
        active_mask = sum(1 << i for i in active)
        pivot = next((i for i in active if bilinear_rows[i] >> i & 1), None)
        if pivot is not None:
            active.remove(pivot)
            neighbors = bilinear_rows[pivot] & (active_mask ^ (1 << pivot))
            for k in active:
                if neighbors >> k & 1:
                    add(k, pivot)
                    bilinear_rows[k] ^= neighbors
            first.append(pivot)
            continue
        pair = None
        for i in active:
            later = bilinear_rows[i] & active_mask & ~((1 << (i + 1)) - 1)
            if later:
                pair = (i, (later & -later).bit_length() - 1)
                break
        if pair is None:
            first.extend(active)
            break
        i, j = pair
        active.remove(i)
        active.remove(j)
        remaining = active_mask ^ (1 << i) ^ (1 << j)
        neighbors_i = bilinear_rows[i] & remaining
        neighbors_j = bilinear_rows[j] & remaining
        for k in active:
            with_i, with_j = neighbors_i >> k & 1, neighbors_j >> k & 1
            if with_i:
                add(k, j)
                bilinear_rows[k] ^= neighbors_j
            if with_j:
                add(k, i)
                bilinear_rows[k] ^= neighbors_i
        first.append(i)
        second.append(j)
    return Regularization(tuple(rows), tuple(masks), tuple(tuple(g) for g in (first, second) if g))


def recover_original_outcomes(
    combinations: tuple[int, ...], outcomes: tuple[int, ...]
) -> tuple[int, ...]:
    """Invert the signed-generator product map over GF(2)."""
    n = len(combinations)
    if len(outcomes) != n or any(b not in (0, 1) for b in outcomes):
        raise ValueError("invalid generator outcome vector")
    rows = list(combinations)
    bits = list(outcomes)
    for col in range(n):
        pivot = next((j for j in range(col, n) if rows[j] >> col & 1), None)
        if pivot is None:
            raise ValueError("noninvertible generator map")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        bits[col], bits[pivot] = bits[pivot], bits[col]
        for j in range(n):
            if j != col and rows[j] >> col & 1:
                rows[j] ^= rows[col]
                bits[j] ^= bits[col]
    return tuple(bits)


@dataclass(frozen=True, slots=True)
class Gadget:
    generator_index: int
    a: int
    b: int | None
    first: Pauli
    second: Pauli
    outcome_xor: int
    correction: Pauli


def twist_gadget(p: Pauli, index: int, a: int, b: int) -> Gadget:
    """Measure first, second, then Z_A; apply correction iff Z_A=-1.

    Outcome bit = m_first XOR m_second XOR outcome_xor. For odd Y count,
    the correction includes Z_B to restore the catalyst |Y+>.
    """
    if min(a, b) < (p.x | p.z).bit_length() or a == b:
        raise ValueError("ancillas must be fresh and distinct")
    y = (p.x & p.z).bit_count()
    odd = y % 2
    first = Pauli(x=p.x | (1 << a) | ((1 << b) if odd else 0))
    second = Pauli(x=1 << a, z=p.z | ((1 << b) if odd else 0))
    correction = Pauli(z=p.z | ((1 << b) if odd else 0))
    return Gadget(
        index, a, b if odd else None, first, second, p.sign ^ (((y + 1) // 2) % 2), correction
    )


@dataclass(frozen=True, slots=True)
class Stage:
    kind: str
    ppms: tuple[Pauli, ...]
    labels: tuple[int, ...]
    zero_preparations: int = 0
    final_readouts: int = 0
    reaction_after: bool = False


@dataclass(frozen=True, slots=True)
class Lowering:
    mode: str
    stages: tuple[Stage, ...]
    regularization: Regularization
    gadgets: tuple[Gadget, ...]
    logical_ancillas: int
    y_catalysts: int


def lower(ppms: tuple[Pauli, ...], mode: Literal["qwc", "general"]) -> Lowering:
    if mode not in ("qwc", "general") or not ppms:
        raise ValueError("nonempty PPM set and supported mode required")
    if any(not p.weight for p in ppms):
        raise ValueError("identity inputs must be resolved before surgery")
    union = Pauli()
    whole_qwc = True
    for p in ppms:
        _ = p.sign
        whole_qwc = whole_qwc and p.qwc(union)
        union = Pauli(union.x | p.x, union.z | p.z)
    identity = Regularization(
        ppms, tuple(1 << i for i in range(len(ppms))), (tuple(range(len(ppms))),)
    )
    if mode == "qwc" or whole_qwc:
        if not whole_qwc and any(not p.commutes(q) for i, p in enumerate(ppms) for q in ppms[:i]):
            raise ValueError("noncommuting PPMs")
        return Lowering(mode, (Stage("direct", ppms, tuple(range(len(ppms)))),), identity, (), 0, 0)
    regular = regularize(ppms)
    fresh = max((p.x | p.z).bit_length() for p in ppms)
    gadgets = tuple(
        twist_gadget(p, i, fresh + 2 * i, fresh + 2 * i + 1)
        for i, p in enumerate(regular.generators)
    )
    stages: list[Stage] = []
    for group in regular.groups:
        subset = [gadgets[i] for i in group]
        catalysts = tuple(Pauli(1 << g.b, 1 << g.b, 1) for g in subset if g.b is not None)
        if catalysts:
            stages.append(
                Stage(
                    "prepare_y",
                    catalysts,
                    tuple(g.generator_index for g in subset if g.b is not None),
                    zero_preparations=len(catalysts),
                    reaction_after=True,
                )
            )
        stages.append(
            Stage("split_x", tuple(g.first for g in subset), group, zero_preparations=len(subset))
        )
        stages.append(
            Stage(
                "split_z",
                tuple(g.second for g in subset),
                group,
                final_readouts=len(subset),
                reaction_after=True,
            )
        )
    return Lowering(
        mode,
        tuple(stages),
        regular,
        gadgets,
        len(gadgets) + sum(g.b is not None for g in gadgets),
        sum(g.b is not None for g in gadgets),
    )


@dataclass(frozen=True, slots=True)
class Batch:
    indices: tuple[int, ...]
    weight_sum: int
    support_union: int
    maximum_weight: int


def pack(ppms: tuple[Pauli, ...], limits: Limits) -> tuple[Batch, ...]:
    """Deterministic source-order first-fit QWC packing; not an optimum."""
    if limits.parallel == 1:
        if any(
            (limits.weight is not None and p.weight > limits.weight)
            or (limits.total_support is not None and p.weight > limits.total_support)
            for p in ppms
        ):
            raise ValueError("executed_ppm_exceeds_support_limit")
        return tuple(Batch((i,), p.weight, p.weight, p.weight) for i, p in enumerate(ppms))
    bins: list[list[int]] = []
    unions: list[Pauli] = []
    sums: list[int] = []
    for i, p in enumerate(ppms):
        if (limits.weight is not None and p.weight > limits.weight) or (
            limits.total_support is not None and p.weight > limits.total_support
        ):
            raise ValueError("executed_ppm_exceeds_support_limit")
        selected = next(
            (
                j
                for j, bucket in enumerate(bins)
                if (limits.parallel is None or len(bucket) < limits.parallel)
                and (limits.total_support is None or sums[j] + p.weight <= limits.total_support)
                and p.qwc(unions[j])
            ),
            None,
        )
        if selected is None:
            selected = len(bins)
            bins.append([])
            unions.append(Pauli())
            sums.append(0)
        bins[selected].append(i)
        union = unions[selected]
        unions[selected] = Pauli(union.x | p.x, union.z | p.z)
        sums[selected] += p.weight
    return tuple(
        Batch(tuple(bucket), sums[j], unions[j].weight, max(ppms[i].weight for i in bucket))
        for j, bucket in enumerate(bins)
    )


def lane_steps(count: int, lanes: int | None) -> int:
    return math.ceil(count / lanes) if lanes is not None else int(count > 0)


@dataclass(frozen=True, slots=True)
class MacroSchedule:
    feasible: bool
    reason: str | None
    batches: tuple[tuple[Batch, ...], ...]
    surgery_steps: int | None
    prepare_steps: int
    readout_steps: int
    reaction_steps: int
    duration: float | None


def schedule_macro(
    lowering: Lowering, limits: Limits, timing: Timing, resource_readouts: int
) -> MacroSchedule:
    """Serial stage barriers, conservative readout and reaction frontiers."""
    if type(resource_readouts) is not int or resource_readouts < 0:
        raise ValueError("nonnegative resource readout count required")
    try:
        packed = tuple(pack(stage.ppms, limits) for stage in lowering.stages)
    except ValueError as exc:
        return MacroSchedule(False, str(exc), (), None, 0, 0, 0, None)
    surgery = sum(map(len, packed))
    prep = sum(lane_steps(s.zero_preparations, timing.prepare_lanes) for s in lowering.stages)
    read = sum(lane_steps(s.final_readouts, timing.readout_lanes) for s in lowering.stages)
    read += lane_steps(resource_readouts, timing.readout_lanes)
    reaction = sum(s.reaction_after for s in lowering.stages) + 1
    duration = (
        surgery * timing.surgery
        + prep * timing.prepare_zero
        + read * timing.readout
        + reaction * timing.reaction
    )
    return MacroSchedule(True, None, packed, surgery, prep, read, reaction, duration)
