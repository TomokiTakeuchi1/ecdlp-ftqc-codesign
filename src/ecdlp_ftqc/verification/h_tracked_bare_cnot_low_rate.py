"""Independent source-plan, signed reverse-history and rational cost checks.

No imports of the hybrid compiler, analysis or experiment driver. This oracle
uses explicit mathematical factors and bit-sliced Pauli conjugation rather than
the compiler's forward tableau updates. Complete-pair source planning is reused
from the approved independent verifier, not the compiler's streaming planner.
"""

from __future__ import annotations

import hashlib
from fractions import Fraction
from typing import Any

from ecdlp_ftqc.verification.parallel_low_rate import _source_plan

FIELDS = ("surgery", "prepare", "readout", "reaction")
RATES = ("surgery", "prepare_zero", "readout", "reaction")


def _images(
    history: list[tuple[str, int, int | None]], n: int, probes: list[tuple[int, str]]
) -> list[dict[str, int]]:
    xs, zs = [0] * n, [0] * n
    signs = 0
    ones = (1 << len(probes)) - 1
    for j, (q, axis) in enumerate(probes):
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
            if b is None or kind not in ("cnot", "cz"):
                raise ValueError("invalid oracle history")
            if kind == "cz":
                h(b)
            signs ^= xs[a] & zs[b] & (xs[b] ^ zs[a] ^ ones)
            xs[b] ^= xs[a]
            zs[a] ^= zs[b]
            if kind == "cz":
                h(b)
    xx, zz = [0] * len(probes), [0] * len(probes)
    for planes, outputs in ((xs, xx), (zs, zz)):
        for q, plane in enumerate(planes):
            while plane:
                bit = plane & -plane
                outputs[bit.bit_length() - 1] |= 1 << q
                plane ^= bit
    return [
        {"x": x, "z": z, "phase": ((x & z).bit_count() + 2 * (signs >> j & 1)) % 4}
        for j, (x, z) in enumerate(zip(xx, zz, strict=True))
    ]


def audit_hybrid_trace(trace: dict[str, Any], source: list[dict[str, Any]], x_policy: str) -> int:
    """Rebuild every signed coupling and final X/Z image from source records."""
    if x_policy not in ("bare", "frame") or trace["variant"] != "ip":
        raise ValueError("hybrid policy mismatch")
    branch = trace["branch"]
    if type(branch) is not int or branch < -2:
        raise ValueError("invalid hybrid branch")
    names = trace["data_names"]
    ids = {name: i for i, name in enumerate(names)}
    if len(ids) != len(names) or set(ids) != {
        q for g in source for q in (*g["controls"], g["target"])
    }:
        raise ValueError("hybrid data identity mismatch")
    plan = _source_plan(
        tuple(
            (g["gate_id"], g["kind"], tuple(g["controls"]), g["target"], g["algorithmic_layer"])
            for g in source
        )
    )
    if tuple(tuple(m["gate_ids"]) for m in trace["macros"]) != plan:
        raise ValueError("hybrid macro plan mismatch")
    gates = {g["gate_id"]: g for g in source}
    applied: set[str] = set()
    history: list[tuple[str, int, int | None]] = []
    resource = len(names)
    count = 0

    def source_before(layer: int, recorded: Any) -> None:
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
            # Bare U: U F U^dagger; virtual source X: F X.
            if op[0] == "cnot" or x_policy == "bare":
                history.insert(0, op)
            history.append(op)
            applied.add(g["gate_id"])
        if list(map(tuple, recorded)) != expected:
            raise ValueError("hybrid source barrier mismatch")

    for index, macro in enumerate(trace["macros"], 1):
        group = [gates[gid] for gid in macro["gate_ids"]]
        if macro["index"] != index or macro["required_previous_macro"] != (
            index - 1 if index > 1 else None
        ):
            raise ValueError("hybrid reaction frontier mismatch")
        if (macro["resource_start"], macro["resource_end"]) != (
            resource,
            resource + 3 * len(group),
        ):
            raise ValueError("hybrid resource identity mismatch")
        source_before(min(g["algorithmic_layer"] for g in group), macro["preceding_cliffords"])
        targets = sorted({ids[g["target"]] for g in group})
        if list(macro["opening_targets"]) != targets:
            raise ValueError("hybrid H targets mismatch")
        history.extend(("h", q, None) for q in targets)
        expected = _images(
            history,
            len(names),
            [(ids[q], "z") for g in group for q in (*g["controls"], g["target"])],
        )
        for j, (p, actual) in enumerate(zip(expected, macro["ppms"], strict=True)):
            p["z"] |= 1 << (resource + j)
            if p != actual or (p["x"] & p["z"]).bit_count() % 2:
                raise ValueError("hybrid signed PPM mismatch")
        count += len(expected)
        resource = macro["resource_end"]
        for g, recorded in zip(group, macro["outcomes"], strict=True):
            if branch < 0:
                bits = [branch + 2] * 6
            else:
                byte = hashlib.shake_256(
                    f"T-20260926-001-full-frame-v1|ip|{g['gate_id']}|{branch}".encode()
                ).digest(1)[0]
                bits = [byte >> j & 1 for j in range(6)]
            if list(recorded) != bits:
                raise ValueError("hybrid branch outcomes mismatch")
            a, b, c, rx, ry, rz = bits
            u, v, t = (ids[q] for q in (*g["controls"], g["target"]))
            for on, op in (
                (a, ("cz", v, t)),
                (b, ("cz", u, t)),
                (c, ("cz", u, v)),
                (rx ^ (b & c), ("z", u, None)),
                (ry ^ (a & c), ("z", v, None)),
                (rz ^ (a & b), ("z", t, None)),
            ):
                if on:
                    history.append(op)
        history.extend(("h", q, None) for q in targets)
    source_before(10**9, trace["trailing_cliffords"])
    images = _images(history, len(names), [(q, a) for a in ("x", "z") for q in range(len(names))])
    if images != [*trace["final_x"], *trace["final_z"]]:
        raise ValueError("hybrid final frame mismatch")
    return count


