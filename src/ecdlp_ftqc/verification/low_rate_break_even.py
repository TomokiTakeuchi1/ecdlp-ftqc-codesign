"""Independent signed-history and paired-statistics audits.

Does not import the new legacy compiler or break-even analysis. It uses the
approved complete-pair source oracle, not the compiler's cached blueprint.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

from ecdlp_ftqc.verification.parallel_low_rate import _source_plan


def audit_pair_alignment(tracked: dict[str, Any], legacy: dict[str, Any]) -> None:
    for key in ("variant", "width", "branch", "data_names", "trailing_cliffords"):
        if tracked[key] != legacy[key]:
            raise ValueError("policy branch pairing mismatch")
    if len(tracked["macros"]) != len(legacy["macros"]):
        raise ValueError("policy macro pairing mismatch")
    for tm, lm in zip(tracked["macros"], legacy["macros"], strict=True):
        if any(
            tm[key] != lm[key]
            for key in (
                "index",
                "gate_ids",
                "outcomes",
                "opening_targets",
                "preceding_cliffords",
                "required_previous_macro",
                "resource_start",
                "resource_end",
            )
        ):
            raise ValueError("policy event/outcome pairing mismatch")


def audit_legacy_trace(trace: dict[str, Any], source: list[dict[str, Any]]) -> int:
    names = trace["data_names"]
    ids = {name: i for i, name in enumerate(names)}
    if len(ids) != len(names) or set(ids) != {
        q for g in source for q in (*g["controls"], g["target"])
    }:
        raise ValueError("legacy data names mismatch")
    plan = _source_plan(
        tuple(
            (g["gate_id"], g["kind"], tuple(g["controls"]), g["target"], g["algorithmic_layer"])
            for g in source
        )
    )
    if tuple(tuple(m["gate_ids"]) for m in trace["macros"]) != plan:
        raise ValueError("legacy source macro mismatch")
    gates = {g["gate_id"]: g for g in source}
    history: list[tuple[str, int, int | None]] = []
    applied: set[str] = set()
    resource_next = len(names)
    count = 0

    def bare_before(layer: int, recorded: Any) -> None:
        expected = []
        for g in source:
            if g["kind"] == "toffoli" or g["gate_id"] in applied or g["algorithmic_layer"] >= layer:
                continue
            op = (
                ("cnot", ids[g["controls"][0]], ids[g["target"]])
                if g["controls"]
                else ("x", ids[g["target"]], None)
            )
            expected.append(op)
            # Mathematical factors U F U^dagger, replayed in reverse below.
            history.insert(0, op)
            history.append(op)
            applied.add(g["gate_id"])
        if list(map(tuple, recorded)) != expected:
            raise ValueError("legacy source Clifford mismatch")

    def image(probes: list[tuple[int, str]]) -> list[dict[str, int]]:
        xs, zs = [0] * len(names), [0] * len(names)
        sign = 0
        ones = (1 << len(probes)) - 1
        for j, (q, axis) in enumerate(probes):
            (xs if axis == "x" else zs)[q] |= 1 << j

        def hadamard(q: int) -> None:
            nonlocal sign
            sign ^= xs[q] & zs[q]
            xs[q], zs[q] = zs[q], xs[q]

        for kind, a, b in reversed(history):
            if kind == "h":
                hadamard(a)
            elif kind == "x":
                sign ^= zs[a]
            elif kind == "z":
                sign ^= xs[a]
            else:
                assert b is not None
                if kind == "cz":
                    hadamard(b)
                sign ^= xs[a] & zs[b] & (xs[b] ^ zs[a] ^ ones)
                xs[b] ^= xs[a]
                zs[a] ^= zs[b]
                if kind == "cz":
                    hadamard(b)
        xx, zz = [0] * len(probes), [0] * len(probes)
        for planes, outputs in ((xs, xx), (zs, zz)):
            for q, plane in enumerate(planes):
                while plane:
                    bit = plane & -plane
                    outputs[bit.bit_length() - 1] |= 1 << q
                    plane ^= bit
        return [
            {"x": x, "z": z, "phase": ((x & z).bit_count() + 2 * (sign >> j & 1)) % 4}
            for j, (x, z) in enumerate(zip(xx, zz, strict=True))
        ]

    for index, macro in enumerate(trace["macros"], 1):
        group = [gates[gid] for gid in macro["gate_ids"]]
        if macro["index"] != index or macro["required_previous_macro"] != (
            index - 1 if index > 1 else None
        ):
            raise ValueError("legacy reaction frontier mismatch")
        if (macro["resource_start"], macro["resource_end"]) != (
            resource_next,
            resource_next + 3 * len(group),
        ):
            raise ValueError("legacy resource ownership mismatch")
        bare_before(min(g["algorithmic_layer"] for g in group), macro["preceding_cliffords"])
        targets = sorted({ids[g["target"]] for g in group})
        if list(macro["opening_targets"]) != targets:
            raise ValueError("legacy H targets mismatch")
        expected = image([(ids[q], "z") for g in group for q in (*g["controls"], g["target"])])
        for j, (p, actual) in enumerate(zip(expected, macro["ppms"], strict=True)):
            p["z"] |= 1 << (resource_next + j)
            if p != actual or p["x"]:
                raise ValueError("legacy signed PPM mismatch")
        count += len(expected)
        resource_next = macro["resource_end"]
        history.extend(("h", q, None) for q in targets)
        for g, recorded in zip(group, macro["outcomes"], strict=True):
            branch = trace["branch"]
            if type(branch) is not int or branch < -2:
                raise ValueError("legacy branch index mismatch")
            if branch < 0:
                bits = [branch + 2] * 6
            else:
                value = hashlib.shake_256(
                    f"T-20260926-001-full-frame-v1|{trace['variant']}|{g['gate_id']}|{branch}".encode()
                ).digest(1)[0]
                bits = [value >> k & 1 for k in range(6)]
            if list(recorded) != bits:
                raise ValueError("legacy outcome mismatch")
            a, b, c, rx, ry, rz = bits
            u, v, t = (ids[q] for q in (*g["controls"], g["target"]))
            for enabled, op in (
                (a, ("cz", v, t)),
                (b, ("cz", u, t)),
                (c, ("cz", u, v)),
                (rx ^ b * c, ("z", u, None)),
                (ry ^ a * c, ("z", v, None)),
                (rz ^ a * b, ("z", t, None)),
            ):
                if enabled:
                    history.append(op)
        history.extend(("h", q, None) for q in targets)
    bare_before(10**9, trace["trailing_cliffords"])
    final = image([(q, axis) for axis in ("x", "z") for q in range(len(names))])
    if final != [*trace["final_x"], *trace["final_z"]]:
        raise ValueError("legacy retained frame mismatch")
    return count


def audit_pair(row: dict[str, Any], timing: dict[str, Any]) -> None:
    ts, ls = row["tracked_services"], row["legacy_ppm_services"]
    expected_state = (
        "both_ppm_feasible"
        if ts is not None and ls is not None
        else "tracked_ppm_only"
        if ts is not None
        else "legacy_ppm_only"
        if ls is not None
        else "neither_ppm_feasible"
    )
    if row["status"] != expected_state:
        raise ValueError("pair feasibility mismatch")
    coefficients = {
        "surgery": "surgery",
        "prepare": "prepare_zero",
        "readout": "readout",
        "reaction": "reaction",
    }
    costs: list[float | None] = []
    for services, field in (
        (ts, "tracked_conditional_units"),
        (ls, "legacy_ppm_conditional_units"),
    ):
        if services is None:
            if row[field] is not None:
                raise ValueError("finite infeasible cost")
            costs.append(None)
            continue
        if set(services) != set(coefficients) or any(
            type(v) is not int or v < 0 for v in services.values()
        ):
            raise ValueError("invalid service counts")
        value = sum(services[k] * timing[c] for k, c in coefficients.items())
        if not math.isclose(value, row[field], abs_tol=1e-9, rel_tol=0):
            raise ValueError("paired service cost mismatch")
        costs.append(value)
    if ts is not None and ls is not None:
        if row["delta_service_counts"] != {k: ts[k] - ls[k] for k in coefficients}:
            raise ValueError("paired coefficient mismatch")
        assert costs[0] is not None and costs[1] is not None
        if not math.isclose(costs[0] - costs[1], row["b_crit_units"], abs_tol=1e-9, rel_tol=0):
            raise ValueError("paired budget mismatch")
    elif row["b_crit_units"] is not None or row["delta_service_counts"] is not None:
        raise ValueError("budget outside paired intersection")
    if any(
        row[key] is not None
        for key in (
            "legacy_clifford_cost_units",
            "legacy_complete_duration",
            "native_runtime_seconds",
        )
    ):
        raise ValueError("unsupported complete/native cost")


def audit_aggregate(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    states = ("both_ppm_feasible", "tracked_ppm_only", "legacy_ppm_only", "neither_ppm_feasible")
    if summary["hashed_witness_count"] != len(rows) or summary["status_counts"] != {
        state: sum(row["status"] == state for row in rows) for state in states
    }:
        raise ValueError("paired sample counts mismatch")
    common = [row for row in rows if row["status"] == states[0]]
    for key, field in (
        ("b_crit_units", "b_crit_units"),
        ("tracked_common_units", "tracked_conditional_units"),
        ("legacy_ppm_common_units", "legacy_ppm_conditional_units"),
    ):
        values = sorted(row[field] for row in common)
        expected = (
            None
            if not values
            else {
                "min": values[0],
                "p50": values[(len(values) - 1) // 2],
                "p95": values[(95 * len(values) + 99) // 100 - 1],
                "max": values[-1],
            }
        )
        if summary[key] != expected:
            raise ValueError("paired quantile mismatch")
    if summary["negative_budget_count"] != sum(
        row["b_crit_units"] < 0 for row in common
    ) or summary["zero_budget_count"] != sum(row["b_crit_units"] == 0 for row in common):
        raise ValueError("paired budget sign counts mismatch")
