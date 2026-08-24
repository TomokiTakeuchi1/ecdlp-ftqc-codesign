"""Generate deterministic source-pinned artifacts for T-20260824-003."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.circuits import (
    QCLA_SOURCE_ID,
    QCLA_SOURCE_PDF_SHA256,
    build_qcla_trace,
    qcla_metrics,
    qcla_trace_to_data,
    replay_qcla,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260824-003"
EXPERIMENT_ID = "E-20260824-003"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
CONFIG_PATH = PROJECT_ROOT / "configs" / "circuits" / "qcla_inplace_mod2n_v1.yaml"
SOURCE_PDF = PROJECT_ROOT / "literature" / "papers" / "quant-ph-0406142v1.pdf"
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
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


def _load_and_verify_config() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        raise RuntimeError(f"missing QCLA configuration: {CONFIG_PATH}")
    loaded = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError("QCLA configuration must be a mapping")
    source = loaded.get("source")
    arithmetic = loaded.get("arithmetic")
    verification = loaded.get("verification")
    if not all(isinstance(item, dict) for item in (source, arithmetic, verification)):
        raise RuntimeError("QCLA configuration sections must be mappings")
    assert isinstance(source, dict)
    assert isinstance(arithmetic, dict)
    if loaded.get("configuration_id") != "circuit-qcla-inplace-mod2n-v1":
        raise RuntimeError("unsupported QCLA configuration ID")
    if source.get("source_id") != QCLA_SOURCE_ID:
        raise RuntimeError("QCLA source ID mismatch")
    if source.get("pdf_sha256") != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("QCLA configured PDF hash mismatch")
    if arithmetic != {
        "family": "draper_qcla",
        "variant": "in_place_modulo_2n",
        "register_contract": "(A,B)->(A,A+B mod 2^n)",
        "incoming_carry": False,
        "exported_overflow": False,
    }:
        raise RuntimeError("unsupported QCLA arithmetic contract")
    if not SOURCE_PDF.is_file():
        raise RuntimeError(f"missing pinned source PDF: {SOURCE_PDF}")
    if _sha256(SOURCE_PDF) != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("QCLA source PDF hash mismatch")
    return loaded


def _semantic_verification(config: dict[str, Any]) -> dict[str, Any]:
    verification = config["verification"]
    results: dict[str, Any] = {}
    for width in verification["exhaustive_widths"]:
        trace = build_qcla_trace(width)
        limit = 1 << width
        checked = 0
        for input_a in range(limit):
            for input_b in range(limit):
                replay_qcla(trace, input_a, input_b)
                checked += 1
        results[str(width)] = {
            "all_passed": True,
            "basis_input_pairs_checked": checked,
            "method": "exhaustive_computational_basis_replay",
        }

    seed = int(verification["seed"])
    samples = int(verification["seeded_samples_per_width"])
    for width in verification["seeded_widths"]:
        trace = build_qcla_trace(width)
        generator = random.Random(seed + width)
        for _ in range(samples):
            replay_qcla(
                trace,
                generator.randrange(1 << width),
                generator.randrange(1 << width),
            )
        results[str(width)] = {
            "all_passed": True,
            "basis_input_pairs_checked": samples,
            "method": "seeded_computational_basis_replay",
            "seed": seed + width,
        }
    return results


def _metrics_data(width: int) -> dict[str, Any]:
    trace = build_qcla_trace(width)
    metrics = qcla_metrics(trace)
    return {
        "cnot_count": metrics.cnot_count,
        "dependency_critical_path_gates": metrics.dependency_critical_path_gates,
        "gate_count": metrics.gate_count,
        "peak_live_ancillas": metrics.peak_live_ancillas,
        "peak_toffoli_per_source_layer": metrics.peak_toffoli_per_layer,
        "prefix_scratch_count": metrics.prefix_scratch_count,
        "source_ancilla_count": metrics.source_ancilla_count,
        "source_layer_count": metrics.source_layer_count,
        "toffoli_count": metrics.toffoli_count,
        "x_count": metrics.x_count,
    }


def _structural_verification(config: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for width in config["verification"]["structural_widths"]:
        trace = build_qcla_trace(width)
        metrics = qcla_metrics(trace)
        replay_qcla(trace, (1 << width) - 1, 1)
        expected_layers = trace.expected_source_layer_count
        if expected_layers is None or metrics.source_layer_count != expected_layers:
            raise RuntimeError("QCLA source layer formula mismatch")
        results[str(width)] = {
            **_metrics_data(width),
            "all_formulas_passed": True,
            "all_ones_plus_one_replay_passed": True,
            "topological_gate_count": len(trace.topological_order()),
        }
    return results


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    config = _load_and_verify_config()
    semantic = _semantic_verification(config)
    structural = _structural_verification(config)
    width_256 = build_qcla_trace(256)
    width_256_metrics = qcla_metrics(width_256)
    summary = {
        "evidence_qualification": {
            "basis_replay": (
                "NUMERICAL exact reversible-gate computational-basis replay; "
                "small-width exhaustive checks do not constitute a general proof"
            ),
            "generated_counts_and_layers": (
                "NUMERICAL reproduction of LITERATURE closed forms"
            ),
            "source_circuit": (
                "LITERATURE Draper et al. Sections 3, 4.2, and 5.1"
            ),
            "toffoli_demand": (
                "NUMERICAL demand per source algorithmic layer; not factory "
                "service, high-rate surgery, QEC cycles, or wall-clock time"
            ),
        },
        "experiment_id": EXPERIMENT_ID,
        "input_configuration": str(CONFIG_PATH.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "random_seed": config["verification"]["seed"],
        "semantic_verification": semantic,
        "source": {
            "pdf": str(SOURCE_PDF.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "pdf_sha256": _sha256(SOURCE_PDF),
            "source_id": QCLA_SOURCE_ID,
        },
        "structural_verification": structural,
        "task_id": TASK_ID,
        "validation_status": "passed",
        "width_256": _metrics_data(256),
    }
    demand = {
        "evidence_status": "NUMERICAL",
        "task_id": TASK_ID,
        "time_unit": "source_algorithmic_layer",
        "timing_exclusions": [
            "factory_supply_and_buffering",
            "high_rate_surgery_selection",
            "memory_io",
            "qec_cycles",
            "routing",
            "wall_clock",
        ],
        "total_toffoli_demand": width_256_metrics.toffoli_count,
        "width": 256,
        "demand": [
            {"source_algorithmic_layer": layer, "toffoli_demand": count}
            for layer, count in width_256_metrics.toffoli_demand_by_layer
        ],
    }
    git_status = _git("status", "--porcelain")
    reproducibility = {
        "configuration_sha256": _sha256(CONFIG_PATH),
        "git_commit": _git("rev-parse", "HEAD"),
        "input_circuit": "generated_source_exact_qcla_trace_v1",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "project_worktree": {
            "status": "dirty" if git_status else "clean",
            "status_sha256": hashlib.sha256(git_status.encode()).hexdigest().upper(),
        },
        "random_seed": config["verification"]["seed"],
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
        "source_pdf_sha256": _sha256(SOURCE_PDF),
        "task_id": TASK_ID,
        "validation_status": "passed",
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(OUTPUT_ROOT / "summary.json", summary)
    _write_json(OUTPUT_ROOT / "qcla_width8_trace.json", qcla_trace_to_data(build_qcla_trace(8)))
    _write_json(OUTPUT_ROOT / "qcla_width256_structure.json", qcla_trace_to_data(width_256))
    _write_json(OUTPUT_ROOT / "qcla_width256_toffoli_demand.json", demand)
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary["width_256"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
