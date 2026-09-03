"""Generate scalable direct-CCZ QCLA PPM compatibility certificates."""

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
from ecdlp_ftqc.compiler import (
    lower_oop_qcla_to_direct_ccz_events,
    lower_qcla_to_direct_ccz_events,
)
from ecdlp_ftqc.scheduler import (
    analyze_qcla_direct_ccz_exact_anchor,
    certify_qcla_direct_ccz_ppm_compatibility,
    compare_certificate_to_exact_anchor,
    exact_anchor_compatibility_equivalence_to_data,
    qcla_ppm_compatibility_certificate_to_data,
)
from ecdlp_ftqc.verification import (
    direct_ccz_ppm_compatibility_replay_to_data,
    replay_direct_ccz_ppm_compatibility,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260903-001"
EXPERIMENT_ID = "E-20260903-001"
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
    / "direct_ccz_ppm_compatibility_certificate.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "direct_ccz_ppm_compatibility_replay.py",
    PROJECT_ROOT / "docs" / "DIRECT_CCZ_QCLA_SCALABLE_COMPATIBILITY_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260903-001.yaml",
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
    backend_audit = load_direct_ccz_backend_audit(BACKEND_AUDIT_PATH)
    if not capability.event_lowering_admitted:
        raise RuntimeError("direct-CCZ event lowering is not admitted")

    certificate_objects: dict[tuple[str, int], Any] = {}
    certificate_data: list[dict[str, Any]] = []
    for width in WIDTHS:
        for variant in VARIANTS:
            if variant == "oop":
                oop_trace = build_oop_qcla_trace(width)
                oop_events = lower_oop_qcla_to_direct_ccz_events(
                    oop_trace, capability
                )
                certificate = certify_qcla_direct_ccz_ppm_compatibility(
                    oop_trace,
                    oop_events,
                    variant=variant,
                )
            else:
                ip_trace = build_qcla_trace(width)
                ip_events = lower_qcla_to_direct_ccz_events(ip_trace, capability)
                certificate = certify_qcla_direct_ccz_ppm_compatibility(
                    ip_trace,
                    ip_events,
                    variant=variant,
                )
            if (
                not certificate.compatibility_proved
                or not certificate.candidate_equals_causal_lower_bound
                or certificate.candidate_optimality_evidence_status.value != "PROVED"
            ):
                raise RuntimeError(
                    f"compatibility certificate failed for {variant} width {width}: "
                    f"{certificate.counterexample}"
                )
            certificate_objects[(variant, width)] = certificate
            certificate_data.append(
                qcla_ppm_compatibility_certificate_to_data(certificate)
            )

    equivalence_data: list[dict[str, Any]] = []
    for width in EXACT_WIDTHS:
        for variant in VARIANTS:
            if variant == "oop":
                oop_trace = build_oop_qcla_trace(width)
                _, exact_analysis = analyze_qcla_direct_ccz_exact_anchor(
                    oop_trace,
                    capability,
                    backend_audit,
                    variant=variant,
                )
            else:
                ip_trace = build_qcla_trace(width)
                _, exact_analysis = analyze_qcla_direct_ccz_exact_anchor(
                    ip_trace,
                    capability,
                    backend_audit,
                    variant=variant,
                )
            comparison = compare_certificate_to_exact_anchor(
                certificate_objects[(variant, width)],
                exact_analysis,
            )
            if not comparison.all_checks_passed:
                raise RuntimeError(
                    f"exact anchor disagrees for {variant} width {width}"
                )
            equivalence_data.append(
                exact_anchor_compatibility_equivalence_to_data(comparison)
            )

    replay = replay_direct_ccz_ppm_compatibility(
        certificate_data,
        equivalence_data,
        expected_widths=WIDTHS,
        expected_exact_widths=EXACT_WIDTHS,
    )
    if not replay.all_passed:
        raise RuntimeError("independent compatibility replay failed")
    replay_data = direct_ccz_ppm_compatibility_replay_to_data(replay)

    width_256 = [item for item in certificate_data if item["width"] == 256]
    width_256_by_variant = {str(item["variant"]): item for item in width_256}
    maximum_batch_ppms = {
        variant: max(
            int(batch["ppm_count"])
            for batch in width_256_by_variant[variant]["batches"]
        )
        for variant in ("oop", "ip")
    }
    summary = {
        "certificate_method": {
            "asymptotic_size": "O(source_gates + source_dependencies + PPMs)",
            "frame_closure": (
                "conditional X/Z/CNOT/CZ frames preserve the Z-type Pauli subspace"
            ),
            "phase_one": (
                "all resource-data ZZ PPMs remain branchwise Z type"
            ),
            "phase_two": (
                "all resource X readouts act on unique fresh values absent from the frame"
            ),
            "pair_records_materialized_outside_exact_anchors": 0,
        },
        "evidence_qualification": {
            "candidate_compatibility": (
                "PROVED relative to the stated architecture-independent logical screen"
            ),
            "candidate_optimality": (
                "PROVED for every selected source trace because the construction "
                "meets the independently computed weighted causal lower bound"
            ),
            "exact_anchor_bridge": (
                "NUMERICAL full-ANF agreement at OOP/IP widths 5 and 8"
            ),
            "finite_backend": (
                "OPEN; native schedule, surgery rounds, runtime, physical qubits, "
                "and failure probability remain null"
            ),
        },
        "exact_anchor_equivalences": equivalence_data,
        "experiment_id": EXPERIMENT_ID,
        "input_configuration": [
            str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            str(BACKEND_AUDIT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        ],
        "random_seed": "not_applicable_deterministic_proof_certificate",
        "source_pdf_hashes": source_pdf_hashes,
        "task_id": TASK_ID,
        "validation_status": (
            "passed_linear_certificates_exact_anchor_equivalence_and_independent_replay"
        ),
        "width_256": {
            "ip": {
                "candidate_batch_level_count": width_256_by_variant["ip"][
                    "candidate_batch_level_count"
                ],
                "direct_ccz_event_count": width_256_by_variant["ip"][
                    "direct_ccz_event_count"
                ],
                "maximum_batch_ppm_count": maximum_batch_ppms["ip"],
                "ppm_count": width_256_by_variant["ip"]["ppm_count"],
                "theoretical_global_pair_count": width_256_by_variant["ip"][
                    "theoretical_global_pair_count"
                ],
            },
            "oop": {
                "candidate_batch_level_count": width_256_by_variant["oop"][
                    "candidate_batch_level_count"
                ],
                "direct_ccz_event_count": width_256_by_variant["oop"][
                    "direct_ccz_event_count"
                ],
                "maximum_batch_ppm_count": maximum_batch_ppms["oop"],
                "ppm_count": width_256_by_variant["oop"]["ppm_count"],
                "theoretical_global_pair_count": width_256_by_variant["oop"][
                    "theoretical_global_pair_count"
                ],
            },
        },
    }
    width_256_artifact = {
        "certificates": width_256,
        "coordinate": "candidate_batch_level_not_time",
        "finite_outputs": {
            "failure_probability": None,
            "native_schedule": None,
            "physical_qubits": None,
            "runtime_seconds": None,
            "surgery_rounds": None,
        },
        "task_id": TASK_ID,
        "warning": (
            "proved logical compatibility does not supply a physical support, "
            "routing, factory, decoder, buffer, or timing construction"
        ),
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    primary_outputs = {
        "compatibility_certificates.json": certificate_data,
        "compatibility_replay.json": replay_data,
        "exact_anchor_equivalence.json": equivalence_data,
        "summary.json": summary,
        "width_256_candidate_certificate.json": width_256_artifact,
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
        "random_seed": "not_applicable_deterministic_proof_certificate",
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
