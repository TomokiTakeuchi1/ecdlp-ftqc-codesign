from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "direct_lp_runner", ROOT / "scripts/run_lp_direct_ghz_cycle.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def saved() -> dict[str, Any]:
    return json.loads((ROOT / "experiments/runs/T-20261001-006/summary.json").read_text(
        encoding="utf-8",
    ))  # type: ignore[no-any-return]


def test_manifest_and_saved_result_are_admitted_only_as_ideal(saved: dict[str, Any]) -> None:
    runner = _runner()
    runner.load_manifest(runner.MANIFEST)
    runner.validate_result(saved)


@pytest.mark.parametrize("path,value", [
    (("task_id",), "wrong"),
    (("ideal_certificate", "checks", "correction_pairing_failures"), 1),
    (("ideal_certificate", "output", "ghz4_count"), 301),
    (("ideal_certificate", "readout_map", "independent_logical_outcome_bits"), 900),
    (("ideal_certificate", "admission", "fault_tolerant_factory"), True),
    (("ideal_certificate", "admission", "native_runtime_seconds"), 1),
    (("preparation_and_fault_diagnostic", "structural_resources", "interface_cnots"), 525),
    (("preparation_and_fault_diagnostic", "symbolic_time", "qec_rounds"), 1),
    (("ideal_preparation_sign_recovery", "noisy_decoder"), True),
    (("independent_dense_replay", "all_checks_passed"), False),
    (("preparation_and_fault_diagnostic", "bounded_fault_diagnostic",
      "record_blind_common_recovery_obstruction", "harmless_coset_minimum_weight"), 1),
])
def test_result_mutations_fail_closed(
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
    ("lift", True), ("ft_admission", True), ("outcome_postselection", True),
    ("native_runtime_seconds", 1), ("ancilla_caps_per_block", [64]),
])
def test_changed_manifest_model_rejected(tmp_path: Path, key: str, value: Any) -> None:
    runner = _runner()
    config = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
    config[key] = value
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.load_manifest(path)


def test_dependency_hash_mutation_rejected(tmp_path: Path) -> None:
    runner = _runner()
    config = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
    config["inherited_files"][0]["sha256"] = "0" * 64
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        runner.load_manifest(path)
