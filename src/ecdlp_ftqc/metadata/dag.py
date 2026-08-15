"""Immutable, architecture-independent dependency records for logical circuits."""

from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

DAG_SCHEMA = "ecdlp-ftqc/qec-neutral-dag"
DAG_SCHEMA_VERSION = 1


class EvidenceStatus(str, Enum):
    """Scientific evidence labels permitted by the project conventions."""

    PROVED = "PROVED"
    NUMERICAL = "NUMERICAL"
    LITERATURE = "LITERATURE"
    CONJECTURE = "CONJECTURE"
    OPEN = "OPEN"
    CHECK = "CHECK"
    FALSIFIED = "FALSIFIED"
    INCONCLUSIVE = "INCONCLUSIVE"


class DagNodeKind(str, Enum):
    """Circuit semantics before any QEC-native lowering is selected."""

    ALLOCATE = "allocate"
    CNOT = "cnot"
    TEMPORARY_AND_COMPUTE = "temporary_and_compute"
    MEASUREMENT = "measurement"
    CLASSICAL_FRAME_UPDATE = "classical_frame_update"
    RELEASE = "release"


class DependencyKind(str, Enum):
    """Why one DAG node must precede another."""

    QUANTUM_ORDER = "quantum_order"
    VALUE_LIFETIME = "value_lifetime"
    CLASSICAL_FEED_FORWARD = "classical_feed_forward"


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Versioned provenance for the circuit frontend consumed by an adapter."""

    repository: str
    commit: str
    oracle_schema: str
    oracle_schema_version: int
    generator: str
    semantic_mapping_version: int
    unit_decomposition: str
    verification_method: str
    verification_status: str

    def __post_init__(self) -> None:
        text_fields = (
            self.repository,
            self.oracle_schema,
            self.generator,
            self.unit_decomposition,
            self.verification_method,
            self.verification_status,
        )
        if any(not value for value in text_fields):
            raise ValueError("source-reference text fields cannot be empty")
        if len(self.commit) != 40 or any(
            character not in "0123456789abcdef" for character in self.commit.lower()
        ):
            raise ValueError("source commit must be a 40-character hexadecimal SHA")
        if self.oracle_schema_version < 1 or self.semantic_mapping_version < 1:
            raise ValueError("source schema and mapping versions must be positive")


@dataclass(frozen=True, slots=True)
class ClassicalValue:
    """A measurement result used by later classical control."""

    value_id: str
    producer_node_id: str

    def __post_init__(self) -> None:
        if not self.value_id or not self.producer_node_id:
            raise ValueError("classical value IDs cannot be empty")


@dataclass(frozen=True, slots=True)
class DagNode:
    """One semantic circuit action, not yet assigned to a QEC gadget."""

    node_id: str
    kind: DagNodeKind
    source_operation_id: str
    source_operation_index: int
    source_opcode: str
    semantic_action: str
    arithmetic_region: str
    wire_support: tuple[str, ...]
    value_support: tuple[str, ...]
    operand_roles: tuple[str, ...]
    pauli_terms: tuple[str, ...]
    modified_values: tuple[str, ...]
    required_memory_values: tuple[str, ...]
    required_processor_values: tuple[str, ...]
    classical_inputs: tuple[str, ...] = ()
    classical_outputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.node_id
            or not self.source_operation_id
            or not self.source_opcode
            or not self.semantic_action
            or not self.arithmetic_region
        ):
            raise ValueError("node and source operation IDs cannot be empty")
        if self.source_operation_index < 0:
            raise ValueError("source operation index cannot be negative")
        for field_name in (
            "wire_support",
            "value_support",
            "pauli_terms",
            "modified_values",
            "required_memory_values",
            "required_processor_values",
            "classical_inputs",
            "classical_outputs",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} cannot contain duplicates")
        if len(self.operand_roles) != len(self.value_support):
            raise ValueError("operand_roles must align with value_support")
        if any(not role for role in self.operand_roles):
            raise ValueError("operand roles cannot be empty")


@dataclass(frozen=True, slots=True)
class DagEdge:
    """A causal edge with the wires, values, or classical tokens that justify it."""

    predecessor: str
    successor: str
    kind: DependencyKind
    resource_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.predecessor or not self.successor:
            raise ValueError("edge endpoints cannot be empty")
        if self.predecessor == self.successor:
            raise ValueError("self dependencies are not allowed")
        if not self.resource_ids or len(self.resource_ids) != len(set(self.resource_ids)):
            raise ValueError("an edge requires unique, nonempty resource IDs")


@dataclass(frozen=True, slots=True)
class ValueLifetime:
    """Logical-value lifetime translated onto expanded DAG node IDs."""

    value_id: str
    wire_id: str
    first_node_id: str
    last_node_id: str
    allocation_node_id: str | None
    release_node_id: str | None
    initialization: str
    release: str
    residency: str
    role: str
    escapes_owner: bool | None
    must_store_on_release: bool | None
    must_preserve_initial_state: bool | None


@dataclass(frozen=True, slots=True)
class CircuitDag:
    """A validated QEC-neutral circuit DAG with deterministic serialization."""

    circuit_id: str
    width: int
    source_operation_count: int
    source: SourceReference
    evidence_status: EvidenceStatus
    nodes: tuple[DagNode, ...]
    edges: tuple[DagEdge, ...]
    classical_values: tuple[ClassicalValue, ...]
    lifetimes: tuple[ValueLifetime, ...]
    schema: str = DAG_SCHEMA
    schema_version: int = DAG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.circuit_id:
            raise ValueError("circuit_id cannot be empty")
        if self.width < 2:
            raise ValueError("circuit width must be at least two")
        if self.source_operation_count < 1:
            raise ValueError("source operation count must be positive")
        if self.schema != DAG_SCHEMA or self.schema_version != DAG_SCHEMA_VERSION:
            raise ValueError("unsupported DAG schema identity")
        self._validate()

    def _validate(self) -> None:
        node_ids = tuple(node.node_id for node in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("DAG node IDs must be unique")
        known_nodes = set(node_ids)
        edge_keys = tuple(
            (edge.predecessor, edge.successor, edge.kind, edge.resource_ids)
            for edge in self.edges
        )
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("DAG edges must be unique")
        for edge in self.edges:
            if edge.predecessor not in known_nodes or edge.successor not in known_nodes:
                raise ValueError("DAG edge references an unknown node")

        classical_ids = tuple(value.value_id for value in self.classical_values)
        if len(classical_ids) != len(set(classical_ids)):
            raise ValueError("classical value IDs must be unique")
        classical_by_id = {value.value_id: value for value in self.classical_values}
        node_by_id = {node.node_id: node for node in self.nodes}
        for value in self.classical_values:
            producer = node_by_id.get(value.producer_node_id)
            if producer is None or value.value_id not in producer.classical_outputs:
                raise ValueError("classical producer metadata is inconsistent")
        for node in self.nodes:
            for value_id in node.classical_inputs:
                if value_id not in classical_by_id:
                    raise ValueError("node consumes an unknown classical value")

        lifetime_ids = tuple(lifetime.value_id for lifetime in self.lifetimes)
        if len(lifetime_ids) != len(set(lifetime_ids)):
            raise ValueError("logical-value lifetime IDs must be unique")
        known_values = set(lifetime_ids)
        known_wires = {lifetime.wire_id for lifetime in self.lifetimes}
        for node in self.nodes:
            referenced_values = set(
                node.value_support
                + node.modified_values
                + node.required_memory_values
                + node.required_processor_values
            )
            if not referenced_values.issubset(known_values):
                raise ValueError("DAG node references a value without a lifetime")
            if not set(node.wire_support).issubset(known_wires):
                raise ValueError("DAG node references a wire without a lifetime")
            if not set(node.modified_values).issubset(node.value_support):
                raise ValueError("modified values must be direct node operands")
            if not set(node.value_support).issubset(node.required_processor_values):
                raise ValueError("direct node operands must occupy the processor")
            if not set(node.required_memory_values).issubset(
                node.required_processor_values
            ):
                raise ValueError("memory support must be included in processor occupancy")
        for lifetime in self.lifetimes:
            referenced_nodes = (
                lifetime.first_node_id,
                lifetime.last_node_id,
                lifetime.allocation_node_id,
                lifetime.release_node_id,
            )
            if any(node_id is not None and node_id not in known_nodes for node_id in referenced_nodes):
                raise ValueError("logical-value lifetime references an unknown node")

        feed_forward_edges = {
            (edge.predecessor, edge.successor, resource_id)
            for edge in self.edges
            if edge.kind is DependencyKind.CLASSICAL_FEED_FORWARD
            for resource_id in edge.resource_ids
        }
        for node in self.nodes:
            for value_id in node.classical_inputs:
                producer_node_id = classical_by_id[value_id].producer_node_id
                if (
                    producer_node_id,
                    node.node_id,
                    value_id,
                ) not in feed_forward_edges:
                    raise ValueError("classical input lacks a feed-forward edge")

        topological_order = self.topological_order()
        topological_position = {
            node_id: index for index, node_id in enumerate(topological_order)
        }
        for lifetime in self.lifetimes:
            if topological_position[lifetime.first_node_id] > topological_position[
                lifetime.last_node_id
            ]:
                raise ValueError("logical-value lifetime ends before its first use")
            if (
                lifetime.allocation_node_id is not None
                and topological_position[lifetime.allocation_node_id]
                > topological_position[lifetime.first_node_id]
            ):
                raise ValueError("logical value is used before allocation")
            if (
                lifetime.release_node_id is not None
                and topological_position[lifetime.release_node_id]
                < topological_position[lifetime.last_node_id]
            ):
                raise ValueError("logical value is released before its last use")

    def topological_order(self) -> tuple[str, ...]:
        """Return a deterministic topological order or reject a causal cycle."""

        original_order = {node.node_id: index for index, node in enumerate(self.nodes)}
        indegree = {node.node_id: 0 for node in self.nodes}
        successors: dict[str, list[str]] = defaultdict(list)
        for edge in self.edges:
            successors[edge.predecessor].append(edge.successor)
            indegree[edge.successor] += 1

        ready = deque(node.node_id for node in self.nodes if indegree[node.node_id] == 0)
        result: list[str] = []
        while ready:
            node_id = ready.popleft()
            result.append(node_id)
            for successor in sorted(successors[node_id], key=original_order.__getitem__):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
        if len(result) != len(self.nodes):
            raise ValueError("DAG contains a causal cycle")
        return tuple(result)

    @property
    def kind_counts(self) -> Counter[DagNodeKind]:
        return Counter(node.kind for node in self.nodes)

    @property
    def critical_path_node_count(self) -> int:
        """Count unit-weight semantic nodes on the longest dependency path."""

        predecessors: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            predecessors[edge.successor].add(edge.predecessor)
        depth: dict[str, int] = {}
        for node_id in self.topological_order():
            depth[node_id] = 1 + max(
                (depth[predecessor] for predecessor in predecessors[node_id]),
                default=0,
            )
        return max(depth.values(), default=0)


def dag_to_data(dag: CircuitDag) -> dict[str, Any]:
    """Convert a DAG to a deterministic JSON-compatible object."""

    return {
        "circuit_id": dag.circuit_id,
        "classical_values": [
            {
                "producer_node_id": value.producer_node_id,
                "value_id": value.value_id,
            }
            for value in dag.classical_values
        ],
        "edges": [
            {
                "kind": edge.kind.value,
                "predecessor": edge.predecessor,
                "resource_ids": list(edge.resource_ids),
                "successor": edge.successor,
            }
            for edge in dag.edges
        ],
        "evidence_status": dag.evidence_status.value,
        "lifetimes": [
            {
                "allocation_node_id": lifetime.allocation_node_id,
                "escapes_owner": lifetime.escapes_owner,
                "first_node_id": lifetime.first_node_id,
                "initialization": lifetime.initialization,
                "last_node_id": lifetime.last_node_id,
                "must_preserve_initial_state": lifetime.must_preserve_initial_state,
                "must_store_on_release": lifetime.must_store_on_release,
                "release": lifetime.release,
                "release_node_id": lifetime.release_node_id,
                "residency": lifetime.residency,
                "role": lifetime.role,
                "value_id": lifetime.value_id,
                "wire_id": lifetime.wire_id,
            }
            for lifetime in dag.lifetimes
        ],
        "nodes": [
            {
                "arithmetic_region": node.arithmetic_region,
                "classical_inputs": list(node.classical_inputs),
                "classical_outputs": list(node.classical_outputs),
                "kind": node.kind.value,
                "modified_values": list(node.modified_values),
                "node_id": node.node_id,
                "operand_roles": list(node.operand_roles),
                "pauli_terms": list(node.pauli_terms),
                "required_memory_values": list(node.required_memory_values),
                "required_processor_values": list(node.required_processor_values),
                "semantic_action": node.semantic_action,
                "source_opcode": node.source_opcode,
                "source_operation_id": node.source_operation_id,
                "source_operation_index": node.source_operation_index,
                "value_support": list(node.value_support),
                "wire_support": list(node.wire_support),
            }
            for node in dag.nodes
        ],
        "schema": dag.schema,
        "schema_version": dag.schema_version,
        "source": {
            "commit": dag.source.commit,
            "generator": dag.source.generator,
            "oracle_schema": dag.source.oracle_schema,
            "oracle_schema_version": dag.source.oracle_schema_version,
            "repository": dag.source.repository,
            "semantic_mapping_version": dag.source.semantic_mapping_version,
            "unit_decomposition": dag.source.unit_decomposition,
            "verification_method": dag.source.verification_method,
            "verification_status": dag.source.verification_status,
        },
        "source_operation_count": dag.source_operation_count,
        "width": dag.width,
    }


def dumps_dag(dag: CircuitDag) -> str:
    """Serialize a DAG canonically for hashing and regression comparison."""

    return json.dumps(dag_to_data(dag), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
