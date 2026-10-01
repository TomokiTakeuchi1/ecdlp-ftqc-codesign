from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from ecdlp_ftqc.code_constructions.lp_ghz import (
    apply_rows,
    auxiliary,
    base_seed,
    canonical_logicals,
    completed_seed,
    echelon,
    kernel,
    lifted_product,
    permute,
    remainder,
)
from ecdlp_ftqc.code_constructions.lp_protected_ghz import (
    audit_masked_instance,
    punctured_mask,
    restrict,
)
from ecdlp_ftqc.verification.lp_protected_ghz import audit_low_weight


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return audit_masked_instance()


def _runner() -> Any:
    path = Path(__file__).resolve().parents[2] / "scripts/run_lp_protected_ghz_cycle.py"
    spec = importlib.util.spec_from_file_location("protected_lp_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixed_mask_ranks_weights_and_full_measurement_algebra(report: dict[str, Any]) -> None:
    mask = report["mask"]
    assert (mask["physical_qubits"], mask["logical_qubits"]) == (9075, 938)
    assert (mask["hx"]["rank"], mask["hz"]["rank"]) == (5226, 2911)
    assert (mask["hx"]["max_row_weight"], mask["hz"]["max_row_weight"]) == (10, 13)
    assert (mask["hx"]["edges"], mask["hz"]["edges"]) == (42525, 31950)
    assert mask["hx"]["max_column_degree"] == mask["hz"]["max_column_degree"] == 7
    assert not any(report["checks"].values())
    measured = report["measured_algebra"]
    assert measured["mask_z_normalizer_dimension"] == 3849
    assert measured["data_z_restriction_rank"] == 223
    assert measured["supported_data_z_stabilizer_dimension"] == 2911
    assert measured["unwanted_canonical_z_fixed"] == 900
    assert measured["additional_residual_z_fixed"] == 38
    assert measured["final_independent_x_measurements"] == 302
    assert measured["final_canonical_x_measurements"] == 300
    assert measured["final_residual_x_measurements"] == 2
    assert measured["preserves_arbitrary_residual_state"] is False
    assert measured["strict_300_without_residual_measurement"] == "OPEN"


@pytest.mark.parametrize("lift", [1, 3, 5])
def test_small_full_kernel_matches_dimension_certificate(lift: int) -> None:
    """Explicit kernel checks supplement the efficient full-size rank proof."""
    data = lifted_product(completed_seed(lift), base_seed(lift).adjoint())
    mask, coordinates = punctured_mask(lift)
    image = tuple(permute(row, coordinates) for row in kernel(mask.hx, mask.n))
    bz = echelon(data.hz)
    full_z = echelon(data.hz + image)
    xs, zs = canonical_logicals(lift)
    assert all(apply_rows(xs[12 * lift :], z) == 0 for z in image)
    assert all(remainder(z, full_z) == 0 for z in zs[: 12 * lift])
    assert len(full_z) - len(bz) == mask.n - len(echelon(mask.hx)) - len(echelon(mask.hz))
    final_x = kernel(tuple(full_z.values()), data.n)
    # The selected canonical Xs and two residuals span the entire measured quotient.
    omega = (1 << lift) - 1
    residual = (
        (omega | (omega << lift)) << (42 * lift),
        (omega | (omega << (4 * lift))) << (42 * lift),
    )
    proposed = echelon(data.hx + xs[12 * lift :] + residual)
    assert len(proposed) == len(final_x)
    assert all(remainder(x, proposed) == 0 for x in final_x)


def test_distance_threshold_is_complete_but_not_full_ft(report: dict[str, Any]) -> None:
    for audit in report["distance_audits"].values():
        assert audit["both_distances_at_least_3_certified"] is True
        assert audit["full_distance_computed"] is False
        assert audit["circuit_fault_tolerance_certified"] is False
        for axis in ("X", "Z"):
            assert audit[axis]["certified_distance_lower_bound"] == 3
            assert audit[axis]["logical_witness_upper_bound"] is None
            assert audit[axis]["weight_1"]["undetected_errors"] == 0
            assert audit[axis]["weight_2"]["undetected_errors"] == 0
    raw = auxiliary()
    assert audit_low_weight(raw.n, raw.hx, raw.hz)["Z"]["certified_distance_lower_bound"] == 1
    assert report["admission"]["fault_tolerant_factory"] is False


def test_direction_and_cost_boundaries(report: dict[str, Any]) -> None:
    assert report["negative_control"]["reversed_mask_cnot_inclusion_failures"] == [2625, 225]
    cost = report["structural_cost"]
    assert cost["total_interface_cnots"] == 18675
    assert cost["ordered_interface_matching_layers"] == 2
    assert cost["resource_preparation_peak_carriers_excluding_qec"] == 18675
    assert cost["online_data_plus_prepared_auxiliary_carriers_excluding_qec"] == 19200
    assert cost["resident_data_plus_preparation_peak_carriers_excluding_qec"] == 28275
    assert cost["native_runtime_seconds"] is None
    assert cost["native_initialization_rounds"] is None
    assert cost["logical_failure_probability"] is None


@pytest.mark.parametrize("row", [-1, 4])
def test_invalid_selected_row_rejected(row: int) -> None:
    with pytest.raises(ValueError):
        punctured_mask(75, row)


@pytest.mark.parametrize("vector,coordinates", [(-1, (0,)), (2, (-1,)), (2, (1, 1))])
def test_restriction_rejects_invalid_inputs(vector: int, coordinates: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        restrict(vector, coordinates)


@pytest.mark.parametrize(
    "key,value",
    [
        ("lift", 3),
        ("ft_admission", True),
        ("native_runtime_seconds", 1),
        ("residual_measurements_allowed", False),
        ("maximum_error_weight_checked", 1),
    ],
)
def test_manifest_changes_are_not_ignored(tmp_path: Path, key: str, value: Any) -> None:
    runner = _runner()
    original = runner.load_manifest(runner.MANIFEST)
    original[key] = value
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.load_manifest(path)


def test_manifest_missing_null_and_tampered_pin_rejected(tmp_path: Path) -> None:
    runner = _runner()
    config = runner.load_manifest(runner.MANIFEST)
    del config["random_seed"]
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError):
        runner.load_manifest(path)
    config = runner.load_manifest(runner.MANIFEST)
    config["inherited_files"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        runner.load_manifest(path)


def test_admission_rejects_forged_distance_ft_time_or_algebra(report: dict[str, Any]) -> None:
    runner = _runner()
    runner.validate_result(report)
    mutations = [
        ("admission", "fault_tolerant_factory", True),
        ("admission", "signed_outcomes_require_x_frame_correction_or_propagation", False),
        ("structural_cost", "native_runtime_seconds", 0),
        ("structural_cost", "ordered_interface_matching_layers", 1),
        ("measured_algebra", "final_residual_x_measurements", 0),
    ]
    for group, key, value in mutations:
        forged = copy.deepcopy(report)
        forged[group][key] = value
        with pytest.raises(ValueError):
            runner.validate_result(forged)
    forged = copy.deepcopy(report)
    forged["distance_audits"]["mask"]["both_distances_at_least_3_certified"] = False
    with pytest.raises(ValueError):
        runner.validate_result(forged)
