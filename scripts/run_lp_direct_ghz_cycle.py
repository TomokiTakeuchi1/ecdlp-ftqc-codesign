"""Generate T-20261001-006 retained-block LP GHZ evidence and provenance."""

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

from ecdlp_ftqc.analysis.lp_ghz_preparation import audit_preparation
from ecdlp_ftqc.code_constructions.lp_direct_ghz import (
    audit_direct_instance,
    build_direct_certificate,
)
from ecdlp_ftqc.verification.lp_direct_ghz import (
    audit_projection_recovery,
    dense_direct_ghz_audit,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/manifests/E-20261001-006.json"
_EXPECTED = {
    "schema": "lp-direct-ghz-input-v1",
    "task_id": "T-20261001-006",
    "lift": 75,
    "construction": "retain_masked_Q_then_automorphism",
    "selected_canonical_row_zero_based": 3,
    "residual_fixing_allowed": True,
    "outcome_postselection": False,
    "ancilla_caps_per_block": [1, 64, 256, 5250],
    "preparation_projection_passes": 1,
    "fault_scope": "spreading_axis_check_ancilla_faults_and_mask_readout_flips",
    "random_seed": None,
    "native_runtime_seconds": None,
    "ft_admission": False,
}
_INHERITED = (
    "src/ecdlp_ftqc/code_constructions/lp_ghz.py",
    "src/ecdlp_ftqc/code_constructions/lp_protected_ghz.py",
    "experiments/runs/T-20261001-004/summary.json",
)


def load_manifest(path: Path) -> dict[str, Any]:
    """Fail closed on unsupported models and changed approved dependencies."""
    config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if set(config) != set(_EXPECTED) | {"inherited_files"}:
        raise ValueError("Unexpected manifest fields")
    for key, expected in _EXPECTED.items():
        if type(config[key]) is not type(expected) or config[key] != expected:
            raise ValueError(f"Unsupported manifest field: {key}")
    pins = config["inherited_files"]
    if not isinstance(pins, list) or tuple(pin["path"] for pin in pins) != _INHERITED:
        raise ValueError("Missing or changed inherited evidence paths")
    for pin in pins:
        source = (ROOT / pin["path"]).resolve()
        if not source.is_relative_to(ROOT):
            raise ValueError("Evidence path escapes repository")
        if hashlib.sha256(source.read_bytes()).hexdigest() != pin["sha256"]:
            raise ValueError(f"Evidence hash mismatch: {pin['path']}")
    return config


def validate_result(result: dict[str, Any]) -> None:
    """Guard the exact instance and the distinction between ideal and FT claims."""
    if result["task_id"] != "T-20261001-006":
        raise ValueError("Wrong task")
    ideal = result["ideal_certificate"]
    if ideal["lift"] != 75 or any(ideal["checks"].values()):
        raise ValueError("Failed full-instance certificate")
    output = ideal["output"]
    if tuple(output[k] for k in (
        "physical_carriers", "logical_qubits", "ghz4_count",
        "verified_canonical_ghz_stabilizers", "residual_z_fixed", "residual_x_retained",
    )) != (9600, 1240, 300, 1200, 38, 2):
        raise ValueError("Changed direct GHZ output")
    readout = ideal["readout_map"]
    if tuple(readout[k] for k in (
        "physical_Z_readout_bits", "allowed_ideal_readout_space_dimension",
        "readout_gauge_dimension", "independent_logical_outcome_bits",
    )) != (9075, 6164, 5226, 938):
        raise ValueError("Changed all-outcome map")
    if (readout["postselection_on_logical_outcomes"] is not False
            or output["canonical_residual_factorization"] is not True
            or ideal["admission"]["general_arbitrary_data_measurement_equivalence"] is not False):
        raise ValueError("Unsupported channel or postselection claim")
    prep = result["preparation_and_fault_diagnostic"]
    costs = prep["structural_resources"]
    if tuple(costs[k] for k in (
        "concurrent_code_carriers", "preparation_check_cnots", "interface_cnots",
        "total_cnots_before_automorphism", "interface_matching_layers",
        "destructive_output_readouts",
    )) != (18675, 77175, 9075, 86250, 1, 0):
        raise ValueError("Changed structural cost")
    if costs["interface_matching_layer_is_qec_cycle"] is not False:
        raise ValueError("Matching stage is not a QEC cycle")
    if prep["preparation"]["projection_pass_is_ft_initialization"] is not False:
        raise ValueError("Bare projection pass is not FT initialization")
    fault = prep["bounded_fault_diagnostic"]
    obstruction = fault["record_blind_common_recovery_obstruction"]
    if (fault["total_enumerated_fault_events"] != 86250
            or obstruction["evidence"] != "FALSIFIED"
            or obstruction["harmless_coset_minimum_weight"] != 3
            or obstruction["signature_audit"]["no_representative_of_weight_at_most_two"] is not True
            or obstruction["no_fault_and_fault_actual_record_deltas_identical"] is not True):
        raise ValueError("Bounded bare-baseline obstruction not certified")
    for item in (ideal["admission"], prep["admission"]):
        if item["fault_tolerant_factory"] is not False or item["logical_failure_probability"] is not None:
            raise ValueError("Unsupported FT or failure admission")
    if (ideal["admission"]["native_runtime_seconds"] is not None
            or prep["symbolic_time"]["native_seconds"] is not None
            or prep["symbolic_time"]["qec_rounds"] is not None):
        raise ValueError("Unsupported native timing")
    dense = result["independent_dense_replay"]
    if (dense["all_checks_passed"] is not True
            or dense["nonzero_branches"] != 16
            or dense["pre_and_post_automorphism_frame_max_residual"] >= 1e-12
            or dense["physical_fault_tolerance_certified"] is not False):
        raise ValueError("Dense signed replay failed")
    projection = result["ideal_preparation_sign_recovery"]
    if (projection["noisy_decoder"] is not False
            or projection["maps"]["Q_Z_projection"]["independent_ideal_sign_bits"] != 3134
            or projection["maps"]["M_X_projection"]["independent_ideal_sign_bits"] != 5226):
        raise ValueError("Invalid ideal preparation sign recovery")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/runs/T-20261001-006")
    args = parser.parse_args()
    config = load_manifest(MANIFEST)
    print("Certifying the retained LP output and every ideal mask outcome...", flush=True)
    ideal = audit_direct_instance()
    certificate = build_direct_certificate()
    print("Checking independent signed replay and preparation sign maps...", flush=True)
    projection = audit_projection_recovery(
        certificate.output_code.hz, certificate.mask_code.hx,
        certificate.output_code.n, certificate.mask_code.n,
    )
    print("Scheduling one bare projection pass and auditing bounded faults...", flush=True)
    prep = audit_preparation(ancilla_caps=tuple(config["ancilla_caps_per_block"]))
    result = {
        "schema": "lp-direct-ghz-cycle-v1",
        "task_id": config["task_id"],
        "ideal_certificate": ideal,
        "independent_dense_replay": dense_direct_ghz_audit(),
        "ideal_preparation_sign_recovery": projection,
        "preparation_and_fault_diagnostic": prep,
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "inherited_files": config["inherited_files"],
        "review_status": "PENDING",
    }
    validate_result(result)
    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    summary = json.dumps(result, sort_keys=True, indent=2) + "\n"
    (output / "summary.json").write_text(summary, encoding="utf-8", newline="\n")
    sources = [
        *_INHERITED,
        "src/ecdlp_ftqc/code_constructions/lp_direct_ghz.py",
        "src/ecdlp_ftqc/analysis/lp_ghz_preparation.py",
        "src/ecdlp_ftqc/verification/lp_direct_ghz.py",
        "scripts/run_lp_direct_ghz_cycle.py",
        "experiments/manifests/E-20261001-006.json",
    ]
    repro = {
        "task_id": config["task_id"],
        "python": sys.version,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "random_seed": None,
        "working_tree_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip(),
        "working_tree_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True,
        ).splitlines(),
        "input_files_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
        "summary_sha256": hashlib.sha256(summary.encode()).hexdigest(),
        "output_path": str(output.resolve()),
        "validation": "full-size exact GF2 certificate; independent reduced dense replay; ideal projection right inverses; bounded bare-hook diagnostic, not full FT",
        "cross_review": "PENDING",
    }
    (output / "reproducibility.json").write_text(
        json.dumps(repro, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    print(json.dumps({
        "summary_sha256": repro["summary_sha256"],
        "output": ideal["output"],
        "resources": prep["structural_resources"],
    }, indent=2))


if __name__ == "__main__":
    main()
