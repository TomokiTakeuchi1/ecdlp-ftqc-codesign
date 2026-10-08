from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from ecdlp_ftqc.analysis.lp_flag_preparation import _Quotient

ROOT = Path(__file__).resolve().parents[2]


def _runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flag_lp_runner", ROOT / "scripts/run_lp_flag_preparation_cycle.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def saved() -> dict[str, Any]:
    return json.loads((ROOT / "experiments/runs/T-20261001-008/summary.json").read_text(
        encoding="utf-8",
    ))  # type: ignore[no-any-return]


def test_manifest_and_saved_certificate(saved: dict[str, Any]) -> None:
    runner = _runner()
    runner.load_manifest(runner.MANIFEST)
    runner.validate_result(saved)
    assert saved["blocks"]["Q"]["single_fault_audit"]["row0_third_data_cnot_hook"] == {
        "row_zero_based": 0, "after_data_cnot": 3, "tick": 5,
        "physical_fault": "syndrome_Z", "actual_flag_indices": [0],
        "classification": "reject_flag",
    }


@pytest.mark.parametrize("path,value", [
    (("task_id",), "wrong"),
    (("blocks", "Q", "single_fault_audit", "single_fault_residual_weight_at_most_one"), False),
    (("blocks", "M", "single_fault_audit", "total_pauli_fault_cases"), 1),
    (("blocks", "Q", "single_fault_audit", "total_outcomes", "accept_bad"), 1),
    (("blocks", "Q", "single_fault_audit", "full_factory_ft"), True),
    (("blocks", "M", "single_fault_audit", "logical_failure_probability"), 0),
    (("blocks", "Q", "resources", "native_seconds"), 1),
    (("blocks", "Q", "resources", "qec_cycles"), 1571),
    (("blocks", "Q", "resources", "idle_locations", "flag"), 0),
    (("blocks", "Q", "single_fault_audit", "fault_classes", "cnot", "paulis_per_location"), 1),
    (("blocks", "Q", "single_fault_audit", "fault_classes", "idle_data", "locations"), 0),
    (("blocks", "Q", "single_fault_audit", "fault_classes", "read_flag",
      "linear_rejection_coefficient"), "0"),
    (("blocks", "M", "retry", "finite_p_acceptance_estimate"), 0.5),
    (("combined", "full_GHZ_factory_FT"), True),
    (("combined", "waiting_is_inside_preparation_certificate"), True),
    (("independent_dense_replay", "axis_reports", "X", "bad_accepted_branches"), 1),
    (("independent_dense_replay", "axis_reports", "Z",
      "one_pass_readout_negative_control_best_orbit_fidelity"), 1),
    (("ideal_preparation_sign_recovery", "noisy_decoder"), True),
])
def test_result_mutation_rejected(
    saved: dict[str, Any], path: tuple[str, ...], value: Any,
) -> None:
    changed = copy.deepcopy(saved)
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        _runner().validate_result(changed)


@pytest.mark.parametrize("key,value", [
    ("projection_passes", 1), ("lift", True), ("interpass_correction", True),
    ("full_factory_ft", True), ("resource_caps", [True, 64, 256, 5250]),
    ("final_correction", "physical_gates"), ("native_seconds", 1),
])
def test_unsupported_manifest_rejected(tmp_path: Path, key: str, value: Any) -> None:
    runner = _runner()
    config = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
    config[key] = value
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.load_manifest(path)


def test_dependency_pin_and_sensitivity_mutations_rejected(
    tmp_path: Path, saved: dict[str, Any],
) -> None:
    runner = _runner()
    config = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
    config["inherited_files"][0]["sha256"] = "0" * 64
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        runner.load_manifest(path)
    changed = copy.deepcopy(saved)
    changed["resource_sensitivity"][0]["Q"]["total_idle_locations"] = 0
    with pytest.raises(ValueError, match="sensitivity"):
        runner.validate_result(changed)


def test_equal_but_inconsistent_syndromes_fail_closed() -> None:
    quotient = _Quotient((15, 5, 10), 4)
    # Dependency row0+row1+row2=0: a common delta001 is not a valid image.
    effect = (1 << quotient.output_width) | (1 << (quotient.output_width + 3))
    assert quotient.classify(effect) == "reject_inconsistent"
    # A genuine valid common delta, with its corresponding output X signature,
    # is removed by the same record-dependent frame correction.
    column = quotient.columns[0]
    valid = column | (column << quotient.output_width) | (
        column << (quotient.output_width + 3)
    )
    assert quotient.classify(valid) == "accept_target"
