"""Generate the width-256 commutation-aware in-place QCLA study."""

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
from ecdlp_ftqc.circuits import build_qcla_trace
from ecdlp_ftqc.compiler import lower_qcla_to_direct_ccz_events
from ecdlp_ftqc.scheduler import (
    build_width256_ip_commutation_aware_study,
    width256_ip_commutation_aware_study_to_data,
)
from ecdlp_ftqc.verification import (
    replay_width256_ip_commutation_aware_study,
    width256_ip_commutation_aware_replay_to_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260907-001"
EXPERIMENT_ID = "E-20260907-001"
CAPABILITY_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
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
    / "width256_ip_commutation_aware_qcla.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "width256_ip_commutation_aware_qcla.py",
    PROJECT_ROOT / "docs" / "WIDTH256_IP_COMMUTATION_AWARE_QCLA_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260907-001.yaml",
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


def _maximum(levels: list[dict[str, Any]], field: str) -> int:
    return max(int(item[field]) for item in levels)


def main() -> None:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    source = build_qcla_trace(256)
    events = lower_qcla_to_direct_ccz_events(source, capability)
    study = build_width256_ip_commutation_aware_study(events)
    study_data = width256_ip_commutation_aware_study_to_data(study)
    replay = replay_width256_ip_commutation_aware_study(study_data, events)
    if not replay.all_passed:
        raise RuntimeError("independent width-256 IP replay failed")
    replay_data = width256_ip_commutation_aware_replay_to_data(replay)
    levels = study_data["candidate_levels"]
    macro_layers = study_data["macro_layers"]
    if not isinstance(levels, list) or not isinstance(macro_layers, list):
        raise TypeError("study level serialization is invalid")
    bounded_levels = sum(
        item["possible_support_exact"] is False for item in levels
    )
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "inplace_result": {
            "candidate_levels": study.direct_ccz_candidate_levels,
            "coherent_cleanup_ccx_count": study.coherent_cleanup_ccx_count,
            "critical_path_source_gate_ids": list(
                study.critical_path_source_gate_ids
            ),
            "macro_depth": study.macro_depth,
            "macro_layer_event_counts": [len(item) for item in macro_layers],
            "reduction_from_source_candidate_levels": (
                study.source_aligned_candidate_levels
                - study.direct_ccz_candidate_levels
            ),
            "reduction_from_source_macro_depth": (
                study.source_toffoli_bearing_layers - study.macro_depth
            ),
            "status": "PROVED_within_logical_candidate_model",
        },
        "logical_demand": {
            "ccz_resource_state_total": study.source_ccx_count,
            "clifford_layer_demands": [
                list(item) for item in study.source_clifford_layer_demands
            ],
            "maximum_ccz_burst": study.peak_fresh_ccz_resource_count,
            "maximum_parallel_distinct_target_h": (
                study.peak_distinct_target_h_count
            ),
            "ppm_total": 6 * study.source_ccx_count,
            "source_ancilla_values": study.live_ancillas.source_ancilla_values,
            "source_fully_resident_values": (
                study.live_ancillas.fully_resident_source_values
            ),
            "target_h_total": study.total_target_h_count,
        },
        "native_backend": {
            "complete_native_schedule": False,
            "failure_probability": None,
            "native_cycles": None,
            "physical_qubits": None,
            "runtime_seconds": None,
        },
        "pair_oracle": study_data["pair_oracle"],
        "source_aligned_baseline": {
            "candidate_levels": study.source_aligned_candidate_levels,
            "ccx_count": study.source_ccx_count,
            "macro_depth": study.source_toffoli_bearing_layers,
        },
        "support_envelopes": {
            "bounded_level_count": bounded_levels,
            "coordinate": "logical_support_hypergraph_not_native_geometry",
            "deterministic_branch_sample_count": 512,
            "deterministic_branch_sample_seed": (
                "T-20260903-002-support-witnesses-v1"
            ),
            "maximum_may_contact_count": _maximum(
                levels, "maximum_may_contact_count"
            ),
            "maximum_may_support_union_upper_bound_size": _maximum(
                levels, "may_support_union_upper_bound_size"
            ),
            "maximum_ppm_weight_upper_bound": _maximum(
                levels, "maximum_ppm_weight_upper_bound"
            ),
            "maximum_sampled_branch_weight": _maximum(
                levels, "maximum_sampled_branch_weight"
            ),
            "maximum_witnessed_contact_count": _maximum(
                levels, "maximum_witnessed_contact_count"
            ),
            "maximum_witnessed_support_union_lower_bound_size": _maximum(
                levels, "witnessed_support_union_lower_bound_size"
            ),
            "may_union_is_simultaneous_branch_weight": False,
            "status": study.support_envelope_status.value,
            "total_unwitnessed_may_incidence_count": sum(
                int(item["unwitnessed_may_incidence_count"])
                for item in levels
            ),
        },
        "task_id": TASK_ID,
        "validation_status": (
            "passed_full_pair_small_width_arithmetic_support_liveness_and_"
            "independent_replay"
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
            "distinct_target_h_count": item["distinct_target_h_count"],
            "evidence_status": item["evidence_status"],
            "logical_ppm_count": item["logical_ppm_count"],
            "macro_layer": item["macro_layer"],
            "maximum_may_contact_count": item["maximum_may_contact_count"],
            "maximum_ppm_weight_upper_bound": item[
                "maximum_ppm_weight_upper_bound"
            ],
            "maximum_sampled_branch_weight": item[
                "maximum_sampled_branch_weight"
            ],
            "maximum_witnessed_contact_count": item[
                "maximum_witnessed_contact_count"
            ],
            "may_support_union_upper_bound_size": item[
                "may_support_union_upper_bound_size"
            ],
            "possible_support_exact": item["possible_support_exact"],
            "source_algorithmic_layer_max": item[
                "source_algorithmic_layer_max"
            ],
            "source_algorithmic_layer_min": item[
                "source_algorithmic_layer_min"
            ],
            "unwitnessed_may_incidence_count": item[
                "unwitnessed_may_incidence_count"
            ],
            "witnessed_support_union_lower_bound_size": item[
                "witnessed_support_union_lower_bound_size"
            ],
        }
        for item in levels
    ]
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    primary = {
        "independent_replay.json": replay_data,
        "level_envelopes.json": level_table,
        "summary.json": summary,
        "width256_ip_study.json": study_data,
    }
    for name, value in primary.items():
        _write_json(OUTPUT_ROOT / name, value)
    reproducibility = {
        "command": (
            "uv --native-tls run python "
            "scripts/run_width256_ip_commutation_aware_qcla_cycle.py"
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
        "random_seed": "T-20260903-002-support-witnesses-v1",
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
