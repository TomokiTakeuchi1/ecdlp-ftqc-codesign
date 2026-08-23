"""Generate the bounded T-20260823-001 memory-I/O result bundle."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecdlp_ftqc.circuits import generate_gidney_dag
from ecdlp_ftqc.codes import load_pbc_mitten_backend_config
from ecdlp_ftqc.compiler import (
    lower_gidney_phase_exact,
    lower_to_adaptive_pauli_measurements,
)
from ecdlp_ftqc.io import (
    adapt_gidney_dag_to_memory_program,
    build_maximal_prefix_partitions,
    schedule_small_width_partition_reference,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    MemoryIoTimingConfig,
    load_memory_io_timing_config,
    schedule_adaptive_pbc_greedy,
    schedule_io_aware_adaptive_pbc,
)

TASK_ID = "T-20260823-001"
EXPERIMENT_ID = "E-20260823-001"
SOURCE_COMMIT = "75a6e83d5acde37f0987ab867352ee8b2c6afd10"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = PROJECT_ROOT.parent
SOURCE_REPOSITORY = RESEARCH_ROOT / "runtime-metadata-benchmark"
SOURCE_PACKAGE = SOURCE_REPOSITORY / "src"
OUTPUT_PATH = PROJECT_ROOT / "experiments" / "runs" / TASK_ID / "summary.json"
REFERENCE_PATH = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "memory_io"
    / "legacy_partition_reference.json"
)
PBC_CONFIG_PATH = PROJECT_ROOT / "configs" / "codes" / "mitten_j300_pbc_v2.yaml"
IO_CONFIG_PATH = PROJECT_ROOT / "configs" / "architectures" / "j300_memory_io_v1.yaml"
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "io" / "model.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "io" / "gidney_adapter.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "io" / "placement.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "io" / "replay.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "io_aware_pbc.py",
    PBC_CONFIG_PATH,
    IO_CONFIG_PATH,
    REFERENCE_PATH,
)


def _git(*args: str, repository: Path) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repository.as_posix()}",
            "-C",
            str(repository),
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_source_checkout() -> None:
    if _git("rev-parse", "HEAD", repository=SOURCE_REPOSITORY) != SOURCE_COMMIT:
        raise RuntimeError("runtime-metadata-benchmark checkout is not source-pinned")
    if _git("status", "--porcelain", repository=SOURCE_REPOSITORY):
        raise RuntimeError("runtime-metadata-benchmark checkout is not clean")
    unchanged = _git(
        "diff",
        "--stat",
        "8c1638805e7246c30117a0251526661039df1369.." + SOURCE_COMMIT,
        "--",
        "src/runtime_metadata_benchmark/gidney",
        "src/runtime_metadata_benchmark/ir/model.py",
        "src/runtime_metadata_benchmark/ir/oracle_json.py",
        repository=SOURCE_REPOSITORY,
    )
    if unchanged:
        raise RuntimeError("reviewed Gidney frontend changed after its pinned fixture commit")


def _legacy_reference_results() -> dict[str, Any]:
    expected = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    widths: dict[str, Any] = {}
    for width_text, rows in expected["widths"].items():
        width = int(width_text)
        dag = generate_gidney_dag(width, source_commit=SOURCE_COMMIT)
        program = adapt_gidney_dag_to_memory_program(dag)
        observed_rows: list[dict[str, int]] = []
        for row in rows:
            layout = build_maximal_prefix_partitions(program, row["capacity"])
            schedule = schedule_small_width_partition_reference(program, layout)
            observed = {
                "capacity": schedule.capacity,
                "loads": schedule.loads,
                "partitions": len(layout.partitions),
                "stores": schedule.stores,
            }
            if observed != row:
                raise RuntimeError(
                    f"legacy reference mismatch at width {width}: {observed} != {row}"
                )
            observed_rows.append(observed)
        widths[width_text] = observed_rows
    return {
        "evidence_status": "NUMERICAL",
        "qualification": "Exact small-width source-pinned regression",
        "widths": widths,
    }


def _pbc_results() -> dict[str, Any]:
    backend = load_pbc_mitten_backend_config(PBC_CONFIG_PATH)
    sensitivity = load_memory_io_timing_config(IO_CONFIG_PATH)
    ideal = MemoryIoTimingConfig(
        configuration_id="architecture-memory-io-zero-latency-regression-v1",
        logical_qubits=sensitivity.logical_qubits,
        transfer_lanes=sensitivity.transfer_lanes,
        load_rounds=0,
        store_rounds=0,
        timing_evidence_status=EvidenceStatus.PROVED,
        source_note="Regression boundary only; not a physical architecture claim",
    )
    results: dict[str, Any] = {}
    for width in (2, 4, 16, 32):
        dag = generate_gidney_dag(width, source_commit=SOURCE_COMMIT)
        logical = lower_gidney_phase_exact(dag)
        pbc = lower_to_adaptive_pauli_measurements(logical)
        base = schedule_adaptive_pbc_greedy(
            pbc,
            backend,
            scratch_slot_count=1,
            enable_high_rate=True,
            allow_check_assumptions=True,
        )
        ideal_schedule = schedule_io_aware_adaptive_pbc(
            dag, logical, pbc, base, ideal
        )
        if ideal_schedule.scheduled_rounds != base.scheduled_rounds:
            raise RuntimeError("zero-latency I/O changed the reviewed PBC schedule")
        sensitivity_schedule = schedule_io_aware_adaptive_pbc(
            dag,
            logical,
            pbc,
            base,
            sensitivity,
            allow_check_assumptions=True,
        )
        results[str(width)] = {
            "base_scheduled_rounds": base.scheduled_rounds,
            "high_rate_batch_count": base.high_rate_batch_count,
            "ideal_io_scheduled_rounds": ideal_schedule.scheduled_rounds,
            "loads": sensitivity_schedule.loads,
            "stores": sensitivity_schedule.stores,
            "sensitivity_added_rounds": sensitivity_schedule.added_rounds,
            "sensitivity_scheduled_rounds": sensitivity_schedule.scheduled_rounds,
            "strict_executable": sensitivity_schedule.strict_executable,
        }
    return {
        "evidence_status": "CHECK",
        "qualification": (
            "One-round no-prefetch/no-compute-overlap transfer sensitivity; "
            "not a QEC-native runtime"
        ),
        "widths": results,
    }


def main() -> None:
    _verify_source_checkout()
    sys.path.insert(0, str(SOURCE_PACKAGE))
    project_commit = _git("rev-parse", "HEAD", repository=PROJECT_ROOT)
    project_status = _git("status", "--porcelain", repository=PROJECT_ROOT)
    result = {
        "assumptions": {
            "factory": "ideal supply inherited from the reviewed adaptive-PBC baseline",
            "fixed_event_order": True,
            "memory_copy_semantics": "one usable logical-state location at a time",
            "overlap_policy": "no_prefetch_no_compute_overlap_v1",
            "scratch_slots": 1,
        },
        "experiment_id": EXPERIMENT_ID,
        "legacy_partition_reference": _legacy_reference_results(),
        "pbc_io_sensitivity": _pbc_results(),
        "project_commit": project_commit,
        "project_worktree": {
            "status": "dirty" if project_status else "clean",
            "status_sha256": hashlib.sha256(project_status.encode()).hexdigest(),
        },
        "random_seed": None,
        "software_environment": {
            "platform": platform.platform(),
            "python": sys.version,
        },
        "source_bindings": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "source_repository": {
            "commit": SOURCE_COMMIT,
            "path_role": "read-only generation and import-provenance source",
        },
        "task_id": TASK_ID,
        "validation_status": "generated_after_fail-closed_source_and_reference_checks",
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
