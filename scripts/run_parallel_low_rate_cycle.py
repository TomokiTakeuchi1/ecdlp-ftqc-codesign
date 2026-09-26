"""Reproduce the parameterized low-rate QCLA study (no native timing claims)."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from ecdlp_ftqc.circuits.qcla import build_qcla_trace
from ecdlp_ftqc.circuits.qcla_oop import build_oop_qcla_trace
from ecdlp_ftqc.compiler.parallel_low_rate_trace import SEED, build_tracked_trace
from ecdlp_ftqc.scheduler.parallel_low_rate import Limits, Timing, lower, schedule_macro
from ecdlp_ftqc.verification.parallel_low_rate import (
    audit_lowering,
    audit_packing,
    audit_service,
    audit_trace,
)

ROOT = Path(__file__).resolve().parents[1]
TASK = "T-20260926-001"
MANIFEST = ROOT / "experiments/manifests/E-20260926-001.json"


def write_json(path: Path, data: Any, compressed: bool = False) -> None:
    def compact(value: Any) -> Any:
        # Decimal powers of two look random to gzip. Hex preserves sparse bitmaps.
        if type(value) is int and value >= 2**53:
            return hex(value)
        if isinstance(value, dict):
            return {k: compact(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [compact(v) for v in value]
        return value

    payload = (
        json.dumps(
            compact(data),
            sort_keys=True,
            separators=(",", ":") if compressed else None,
            indent=None if compressed else 2,
        )
        + "\n"
    ).encode()
    path.write_bytes(gzip.compress(payload, compresslevel=6, mtime=0) if compressed else payload)


def distribution(values: list[float | int]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "p50": ordered[math.ceil(len(ordered) * 0.5) - 1],
        "p95": ordered[math.ceil(len(ordered) * 0.95) - 1],
        "max": ordered[-1],
    }


def profile(
    variant: Literal["oop", "ip"],
    branch: int,
    config: dict[str, Any],
    output: Path,
    *,
    store_detail: bool = True,
) -> dict[str, Any]:
    width = config["width"]
    if variant == "oop":
        source_oop = build_oop_qcla_trace(width)
        resident = source_oop.expected_fully_resident_source_values
        source_gates = [asdict(g) for g in source_oop.gates]
    else:
        source_ip = build_qcla_trace(width)
        resident = 2 * width + source_ip.source_ancilla_count
        source_gates = [asdict(g) for g in source_ip.gates]
    trace = build_tracked_trace(variant, width, branch)
    trace_data = asdict(trace)
    audited = audit_trace(trace_data, source_gates)
    timing = Timing(**config["timing"])
    branch_result: dict[str, Any] = {
        "variant": variant,
        "branch": branch,
        "macro_count": len(trace.macros),
        "audited_ppms": audited,
        "original_max_weight": max(p.weight for m in trace.macros for p in m.ppms),
        "modes": {},
    }
    detailed_modes = {}
    for mode in ("qwc", "general"):
        lowered = [lower(m.ppms, mode) for m in trace.macros]
        lowered_data = [asdict(item) for item in lowered]
        for macro, lowered_macro in zip(trace.macros, lowered_data, strict=True):
            audit_lowering([asdict(p) for p in macro.ppms], lowered_macro)
        max_weight = max(p.weight for item in lowered for s in item.stages for p in s.ppms)
        peak_ancilla = max(item.logical_ancillas for item in lowered)
        capacities = [(k, None) for k in config["parallel_limits"]]
        capacities += [(64, s) for s in config["total_support_limits_at_k64"]]
        grid = []
        examples = {}
        for parallel, support in capacities:
            limits = Limits(parallel, None, support)
            schedules = [
                schedule_macro(item, limits, timing, len(m.ppms))
                for m, item in zip(trace.macros, lowered, strict=True)
            ]
            for macro, lowered_dict, sched in zip(
                trace.macros, lowered_data, schedules, strict=True
            ):
                audit_packing(lowered_dict, asdict(sched), asdict(limits))
                audit_service(lowered_dict, asdict(sched), asdict(timing), len(macro.ppms))
            fits_sum = all(s.feasible for s in schedules)
            steps = sum(s.surgery_steps or 0 for s in schedules) if fits_sum else None
            duration = sum(s.duration or 0 for s in schedules) if fits_sum else None
            for weight in config["weight_limits"]:
                feasible = fits_sum and (weight is None or max_weight <= weight)
                grid.append(
                    {
                        "parallel": parallel,
                        "weight": weight,
                        "total_support": support,
                        "feasible": feasible,
                        "reason": None if feasible else "infeasible_for_this_lowering",
                        "surgery_steps": steps if feasible else None,
                        "conditional_time_units": duration if feasible else None,
                        "conditional_seconds": (
                            duration * timing.seconds_per_unit
                            if feasible
                            and duration is not None
                            and timing.seconds_per_unit is not None
                            else None
                        ),
                    }
                )
            if fits_sum and support is None and parallel in (64, None):
                now = 0.0
                timeline = []
                for m, lo, sched in zip(trace.macros, lowered, schedules, strict=True):
                    assert sched.duration is not None
                    timeline.append(
                        {
                            "macro": m.index,
                            "start": now,
                            "end": now + sched.duration,
                            "ccz_demand": len(m.gate_ids),
                            "ccz_held_until": now + sched.duration,
                            "logical_wire_envelope": resident + len(m.ppms) + lo.logical_ancillas,
                            "schedule": asdict(sched),
                        }
                    )
                    now += sched.duration
                examples[str(parallel)] = timeline
        macro_rows = []
        for m, lo in zip(trace.macros, lowered, strict=True):
            xs = zs = 0
            contacts: Counter[int] = Counter()
            for p in m.ppms:
                xs |= p.x
                zs |= p.z
                mask = p.x | p.z
                while mask:
                    bit = mask & -mask
                    contacts[bit.bit_length() - 1] += 1
                    mask ^= bit
            macro_rows.append(
                {
                    "macro": m.index,
                    "source_ppms": len(m.ppms),
                    "source_weight_max": max(p.weight for p in m.ppms),
                    "source_weight_sum": sum(p.weight for p in m.ppms),
                    "source_support_union": (xs | zs).bit_count(),
                    "source_max_contact": max(contacts.values()),
                    "source_mixed_count": sum(bool(p.x and p.z) for p in m.ppms),
                    "source_y_count": sum(bool(p.x & p.z) for p in m.ppms),
                    "executed_weight_max": max(p.weight for s in lo.stages for p in s.ppms),
                    "logical_ancillas": lo.logical_ancillas,
                    "y_catalysts": lo.y_catalysts,
                    "main_stages": sum(s.kind != "prepare_y" for s in lo.stages),
                }
            )
        branch_result["modes"][mode] = {
            "executed_max_weight": max_weight,
            "peak_logical_ancillas": peak_ancilla,
            "grid": grid,
            "macros": macro_rows,
        }
        if store_detail:
            detailed_modes[mode] = {"lowerings": lowered_data, "schedules": examples}
    if store_detail:
        write_json(
            output / f"{variant}-branch-{branch}.json.gz",
            {"trace": trace_data, "modes": detailed_modes},
            compressed=True,
        )
    return branch_result


def aggregate(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in ("oop", "ip"):
        subset = [b for b in branches if b["variant"] == variant and b["branch"] >= 0]
        for mode in ("qwc", "general"):
            for index, prototype in enumerate(subset[0]["modes"][mode]["grid"]):
                entries = [b["modes"][mode]["grid"][index] for b in subset]
                feasible = [e for e in entries if e["feasible"]]
                rows.append(
                    {
                        "variant": variant,
                        "mode": mode,
                        **{key: prototype[key] for key in ("parallel", "weight", "total_support")},
                        "hashed_witness_count": len(entries),
                        "feasible_count": len(feasible),
                        "surgery_steps": distribution([e["surgery_steps"] for e in feasible])
                        if feasible
                        else None,
                        "conditional_time_units": distribution(
                            [e["conditional_time_units"] for e in feasible]
                        )
                        if feasible
                        else None,
                    }
                )
    return rows


def heatmap(path: Path, rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    """Static scientific SVG: feasible witnesses and conditional median steps."""
    parts = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1140" height="980" '
            'viewBox="0 0 1140 980">'
        ),
        '<rect width="1140" height="980" fill="#f5f7fb"/>',
        '<g font-family="Segoe UI, sans-serif" fill="#16233b">',
        '<text x="30" y="32" font-size="23">Parallel low-rate surgery | QCLA n=256</text>',
        (
            '<text x="30" y="57" font-size="13">Cell: median surgery steps / feasible hashed witnesses. '
            "Conditional logical macros, not native runtime.</text>"
        ),
    ]
    for panel, (variant, mode) in enumerate(product_pairs()):
        ox, oy = 30 + (panel % 2) * 555, 90 + (panel // 2) * 435
        parts.append(f'<text x="{ox}" y="{oy}" font-size="20">{variant.upper()} / {mode}</text>')
        parts.append(
            f'<text x="{ox}" y="{oy + 23}" font-size="12">Columns: K; rows: maximum executed logical weight</text>'
        )
        for j, k in enumerate(config["parallel_limits"]):
            parts.append(
                f'<text x="{ox + 78 + 75 * j}" y="{oy + 48}" font-size="13">{k if k else "inf"}</text>'
            )
        for i, w in enumerate(config["weight_limits"]):
            y = oy + 60 + i * 45
            parts.append(f'<text x="{ox}" y="{y + 25}" font-size="13">{w if w else "inf"}</text>')
            for j, k in enumerate(config["parallel_limits"]):
                row = next(
                    r
                    for r in rows
                    if r["variant"] == variant
                    and r["mode"] == mode
                    and r["parallel"] == k
                    and r["weight"] == w
                    and r["total_support"] is None
                )
                count, total = row["feasible_count"], row["hashed_witness_count"]
                color = "#d8ece4" if count == total else "#fff0d1" if count else "#e4e7ee"
                label = f"{row['surgery_steps']['p50']} / {count}" if count else f"-- / {count}"
                parts.append(
                    f'<rect x="{ox + 58 + 75 * j}" y="{y}" width="72" height="41" rx="4" fill="{color}"/>'
                )
                parts.append(
                    f'<text x="{ox + 64 + 75 * j}" y="{y + 25}" font-size="12">{label}</text>'
                )
    parts.extend(
        [
            (
                '<text x="30" y="958" font-size="12">Forced zero/one branches excluded from these summaries; '
                "no sampled maximum is a worst-case guarantee. See summary.json.</text>"
            ),
            "</g></svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def product_pairs() -> tuple[tuple[str, str], ...]:
    return (("oop", "qwc"), ("oop", "general"), ("ip", "qwc"), ("ip", "general"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branches", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-samples", type=int)
    args = parser.parse_args()
    if args.verify_samples is not None:
        verify_samples(args.output or ROOT / "experiments/runs" / TASK, args.verify_samples)
        return
    config = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if config["seed"] != SEED or config["complete_native_schedule"]:
        raise ValueError("manifest contradicts evidence/seed contract")
    if args.branches is not None:
        if args.branches < 1:
            raise ValueError("positive branch count required")
        config["hashed_branch_count"] = args.branches
    output = args.output or ROOT / "experiments/runs" / TASK
    output.mkdir(parents=True, exist_ok=True)
    branches = []
    for variant in ("oop", "ip"):
        for branch in [*config["boundary_branches"], *range(config["hashed_branch_count"])]:
            result = profile(variant, branch, config, output)
            branches.append(result)
            print(
                f"{variant} branch {branch}: signed replay PASS; max weight "
                f"{result['original_max_weight']}",
                flush=True,
            )
    rows = aggregate(branches)
    source_paths = [
        Path(__file__).resolve(),
        MANIFEST,
        ROOT / "src/ecdlp_ftqc/compiler/parallel_low_rate_trace.py",
        ROOT / "src/ecdlp_ftqc/scheduler/parallel_low_rate.py",
        ROOT / "src/ecdlp_ftqc/verification/parallel_low_rate.py",
        ROOT / "src/ecdlp_ftqc/circuits/qcla.py",
        ROOT / "src/ecdlp_ftqc/circuits/qcla_oop.py",
        ROOT / "src/ecdlp_ftqc/scheduler/width256_commutation_aware_qcla.py",
        ROOT / "src/ecdlp_ftqc/scheduler/width256_ip_commutation_aware_qcla.py",
    ]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    summary = {
        "task_id": TASK,
        "config": config,
        "git_head": head,
        "worktree": "dirty; preexisting changes preserved; exact dependency hashes below",
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_paths
        },
        "python": platform.python_version(),
        "validation": "signed reverse-history, full-pair DAG, signed basis and resource replay passed",
        "evidence": "NUMERICAL",
        "timing_evidence": "CHECK",
        "complete_native_schedule": False,
        "native_runtime_seconds": None,
        "physical_qubits": None,
        "failure_probability": None,
        "grid": rows,
        "branches": branches,
    }
    write_json(output / "summary.json", summary)
    heatmap(output / "capacity-map.svg", rows, config)
    print(f"Wrote {output}", flush=True)


def verify_samples(output: Path, count: int) -> None:
    """Regenerate selected complete artifacts and compare their exact bytes."""
    if count < 1:
        raise ValueError("positive verification sample count required")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    for name, digest in summary["source_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"source binding changed: {name}")
    repeat = output / "reproduction"
    repeat.mkdir(exist_ok=True)
    audited = 0
    for expected in summary["branches"]:
        if expected["branch"] >= count:
            continue
        variant, branch = expected["variant"], expected["branch"]
        actual = profile(variant, branch, summary["config"], repeat)
        if actual != expected:
            raise ValueError(f"regenerated branch summary differs: {variant} {branch}")
        name = f"{variant}-branch-{branch}.json.gz"
        if (repeat / name).read_bytes() != (output / name).read_bytes():
            raise ValueError(f"regenerated bytes differ: {name}")
        audited += 1
        print(f"Byte-identical regenerated {name}", flush=True)
    write_json(
        repeat / "validation.json",
        {
            "task_id": TASK,
            "regenerated_branches": audited,
            "byte_identical": True,
            "scope": "both forced branches plus selected hashed branches",
        },
    )


if __name__ == "__main__":
    main()
