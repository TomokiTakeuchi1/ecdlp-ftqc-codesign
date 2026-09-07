"""Generate the compact width-256 commutation-aware OOP-QCLA study."""

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
from ecdlp_ftqc.circuits import build_oop_qcla_trace
from ecdlp_ftqc.compiler import lower_oop_qcla_to_direct_ccz_events
from ecdlp_ftqc.scheduler import (
    build_width256_commutation_aware_study,
    width256_commutation_aware_study_to_data,
)
from ecdlp_ftqc.verification import (
    replay_width256_commutation_aware_study,
    width256_commutation_aware_replay_to_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260906-004"
EXPERIMENT_ID = "E-20260906-004"
CAPABILITY_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
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
    / "verification"
    / "width256_commutation_aware_qcla.py",
    PROJECT_ROOT / "docs" / "WIDTH256_COMMUTATION_AWARE_QCLA_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260906-004.yaml",
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


def _level_maximum(levels: list[dict[str, Any]], field: str) -> int:
    return max(int(item[field]) for item in levels)


def main() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    source = build_oop_qcla_trace(256)
    events = lower_oop_qcla_to_direct_ccz_events(source, capability)
    study = build_width256_commutation_aware_study(events)
    study_data = width256_commutation_aware_study_to_data(study)
    replay = replay_width256_commutation_aware_study(study_data, events)
    if not replay.all_passed:
        raise RuntimeError("independent width-256 replay failed")
    replay_data = width256_commutation_aware_replay_to_data(replay)

    unitary = study_data["unitary"]
    measured = study_data["measured_cleanup"]
    if not isinstance(unitary, dict) or not isinstance(measured, dict):
        raise TypeError("variant serialization is not a mapping")
    levels = unitary["candidate_levels"]
    cleanups = measured["cleanup_certificates"]
    if not isinstance(levels, list) or not isinstance(cleanups, list):
        raise TypeError("level or cleanup serialization is not a list")
    macro_layers = unitary["macro_layers"]
    if not isinstance(macro_layers, list):
        raise TypeError("macro-layer serialization is not a list")
    summary = {
        "cleanup_gate": {
            "admitted_cleanup_count": 0,
            "fallback_variant": "commutation_aware_unitary",
            "maximum_later_ccx_count_after_source_cleanup": max(
                int(item["later_ppm_count"]) for item in cleanups
            ),
            "mixed_axis_witness_count": len(cleanups),
            "proposed_cleanup_count": len(cleanups),
            "reason": (
                "a surviving conditional control-control CZ presents logical "
                "X(p) as branch-dependent X(p)Z(q); later PPM frame propagation "
                "is also required"
            ),
            "status": "FALSIFIED_for_current_Z_X_only_high_rate_family",
        },
        "experiment_id": EXPERIMENT_ID,
        "logical_demand": {
            "ccz_resource_state_total": study.source_ccx_count,
            "cnot_layer_demands": [list(item) for item in study.source_cnot_layer_demands],
            "maximum_ccz_burst": _level_maximum(levels, "direct_ccz_event_count"),
            "maximum_parallel_unique_target_h": _level_maximum(
                levels, "unique_target_h_count"
            ),
            "ppm_total": 6 * study.source_ccx_count,
        },
        "native_backend": {
            "complete_native_schedule": False,
            "failure_probability": None,
            "native_cycles": None,
            "physical_qubits": None,
            "runtime_seconds": None,
        },
        "pair_oracle": unitary["pair_oracle"],
        "source_aligned_baseline": {
            "candidate_levels": study.source_aligned_candidate_levels,
            "ccx_count": study.source_ccx_count,
            "macro_depth": study.source_toffoli_bearing_layers,
        },
        "support_envelopes": {
            "coordinate": "logical_support_hypergraph_not_native_geometry",
            "maximum_possible_contact_count": _level_maximum(
                levels, "maximum_possible_contact_count"
            ),
            "maximum_possible_support_union_size": _level_maximum(
                levels, "possible_support_union_size"
            ),
            "maximum_ppm_weight_upper_bound": _level_maximum(
                levels, "maximum_ppm_weight_upper_bound"
            ),
            "possible_union_is_simultaneous_weight": False,
        },
        "task_id": TASK_ID,
        "unitary_selected_result": {
            "candidate_levels": unitary["direct_ccz_candidate_levels"],
            "ccx_count": unitary["scheduled_ccx_count"],
            "critical_path_source_gate_ids": unitary[
                "critical_path_source_gate_ids"
            ],
            "macro_depth": unitary["macro_depth"],
            "macro_layer_event_counts": [len(item) for item in macro_layers],
            "peak_live_source_values": unitary["live_values"][
                "peak_live_source_values"
            ],
            "reduction_from_source_candidate_levels": (
                study.source_aligned_candidate_levels
                - int(unitary["direct_ccz_candidate_levels"])
            ),
            "reduction_from_source_macro_depth": (
                study.source_toffoli_bearing_layers - int(unitary["macro_depth"])
            ),
            "status": "PROVED_within_logical_candidate_model",
        },
        "validation_status": (
            "passed_compact_full_pair_support_cleanup_lifetime_and_independent_replay"
        ),
    }
    level_table = [
        {
            "axis": item["axis"],
            "branch_dependent_profile_count": item[
                "branch_dependent_profile_count"
            ],
            "candidate_level": item["candidate_level"],
            "direct_ccz_event_count": item["direct_ccz_event_count"],
            "logical_ppm_count": item["logical_ppm_count"],
            "macro_layer": item["macro_layer"],
            "maximum_possible_contact_count": item[
                "maximum_possible_contact_count"
            ],
            "maximum_ppm_weight_upper_bound": item[
                "maximum_ppm_weight_upper_bound"
            ],
            "possible_support_union_size": item["possible_support_union_size"],
            "unique_target_h_count": item["unique_target_h_count"],
        }
        for item in levels
    ]

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    primary = {
        "independent_replay.json": replay_data,
        "level_envelopes.json": level_table,
        "summary.json": summary,
        "width256_study.json": study_data,
    }
    for name, value in primary.items():
        _write_json(OUTPUT_ROOT / name, value)

    source_hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in SOURCE_BINDINGS
    }
    reproducibility = {
        "command": (
            "uv --native-tls run python "
            "scripts/run_width256_commutation_aware_qcla_cycle.py"
        ),
        "experiment_id": EXPERIMENT_ID,
        "git_branch": _git("branch", "--show-current"),
        "git_head": _git("rev-parse", "HEAD"),
        "input_circuit": source.trace_id,
        "input_configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "output_sha256": {
            name: _sha256(OUTPUT_ROOT / name) for name in sorted(primary)
        },
        "random_seed": None,
        "software_environment": {
            "numpy": importlib.metadata.version("numpy"),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "pyyaml": importlib.metadata.version("pyyaml"),
        },
        "source_binding_sha256": source_hashes,
        "task_id": TASK_ID,
        "validation_status": summary["validation_status"],
        "working_tree_state_excluding_outputs_and_unrelated_claude": (
            _filtered_worktree_status()
        ),
    }
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)


if __name__ == "__main__":
    main()
