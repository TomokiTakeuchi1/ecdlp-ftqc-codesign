"""Generate deterministic finite direct-CCZ backend audit artifacts."""

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
    load_direct_ccz_backend_audit,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260831-004"
EXPERIMENT_ID = "E-20260831-004"
CONFIG_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_finite_backend_audit_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "architectures"
    / "direct_ccz_backend_audit.py",
    CONFIG_PATH,
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
    audit = load_direct_ccz_backend_audit(CONFIG_PATH)
    hashes: dict[str, str] = {}
    for source in audit.sources:
        path = PROJECT_ROOT / source.local_pdf
        actual = _sha256(path)
        if actual != source.pdf_sha256.upper():
            raise RuntimeError(f"audit source PDF hash mismatch: {source.local_pdf}")
        hashes[source.local_pdf] = actual
    return dict(sorted(hashes.items()))


def main() -> None:
    audit = load_direct_ccz_backend_audit(CONFIG_PATH)
    source_hashes = _verify_source_hashes()
    candidate = audit.candidate
    if candidate.backend_admitted:
        raise RuntimeError("audit unexpectedly admitted a finite direct-CCZ backend")
    if not candidate.missing_fields or not candidate.incompatible_fields:
        raise RuntimeError("negative admission must expose missing and incompatible fields")

    audit_data = direct_ccz_backend_audit_to_data(audit)
    summary = {
        "admission": audit_data["admission"],
        "audit_id": audit.audit_id,
        "candidate_id": candidate.candidate_id,
        "compatibility_domain": candidate.compatibility_domain,
        "evidence_qualification": {
            "backend_admission": "OPEN and rejected",
            "finite_bb18_factory_values": (
                "LITERATURE but incompatible with the selected time-efficient backend"
            ),
            "portable_event_semantics": (
                "LITERATURE with reviewed NUMERICAL verification in T-20260831-003"
            ),
            "screened_alternatives": (
                "LITERATURE contributions with CHECK or OPEN compatibility exclusions"
            ),
        },
        "experiment_id": EXPERIMENT_ID,
        "next_executable_research_step": (
            "construct or source-qualify one finite factory-to-consumer adapter with "
            "decoded batch timing before any high-rate schedule is emitted"
        ),
        "output_contract": {
            "high_rate_schedule_emitted": False,
            "reason": "fail-closed admission gate rejected the candidate",
        },
        "source_pdf_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed_negative_admission",
    }

    raw_status = _git("status", "--porcelain").splitlines()
    filtered_status = "\n".join(
        line
        for line in raw_status
        if not line.startswith("?? .claude/")
        and f"experiments/runs/{TASK_ID}/" not in line.replace("\\", "/")
        and not line.startswith("?? tmp/")
    )
    reproducibility = {
        "configuration": str(CONFIG_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "configuration_sha256": _sha256(CONFIG_PATH),
        "git_commit": _git("rev-parse", "HEAD"),
        "input": "source-qualified finite direct-CCZ backend field matrix v1",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": hashlib.sha256(filtered_status.encode()).hexdigest().upper(),
        },
        "random_seed": "not_applicable_deterministic_audit",
        "software_environment": {
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
        "validation_status": "passed_negative_admission",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "direct_ccz_backend_audit.json", audit_data)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    if (OUTPUT_ROOT / "schedule.json").exists():
        raise RuntimeError("a rejected backend must not leave a schedule artifact")
    print(json.dumps(summary["admission"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
