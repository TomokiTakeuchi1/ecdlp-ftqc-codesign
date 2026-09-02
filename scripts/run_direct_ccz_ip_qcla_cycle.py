"""Generate the bounded in-place versus out-of-place direct-CCZ comparison."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecdlp_ftqc.architectures import (
    direct_ccz_backend_audit_to_data,
    direct_ccz_capability_to_data,
    load_direct_ccz_backend_audit,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import (
    QCLA_SOURCE_PDF_SHA256,
    build_oop_qcla_trace,
    build_qcla_trace,
    oop_qcla_metrics,
    qcla_metrics,
)
from ecdlp_ftqc.compiler import (
    dumps_symbolic_direct_ccz_ppm_trace,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    lower_qcla_to_symbolic_direct_ccz_ppm,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.scheduler import (
    DirectCczPpmBatchAnalysis,
    analyze_direct_ccz_ppm_batches,
    dumps_phase_b_artifact,
    finite_instance_admission_to_data,
    general_high_rate_candidate_to_data,
    low_rate_fallback_to_data,
    strategy_frontier_to_data,
)
from ecdlp_ftqc.verification import (
    direct_ccz_ppm_batching_replay_to_data,
    ip_qcla_symbolic_direct_ccz_ppm_replay_to_data,
    replay_direct_ccz_ppm_batching,
    replay_ip_qcla_symbolic_direct_ccz_ppm_trace,
    replay_symbolic_direct_ccz_ppm_trace,
    symbolic_direct_ccz_ppm_replay_to_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260901-009"
EXPERIMENT_ID = "E-20260901-009"
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
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz.py",
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
    / "direct_ccz_ppm_replay.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "direct_ccz_ppm_batching_replay.py",
    PROJECT_ROOT / "docs" / "DIRECT_CCZ_IP_QCLA_COMPARISON_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260901-009.yaml",
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
    paths = {DRAPER_PDF}
    paths.update(PROJECT_ROOT / source.local_pdf for source in capability.sources)
    paths.update(PROJECT_ROOT / source.local_pdf for source in audit.sources)
    hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in sorted(paths)
    }
    draper_key = str(DRAPER_PDF.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if hashes[draper_key] != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("Draper source PDF hash mismatch")
    for capability_source in capability.sources:
        if (
            hashes[capability_source.local_pdf]
            != capability_source.pdf_sha256.upper()
        ):
            raise RuntimeError(
                f"source PDF hash mismatch: {capability_source.local_pdf}"
            )
    for audit_source in audit.sources:
        if hashes[audit_source.local_pdf] != audit_source.pdf_sha256.upper():
            raise RuntimeError(
                f"source PDF hash mismatch: {audit_source.local_pdf}"
            )
    return hashes


def _relation_counts(analysis: DirectCczPpmBatchAnalysis) -> dict[str, int]:
    profiles = analysis.general.observable_profiles
    relations = analysis.general.pair_relations
    return {
        "anticommuting_pairs": sum(
            not relation.universally_commuting for relation in relations
        ),
        "axis_conflict_pairs": sum(
            not relation.universally_axis_consistent for relation in relations
        ),
        "causal_pairs": sum(
            relation.causal_order != "none" for relation in relations
        ),
        "compatible_overlap_pairs": sum(
            relation.general_high_rate_compatible
            and bool(relation.shared_logical_values)
            for relation in relations
        ),
        "pair_count": len(relations),
        "possible_y_ppms": sum(profile.has_possible_y for profile in profiles),
        "reaction_pairs": sum(
            relation.reaction_dependent for relation in relations
        ),
        "resource_reuse_pairs": sum(
            relation.resource_reuse_conflict for relation in relations
        ),
    }


def _candidate_counts(analysis: DirectCczPpmBatchAnalysis) -> dict[str, Any]:
    schedule = analysis.general.optimized_schedule
    profiles = analysis.general.observable_profiles
    return {
        "batch_level_count": schedule.candidate_batch_level_count,
        "batch_sizes": [len(batch.operation_ids) for batch in schedule.batches],
        "causal_lower_bound": schedule.causal_critical_path_lower_bound,
        "combined_lower_bound": schedule.combined_batch_level_lower_bound,
        "conflict_clique_bound_method": schedule.conflict_clique_bound_method,
        "conflict_clique_lower_bound": schedule.conflict_clique_lower_bound,
        "fallback_operation_count": schedule.fallback_operation_count,
        "maximum_ppm_weight_or_upper_bound": schedule.maximum_ppm_weight,
        "nonexact_weight_profile_count": sum(
            not profile.weight_bounds_exact for profile in profiles
        ),
        "null_distinct_observable_profile_count": sum(
            profile.distinct_branch_observables is None for profile in profiles
        ),
        "optimality_evidence_status": schedule.optimality_evidence_status.value,
        "peak_live_logical_requirement": schedule.peak_live_logical_requirement,
        "peak_resource_state_count": schedule.peak_resource_state_count,
        "unit": "candidate_batch_level_not_time",
    }


def main() -> None:
    source_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    backend_audit = load_direct_ccz_backend_audit(BACKEND_AUDIT_PATH)
    if not capability.event_lowering_admitted:
        raise RuntimeError("single-event semantics are not admitted")
    if capability.high_rate_schedule_admitted or backend_audit.candidate.backend_admitted:
        raise RuntimeError("comparison requires the reviewed negative finite admission")

    oop_source = build_oop_qcla_trace(WIDTH)
    ip_source = build_qcla_trace(WIDTH)
    oop_metrics = oop_qcla_metrics(oop_source)
    ip_metrics = qcla_metrics(ip_source)
    oop_trace = lower_oop_qcla_to_symbolic_direct_ccz_ppm(oop_source, capability)
    ip_trace = lower_qcla_to_symbolic_direct_ccz_ppm(ip_source, capability)
    oop_trace_data = symbolic_direct_ccz_ppm_trace_to_data(oop_trace)
    ip_trace_data = symbolic_direct_ccz_ppm_trace_to_data(ip_trace)

    oop_semantic = replay_symbolic_direct_ccz_ppm_trace(oop_source, oop_trace_data)
    ip_semantic = replay_ip_qcla_symbolic_direct_ccz_ppm_trace(
        ip_source,
        ip_trace_data,
    )
    if not oop_semantic.all_passed or not ip_semantic.all_passed:
        raise RuntimeError("symbolic semantic replay failed")

    oop_analysis = analyze_direct_ccz_ppm_batches(
        oop_trace,
        capability,
        backend_audit,
    )
    ip_analysis = analyze_direct_ccz_ppm_batches(
        ip_trace,
        capability,
        backend_audit,
    )
    ip_general_data = general_high_rate_candidate_to_data(ip_analysis.general)
    ip_finite_data = finite_instance_admission_to_data(ip_analysis.finite)
    ip_fallback_data = low_rate_fallback_to_data(ip_analysis.fallback)
    ip_frontier_data = strategy_frontier_to_data(ip_analysis.frontier)
    ip_batching_replay = replay_direct_ccz_ppm_batching(
        ip_trace_data,
        ip_general_data,
        ip_finite_data,
        ip_fallback_data,
        ip_frontier_data,
        direct_ccz_capability_to_data(capability),
        direct_ccz_backend_audit_to_data(backend_audit),
    )
    if not ip_batching_replay.all_passed:
        raise RuntimeError("independent IP batching replay failed")

    expected_ip = {
        "batch_level_count": 24,
        "causal_lower_bound": 24,
        "fallback_operation_count": 0,
        "nonexact_weight_profile_count": 7,
        "null_distinct_observable_profile_count": 7,
        "peak_live_logical_requirement": 26,
        "peak_resource_state_count": 4,
    }
    ip_candidate = _candidate_counts(ip_analysis)
    for name, expected in expected_ip.items():
        if ip_candidate[name] != expected:
            raise RuntimeError(f"unexpected IP {name}: {ip_candidate[name]}")
    ip_relations = _relation_counts(ip_analysis)
    if ip_relations != {
        "anticommuting_pairs": 60,
        "axis_conflict_pairs": 60,
        "causal_pairs": 6012,
        "compatible_overlap_pairs": 134,
        "pair_count": 7140,
        "possible_y_ppms": 0,
        "reaction_pairs": 5832,
        "resource_reuse_pairs": 60,
    }:
        raise RuntimeError("unexpected IP exact relation counts")
    if any(ip_finite_data[key] is not None for key in (
        "schedule",
        "runtime_seconds",
        "physical_qubits",
        "failure_probability",
    )):
        raise RuntimeError("finite rejection emitted a prohibited result")

    comparison = {
        "coordinate": "candidate_batch_level_not_time",
        "cleanup_scope": {
            "ip": "source steps 7-10",
            "oop": "input_restore and prefix_uncompute stages",
        },
        "ip": {
            "candidate": ip_candidate,
            "cleanup_operation_count": sum(
                gate.source_step >= 7 for gate in ip_source.gates
            ),
            "cleanup_toffoli_count": sum(
                gate.source_step >= 7 and gate.kind.value == "toffoli"
                for gate in ip_source.gates
            ),
            "direct_ccz_event_count": len(ip_trace.injections),
            "fallback_singleton_demand": len(ip_analysis.fallback.operation_ids),
            "high_rate_candidate_fraction": (
                1
                - ip_analysis.general.optimized_schedule.fallback_operation_count
                / len(ip_trace.ppms)
            ),
            "logical_lifetime_count": len(ip_trace.logical_lifetimes),
            "nonclifford_source_layer_count": len(
                {
                    gate.algorithmic_layer
                    for gate in ip_source.gates
                    if gate.kind.value == "toffoli"
                }
            ),
            "ppm_count": len(ip_trace.ppms),
            "relation_counts": ip_relations,
            "reaction_boundary_count": len(ip_analysis.fallback.reaction_boundaries),
            "source_dependency_count": len(ip_source.dependencies),
            "source_metrics": {
                "cnot_count": ip_metrics.cnot_count,
                "gate_count": ip_metrics.gate_count,
                "source_layer_count": ip_metrics.source_layer_count,
                "toffoli_count": ip_metrics.toffoli_count,
                "x_count": ip_metrics.x_count,
            },
        },
        "oop": {
            "candidate": _candidate_counts(oop_analysis),
            "cleanup_operation_count": sum(
                gate.stage.value in {"input_restore", "prefix_uncompute"}
                for gate in oop_source.gates
            ),
            "cleanup_toffoli_count": sum(
                gate.stage.value in {"input_restore", "prefix_uncompute"}
                and gate.kind.value == "toffoli"
                for gate in oop_source.gates
            ),
            "direct_ccz_event_count": len(oop_trace.injections),
            "fallback_singleton_demand": len(oop_analysis.fallback.operation_ids),
            "high_rate_candidate_fraction": (
                1
                - oop_analysis.general.optimized_schedule.fallback_operation_count
                / len(oop_trace.ppms)
            ),
            "logical_lifetime_count": len(oop_trace.logical_lifetimes),
            "nonclifford_source_layer_count": len(
                {
                    gate.algorithmic_layer
                    for gate in oop_source.gates
                    if gate.kind.value == "toffoli"
                }
            ),
            "ppm_count": len(oop_trace.ppms),
            "relation_counts": _relation_counts(oop_analysis),
            "reaction_boundary_count": len(oop_analysis.fallback.reaction_boundaries),
            "source_dependency_count": len(oop_source.dependencies),
            "source_metrics": {
                "cnot_count": oop_metrics.cnot_count,
                "gate_count": oop_metrics.gate_count,
                "source_layer_count": oop_metrics.source_layer_count,
                "toffoli_count": oop_metrics.toffoli_count,
                "x_count": 0,
            },
        },
        "scope": "bounded width-5 logical comparison; not a native schedule",
    }

    summary = {
        "comparison": comparison,
        "evidence_qualification": {
            "candidate_compatibility_and_pair_relations": (
                "PROVED relative to the serialized symbolic ANF trace"
            ),
            "candidate_level_optimality": (
                "PROVED inside the stated logical candidate model by a 24-level "
                "causal lower bound and matching construction"
            ),
            "finite_backend": "OPEN and rejected; native outputs are null",
            "ip_large_frame_weight": (
                "CHECK conservative nonidentity lower and exact support-union upper "
                "bounds for seven profiles; not used for pair compatibility"
            ),
            "source_circuits": "LITERATURE with reviewed NUMERICAL source replay",
        },
        "experiment_id": EXPERIMENT_ID,
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
        "random_seed": "not_applicable_deterministic_symbolic_analysis",
        "source_pdf_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed_bounded_comparison_and_negative_finite_admission",
    }

    ip_trace_text = dumps_symbolic_direct_ccz_ppm_trace(ip_trace)
    oop_trace_text = dumps_symbolic_direct_ccz_ppm_trace(oop_trace)
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
        "input_circuits": [
            "draper-clean-oop-qcla-mod2n width-5 trace v1",
            "draper-qcla-inplace-mod2n width-5 trace v1",
        ],
        "input_trace_sha256": {
            "ip": _text_sha256(ip_trace_text),
            "oop": _text_sha256(oop_trace_text),
        },
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": _text_sha256(filtered_status),
        },
        "random_seed": "not_applicable_deterministic_symbolic_analysis",
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
    (OUTPUT_ROOT / "ip_qcla_n5_symbolic_direct_ccz_ppm.json").write_text(
        ip_trace_text,
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "ip_general_candidate_batches.json").write_text(
        dumps_phase_b_artifact(ip_general_data), encoding="utf-8"
    )
    (OUTPUT_ROOT / "ip_finite_instance_admission.json").write_text(
        dumps_phase_b_artifact(ip_finite_data), encoding="utf-8"
    )
    (OUTPUT_ROOT / "ip_low_rate_fallback_order.json").write_text(
        dumps_phase_b_artifact(ip_fallback_data), encoding="utf-8"
    )
    (OUTPUT_ROOT / "ip_strategy_pareto_frontier.json").write_text(
        dumps_phase_b_artifact(ip_frontier_data), encoding="utf-8"
    )
    _write_json(
        OUTPUT_ROOT / "ip_semantic_replay.json",
        ip_qcla_symbolic_direct_ccz_ppm_replay_to_data(ip_semantic),
    )
    _write_json(
        OUTPUT_ROOT / "ip_batching_replay.json",
        direct_ccz_ppm_batching_replay_to_data(ip_batching_replay),
    )
    _write_json(
        OUTPUT_ROOT / "oop_semantic_replay.json",
        symbolic_direct_ccz_ppm_replay_to_data(oop_semantic),
    )
    _write_json(OUTPUT_ROOT / "oop_ip_comparison.json", comparison)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(comparison, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
