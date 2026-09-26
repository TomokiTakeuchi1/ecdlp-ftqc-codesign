"""Independent matrix and reverse-history audits; no tracker/scheduler helpers.

Public checks consume serialized data, not the implementation's dataclasses.
"""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache
from itertools import product
from typing import Any

import numpy as np
from numpy.typing import NDArray

Matrix = NDArray[np.complex128]


@lru_cache(maxsize=32)
def _source_plan(
    gates: tuple[tuple[str, str, tuple[str, ...], str, int], ...],
) -> tuple[tuple[str, ...], ...]:
    """Complete-pair longest path, independent of the streaming recurrence."""
    barriers = {g[4] for g in gates if g[1] != "toffoli"}
    ccxs = [g for g in gates if g[1] == "toffoli"]
    ranks: list[int] = []
    for i, right in enumerate(ccxs):
        parents = [
            ranks[j]
            for j, left in enumerate(ccxs[:i])
            if left[3] in right[2]
            or right[3] in left[2]
            or any(left[4] < layer < right[4] for layer in barriers)
        ]
        ranks.append(1 + max(parents, default=0))
    return tuple(
        tuple(g[0] for g, r in zip(ccxs, ranks, strict=True) if r == rank)
        for rank in range(1, max(ranks, default=0) + 1)
    )


def pauli_matrix(x: int, z: int, phase: int, n: int) -> Matrix:
    matrix = np.zeros((1 << n, 1 << n), dtype=np.complex128)
    for j in range(1 << n):
        matrix[j ^ x, j] = (1j**phase) * (-1) ** ((j & z).bit_count() % 2)
    return matrix


def audit_gadget(p: dict[str, int], gadget: dict[str, Any], n: int) -> float:
    """Exhaust ALL internal outcomes and verify the complete data instrument.

    The generator may be signed, contain Y, or have several Y terms. Check the
    restored catalyst as a vector, not only after tracing it out.
    """
    a, b = gadget["a"], gadget["b"]
    if a != n or (b is not None and b != n + 1):
        raise ValueError("matrix anchor requires adjacent fresh ancillas")
    total = n + 1 + int(b is not None)
    dim = 1 << n
    embedding = np.zeros((1 << total, dim), dtype=np.complex128)
    for i in range(dim):
        embedding[i, i] = 1 if b is None else 1 / np.sqrt(2)
        if b is not None:
            embedding[i | (1 << b), i] = 1j / np.sqrt(2)
    ideal = pauli_matrix(p["x"], p["z"], p["phase"], n)
    ops = [
        pauli_matrix(gadget[name]["x"], gadget[name]["z"], gadget[name]["phase"], total)
        for name in ("first", "second")
    ]
    corr = pauli_matrix(**gadget["correction"], n=total)
    error = 0.0
    for s in range(8):
        u, v, r = (s >> j & 1 for j in range(3))
        state = embedding.copy()
        for bit, op in zip((u, v), ops, strict=True):
            state = (state + (-1) ** bit * op @ state) / 2
        state = state.copy()
        state[[j for j in range(1 << total) if (j >> a & 1) != r], :] = 0
        if r:
            state = corr @ state
        # Reset measured A to zero solely to compare the output isometry.
        reset = np.zeros_like(state)
        for j in range(1 << total):
            if (j >> a & 1) == r:
                reset[j ^ (r << a), :] = state[j, :]
        outcome = u ^ v ^ gadget["outcome_xor"]
        target = embedding @ ((np.eye(dim) + (-1) ** outcome * ideal) / 2)
        norm = float(np.vdot(target, target).real)
        if norm == 0:
            error = max(error, float(np.linalg.norm(reset)))
        else:
            coefficient = np.vdot(target, reset) / norm
            error = max(
                error,
                float(np.linalg.norm(reset - coefficient * target)),
                abs(float(abs(coefficient)) - 0.5),
            )
    if error > 1e-10:
        raise ValueError(f"measurement instrument mismatch: {error}")
    return error