def audit_cost(row: dict[str, Any], timing: dict[str, Any]) -> None:
    """Check rational units and the strict native/complete-cost boundary."""
    for name in ("native_runtime_seconds", "complete_kernel_units", "physical_qubits"):
        if row.get(name) is not None:
            raise ValueError("unsupported native/complete claim")
    services = row["services"]
    if not row["feasible"]:
        if services is not None or row["units_exact"] is not None or row["units"] is not None:
            raise ValueError("cost on infeasible cell")
        return
    if set(services) != set(FIELDS) or any(type(v) is not int or v < 0 for v in services.values()):
        raise ValueError("invalid service counts")
    value = sum(
        (services[f] * Fraction(str(timing[r])) for f, r in zip(FIELDS, RATES, strict=True)),
        Fraction(),
    )
    if row["units_exact"] != [value.numerator, value.denominator] or row["units"] != float(value):
        raise ValueError("exact service cost mismatch")


def audit_comparison(
    row: dict[str, Any], reference: dict[str, Any], hybrid: dict[str, Any]
) -> None:
    """Do not equate the legacy PPM-only difference with a complete legacy budget."""
    status = (
        "both_feasible"
        if reference["feasible"] and hybrid["feasible"]
        else "reference_only"
        if reference["feasible"]
        else "hybrid_only"
        if hybrid["feasible"]
        else "neither_feasible"
    )
    if row["status"] != status:
        raise ValueError("paired feasibility mismatch")
    if status == "both_feasible":
        delta = Fraction(*reference["units_exact"]) - Fraction(*hybrid["units_exact"])
        coefficients = {f: reference["services"][f] - hybrid["services"][f] for f in FIELDS}
        if (
            row["delta_units_exact"] != [delta.numerator, delta.denominator]
            or row["delta_units"] != float(delta)
            or row["delta_services"] != coefficients
        ):
            raise ValueError("paired delta mismatch")
    elif any(row[k] is not None for k in ("delta_units", "delta_units_exact", "delta_services")):
        raise ValueError("budget outside common feasible set")
    if row["reference_policy"] == "legacy":
        if (
            row["condition"] != "B_hybrid - B_legacy < delta"
            or row["absolute_hybrid_budget"] is not None
        ):
            raise ValueError("legacy service incorrectly priced at zero")
    elif (
        row["condition"] != "B_hybrid < delta"
        or row["absolute_hybrid_budget"] != row["delta_units"]
    ):
        raise ValueError("full-tracking budget mismatch")


