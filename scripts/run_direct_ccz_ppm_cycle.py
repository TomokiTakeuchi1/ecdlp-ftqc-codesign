"""Generate deterministic symbolic direct-CCZ PPM artifacts for Phase A."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import (
    QCLA_SOURCE_PDF_SHA256,
    build_oop_qcla_trace,
    oop_qcla_metrics,
)
from ecdlp_ftqc.compiler import (
    dumps_symbolic_direct_ccz_ppm_trace,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.verification import (
    replay_symbolic_direct_ccz_ppm_trace,
    symbolic_direct_ccz_ppm_replay_to_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260901-006"
EXPERIMENT_ID = "E-20260901-006"
WIDTH = 5
CAPABILITY_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
DRAPER_PDF = PROJECT_ROOT / "literature" / "papers" / "quant-ph-0406142v1.pdf"
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "architectures" / "direct_ccz.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz_ppm.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "direct_ccz_injection.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "direct_ccz_ppm_replay.py",
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


def _verify_source_hashes() -> dict[str, str]:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    paths = {DRAPER_PDF, *(PROJECT_ROOT / item.local_pdf for item in capability.sources)}
    hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in sorted(paths)
    }
    draper_key = str(DRAPER_PDF.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if hashes[draper_key] != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("Draper source PDF hash mismatch")
    for item in capability.sources:
        if hashes[item.local_pdf] != item.pdf_sha256.upper():
            raise RuntimeError(f"capability source PDF hash mismatch: {item.local_pdf}")
    return hashes


def _filtered_worktree_status() -> str:
    lines = _git("status", "--porcelain").splitlines()
    return "\n".join(
        line
        for line in lines
        if not line.startswith("?? .claude/")
        and f"experiments/runs/{TASK_ID}/" not in line.replace("\\", "/")
        and not line.startswith("?? tmp/")
    )


def main() -> None:
    source_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    if not capability.event_lowering_admitted:
        raise RuntimeError("single-event lowering is not admitted")
    if capability.high_rate_schedule_admitted:
        raise RuntimeError("Phase A unexpectedly received high-rate admission")

    source = build_oop_qcla_trace(WIDTH)
    source_metrics = oop_qcla_metrics(source)
    compiled = lower_oop_qcla_to_symbolic_direct_ccz_ppm(source, capability)
    trace_data = symbolic_direct_ccz_ppm_trace_to_data(compiled)
    replay = replay_symbolic_direct_ccz_ppm_trace(source, trace_data)
    replay_data = symbolic_direct_ccz_ppm_replay_to_data(replay)
    if not replay.all_passed:
        raise RuntimeError("independent symbolic PPM replay failed")
    if compiled.complete_native_schedule:
        raise RuntimeError("Phase-A trace cannot claim a native schedule")

    expected = {
        "source_operation_count": 23,
        "injection_count": 10,
        "ppm_count": 60,
        "passthrough_cnot_count": 13,
        "correction_update_count": 60,
        "macro_layer_count": 9,
        "source_dependency_count": 36,
        "logical_lifetime_count": 16,
        "resource_lifetime_count": 10,
        "compiler_ancilla_count": 0,
    }
    for name, expected_value in expected.items():
        if replay_data[name] != expected_value:
            raise RuntimeError(f"unexpected {name}: {replay_data[name]}")

    summary = {
        "capability": {
            "capability_id": capability.capability_id,
            "event_lowering_admitted": capability.event_lowering_admitted,
            "high_rate_schedule_admitted": capability.high_rate_schedule_admitted,
        },
        "evidence_qualification": {
            "frame_and_ppm_trace": (
                "NUMERICAL exact symbolic ANF/Clifford-frame construction; "
                "not a formal proof or native schedule"
            ),
            "finite_cnot_cost": "OPEN; pass-through CNOT is implementation-neutral",
            "high_rate_backend": "OPEN and rejected in Phase A",
            "local_injection_channel": (
                "NUMERICAL all-64-branch operator comparison with ideal CCX"
            ),
            "source_qcla": "LITERATURE with reviewed NUMERICAL source trace",
        },
        "experiment_id": EXPERIMENT_ID,
        "input_configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "random_seed": "not_applicable_deterministic_symbolic_replay",
        "replay": replay_data,
        "source_metrics": {
            "cnot_count": source_metrics.cnot_count,
            "gate_count": source_metrics.gate_count,
            "source_layer_count": source_metrics.source_layer_count,
            "toffoli_count": source_metrics.toffoli_count,
            "width": WIDTH,
        },
        "source_pdf_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed",
    }

    filtered_status = _filtered_worktree_status()
    reproducibility = {
        "configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "configuration_sha256": _sha256(CAPABILITY_PATH),
        "git_commit": _git("rev-parse", "HEAD"),
        "input_circuit": "draper-clean-oop-qcla-mod2n width-5 trace v1",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": hashlib.sha256(filtered_status.encode()).hexdigest().upper(),
        },
        "random_seed": "not_applicable_deterministic_symbolic_replay",
        "software_environment": {
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
    (OUTPUT_ROOT / "qcla_oop_n5_symbolic_direct_ccz_ppm.json").write_text(
        dumps_symbolic_direct_ccz_ppm_trace(compiled),
        encoding="utf-8",
    )
    _write_json(OUTPUT_ROOT / "symbolic_direct_ccz_ppm_replay.json", replay_data)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(replay_data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