def audit_joint_instrument(
    original: list[dict[str, int]], lowered: dict[str, Any], n: int
) -> float:
    """Tiny exhaustive instrument oracle for the actual regular-subset stage order."""
    gadgets = lowered["gadgets"]
    if not gadgets or len(gadgets) > 3:
        raise ValueError("anchor requires one to three twist-free gadgets")
    total = max(max(g["a"], g["b"] or 0) for g in gadgets) + 1
    dim = 1 << n
    embedding = np.zeros((1 << total, dim), dtype=complex)
    catalysts = [g["b"] for g in gadgets if g["b"] is not None]
    for i in range(dim):
        for cat_bits in product((0, 1), repeat=len(catalysts)):
            row = i | sum(bit << q for bit, q in zip(cat_bits, catalysts, strict=True))
            embedding[row, i] = 1j ** sum(cat_bits) / np.sqrt(2 ** len(catalysts))
    ops = [
        (
            pauli_matrix(**g["first"], n=total),
            pauli_matrix(**g["second"], n=total),
            pauli_matrix(**g["correction"], n=total),
        )
        for g in gadgets
    ]
    originals = [pauli_matrix(**p, n=n) for p in original]
    combinations = lowered["regularization"]["combinations"]
    # Enumerate original outcomes to independently invert their linear map.
    inverse = {
        tuple(
            sum(bits[j] for j in range(len(bits)) if mask >> j & 1) % 2 for mask in combinations
        ): bits
        for bits in product((0, 1), repeat=len(original))
    }
    maximum = 0.0
    for branch in product(range(8), repeat=len(gadgets)):
        state = embedding.copy()
        for group in lowered["regularization"]["groups"]:
            for step in (0, 1):
                for i in group:
                    bit = branch[i] >> step & 1
                    state = (state + (-1) ** bit * ops[i][step] @ state) / 2
            for i in group:
                bit = branch[i] >> 2 & 1
                a = gadgets[i]["a"]
                state[[j for j in range(1 << total) if (j >> a & 1) != bit], :] = 0
                if bit:
                    state = ops[i][2] @ state
                reset = np.zeros_like(state)
                for j in range(1 << total):
                    if (j >> a & 1) == bit:
                        reset[j ^ (bit << a), :] = state[j, :]
                state = reset
        gen_bits = tuple(
            (b & 1) ^ (b >> 1 & 1) ^ g["outcome_xor"] for b, g in zip(branch, gadgets, strict=True)
        )
        ideal = np.eye(dim, dtype=complex)
        for bit, op in zip(inverse[gen_bits], originals, strict=True):
            ideal = (ideal + (-1) ** bit * op @ ideal) / 2
        target = embedding @ ideal
        norm = float(np.vdot(target, target).real)
        if norm == 0:
            maximum = max(maximum, float(np.linalg.norm(state)))
        else:
            scalar = np.vdot(target, state) / norm
            maximum = max(
                maximum,
                float(np.linalg.norm(state - scalar * target)),
                abs(float(abs(scalar)) - 0.5 ** len(gadgets)),
            )
    if maximum > 1e-10:
        raise ValueError(f"joint instrument mismatch: {maximum}")
    return maximum


