"""Independent exact-rational audit of saved paired budgets and cell summaries.

The canonical example rates are decimal rationals. Preserve their exact cost
fractions in addition to the normalized floating display fields. No compiler,
scheduler, generator, or primary analysis imports are used here.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("surgery", "prepare", "readout", "reaction")
RATES = ("surgery", "prepare_zero", "readout", "reaction")
CELL = ("mode", "parallel", "weight", "total_support")
STATES = ("both_ppm_feasible", "tracked_ppm_only", "legacy_ppm_only", "neither_ppm_feasible")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cost(counts: dict[str, int] | None, rates: list[Fraction]) -> Fraction | None:
    if counts is None:
        return None
    if set(counts) != set(FIELDS) or any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError("invalid persisted service coefficients")
    return sum((counts[k] * rate for k, rate in zip(FIELDS, rates, strict=True)), Fraction())


def ratio(value: Fraction | None) -> list[int] | None:
    return [value.numerator, value.denominator] if value is not None else None


def quantiles(values: list[Fraction]) -> dict[str, float] | None:
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    return {
        "min": float(values[0]),
        "p50": float(values[(n - 1) // 2]),
        "p95": float(values[(95 * n + 99) // 100 - 1]),
        "max": float(values[-1]),
    }


def audit(output: Path) -> dict[str, Any]:
    source = output / "summary.json"
    summary = json.loads(source.read_text(encoding="utf-8"))
    if not summary["refinement_complete"] or summary["complete_native_schedule"]:
        raise ValueError("incomplete or unsupported native claim")
    if any(
        summary.get(k) is not None
        for k in (
            "native_runtime_seconds",
            "physical_qubits",
            "failure_probability",
            "legacy_clifford_cost_units",
        )
    ):
        raise ValueError("unsupported native summary")
    for name, expected in summary["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("changed computational source")
    for name, expected in summary["paper_sha256"].items():
        if sha(ROOT / "literature/papers" / name) != expected:
            raise ValueError("changed literature pin")
    cfg = summary["config"]
    rates = [Fraction(str(cfg["timing"][k])) for k in RATES]
    indexes: dict[tuple[Any, ...], dict[str, Any]] = {}
    exact = []
    identities = set()
    for branch in summary["branches"]:
        identity = (branch["variant"], branch["branch"])
        if identity in identities:
            raise ValueError("duplicate persisted branch")
        identities.add(identity)
        if sha(output / branch["artifact"]) != branch["artifact_sha256"]:
            raise ValueError("corrupt persisted signed artifact")
        for row in branch["grid"]:
            key = (*identity, *(row[k] for k in CELL))
            if key in indexes:
                raise ValueError("duplicate persisted cell")
            ts, ls = row["tracked_services"], row["legacy_ppm_services"]
            t, l = cost(ts, rates), cost(ls, rates)
            state = (
                STATES[0]
                if t is not None and l is not None
                else (STATES[1] if t is not None else STATES[2] if l is not None else STATES[3])
            )
            delta = t - l if t is not None and l is not None else None
            if row["status"] != state or row["delta_service_counts"] != (
                {k: ts[k] - ls[k] for k in FIELDS} if ts is not None and ls is not None else None
            ):
                raise ValueError("persisted pairing/state mismatch")
            for field, value in (
                ("tracked_conditional_units", t),
                ("legacy_ppm_conditional_units", l),
                ("b_crit_units", delta),
            ):
                if row[field] != (float(value) if value is not None else None):
                    raise ValueError(f"not the correctly rounded exact decimal cost: {field}")
            if any(
                row[k] is not None
                for k in (
                    "native_runtime_seconds",
                    "legacy_complete_duration",
                    "legacy_clifford_cost_units",
                )
            ):
                raise ValueError("unsupported persisted complete time")
            indexes[key] = {"status": state, "t": t, "l": l, "b": delta}
            exact.append(
                {
                    "variant": identity[0],
                    "branch": identity[1],
                    **{k: row[k] for k in CELL},
                    "status": state,
                    "tracked_units_fraction": ratio(t),
                    "legacy_ppm_units_fraction": ratio(l),
                    "b_crit_units_fraction": ratio(delta),
                }
            )
    checked = 0
    for group in ("initial_grid", "refined_grid", "grid"):
        for row in summary[group]:
            rows = [
                indexes[(row["variant"], b, *(row[k] for k in CELL))]
                for b in range(row["hashed_witness_count"])
            ]
            counts = Counter(r["status"] for r in rows)
            if row["status_counts"] != {s: counts[s] for s in STATES}:
                raise ValueError("wrong saved feasibility counts")
            common = [r for r in rows if r["status"] == STATES[0]]
            for field, k in (
                ("b_crit_units", "b"),
                ("tracked_common_units", "t"),
                ("legacy_ppm_common_units", "l"),
            ):
                if row[field] != quantiles([r[k] for r in common]):
                    raise ValueError("wrong saved exact paired quantiles")
            if row["negative_budget_count"] != sum(r["b"] < 0 for r in common) or row[
                "zero_budget_count"
            ] != sum(r["b"] == 0 for r in common):
                raise ValueError("wrong saved budget signs")
            checked += 1
    selection = {
        (r["variant"], *(r[k] for k in CELL))
        for r in summary["initial_grid"]
        if 0 < r["status_counts"][STATES[0]] < cfg["initial_hashed_branches"]
        or r["b_crit_units"] is not None
        and r["b_crit_units"]["min"] <= 0 < r["b_crit_units"]["max"]
    }
    if selection != {(r["variant"], *(r[k] for k in CELL)) for r in summary["refined_grid"]}:
        raise ValueError("wrong refinement selection")
    for row in summary["grid"]:
        expected = (
            cfg["refinement_hashed_branches"]
            if (row["variant"], *(row[k] for k in CELL)) in selection
            else cfg["initial_hashed_branches"]
        )
        if row["hashed_witness_count"] != expected:
            raise ValueError("wrong refinement sample size")
    return {
        "task_id": summary["task_id"],
        "evidence": "NUMERICAL",
        "input_summary_sha256": sha(source),
        "auditor_sha256": sha(Path(__file__)),
        "rates_as_exact_fractions": [ratio(r) for r in rates],
        "fraction_encoding": "[numerator, denominator]; decimal manifest rates are exact",
        "audited_branch_artifact_count": len(identities),
        "audited_paired_cell_count": len(exact),
        "audited_aggregate_count": checked,
        "native_runtime_seconds": None,
        "rows": exact,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/runs/T-20260926-002")
    args = parser.parse_args()
    data = audit(args.output)
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    target = args.output / "exact-cost-audit.json.gz"
    target.write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))
    print(json.dumps({k: v for k, v in data.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
