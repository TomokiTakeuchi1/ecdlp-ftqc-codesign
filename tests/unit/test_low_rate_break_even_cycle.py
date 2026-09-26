"""Generator pairing, refinement selection, and fail-closed resume contracts."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "break_even_cycle", ROOT / "scripts/run_low_rate_break_even_cycle.py"
)
assert spec and spec.loader
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)
audit_spec = importlib.util.spec_from_file_location(
    "exact_cost_audit", ROOT / "scripts/audit_low_rate_break_even_outputs.py"
)
assert audit_spec and audit_spec.loader
exact_audit = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(exact_audit)


def test_small_end_to_end_and_reproducible_checkpoint(tmp_path):
    config = json.loads(cycle.MANIFEST.read_text())
    config["width"] = 5
    selected = cycle.cells(config)
    hashes = cycle.source_hashes()
    job = ("ip", 0, config, selected, str(tmp_path), hashes)
    first = cycle.cached_job(job)
    assert len(first["grid"]) == 54
    for row in first["grid"]:
        if row["mode"] == "qwc" and row["status"] == "both_ppm_feasible":
            assert all(
                row["delta_service_counts"][k] == 0 for k in ("prepare", "readout", "reaction")
            )
    assert cycle.cached_job(job) == first
    assert first["legacy_obligations"]["bare_source_cnot_count"] == 15
    assert first["legacy_obligations"]["bare_source_x_count"] == 8
    assert first["legacy_obligations"]["legacy_clifford_cost_units"] is None
    aggregate = cycle.aggregate([first], "ip", selected, 1)
    assert len(aggregate) == 54
    audit_config = deepcopy(config)
    audit_config["initial_hashed_branches"] = 1
    summary = {
        "task_id": cycle.TASK,
        "config": audit_config,
        "source_sha256": hashes,
        "paper_sha256": {},
        "refinement_complete": True,
        "complete_native_schedule": False,
        "branches": [first],
        "initial_grid": aggregate,
        "refined_grid": [],
        "grid": aggregate,
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    audited = exact_audit.audit(tmp_path)
    assert audited["audited_paired_cell_count"] == 54
    assert audited["audited_aggregate_count"] == 108
    assert audited["rates_as_exact_fractions"] == [[1, 1], [1, 4], [1, 4], [1, 10]]
    native_claim = deepcopy(summary)
    native_claim["physical_qubits"] = 123
    (tmp_path / "summary.json").write_text(json.dumps(native_claim), encoding="utf-8")
    with pytest.raises(ValueError, match="native summary"):
        exact_audit.audit(tmp_path)
    damaged = deepcopy(summary)
    damaged["branches"][0]["grid"][0]["b_crit_units"] += 0.125
    (tmp_path / "summary.json").write_text(json.dumps(damaged), encoding="utf-8")
    with pytest.raises(ValueError, match="exact decimal cost"):
        exact_audit.audit(tmp_path)
    with pytest.raises(ValueError, match="duplicated"):
        cycle.aggregate([first, first], "ip", selected, 1)
    with pytest.raises(ValueError, match="missing"):
        cycle.aggregate([first], "ip", selected, 2)
    changed = deepcopy(config)
    changed["timing"]["surgery"] = 2
    with pytest.raises(ValueError, match="stale checkpoint"):
        cycle.cached_job(("ip", 0, changed, selected, str(tmp_path), hashes))
    (tmp_path / first["artifact"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="artifact hash"):
        cycle.cached_job(job)


@pytest.mark.parametrize(
    "count,budget,expected",
    [
        (0, None, False),
        (64, {"min": 1, "max": 4}, False),
        (64, {"min": -3, "max": -1}, False),
        (25, {"min": 2, "max": 5}, True),
        (64, {"min": 0, "max": 1}, True),
        (64, {"min": -1, "max": 1}, True),
        (64, {"min": 0, "max": 0}, False),
    ],
)
def test_manifest_refinement_rule(count, budget, expected):
    assert (
        cycle.needs_refinement(
            {
                "status_counts": {"both_ppm_feasible": count},
                "hashed_witness_count": 64,
                "b_crit_units": budget,
            }
        )
        == expected
    )


def test_deterministic_serialization():
    data = {"z": 2**999, "items": [1, 2, 3]}
    assert cycle.payload(data, True) == cycle.payload(data, True)
    assert cycle.compact(data)["z"] == hex(2**999)
