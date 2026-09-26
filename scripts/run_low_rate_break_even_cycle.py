"""Paired low-rate policy experiment; deterministic, resumable, independently audited."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from importlib.metadata import version
from itertools import product
from pathlib import Path
from typing import Any, Literal, cast

from ecdlp_ftqc.analysis.low_rate_break_even import Services, paired_budget, summarize_pairs
from ecdlp_ftqc.circuits.qcla import build_qcla_trace
from ecdlp_ftqc.circuits.qcla_oop import build_oop_qcla_trace
from ecdlp_ftqc.compiler.low_rate_policy_trace import build_legacy_trace
from ecdlp_ftqc.compiler.parallel_low_rate_trace import SEED, build_tracked_trace
from ecdlp_ftqc.scheduler.parallel_low_rate import Limits, Timing, lower, schedule_macro
from ecdlp_ftqc.verification.low_rate_break_even import (
    audit_aggregate,
    audit_legacy_trace,
    audit_pair,
    audit_pair_alignment,
)
from ecdlp_ftqc.verification.parallel_low_rate import (
    audit_lowering,
    audit_packing,
    audit_service,
    audit_trace,
)

ROOT = Path(__file__).resolve().parents[1]
TASK = "T-20260926-002"
MANIFEST = ROOT / "experiments/manifests/E-20260926-002.json"
KEYS = ("mode", "parallel", "weight", "total_support")
Variant = Literal["oop", "ip"]
PAPERS = {
    "2408.01339v3.pdf": "f11c40ff1e4c7a5a9d5b81dbbbd24a6ed6811fbc401c3a0fa165ef7623c69b4a",
    "2503.05003v3.pdf": "8ffeb13f3299a1037c709eb1d63e8b032e962514397fa94c5fd6178ba5630eb2",
}


def compact(value: Any) -> Any:
    if type(value) is int and value >= 2**53:
        return hex(value)
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [compact(v) for v in value]
    return value


def payload(data: Any, compressed: bool = False) -> bytes:
    raw = (
        json.dumps(
            compact(data),
            sort_keys=True,
            separators=(",", ":") if compressed else None,
            indent=None if compressed else 2,
        )
        + "\n"
    ).encode()
    return gzip.compress(raw, compresslevel=6, mtime=0) if compressed else raw


def write_json(path: Path, data: Any, compressed: bool = False) -> None:
    path.write_bytes(payload(data, compressed))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    names = [
        "scripts/run_low_rate_break_even_cycle.py",
        "experiments/manifests/E-20260926-002.json",
        "src/ecdlp_ftqc/analysis/low_rate_break_even.py",
        "src/ecdlp_ftqc/compiler/low_rate_policy_trace.py",
        "src/ecdlp_ftqc/compiler/parallel_low_rate_trace.py",
        "src/ecdlp_ftqc/verification/low_rate_break_even.py",
        "src/ecdlp_ftqc/verification/parallel_low_rate.py",
        "src/ecdlp_ftqc/scheduler/parallel_low_rate.py",
        "src/ecdlp_ftqc/circuits/qcla.py",
        "src/ecdlp_ftqc/circuits/qcla_oop.py",
        "src/ecdlp_ftqc/scheduler/width256_commutation_aware_qcla.py",
        "src/ecdlp_ftqc/scheduler/width256_ip_commutation_aware_qcla.py",
    ]
    return {name: digest(ROOT / name) for name in names}


def cells(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(zip(KEYS, values, strict=True))
        for values in product(
            config["tracked_modes"],
            config["parallel_limits"],
            config["weight_limits"],
            config["total_support_limits"],
        )
    ]


def key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row[k] for k in KEYS)


def binding(config: dict[str, Any], selected: list[dict[str, Any]], hashes: dict[str, str]) -> str:
    return hashlib.sha256(
        payload({"config": config, "cells": selected, "sources": hashes})
    ).hexdigest()


def profile(
    variant: Variant,
    branch: int,
    config: dict[str, Any],
    selected: list[dict[str, Any]],
    output: Path,
) -> dict[str, Any]:
    width = config["width"]
    if variant == "oop":
        source_oop = build_oop_qcla_trace(width)
        gates = [asdict(g) for g in source_oop.gates]
        resident = source_oop.expected_fully_resident_source_values
    else:
        source_ip = build_qcla_trace(width)
        gates = [asdict(g) for g in source_ip.gates]
        resident = 2 * width + source_ip.source_ancilla_count
    tracked, legacy = (
        build_tracked_trace(variant, width, branch),
        build_legacy_trace(variant, width, branch),
    )
    td, ld = asdict(tracked), asdict(legacy)
    audit_pair_alignment(td, ld)
    audits = {"tracked": audit_trace(td, gates), "legacy": audit_legacy_trace(ld, gates)}
    timing = Timing(**config["timing"])
    statistics: dict[str, Any] = {}
    details: dict[str, Any] = {}
    available: dict[tuple[str, str, Any, Any], Services | None] = {}
    policies = [("legacy", "qwc", legacy)] + [
        ("tracked", mode, tracked)
        for mode in config["tracked_modes"]
        if any(c["mode"] == mode for c in selected)
    ]
    for policy, mode, trace in policies:
        lowered = [lower(m.ppms, mode) for m in trace.macros]
        lod = [asdict(lo) for lo in lowered]
        for macro, serialized in zip(trace.macros, lod, strict=True):
            audit_lowering([asdict(p) for p in macro.ppms], serialized)
        maximum = max(p.weight for lo in lowered for stage in lo.stages for p in stage.ppms)
        stats_key = f"{policy}_{mode}"
        statistics[stats_key] = {
            "executed_max_weight": maximum,
            "peak_extra_logical_ancillas": max(lo.logical_ancillas for lo in lowered),
            "peak_y_catalysts": max(lo.y_catalysts for lo in lowered),
            "retained_frame_sha256": hashlib.sha256(
                payload(
                    {
                        "x": trace.final_x and [asdict(p) for p in trace.final_x],
                        "z": trace.final_z and [asdict(p) for p in trace.final_z],
                    }
                )
            ).hexdigest(),
        }
        capacities = list(
            dict.fromkeys(
                (c["parallel"], c["total_support"])
                for c in selected
                if policy == "legacy" or c["mode"] == mode
            )
        )
        examples = []
        for parallel, support in capacities:
            limits = Limits(parallel, None, support)
            totals = [0, 0, 0, 0]
            fits = True
            timeline = []
            now = 0.0
            for macro, lo, lo_dict in zip(trace.macros, lowered, lod, strict=True):
                schedule = schedule_macro(lo, limits, timing, len(macro.ppms))
                sd = asdict(schedule)
                audit_packing(lo_dict, sd, asdict(limits))
                audit_service(lo_dict, sd, config["timing"], len(macro.ppms))
                fits &= schedule.feasible
                for j, value in enumerate(
                    (
                        schedule.surgery_steps or 0,
                        schedule.prepare_steps,
                        schedule.readout_steps,
                        schedule.reaction_steps,
                    )
                ):
                    totals[j] += value
                if parallel == 64 and support is None:
                    duration = schedule.duration or 0
                    timeline.append(
                        {
                            "macro": macro.index,
                            "ppm_time_start": round(now, 12),
                            "ppm_time_end": round(now + duration, 12),
                            "ccz_demand": len(macro.gate_ids),
                            "logical_wire_envelope": resident
                            + len(macro.ppms)
                            + lo.logical_ancillas,
                            "schedule": sd,
                        }
                    )
                    now += duration
            available[(policy, mode, parallel, support)] = Services(*totals) if fits else None
            if timeline:
                examples.append(
                    {"parallel": parallel, "total_support": support, "macros": timeline}
                )
        details[stats_key] = {"lowerings": lod, "representative_schedules": examples}
    rows = []
    for cell in selected:
        mode, parallel, weight, support = (cell[k] for k in KEYS)
        tt = available[("tracked", mode, parallel, support)]
        ll = available[("legacy", "qwc", parallel, support)]
        if weight is not None:
            if statistics[f"tracked_{mode}"]["executed_max_weight"] > weight:
                tt = None
            if statistics["legacy_qwc"]["executed_max_weight"] > weight:
                ll = None
        row = {**cell, **paired_budget(tt, ll, timing)}
        audit_pair(row, config["timing"])
        rows.append(row)
    obligations = {
        "conjugated_h_target_applications": 2 * sum(len(m.opening_targets) for m in legacy.macros),
        "candidate_conjugated_h_layers": 2 * len(legacy.macros),
        "bare_source_cnot_count": sum(g["kind"] == "cnot" for g in gates),
        "bare_source_x_count": sum(g["kind"] == "x" for g in gates),
        "native_clifford_feasibility": None,
        "legacy_clifford_cost_units": None,
    }
    artifact = output / f"{variant}-branch-{branch}.json.gz"
    write_json(
        artifact,
        {
            "tracked_trace": td,
            "legacy_trace": ld,
            "lowerings": details,
            "timeline_scope": "PPM-only time; legacy Clifford intervals excluded",
        },
        True,
    )
    return {
        "variant": variant,
        "branch": branch,
        "macro_count": len(legacy.macros),
        "source_resident_values": resident,
        "active_frame_values": len(legacy.data_names),
        "audited_coupling_ppms": audits,
        "statistics": statistics,
        "legacy_obligations": obligations,
        "grid": rows,
        "artifact": artifact.name,
        "artifact_sha256": digest(artifact),
    }


def cached_job(
    job: tuple[Variant, int, dict[str, Any], list[dict[str, Any]], str, dict[str, str]],
) -> dict[str, Any]:
    variant, branch, config, selected, directory, hashes = job
    output = Path(directory)
    checkpoint = output / f"{variant}-branch-{branch}.result.json"
    expected_binding = binding(config, selected, hashes)
    if checkpoint.exists():
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        if saved["binding"] != expected_binding:
            raise ValueError(f"stale checkpoint; choose a new output directory: {checkpoint}")
        result = saved["result"]
        if (result["variant"], result["branch"]) != (variant, branch):
            raise ValueError("checkpoint identity mismatch")
        if digest(output / result["artifact"]) != result["artifact_sha256"]:
            raise ValueError("checkpoint artifact hash mismatch")
        for row in result["grid"]:
            audit_pair(row, config["timing"])
        return cast(dict[str, Any], result)
    result = profile(variant, branch, config, selected, output)
    write_json(checkpoint, {"binding": expected_binding, "result": result})
    return result


def aggregate(
    branches: list[dict[str, Any]], variant: str, selected: list[dict[str, Any]], count: int
) -> list[dict[str, Any]]:
    subset = [b for b in branches if b["variant"] == variant and 0 <= b["branch"] < count]
    if sorted(b["branch"] for b in subset) != list(range(count)):
        raise ValueError("missing or duplicated paired branch")
    indexes = [{key(r): r for r in b["grid"]} for b in subset]
    rows = []
    for cell in selected:
        paired = [index[key(cell)] for index in indexes]
        summary = summarize_pairs(paired)
        audit_aggregate(paired, summary)
        rows.append({"variant": variant, **cell, **summary})
    return rows


def needs_refinement(row: dict[str, Any]) -> bool:
    count = row["status_counts"]["both_ppm_feasible"]
    budgets = row["b_crit_units"]
    return bool(
        0 < count < row["hashed_witness_count"]
        or budgets is not None
        and budgets["min"] <= 0 < budgets["max"]
    )


def heatmap(path: Path, rows: list[dict[str, Any]], width: int) -> None:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1190" height="980" viewBox="0 0 1190 980">',
        '<rect width="1190" height="980" fill="#f5f7fb"/>',
        '<g font-family="Segoe UI,sans-serif" fill="#17263c">',
        f'<text x="24" y="35" font-size="24">Paired Clifford budget | QCLA n={width}</text>',
        '<text x="24" y="60" font-size="14">Cell: median Bcrit in conditional units; both-PPM-feasible / hashed witnesses.</text>',
        '<text x="24" y="82" font-size="14">Legacy wins only if its additional Clifford service B is feasible and B &lt; Bcrit.</text>',
    ]
    for panel, (variant, mode) in enumerate(product(("oop", "ip"), ("qwc", "general"))):
        ox, oy = 24 + 590 * (panel % 2), 125 + 410 * (panel // 2)
        parts.append(
            f'<text x="{ox}" y="{oy}" font-size="20">{variant.upper()} / tracked {mode}</text>'
        )
        parts.append(
            f'<text x="{ox}" y="{oy + 24}" font-size="12">Rows: individual weight; groups: summed support S; columns: K</text>'
        )
        for si, support in enumerate((512, 2048, None)):
            y0 = oy + 55 + 101 * si
            parts.append(f'<text x="{ox}" y="{y0}" font-size="13">S={support or "inf"}</text>')
            for j, parallel in enumerate((64, 256, None)):
                parts.append(
                    f'<text x="{ox + 123 + 139 * j}" y="{y0}" font-size="12">K={parallel or "inf"}</text>'
                )
            for i, weight in enumerate((256, 512, None)):
                y = y0 + 7 + 27 * i
                parts.append(
                    f'<text x="{ox}" y="{y + 18}" font-size="12">w={weight or "inf"}</text>'
                )
                for j, parallel in enumerate((64, 256, None)):
                    row = next(
                        r
                        for r in rows
                        if r["variant"] == variant
                        and r["mode"] == mode
                        and (r["parallel"], r["weight"], r["total_support"])
                        == (parallel, weight, support)
                    )
                    budget = row["b_crit_units"]
                    median = budget["p50"] if budget else None
                    color = "#dae0e8" if median is None else "#f5d2c8" if median < 0 else "#bfe3dc"
                    count, total = (
                        row["status_counts"]["both_ppm_feasible"],
                        row["hashed_witness_count"],
                    )
                    label = "--" if median is None else f"{median:g}"
                    x = ox + 88 + 139 * j
                    parts.append(
                        f'<rect x="{x}" y="{y}" width="134" height="24" rx="3" fill="{color}"/>'
                    )
                    parts.append(
                        f'<text x="{x + 6}" y="{y + 17}" font-size="12">{label} | {count}/{total}</text>'
                    )
    parts.extend(
        [
            '<text x="24" y="944" font-size="13">Retained final frames, serial service model; no native runtime, factory, routing or failure estimate.</text>',
            '<text x="24" y="966" font-size="12">Forced zero/one excluded. Boundary-selected cells have 512 witnesses; others 64. This is not a worst-case bound.</text>',
            "</g></svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def run_jobs(jobs: list[Any], workers: int) -> list[dict[str, Any]]:
    if not jobs:
        return []
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(cached_job, jobs):
            results.append(result)
            print(
                f"{result['variant']} branch {result['branch']}: paired signed/lowering/packing audits PASS",
                flush=True,
            )
    return results


def verify_samples(output: Path, count: int) -> None:
    if count < 1:
        raise ValueError("positive sample count required")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if summary["source_sha256"] != source_hashes():
        raise ValueError("source binding changed")
    repeat = output / "reproduction"
    repeat.mkdir(exist_ok=True)
    checked = []
    for expected in summary["branches"]:
        branch = expected["branch"]
        if not (branch < count or branch == summary["config"]["refinement_hashed_branches"] - 1):
            continue
        selected = [{k: r[k] for k in KEYS} for r in expected["grid"]]
        actual = profile(expected["variant"], branch, summary["config"], selected, repeat)
        if (
            actual != expected
            or (output / expected["artifact"]).read_bytes()
            != (repeat / actual["artifact"]).read_bytes()
        ):
            raise ValueError("non-reproducible branch artifact")
        checked.append([expected["variant"], branch])
        print(f"Byte-identical independent regeneration: {checked[-1]}", flush=True)
    write_json(repeat / "validation.json", {"checked": checked, "byte_identical": True})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--width", type=int)
    parser.add_argument("--branches", type=int)
    parser.add_argument("--skip-refinement", action="store_true")
    parser.add_argument("--verify-samples", type=int)
    args = parser.parse_args()
    output = args.output or ROOT / "experiments/runs" / TASK
    if args.verify_samples is not None:
        verify_samples(output, args.verify_samples)
        return
    config = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (
        config["branch_seed"] != SEED
        or config["native_runtime_seconds"] is not None
        or config["timing"]["seconds_per_unit"] is not None
    ):
        raise ValueError("manifest contradicts seed/native boundary")
    if args.width is not None:
        config["width"] = args.width
    if args.branches is not None:
        config["initial_hashed_branches"] = args.branches
    if (
        config["width"] < 2
        or not 1 <= config["initial_hashed_branches"] <= config["refinement_hashed_branches"]
        or not 1 <= args.workers <= 8
    ):
        raise ValueError("invalid experiment dimensions/workers")
    if (args.width is not None or args.branches is not None) and args.output is None:
        raise ValueError("noncanonical dimensions require explicit output")
    for name, expected in PAPERS.items():
        path = ROOT / "literature/papers" / name
        if (
            not path.exists()
            or digest(path) != expected
            or not path.read_bytes().startswith(b"%PDF-")
        ):
            raise ValueError(f"missing/mismatched literature pin: {name}")
    output.mkdir(parents=True, exist_ok=True)
    hashes = source_hashes()
    selected = cells(config)
    count = config["initial_hashed_branches"]
    jobs = [
        (v, b, config, selected, str(output), hashes)
        for v in ("oop", "ip")
        for b in [*config["forced_branches"], *range(count)]
    ]
    branches = run_jobs(jobs, args.workers)
    initial = [r for v in ("oop", "ip") for r in aggregate(branches, v, selected, count)]
    write_json(
        output / "initial-grid.json", {"grid": initial, "source_sha256": hashes, "config": config}
    )
    refinement = [r for r in initial if needs_refinement(r)]
    write_json(
        output / "refinement-selection.json",
        {
            "selected": refinement,
            "rule": config["refinement_rule"],
            "source_sha256": hashes,
        },
    )
    jobs = []
    if not args.skip_refinement:
        for v in ("oop", "ip"):
            subset = [{k: r[k] for k in KEYS} for r in refinement if r["variant"] == v]
            if subset:
                jobs.extend(
                    (v, b, config, subset, str(output), hashes)
                    for b in range(count, config["refinement_hashed_branches"])
                )
    branches.extend(run_jobs(jobs, args.workers))
    refined = []
    if not args.skip_refinement:
        for v in ("oop", "ip"):
            subset = [{k: r[k] for k in KEYS} for r in refinement if r["variant"] == v]
            if subset:
                refined.extend(aggregate(branches, v, subset, config["refinement_hashed_branches"]))
    replacements = {(r["variant"], key(r)): r for r in refined}
    final_grid = [replacements.get((r["variant"], key(r)), r) for r in initial]
    if hashes != source_hashes():
        raise ValueError("source changed during experiment")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    summary = {
        "task_id": TASK,
        "config": config,
        "source_sha256": hashes,
        "paper_sha256": PAPERS,
        "git_head": head,
        "worktree": "task working tree; exact computational hashes recorded",
        "environment": {
            "python": platform.python_version(),
            **{p: version(p) for p in ("numpy", "pytest")},
        },
        "evidence": "NUMERICAL",
        "timing_evidence": "CHECK",
        "validation": "paired signed histories, lowerings, packing, services, budgets and summaries audited",
        "refinement_complete": not args.skip_refinement or not refinement,
        "native_runtime_seconds": None,
        "physical_qubits": None,
        "failure_probability": None,
        "legacy_clifford_cost_units": None,
        "complete_native_schedule": False,
        "initial_grid": initial,
        "refined_grid": refined,
        "grid": final_grid,
        "branches": branches,
    }
    write_json(output / "summary.json", summary)
    heatmap(output / "clifford-budget-map.svg", final_grid, config["width"])
    print(f"Wrote {output}; refinement complete={summary['refinement_complete']}", flush=True)


if __name__ == "__main__":
    main()
