from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import (
    PINNED_GIDNEY_SOURCE_COMMIT,
    GidneyAdapterError,
    adapt_gidney_oracle,
    generate_gidney_dag,
    load_gidney_oracle_dag,
)
from ecdlp_ftqc.metadata import (
    DagNodeKind,
    DependencyKind,
    EvidenceStatus,
    dumps_dag,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "gidney_oracle"
EXPECTED_STRUCTURE = {
    2: {"source_operations": 7, "nodes": 8, "edges": 8, "critical_path": 6},
    3: {"source_operations": 17, "nodes": 19, "edges": 25, "critical_path": 14},
    4: {"source_operations": 27, "nodes": 30, "edges": 42, "critical_path": 22},
}


def _fixture(width: int) -> Path:
    return FIXTURE_ROOT / f"gidney_width{width}_oracle_v3.json"


def test_fixture_manifest_binds_exact_source_bytes() -> None:
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["source_commit"] == PINNED_GIDNEY_SOURCE_COMMIT
    assert manifest["oracle_schema_version"] == 3
    for record in manifest["files"]:
        data = (FIXTURE_ROOT / record["name"]).read_bytes()
        assert len(data) == record["bytes"]
        assert sha256(data).hexdigest() == record["sha256"]


@pytest.mark.parametrize("width", (2, 3, 4))
def test_small_verified_widths_convert_reproducibly(width: int) -> None:
    dag = load_gidney_oracle_dag(_fixture(width))
    expected = EXPECTED_STRUCTURE[width]

    assert dag.width == width
    assert dag.source_operation_count == expected["source_operations"]
    assert len(dag.nodes) == expected["nodes"]
    assert len(dag.edges) == expected["edges"]
    assert dag.critical_path_node_count == expected["critical_path"]
    assert dag.evidence_status is EvidenceStatus.NUMERICAL
    assert dag.source.commit == PINNED_GIDNEY_SOURCE_COMMIT
    assert dumps_dag(dag) == dumps_dag(load_gidney_oracle_dag(_fixture(width)))


@pytest.mark.parametrize("width", (2, 3, 4))
def test_temporary_and_erase_exposes_measurement_and_feed_forward(width: int) -> None:
    dag = load_gidney_oracle_dag(_fixture(width))
    counts = dag.kind_counts

    assert counts[DagNodeKind.MEASUREMENT] == width - 1
    assert counts[DagNodeKind.CLASSICAL_FRAME_UPDATE] == width - 1
    assert len(dag.classical_values) == width - 1
    node_by_id = {node.node_id: node for node in dag.nodes}
    edges = {
        (edge.predecessor, edge.successor, edge.kind, edge.resource_ids)
        for edge in dag.edges
    }
    for outcome in dag.classical_values:
        measurement = node_by_id[outcome.producer_node_id]
        consumers = [
            node for node in dag.nodes if outcome.value_id in node.classical_inputs
        ]
        assert measurement.kind is DagNodeKind.MEASUREMENT
        assert measurement.semantic_action == "measure_temporary_in_x_basis"
        assert measurement.operand_roles == ("measured",)
        assert measurement.pauli_terms == (f"X:{measurement.value_support[0]}",)
        assert len(consumers) == 1
        frame_update = consumers[0]
        assert frame_update.kind is DagNodeKind.CLASSICAL_FRAME_UPDATE
        assert frame_update.semantic_action == "conditional_cz_on_measurement_one"
        assert frame_update.operand_roles == (
            "conditional_cz_support",
            "conditional_cz_support",
        )
        assert (
            measurement.node_id,
            frame_update.node_id,
            DependencyKind.CLASSICAL_FEED_FORWARD,
            (outcome.value_id,),
        ) in edges


def test_adapter_does_not_turn_source_adjacency_into_a_false_dependency() -> None:
    dag = load_gidney_oracle_dag(_fixture(3))
    edge_endpoints = {(edge.predecessor, edge.successor) for edge in dag.edges}

    # These operations are adjacent in the source list but touch disjoint wires.
    assert ("op:0003:cnot", "op:0004:allocate") not in edge_endpoints
    # Their effects join only at the following temporary-AND computation.
    assert ("op:0003:cnot", "op:0005:temporary_and_compute") in edge_endpoints
    assert ("op:0004:allocate", "op:0005:temporary_and_compute") in edge_endpoints


def test_measurement_releases_temporary_without_waiting_for_frame_application() -> None:
    dag = load_gidney_oracle_dag(_fixture(2))
    edge_endpoints = {(edge.predecessor, edge.successor) for edge in dag.edges}
    measurement = next(
        node for node in dag.nodes if node.kind is DagNodeKind.MEASUREMENT
    )
    frame = next(
        node for node in dag.nodes if node.kind is DagNodeKind.CLASSICAL_FRAME_UPDATE
    )
    release = next(node for node in dag.nodes if node.kind is DagNodeKind.RELEASE)

    assert (measurement.node_id, release.node_id) in edge_endpoints
    assert (frame.node_id, release.node_id) not in edge_endpoints


def test_lifetimes_reference_expanded_nodes() -> None:
    dag = load_gidney_oracle_dag(_fixture(3))
    carry_one = next(
        lifetime for lifetime in dag.lifetimes if lifetime.value_id == "value:carry[1]"
    )

    assert carry_one.allocation_node_id == "op:0004:allocate"
    assert carry_one.last_node_id == "op:0010:temporary_and_erase:measure_x"
    assert carry_one.release_node_id == "op:0011:release"
    assert carry_one.initialization == "t_state"
    assert carry_one.residency == "local"
    assert carry_one.must_store_on_release is False


def test_adapter_rejects_unverified_or_wrong_mapping_input() -> None:
    value = json.loads(_fixture(2).read_text(encoding="utf-8"))
    value["configuration"]["semantic_mapping_version"] = 99
    with pytest.raises(GidneyAdapterError, match="semantic_mapping_version"):
        adapt_gidney_oracle(value)

    value = json.loads(_fixture(2).read_text(encoding="utf-8"))
    value["configuration"]["phase_verification_provenance"]["status"] = "unchecked"
    with pytest.raises(GidneyAdapterError, match="not verified"):
        adapt_gidney_oracle(value)


def test_width_256_structural_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    research_root = Path(__file__).resolve().parents[3]
    source_repo = research_root / "runtime-metadata-benchmark"
    source_package = source_repo / "src" / "runtime_metadata_benchmark"
    if not source_package.is_dir():
        pytest.skip("pinned runtime-metadata-benchmark checkout is not available")

    observed_commit = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={source_repo.as_posix()}",
            "-C",
            str(source_repo),
            "rev-parse",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert observed_commit == PINNED_GIDNEY_SOURCE_COMMIT
    monkeypatch.syspath_prepend(str(source_repo / "src"))

    dag = generate_gidney_dag(256)

    assert dag.source_operation_count == 2547
    assert len(dag.nodes) == 2802
    assert len(dag.edges) == 4326
    assert len(dag.lifetimes) == 767
    assert len(dag.classical_values) == 255
    assert dag.critical_path_node_count == 2038
    assert dag.evidence_status is EvidenceStatus.LITERATURE
    assert dag.kind_counts == {
        DagNodeKind.ALLOCATE: 255,
        DagNodeKind.CNOT: 1527,
        DagNodeKind.TEMPORARY_AND_COMPUTE: 255,
        DagNodeKind.MEASUREMENT: 255,
        DagNodeKind.CLASSICAL_FRAME_UPDATE: 255,
        DagNodeKind.RELEASE: 255,
    }
