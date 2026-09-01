"""Generate the deterministic width-5 direct-CCZ PPM audit atlas."""

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
from ecdlp_ftqc.circuits import QCLA_SOURCE_PDF_SHA256, build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.scheduler import (
    analyze_direct_ccz_ppm_batches,
    finite_instance_admission_to_data,
    general_high_rate_candidate_to_data,
    low_rate_fallback_to_data,
    strategy_frontier_to_data,
)
from ecdlp_ftqc.verification import (
    direct_ccz_ppm_atlas_replay_to_data,
    replay_direct_ccz_ppm_atlas,
    replay_direct_ccz_ppm_batching,
    replay_symbolic_direct_ccz_ppm_trace,
)
from ecdlp_ftqc.visualization import (
    build_direct_ccz_ppm_atlas,
    dumps_direct_ccz_ppm_atlas,
    render_direct_ccz_ppm_atlas_svgs,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260901-008"
EXPERIMENT_ID = "E-20260901-008"
WIDTH = 5
CAPABILITY_PATH = (
    PROJECT_ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
)
BACKEND_AUDIT_PATH = (
    PROJECT_ROOT / "configs" / "architectures" / "direct_ccz_finite_backend_audit_v1.yaml"
)
DRAPER_PDF = PROJECT_ROOT / "literature" / "papers" / "quant-ph-0406142v1.pdf"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz_ppm.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "direct_ccz_ppm_batching.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "visualization" / "direct_ccz_ppm_atlas.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "verification" / "direct_ccz_ppm_atlas_replay.py",
    PROJECT_ROOT / "docs" / "DIRECT_CCZ_PPM_ATLAS_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260901-008.yaml",
    CAPABILITY_PATH,
    BACKEND_AUDIT_PATH,
    Path(__file__),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest().upper()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return _text_sha256(payload)


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


def _assert_expected(replay_data: dict[str, Any]) -> None:
    expected = {
        "all_passed": True,
        "atlas_panel_count": 9,
        "batch_membership_checks": 60,
        "correction_update_checks": 60,
        "finite_backend_rejected": True,
        "non_temporal_document_checks": 10,
        "ppm_checks": 60,
        "separation_certificate_checks": 1584,
        "source_dependency_checks": 36,
        "source_operation_checks": 23,
        "svg_document_checks": 10,
        "svg_ppm_id_checks": 60,
        "svg_source_operation_id_checks": 23,
        "svg_update_id_checks": 60,
    }
    for name, expected_value in expected.items():
        if replay_data.get(name) != expected_value:
            raise RuntimeError(f"unexpected atlas replay {name}: {replay_data.get(name)!r}")


def main() -> None:
    source_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    backend_audit = load_direct_ccz_backend_audit(BACKEND_AUDIT_PATH)
    source = build_oop_qcla_trace(WIDTH)
    trace = lower_oop_qcla_to_symbolic_direct_ccz_ppm(source, capability)
    trace_data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    phase_a_replay = replay_symbolic_direct_ccz_ppm_trace(source, trace_data)
    if not phase_a_replay.all_passed:
        raise RuntimeError("Phase-A symbolic trace replay failed")

    analysis = analyze_direct_ccz_ppm_batches(trace, capability, backend_audit)
    general_data = general_high_rate_candidate_to_data(analysis.general)
    finite_data = finite_instance_admission_to_data(analysis.finite)
    fallback_data = low_rate_fallback_to_data(analysis.fallback)
    frontier_data = strategy_frontier_to_data(analysis.frontier)
    phase_b_replay = replay_direct_ccz_ppm_batching(
        trace_data,
        general_data,
        finite_data,
        fallback_data,
        frontier_data,
        direct_ccz_capability_to_data(capability),
        direct_ccz_backend_audit_to_data(backend_audit),
    )
    if not phase_b_replay.all_passed:
        raise RuntimeError("Phase-B batching replay failed")

    atlas_data = build_direct_ccz_ppm_atlas(trace_data, general_data, finite_data)
    svg_documents = render_direct_ccz_ppm_atlas_svgs(atlas_data)
    atlas_replay = replay_direct_ccz_ppm_atlas(
        trace_data,
        general_data,
        finite_data,
        atlas_data,
        svg_documents,
    )
    replay_data = direct_ccz_ppm_atlas_replay_to_data(atlas_replay)
    _assert_expected(replay_data)

    atlas_text = dumps_direct_ccz_ppm_atlas(atlas_data)
    svg_sha256 = {name: _text_sha256(document) for name, document in svg_documents.items()}
    summary = {
        "atlas": atlas_data["overview"],
        "backend_status": atlas_data["backend_status"],
        "evidence_qualification": {
            "atlas_projection": (
                "NUMERICAL deterministic projection of reviewed Phase-A/Phase-B artifacts"
            ),
            "candidate_optimality": ("PROVED only inside the stated logical candidate model"),
            "finite_backend": "OPEN and rejected; all finite outputs null",
            "physical_interpretation": (
                "candidate levels are not time, surgery rounds, or native simultaneity"
            ),
        },
        "experiment_id": EXPERIMENT_ID,
        "independent_replay": replay_data,
        "input_artifact_sha256": {
            "finite_admission": _canonical_sha256(finite_data),
            "general_candidate": _canonical_sha256(general_data),
            "symbolic_trace": _canonical_sha256(trace_data),
        },
        "random_seed": "not_applicable_deterministic_projection",
        "svg_sha256": dict(sorted(svg_sha256.items())),
        "task_id": TASK_ID,
        "validation_status": "passed_data_and_svg_independent_replay",
    }

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
        "input_artifact_sha256": summary["input_artifact_sha256"],
        "input_circuit": "draper-clean-oop-qcla-mod2n width-5 trace v1",
        "output_atlas_sha256": _text_sha256(atlas_text),
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": _text_sha256(filtered_status),
        },
        "random_seed": "not_applicable_deterministic_projection",
        "software_environment": {
            "networkx": importlib.metadata.version("networkx"),
            "platform": platform.platform(),
            "python": sys.version,
            "pyyaml": importlib.metadata.version("pyyaml"),
        },
        "source_bindings": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "source_pdf_hashes": source_hashes,
        "svg_sha256": dict(sorted(svg_sha256.items())),
        "task_id": TASK_ID,
        "validation_status": "passed",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "atlas.json").write_text(atlas_text, encoding="utf-8")
    for name, document in sorted(svg_documents.items()):
        (OUTPUT_ROOT / name).write_text(document, encoding="utf-8")
    _write_json(OUTPUT_ROOT / "independent_replay.json", replay_data)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
