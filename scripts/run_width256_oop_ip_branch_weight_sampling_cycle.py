"""Generate the shared width-256 OOP/IP branch-weight sampling study."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.compiler import (
    lower_oop_qcla_to_direct_ccz_events,
    lower_qcla_to_direct_ccz_events,
)
from ecdlp_ftqc.scheduler import (
    build_width256_commutation_aware_study,
    build_width256_ip_commutation_aware_study,
    build_width256_oop_ip_branch_weight_study,
    width256_oop_ip_branch_weight_study_to_data,
)
from ecdlp_ftqc.verification import (
    replay_width256_oop_ip_branch_weight_study,
    width256_oop_ip_branch_weight_replay_to_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260907-002"
EXPERIMENT_ID = "E-20260907-002"
CAPABILITY_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "scheduler"
    / "direct_ccz_ppm_support_certificate.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "scheduler"
    / "width256_commutation_aware_qcla.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "scheduler"
    / "width256_ip_commutation_aware_qcla.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "scheduler"
    / "width256_oop_ip_branch_weight_sampling.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "width256_oop_ip_branch_weight_sampling.py",
    PROJECT_ROOT / "docs" / "WIDTH256_OOP_IP_BRANCH_WEIGHT_SAMPLING_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260907-002.yaml",
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


def _level_statistics(variant: dict[str, Any]) -> list[dict[str, Any]]:
    levels = variant["levels"]
    if not isinstance(levels, list):
        raise TypeError("variant levels are not serialized as a list")
    return [
        {
            key: value
            for key, value in level.items()
            if key != "branch_maximum_weights"
        }
        for level in levels
    ]


def _hotspot(levels: list[dict[str, Any]], field: str) -> dict[str, object]:
    maximum = max(int(level[field]) for level in levels)
    return {
        "candidate_levels": [
            int(level["candidate_level"])
            for level in levels
            if int(level[field]) == maximum
        ],
        "value": maximum,
    }


def _variant_summary(variant: dict[str, Any]) -> dict[str, object]:
    levels = _level_statistics(variant)
    z_levels = [level for level in levels if level["axis"] == "Z"]
    return {
        "arithmetic_contract": variant["arithmetic_contract"],
        "candidate_level_count": variant["candidate_level_count"],
        "direct_ccz_event_count": variant["direct_ccz_event_count"],
        "evaluated_branch_ppm_instance_count": variant[
            "evaluated_branch_ppm_instance_count"
        ],
        "global_sampled_maximum": variant["global_sampled_maximum"],
        "global_support_weight_upper_bound": variant[
            "global_support_weight_upper_bound"
        ],
        "hashed_branch_maximum_hotspot": _hotspot(
            z_levels, "hashed_branch_maximum"
        ),
        "macro_depth": variant["macro_depth"],
        "maximum_level_sampled_to_upper_gap": variant[
            "maximum_level_sampled_to_upper_gap"
        ],
        "p50_hotspot": _hotspot(z_levels, "p50"),
        "p95_hotspot": _hotspot(z_levels, "p95"),
        "p99_hotspot": _hotspot(z_levels, "p99"),
        "ppm_count": variant["ppm_count"],
        "sampled_maximum_hotspot": _hotspot(z_levels, "sampled_maximum"),
        "support_upper_hotspot": _hotspot(
            z_levels, "support_weight_upper_bound"
        ),
    }


def main() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    oop_source = build_oop_qcla_trace(256)
    oop_events = lower_oop_qcla_to_direct_ccz_events(oop_source, capability)
    oop_reviewed = build_width256_commutation_aware_study(oop_events)
    ip_source = build_qcla_trace(256)
    ip_events = lower_qcla_to_direct_ccz_events(ip_source, capability)
    ip_reviewed = build_width256_ip_commutation_aware_study(ip_events)
    study = build_width256_oop_ip_branch_weight_study(
        oop_source=oop_source,
        oop_events=oop_events,
        oop_study=oop_reviewed,
        ip_source=ip_source,
        ip_events=ip_events,
        ip_study=ip_reviewed,
    )
    study_data = width256_oop_ip_branch_weight_study_to_data(study)
    replay = replay_width256_oop_ip_branch_weight_study(
        study_data,
        oop_source=oop_source,
        oop_events=oop_events,
        ip_source=ip_source,
        ip_events=ip_events,
    )
    if not replay.all_passed:
        raise RuntimeError("independent OOP/IP branch-weight replay failed")

    oop_data = study_data["oop"]
    ip_data = study_data["ip"]
    if not isinstance(oop_data, dict) or not isinstance(ip_data, dict):
        raise TypeError("variant serialization is invalid")
    level_quantiles = {
        "coordinate": study.oop.levels[0].coordinate,
        "experiment_id": EXPERIMENT_ID,
        "ip": _level_statistics(ip_data),
        "oop": _level_statistics(oop_data),
        "quantile_method": study.oop.levels[0].quantile_method,
        "sample_count": study.sample_count,
        "sample_seed": study.sample_seed,
        "task_id": TASK_ID,
    }
    summary = {
        "comparison": {
            "ip": _variant_summary(ip_data),
            "oop": _variant_summary(oop_data),
        },
        "evidence": {
            "phase_one_branch_statistics": "NUMERICAL",
            "phase_two_fresh_resource_x_weight": "PROVED",
            "sampled_maximum_is_global_true_maximum": False,
        },
        "experiment_id": EXPERIMENT_ID,
        "native_backend": {
            "complete_native_schedule": False,
            "failure_probability": None,
            "native_cycles": None,
            "physical_qubits": None,
            "runtime_seconds": None,
        },
        "protocol": {
            "coordinate": study.oop.levels[0].coordinate,
            "quantile_method": study.oop.levels[0].quantile_method,
            "sample_count": study.sample_count,
            "forced_boundary_branch_count": 2,
            "hashed_branch_sample_count": study.sample_count - 2,
            "sample_seed": study.sample_seed,
            "total_evaluated_branch_ppm_instance_count": (
                study.total_evaluated_branch_ppm_instance_count
            ),
            "total_sampled_level_values_independently_replayed": (
                replay.total_sampled_level_values_checked
            ),
        },
        "task_id": TASK_ID,
        "validation_status": (
            "passed_complete_vector_scalar_replay_quantile_hash_bound_"
            "x_phase_and_fail_closed_native_checks"
        ),
    }
    primary = {
        "branch_weight_study.json": study_data,
        "independent_replay.json": (
            width256_oop_ip_branch_weight_replay_to_data(replay)
        ),
        "level_quantiles.json": level_quantiles,
        "summary.json": summary,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, value in primary.items():
        _write_json(OUTPUT_ROOT / name, value)
    reproducibility = {
        "command": (
            "uv --native-tls run python "
            "scripts/run_width256_oop_ip_branch_weight_sampling_cycle.py"
        ),
        "experiment_id": EXPERIMENT_ID,
        "git_branch": _git("branch", "--show-current"),
        "git_head": _git("rev-parse", "HEAD"),
        "input_circuits": [oop_source.trace_id, ip_source.trace_id],
        "input_configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "output_sha256": {
            name: _sha256(OUTPUT_ROOT / name) for name in sorted(primary)
        },
        "random_seed": study.sample_seed,
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
        "working_tree_state_excluding_outputs_and_unrelated_claude": (
            _filtered_worktree_status()
        ),
    }
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)


if __name__ == "__main__":
    main()
