"""Generate deterministic QCLA-to-adaptive-PBC sensitivity artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.circuits import build_qcla_trace, qcla_metrics
from ecdlp_ftqc.codes import load_pbc_mitten_backend_config
from ecdlp_ftqc.compiler import (
    SELINGER_CCX_DECOMPOSITION_ID,
    SELINGER_CCX_SOURCE_ID,
    SELINGER_CCX_SOURCE_PDF_SHA256,
    lower_qcla_phase_exact,
    qcla_logical_lowering_to_data,
    verify_selinger_ccx_channel,
)
from ecdlp_ftqc.scheduler import (
    assess_qcla_resident_capacity,
    qcla_capacity_assessment_to_data,
    schedule_qcla_resident_pbc,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260825-001"
EXPERIMENT_ID = "E-20260825-001"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
CONFIG_PATH = PROJECT_ROOT / "configs" / "codes" / "qcla_j300_pbc_sensitivity_v1.yaml"
CCX_SOURCE_PDF = PROJECT_ROOT / "literature" / "papers" / "1210.0974.pdf"
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "native_lowering.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "pbc_lowering.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "qcla_pbc.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "adaptive_pbc.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "scheduler" / "qcla_pbc.py",
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
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _load_config() -> tuple[dict[str, Any], Path]:
    loaded: Any = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError("QCLA PBC configuration must be a mapping")
    ccx = loaded.get("ccx_lowering")
    adaptive = loaded.get("adaptive_pbc")
    if not isinstance(ccx, dict) or not isinstance(adaptive, dict):
        raise TypeError("QCLA PBC configuration sections must be mappings")
    if loaded.get("configuration_id") != "qcla-j300-resident-pbc-v1-sensitivity":
        raise RuntimeError("unsupported QCLA PBC configuration ID")
    if ccx.get("decomposition_id") != SELINGER_CCX_DECOMPOSITION_ID:
        raise RuntimeError("CCX decomposition ID mismatch")
    if ccx.get("source_id") != SELINGER_CCX_SOURCE_ID:
        raise RuntimeError("CCX source ID mismatch")
    if ccx.get("source_pdf_sha256") != SELINGER_CCX_SOURCE_PDF_SHA256:
        raise RuntimeError("configured CCX source hash mismatch")
    if _sha256(CCX_SOURCE_PDF) != SELINGER_CCX_SOURCE_PDF_SHA256:
        raise RuntimeError("pinned CCX source PDF hash mismatch")
    backend_path = PROJECT_ROOT / str(adaptive["backend_config"])
    return loaded, backend_path


def _compact_schedule(result: object) -> dict[str, Any]:
    schedule = result.schedule
    lowering = result.lowering
    return {
        "capacity": qcla_capacity_assessment_to_data(result.capacity),
        "dependency_only_critical_path_rounds": schedule.dependency_only_critical_path_rounds,
        "factory_mode": schedule.factory_mode,
        "high_rate_batch_count": schedule.high_rate_batch_count,
        "high_rate_operation_count": schedule.high_rate_operation_count,
        "logical_lowering": qcla_logical_lowering_to_data(lowering.logical),
        "pbc_measurement_count": lowering.pbc_trace.measurement_count,
        "pbc_operation_count": len(lowering.pbc_trace.operations),
        "scheduled_rounds": schedule.scheduled_rounds,
        "serialized_operation_rounds": schedule.serialized_operation_rounds,
        "strict_executable": schedule.strict_executable,
        "total_resource_state_demand": schedule.total_resource_state_demand,
        "unresolved_implementations": [
            implementation.value for implementation in schedule.unresolved_implementations
        ],
    }


def main() -> None:
    config, backend_path = _load_config()
    backend = load_pbc_mitten_backend_config(backend_path)
    channel = verify_selinger_ccx_channel()
    if not channel.passed:
        raise RuntimeError("selected Selinger circuit failed independent CCX verification")

    scratch = config["adaptive_pbc"]["scratch_scenarios"]
    scheduled: dict[str, dict[str, Any]] = {}
    for width in config["experiments"]["scheduled_widths"]:
        source = build_qcla_trace(int(width))
        serial = schedule_qcla_resident_pbc(
            source,
            backend,
            scratch_slot_count=int(scratch["serial"]),
            enable_high_rate=False,
            allow_check_assumptions=True,
        )
        high_rate = schedule_qcla_resident_pbc(
            source,
            backend,
            scratch_slot_count=int(scratch["high_rate_xx_10"]),
            enable_high_rate=True,
            allow_check_assumptions=True,
        )
        scheduled[str(width)] = {
            "serial_one_scratch": _compact_schedule(serial),
            "high_rate_ten_scratch": _compact_schedule(high_rate),
        }

    boundaries: dict[str, dict[str, Any]] = {}
    for width in config["experiments"]["capacity_boundary_widths"]:
        source = build_qcla_trace(int(width))
        boundaries[str(width)] = {
            "one_scratch": qcla_capacity_assessment_to_data(
                assess_qcla_resident_capacity(source, backend, scratch_slot_count=1)
            ),
            "ten_scratch": qcla_capacity_assessment_to_data(
                assess_qcla_resident_capacity(source, backend, scratch_slot_count=10)
            ),
        }

    structural_width = int(config["experiments"]["structural_width"])
    structural_trace = build_qcla_trace(structural_width)
    structural_metrics = qcla_metrics(structural_trace)
    structural_lowering = lower_qcla_phase_exact(structural_trace)
    width_structure = {
        **qcla_logical_lowering_to_data(structural_lowering),
        "source_ancilla_count": structural_metrics.source_ancilla_count,
        "source_cnot_count": structural_metrics.cnot_count,
        "source_toffoli_count": structural_metrics.toffoli_count,
        "source_x_count": structural_metrics.x_count,
        "resident_capacity": boundaries[str(structural_width)],
        "adaptive_pbc_trace_constructed": False,
        "rejection_status": "PROVED resident-capacity rejection",
    }

    summary = {
        "ccx_channel_verification": {
            **asdict(channel),
            "evidence_status": channel.evidence_status.value,
        },
        "configuration_id": config["configuration_id"],
        "evidence_qualification": {
            "capacity_inequality": "PROVED integer slot accounting",
            "ccx_channel": "NUMERICAL exhaustive 8x8 unitary comparison up to global phase",
            "ccx_source": "LITERATURE Selinger circuit (1)",
            "logical_and_pbc_counts": "NUMERICAL deterministic lowering",
            "scheduled_rounds": "CHECK sensitivity values; not executable estimates",
        },
        "experiment_id": EXPERIMENT_ID,
        "exclusions": config["exclusions"],
        "scheduled_widths": scheduled,
        "task_id": TASK_ID,
        "validation_status": "passed",
        "width_256": width_structure,
    }
    git_status = _git("status", "--porcelain")
    reproducibility = {
        "configuration": str(CONFIG_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "configuration_sha256": _sha256(CONFIG_PATH),
        "git_commit": _git("rev-parse", "HEAD"),
        "input_circuit": "draper-qcla-inplace-mod2n generated trace v1",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if git_status else "clean",
            "status_sha256": hashlib.sha256(git_status.encode()).hexdigest().upper(),
        },
        "random_seed": "not_applicable_deterministic",
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
        "source_pdf_sha256": _sha256(CCX_SOURCE_PDF),
        "task_id": TASK_ID,
        "validation_status": "passed",
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "capacity_boundaries.json", boundaries)
    _write_json(OUTPUT_ROOT / "qcla_width256_logical_structure.json", width_structure)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps({
        "ccx_max_error": channel.maximum_absolute_error,
        "width14_high_rate_batches": scheduled["14"]["high_rate_ten_scratch"]["high_rate_batch_count"],
        "width256_required_slots_one_scratch": boundaries["256"]["one_scratch"]["total_required_slots"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
