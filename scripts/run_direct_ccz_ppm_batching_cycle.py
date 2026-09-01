"""Generate deterministic Phase-B direct-CCZ PPM batching artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

from ecdlp_ftqc.architectures import (
    direct_ccz_backend_audit_to_data,
    direct_ccz_capability_to_data,
    load_direct_ccz_backend_audit,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import QCLA_SOURCE_PDF_SHA256, build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    dumps_symbolic_direct_ccz_ppm_trace,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.scheduler import (
    analyze_direct_ccz_ppm_batches,
    dumps_phase_b_artifact,
    finite_instance_admission_to_data,
    general_high_rate_candidate_to_data,
    low_rate_fallback_to_data,
    strategy_frontier_to_data,
)
from ecdlp_ftqc.verification import (
    direct_ccz_ppm_batching_replay_to_data,
    replay_direct_ccz_ppm_batching,
    replay_symbolic_direct_ccz_ppm_trace,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260901-007"
EXPERIMENT_ID = "E-20260901-007"
WIDTH = 5
CAPABILITY_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)
BACKEND_AUDIT_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_finite_backend_audit_v1.yaml"
)
DRAPER_PDF = PROJECT_ROOT / "literature" / "papers" / "quant-ph-0406142v1.pdf"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "architectures" / "direct_ccz.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "architectures"
    / "direct_ccz_backend_audit.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz_ppm.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "scheduler"
    / "direct_ccz_ppm_batching.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "direct_ccz_ppm_batching_replay.py",
    PROJECT_ROOT / "docs" / "DIRECT_CCZ_PPM_BATCHING_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260901-007.yaml",
    CAPABILITY_PATH,
    BACKEND_AUDIT_PATH,
    Path(__file__),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest().upper()


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
        and not line.startswith("?? tmp/")
    )


def _verify_source_hashes() -> dict[str, str]:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    audit = load_direct_ccz_backend_audit(BACKEND_AUDIT_PATH)
    paths = {
        DRAPER_PDF,
        *(PROJECT_ROOT / source.local_pdf for source in capability.sources),
        *(PROJECT_ROOT / source.local_pdf for source in audit.sources),
    }
    hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in sorted(paths)
    }
    draper_key = str(DRAPER_PDF.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if hashes[draper_key] != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("Draper source PDF hash mismatch")
    for source in (*capability.sources, *audit.sources):
        if hashes[source.local_pdf] != source.pdf_sha256.upper():
            raise RuntimeError(f"source PDF hash mismatch: {source.local_pdf}")
    return hashes


def main() -> None:
    source_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    backend_audit = load_direct_ccz_backend_audit(BACKEND_AUDIT_PATH)
    if not capability.event_lowering_admitted:
        raise RuntimeError("single-event semantics are not admitted")
    if capability.high_rate_schedule_admitted or backend_audit.candidate.backend_admitted:
        raise RuntimeError("this negative-admission Phase-B experiment received a finite backend")

    source = build_oop_qcla_trace(WIDTH)
    trace = lower_oop_qcla_to_symbolic_direct_ccz_ppm(source, capability)
    trace_data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    phase_a_replay = replay_symbolic_direct_ccz_ppm_trace(source, trace_data)
    if not phase_a_replay.all_passed:
        raise RuntimeError("Phase-A semantic replay failed")

    analysis = analyze_direct_ccz_ppm_batches(trace, capability, backend_audit)
    general_data = general_high_rate_candidate_to_data(analysis.general)
    finite_data = finite_instance_admission_to_data(analysis.finite)
    fallback_data = low_rate_fallback_to_data(analysis.fallback)
    frontier_data = strategy_frontier_to_data(analysis.frontier)
    replay = replay_direct_ccz_ppm_batching(
        trace_data,
        general_data,
        finite_data,
        fallback_data,
        frontier_data,
        direct_ccz_capability_to_data(capability),
        direct_ccz_backend_audit_to_data(backend_audit),
    )
    replay_data = direct_ccz_ppm_batching_replay_to_data(replay)
    if not replay.all_passed:
        raise RuntimeError("independent Phase-B replay failed")

    expected = {
        "anticommuting_pair_count": 30,
        "axis_conflict_pair_count": 30,
        "causal_lower_bound": 12,
        "causal_pair_count": 1206,
        "compatible_overlap_pair_count": 6,
        "conflict_clique_lower_bound": 12,
        "finite_backend_incompatible_field_count": 3,
        "finite_backend_missing_field_count": 13,
        "finite_capability_missing_field_count": 13,
        "low_rate_singleton_count": 60,
        "optimized_candidate_batch_levels": 12,
        "pair_relation_count": 1770,
        "possible_y_ppm_count": 0,
        "reaction_pair_count": 1116,
        "source_layer_candidate_batch_levels": 12,
    }
    for name, expected_value in expected.items():
        if replay_data[name] != expected_value:
            raise RuntimeError(f"unexpected {name}: {replay_data[name]}")
    optimized = analysis.general.optimized_schedule
    if optimized.candidate_batch_level_count != optimized.combined_batch_level_lower_bound:
        raise RuntimeError("candidate construction did not meet the exact lower bound")
    if optimized.complete_native_schedule or analysis.finite.native_schedule_emitted:
        raise RuntimeError("Phase B cannot forge a native schedule")

    summary = {
        "candidate_result": {
            "batch_level_count": optimized.candidate_batch_level_count,
            "batch_sizes": [len(batch.operation_ids) for batch in optimized.batches],
            "causal_lower_bound": optimized.causal_critical_path_lower_bound,
            "conflict_clique_lower_bound": optimized.conflict_clique_lower_bound,
            "fallback_operation_count": optimized.fallback_operation_count,
            "maximum_ppm_weight": optimized.maximum_ppm_weight,
            "optimality_evidence_status": optimized.optimality_evidence_status.value,
            "peak_live_logical_requirement": optimized.peak_live_logical_requirement,
            "peak_resource_state_count": optimized.peak_resource_state_count,
            "unit": "candidate_batch_level_not_time",
        },
        "evidence_qualification": {
            "exact_anf_relations": "PROVED relative to the reviewed symbolic trace",
            "finite_backend": "OPEN and rejected; native schedule is null",
            "low_rate_fallback": "NUMERICAL semantic order with finite cost OPEN",
            "width_five_candidate_construction": (
                "NUMERICAL deterministic construction meeting a PROVED lower bound "
                "inside the stated logical candidate model"
            ),
        },
        "experiment_id": EXPERIMENT_ID,
        "finite_result": finite_data,
        "independent_replay": replay_data,
        "input_configuration": [
            str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            str(BACKEND_AUDIT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        ],
        "prohibited_claims": {
            "failure_probability": None,
            "native_schedule": None,
            "physical_qubits": None,
            "runtime_seconds": None,
            "surgery_rounds": None,
        },
        "random_seed": "not_applicable_deterministic_exact_search",
        "source_pdf_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed_candidate_and_negative_finite_admission",
    }

    trace_text = dumps_symbolic_direct_ccz_ppm_trace(trace)
    filtered_status = _filtered_worktree_status()
    reproducibility = {
        "configuration_sha256": {
            str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"): (
                _sha256(CAPABILITY_PATH)
            ),
            str(BACKEND_AUDIT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"): (
                _sha256(BACKEND_AUDIT_PATH)
            ),
        },
        "git_commit": _git("rev-parse", "HEAD"),
        "input_circuit": "draper-clean-oop-qcla-mod2n width-5 trace v1",
        "input_symbolic_trace_sha256": _text_sha256(trace_text),
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": _text_sha256(filtered_status),
        },
        "random_seed": "not_applicable_deterministic_exact_search",
        "software_environment": {
            "networkx": importlib.metadata.version("networkx"),
            "numpy": importlib.metadata.version("numpy"),
            "platform": platform.platform(),
            "python": sys.version,
            "pyyaml": importlib.metadata.version("pyyaml"),
        },
        "source_bindings": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "source_pdf_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "general_candidate_batches.json").write_text(
        dumps_phase_b_artifact(general_data), encoding="utf-8"
    )
    (OUTPUT_ROOT / "finite_instance_admission.json").write_text(
        dumps_phase_b_artifact(finite_data), encoding="utf-8"
    )
    (OUTPUT_ROOT / "low_rate_fallback_order.json").write_text(
        dumps_phase_b_artifact(fallback_data), encoding="utf-8"
    )
    (OUTPUT_ROOT / "strategy_pareto_frontier.json").write_text(
        dumps_phase_b_artifact(frontier_data), encoding="utf-8"
    )
    _write_json(OUTPUT_ROOT / "independent_replay.json", replay_data)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary["candidate_result"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
