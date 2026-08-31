"""Generate deterministic single-event direct-CCZ verification artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from itertools import product
from pathlib import Path
from typing import Any

from ecdlp_ftqc.architectures import (
    DIRECT_CCZ_FIGURE14_CORRECTION_MAP,
    direct_ccz_capability_to_data,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import (
    QCLA_SOURCE_PDF_SHA256,
    build_oop_qcla_trace,
    oop_qcla_metrics,
)
from ecdlp_ftqc.compiler import (
    direct_ccz_event_trace_to_data,
    lower_oop_qcla_to_direct_ccz_events,
)
from ecdlp_ftqc.verification import (
    direct_ccz_branch_correction,
    direct_ccz_injection_verification_to_data,
    verify_direct_ccz_injection_channel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260831-003"
EXPERIMENT_ID = "E-20260831-003"
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
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "verification" / "direct_ccz_injection.py",
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
    paths = {DRAPER_PDF, *(PROJECT_ROOT / source.local_pdf for source in capability.sources)}
    hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in sorted(paths)
    }
    draper_key = str(DRAPER_PDF.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if hashes[draper_key] != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("Draper source PDF hash mismatch")
    for source in capability.sources:
        if hashes[source.local_pdf] != source.pdf_sha256.upper():
            raise RuntimeError(f"capability source PDF hash mismatch: {source.local_pdf}")
    return hashes


def _truth_table() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_bits in product((0, 1), repeat=6):
        zz_bits = (raw_bits[0], raw_bits[1], raw_bits[2])
        x_bits = (raw_bits[3], raw_bits[4], raw_bits[5])
        correction = direct_ccz_branch_correction(zz_bits, x_bits)
        rows.append(
            {
                "conditional_cz_exponents": list(correction.conditional_cz_exponents),
                "pauli_exponents": list(correction.pauli_exponents),
                "x_bits": list(x_bits),
                "zz_bits": list(zz_bits),
            }
        )
    return rows


def main() -> None:
    source_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    verification = verify_direct_ccz_injection_channel()
    if not verification.all_passed:
        raise RuntimeError("direct-CCZ injection channel verification failed")
    if not capability.event_lowering_admitted:
        raise RuntimeError("verified single-event capability was not admitted")
    if (
        capability.injection.correction.outcome_bit_convention
        != verification.outcome_bit_convention
    ):
        raise RuntimeError("capability and independent verifier use different bit conventions")
    if capability.high_rate_schedule_admitted:
        raise RuntimeError("single-event evidence unexpectedly admitted high-rate scheduling")

    source = build_oop_qcla_trace(256)
    metrics = oop_qcla_metrics(source)
    event_trace = lower_oop_qcla_to_direct_ccz_events(source, capability)
    if len(event_trace.injection_events) != metrics.toffoli_count:
        raise RuntimeError("direct-CCZ event count does not conserve source Toffolis")
    if event_trace.complete_native_schedule:
        raise RuntimeError("event trace cannot claim a complete native schedule")

    ppm_count = sum(len(event.ppms) for event in event_trace.injection_events)
    reaction_token_count = sum(
        len(event.reaction_dependencies) for event in event_trace.injection_events
    )
    if ppm_count != 6 * metrics.toffoli_count or reaction_token_count != ppm_count:
        raise RuntimeError("six-PPM/reaction-token conservation failed")

    summary = {
        "capability": {
            "capability_id": capability.capability_id,
            "event_lowering_admitted": capability.event_lowering_admitted,
            "high_rate_schedule_admitted": capability.high_rate_schedule_admitted,
            "missing_for_high_rate_schedule": list(
                capability.missing_for_high_rate_schedule
            ),
            "outcome_bit_convention": (
                capability.injection.correction.outcome_bit_convention
            ),
        },
        "channel_verification": direct_ccz_injection_verification_to_data(verification),
        "evidence_qualification": {
            "correction_map": (
                "NUMERICAL operator reconstruction of LITERATURE Figure 14(a); "
                "not a formal proof"
            ),
            "event_trace": "NUMERICAL typed semantic trace without native timing",
            "high_rate_backend": "OPEN and rejected",
            "source_qcla": "LITERATURE with previously reviewed NUMERICAL trace",
        },
        "experiment_id": EXPERIMENT_ID,
        "input_configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "random_seed": "not_applicable_deterministic_operator_check",
        "source_pdf_hashes": source_hashes,
        "task_id": TASK_ID,
        "validation_status": "passed",
        "width_256_event_trace": {
            "basis_change_count": 2 * metrics.toffoli_count,
            "complete_native_schedule": event_trace.complete_native_schedule,
            "conditional_cz_expression_count": 3 * metrics.toffoli_count,
            "direct_ccz_injection_event_count": len(event_trace.injection_events),
            "pauli_correction_expression_count": 3 * metrics.toffoli_count,
            "passthrough_cnot_count": len(event_trace.passthrough_clifford_gate_ids),
            "ppm_count": ppm_count,
            "reaction_outcome_token_count": reaction_token_count,
            "source_dependency_count": len(event_trace.source_dependencies),
            "source_layer_count": metrics.source_layer_count,
            "source_peak_ccz_candidates": metrics.peak_toffoli_per_layer,
            "source_peak_layer": metrics.peak_toffoli_layer,
        },
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
        "configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "configuration_sha256": _sha256(CAPABILITY_PATH),
        "git_commit": _git("rev-parse", "HEAD"),
        "input_circuit": "draper-clean-oop-qcla-mod2n generated trace v1",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if filtered_status else "clean",
            "status_sha256": hashlib.sha256(filtered_status.encode()).hexdigest().upper(),
        },
        "random_seed": "not_applicable_deterministic_operator_check",
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

    truth_table = {
        "correction_expressions": list(DIRECT_CCZ_FIGURE14_CORRECTION_MAP),
        "evidence_status": "NUMERICAL",
        "outcome_bit_convention": verification.outcome_bit_convention,
        "rows": _truth_table(),
        "source": "Litinski and Nickerson arXiv:2211.15465v1 Figure 14(a)",
        "task_id": TASK_ID,
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(
        OUTPUT_ROOT / "direct_ccz_injection_channel_verification.json",
        direct_ccz_injection_verification_to_data(verification),
    )
    _write_json(OUTPUT_ROOT / "direct_ccz_correction_truth_table.json", truth_table)
    _write_json(
        OUTPUT_ROOT / "qcla_oop_width256_direct_ccz_events.json",
        direct_ccz_event_trace_to_data(event_trace),
    )
    _write_json(
        OUTPUT_ROOT / "direct_ccz_single_event_capability.json",
        direct_ccz_capability_to_data(capability),
    )
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary["channel_verification"], indent=2, sort_keys=True))
    print(json.dumps(summary["width_256_event_trace"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
