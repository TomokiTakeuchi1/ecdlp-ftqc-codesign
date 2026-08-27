"""Generate deterministic finite-capacity QCLA memory-I/O artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.circuits import build_qcla_trace, qcla_metrics
from ecdlp_ftqc.codes import load_pbc_mitten_backend_config
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    UnsupportedQclaMemoryIoScheduleError,
    load_memory_io_timing_config,
    qcla_io_aware_schedule_to_data,
    resource_state_demand_to_data,
    schedule_qcla_io_aware_pbc,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260825-002"
EXPERIMENT_ID = "E-20260825-002"
CONFIG_PATH = PROJECT_ROOT / "configs" / "architectures" / "qcla_j300_memory_io_v1.yaml"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "qcla_pbc.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "pbc_lowering.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "io" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "adaptive_pbc.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "qcla_io_aware_pbc.py",
    CONFIG_PATH,
    Path(__file__),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _git(*args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _load_cycle_config() -> tuple[dict[str, Any], Path, Path]:
    loaded: Any = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError("QCLA memory-I/O cycle config must be a mapping")
    if loaded.get("configuration_id") != "qcla-j300-memory-io-v1-sensitivity":
        raise RuntimeError("unsupported QCLA memory-I/O configuration ID")
    policies = loaded.get("policies")
    experiments = loaded.get("experiments")
    if not isinstance(policies, dict) or not isinstance(experiments, dict):
        raise TypeError("QCLA memory-I/O policy and experiment sections are required")
    expected = {
        "serial_one_scratch",
        "serial_ten_scratch",
        "high_rate_ten_scratch",
    }
    if set(policies) != expected:
        raise RuntimeError("QCLA memory-I/O policy set mismatch")
    return (
        loaded,
        PROJECT_ROOT / str(loaded["backend_config"]),
        PROJECT_ROOT / str(loaded["memory_io_config"]),
    )


def _compact_result(result: Any, width: int) -> dict[str, Any]:
    schedule = result
    metrics = qcla_metrics(build_qcla_trace(width))
    return {
        **qcla_io_aware_schedule_to_data(schedule),
        "compute_event_count": len(schedule.compute_events),
        "pbc_operation_count": len(schedule.lowering.pbc_trace.operations),
        "source_ancilla_count": metrics.source_ancilla_count,
        "source_gate_count": metrics.gate_count,
        "source_peak_live_ancillas": metrics.peak_live_ancillas,
        "source_toffoli_count": metrics.toffoli_count,
        "width": width,
    }


def _difference(left: int, right: int) -> dict[str, float | int]:
    delta = left - right
    return {
        "left_minus_right": delta,
        "relative_to_right": delta / right if right else 0.0,
    }


def main() -> None:
    config, backend_path, io_path = _load_cycle_config()
    backend = load_pbc_mitten_backend_config(backend_path)
    io_config = load_memory_io_timing_config(io_path)
    policies: dict[str, dict[str, Any]] = config["policies"]
    widths = tuple(int(width) for width in config["experiments"]["widths"])
    demand_width = int(config["experiments"]["demand_trace_width"])

    scaling: dict[str, dict[str, dict[str, Any]]] = {}
    demand_traces: dict[str, dict[str, Any]] = {}
    for width in widths:
        width_results: dict[str, dict[str, Any]] = {}
        for policy_name, policy in policies.items():
            result = schedule_qcla_io_aware_pbc(
                build_qcla_trace(width),
                backend,
                io_config,
                scratch_slot_count=int(policy["scratch_slot_count"]),
                enable_high_rate=bool(policy["high_rate_enabled"]),
                allow_check_assumptions=True,
            )
            if result.placement.peak_source_logical_occupancy > (
                backend.logical_qubits - result.scratch_slot_count
            ):
                raise RuntimeError("generated QCLA placement exceeds J300")
            width_results[policy_name] = _compact_result(result, width)
            if width == demand_width:
                demand_traces[policy_name] = {
                    "factory_mode": result.factory_mode,
                    "points": resource_state_demand_to_data(result),
                    "total_resource_state_demand": result.total_resource_state_demand,
                }
            print(
                json.dumps(
                    {
                        "high_rate_batches": result.high_rate_batch_count,
                        "loads": result.placement.loads,
                        "policy": policy_name,
                        "scheduled_rounds": result.scheduled_rounds,
                        "width": width,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        scaling[str(width)] = width_results

    zero_width = int(config["experiments"]["zero_round_regression_width"])
    zero_io = replace(
        io_config,
        configuration_id="qcla-zero-round-regression",
        load_rounds=0,
        store_rounds=0,
        timing_evidence_status=EvidenceStatus.PROVED,
    )
    zero_result = schedule_qcla_io_aware_pbc(
        build_qcla_trace(zero_width),
        backend,
        zero_io,
        scratch_slot_count=1,
        enable_high_rate=False,
        allow_check_assumptions=True,
    )
    zero_preserved = (
        zero_result.scheduled_rounds == zero_result.base_scheduled_rounds
        and tuple(event.start_round for event in zero_result.compute_events)
        == tuple(event.start_round for event in zero_result.base_schedule.events)
    )
    if not zero_preserved:
        raise RuntimeError("zero-round QCLA I/O regression changed base event timing")

    strict_width = int(config["experiments"]["strict_rejection_width"])
    strict_rejected = False
    try:
        schedule_qcla_io_aware_pbc(
            build_qcla_trace(strict_width),
            backend,
            io_config,
            scratch_slot_count=1,
            enable_high_rate=False,
        )
    except UnsupportedQclaMemoryIoScheduleError:
        strict_rejected = True
    if not strict_rejected:
        raise RuntimeError("strict QCLA I/O schedule did not reject CHECK timing")

    width_256 = scaling[str(demand_width)]
    serial_one = width_256["serial_one_scratch"]
    serial_ten = width_256["serial_ten_scratch"]
    high_rate_ten = width_256["high_rate_ten_scratch"]
    comparisons = {
        "scratch_payload_penalty_serial_ten_vs_one": {
            "scheduled_rounds": _difference(
                int(serial_ten["scheduled_rounds"]),
                int(serial_one["scheduled_rounds"]),
            ),
            "reloads": _difference(
                int(serial_ten["placement"]["reloads"]),
                int(serial_one["placement"]["reloads"]),
            ),
        },
        "high_rate_ten_vs_serial_ten": {
            "base_scheduled_rounds": _difference(
                int(high_rate_ten["base_scheduled_rounds"]),
                int(serial_ten["base_scheduled_rounds"]),
            ),
            "scheduled_rounds": _difference(
                int(high_rate_ten["scheduled_rounds"]),
                int(serial_ten["scheduled_rounds"]),
            ),
            "reloads": _difference(
                int(high_rate_ten["placement"]["reloads"]),
                int(serial_ten["placement"]["reloads"]),
            ),
        },
        "high_rate_ten_vs_serial_one_net": {
            "scheduled_rounds": _difference(
                int(high_rate_ten["scheduled_rounds"]),
                int(serial_one["scheduled_rounds"]),
            ),
            "reloads": _difference(
                int(high_rate_ten["placement"]["reloads"]),
                int(serial_one["placement"]["reloads"]),
            ),
        },
    }
    summary = {
        "configuration_id": config["configuration_id"],
        "evidence_qualification": {
            "fixed_order_capacity_and_location_replay": "PROVED exact checks",
            "generated_counts_and_schedule_comparisons": "NUMERICAL deterministic",
            "source_and_CCX_lowering": "LITERATURE plus prior NUMERICAL channel check",
            "transfer_native_and_clean_lifecycle_timing": "CHECK sensitivity",
        },
        "experiment_id": EXPERIMENT_ID,
        "exclusions": config["exclusions"],
        "factory": config["factory"],
        "strict_check_timing_rejected": strict_rejected,
        "task_id": TASK_ID,
        "validation_status": "passed",
        "width_256": {
            "comparisons": comparisons,
            "policies": width_256,
        },
        "zero_round_regression": {
            "base_event_starts_preserved": zero_preserved,
            "width": zero_width,
        },
    }

    raw_status = _git("status", "--porcelain").splitlines()
    filtered_status = "\n".join(
        line
        for line in raw_status
        if not line.startswith("?? .claude/")
        and f"experiments/runs/{TASK_ID}/" not in line.replace("\\", "/")
    )
    reproducibility = {
        "configuration": str(CONFIG_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "configuration_sha256": _sha256(CONFIG_PATH),
        "git_commit": _git("rev-parse", "HEAD"),
        "input_circuit": "draper-qcla-inplace-mod2n generated trace v1",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": hashlib.sha256(filtered_status.encode()).hexdigest().upper(),
        },
        "random_seed": "not_applicable_deterministic",
        "software_environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "pyyaml": importlib.metadata.version("pyyaml"),
        },
        "source_bindings": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "task_id": TASK_ID,
        "validation_status": "passed",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "scaling.json", scaling)
    _write_json(
        OUTPUT_ROOT / "qcla_width256_t_state_demand.json",
        {
            "evidence_status": "NUMERICAL",
            "factory_service_included": False,
            "policies": demand_traces,
            "task_id": TASK_ID,
            "width": demand_width,
        },
    )
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(comparisons, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
