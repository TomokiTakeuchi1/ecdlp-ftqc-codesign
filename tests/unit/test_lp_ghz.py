from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from ecdlp_ftqc.code_constructions.lp_ghz import (
    INFORMATION,
    CSSCode,
    RingMatrix,
    apply_rows,
    audit_instance,
    automorphism_permutation,
    auxiliary,
    base_seed,
    canonical_logicals,
    canonical_seed_words,
    completed_seed,
    echelon,
    homomorphic_css_failures,
    info_projection,
    kernel,
    lifted_product,
    remainder,
    rotate_cells,
    transpose,
)


@pytest.fixture(scope="module")
def certificate() -> dict[str, Any]:
    return audit_instance()


def test_small_binary_algebra_exhaustively() -> None:
    for a in range(8):
        for b in range(8):
            rows = (a, b)
            basis = echelon(rows)
            null = kernel(rows, 3)
            assert len(null) + len(basis) == 3
            assert all(apply_rows(rows, v) == 0 for v in null)
            assert len(echelon(null)) == len(null)
            assert transpose(transpose(rows, 3), 2) == rows
            for v in range(8):
                assert (remainder(v, basis) == 0) == (v in {0, a, b, a ^ b})


@pytest.mark.parametrize("lift", [1, 3, 5])
def test_ring_conventions_and_canonical_pairing(lift: int) -> None:
    a = base_seed(lift)
    assert a.adjoint().binary() == transpose(a.binary(), 7 * lift)
    q = lifted_product(completed_seed(lift), a.adjoint())
    xs, zs = canonical_logicals(lift)
    assert len(xs) == 16 * lift
    assert all(apply_rows(q.hz, v) == 0 for v in xs)
    assert all(apply_rows(q.hx, v) == 0 for v in zs)
    assert all(apply_rows(zs, x) == 1 << i for i, x in enumerate(xs))
    for i, v in enumerate(canonical_seed_words(lift)):
        assert info_projection(v, lift) == 1 << (i * lift)
        assert rotate_cells(rotate_cells(v, 1, lift, 7), -1, lift, 7) == v
    p = automorphism_permutation(lift)
    assert sorted(p) == list(range(q.n))
    assert all(p[p[i]] == i for i in range(q.n))


def test_finite_css_and_all_logical_generators(certificate: dict[str, Any]) -> None:
    q = certificate["code"]
    assert (q["data_qubits"], q["hx_rank"], q["hz_rank"]) == (9600, 5226, 3134)
    assert q["logical_qubits"] == 1240
    assert q["canonical_logical_qubits"] == 1200
    assert q["residual_logical_qubits"] == 40
    assert all(value == 0 for value in certificate["checks"].values())
    assert certificate["convention"]["wrong_x_action_failures_of_1200"] == 1200
    assert certificate["convention"]["correct_selected_logical_row_one_based"] == 4
    assert certificate["residual_image"]["additional_rank_beyond_all_canonical_x"] == 2


def test_complete_measured_space_and_ft_rejection(certificate: dict[str, Any]) -> None:
    raw, strict = certificate["auxiliaries"]
    assert [a["independent_measured_data_x"] for a in (raw, strict)] == [302, 300]
    assert [a["additional_residual_x_measurements"] for a in (raw, strict)] == [2, 0]
    assert [a["hz_weight_max"] for a in (raw, strict)] == [7, 75]
    for aux in (raw, strict):
        assert aux["homomorphic_inclusion_failures"] == [0, 0]
        assert aux["single_z_logical_count"] == 525
        assert aux["z_distance"] == 1
        assert aux["single_fault_witness"]["canonical_outcomes_flipped"] == 1
        assert aux["readout_fault_canonical_outcomes_flipped_max"] == 156
        assert aux["ft_single_shot_admitted"] is False
        assert aux["native_runtime_seconds"] is None
        assert aux["ft_admitted_parallel_measurements"] is None
    assert certificate["admission"]["fault_tolerant_factory"] is False


def test_code_inclusion_rejects_unprotected_arbitrary_ancilla() -> None:
    q = lifted_product(completed_seed(1), base_seed(1).adjoint())
    targets = tuple(range(INFORMATION[3] * 7, (INFORMATION[3] + 1) * 7))
    assert homomorphic_css_failures(q, auxiliary(1), targets) == (0, 0)
    assert homomorphic_css_failures(q, CSSCode(7, (), ()), targets)[1] > 0
    with pytest.raises(ValueError, match="matching"):
        homomorphic_css_failures(q, auxiliary(1), (0,) * 7)
    with pytest.raises(ValueError, match="matching"):
        homomorphic_css_failures(q, auxiliary(1), targets[:-1])


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        base_seed(0)
    with pytest.raises(ValueError):
        base_seed(2)
    with pytest.raises(ValueError):
        RingMatrix(3, ((8,),))
    with pytest.raises(ValueError):
        RingMatrix(3, ((1,), (1, 0)))
    with pytest.raises(ValueError):
        CSSCode(2, (4,), ())
    with pytest.raises(ValueError):
        kernel((8,), 3)
    with pytest.raises(ValueError):
        remainder(-1, {})
    with pytest.raises(ValueError):
        lifted_product(base_seed(3), base_seed(5))


def test_manifest_mutation_is_not_silently_ignored(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "lp_ghz_cycle", root / "scripts/run_lp_ghz_cycle.py"
    )
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    config = runner.load_manifest(root / "experiments/manifests/E-20261001-001.json")
    config["selected_logical_row_one_based"] = 1
    altered = tmp_path / "bad.json"
    altered.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="selected_logical_row"):
        runner.load_manifest(altered)
