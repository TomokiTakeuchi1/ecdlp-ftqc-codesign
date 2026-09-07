"""Generate the width-5 joint direct-CCZ validation artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecdlp_ftqc.circuits import build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    build_width5_joint_ccx_validation_plan,
    width5_joint_ccx_validation_plan_to_data,
)
from ecdlp_ftqc.verification import (
    JointInjectionAnchorSummary,
    replay_width5_joint_direct_ccz,
    width5_joint_direct_ccz_replay_to_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260906-002"
EXPERIMENT_ID = "E-20260906-002"
WIDTH = 5
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "joint_direct_ccz.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "verification" / "joint_direct_ccz.py",
    PROJECT_ROOT / "docs" / "JOINT_DIRECT_CCZ_WIDTH5_CONTRACT.md",
    PROJECT_ROOT / "docs" / "JOINT_CCX_QCLA_REEVALUATION_CYCLE.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260906-002.yaml",
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
    source = build_oop_qcla_trace(WIDTH)
    plan = build_width5_joint_ccx_validation_plan(source)
    plan_data = width5_joint_ccx_validation_plan_to_data(plan)
    replay = replay_width5_joint_direct_ccz(source, plan_data)
    replay_data = width5_joint_direct_ccz_replay_to_data(replay)
    if not replay.all_passed:
        raise RuntimeError("width-5 joint direct-CCZ independent replay failed")

    commutation_data = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "width": WIDTH,
        "theorem": (
            "two positive-control CCX gates commute exactly iff neither gate's "
            "target is a control of the other; disjoint, shared-control, and "
            "shared-target pairs are admitted"
        ),
        "all_source_pair_certificates": plan_data["all_pair_certificates"],
        "synthetic_overlap_certificates": plan_data[
            "synthetic_overlap_certificates"
        ],
        "source_pair_count": replay.all_source_pair_count,
        "commuting_source_pair_count": replay.commuting_source_pair_count,
        "noncommuting_source_pair_count": replay.noncommuting_source_pair_count,
        "truth_table_rows_checked": replay.source_pair_truth_table_rows_checked,
        "evidence_status": "PROVED",
    }
    measurement_data = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "width": WIDTH,
        "record": plan_data["measured_cleanup_candidate"][
            "measurement_uncompute"
        ],
        "verification": replay_data["measurement_uncompute"],
        "channel_statement": (
            "both destructive-X outcomes produce the same width-5 OOP addition "
            "isometry after the conditional CZ frame update"
        ),
        "evidence_status": "NUMERICAL",
    }
    summary = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "width": WIDTH,
        "source_trace_id": source.trace_id,
        "baseline": plan_data["baseline"],
        "commutation": {
            "source_pair_count": replay.all_source_pair_count,
            "commuting_pair_count": replay.commuting_source_pair_count,
            "noncommuting_pair_count": replay.noncommuting_source_pair_count,
            "synthetic_overlap_cases": replay.synthetic_overlap_cases_checked,
            "synthetic_noncommuting_witnesses": (
                replay.synthetic_noncommuting_witnesses
            ),
            "evidence_status": "PROVED",
        },
        "joint_injection": {
            "unitary_macro_layer_sizes": [
                len(item.operations) for item in plan.unitary_macro_layers
            ],
            "admitted_macro_pairs": replay.admitted_macro_pair_count,
            "common_incoming_frame_rule": (
                "all event PPMs are presented relative to one macro-layer-entry "
                "Clifford frame; canonical Z/CZ and post-H Z-control/X-target "
                "primitives commute across every admitted pair, so each joint "
                "branch factorizes into the product of verified single-event branches"
            ),
            "factorization_proofs": replay.common_frame_factorization_proofs,
            "factorized_two_event_branches_covered": (
                replay.factorized_two_event_branches_covered
            ),
            "single_event_branches_checked": replay.single_event_branches_checked,
            "shared_control_statevector_anchor": asdict_anchor(
                replay.shared_control_anchor
            ),
            "shared_target_statevector_anchor": asdict_anchor(
                replay.shared_target_anchor
            ),
            "event_to_event_reaction_edges": (
                replay.event_to_event_reaction_edge_count
            ),
            "evidence_status": "NUMERICAL with PROVED structural factorization",
        },
        "measurement_uncompute": measurement_data["verification"],
        "candidates": {
            "unitary": {
                "ccx_count": plan.unitary_candidate_ccx_count,
                "macro_depth": plan.unitary_candidate_macro_depth,
                "two_phase_candidate_levels": plan.unitary_candidate_levels,
                "semantic_status": "ADMITTED_FOR_T-20260906-003",
                "schedule_status": "CHECK_PENDING_DEPENDENCY_MODEL",
            },
            "measured_cleanup": {
                "ccx_count": plan.measured_candidate_ccx_count,
                "macro_depth": plan.measured_candidate_macro_depth,
                "two_phase_candidate_levels": plan.measured_candidate_levels,
                "cleanup_measurement_count": 1,
                "conditional_cz_frame_update_count": 1,
                "semantic_status": "ADMITTED_FOR_T-20260906-003",
                "schedule_status": "CHECK_PENDING_DEPENDENCY_MODEL",
            },
        },
        "finite_outputs": plan_data["finite_outputs"],
        "complete_native_schedule": False,
        "validation_status": "passed_independent_replay",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, object] = {
        "width5_joint_direct_ccz_plan.json": plan_data,
        "commutation_certificates.json": commutation_data,
        "measurement_uncompute_verification.json": measurement_data,
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
        "input_circuit": source.trace_id,
        "configuration": None,
        "code_assumptions": ["A-0030", "A-0032", "A-0036", "A-0046", "A-0047"],
        "architecture_assumptions": (
            "logical two-phase direct-CCZ event only; no native backend admitted"
        ),
        "random_seed": None,
        "software_environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": importlib.metadata.version("numpy"),
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


def asdict_anchor(value: JointInjectionAnchorSummary) -> dict[str, Any]:
    """Serialize a frozen joint-anchor summary without importing dataclasses.asdict."""

    return {
        "basis_columns_per_branch": value.basis_columns_per_branch,
        "branch_anchors_per_pair": value.branch_anchors_per_pair,
        "expected_branch_probability": value.expected_branch_probability,
        "maximum_operator_frobenius_error": value.maximum_operator_frobenius_error,
        "maximum_probability_error": value.maximum_probability_error,
        "overlap_kind": value.overlap_kind,
        "pair_count": value.pair_count,
    }


if __name__ == "__main__":
    main()