def audit_lowering(original: list[dict[str, int]], lowered: dict[str, Any]) -> None:
    """Reconstruct signed generator products and regularity independently."""
    regular = lowered["regularization"]
    for claimed, mask in zip(regular["generators"], regular["combinations"], strict=True):
        x = z = phase = 0
        while mask:
            bit = mask & -mask
            p = original[bit.bit_length() - 1]
            phase = (phase + p["phase"] + 2 * (z & p["x"]).bit_count()) % 4
            x ^= p["x"]
            z ^= p["z"]
            mask ^= bit
        if claimed != {"x": x, "z": z, "phase": phase}:
            raise ValueError("signed generator product mismatch")
    # Rank of the outcome change-of-basis map must be full.
    basis: dict[int, int] = {}
    for mask in regular["combinations"]:
        while mask:
            pivot = mask.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = mask
                break
            mask ^= basis[pivot]
    if len(basis) != len(original):
        raise ValueError("singular outcome map")
    if lowered["gadgets"]:
        gadgets = lowered["gadgets"]
        if len(gadgets) != len(original):
            raise ValueError("gadget coverage mismatch")
        stages = iter(lowered["stages"])
        catalysts_total = 0
        for i, (p, gadget) in enumerate(zip(regular["generators"], gadgets, strict=True)):
            a, b = gadget["a"], gadget["b"]
            k = (p["x"] & p["z"]).bit_count()
            if (
                a < (p["x"] | p["z"]).bit_length()
                or (b is None) != (k % 2 == 0)
                or gadget["generator_index"] != i
            ):
                raise ValueError("gadget ancilla mismatch")
            bm = 0 if b is None else 1 << b
            catalysts_total += int(b is not None)
            expected_first = {"x": p["x"] | (1 << a) | bm, "z": 0, "phase": 0}
            expected_second = {"x": 1 << a, "z": p["z"] | bm, "phase": 0}
            expected_sign = ((p["phase"] - k) % 4) // 2 ^ (((k + 1) // 2) % 2)
            if (
                gadget["first"] != expected_first
                or gadget["second"] != expected_second
                or gadget["outcome_xor"] != expected_sign
                or gadget["correction"] != {"x": 0, "z": p["z"] | bm, "phase": 0}
            ):
                raise ValueError("twist-free gadget contract mismatch")
        if (
            lowered["logical_ancillas"] != len(original) + catalysts_total
            or lowered["y_catalysts"] != catalysts_total
        ):
            raise ValueError("ancilla accounting mismatch")
        for group in regular["groups"]:
            group_catalysts = [gadgets[i]["b"] for i in group if gadgets[i]["b"] is not None]
            if group_catalysts:
                stage = next(stages)
                expected_y = [{"x": 1 << q, "z": 1 << q, "phase": 1} for q in group_catalysts]
                if (
                    stage["kind"] != "prepare_y"
                    or list(stage["ppms"]) != expected_y
                    or stage["zero_preparations"] != len(expected_y)
                    or not stage["reaction_after"]
                ):
                    raise ValueError("catalyst preparation mismatch")
            first, second = next(stages), next(stages)
            if (
                first["kind"] != "split_x"
                or second["kind"] != "split_z"
                or list(first["ppms"]) != [gadgets[i]["first"] for i in group]
                or list(second["ppms"]) != [gadgets[i]["second"] for i in group]
                or first["zero_preparations"] != len(group)
                or second["final_readouts"] != len(group)
                or not second["reaction_after"]
            ):
                raise ValueError("gadget stage mismatch")
            for i in group:
                for j in group:
                    if (
                        i != j
                        and (
                            regular["generators"][i]["x"] & regular["generators"][j]["z"]
                        ).bit_count()
                        % 2
                    ):
                        raise ValueError("nonregular subset")
        if next(stages, None) is not None:
            raise ValueError("extra measurement stages")
    elif (
        len(lowered["stages"]) != 1
        or list(lowered["stages"][0]["ppms"]) != original
        or lowered["logical_ancillas"] != 0
        or lowered["y_catalysts"] != 0
    ):
        raise ValueError("direct lowering mismatch")


def audit_packing(lowered: dict[str, Any], schedule: dict[str, Any], limits: dict[str, Any]) -> int:
    """Replay membership, QWC, limits and batch statistics without first-fit."""
    if not schedule["feasible"]:
        if not any(
            (limits["weight"] is not None and (p["x"] | p["z"]).bit_count() > limits["weight"])
            or (
                limits["total_support"] is not None
                and (p["x"] | p["z"]).bit_count() > limits["total_support"]
            )
            for stage in lowered["stages"]
            for p in stage["ppms"]
        ):
            raise ValueError("unsupported infeasibility claim")
        return 0
    steps = 0
    for stage, batches in zip(lowered["stages"], schedule["batches"], strict=True):
        seen = []
        for batch in batches:
            indices = batch["indices"]
            seen.extend(indices)
            ppms = [stage["ppms"][i] for i in indices]
            weights = [(p["x"] | p["z"]).bit_count() for p in ppms]
            union = 0
            seen_x = seen_z = seen_y = 0
            for p in ppms:
                support = p["x"] | p["z"]
                union |= support
                only_x, only_z, y = p["x"] & ~p["z"], p["z"] & ~p["x"], p["x"] & p["z"]
                if (
                    only_x & (seen_z | seen_y)
                    or only_z & (seen_x | seen_y)
                    or y & (seen_x | seen_z)
                ):
                    raise ValueError("QWC conflict")
                seen_x |= only_x
                seen_z |= only_z
                seen_y |= y
            for value, bound in (
                (len(ppms), limits["parallel"]),
                (max(weights), limits["weight"]),
                (sum(weights), limits["total_support"]),
            ):
                if bound is not None and value > bound:
                    raise ValueError("capacity exceeded")
            if (sum(weights), union.bit_count(), max(weights)) != (
                batch["weight_sum"],
                batch["support_union"],
                batch["maximum_weight"],
            ):
                raise ValueError("batch statistics mismatch")
        if sorted(seen) != list(range(len(stage["ppms"]))):
            raise ValueError("measurement missing or duplicated")
        steps += len(batches)
    if steps != schedule["surgery_steps"]:
        raise ValueError("surgery step mismatch")
    return steps


