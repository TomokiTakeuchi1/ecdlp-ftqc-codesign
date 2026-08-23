"""Generate reproducible J300 schedules from adaptive PBC traces."""

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

from ecdlp_ftqc.circuits import PINNED_GIDNEY_SOURCE_COMMIT, generate_gidney_dag
from ecdlp_ftqc.codes import load_pbc_mitten_backend_config
from ecdlp_ftqc.compiler import (
    LogicalPrimitive,
    LogicalPrimitiveKind,
    LogicalTrace,
    lower_gidney_phase_exact,
    lower_to_adaptive_pauli_measurements,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    UnsupportedAdaptivePbcScheduleError,
    adaptive_pbc_schedule_to_data,
    schedule_adaptive_pbc_greedy,
)

TASK_ID = "T-20260815-005"
EXPERIMENT_ID = "E-20260815-003"
WIDTHS = (2, 4, 16, 32)
RELEVANT_SOURCE_PATHS = (
    "src/runtime_metadata_benchmark/gidney",
    "src/runtime_metadata_benchmark/ir",
    "src/runtime_metadata_benchmark/ppm",
    "src/runtime_metadata_benchmark/scheduling",
)
PROFILES = (
    ("scratch1_serial", 1, False),
    ("scratch1_high_rate_enabled", 1, True),
    ("scratch10_serial", 10, False),
    ("scratch10_high_rate_enabled", 10, True),
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


def _schedule_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "classical_reaction_evidence_status": data[
            "classical_reaction_evidence_status"
        ],
        "dependency_only_critical_path_rounds": data[
            "dependency_only_critical_path_rounds"
        ],
        "high_rate_batch_count": data["high_rate_batch_count"],
        "high_rate_operation_count": data["high_rate_operation_count"],
        "implementation_counts": data["implementation_counts"],
        "known_peak_physical_qubits_lower_bound": data[
            "known_peak_physical_qubits_lower_bound"
        ],
        "peak_total_logical_occupancy": data["peak_total_logical_occupancy"],
        "physical_qubit_total_complete": data["physical_qubit_total_complete"],
        "primary_bottleneck_counts": data["primary_bottleneck_counts"],
        "scheduled_rounds": data["scheduled_rounds"],
        "serialized_operation_rounds": data["serialized_operation_rounds"],
        "strict_executable": data["strict_executable"],
        "total_resource_state_demand": data["total_resource_state_demand"],
        "unresolved_implementations": data["unresolved_implementations"],
    }


def _ten_independent_cnot_trace() -> LogicalTrace:
    primitives = tuple(
        LogicalPrimitive(
            primitive_id=f"cnot:{index:02d}",
            source_node_id=f"source:{index:02d}",
            kind=LogicalPrimitiveKind.CNOT,
            logical_support=(f"q:{2 * index}", f"q:{2 * index + 1}"),
            evidence_status=EvidenceStatus.LITERATURE,
        )
        for index in range(10)
    )
    return LogicalTrace(
        trace_id="synthetic-ten-independent-cnot",
        source_circuit_id="gidney-ripple-adder-width-synthetic",
        source_dag_schema_version=1,
        source_evidence_status=EvidenceStatus.LITERATURE,
        peak_source_processor_occupancy=20,
        primitives=primitives,
        dependencies=(),
    )


