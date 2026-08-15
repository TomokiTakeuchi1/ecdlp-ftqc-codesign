"""Generate the bounded Gidney-to-Mitten research-cycle artifacts."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecdlp_ftqc.circuits import (
    PINNED_GIDNEY_SOURCE_COMMIT,
    generate_gidney_dag,
)
from ecdlp_ftqc.codes import load_mitten_backend_config
from ecdlp_ftqc.compiler import lower_gidney_phase_exact
from ecdlp_ftqc.scheduler import (
    ProcessorCapacityError,
    UnsupportedMittenLoweringError,
    schedule_mitten_greedy,
    schedule_to_data,
)

TASK_ID = "T-20260815-002"
EXPERIMENT_ID = "E-20260815-001"
WIDTHS = (2, 3, 4, 16, 32, 59)
RELEVANT_SOURCE_PATHS = (
    "src/runtime_metadata_benchmark/gidney",
    "src/runtime_metadata_benchmark/ir",
    "src/runtime_metadata_benchmark/ppm",
    "src/runtime_metadata_benchmark/scheduling",
)


def _git(repo: Path, *arguments: str, check: bool = True) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repo.as_posix()}",
            "-C",
            str(repo),
            *arguments,
        ],
        check=check,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _verify_source(source_repo: Path) -> None:
    observed_commit = _git(source_repo, "rev-parse", "HEAD")
    if observed_commit != PINNED_GIDNEY_SOURCE_COMMIT:
        raise RuntimeError(
            "Gidney source commit mismatch: "
            f"expected {PINNED_GIDNEY_SOURCE_COMMIT}, observed {observed_commit}"
        )
    status = _git(source_repo, "status", "--porcelain", "--", *RELEVANT_SOURCE_PATHS)
    if status:
        raise RuntimeError("Gidney source inputs contain uncommitted changes:\n" + status)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _summary(schedule_data: dict[str, Any], primitive_count: int) -> dict[str, Any]:
    return {
        "dependency_only_critical_path_rounds": schedule_data[
            "dependency_only_critical_path_rounds"
        ],
        "high_rate_primitive_count": schedule_data["high_rate_primitive_count"],
        "implementation_counts": schedule_data["implementation_counts"],
        "known_peak_physical_qubits_lower_bound": schedule_data[
            "known_peak_physical_qubits_lower_bound"
        ],
        "peak_source_processor_occupancy": schedule_data[
            "peak_source_processor_occupancy"
        ],
        "physical_qubit_total_complete": schedule_data[
            "physical_qubit_total_complete"
        ],
        "primitive_count": primitive_count,
        "scheduled_rounds": schedule_data["scheduled_rounds"],
        "sequential_rounds": schedule_data["sequential_rounds"],
        "strict_executable": schedule_data["strict_executable"],
        "total_resource_state_demand": schedule_data[
            "total_resource_state_demand"
        ],
        "unresolved_primitive_kinds": schedule_data[
            "unresolved_primitive_kinds"
        ],
    }


def _run(source_repo: Path, config_path: Path, output_dir: Path) -> None:
    _verify_source(source_repo)
    sys.path.insert(0, str(source_repo / "src"))
    config = load_mitten_backend_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, Any] = {}
    strict_errors: dict[str, str] = {}
    for width in WIDTHS:
        trace = lower_gidney_phase_exact(generate_gidney_dag(width))
        try:
            schedule_mitten_greedy(trace, config)
        except UnsupportedMittenLoweringError as exc:
            strict_errors[str(width)] = str(exc)
        provisional = schedule_mitten_greedy(
            trace, config, allow_check_assumptions=True
        )
        data = schedule_to_data(provisional)
        _write_json(output_dir / f"gidney_width{width}_schedule.json", data)
        summaries[str(width)] = _summary(data, len(trace.primitives))

    width_60_trace = lower_gidney_phase_exact(generate_gidney_dag(60))
    try:
        schedule_mitten_greedy(
            width_60_trace, config, allow_check_assumptions=True
        )
    except ProcessorCapacityError as exc:
        capacity_boundary = {
            "status": "INFEASIBLE",
            "width": 60,
            "peak_source_processor_occupancy": (
                width_60_trace.peak_source_processor_occupancy
            ),
            "processor_logical_capacity": config.logical_qubits,
            "reason": str(exc),
        }
    else:
        raise AssertionError("width 60 unexpectedly fit the 60-logical processor")

    _write_json(
        output_dir / "summary.json",
        {
            "capacity_boundary": capacity_boundary,
            "configuration_id": config.configuration_id,
            "evidence_status": "CHECK",
            "experiment_id": EXPERIMENT_ID,
            "factory_mode": "ideal_supply_no_stalls",
            "notes": [
                "Runtime includes CHECK placeholder costs for unresolved intra-block CQLU lowering.",
                "Known physical-qubit values are lower bounds; placeholder gadget space is zero.",
                "Single-X erasures use seed surgery and are not promoted to high-rate surgery.",
            ],
            "strict_mode_errors": strict_errors,
            "task_id": TASK_ID,
            "widths": summaries,
        },
    )
    demand = {
        str(width): [
            {
                "event_id": event["event_id"],
                "resource_state_demand": event["resource_state_demand"],
                "start_round": event["start_round"],
            }
            for event in json.loads(
                (output_dir / f"gidney_width{width}_schedule.json").read_text(
                    encoding="utf-8"
                )
            )["events"]
            if event["resource_state_demand"]
        ]
        for width in WIDTHS
    }
    _write_json(output_dir / "resource_state_demand.json", demand)
    working_tree = _git(PROJECT_ROOT, "status", "--porcelain", check=False)
    _write_json(
        output_dir / "reproducibility.json",
        {
            "architecture_configuration": str(config_path.relative_to(PROJECT_ROOT)),
            "assumption_ids": [
                "A-0004",
                "A-0006",
                "A-0007",
                "A-0008",
                "A-0009",
                "A-0010",
            ],
            "circuit_source": "runtime_metadata_benchmark.gidney",
            "circuit_source_commit": PINNED_GIDNEY_SOURCE_COMMIT,
            "code_instance": "[[300,60,14]] Mitten",
            "experiment_id": EXPERIMENT_ID,
            "factory_assumption": "ideal supply; no stalls; demand retained",
            "git_commit": "unborn repository",
            "output_path": str(output_dir.relative_to(PROJECT_ROOT)),
            "processor_capacity": config.logical_qubits,
            "python": platform.python_version(),
            "random_seed": None,
            "task_id": TASK_ID,
            "validation_status": "CHECK",
            "working_tree_porcelain": working_tree.splitlines(),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-repo",
        type=Path,
        default=PROJECT_ROOT.parent / "runtime-metadata-benchmark",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "codes" / "mitten_j300_k60_d14_v1.yaml",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "experiments" / "runs" / TASK_ID,
    )
    arguments = parser.parse_args()
    _run(
        arguments.source_repo.resolve(),
        arguments.config.resolve(),
        arguments.output_dir.resolve(),
    )


if __name__ == "__main__":
    main()
