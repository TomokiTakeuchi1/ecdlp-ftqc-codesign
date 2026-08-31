"""Generate deterministic capability-gated clean OOP-QCLA artifacts."""

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
    DirectCczCapabilityError,
    direct_ccz_capability_to_data,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import (
    QCLA_SOURCE_PDF_SHA256,
    build_oop_qcla_trace,
    oop_qcla_metrics,
    oop_qcla_trace_to_data,
    replay_oop_qcla,
)
from ecdlp_ftqc.compiler import lower_oop_qcla_to_direct_ccz_events

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260831-002"
EXPERIMENT_ID = "E-20260831-002"
CAPABILITY_PATH = (
    PROJECT_ROOT / "configs" / "architectures" / "direct_ccz_high_rate_capability_v1.yaml"
)
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
DRAPER_PDF = PROJECT_ROOT / "literature" / "papers" / "quant-ph-0406142v1.pdf"
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "architectures" / "direct_ccz.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz.py",
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
    paths = {DRAPER_PDF}
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    paths.update(PROJECT_ROOT / source.local_pdf for source in capability.sources)
    hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in sorted(paths)
    }
    if hashes[str(DRAPER_PDF.relative_to(PROJECT_ROOT)).replace("\\", "/")] != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("Draper source PDF hash mismatch")
    expected = {source.local_pdf: source.pdf_sha256.upper() for source in capability.sources}
    for path, expected_hash in expected.items():
        if hashes[path] != expected_hash:
            raise RuntimeError(f"capability source PDF hash mismatch: {path}")
    return hashes


def _semantic_verification() -> dict[str, Any]:
    results: dict[str, Any] = {}
    for width in range(2, 7):
        trace = build_oop_qcla_trace(width)
        limit = 1 << width
        checked = 0
        for input_a in range(limit):
            for input_b in range(limit):
                replay_oop_qcla(trace, input_a, input_b)
                checked += 1
        results[str(width)] = {
            "all_passed": True,
            "basis_input_pairs_checked": checked,
            "method": "exhaustive_computational_basis_replay",
        }
    return results


def _metrics(width: int) -> dict[str, int]:
    metrics = oop_qcla_metrics(build_oop_qcla_trace(width))
    return {
        "cnot_count": metrics.cnot_count,
        "dependency_critical_path_gates": metrics.dependency_critical_path_gates,
        "fully_resident_source_values": metrics.fully_resident_source_values,
        "gate_count": metrics.gate_count,
        "peak_toffoli_layer": metrics.peak_toffoli_layer,
        "peak_toffoli_per_layer": metrics.peak_toffoli_per_layer,
        "source_auxiliary_count": metrics.source_auxiliary_count,
        "source_layer_count": metrics.source_layer_count,
        "toffoli_count": metrics.toffoli_count,
    }


def _structural_verification() -> dict[str, Any]:
    results: dict[str, Any] = {}
    for width in (5, 8, 16, 17, 32, 256):
        trace = build_oop_qcla_trace(width)
        replay_oop_qcla(trace, (1 << width) - 1, 1)
        expected_layers = trace.expected_source_layer_count
        metrics = oop_qcla_metrics(trace)
        if expected_layers is None or metrics.source_layer_count != expected_layers:
            raise RuntimeError("OOP-QCLA source layer formula mismatch")
        results[str(width)] = {
            **_metrics(width),
            "all_formulas_passed": True,
            "all_ones_plus_one_replay_passed": True,
            "topological_gate_count": len(trace.topological_order()),
        }
    return results


def main() -> None:
    source_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    semantic = _semantic_verification()
    structural = _structural_verification()
    width_256 = build_oop_qcla_trace(256)
    width_256_metrics = oop_qcla_metrics(width_256)

    strict_rejected = False
    strict_error = ""
    try:
        lower_oop_qcla_to_direct_ccz_events(width_256, capability)
    except DirectCczCapabilityError as exc:
        strict_rejected = True
        strict_error = str(exc)
    if not strict_rejected:
        raise RuntimeError("incomplete direct-CCZ capability unexpectedly emitted events")

    summary = {
        "capability_gate": {
            "conclusion": "OPEN",
            "event_lowering_admitted": capability.event_lowering_admitted,
            "high_rate_schedule_admitted": capability.high_rate_schedule_admitted,
            "missing_for_event_lowering": list(capability.missing_for_event_lowering),
            "missing_for_high_rate_schedule": list(capability.missing_for_high_rate_schedule),
            "strict_rejection_error": strict_error,
            "strict_rejection_passed": strict_rejected,
        },
        "capacity_diagnostic": {
            "j300_logical_capacity": 60,
            "qualification": (
                "source-value occupancy only; direct-CCZ resources, ports, routing, "
                "and operation ancillas are excluded"
            ),
            "width_16_fully_resident_source_values": structural["16"][
                "fully_resident_source_values"
            ],
            "width_17_fully_resident_source_values": structural["17"][
                "fully_resident_source_values"
            ],
            "width_256_fully_resident_source_values": structural["256"][
                "fully_resident_source_values"
            ],
        },
        "evidence_qualification": {
            "capability_conclusion": (
                "OPEN: exact correction map and finite high-rate direct-CCZ backend fields are absent"
            ),
            "generated_counts_and_layers": "NUMERICAL reproduction of LITERATURE formulas",
            "semantic_replay": (
                "NUMERICAL exhaustive computational-basis checks at widths 2--6; not a proof"
            ),
            "source_circuit": "LITERATURE Draper Sections 3, 4.1, and 5.1",
            "source_depth": "source algorithmic layers, not a QEC schedule or runtime",
        },
        "experiment_id": EXPERIMENT_ID,
        "input_configuration": str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "random_seed": "not_applicable_deterministic",
        "semantic_verification": semantic,
        "source_pdf_hashes": source_hashes,
        "structural_verification": structural,
        "task_id": TASK_ID,
        "validation_status": "passed",
        "width_256": _metrics(256),
    }
    demand = {
        "admitted_high_rate_batch_sizes": list(capability.high_rate.admitted_batch_sizes),
        "evidence_status": "NUMERICAL",
        "factory_service_included": False,
        "peak_candidate_layer": width_256_metrics.peak_toffoli_layer,
        "peak_candidate_source_ccz_demand": width_256_metrics.peak_toffoli_per_layer,
        "task_id": TASK_ID,
        "time_unit": "source_algorithmic_layer",
        "timing_exclusions": [
            "backend_batch_admission",
            "decoder_and_classical_reaction",
            "factory_delivery_and_buffering",
            "injection_ports",
            "memory_io",
            "qec_cycles",
            "routing",
            "wall_clock",
        ],
        "total_source_ccz_candidates": width_256_metrics.toffoli_count,
        "width": 256,
        "demand": [
            {"source_algorithmic_layer": layer, "source_ccz_candidates": count}
            for layer, count in width_256_metrics.toffoli_demand_by_layer
        ],
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
        "random_seed": "not_applicable_deterministic",
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
        "validation_status": "passed",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(
        OUTPUT_ROOT / "direct_ccz_capability_gap.json",
        direct_ccz_capability_to_data(capability),
    )
    _write_json(
        OUTPUT_ROOT / "qcla_oop_width256_trace.json",
        oop_qcla_trace_to_data(width_256),
    )
    _write_json(OUTPUT_ROOT / "qcla_oop_width256_ccz_candidates.json", demand)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary["width_256"], indent=2, sort_keys=True))
    print(json.dumps(summary["capability_gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