def audit_service(
    lowered: dict[str, Any],
    schedule: dict[str, Any],
    timing: dict[str, Any],
    resource_readouts: int,
) -> None:
    """Independent preparation/readout/reaction and conditional-time audit."""
    if not schedule["feasible"]:
        if schedule["duration"] is not None or schedule["surgery_steps"] is not None:
            raise ValueError("infeasible schedule has finite time")
        return

    def rounds(n: int, lanes: int | None) -> int:
        return (n + lanes - 1) // lanes if lanes else int(n > 0)

    prep = sum(rounds(s["zero_preparations"], timing["prepare_lanes"]) for s in lowered["stages"])
    readout = sum(
        rounds(s["final_readouts"], timing["readout_lanes"]) for s in lowered["stages"]
    ) + rounds(resource_readouts, timing["readout_lanes"])
    reaction = 1 + sum(int(s["reaction_after"]) for s in lowered["stages"])
    duration = (
        sum(len(b) for b in schedule["batches"]) * timing["surgery"]
        + prep * timing["prepare_zero"]
        + readout * timing["readout"]
        + reaction * timing["reaction"]
    )
    if (prep, readout, reaction) != (
        schedule["prepare_steps"],
        schedule["readout_steps"],
        schedule["reaction_steps"],
    ):
        raise ValueError("service accounting mismatch")
    if not math.isclose(duration, schedule["duration"], abs_tol=1e-10):
        raise ValueError("conditional time mismatch")


