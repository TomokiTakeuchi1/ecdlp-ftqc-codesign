from __future__ import annotations

from typing import Any

import pytest

from ecdlp_ftqc.code_constructions.lp_direct_ghz import (
    _solve_columns,
    audit_direct_instance,
    build_direct_certificate,
)
from ecdlp_ftqc.code_constructions.lp_ghz import apply_rows, permute
from ecdlp_ftqc.code_constructions.lp_protected_ghz import restrict


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return audit_direct_instance()


def test_full_direct_output_and_all_outcome_certificate(report: dict[str, Any]) -> None:
    assert not any(report["checks"].values())
    output = report["output"]
    assert output["physical_carriers"] == 9600
    assert output["logical_qubits"] == 1240
    assert output["canonical_logical_qubits"] == 1200
    assert output["ghz4_count"] == 300
    assert output["verified_canonical_ghz_stabilizers"] == 1200
    assert (output["residual_z_fixed"], output["residual_x_retained"]) == (38, 2)
    assert output["canonical_residual_factorization"] is True
    signs = report["readout_map"]
    assert signs["physical_Z_readout_bits"] == 9075
    assert signs["allowed_ideal_readout_space_dimension"] == 6164
    assert signs["readout_gauge_dimension"] == 5226
    assert signs["independent_logical_outcome_bits"] == 938
    assert signs["logical_outcome_count"] == "2**938"
    assert signs["noisy_readout_decoding"] == "OPEN"
    assert report["admission"]["fault_tolerant_factory"] is False


@pytest.mark.parametrize("lift", [1, 3, 5])
def test_small_structural_instances(lift: int) -> None:
    small = audit_direct_instance(lift)
    assert not any(small["checks"].values())
    assert small["output"]["ghz4_count"] == 4 * lift


def test_frames_for_combined_outcomes_and_gauge_equivalent_readouts() -> None:
    c = build_direct_certificate(3)
    # Generator identities in the audit are exhaustive; this also tests the
    # user-facing multi-bit APIs with canonical and residual signs together.
    outcomes = (1 << len(c.measured_z)) - 1
    frame = c.frame_from_outcomes(outcomes)
    readout = restrict(frame, c.coordinates)
    assert c.decode_readout(readout) == outcomes
    assert c.frame_from_readout(readout) == frame
    for gauge in c.mask_code.hx:
        assert c.decode_readout(readout ^ gauge) == outcomes
    final_frame = c.frame_from_readout(readout, after_automorphism=True)
    assert final_frame == permute(frame, c.permutation)
    assert apply_rows(c.ghz_z, final_frame) == apply_rows(c.raw_ghz_sign_rows, readout)
    assert apply_rows(c.measured_z, frame) == outcomes


def test_negative_controls_are_discriminating(report: dict[str, Any]) -> None:
    negative = report["negative_controls"]
    assert negative["omitted_frame_bad_outcome_generators"] == 900
    assert negative["omitted_frame_canonical_good_fraction"] == "2**-900"
    assert negative["omitted_automorphism_missing_ghz_x_stabilizers"] == 300
    assert negative["omitted_automorphism_missing_ghz_z_stabilizers"] == 900
    c = build_direct_certificate(3)
    uncorrected = c.frame_from_outcomes(1, after_automorphism=True)
    assert apply_rows(c.ghz_z, uncorrected) != 0
    residual_frame = c.frame_from_outcomes(1 << (12 * c.lift), after_automorphism=True)
    assert apply_rows(c.ghz_z, residual_frame) == 0


@pytest.mark.parametrize("lift", [0, -1, 2, True, 3.0])
def test_invalid_lift_rejected(lift: Any) -> None:
    with pytest.raises(ValueError):
        build_direct_certificate(lift)


@pytest.mark.parametrize("invalid", [-1, True, 1.0, 1 << 1000])
def test_invalid_vectors_rejected(invalid: Any) -> None:
    c = build_direct_certificate(3)
    with pytest.raises(ValueError):
        c.decode_readout(invalid)
    with pytest.raises(ValueError):
        c.frame_from_outcomes(invalid)


def test_noisy_readout_is_not_silently_decoded() -> None:
    c = build_direct_certificate(3)
    fault = c.mask_code.hz[0] & -c.mask_code.hz[0]
    with pytest.raises(ValueError, match="noisy decoding is OPEN"):
        c.decode_readout(fault)


def test_simultaneous_solver_and_inconsistent_system() -> None:
    solutions = _solve_columns((0b011, 0b110), (0b01, 0b10), 3, 2)
    assert tuple(apply_rows((0b011, 0b110), x) for x in solutions) == (1, 2)
    with pytest.raises(ValueError, match="Inconsistent"):
        _solve_columns((1, 1), (0, 1), 1, 1)
    with pytest.raises(ValueError):
        _solve_columns((1,), (), 1, 1)
