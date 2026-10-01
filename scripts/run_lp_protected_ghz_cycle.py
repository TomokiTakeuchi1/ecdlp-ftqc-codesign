"""Generate the bounded T-20261001-004 protected LP masking certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from ecdlp_ftqc.code_constructions.lp_protected_ghz import audit_masked_instance
from ecdlp_ftqc.verification.lp_masked_channel import dense_masked_channel_audit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/manifests/E-20261001-004.json"


def load_manifest(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema": "lp-protected-ghz-input-v1",
        "task_id": "T-20261001-004",
        "lift": 75,
        "selected_canonical_row_zero_based": 3,
        "punctured_completed_seed_column_zero_based": 6,
        "construction": "uniform_plus_full_LP_then_Z_mask_then_X_readout",
        "residual_measurements_allowed": True,
        "maximum_error_weight_checked": 2,
        "random_seed": None,
        "native_runtime_seconds": None,
        "ft_admission": False,
    }
    if set(config) != set(expected) | {"sources", "inherited_files"}:
        raise ValueError("Unexpected or missing manifest fields")
    for key, value in expected.items():
        if type(config[key]) is not type(value) or config[key] != value:
            raise ValueError(f"Unsupported manifest value: {key}")
    if len(config["sources"]) != 3 or len(config["inherited_files"]) != 1:
        raise ValueError("Missing source or inherited evidence pins")
    for source in config["sources"] + config["inherited_files"]:
        if "path" in source:
            source_path = (ROOT / source["path"]).resolve()
            if not source_path.is_relative_to(ROOT):
                raise ValueError("Evidence path escapes repository")
            if hashlib.sha256(source_path.read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"Evidence hash mismatch: {source['path']}")
    return config


def validate_result(result: dict[str, Any]) -> None:
    """Fail closed on unsupported admission or inconsistent finite counts."""
    if result["task_id"] != "T-20261001-004" or result["lift"] != 75:
        raise ValueError("Wrong finite instance")
    if any(result["checks"].values()):
        raise ValueError("Nonzero algebraic certificate failure")
    measured = result["measured_algebra"]
    if (
        measured["mask_independent_z_measurements"],
        measured["final_canonical_x_measurements"],
        measured["final_residual_x_measurements"],
        measured["effective_auxiliary_logical_qubits"],
    ) != (938, 300, 2, 302):
        raise ValueError("Changed measured algebra")
    for report in result["distance_audits"].values():
        if not report["both_distances_at_least_3_certified"]:
            raise ValueError("Required finite distance threshold not certified")
        for axis in ("X", "Z"):
            for weight in ("weight_1", "weight_2"):
                if report[axis][weight]["logical_errors"] != 0:
                    raise ValueError("Low-weight logical remains")
    admission = result["admission"]
    if (
        admission["fault_tolerant_factory"] is not False
        or admission["native_speedup"] is not False
        or admission["postselection_on_logical_outcomes"] is not False
        or admission["signed_outcomes_require_x_frame_correction_or_propagation"] is not True
    ):
        raise ValueError("Unsupported FT, timing or signed-channel admission")
    cost = result["structural_cost"]
    if (cost["total_interface_cnots"], cost["ordered_interface_matching_layers"]) != (18675, 2):
        raise ValueError("Inconsistent structural interface cost")
    for key in (
        "native_initialization_rounds",
        "native_runtime_seconds",
        "logical_failure_probability",
    ):
        if cost[key] is not None:
            raise ValueError("Unsupported native cost")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/runs/T-20261001-004")
    args = parser.parse_args()
    config = load_manifest(MANIFEST)
    print("Auditing full-binary LP mask and complete measured algebra...", flush=True)
    result = audit_masked_instance()
    print("Auditing signed two-stage logical channel...", flush=True)
    result["independent_signed_channel"] = dense_masked_channel_audit()
    result["sources"] = config["sources"]
    result["inherited_files"] = config["inherited_files"]
    result["manifest_sha256"] = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    validate_result(result)
    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    summary = json.dumps(result, sort_keys=True, indent=2) + "\n"
    (output / "summary.json").write_text(summary, encoding="utf-8", newline="\n")
    files = [
        "src/ecdlp_ftqc/code_constructions/lp_ghz.py",
        "src/ecdlp_ftqc/code_constructions/lp_protected_ghz.py",
        "src/ecdlp_ftqc/verification/lp_protected_ghz.py",
        "src/ecdlp_ftqc/verification/lp_masked_channel.py",
        "scripts/run_lp_protected_ghz_cycle.py",
        "experiments/manifests/E-20261001-004.json",
    ]
    repro = {
        "task_id": "T-20261001-004",
        "python": sys.version,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "random_seed": None,
        "working_tree_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "input_files_sha256": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files
        },
        "summary_sha256": hashlib.sha256(summary.encode()).hexdigest(),
        "output_path": str(output.resolve()),
        "validation": "exact whole-algebra rank certificate; independent complete weight<=2 audit; independent signed-channel replay",
        "cross_review": "PENDING",
    }
    (output / "reproducibility.json").write_text(
        json.dumps(repro, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "summary_sha256": repro["summary_sha256"],
                "measured_algebra": result["measured_algebra"],
                "structural_cost": result["structural_cost"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
