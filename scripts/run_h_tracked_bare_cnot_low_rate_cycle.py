"""Reproduce the hybrid H-tracked/bare-CNOT finite-capacity study.

All policies use the same raw branches and source macro/barrier plan. Costs
are stored as exact fractions and integer services. Native execution stays open.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal, cast

from ecdlp_ftqc.circuits.qcla import build_qcla_trace
from ecdlp_ftqc.compiler.h_tracked_bare_cnot_trace import build_hybrid_trace
from ecdlp_ftqc.compiler.low_rate_policy_trace import build_legacy_trace
from ecdlp_ftqc.compiler.parallel_low_rate_trace import SEED, build_tracked_trace
from ecdlp_ftqc.scheduler.parallel_low_rate import Limits, Timing, lower, schedule_macro
from ecdlp_ftqc.verification.h_tracked_bare_cnot_low_rate import (
    audit_comparison,
    audit_cost,
    audit_hybrid_trace,
    audit_summary,
)
from ecdlp_ftqc.verification.low_rate_break_even import audit_legacy_trace, audit_pair_alignment
from ecdlp_ftqc.verification.parallel_low_rate import (
    audit_lowering,
    audit_packing,
    audit_service,
    audit_trace,
)

ROOT = Path(__file__).resolve().parents[1]
TASK = "T-20260927-001"
MANIFEST = ROOT / "experiments/manifests/E-20260927-001.json"
FIELDS = ("surgery", "prepare", "readout", "reaction")
RATES = ("surgery", "prepare_zero", "readout", "reaction")
CELL = ("parallel", "weight", "total_support")
POLICIES = ("hybrid_bare", "hybrid_frame", "full", "legacy")


def payload(data: Any, compressed: bool = False) -> bytes:
    def compact(value: Any) -> Any:
        if type(value) is int and value >= 2**53:
            return hex(value)
        if isinstance(value, dict):
            return {k: compact(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [compact(v) for v in value]
        return value

    raw = (
        json.dumps(
            compact(data),
            sort_keys=True,
            indent=None if compressed else 2,
            separators=(",", ":") if compressed else None,
        )
        + "\n"
    ).encode()
    return gzip.compress(raw, mtime=0, compresslevel=6) if compressed else raw


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: Any, compressed: bool = False) -> None:
    path.write_bytes(payload(data, compressed))


def source_hashes() -> dict[str, str]:
    files = [
        "scripts/run_h_tracked_bare_cnot_low_rate_cycle.py",
        "experiments/manifests/E-20260927-001.json",
        "src/ecdlp_ftqc/compiler/h_tracked_bare_cnot_trace.py",
        "src/ecdlp_ftqc/verification/h_tracked_bare_cnot_low_rate.py",
        "src/ecdlp_ftqc/compiler/parallel_low_rate_trace.py",
        "src/ecdlp_ftqc/compiler/low_rate_policy_trace.py",
        "src/ecdlp_ftqc/verification/parallel_low_rate.py",
        "src/ecdlp_ftqc/verification/low_rate_break_even.py",
        "src/ecdlp_ftqc/scheduler/parallel_low_rate.py",
        "src/ecdlp_ftqc/scheduler/width256_commutation_aware_qcla.py",
        "src/ecdlp_ftqc/scheduler/width256_ip_commutation_aware_qcla.py",
        "src/ecdlp_ftqc/circuits/qcla.py",
        "src/ecdlp_ftqc/circuits/qcla_oop.py",
    ]
    return {f: digest(ROOT / f) for f in files}


def fraction_record(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def cost(services: dict[str, int], timing: dict[str, Any]) -> Fraction:
    return sum(
        (services[f] * Fraction(str(timing[r])) for f, r in zip(FIELDS, RATES, strict=True)),
        Fraction(),
    )


def distribution(values: list[float | int]) -> dict[str, float | int] | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    return {
        "min": ordered[0],
        "p50": ordered[(n - 1) // 2],
        "p95": ordered[(95 * n + 99) // 100 - 1],
        "max": ordered[-1],
    }


def pair(reference: dict[str, Any], hybrid: dict[str, Any]) -> dict[str, Any]:
    if any(reference[k] != hybrid[k] for k in CELL):
        raise ValueError("capacity pairing mismatch")
    common = reference["feasible"] and hybrid["feasible"]
    delta = (
        Fraction(*reference["units_exact"]) - Fraction(*hybrid["units_exact"]) if common else None
    )
    full = reference["policy"] == "full"
    row = {
        **{k: hybrid[k] for k in CELL},
        "mode": hybrid["mode"],
        "hybrid_policy": hybrid["policy"],
        "reference_policy": reference["policy"],
        "reference_mode": reference["mode"],
        "status": "both_feasible"
        if common
        else "reference_only"
        if reference["feasible"]
        else "hybrid_only"
        if hybrid["feasible"]
        else "neither_feasible",
        "delta_services": {f: reference["services"][f] - hybrid["services"][f] for f in FIELDS}
        if common
        else None,
        "delta_units_exact": fraction_record(delta) if delta is not None else None,
        "delta_units": float(delta) if delta is not None else None,
        "condition": "B_hybrid < delta" if full else "B_hybrid - B_legacy < delta",
        "absolute_hybrid_budget": float(delta) if full and delta is not None else None,
        "equal_auto_call_allowance_if_four_calls_and_tx_zero": float(delta / 4)
        if full and delta is not None and hybrid.get("width") == 256
        else None,
        "native_runtime_seconds": None,
    }
    audit_comparison(row, reference, hybrid)
    return row


def profile(branch: int, config: dict[str, Any], output: Path) -> dict[str, Any]:
    width = config["width"]
    source = build_qcla_trace(width)
    gates = [asdict(g) for g in source.gates]
    traces = {
        "hybrid_bare": build_hybrid_trace(width, branch, "bare"),
        "hybrid_frame": build_hybrid_trace(width, branch, "frame"),
        "full": build_tracked_trace("ip", width, branch),
        "legacy": build_legacy_trace("ip", width, branch),
    }
    serialized = {k: asdict(t) for k, t in traces.items()}
    audits = {}
    for policy, trace_dict in serialized.items():
        audit_pair_alignment(serialized["full"], trace_dict)
        audits[policy] = (
            audit_hybrid_trace(trace_dict, gates, policy.split("_")[1])
            if policy.startswith("hybrid_")
            else audit_trace(trace_dict, gates)
            if policy == "full"
            else audit_legacy_trace(trace_dict, gates)
        )
    timing = Timing(**config["timing"])
    capacities = [(k, None) for k in config["parallel_limits"]] + [
        (64, s) for s in config["total_support_limits_at_k64"]
    ]
    grid = []
    statistics = {}
    details = {}
    for policy, trace in traces.items():
        for mode in ["qwc"] if policy == "legacy" else config["modes"]:
            los = [lower(m.ppms, cast(Literal["qwc", "general"], mode)) for m in trace.macros]
            ld = [asdict(lo) for lo in los]
            for macro, lowered_dict in zip(trace.macros, ld, strict=True):
                audit_lowering([asdict(p) for p in macro.ppms], lowered_dict)
            executed = [p for lo in los for stage in lo.stages for p in stage.ppms]
            presented = [p for m in trace.macros for p in m.ppms]
            maximum = max(p.weight for p in executed)
            tag = f"{policy}:{mode}"
            statistics[tag] = {
                "presented_weight_max": max(p.weight for p in presented),
                "executed_weight_max": maximum,
                "executed_ppm_count": len(executed),
                "presented_y_count": sum(bool(p.x & p.z) for p in presented),
                "presented_odd_y_count": sum((p.x & p.z).bit_count() % 2 for p in presented),
                "presented_mixed_count": sum(bool(p.x and p.z) for p in presented),
                "peak_extra_logical_ancillas": max(lo.logical_ancillas for lo in los),
                "peak_y_catalysts": max(lo.y_catalysts for lo in los),
                "main_stages": sum(s.kind != "prepare_y" for lo in los for s in lo.stages),
                "final_frame_max_weight": max(p.weight for p in (*trace.final_x, *trace.final_z)),
                "final_frame_total_weight": sum(p.weight for p in (*trace.final_x, *trace.final_z)),
            }
            examples = []
            for parallel, support in capacities:
                limits = Limits(parallel, None, support)
                total = {f: 0 for f in FIELDS}
                fits = True
                failures = []
                largest_sum = largest_union = 0
                timeline = []
                now = Fraction()
                for macro, lo, lo_dict in zip(trace.macros, los, ld, strict=True):
                    sched = schedule_macro(lo, limits, timing, len(macro.ppms))
                    sd = asdict(sched)
                    audit_packing(lo_dict, sd, asdict(limits))
                    audit_service(lo_dict, sd, config["timing"], len(macro.ppms))
                    fits &= sched.feasible
                    if not sched.feasible:
                        failures.append({"macro": macro.index, "reason": sched.reason})
                    services = dict(
                        zip(
                            FIELDS,
                            (
                                sched.surgery_steps or 0,
                                sched.prepare_steps,
                                sched.readout_steps,
                                sched.reaction_steps,
                            ),
                            strict=True,
                        )
                    )
                    for f in FIELDS:
                        total[f] += services[f]
                    for stage in sched.batches:
                        for batch in stage:
                            largest_sum = max(largest_sum, batch.weight_sum)
                            largest_union = max(largest_union, batch.support_union)
                    if parallel == 64 and support is None:
                        macro_duration = cost(services, config["timing"])
                        timeline.append(
                            {
                                "macro": macro.index,
                                "ppm_only_start_exact": fraction_record(now),
                                "ppm_only_end_exact": fraction_record(now + macro_duration),
                                "ccz_demand": len(macro.gate_ids),
                                "ccz_held_to_end": True,
                                "preceding_cliffords": macro.preceding_cliffords,
                                "logical_wire_envelope": 2 * width
                                + source.source_ancilla_count
                                + len(macro.ppms)
                                + lo.logical_ancillas,
                                "schedule": sd,
                            }
                        )
                        now += macro_duration
                if timeline:
                    examples.append(
                        {"parallel": parallel, "total_support": support, "macros": timeline}
                    )
                for weight in config["weight_limits"]:
                    feasible = fits and (weight is None or maximum <= weight)
                    reason = []
                    if not fits:
                        reason.append("executed_ppm_exceeds_sum_support_limit")
                    if weight is not None and maximum > weight:
                        reason.append("executed_ppm_exceeds_individual_weight_limit")
                    duration = cost(total, config["timing"]) if feasible else None
                    row = {
                        "policy": policy,
                        "mode": mode,
                        "width": width,
                        "parallel": parallel,
                        "weight": weight,
                        "total_support": support,
                        "feasible": feasible,
                        "rejection_reasons": reason,
                        "failed_macros_without_weight_cap": failures,
                        "services": total.copy() if feasible else None,
                        "units_exact": fraction_record(duration) if duration is not None else None,
                        "units": float(duration) if duration is not None else None,
                        "executed_max_weight": maximum,
                        "batch_sum_weight_max": largest_sum if feasible else None,
                        "batch_support_union_max": largest_union if feasible else None,
                        "complete_kernel_units": None,
                        "native_runtime_seconds": None,
                        "physical_qubits": None,
                    }
                    audit_cost(row, config["timing"])
                    grid.append(row)
            details[tag] = {"lowerings": ld, "representative_ppm_only_schedules": examples}
    indices = {(r["policy"], r["mode"], *(r[k] for k in CELL)): r for r in grid}
    comparisons = []
    for row in grid:
        if row["policy"].startswith("hybrid_"):
            for reference in ("full", "legacy"):
                mode = row["mode"] if reference == "full" else "qwc"
                comparisons.append(pair(indices[(reference, mode, *(row[k] for k in CELL))], row))
    # Pauli-only source-X policy differences cannot change axes or fixed service.
    for left, right in zip(
        traces["hybrid_bare"].macros, traces["hybrid_frame"].macros, strict=True
    ):
        if [(p.x, p.z) for p in left.ppms] != [(p.x, p.z) for p in right.ppms]:
            raise ValueError("X policy unexpectedly changed support/axis")
    for row in grid:
        if row["policy"] == "hybrid_bare":
            other = indices[("hybrid_frame", row["mode"], *(row[k] for k in CELL))]
            if any(row[k] != other[k] for k in row if k != "policy"):
                raise ValueError("X policy unexpectedly changed services")
    cnot_layers = []
    for layer in sorted({g["algorithmic_layer"] for g in gates if g["kind"] == "cnot"}):
        members = [g for g in gates if g["kind"] == "cnot" and g["algorithmic_layer"] == layer]
        cnot_layers.append(
            {
                "source_layer": layer,
                "count": len(members),
                "gate_ids": [g["gate_id"] for g in members],
                "native_call_count": None,
                "call_duration": None,
                "optimistic_sensitivity_calls": 1,
            }
        )
    if width == 256 and (
        [r["count"] for r in cnot_layers] != [256, 255, 254, 254]
        or len(traces["full"].macros) != 30
        or audits["hybrid_bare"] != 7374
    ):
        raise ValueError("width-256 regression target mismatch")
    artifact = output / f"ip-branch-{branch}.json.gz"
    write_json(
        artifact,
        {
            "traces": serialized,
            "modes": details,
            "timeline_scope": "PPM-only; physical source-Clifford intervals and factory supply excluded",
        },
        True,
    )
    return {
        "branch": branch,
        "variant": "ip",
        "width": width,
        "audited_coupling_ppms": audits,
        "statistics": statistics,
        "grid": grid,
        "comparisons": comparisons,
        "macro_count": len(traces["full"].macros),
        "ccz_count": sum(len(m.gate_ids) for m in traces["full"].macros),
        "peak_ccz_demand": max(len(m.gate_ids) for m in traces["full"].macros),
        "source_resident_values": 2 * width + source.source_ancilla_count,
        "cnot_layers": cnot_layers,
        "source_x_count": sum(g["kind"] == "x" for g in gates),
        "source_x_physical_service": {"bare": None, "frame": 0},
        "x_policy_axis_service_equal": True,
        "artifact": artifact.name,
        "artifact_sha256": digest(artifact),
    }


def cached_job(job: tuple[int, dict[str, Any], str, dict[str, str]]) -> dict[str, Any]:
    branch, config, directory, hashes = job
    output = Path(directory)
    checkpoint = output / f"ip-branch-{branch}.result.json"
    binding = hashlib.sha256(payload({"config": config, "sources": hashes})).hexdigest()
    if checkpoint.exists():
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        if data["binding"] != binding:
            raise ValueError("stale checkpoint; use a new output directory")
        result = data["result"]
        if result["branch"] != branch or result["width"] != config["width"]:
            raise ValueError("checkpoint identity mismatch")
        if digest(output / result["artifact"]) != result["artifact_sha256"]:
            raise ValueError("checkpoint artifact hash mismatch")
        audit_rows(result, config)
        return cast(dict[str, Any], result)
    result = profile(branch, config, output)
    audit_rows(result, config)
    write_json(checkpoint, {"binding": binding, "result": result})
    return result


def audit_rows(result: dict[str, Any], config: dict[str, Any]) -> None:
    index = {(r["policy"], r["mode"], *(r[k] for k in CELL)): r for r in result["grid"]}
    if len(index) != len(result["grid"]):
        raise ValueError("duplicate grid row")
    for row in result["grid"]:
        audit_cost(row, config["timing"])
    for row in result["comparisons"]:
        audit_comparison(
            row,
            index[(row["reference_policy"], row["reference_mode"], *(row[k] for k in CELL))],
            index[(row["hybrid_policy"], row["mode"], *(row[k] for k in CELL))],
        )


def aggregate(branches: list[dict[str, Any]], count: int) -> dict[str, Any]:
    hashed = sorted((b for b in branches if b["branch"] >= 0), key=lambda b: b["branch"])
    if [b["branch"] for b in hashed] != list(range(count)):
        raise ValueError("missing or duplicate hashed branch")
    grid: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for category, output, fields in (
        ("grid", grid, ("policy", "mode", *CELL)),
        (
            "comparisons",
            comparisons,
            ("hybrid_policy", "mode", "reference_policy", "reference_mode", *CELL),
        ),
    ):
        indexes = [{tuple(r[k] for k in fields): r for r in b[category]} for b in hashed]
        if any(
            len(i) != len(b[category]) or i.keys() != indexes[0].keys()
            for i, b in zip(indexes, hashed, strict=True)
        ):
            raise ValueError("missing/duplicate grid or comparison cell")
        for key in indexes[0]:
            rows = [i[key] for i in indexes]
            result = {**dict(zip(fields, key, strict=True)), "hashed_witness_count": count}
            if category == "grid":
                feasible = [r for r in rows if r["feasible"]]
                result.update(
                    {
                        "feasible_count": len(feasible),
                        "units": distribution([r["units"] for r in feasible]),
                        "surgery_steps": distribution([r["services"]["surgery"] for r in feasible]),
                    }
                )
            else:
                common = [r for r in rows if r["status"] == "both_feasible"]
                result.update(
                    {
                        "status_counts": {
                            s: sum(r["status"] == s for r in rows)
                            for s in (
                                "both_feasible",
                                "reference_only",
                                "hybrid_only",
                                "neither_feasible",
                            )
                        },
                        "delta_units": distribution([r["delta_units"] for r in common]),
                        "negative_delta_count": sum(r["delta_units"] < 0 for r in common),
                        "zero_delta_count": sum(r["delta_units"] == 0 for r in common),
                        "condition": rows[0]["condition"],
                    }
                )
            output.append(result)
    return {"grid": grid, "comparisons": comparisons}


def verify_samples(output: Path, count: int) -> None:
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if summary["source_sha256"] != source_hashes():
        raise ValueError("source changed since generation")
    repeat = output / "reproduction"
    repeat.mkdir(exist_ok=True)
    checked = []
    for expected in summary["branches"]:
        if expected["branch"] >= count:
            continue
        actual = profile(expected["branch"], summary["config"], repeat)
        if (
            actual != expected
            or (repeat / actual["artifact"]).read_bytes()
            != (output / expected["artifact"]).read_bytes()
        ):
            raise ValueError("artifact regeneration mismatch")
        checked.append(expected["branch"])
        print(f"Byte-identical branch {expected['branch']}", flush=True)
    write_json(repeat / "validation.json", {"branches": checked, "byte_identical": True})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--width", type=int)
    parser.add_argument("--branches", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--verify-samples", type=int)
    args = parser.parse_args()
    output = args.output or ROOT / "experiments/runs" / TASK
    if args.verify_samples is not None:
        verify_samples(output, args.verify_samples)
        return
    config = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (args.width is not None or args.branches is not None) and args.output is None:
        raise ValueError("noncanonical run requires explicit output")
    if args.width is not None:
        config["width"] = args.width
    if args.branches is not None:
        config["hashed_branches"] = args.branches
    if config["width"] < 2 or config["hashed_branches"] < 1 or not 1 <= args.workers <= 8:
        raise ValueError("invalid experiment dimensions")
    if (
        config["branch_seed"] != SEED
        or config["native_runtime_seconds"] is not None
        or config["timing"]["seconds_per_unit"] is not None
    ):
        raise ValueError("invalid seed/native boundary")
    output.mkdir(parents=True, exist_ok=True)
    hashes = source_hashes()
    jobs = [
        (b, config, str(output), hashes)
        for b in [*config["forced_branches"], *range(config["hashed_branches"])]
    ]
    branches = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(cached_job, jobs):
            branches.append(result)
            print(f"Audited branch {result['branch']} ({len(branches)}/{len(jobs)})", flush=True)
    if hashes != source_hashes():
        raise ValueError("source changed during generation")
    summary = {
        "task_id": TASK,
        "config": config,
        "source_sha256": hashes,
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree": "task working tree; exact computational hashes recorded",
        "environment": {
            "python": platform.python_version(),
            **{p: version(p) for p in ("numpy", "pytest")},
        },
        "evidence": "NUMERICAL",
        "timing_evidence": "CHECK",
        "native_runtime_seconds": None,
        "physical_qubits": None,
        "failure_probability": None,
        "complete_native_schedule": False,
        "native_automorphism_calls": None,
        "scope": config["scope"],
        "validation": "independent signed, lowering, packing, service and exact-rational pairing audits passed",
        **aggregate(branches, config["hashed_branches"]),
        "branches": branches,
    }
    write_json(output / "summary.json", summary)
    audit_summary(json.loads((output / "summary.json").read_text(encoding="utf-8")))
    print(f"Wrote {output}", flush=True)


if __name__ == "__main__":
    main()
