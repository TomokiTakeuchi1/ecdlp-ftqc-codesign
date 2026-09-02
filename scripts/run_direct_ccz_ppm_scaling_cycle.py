"""Generate exact-anchor and structural direct-CCZ QCLA scaling artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from ecdlp_ftqc.architectures import (
    load_direct_ccz_backend_audit,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import (
    QCLA_SOURCE_PDF_SHA256,
    build_oop_qcla_trace,
    build_qcla_trace,
)
from ecdlp_ftqc.scheduler import (
    analyze_qcla_direct_ccz_exact_anchor,
    analyze_qcla_direct_ccz_structural_point,
    assess_qcla_direct_ccz_finite_scaling_admission,
    qcla_direct_ccz_exact_anchor_to_data,
    qcla_direct_ccz_finite_scaling_admission_to_data,
    qcla_direct_ccz_structural_point_to_data,
)
from ecdlp_ftqc.verification import (
    direct_ccz_ppm_scaling_replay_to_data,
    replay_direct_ccz_ppm_scaling,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260901-010"
EXPERIMENT_ID = "E-20260901-010"
WIDTHS = (
    5,
    7,
    8,
    9,
    15,
    16,
    17,
    31,
    32,
    33,
    63,
    64,
    65,
    127,
    128,
    129,
    255,
    256,
    257,
)
EXACT_WIDTHS = (5, 8)
VARIANTS: tuple[Literal["oop", "ip"], ...] = ("oop", "ip")
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
    / "scheduler"
    / "direct_ccz_ppm_scaling.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "direct_ccz_ppm_scaling_replay.py",
    PROJECT_ROOT / "docs" / "DIRECT_CCZ_QCLA_SCALING_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260901-010.yaml",
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


def main() -> None:
    source_pdf_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    audit = load_direct_ccz_backend_audit(BACKEND_AUDIT_PATH)
    if not capability.event_lowering_admitted:
        raise RuntimeError("direct-CCZ single-event lowering is not admitted")

    structural_data: list[dict[str, Any]] = []
    for width in WIDTHS:
        for variant in VARIANTS:
            if variant == "oop":
                point = analyze_qcla_direct_ccz_structural_point(
                    build_oop_qcla_trace(width),
                    capability,
                    variant=variant,
                )
            else:
                point = analyze_qcla_direct_ccz_structural_point(
                    build_qcla_trace(width),
                    capability,
                    variant=variant,
                )
            structural_data.append(qcla_direct_ccz_structural_point_to_data(point))

    exact_data: list[dict[str, Any]] = []
    for width in EXACT_WIDTHS:
        for variant in VARIANTS:
            if variant == "oop":
                anchor, _ = analyze_qcla_direct_ccz_exact_anchor(
                    build_oop_qcla_trace(width),
                    capability,
                    audit,
                    variant=variant,
                )
            else:
                anchor, _ = analyze_qcla_direct_ccz_exact_anchor(
                    build_qcla_trace(width),
                    capability,
                    audit,
                    variant=variant,
                )
            if (
                anchor.candidate_batch_level_count
                != anchor.causal_critical_path_lower_bound
                or anchor.candidate_optimality_evidence_status.value != "PROVED"
            ):
                raise RuntimeError("exact anchor did not close its causal lower bound")
            exact_data.append(qcla_direct_ccz_exact_anchor_to_data(anchor))

    finite_data = qcla_direct_ccz_finite_scaling_admission_to_data(
        assess_qcla_direct_ccz_finite_scaling_admission(capability, audit)
    )
    replay = replay_direct_ccz_ppm_scaling(
        structural_data,
        exact_data,
        finite_data,
        expected_widths=WIDTHS,
        expected_exact_widths=EXACT_WIDTHS,
    )
    if not replay.all_passed:
        raise RuntimeError("independent scaling replay failed")
    replay_data = direct_ccz_ppm_scaling_replay_to_data(replay)

    point_by_key = {
        (str(item["variant"]), int(item["width"])): item
        for item in structural_data
    }
    width_256 = [item for item in structural_data if item["width"] == 256]
    width_256_by_variant = {
        str(item["variant"]): item for item in width_256
    }
    boundary_windows = [
        {
            "causal_lower_bounds": [
                point_by_key[(variant, power + offset)][
                    "weighted_causal_ppm_level_lower_bound"
                ]
                for offset in (-1, 0, 1)
            ],
            "evidence_status": "NUMERICAL",
            "peak_source_toffoli_demands": [
                point_by_key[(variant, power + offset)][
                    "peak_source_toffoli_per_layer"
                ]
                for offset in (-1, 0, 1)
            ],
            "power_of_two": power,
            "source_toffoli_counts": [
                point_by_key[(variant, power + offset)][
                    "source_toffoli_count"
                ]
                for offset in (-1, 0, 1)
            ],
            "variant": variant,
            "widths": [power - 1, power, power + 1],
        }
        for power in (8, 16, 32, 64, 128, 256)
        for variant in VARIANTS
    ]
    scaling_findings = {
        "exact_anchor_level_closure": {
            "evidence_status": "NUMERICAL",
            "statement": (
                "all four width-5/8 OOP/IP exact candidates meet their causal lower bound"
            ),
        },
        "ip_to_oop_selected_width_relations": {
            "causal_lower_bound_ratio_two": all(
                point_by_key[("ip", width)][
                    "weighted_causal_ppm_level_lower_bound"
                ]
                == 2
                * point_by_key[("oop", width)][
                    "weighted_causal_ppm_level_lower_bound"
                ]
                for width in WIDTHS
            ),
            "evidence_status": "NUMERICAL",
            "nonclifford_source_layer_ratio_two": all(
                point_by_key[("ip", width)]["nonclifford_source_layer_count"]
                == 2
                * point_by_key[("oop", width)][
                    "nonclifford_source_layer_count"
                ]
                for width in WIDTHS
            ),
            "toffoli_and_event_ratio_two": all(
                point_by_key[("ip", width)]["direct_ccz_event_count"]
                == 2 * point_by_key[("oop", width)]["direct_ccz_event_count"]
                for width in WIDTHS
            ),
            "scope": "selected widths only; not a general proof",
        },
        "power_boundary_windows": boundary_windows,
        "width_256_comparison": {
            "evidence_status": "NUMERICAL",
            "ip": {
                "cleanup_toffoli_count": width_256_by_variant["ip"][
                    "cleanup_toffoli_count"
                ],
                "direct_ccz_event_count": width_256_by_variant["ip"][
                    "direct_ccz_event_count"
                ],
                "peak_source_layer_ppm_demand": width_256_by_variant["ip"][
                    "peak_source_layer_ppm_demand"
                ],
                "ppm_count": width_256_by_variant["ip"]["ppm_count"],
                "theoretical_pair_count": width_256_by_variant["ip"][
                    "theoretical_pair_count"
                ],
                "weighted_causal_lower_bound": width_256_by_variant["ip"][
                    "weighted_causal_ppm_level_lower_bound"
                ],
            },
            "oop": {
                "cleanup_toffoli_count": width_256_by_variant["oop"][
                    "cleanup_toffoli_count"
                ],
                "direct_ccz_event_count": width_256_by_variant["oop"][
                    "direct_ccz_event_count"
                ],
                "peak_source_layer_ppm_demand": width_256_by_variant["oop"][
                    "peak_source_layer_ppm_demand"
                ],
                "ppm_count": width_256_by_variant["oop"]["ppm_count"],
                "theoretical_pair_count": width_256_by_variant["oop"][
                    "theoretical_pair_count"
                ],
                "weighted_causal_lower_bound": width_256_by_variant["oop"][
                    "weighted_causal_ppm_level_lower_bound"
                ],
            },
        },
    }
    exact_frontier = {
        "exact_widths": list(EXACT_WIDTHS),
        "largest_exact_width": max(EXACT_WIDTHS),
        "reason_for_structural_mode": (
            "all-pairs materialization grows quadratically; width-256 OOP/IP "
            "would require 27184251/108744378 pair records"
        ),
        "structural_widths_without_pair_tables": [
            width for width in WIDTHS if width not in EXACT_WIDTHS
        ],
    }
    sweep_artifact = {
        "analysis_boundary": exact_frontier,
        "exact_anchors": exact_data,
        "finite_admission": finite_data,
        "points": structural_data,
        "scaling_findings": scaling_findings,
        "task_id": TASK_ID,
    }
    width_256_artifact = {
        "coordinate": "ppm_level_not_time",
        "finite_outputs": {
            "failure_probability": None,
            "native_schedule": None,
            "physical_qubits": None,
            "runtime_seconds": None,
            "surgery_rounds": None,
        },
        "points": width_256,
        "task_id": TASK_ID,
        "warning": (
            "weighted causal lower bounds and source two-phase envelopes are "
            "not width-256 compatibility-certified schedules"
        ),
    }
    summary = {
        "analysis_boundary": exact_frontier,
        "evidence_qualification": {
            "exact_anchor_pair_classification": (
                "PROVED relative to exact Boolean-ANF traces at widths 5 and 8"
            ),
            "source_and_event_counts": (
                "NUMERICAL from deterministic source/event trace traversal"
            ),
            "weighted_causal_lower_bound": (
                "PROVED by longest-path weighting of two ordered PPM layers "
                "per source Toffoli"
            ),
            "source_two_phase_envelope": (
                "CHECK only; it is demand structure, not a compatibility-certified schedule"
            ),
            "width_256_candidate_batch_count": "OPEN",
            "width_256_finite_resources": "OPEN and all outputs remain null",
        },
        "exact_anchors": exact_data,
        "experiment_id": EXPERIMENT_ID,
        "input_configuration": [
            str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            str(BACKEND_AUDIT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        ],
        "random_seed": "not_applicable_deterministic_analysis",
        "scaling_findings": scaling_findings,
        "source_pdf_hashes": source_pdf_hashes,
        "task_id": TASK_ID,
        "validation_status": (
            "passed_exact_anchors_structural_sweep_independent_replay_"
            "and_negative_finite_admission"
        ),
        "width_256": width_256,
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    primary_outputs = {
        "exact_anchors.json": exact_data,
        "finite_scaling_admission.json": finite_data,
        "scaling_replay.json": replay_data,
        "summary.json": summary,
        "width_256_demand.json": width_256_artifact,
        "width_sweep.json": sweep_artifact,
    }
    for name, value in primary_outputs.items():
        _write_json(OUTPUT_ROOT / name, value)

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
        "exact_widths": list(EXACT_WIDTHS),
        "experiment_id": EXPERIMENT_ID,
        "git_branch": _git("branch", "--show-current"),
        "git_head": _git("rev-parse", "HEAD"),
        "input_trace": "deterministically generated OOP/IP QCLA source traces",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "output_sha256": {
            name: _sha256(OUTPUT_ROOT / name) for name in sorted(primary_outputs)
        },
        "package_versions": {
            name: importlib.metadata.version(name)
            for name in ("mypy", "networkx", "pytest", "pyyaml", "ruff")
        },
        "platform": platform.platform(),
        "python": sys.version,
        "random_seed": "not_applicable_deterministic_analysis",
        "source_binding_sha256": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "source_pdf_hashes": source_pdf_hashes,
        "task_id": TASK_ID,
        "validation_status": summary["validation_status"],
        "widths": list(WIDTHS),
        "working_tree_state": "dirty:" + _text_sha256(filtered_status),
        "working_tree_status": filtered_status,
    }
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