def audit_summary(summary: dict[str, Any]) -> None:
    """Independent saved-row coverage, rational costs and nearest-rank audit."""
    config = summary["config"]
    if (
        any(
            summary.get(k) is not None
            for k in (
                "native_runtime_seconds",
                "physical_qubits",
                "failure_probability",
                "native_automorphism_calls",
            )
        )
        or summary.get("complete_native_schedule") is not False
    ):
        raise ValueError("unsupported native summary")
    capacities = [(k, None) for k in config["parallel_limits"]] + [
        (64, s) for s in config["total_support_limits_at_k64"]
    ]
    expected = {
        (p, m, k, w, s)
        for p in ("hybrid_bare", "hybrid_frame", "full", "legacy")
        for m in (["qwc"] if p == "legacy" else config["modes"])
        for k, s in capacities
        for w in config["weight_limits"]
    }
    compare_expected = {
        (h, m, r, m if r == "full" else "qwc", k, w, s)
        for h in ("hybrid_bare", "hybrid_frame")
        for m in config["modes"]
        for r in ("full", "legacy")
        for k, s in capacities
        for w in config["weight_limits"]
    }
    keys = ("policy", "mode", "parallel", "weight", "total_support")
    ck = (
        "hybrid_policy",
        "mode",
        "reference_policy",
        "reference_mode",
        "parallel",
        "weight",
        "total_support",
    )
    branches = summary["branches"]
    if sorted(b["branch"] for b in branches) != sorted(
        [*config["forced_branches"], *range(config["hashed_branches"])]
    ):
        raise ValueError("missing/duplicate branch")
    grids, pairs = [], []
    for branch in branches:
        grid = {tuple(r[k] for k in keys): r for r in branch["grid"]}
        comparisons = {tuple(r[k] for k in ck): r for r in branch["comparisons"]}
        if len(grid) != len(branch["grid"]) or set(grid) != expected:
            raise ValueError("grid coverage mismatch")
        if len(comparisons) != len(branch["comparisons"]) or set(comparisons) != compare_expected:
            raise ValueError("comparison coverage mismatch")
        for row in grid.values():
            audit_cost(row, config["timing"])
        for key, row in comparisons.items():
            hp, mode, ref, rm, k, w, s = key
            audit_comparison(row, grid[ref, rm, k, w, s], grid[hp, mode, k, w, s])
            allowed = (
                float(Fraction(*row["delta_units_exact"]) / 4)
                if (
                    ref == "full"
                    and config["width"] == 256
                    and row["delta_units_exact"] is not None
                )
                else None
            )
            if row["equal_auto_call_allowance_if_four_calls_and_tx_zero"] != allowed:
                raise ValueError("automorphism sensitivity mismatch")
        if config["width"] == 256 and [r["count"] for r in branch["cnot_layers"]] != [
            256,
            255,
            254,
            254,
        ]:
            raise ValueError("CNOT obligation mismatch")
        if any(
            r["native_call_count"] is not None or r["call_duration"] is not None
            for r in branch["cnot_layers"]
        ):
            raise ValueError("native automorphism not admitted")
        if branch["branch"] >= 0:
            grids.append(grid)
            pairs.append(comparisons)

    def quantiles(values: list[float | int]) -> dict[str, float | int] | None:
        if not values:
            return None
        values = sorted(values)
        n = len(values)
        return {
            "min": values[0],
            "p50": values[(n + 1) // 2 - 1],
            "p95": values[(95 * n + 99) // 100 - 1],
            "max": values[-1],
        }

    aggregates = {tuple(r[k] for k in keys): r for r in summary["grid"]}
    pair_aggregates = {tuple(r[k] for k in ck): r for r in summary["comparisons"]}
    if (
        set(aggregates) != expected
        or len(aggregates) != len(summary["grid"])
        or set(pair_aggregates) != compare_expected
        or len(pair_aggregates) != len(summary["comparisons"])
    ):
        raise ValueError("aggregate coverage mismatch")
    for key, row in aggregates.items():
        feasible = [g[key] for g in grids if g[key]["feasible"]]
        if (
            row["hashed_witness_count"] != config["hashed_branches"]
            or row["feasible_count"] != len(feasible)
            or row["units"] != quantiles([r["units"] for r in feasible])
            or row["surgery_steps"] != quantiles([r["services"]["surgery"] for r in feasible])
        ):
            raise ValueError("grid quantile mismatch")
    for key, row in pair_aggregates.items():
        entries = [g[key] for g in pairs]
        common = [r for r in entries if r["status"] == "both_feasible"]
        counts = {
            s: sum(r["status"] == s for r in entries)
            for s in ("both_feasible", "reference_only", "hybrid_only", "neither_feasible")
        }
        if (
            row["hashed_witness_count"] != config["hashed_branches"]
            or row["status_counts"] != counts
            or row["delta_units"] != quantiles([r["delta_units"] for r in common])
            or row["negative_delta_count"] != sum(r["delta_units"] < 0 for r in common)
            or row["zero_delta_count"] != sum(r["delta_units"] == 0 for r in common)
            or row["condition"] != entries[0]["condition"]
        ):
            raise ValueError("paired quantile mismatch")
