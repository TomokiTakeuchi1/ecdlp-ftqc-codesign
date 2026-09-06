"""Generate the H/CNOT logical-strategy and QEC-option audit."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from math import ceil
from pathlib import Path
from typing import Any

from ecdlp_ftqc.analysis import (
    analyze_qcla_clifford_demand,
    build_execution_options,
    build_strategy_matrix,
    execution_option_to_data,
    strategy_effect_to_data,
    variant_clifford_demand_to_data,
)
from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.verification import (
    qcla_clifford_strategy_replay_to_data,
    replay_qcla_clifford_strategy,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260905-001"
EXPERIMENT_ID = "E-20260905-001"
WIDTH = 256
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
DRAPER_PDF = PROJECT_ROOT / "literature" / "papers" / "quant-ph-0406142v1.pdf"
RASCQL_PDF = PROJECT_ROOT / "literature" / "papers" / "2602.14273v2.pdf"
XU_PDF = PROJECT_ROOT / "literature" / "papers" / "2407.18490v1.pdf"
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "analysis" / "qcla_clifford_strategy.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "qcla_clifford_strategy_replay.py",
    PROJECT_ROOT / "docs" / "HIGH_RATE_QCLA_H_CNOT_STRATEGY_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260905-001.yaml",
    Path(__file__),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest().upper()


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


def _filtered_worktree_status() -> str:
    lines = _git("status", "--porcelain").splitlines()
    return "\n".join(
        line
        for line in lines
        if not line.startswith("?? .claude/")
        and f"experiments/runs/{TASK_ID}/" not in line.replace("\\", "/")
    )


def _layer_envelope(demand: dict[str, Any]) -> dict[str, Any]:
    baseline = int(demand["direct_ccz_ppm_candidate_level_count"])
    return {
        "baseline_direct_ccz_ppm_candidate_levels": baseline,
        "co_design_conditional_best_case": {
            "total_online_primitive_layers": baseline,
            "condition": (
                "all source CNOT-layer transforms are virtual and opening/closing H "
                "is absorbed into an admitted complete direct-CCZ event instruction"
            ),
            "evidence_status": "OPEN",
        },
        "simd_or_one_layer_addressable_h_plus_simd_cnot": {
            "closing_h_overlaps_resource_x_total_layers": (
                baseline
                + int(demand["direct_h_closing_overlap_added_gate_layers"])
                + int(demand["simd_cnot_strict_added_gate_layers"])
            ),
            "strictly_serialized_total_layers": (
                baseline
                + int(demand["direct_h_strict_added_gate_layers"])
                + int(demand["simd_cnot_strict_added_gate_layers"])
            ),
            "condition": (
                "bare H is safe only after frame materialization or a target-specific "
                "proof; global H-SWAP additionally requires block packing"
            ),
            "evidence_status": "NUMERICAL logical layer envelope",
        },
        "one_bit_h_plus_measurement_cnot": {
            "closing_h_teleport_overlaps_resource_x_total_ppm_layers": (
                baseline
                + int(demand["h_teleport_closing_overlap_added_ppm_layers"])
                + int(demand["cnot_teleport_axis_aligned_added_ppm_layers"])
            ),
            "strictly_serialized_total_ppm_layers": (
                baseline
                + int(demand["h_teleport_strict_added_ppm_layers"])
                + int(demand["cnot_teleport_strict_added_ppm_layers"])
            ),
            "condition": (
                "all |0>/|+> ancillas are provisioned; bare H still requires frame "
                "materialization; mixed ZX support is admitted by the native mapper"
            ),
            "evidence_status": "NUMERICAL logical layer envelope",
        },
    }


def _rascql_domain_comparator(demand: dict[str, Any]) -> dict[str, Any]:
    h_seconds = 0.0019
    t_cnot_seconds = 0.003
    resource_x_seconds = 0.0005
    toffoli_layers = int(demand["toffoli_bearing_source_layer_count"])
    h_layers = int(demand["h_parallel_layer_count"])
    cnot_layers = int(demand["cnot_bearing_source_layer_count"])
    h_strict = h_layers * h_seconds
    h_overlap = toffoli_layers * (
        h_seconds + max(0.0, h_seconds - resource_x_seconds)
    )
    cnot = cnot_layers * t_cnot_seconds
    return {
        "source_domain": "RASCqL [[450,32,8]] HGPS on the paper's RNAA model",
        "qec_cycle_seconds": 0.0039,
        "h_swap_execution_seconds_per_layer": h_seconds,
        "t_cnot_execution_seconds_per_layer": t_cnot_seconds,
        "global_x_or_z_measurement_seconds": resource_x_seconds,
        "possible_relabel_debt_seconds_before_later_t_cnot": 0.0024,
        "strict_h_plus_t_cnot_added_seconds": round(h_strict + cnot, 10),
        "closing_h_x_overlap_plus_t_cnot_added_seconds": round(
            h_overlap + cnot, 10
        ),
        "applies_to_current_direct_ccz_high_rate_backend": False,
        "reason_not_admitted": (
            "the source times assume the RASCqL HGPS/RNAA ISA and do not provide "
            "a compatible direct-CCZ consumer, arbitrary subset H, or QCLA layer mapping"
        ),
        "evidence_status": "CHECK arithmetic from LITERATURE inputs",
    }


def _simd_packing_lower_envelope(demand: dict[str, Any]) -> dict[str, int | str]:
    lanes = 32
    source_layers = list(demand["source_layers"])
    h_block_layers = sum(
        ceil(int(layer["toffoli_gate_count"]) / lanes)
        for layer in source_layers
        if int(layer["toffoli_gate_count"]) > 0
    )
    cnot_block_pairs = sum(
        ceil(int(layer["cnot_gate_count"]) / lanes)
        for layer in source_layers
        if int(layer["cnot_gate_count"]) > 0
    )
    h_gates = int(demand["h_gate_count"])
    cnot_gates = int(demand["source_cnot_gate_count"])
    return {
        "logical_lanes_per_block": lanes,
        "h_swap_block_invocations_opening_plus_closing": 2 * h_block_layers,
        "peak_simultaneous_h_swap_blocks": max(
            (
                ceil(int(layer["toffoli_gate_count"]) / lanes)
                for layer in source_layers
            ),
            default=0,
        ),
        "unused_h_lane_invocations": 2 * h_block_layers * lanes - h_gates,
        "t_cnot_block_pair_invocations": cnot_block_pairs,
        "peak_simultaneous_t_cnot_block_pairs": max(
            (
                ceil(int(layer["cnot_gate_count"]) / lanes)
                for layer in source_layers
            ),
            default=0,
        ),
        "unused_cnot_pair_lanes": cnot_block_pairs * lanes - cnot_gates,
        "qualification": (
            "optimistic perfect-packing lower envelope; placement, movement, and "
            "protection of other live logical values are excluded"
        ),
    }


def main() -> None:
    strategy = [strategy_effect_to_data(item) for item in build_strategy_matrix()]
    execution = [execution_option_to_data(item) for item in build_execution_options()]
    demands = [
        variant_clifford_demand_to_data(
            analyze_qcla_clifford_demand(build_oop_qcla_trace(WIDTH), variant="oop")
        ),
        variant_clifford_demand_to_data(
            analyze_qcla_clifford_demand(build_qcla_trace(WIDTH), variant="ip")
        ),
    ]
    replay = replay_qcla_clifford_strategy(strategy, demands, execution)
    replay_data = qcla_clifford_strategy_replay_to_data(replay)
    demand_by_variant = {str(row["variant"]): row for row in demands}
    layer_envelopes = {
        variant: _layer_envelope(demand_by_variant[variant])
        for variant in ("oop", "ip")
    }
    rascql_comparators = {
        variant: _rascql_domain_comparator(demand_by_variant[variant])
        for variant in ("oop", "ip")
    }
    summary = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "width": WIDTH,
        "state_convention": "physical_state=C_dagger|logical_state>",
        "reviewed_current_choice": {
            "H": "clifford_conjugated_logical",
            "CNOT": "bare_logical",
            "reason": (
                "this preserves the Z-only direct-CCZ phase-one invariant while "
                "avoiding branch-dependent conjugated CNOT synthesis"
            ),
        },
        "algebraic_findings": {
            "CNOT": (
                "all three modes preserve Z-only phase-one PPMs because X/Z/CNOT/CZ "
                "is a Z-preserving subgroup; support can still grow and depend on outcomes"
            ),
            "H": (
                "only frame-conjugated logical H preserves the existing downstream "
                "Z-only guarantee in general; bare or tracked H can produce X/mixed/Y"
            ),
            "H_y_witness": (
                "for stored C=[CNOT(t->c),CZ(c,t)] and future Z_t, appending H or "
                "using H C H presents a Pauli with Y on c and t"
            ),
            "resource_readout": (
                "direct-CCZ phase-two resource measurements stay X-only because the "
                "resource values are globally fresh and absent from the data frame"
            ),
            "H_teleportation": (
                "the self-derived ZX/X gadget is NUMERICAL and passes exact all-four-"
                "branch operator verification; Xu Figure 11(c) sources only CNOT"
            ),
        },
        "width_256": {
            variant: {
                "source_cnot_gates": demand_by_variant[variant]["source_cnot_gate_count"],
                "source_cnot_layers": demand_by_variant[variant][
                    "cnot_bearing_source_layer_count"
                ],
                "direct_ccz_events": demand_by_variant[variant][
                    "source_toffoli_gate_count"
                ],
                "opening_plus_closing_h_gates": demand_by_variant[variant]["h_gate_count"],
                "h_parallel_layers": demand_by_variant[variant]["h_parallel_layer_count"],
                "direct_ccz_ppm_candidate_levels": demand_by_variant[variant][
                    "direct_ccz_ppm_candidate_level_count"
                ],
                "maximum_parallel_cnot_gates": demand_by_variant[variant][
                    "maximum_parallel_cnot_gate_count"
                ],
                "maximum_parallel_h_gates": demand_by_variant[variant][
                    "maximum_parallel_h_gate_count"
                ],
            }
            for variant in ("oop", "ip")
        },
        "layer_envelopes": layer_envelopes,
        "rascql_source_domain_comparators": rascql_comparators,
        "simd_32_lane_packing_lower_envelopes": {
            variant: _simd_packing_lower_envelope(demand_by_variant[variant])
            for variant in ("oop", "ip")
        },
        "runtime_formulas": {
            "direct_or_simd_h_strict": "2 L_T tau_H",
            "direct_or_simd_h_with_closing_overlap": (
                "L_T [tau_H + max(0, tau_H - tau_resource_X)]"
            ),
            "one_bit_h_strict": "2 L_T (tau_ZX + tau_X + tau_react_H)",
            "one_bit_h_with_closing_overlap": (
                "L_T [tau_Htel + max(0, tau_Htel - tau_resource_X)]"
            ),
            "simd_cnot": "L_C tau_tCNOT",
            "measurement_cnot": "L_C (tau_ZZ + tau_XX + tau_Z + tau_react_CNOT)",
            "definitions": {
                "L_T": "source layers containing direct-CCZ events",
                "L_C": "source layers containing CNOTs",
                "tau_Htel": "tau_ZX + tau_X + tau_react_H",
            },
        },
        "finite_outputs": {
            "current_backend_logical_cycles": None,
            "current_backend_runtime_seconds": None,
            "physical_qubits": None,
            "failure_probability": None,
        },
        "validation_status": (
            "passed_exact_source_layer_extraction_independent_replay_and_"
            "h_teleportation_all_branch_operator_check"
        ),
    }
    source_pdfs = (DRAPER_PDF, RASCQL_PDF, XU_PDF)
    source_pdf_hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in source_pdfs
    }
    primary_outputs = {
        "strategy_matrix.json": strategy,
        "width_256_clifford_demand.json": demands,
        "execution_options.json": execution,
        "independent_replay.json": replay_data,
        "summary.json": summary,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, value in primary_outputs.items():
        _write_json(OUTPUT_ROOT / name, value)

    filtered_status = _filtered_worktree_status()
    reproducibility = {
        "task_id": TASK_ID,
        "experiment_id": EXPERIMENT_ID,
        "git_branch": _git("branch", "--show-current"),
        "git_head": _git("rev-parse", "HEAD"),
        "input_trace": "reviewed deterministic OOP/IP QCLA width-256 source traces",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "output_sha256": {
            name: _sha256(OUTPUT_ROOT / name) for name in sorted(primary_outputs)
        },
        "package_versions": {
            name: importlib.metadata.version(name)
            for name in ("mypy", "pytest", "pyyaml", "ruff")
        },
        "platform": platform.platform(),
        "python": sys.version,
        "random_seed": "not_applicable_deterministic_analysis",
        "source_binding_sha256": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "source_pdf_hashes": source_pdf_hashes,
        "validation_status": summary["validation_status"],
        "width": WIDTH,
        "working_tree_state": "dirty:" + _text_sha256(filtered_status),
        "working_tree_status": filtered_status,
    }
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
