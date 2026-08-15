"""Generate reproducible artifacts for the adaptive PBC/CQLU research cycle."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecdlp_ftqc.circuits import PINNED_GIDNEY_SOURCE_COMMIT, generate_gidney_dag
from ecdlp_ftqc.codes import load_mitten_backend_config
from ecdlp_ftqc.compiler import (
    PbcOperationKind,
    lower_gidney_phase_exact,
    lower_to_adaptive_pauli_measurements,
    pbc_trace_to_data,
    verify_reference_gadget_channels,
)
from ecdlp_ftqc.compiler.pbc_verification import gadget_verification_to_data

TASK_ID = "T-20260815-004"
EXPERIMENT_ID = "E-20260815-002"
RANDOM_SEED = 20260815
WIDTHS = (2, 3, 4, 16, 32, 58, 59)
RELEVANT_SOURCE_PATHS = (
    "src/runtime_metadata_benchmark/gidney",
    "src/runtime_metadata_benchmark/ir",
    "src/runtime_metadata_benchmark/ppm",
    "src/runtime_metadata_benchmark/scheduling",
)


def _git(repo: Path, *arguments: str, check: bool = True) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repo.as_posix()}",
            "-C",
            str(repo),
            *arguments,
        ],
        check=check,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _verify_source(source_repo: Path) -> None:
    observed_commit = _git(source_repo, "rev-parse", "HEAD")
    if observed_commit != PINNED_GIDNEY_SOURCE_COMMIT:
        raise RuntimeError(
            "Gidney source commit mismatch: "
            f"expected {PINNED_GIDNEY_SOURCE_COMMIT}, observed {observed_commit}"
        )
    status = _git(source_repo, "status", "--porcelain", "--", *RELEVANT_SOURCE_PATHS)
    if status:
        raise RuntimeError("Gidney source inputs contain uncommitted changes:\n" + status)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _measurement_family(pauli_terms: tuple[str, ...]) -> str:
    return "".join(term.split(":", maxsplit=1)[0] for term in pauli_terms)


def _runtime_blockers(trace_data: dict[str, Any]) -> list[dict[str, str]]:
    operations = trace_data["operations"]
    states = {
        choice["state"]
        for operation in operations
        for choice in operation["prepared_states"]
    }
    adaptive_preparation = any(
        choice["condition"]
        for operation in operations
        for choice in operation["prepared_states"]
    )
    measurement_families = {
        _measurement_family(tuple(operation["pauli_terms"]))
        for operation in operations
        if operation["kind"] == PbcOperationKind.MEASURE_PAULI.value
    }
    blockers: list[dict[str, str]] = []
    if "magic_t" in states:
        blockers.append(
            {
                "evidence_status": "CHECK",
                "requirement": "logical |T> preparation/injection duration and occupied space",
            }
        )
    if states - {"magic_t"}:
        blockers.append(
            {
                "evidence_status": "CHECK",
                "requirement": "logical stabilizer-state preparation duration and occupied space",
            }
        )
    if adaptive_preparation:
        blockers.append(
            {
                "evidence_status": "CHECK",
                "requirement": "measurement-to-adaptive-preparation reaction latency",
            }
        )
    unresolved_families = sorted(measurement_families - {"X", "XX"})
    if unresolved_families:
        blockers.append(
            {
                "evidence_status": "CHECK",
                "requirement": (
                    "source-pinned J300 durations for Pauli families "
                    + ", ".join(unresolved_families)
                ),
            }
        )
    if any(operation["frame_updates"] for operation in operations):
        blockers.append(
            {
                "evidence_status": "CHECK",
                "requirement": "decoder and Pauli-frame reaction latency",
            }
        )
    if any(
        operation["kind"] == PbcOperationKind.CONDITIONAL_CLIFFORD_FRAME.value
        for operation in operations
    ):
        blockers.append(
            {
                "evidence_status": "CHECK",
                "requirement": "conditional CZ-frame propagation or physical implementation",
            }
        )
    blockers.append(
        {
            "evidence_status": "CHECK",
            "requirement": "resource-constrained scheduling of the adaptive PBC trace",
        }
    )
    return blockers


def _summary(trace_data: dict[str, Any], processor_capacity: int) -> dict[str, Any]:
    operation_counts = Counter(
        operation["kind"] for operation in trace_data["operations"]
    )
    measurement_counts = Counter(
        _measurement_family(tuple(operation["pauli_terms"]))
        for operation in trace_data["operations"]
        if operation["kind"] == PbcOperationKind.MEASURE_PAULI.value
    )
    minimum_occupancy = trace_data["minimum_serial_processor_occupancy"]
    return {
        "compiler_ancilla_lifetime_count": len(trace_data["compiler_ancillas"]),
        "measurement_family_counts": dict(sorted(measurement_counts.items())),
        "minimum_serial_processor_occupancy": minimum_occupancy,
        "operation_counts": dict(sorted(operation_counts.items())),
        "operation_count": len(trace_data["operations"]),
        "peak_source_processor_occupancy": trace_data[
            "peak_source_processor_occupancy"
        ],
        "processor_capacity": processor_capacity,
        "resource_state_demand": trace_data["resource_state_demand"],
        "serialized_one_scratch_slot_count_fits": minimum_occupancy <= processor_capacity,
    }


def _run(source_repo: Path, config_path: Path, output_dir: Path) -> None:
    _verify_source(source_repo)
    sys.path.insert(0, str(source_repo / "src"))
    config = load_mitten_backend_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    widths: dict[str, Any] = {}
    width_two_data: dict[str, Any] | None = None
    for width in WIDTHS:
        logical_trace = lower_gidney_phase_exact(generate_gidney_dag(width))
        pbc_trace = lower_to_adaptive_pauli_measurements(logical_trace)
        trace_data = pbc_trace_to_data(pbc_trace)
        widths[str(width)] = _summary(trace_data, config.logical_qubits)
        if width == 2:
            width_two_data = trace_data
    if width_two_data is None:
        raise AssertionError("width-two audit trace was not generated")

    verification = verify_reference_gadget_channels(random_seed=RANDOM_SEED)
    if verification.maximum_frobenius_error >= 1e-12:
        raise AssertionError("adaptive measurement gadget channel check failed")
    blockers = _runtime_blockers(width_two_data)
    _write_json(output_dir / "gidney_width2_pbc_trace.json", width_two_data)
    _write_json(
        output_dir / "gadget_channel_verification.json",
        gadget_verification_to_data(verification),
    )
    _write_json(
        output_dir / "summary.json",
        {
            "capacity_boundary": {
                "evidence_status": "NUMERICAL",
                "maximum_width_passing_serialized_slot_count": 58,
                "minimum_reusable_compiler_scratch_slots": 1,
                "processor_logical_capacity": config.logical_qubits,
                "qualification": (
                    "Necessary occupancy for this lowering with a serialized reusable "
                    "scratch slot; not a strict runtime result"
                ),
                "width_58_slot_count_fits": widths["58"][
                    "serialized_one_scratch_slot_count_fits"
                ],
                "width_59_slot_count_fits": widths["59"][
                    "serialized_one_scratch_slot_count_fits"
                ],
            },
            "configuration_id": config.configuration_id,
            "evidence_status": "NUMERICAL",
            "experiment_id": EXPERIMENT_ID,
            "factory_mode": "ideal supply; demand retained; no factory schedule",
            "runtime_blockers": blockers,
            "strict_runtime_available": False,
            "task_id": TASK_ID,
            "widths": widths,
        },
    )
    working_tree = _git(PROJECT_ROOT, "status", "--porcelain", check=False)
    _write_json(
        output_dir / "reproducibility.json",
        {
            "architecture_configuration": str(config_path.relative_to(PROJECT_ROOT)),
            "assumption_ids": ["A-0004", "A-0006", "A-0011", "A-0012"],
            "circuit_source": "runtime_metadata_benchmark.gidney",
            "circuit_source_commit": PINNED_GIDNEY_SOURCE_COMMIT,
            "code_instance": "[[300,60,14]] Mitten",
            "experiment_id": EXPERIMENT_ID,
            "factory_assumption": "ideal supply; no stalls; demand retained",
            "git_commit": "unborn repository",
            "input_trace": "ecdlp-ftqc/phase-exact-logical-trace v1",
            "lowered_trace": "ecdlp-ftqc/adaptive-pauli-measurement-trace v1",
            "output_path": str(output_dir.relative_to(PROJECT_ROOT)),
            "python": platform.python_version(),
            "random_seed": RANDOM_SEED,
            "task_id": TASK_ID,
            "validation_status": "NUMERICAL channel verification; runtime CHECK",
            "working_tree_porcelain": working_tree.splitlines(),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-repo",
        type=Path,
        default=PROJECT_ROOT.parent / "runtime-metadata-benchmark",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "codes" / "mitten_j300_k60_d14_v1.yaml",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "experiments" / "runs" / TASK_ID,
    )
    arguments = parser.parse_args()
    _run(
        arguments.source_repo.resolve(),
        arguments.config.resolve(),
        arguments.output_dir.resolve(),
    )


if __name__ == "__main__":
    main()
