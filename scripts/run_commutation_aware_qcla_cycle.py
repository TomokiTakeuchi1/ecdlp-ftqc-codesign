"""Generate the exact small-width commutation-aware QCLA study artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecdlp_ftqc.scheduler import (
    build_small_width_commutation_aware_study,
    small_width_commutation_aware_study_to_data,
)
from ecdlp_ftqc.verification import (
    commutation_aware_qcla_replay_to_data,
    replay_small_width_commutation_aware_study,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260906-003"
EXPERIMENT_ID = "E-20260906-003"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "joint_direct_ccz.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "commutation_aware_qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "verification" / "commutation_aware_qcla.py",
    PROJECT_ROOT / "docs" / "COMMUTATION_AWARE_QCLA_SCHEDULING_CONTRACT.md",
    PROJECT_ROOT / "docs" / "JOINT_CCX_QCLA_REEVALUATION_CYCLE.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260906-003.yaml",
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
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _filtered_worktree_status() -> str:
    lines = _git("status", "--porcelain").splitlines()
    return "\n".join(
        line
        for line in lines
        if not line.startswith("?? .claude/")
        and f"experiments/runs/{TASK_ID}/" not in line.replace("\\", "/")
    )


def main() -> None:
    study = build_small_width_commutation_aware_study()
    study_data = small_width_commutation_aware_study_to_data(study)
    replay = replay_small_width_commutation_aware_study(study_data)
    replay_data = commutation_aware_qcla_replay_to_data(replay)
    if not replay.all_passed:
        raise RuntimeError("small-width commutation-aware independent replay failed")

    exact_table = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "coordinate": (
            "architecture-independent two-phase direct-CCZ candidate levels; "
            "not cycles or time"
        ),
        "columns": [
            "width",
            "source_ccx_count",
            "source_toffoli_bearing_layers",
            "source_aligned_candidate_levels",
            "unitary_macro_depth",
            "unitary_candidate_levels",
            "measured_scheduled_ccx_count",
            "measurement_cleanup_count",
            "measured_macro_depth",
            "measured_candidate_levels",
        ],
        "rows": [
            [
                row.width,
                row.source_ccx_count,
                row.source_toffoli_bearing_layers,
                row.source_aligned_candidate_levels,
                row.unitary.macro_depth,
                row.unitary.direct_ccz_candidate_levels,
                row.measured_cleanup.scheduled_ccx_count,
                row.measured_cleanup.measured_cleanup_count,
                row.measured_cleanup.macro_depth,
                row.measured_cleanup.direct_ccz_candidate_levels,
            ]
            for row in replay.width_summaries
        ],
        "unitary_optimality_status": "PROVED_IN_STATED_LOGICAL_MODEL",
        "measured_semantic_status": "NUMERICAL_EXHAUSTIVE_WIDTHS_2_THROUGH_8",
        "reaction_frontier_status": "CHECK_CONSERVATIVE_ALL_OUTCOMES",
    }
    width5 = study_data["comparisons"][3]
    width5_witness = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "width": 5,
        "source_trace_id": width5["source_trace_id"],
        "source_trace_sha256": width5["source_trace_sha256"],
        "source_aligned_macro_layers": width5["source_aligned_macro_layers"],
        "source_clifford_barriers": width5["source_clifford_barriers"],
        "unitary": width5["unitary"],
        "measured_cleanup": width5["measured_cleanup"],
    }
    summary = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "widths": list(replay.widths_checked),
        "headline_table": exact_table["rows"],
        "width5": {
            "source_aligned_candidate_levels": (
                replay.width5_source_aligned_candidate_levels
            ),
            "unitary_macro_depth": replay.width5_unitary_macro_depth,
            "unitary_candidate_levels": replay.width5_unitary_candidate_levels,
            "measured_macro_depth": replay.width5_measured_macro_depth,
            "measured_candidate_levels": replay.width5_measured_candidate_levels,
        },
        "depth_reduction_widths": [5, 7],
        "no_cleanup_depth_reduction_widths": [2, 3, 4, 6, 8],
        "independent_replay": {
            "pair_decisions_checked": replay.total_pair_decisions_checked,
            "pair_truth_table_rows_checked": (
                replay.total_pair_truth_table_rows_checked
            ),
            "arithmetic_inputs_checked": replay.total_arithmetic_inputs_checked,
            "measurement_branch_columns_checked": (
                replay.total_measurement_branch_columns_checked
            ),
            "phase_sensitive_relative_pairs_checked": (
                replay.total_phase_sensitive_relative_pairs_checked
            ),
            "all_passed": replay.all_passed,
        },
        "claims": {
            "macro_depth": (
                "PROVED only in the complete pairwise logical dependency model "
                "defined by the scheduling contract"
            ),
            "measurement_cleanup": (
                "NUMERICAL exhaustive basis and phase-sensitive replay at widths 2--8"
            ),
            "reaction_frontiers": (
                "CHECK conservative six-outcome frontier per predecessor CCX; "
                "minimal outcome subset and duration unresolved"
            ),
        },
        "finite_outputs": {
            "complete_native_schedule": False,
            "native_cycles": None,
            "runtime_seconds": None,
            "physical_qubits": None,
            "failure_probability": None,
        },
        "validation_status": "passed_independent_replay",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, object] = {
        "small_width_study.json": study_data,
        "exact_schedule_table.json": exact_table,
        "width5_schedule_witness.json": width5_witness,
        "independent_replay.json": replay_data,
        "summary.json": summary,
    }
    for filename, value in artifacts.items():
        _write_json(OUTPUT_ROOT / filename, value)
    reproducibility: dict[str, Any] = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("branch", "--show-current"),
        "working_tree_state": _filtered_worktree_status(),
        "input_circuit": "clean OOP-QCLA source traces widths 2--8",
        "configuration": None,
        "code_assumptions": [
            "A-0030",
            "A-0032",
            "A-0036",
            "A-0039",
            "A-0046",
            "A-0047",
        ],
        "architecture_assumptions": (
            "unlimited-capacity logical two-phase direct-CCZ candidate levels; "
            "source CNOT barriers retained; no native backend admitted"
        ),
        "random_seed": None,
        "software_environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "package": importlib.metadata.version("ecdlp-ftqc"),
        },
        "source_sha256": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "output_sha256": {
            filename: _sha256(OUTPUT_ROOT / filename) for filename in artifacts
        },
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "validation_status": "passed_independent_replay",
    }
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
