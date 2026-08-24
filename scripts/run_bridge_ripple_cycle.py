"""Generate deterministic artifacts for T-20260824-001."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from ecdlp_ftqc.circuits import (
    ACTIVE_VOLUME_PDF_SHA256,
    XU_ADDER_PDF_SHA256,
    bridge_trace_to_data,
    build_bridge_ripple_trace,
    evaluate_bridge_basis_projection,
    replay_bridge_lifecycle,
    verify_generic_bell_bridge_identity,
)
from ecdlp_ftqc.scheduler import (
    bridge_schedule_to_data,
    load_bridge_timing_config,
    schedule_bridge_ripple,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260824-001"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
CONFIG_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "bridge_ripple_sensitivity_v1.yaml"
)
XU_PDF = PROJECT_ROOT / "literature" / "papers" / "2407.18490v1.pdf"
ACTIVE_VOLUME_PDF = (
    PROJECT_ROOT / "literature" / "papers" / "2211.15465v1.pdf"
)
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "bridge_ripple.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "bridge_ripple.py",
    CONFIG_PATH,
)
SEMANTIC_WIDTHS = (2, 3, 4)
SCHEDULE_WIDTHS = (4, 8, 11, 16, 32)
BELL_LANES = (1, 2, 4, 8, 10)


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


def _verify_sources() -> None:
    expected = {
        XU_PDF: XU_ADDER_PDF_SHA256,
        ACTIVE_VOLUME_PDF: ACTIVE_VOLUME_PDF_SHA256,
    }
    for path, digest in expected.items():
        if not path.is_file():
            raise RuntimeError(f"missing pinned source PDF: {path}")
        if _sha256(path) != digest:
            raise RuntimeError(f"source PDF hash mismatch: {path}")


def _basis_results() -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for width in SEMANTIC_WIDTHS:
        limit = 1 << width
        checked = 0
        for input_register in range(limit):
            for target_register in range(limit):
                result = evaluate_bridge_basis_projection(
                    width, input_register, target_register
                )
                expected = (input_register + target_register) % limit
                if (
                    result.output_input_register != input_register
                    or result.output_target_register != expected
                ):
                    raise RuntimeError("bridge basis projection mismatch")
                checked += 1
        results[str(width)] = {
            "all_passed": True,
            "basis_input_pairs_checked": checked,
        }
    return results


def _schedule_results() -> dict[str, dict[str, dict[str, object]]]:
    base_config = load_bridge_timing_config(CONFIG_PATH)
    results: dict[str, dict[str, dict[str, object]]] = {}
    for width in SCHEDULE_WIDTHS:
        trace = build_bridge_ripple_trace(width)
        by_lane: dict[str, dict[str, object]] = {}
        for lane_count in BELL_LANES:
            config = replace(base_config, bell_measurement_lanes=lane_count)
            disabled = schedule_bridge_ripple(
                trace,
                config,
                allow_check_assumptions=True,
                high_rate_enabled=False,
            )
            enabled = schedule_bridge_ripple(
                trace,
                config,
                allow_check_assumptions=True,
                high_rate_enabled=True,
            )
            by_lane[str(lane_count)] = {
                "algorithmic_critical_path_steps": (
                    enabled.algorithmic_critical_path_steps
                ),
                "disabled_steps": disabled.scheduled_steps,
                "enabled_steps": enabled.scheduled_steps,
                "high_rate_batch_count": enabled.high_rate_batch_count,
                "high_rate_operation_count": enabled.high_rate_operation_count,
                "net_saved_steps": disabled.scheduled_steps - enabled.scheduled_steps,
                "peak_live_bridge_carriers": enabled.peak_live_bridge_carriers,
                "peak_resource_state_demand_per_step": (
                    enabled.peak_resource_state_demand_per_step
                ),
                "strict_executable": enabled.strict_executable,
                "total_resource_state_demand": enabled.total_resource_state_demand,
            }
        results[str(width)] = by_lane
    return results


def _structural_width256() -> dict[str, object]:
    trace = build_bridge_ripple_trace(256)
    replay = replay_bridge_lifecycle(trace)
    return {
        "bridge_count": trace.bridge_count,
        "bridge_segment_depth": trace.bridge_segment_depth,
        "event_count": len(trace.events),
        "peak_live_bridge_carriers": replay.peak_live_bridge_carriers,
        "reactive_ancilla_patch_count": trace.reactive_ancilla_patch_count,
        "sequential_segment_depth_reference": (
            trace.sequential_segment_depth_reference
        ),
        "source_logical_carrier_slots_across_five_patches": (
            trace.source_logical_carrier_slots
        ),
        "temporary_and_count": trace.temporary_and_count,
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    _verify_sources()
    project_status = _git("status", "--porcelain")
    teleportation = verify_generic_bell_bridge_identity(
        seed=20260824, sample_count=32
    )
    if not teleportation.passed:
        raise RuntimeError("generic Bell-bridge verification failed")
    schedules = _schedule_results()
    result: dict[str, Any] = {
        "evidence_qualification": {
            "basis_projection": (
                "NUMERICAL classical-basis projection; not an independent full "
                "phase/channel reconstruction of Xu Figure 6"
            ),
            "finite_timing": (
                "CHECK normalized sensitivity steps; not HGP logical cycles, "
                "active-volume blocks, J300 syndrome rounds, or wall-clock time"
            ),
            "generic_bell_bridge": (
                "NUMERICAL branchwise identity-channel check for the generic "
                "Bell bridge used by the source construction"
            ),
            "source_circuit": (
                "LITERATURE Xu Figure 6 and Active Volume Figures 10/16/24"
            ),
        },
        "experiment_id": "E-20260824-001",
        "generic_bell_bridge_verification": {
            "branch_count": teleportation.branch_count,
            "maximum_frobenius_error": (
                teleportation.maximum_frobenius_error
            ),
            "minimum_branch_probability": (
                teleportation.minimum_branch_probability
            ),
            "passed": teleportation.passed,
            "sample_count": teleportation.sample_count,
            "seed": teleportation.seed,
        },
        "input_configuration": str(CONFIG_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "project_commit": _git("rev-parse", "HEAD"),
        "project_worktree": {
            "status": "dirty" if project_status else "clean",
            "status_sha256": hashlib.sha256(project_status.encode()).hexdigest(),
        },
        "random_seed": 20260824,
        "schedule_sensitivity": schedules,
        "semantic_basis_projection": _basis_results(),
        "software_environment": {
            "platform": platform.platform(),
            "python": sys.version,
        },
        "source_bindings": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "source_pdfs": {
            "literature/papers/2211.15465v1.pdf": _sha256(ACTIVE_VOLUME_PDF),
            "literature/papers/2407.18490v1.pdf": _sha256(XU_PDF),
        },
        "source_reported_structure": {
            "active_volume_sequential_adder_active_volume": (
                "(n-1)*(22+C_CCZ)-3"
            ),
            "active_volume_sequential_reaction_depth": "2n-3",
            "xu_encoded_patch_families": ["a", "b", "c", "d", "e"],
            "xu_parallel_scaling_without_finite_constants": (
                "c1*sqrt(k)*log(k)+c2*k logical cycles"
            ),
            "xu_reactive_ancilla_patch_count": 6,
        },
        "structural_width256": _structural_width256(),
        "task_id": TASK_ID,
        "validation_status": (
            "generated_after_source_hash_checks_semantic_projection_"
            "branchwise_bridge_check_and_independent_lifecycle_replay"
        ),
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "summary.json", result)
    _write_json(
        OUTPUT_ROOT / "bridge_width4_trace.json",
        bridge_trace_to_data(build_bridge_ripple_trace(4)),
    )
    width32_trace = build_bridge_ripple_trace(32)
    width32_schedule = schedule_bridge_ripple(
        width32_trace,
        load_bridge_timing_config(CONFIG_PATH),
        allow_check_assumptions=True,
        high_rate_enabled=True,
    )
    _write_json(
        OUTPUT_ROOT / "bridge_width32_lane1_schedule.json",
        bridge_schedule_to_data(width32_schedule),
    )
    demand = [
        {
            "resource_state_demand": sum(
                width32_trace.event_by_id()[source_id].resource_state_demand
                for source_id in event.source_event_ids
            ),
            "source_event_ids": list(event.source_event_ids),
            "start_step": event.start_step,
        }
        for event in width32_schedule.events
        if any(
            width32_trace.event_by_id()[source_id].resource_state_demand
            for source_id in event.source_event_ids
        )
    ]
    _write_json(
        OUTPUT_ROOT / "width32_resource_state_demand.json",
        {
            "evidence_status": "CHECK",
            "time_unit": width32_schedule.time_unit,
            "trace_id": width32_trace.trace_id,
            "events": demand,
        },
    )
    print(OUTPUT_ROOT / "summary.json")


if __name__ == "__main__":
    main()