def _run(source_repo: Path, config_path: Path, output_dir: Path) -> None:
    _verify_source(source_repo)
    sys.path.insert(0, str(source_repo / "src"))
    config = load_pbc_mitten_backend_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, Any] = {}
    resource_demand: dict[str, Any] = {}
    width_two_schedule: dict[str, Any] | None = None
    strict_rejection = ""
    for width in WIDTHS:
        pbc_trace = lower_to_adaptive_pauli_measurements(
            lower_gidney_phase_exact(generate_gidney_dag(width))
        )
        width_profiles: dict[str, Any] = {}
        width_demand: dict[str, Any] = {}
        for profile, scratch_slots, high_rate in PROFILES:
            schedule = schedule_adaptive_pbc_greedy(
                pbc_trace,
                config,
                scratch_slot_count=scratch_slots,
                enable_high_rate=high_rate,
                allow_check_assumptions=True,
            )
            data = adaptive_pbc_schedule_to_data(schedule)
            width_profiles[profile] = _schedule_summary(data)
            width_demand[profile] = [
                {
                    "count": event["resource_state_demand"],
                    "event_id": event["event_id"],
                    "start_round": event["start_round"],
                }
                for event in data["events"]
                if event["resource_state_demand"]
            ]
            if width == 2 and profile == "scratch1_serial":
                width_two_schedule = data
        summaries[str(width)] = width_profiles
        resource_demand[str(width)] = width_demand
        if width == 2:
            try:
                schedule_adaptive_pbc_greedy(pbc_trace, config)
            except UnsupportedAdaptivePbcScheduleError as exc:
                strict_rejection = str(exc)

    synthetic_pbc = lower_to_adaptive_pauli_measurements(
        _ten_independent_cnot_trace()
    )
    synthetic_serial = schedule_adaptive_pbc_greedy(
        synthetic_pbc,
        config,
        scratch_slot_count=10,
        enable_high_rate=False,
        allow_check_assumptions=True,
    )
    synthetic_high_rate = schedule_adaptive_pbc_greedy(
        synthetic_pbc,
        config,
        scratch_slot_count=10,
        enable_high_rate=True,
        allow_check_assumptions=True,
    )
    if width_two_schedule is None or not strict_rejection:
        raise AssertionError("width-two schedule or strict rejection was not generated")

    _write_json(output_dir / "gidney_width2_schedule.json", width_two_schedule)
    _write_json(output_dir / "resource_state_demand.json", resource_demand)
    _write_json(
        output_dir / "summary.json",
        {
            "configuration_id": config.configuration_id,
            "evidence_status": "CHECK",
            "experiment_id": EXPERIMENT_ID,
            "factory_mode": "ideal supply; demand retained; no factory schedule",
            "high_rate_rule": (
                "exactly ten ready, pairwise-disjoint XX products using ten "
                "distinct live scratch slots"
            ),
            "physical_qubit_result": (
                "known lower bound only; preparation, injection, conditional CZ, "
                "factory, routing, bridge, and memory I/O space are incomplete"
            ),
            "strict_runtime_available": False,
            "strict_rejection": strict_rejection,
            "synthetic_parallelism_witness": {
                "evidence_status": "NUMERICAL",
                "high_rate_batch_count": synthetic_high_rate.high_rate_batch_count,
                "high_rate_scheduled_rounds": synthetic_high_rate.scheduled_rounds,
                "serial_scheduled_rounds": synthetic_serial.scheduled_rounds,
                "speedup": (
                    synthetic_serial.scheduled_rounds
                    / synthetic_high_rate.scheduled_rounds
                ),
                "qualification": (
                    "compiler/scheduler witness only; not an adder workload result"
                ),
            },
            "task_id": TASK_ID,
            "widths": summaries,
        },
    )
    working_tree = _git(PROJECT_ROOT, "status", "--porcelain", check=False)
    _write_json(
        output_dir / "reproducibility.json",
        {
            "architecture_configuration": str(config_path.relative_to(PROJECT_ROOT)),
            "assumption_ids": [
                "A-0004",
                "A-0006",
                "A-0008",
                "A-0009",
                "A-0011",
                "A-0012",
                "A-0013",
                "A-0014",
                "A-0015",
            ],
            "circuit_source": "runtime_metadata_benchmark.gidney",
            "circuit_source_commit": PINNED_GIDNEY_SOURCE_COMMIT,
            "code_instance": "[[300,60,14]] J300 Mitten",
            "experiment_id": EXPERIMENT_ID,
            "factory_assumption": "ideal supply; no stalls; demand retained",
            "git_commit": "unborn repository",
            "input_trace": "ecdlp-ftqc/adaptive-pauli-measurement-trace v1",
            "output_path": str(output_dir.relative_to(PROJECT_ROOT)),
            "python": platform.python_version(),
            "random_seed": None,
            "scheduler": "deterministic greedy adaptive-PBC upper bound",
            "task_id": TASK_ID,
            "validation_status": "NUMERICAL scheduler validation; runtime CHECK",
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
        default=PROJECT_ROOT / "configs" / "codes" / "mitten_j300_pbc_v2.yaml",
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