def audit_trace(trace: dict[str, Any], source_gates: list[dict[str, Any]]) -> int:
    """Reverse-history conjugation, bit-sliced over all probes in a macro.

    Uses elementary physical conjugation (not column products/right tableau
    updates). Derives corrections independently from ALL six recorded bits.
    """
    names = trace["data_names"]
    ids = {q: i for i, q in enumerate(names)}
    by_id = {g["gate_id"]: g for g in source_gates}
    source_plan = _source_plan(
        tuple(
            (g["gate_id"], g["kind"], tuple(g["controls"]), g["target"], g["algorithmic_layer"])
            for g in source_gates
        )
    )
    if tuple(tuple(m["gate_ids"]) for m in trace["macros"]) != source_plan:
        raise ValueError("source dependency/group mismatch")
    history: list[tuple[str, int, int | None]] = []
    audited = 0
    used: list[str] = []
    used_cliffords: set[str] = set()
    resource_next = len(names)

    def expected_cliffords(before_layer: int) -> list[tuple[str, int, int | None]]:
        result: list[tuple[str, int, int | None]] = []
        for g in source_gates:
            if (
                g["kind"] != "toffoli"
                and g["gate_id"] not in used_cliffords
                and g["algorithmic_layer"] < before_layer
            ):
                result.append(
                    ("cnot", ids[g["controls"][0]], ids[g["target"]])
                    if g["controls"]
                    else ("x", ids[g["target"]], None)
                )
                used_cliffords.add(g["gate_id"])
        return result

    def probes(inputs: list[tuple[int, str]]) -> list[dict[str, int]]:
        size = len(inputs)
        all_bits = (1 << size) - 1
        xs = [0] * len(names)
        zs = [0] * len(names)
        signs = 0
        for j, (q, axis) in enumerate(inputs):
            (xs if axis == "x" else zs)[q] |= 1 << j

        def h(q: int) -> None:
            nonlocal signs
            signs ^= xs[q] & zs[q]
            xs[q], zs[q] = zs[q], xs[q]

        for kind, a, b in reversed(history):
            if kind == "h":
                h(a)
            elif kind == "x":
                signs ^= zs[a]
            elif kind == "z":
                signs ^= xs[a]
            else:
                if b is None:
                    raise ValueError("two-qubit gate missing operand")
                if kind == "cz":
                    h(b)
                signs ^= xs[a] & zs[b] & (xs[b] ^ zs[a] ^ all_bits)
                xs[b] ^= xs[a]
                zs[a] ^= zs[b]
                if kind == "cz":
                    h(b)
        x_rows, z_rows = [0] * size, [0] * size
        for planes, decoded in ((xs, x_rows), (zs, z_rows)):
            for q, plane in enumerate(planes):
                while plane:
                    bit = plane & -plane
                    decoded[bit.bit_length() - 1] |= 1 << q
                    plane ^= bit
        result = []
        for j in range(size):
            x, z = x_rows[j], z_rows[j]
            result.append(
                {"x": x, "z": z, "phase": ((x & z).bit_count() + 2 * (signs >> j & 1)) % 4}
            )
        return result

    for index, macro in enumerate(trace["macros"], 1):
        group = [by_id[gid] for gid in macro["gate_ids"]]
        if macro["index"] != index or macro["required_previous_macro"] != (
            index - 1 if index > 1 else None
        ):
            raise ValueError("reaction frontier mismatch")
        if macro["resource_start"] != resource_next or macro[
            "resource_end"
        ] != resource_next + 3 * len(group):
            raise ValueError("resource ownership mismatch")
        resource_next = macro["resource_end"]
        if list(map(tuple, macro["preceding_cliffords"])) != expected_cliffords(
            min(g["algorithmic_layer"] for g in group)
        ):
            raise ValueError("source Clifford barrier mismatch")
        used.extend(macro["gate_ids"])
        history.extend(tuple(op) for op in macro["preceding_cliffords"])
        targets = sorted({ids[g["target"]] for g in group})
        if list(macro["opening_targets"]) != targets:
            raise ValueError("target H set mismatch")
        history.extend(("h", q, None) for q in targets)
        expected = probes([(ids[q], "z") for g in group for q in (*g["controls"], g["target"])])
        for j, (p, actual) in enumerate(zip(expected, macro["ppms"], strict=True)):
            p["z"] |= 1 << (macro["resource_start"] + j)
            if p != actual:
                raise ValueError("signed reverse-history trace mismatch")
        audited += len(expected)
        for g, bits in zip(group, macro["outcomes"], strict=True):
            branch = trace["branch"]
            if branch < 0:
                expected_bits = [branch + 2] * 6
            else:
                token = (
                    f"T-20260926-001-full-frame-v1|{trace['variant']}|{g['gate_id']}|{branch}"
                ).encode()
                value = hashlib.shake_256(token).digest(1)[0]
                expected_bits = [value >> j & 1 for j in range(6)]
            if list(bits) != expected_bits:
                raise ValueError("outcome seed mismatch")
            a, b, c, x, y, z = bits
            u, v, t = (ids[q] for q in (*g["controls"], g["target"]))
            for enabled, op in (
                (a, ("cz", v, t)),
                (b, ("cz", u, t)),
                (c, ("cz", u, v)),
                (x ^ (b * c), ("z", u, None)),
                (y ^ (a * c), ("z", v, None)),
                (z ^ (a * b), ("z", t, None)),
            ):
                if enabled:
                    history.append(op)
        history.extend(("h", q, None) for q in targets)
    if sorted(used) != sorted(g["gate_id"] for g in source_gates if g["kind"] == "toffoli"):
        raise ValueError("CCX coverage mismatch")
    if list(map(tuple, trace["trailing_cliffords"])) != expected_cliffords(10**9):
        raise ValueError("trailing Clifford mismatch")
    history.extend(tuple(op) for op in trace["trailing_cliffords"])
    final = probes([(q, axis) for axis in ("x", "z") for q in range(len(names))])
    if final != [*trace["final_x"], *trace["final_z"]]:
        raise ValueError("retained frame mismatch")
    return audited
