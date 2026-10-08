"""Generate T-20261001-008 two-pass flagged LP preparation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

from ecdlp_ftqc.analysis.lp_flag_preparation import (
    audit_single_faults,
    build_circuit,
    retry_bounds,
    structural_resources,
)
from ecdlp_ftqc.code_constructions.lp_ghz import base_seed, completed_seed, lifted_product
from ecdlp_ftqc.code_constructions.lp_protected_ghz import punctured_mask
from ecdlp_ftqc.verification.lp_direct_ghz import audit_projection_recovery
from ecdlp_ftqc.verification.lp_flag_preparation import dense_uniform_preparation_audit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/manifests/E-20261001-008.json"
_EXPECTED = {
    "schema": "lp-flag-preparation-input-v1",
    "task_id": "T-20261001-008",
    "lift": 75,
    "gadget": "one_flag_bracketing_all_data_CNOTs",
    "projection_passes": 2,
    "primary_check_flag_pairs_per_block": 64,
    "resource_caps": [1, 64, 256, 5250],
    "acceptance": "zero_flags_equal_full_syndromes_valid_image",
    "interpass_correction": False,
    "final_correction": "ideal_classical_Pauli_frame",
    "fault_scope": "all_single_Paulis_CNOT_preparation_reset_live_idle_and_readout_flip",
    "readout_error_sensitivities": [0.0001, 0.001],
    "random_seed": None,
    "full_factory_ft": False,
    "native_seconds": None,
}
_INHERITED = (
    "src/ecdlp_ftqc/code_constructions/lp_ghz.py",
    "src/ecdlp_ftqc/code_constructions/lp_protected_ghz.py",
    "src/ecdlp_ftqc/analysis/lp_ghz_preparation.py",
    "src/ecdlp_ftqc/verification/lp_direct_ghz.py",
)


def load_manifest(path: Path) -> dict[str, Any]:
    """Reject unsupported scopes, malformed values or changed dependencies."""
    config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if set(config) != set(_EXPECTED) | {"inherited_files"}:
        raise ValueError("Unexpected manifest fields")
    for key, expected in _EXPECTED.items():
        if (type(config[key]) is not type(expected)
                or json.dumps(config[key], sort_keys=True) != json.dumps(expected, sort_keys=True)):
            raise ValueError(f"Unsupported manifest field: {key}")
    pins = config["inherited_files"]
    if not isinstance(pins, list) or tuple(p["path"] for p in pins) != _INHERITED:
        raise ValueError("Changed dependency paths")
    for pin in pins:
        if hashlib.sha256((ROOT / pin["path"]).read_bytes()).hexdigest() != pin["sha256"]:
            raise ValueError(f"Dependency hash mismatch: {pin['path']}")
    return config


def validate_result(result: dict[str, Any]) -> None:
    """Fail closed on coverage, accounting, replay and expanded FT admission."""
    if (result["schema"] != "lp-flag-preparation-cycle-v1"
            or result["task_id"] != "T-20261001-008"):
        raise ValueError("Wrong result schema/task")
    for name, expected in (
        ("Q", (9600, 3150, 3134, 81900, 1571, 15080760, 46549980)),
        ("M", (9075, 5250, 5226, 106050, 2131, 19345810, 59739405)),
    ):
        block = result["blocks"][name]
        resources, audit = block["resources"], block["single_fault_audit"]
        actual = (
            resources["data_qubits"], resources["supplied_checks"],
            audit["ideal_independent_sign_bits"], resources["operation_counts"]["cnot"],
            resources["abstract_ticks"], resources["total_idle_locations"],
            audit["total_pauli_fault_cases"],
        )
        if actual != expected or resources["concurrent_check_flag_pairs"] != 64:
            raise ValueError("Changed finite instance/schedule/coverage")
        if (audit["single_fault_residual_weight_at_most_one"] is not True
                or audit["first_accepted_counterexample"] is not None
                or audit["all_valid_ideal_projection_branches"] is not True
                or audit["total_outcomes"].get("accept_bad", 0) != 0
                or audit["row0_third_data_cnot_hook"]["classification"] != "reject_flag"):
            raise ValueError("Single-fault certificate failed")
        cases = sites = 0
        outcomes: dict[str, int] = {}
        for kind, row in audit["fault_classes"].items():
            multiplicity = 15 if kind == "cnot" else 1 if kind.startswith("read_") else 3
            if (row["paulis_per_location"] != multiplicity
                    or row["fault_cases"] != multiplicity * row["locations"]
                    or sum(row["outcomes"].values()) != row["fault_cases"]):
                raise ValueError("Fault multiplicity mismatch")
            rejected = sum(v for k, v in row["outcomes"].items() if k.startswith("reject_"))
            if Fraction(row["linear_rejection_coefficient"]) != Fraction(rejected, multiplicity):
                raise ValueError("Incorrect rejection coefficient")
            if kind.startswith("idle_"):
                if row["locations"] != resources["idle_locations"][kind.removeprefix("idle_")]:
                    raise ValueError("Idle lifetime mismatch")
            elif row["locations"] != resources["operation_counts"][kind]:
                raise ValueError("Operation/fault mismatch")
            for key, value in row["outcomes"].items():
                outcomes[key] = outcomes.get(key, 0) + value
            cases += row["fault_cases"]
            sites += row["locations"]
        if (cases != audit["total_pauli_fault_cases"] or sites != audit["total_locations"]
                or outcomes != audit["total_outcomes"]):
            raise ValueError("Incomplete census")
        if (audit["full_factory_ft"] is not False or audit["native_seconds"] is not None
                or audit["logical_failure_probability"] is not None
                or resources["native_seconds"] is not None or resources["qec_cycles"] is not None
                or block["retry"]["finite_p_acceptance_estimate"] is not None):
            raise ValueError("Unsupported native/factory admission")
        expected_retry = retry_bounds(expected[1], (0.0001, 0.001))
        if block["retry"] != expected_retry:
            raise ValueError("Changed readout assumptions or bounds")
    total = result["combined"]
    if (total["preparation_CNOTs"] != 187950 or total["qubit_peak"] != 18931
            or total["single_fault_cases"] != 106289385
            or total["post_acceptance_Q_wait_idle_locations_if_same_start"] != 5376000
            or total["waiting_is_inside_preparation_certificate"] is not False
            or total["full_GHZ_factory_FT"] is not False):
        raise ValueError("Incorrect combined boundary/accounting")
    grid = result["resource_sensitivity"]
    if [r["check_flag_pair_cap"] for r in grid] != [1, 64, 256, 5250]:
        raise ValueError("Incomplete resource sensitivity")
    for row, expected_grid in zip(grid, (
        (94501, 127051, 907200000, 1152978750, 18679),
        (1571, 2131, 15080760, 19345810, 18931),
        (443, 623, 4268400, 5703470, 19699),
        (53, 47, 637800, 646350, 35475),
    )):
        actual_grid = (row["Q"]["abstract_ticks"], row["M"]["abstract_ticks"],
                       row["Q"]["total_idle_locations"], row["M"]["total_idle_locations"],
                       row["qubit_peak"])
        if actual_grid != expected_grid:
            raise ValueError("Changed resource sensitivity result")
    replay = result["independent_dense_replay"]
    if replay["all_checks_passed"] is not True:
        raise ValueError("Independent dense replay failed")
    for report in replay["axis_reports"].values():
        if (report["bad_accepted_branches"] != 0
                or abs(report["no_fault_acceptance_probability"] - 1) > 1e-12
                or report["accepted_one_pauli_orbit_max_infidelity"] > 1e-12
                or report["max_total_probability_error"] > 1e-12
                or report["drop_flags_negative_control_best_orbit_fidelity"] > 1e-12
                or report["one_pass_readout_negative_control_best_orbit_fidelity"] > 1e-12):
            raise ValueError("Independent dense branch or negative control mismatch")
    projection = result["ideal_preparation_sign_recovery"]
    if (projection["noisy_decoder"] is not False
            or any(item["all_allowed_ideal_syndromes_covered"] is not True
                   for item in projection["maps"].values())):
        raise ValueError("Ideal sign recovery failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/runs/T-20261001-008")
    args = parser.parse_args()
    config = load_manifest(MANIFEST)
    q = lifted_product(completed_seed(), base_seed().adjoint())
    m, _ = punctured_mask()
    blocks = {}
    for name, code, rows, axis in (("Q", q, q.hz, "Z"), ("M", m, m.hx, "X")):
        print(f"Auditing full {name} single-fault maps and weighted live idles...", flush=True)
        circuit = build_circuit(rows, code.n, axis, config["primary_check_flag_pairs_per_block"])
        blocks[name] = {
            "resources": structural_resources(circuit),
            "single_fault_audit": audit_single_faults(circuit),
            "retry": retry_bounds(len(rows), tuple(config["readout_error_sensitivities"])),
        }
    print("Checking ideal sign maps and independent dense measurement branches...", flush=True)
    projection = audit_projection_recovery(q.hz, m.hx, q.n, m.n)
    replay = dense_uniform_preparation_audit()
    sensitivity = []
    for cap in config["resource_caps"]:
        q_resources = structural_resources(build_circuit(q.hz, q.n, "Z", cap))
        m_resources = structural_resources(build_circuit(m.hx, m.n, "X", cap))
        sensitivity.append({
            "check_flag_pair_cap": cap, "Q": q_resources, "M": m_resources,
            "qubit_peak": q_resources["qubit_peak"] + m_resources["qubit_peak"],
            "scope": "structural only; exhaustive full-instance fault census is at cap64",
        })
    result = {
        "schema": "lp-flag-preparation-cycle-v1", "task_id": config["task_id"],
        "blocks": blocks, "resource_sensitivity": sensitivity,
        "ideal_preparation_sign_recovery": projection, "independent_dense_replay": replay,
        "combined": {
            "preparation_CNOTs": 187950, "qubit_peak": 18931,
            "single_fault_cases": sum(b["single_fault_audit"]["total_pauli_fault_cases"]
                                      for b in blocks.values()),
            "post_acceptance_Q_wait_idle_locations_if_same_start": 9600 * (2131 - 1571),
            "waiting_is_inside_preparation_certificate": False,
            "full_GHZ_factory_FT": False,
            "interface_mask_decoder_automorphism_and_buffer_service": "OPEN",
        },
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "inherited_files": config["inherited_files"], "review_status": "PENDING",
    }
    validate_result(result)
    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    summary = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (output / "summary.json").write_text(summary, encoding="utf-8", newline="\n")
    paths = (*_INHERITED, "src/ecdlp_ftqc/analysis/lp_flag_preparation.py",
             "src/ecdlp_ftqc/verification/lp_flag_preparation.py",
             "scripts/run_lp_flag_preparation_cycle.py", "experiments/manifests/E-20261001-008.json")
    repro = {
        "task_id": config["task_id"], "python": sys.version, "numpy": np.__version__,
        "platform": platform.platform(), "random_seed": None,
        "working_tree_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "working_tree_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
        "input_files_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        "summary_sha256": hashlib.sha256(summary.encode()).hexdigest(),
        "output_path": str(output.resolve()), "cross_review": "PENDING",
        "validation": "Full-instance backward Pauli maps, exact idle multiplicities, independent dense branch replay; preparation-only single-fault criterion, not complete factory FT",
    }
    (output / "reproducibility.json").write_text(
        json.dumps(repro, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )
    print(json.dumps({"summary_sha256": repro["summary_sha256"], **result["combined"]}, indent=2))


if __name__ == "__main__":
    main()
