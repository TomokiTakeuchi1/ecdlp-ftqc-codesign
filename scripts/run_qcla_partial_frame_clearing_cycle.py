"""Generate the partial Clifford-frame clearing comparison artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecdlp_ftqc.analysis.qcla_partial_frame_clearing import (
    FramePolicy,
    build_partial_frame_clearing_study,
    partial_frame_clearing_study_to_data,
)
from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_qcla_trace
from ecdlp_ftqc.compiler import lower_qcla_to_direct_ccz_events
from ecdlp_ftqc.verification.qcla_partial_frame_clearing import (
    partial_frame_clearing_replay_to_data,
    replay_partial_frame_clearing_studies,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260909-001"
EXPERIMENT_ID = "E-20260909-001"
CAPABILITY_PATH = (
    PROJECT_ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
WIDTH5_SAMPLE_COUNT = 16
WIDTH256_SAMPLE_COUNT = 32
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "analysis" / "qcla_partial_frame_clearing.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz_ppm.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "verification" / "qcla_partial_frame_clearing.py",
    PROJECT_ROOT / "docs" / "PARTIAL_CLIFFORD_FRAME_CLEARING_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260909-001.yaml",
    CAPABILITY_PATH,
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
    return "\n".join(
        line
        for line in _git("status", "--porcelain").splitlines()
        if not line.startswith("?? .claude/")
        and f"experiments/runs/{TASK_ID}/" not in line.replace("\\", "/")
    )


def _distribution_headline(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        key: raw[key]
        for key in (
            "minimum",
            "p50",
            "p95",
            "p99",
            "maximum",
            "all_zero_branch",
            "all_one_branch",
            "sha256",
        )
    }


def _policy_summary(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_ppm_levels": raw["candidate_ppm_levels"],
        "complete_native_schedule": False,
        "literal_cnot_batches": _distribution_headline(raw["literal_cnot_batches"]),
        "literal_cnot_occurrences": _distribution_headline(raw["literal_cnot_occurrences"]),
        "literal_h_batches": raw["literal_h_batches"],
        "literal_two_qubit_batches": _distribution_headline(raw["literal_two_qubit_batches"]),
        "maximum_frame_primitive_count": _distribution_headline(
            raw["maximum_frame_primitive_count"]
        ),
        "maximum_presented_ppm_weight": _distribution_headline(raw["maximum_presented_ppm_weight"]),
        "final_frame_primitive_count": _distribution_headline(raw["final_frame_primitive_count"]),
        "incompatible_phase_one_ppm_count": _distribution_headline(
            raw["incompatible_phase_one_ppm_count"]
        ),
        "native_scheduled_depth": None,
        "runtime_seconds": None,
        "serialized_logical_layer_envelope": _distribution_headline(
            raw["serialized_logical_layer_envelope"]
        ),
        "z_x_only_high_rate_family_admitted": raw["z_x_only_high_rate_family_admitted"],
        "y_containing_phase_one_ppm_count": _distribution_headline(
            raw["y_containing_phase_one_ppm_count"]
        ),
    }


def _percent_reduction(candidate: int, baseline: int) -> float:
    return 100.0 * (baseline - candidate) / baseline if baseline else 0.0


def main() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    studies = []
    traces = []
    for width, sample_count in ((5, WIDTH5_SAMPLE_COUNT), (256, WIDTH256_SAMPLE_COUNT)):
        trace = build_qcla_trace(width)
        events = lower_qcla_to_direct_ccz_events(trace, capability)
        study = build_partial_frame_clearing_study(
            trace,
            events,
            branch_sample_count=sample_count,
        )
        traces.append(trace.trace_id)
        studies.append(partial_frame_clearing_study_to_data(study))

    replay = replay_partial_frame_clearing_studies(studies)
    if not replay.all_passed:
        raise RuntimeError("independent partial-frame replay failed")

    width256 = studies[1]
    policies = {row["policy"]: row for row in width256["policies"]}
    partial = policies[FramePolicy.PARTIAL_CLEARING.value]
    complete = policies[FramePolicy.FULL_CLEARING.value]
    conjugated = policies[FramePolicy.FULL_CONJUGATION.value]
    partial_cnot_p50 = int(partial["literal_cnot_occurrences"]["p50"])
    complete_cnot_p50 = int(complete["literal_cnot_occurrences"]["p50"])
    summary = {
        "comparison": {
            "full_clearing_to_partial_cnot_p50_reduction_percent": (
                _percent_reduction(partial_cnot_p50, complete_cnot_p50)
            ),
            "partial_cnot_count_does_not_imply_depth_reduction": True,
            "partial_maximum_sampled_ppm_weight": partial["maximum_presented_ppm_weight"][
                "maximum"
            ],
            "retained_frame_baseline_maximum_sampled_ppm_weight": conjugated[
                "maximum_presented_ppm_weight"
            ]["maximum"],
        },
        "evidence": {
            "component_factorization_and_commutation": "PROVED",
            "width5_exact_projective_replay": "NUMERICAL",
            "width256_branch_profiles": "NUMERICAL",
            "native_schedule_runtime_or_space": "OPEN",
        },
        "experiment_id": EXPERIMENT_ID,
        "limitations": {
            "literal_generator_counts_are_minimal_clifford_synthesis": False,
            "logical_asap_envelope_is_native_surgery_depth": False,
            "sample_is_population_distribution": False,
        },
        "native_backend": {
            "complete_native_schedule": False,
            "failure_probability": None,
            "native_cycles": None,
            "physical_qubits": None,
            "runtime_seconds": None,
        },
        "task_id": TASK_ID,
        "validation_status": (
            "passed_width5_three_identity_projective_replay_and_independent_"
            "width5_width256_structure_distribution_fail_closed_checks"
        ),
        "width256": {
            "branch_sample_count": width256["branch_sample_count"],
            "macro_depth": width256["macro_depth"],
            "macro_layer_sizes": width256["macro_layer_sizes"],
            "policies": {name: _policy_summary(row) for name, row in sorted(policies.items())},
            "source_ccx_count": sum(width256["macro_layer_sizes"]),
        },
        "width5": {
            "branch_sample_count": studies[0]["branch_sample_count"],
            "macro_depth": studies[0]["macro_depth"],
            "macro_layer_sizes": studies[0]["macro_layer_sizes"],
            "projective_clifford_checks": studies[0]["width5_projective_clifford_checks"],
            "projective_clifford_mismatches": studies[0]["width5_projective_clifford_mismatches"],
        },
    }
    primary = {
        "independent_replay.json": partial_frame_clearing_replay_to_data(replay),
        "studies.json": studies,
        "summary.json": summary,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, value in primary.items():
        _write_json(OUTPUT_ROOT / name, value)

    reproducibility = {
        "command": ("uv --native-tls run python scripts/run_qcla_partial_frame_clearing_cycle.py"),
        "experiment_id": EXPERIMENT_ID,
        "git_branch": _git("branch", "--show-current"),
        "git_head": _git("rev-parse", "HEAD"),
        "input_circuits": traces,
        "input_configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "output_sha256": {name: _sha256(OUTPUT_ROOT / name) for name in sorted(primary)},
        "random_seed": width256["branch_sample_seed"],
        "sample_counts": {"width5": WIDTH5_SAMPLE_COUNT, "width256": WIDTH256_SAMPLE_COUNT},
        "software_environment": {
            "numpy": importlib.metadata.version("numpy"),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "pyyaml": importlib.metadata.version("pyyaml"),
        },
        "source_binding_sha256": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "task_id": TASK_ID,
        "validation_status": summary["validation_status"],
        "working_tree_state_excluding_outputs_and_unrelated_claude": (_filtered_worktree_status()),
    }
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)


if __name__ == "__main__":
    main()
