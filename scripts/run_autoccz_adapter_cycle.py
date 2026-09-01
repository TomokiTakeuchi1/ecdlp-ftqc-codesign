"""Generate deterministic AutoCCZ adapter-qualification artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

from ecdlp_ftqc.architectures import (
    autoccz_service_audit_to_data,
    load_autoccz_service_audit,
)
from ecdlp_ftqc.verification import (
    autoccz_channel_verification_to_data,
    verify_autoccz_consumption_channel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260901-001"
EXPERIMENT_ID = "E-20260901-001"
CONFIG_PATH = (
    PROJECT_ROOT / "configs" / "architectures" / "autoccz_surface_code_adapter_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "architectures" / "autoccz_adapter.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "verification" / "autoccz_channel.py",
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
    audit = load_autoccz_service_audit(CONFIG_PATH)
    expected = {
        source.local_pdf: source.pdf_sha256 for source in audit.sources
    } | {asset.local_path: asset.sha256 for asset in audit.source_assets}
    actual_hashes: dict[str, str] = {}
    for relative_path, expected_hash in expected.items():
        actual_hash = _sha256(PROJECT_ROOT / relative_path)
        if actual_hash != expected_hash.upper():
            raise RuntimeError(f"AutoCCZ source hash mismatch: {relative_path}")
        actual_hashes[relative_path] = actual_hash
    return dict(sorted(actual_hashes.items()))


def main() -> None:
    audit = load_autoccz_service_audit(CONFIG_PATH)
    source_hashes = _verify_source_hashes()
    verification = verify_autoccz_consumption_channel()
    if not verification.all_passed:
        raise RuntimeError("AutoCCZ logical-channel verification failed")
    if not audit.candidate.adapter_admitted:
        raise RuntimeError("source-native AutoCCZ adapter was not admitted")
    if audit.candidate.service_admitted:
        raise RuntimeError("AutoCCZ service unexpectedly passed the complete gate")
    if len(audit.candidate.missing_fields) != 9:
        raise RuntimeError("AutoCCZ negative service result must retain nine missing fields")
    if audit.candidate.incompatible_fields != ("factory.output_error_probability",):
        raise RuntimeError("AutoCCZ output-error incompatibility changed unexpectedly")

    audit_data = autoccz_service_audit_to_data(audit)
    verification_data = autoccz_channel_verification_to_data(verification)
    summary = {
        "admission": audit_data["admission"],
        "audit_id": audit.audit_id,
        "candidate_id": audit.candidate.candidate_id,
        "compatibility_domain": audit.candidate.compatibility_domain,
        "derived_source_example": audit_data["derived"],
        "evidence_qualification": {
            "adapter": (
                "LITERATURE source-native CCZ-output/fixup-box/Toffoli connection, "
                "with NUMERICAL abstract logical-channel verification"
            ),
            "complete_service": "OPEN and rejected",
            "factory_rates": (
                "NUMERICAL arithmetic from source-defined depths and explicit CHECK "
                "future-hardware timing assumptions"
            ),
            "output_error": (
                "NUMERICAL official-calculator value, but incompatible d1=15/d2=31 "
                "domain instead of the selected d1=17/d2=27 example"
            ),
        },
        "experiment_id": EXPERIMENT_ID,
        "logical_channel": verification_data,
        "next_executable_research_step": (
            "close compatible d1=17/d2=27 output error, decoder throughput, delivery, "
            "finite AutoCCZ buffering/storage, data capacity, and a joint failure budget "
            "before scheduling the width-256 demand trace"
        ),
        "output_contract": {
            "adapter_artifact_emitted": True,
            "width_256_schedule_emitted": False,
            "reason": "complete fail-closed service gate rejected the candidate",
        },
        "source_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed_adapter_and_negative_service_admission",
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
        "input": "source-qualified AutoCCZ surface-code adapter field matrix v1",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": hashlib.sha256(filtered_status.encode()).hexdigest().upper(),
        },
        "random_seed": "not_applicable_deterministic_audit_and_all_branch_check",
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
        "source_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed_adapter_and_negative_service_admission",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "autoccz_service_audit.json", audit_data)
    _write_json(OUTPUT_ROOT / "autoccz_channel_verification.json", verification_data)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    if (OUTPUT_ROOT / "schedule.json").exists():
        raise RuntimeError("a rejected service must not leave a QCLA schedule artifact")
    print(json.dumps(summary["admission"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
