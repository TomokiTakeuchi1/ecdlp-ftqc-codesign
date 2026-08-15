"""Read-only adapter from the verified Gidney oracle to the local causal DAG."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import cast

from ecdlp_ftqc.metadata import (
    CircuitDag,
    ClassicalValue,
    DagEdge,
    DagNode,
    DagNodeKind,
    DependencyKind,
    EvidenceStatus,
    SourceReference,
    ValueLifetime,
)

PINNED_GIDNEY_SOURCE_COMMIT = "8c1638805e7246c30117a0251526661039df1369"
GIDNEY_SOURCE_REPOSITORY = "runtime-metadata-benchmark"
GIDNEY_ORACLE_SCHEMA = "runtime-metadata-benchmark/oracle"
GIDNEY_ORACLE_SCHEMA_VERSION = 3
GIDNEY_GENERATOR = "runtime_metadata_benchmark.gidney"
GIDNEY_SEMANTIC_MAPPING_VERSION = 4
GIDNEY_UNIT_DECOMPOSITION = "operation_atomic_live_local_v1"
GIDNEY_VERIFICATION_STATUS = "verified_for_runtime_contract"
_EXHAUSTIVE_METHOD = "exhaustive_small_width_coherent_regression"
_GENERAL_METHOD = "paper_general_construction_with_verified_local_gadget_and_invariants"

_OPCODE_KIND = {
    "allocate": "allocation",
    "cnot": "unitary",
    "temporary_and_compute": "unitary",
    "temporary_and_erase": "measurement",
    "release": "release",
}


class GidneyAdapterError(ValueError):
    """Raised when an input is not the pinned, verified Gidney oracle contract."""


@dataclass(frozen=True, slots=True)
class _SourceOperation:
    operation_id: str
    kind: str
    wires: tuple[str, ...]
    values: tuple[str, ...]
    modified_values: tuple[str, ...]
    source_opcode: str


@dataclass(frozen=True, slots=True)
class _SourceUnit:
    operation_id: str
    memory_support: tuple[str, ...]
    occupancy_support: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SourceLifetime:
    value_id: str
    wire_id: str
    first_use_operation: str
    last_use_operation: str
    allocation_operation: str | None
    release_operation: str | None
    initialization: str
    release: str
    residency: str
    role: str
    escapes_owner: bool | None
    must_store_on_release: bool | None
    must_preserve_initial_state: bool | None


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise GidneyAdapterError(f"{path}: expected an object with string keys")
    return cast(Mapping[str, object], value)


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise GidneyAdapterError(f"{path}: expected an array")
    return cast(Sequence[object], value)


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise GidneyAdapterError(f"{path}: expected a nonempty string")
    return value


def _optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GidneyAdapterError(f"{path}: expected an integer")
    return value


def _optional_bool(value: object, path: str) -> bool | None:
    if value is None:
        return None
    if type(value) is bool:
        return bool(value)
    raise GidneyAdapterError(f"{path}: expected true, false, or null")


def _strings(value: object, path: str) -> tuple[str, ...]:
    result = tuple(
        _string(item, f"{path}[{index}]")
        for index, item in enumerate(_sequence(value, path))
    )
    if len(result) != len(set(result)):
        raise GidneyAdapterError(f"{path}: duplicate IDs are not allowed")
    return result


def _field(obj: Mapping[str, object], name: str, path: str) -> object:
    if name not in obj:
        raise GidneyAdapterError(f"{path}: missing required field {name!r}")
    return obj[name]


def _parse_operation(value: object, index: int) -> _SourceOperation:
    path = f"$.program.operations[{index}]"
    obj = _mapping(value, path)
    opcode = _string(_field(obj, "source_opcode", path), f"{path}.source_opcode")
    if opcode not in _OPCODE_KIND:
        raise GidneyAdapterError(f"{path}: unsupported Gidney opcode {opcode!r}")
    kind = _string(_field(obj, "kind", path), f"{path}.kind")
    if kind != _OPCODE_KIND[opcode]:
        raise GidneyAdapterError(
            f"{path}: opcode {opcode!r} requires operation kind {_OPCODE_KIND[opcode]!r}"
        )
    wires = _strings(_field(obj, "wires", path), f"{path}.wires")
    values = _strings(_field(obj, "values", path), f"{path}.values")
    modified_values = _strings(
        _field(obj, "modified_values", path), f"{path}.modified_values"
    )
    if len(wires) != len(values):
        raise GidneyAdapterError(f"{path}: wire and logical-value arities differ")
    if not set(modified_values).issubset(values):
        raise GidneyAdapterError(f"{path}: modified values must be operation values")
    expected_arity = {
        "allocate": 1,
        "cnot": 2,
        "temporary_and_compute": 3,
        "temporary_and_erase": 3,
        "release": 1,
    }[opcode]
    if len(values) != expected_arity:
        raise GidneyAdapterError(
            f"{path}: opcode {opcode!r} requires arity {expected_arity}"
        )
    return _SourceOperation(
        operation_id=_string(
            _field(obj, "operation_id", path), f"{path}.operation_id"
        ),
        kind=kind,
        wires=wires,
        values=values,
        modified_values=modified_values,
        source_opcode=opcode,
    )


def _parse_unit(value: object, index: int) -> _SourceUnit:
    path = f"$.program.units[{index}]"
    obj = _mapping(value, path)
    operation_ids = _strings(
        _field(obj, "operation_ids", path), f"{path}.operation_ids"
    )
    if len(operation_ids) != 1:
        raise GidneyAdapterError(
            f"{path}: mapping-v4 requires exactly one operation per unit"
        )
    return _SourceUnit(
        operation_id=operation_ids[0],
        memory_support=tuple(
            sorted(_strings(_field(obj, "memory_support", path), f"{path}.memory_support"))
        ),
        occupancy_support=tuple(
            sorted(
                _strings(
                    _field(obj, "occupancy_support", path),
                    f"{path}.occupancy_support",
                )
            )
        ),
    )


def _parse_lifetime(value: object, index: int) -> _SourceLifetime:
    path = f"$.program.lifetimes[{index}]"
    obj = _mapping(value, path)
    return _SourceLifetime(
        value_id=_string(_field(obj, "value_id", path), f"{path}.value_id"),
        wire_id=_string(_field(obj, "wire_id", path), f"{path}.wire_id"),
        first_use_operation=_string(
            _field(obj, "first_use_operation", path),
            f"{path}.first_use_operation",
        ),
        last_use_operation=_string(
            _field(obj, "last_use_operation", path),
            f"{path}.last_use_operation",
        ),
        allocation_operation=_optional_string(
            _field(obj, "allocation_operation", path),
            f"{path}.allocation_operation",
        ),
        release_operation=_optional_string(
            _field(obj, "release_operation", path),
            f"{path}.release_operation",
        ),
        initialization=_string(
            _field(obj, "initialization", path), f"{path}.initialization"
        ),
        release=_string(_field(obj, "release", path), f"{path}.release"),
        residency=_string(_field(obj, "residency", path), f"{path}.residency"),
        role=_string(_field(obj, "role", path), f"{path}.role"),
        escapes_owner=_optional_bool(
            _field(obj, "escapes_owner", path), f"{path}.escapes_owner"
        ),
        must_store_on_release=_optional_bool(
            _field(obj, "must_store_on_release", path),
            f"{path}.must_store_on_release",
        ),
        must_preserve_initial_state=_optional_bool(
            _field(obj, "must_preserve_initial_state", path),
            f"{path}.must_preserve_initial_state",
        ),
    )


def _source_reference(
    root: Mapping[str, object],
    configuration: Mapping[str, object],
    source_commit: str,
) -> tuple[SourceReference, int, EvidenceStatus]:
    schema = _string(_field(root, "schema", "$"), "$.schema")
    schema_version = _integer(
        _field(root, "schema_version", "$"), "$.schema_version"
    )
    if schema != GIDNEY_ORACLE_SCHEMA or schema_version != GIDNEY_ORACLE_SCHEMA_VERSION:
        raise GidneyAdapterError("unsupported source oracle schema or version")

    expected_configuration: tuple[tuple[str, object], ...] = (
        ("generator", GIDNEY_GENERATOR),
        ("semantic_mapping_version", GIDNEY_SEMANTIC_MAPPING_VERSION),
        ("unit_decomposition", GIDNEY_UNIT_DECOMPOSITION),
        ("phase_correction_verified", True),
    )
    for name, expected in expected_configuration:
        observed = _field(configuration, name, "$.configuration")
        if observed != expected:
            raise GidneyAdapterError(
                f"$.configuration.{name}: expected {expected!r}, observed {observed!r}"
            )
    width = _integer(_field(configuration, "width", "$.configuration"), "$.configuration.width")
    if width < 2:
        raise GidneyAdapterError("$.configuration.width: expected at least two")
    provenance = _mapping(
        _field(configuration, "phase_verification_provenance", "$.configuration"),
        "$.configuration.phase_verification_provenance",
    )
    method = _string(
        _field(provenance, "method", "$.configuration.phase_verification_provenance"),
        "$.configuration.phase_verification_provenance.method",
    )
    status = _string(
        _field(provenance, "status", "$.configuration.phase_verification_provenance"),
        "$.configuration.phase_verification_provenance.status",
    )
    if status != GIDNEY_VERIFICATION_STATUS:
        raise GidneyAdapterError("source oracle is not verified for the runtime contract")
    if method == _EXHAUSTIVE_METHOD:
        evidence_status = EvidenceStatus.NUMERICAL
    elif method == _GENERAL_METHOD:
        evidence_status = EvidenceStatus.LITERATURE
    else:
        raise GidneyAdapterError(f"unsupported phase-verification method {method!r}")
    return (
        SourceReference(
            repository=GIDNEY_SOURCE_REPOSITORY,
            commit=source_commit,
            oracle_schema=schema,
            oracle_schema_version=schema_version,
            generator=GIDNEY_GENERATOR,
            semantic_mapping_version=GIDNEY_SEMANTIC_MAPPING_VERSION,
            unit_decomposition=GIDNEY_UNIT_DECOMPOSITION,
            verification_method=method,
            verification_status=status,
        ),
        width,
        evidence_status,
    )


def _normal_node(
    operation: _SourceOperation,
    operation_index: int,
    unit: _SourceUnit,
) -> DagNode:
    kind = {
        "allocate": DagNodeKind.ALLOCATE,
        "cnot": DagNodeKind.CNOT,
        "temporary_and_compute": DagNodeKind.TEMPORARY_AND_COMPUTE,
        "release": DagNodeKind.RELEASE,
    }[operation.source_opcode]
    action = {
        "allocate": "allocate_t_state_temporary",
        "cnot": "cnot",
        "temporary_and_compute": "temporary_logical_and_compute",
        "release": "release_measured_temporary",
    }[operation.source_opcode]
    operand_roles = {
        "allocate": ("allocated",),
        "cnot": ("control", "target"),
        "temporary_and_compute": ("control", "control", "target"),
        "release": ("released",),
    }[operation.source_opcode]
    return DagNode(
        node_id=operation.operation_id,
        kind=kind,
        source_operation_id=operation.operation_id,
        source_operation_index=operation_index,
        source_opcode=operation.source_opcode,
        semantic_action=action,
        arithmetic_region="gidney_ripple_adder",
        wire_support=operation.wires,
        value_support=operation.values,
        operand_roles=operand_roles,
        pauli_terms=(),
        modified_values=operation.modified_values,
        required_memory_values=unit.memory_support,
        required_processor_values=unit.occupancy_support,
    )


def _erase_nodes(
    operation: _SourceOperation,
    operation_index: int,
    unit: _SourceUnit,
) -> tuple[DagNode, DagNode, ClassicalValue]:
    controls = operation.values[:-1]
    control_wires = operation.wires[:-1]
    measured_value = operation.values[-1]
    measured_wire = operation.wires[-1]
    outcome_id = f"classical:{operation.operation_id}:x_outcome"
    measure_id = f"{operation.operation_id}:measure_x"
    frame_id = f"{operation.operation_id}:conditional_cz"
    measurement = DagNode(
        node_id=measure_id,
        kind=DagNodeKind.MEASUREMENT,
        source_operation_id=operation.operation_id,
        source_operation_index=operation_index,
        source_opcode=operation.source_opcode,
        semantic_action="measure_temporary_in_x_basis",
        arithmetic_region="gidney_ripple_adder",
        wire_support=(measured_wire,),
        value_support=(measured_value,),
        operand_roles=("measured",),
        pauli_terms=(f"X:{measured_value}",),
        modified_values=(measured_value,),
        required_memory_values=unit.memory_support,
        required_processor_values=unit.occupancy_support,
        classical_outputs=(outcome_id,),
    )
    frame = DagNode(
        node_id=frame_id,
        kind=DagNodeKind.CLASSICAL_FRAME_UPDATE,
        source_operation_id=operation.operation_id,
        source_operation_index=operation_index,
        source_opcode=operation.source_opcode,
        semantic_action="conditional_cz_on_measurement_one",
        arithmetic_region="gidney_ripple_adder",
        wire_support=control_wires,
        value_support=controls,
        operand_roles=("conditional_cz_support", "conditional_cz_support"),
        pauli_terms=(),
        modified_values=controls,
        required_memory_values=tuple(
            value for value in unit.memory_support if value != measured_value
        ),
        required_processor_values=tuple(
            value for value in unit.occupancy_support if value != measured_value
        ),
        classical_inputs=(outcome_id,),
    )
    return measurement, frame, ClassicalValue(outcome_id, measure_id)


def _expanded_node_for_value(
    source_operation_id: str,
    value_id: str,
    nodes_by_source: Mapping[str, tuple[DagNode, ...]],
    *,
    choose_last: bool,
) -> str:
    candidates = tuple(
        node.node_id
        for node in nodes_by_source.get(source_operation_id, ())
        if value_id in node.value_support
    )
    if not candidates:
        raise GidneyAdapterError(
            f"lifetime value {value_id!r} is absent from source operation "
            f"{source_operation_id!r}"
        )
    return candidates[-1] if choose_last else candidates[0]


def adapt_gidney_oracle(
    oracle_data: Mapping[str, object],
    *,
    source_commit: str = PINNED_GIDNEY_SOURCE_COMMIT,
) -> CircuitDag:
    """Convert oracle schema v3 into an explicit causal DAG.

    The source operation list supplies only deterministic circuit order.  This
    adapter derives per-wire causal edges and does not insert edges merely
    because two disjoint operations were adjacent in that list.
    """

    root = _mapping(oracle_data, "$")
    configuration = _mapping(
        _field(root, "configuration", "$"), "$.configuration"
    )
    source, width, evidence_status = _source_reference(
        root, configuration, source_commit
    )
    program = _mapping(_field(root, "program", "$"), "$.program")
    operations = tuple(
        _parse_operation(value, index)
        for index, value in enumerate(
            _sequence(_field(program, "operations", "$.program"), "$.program.operations")
        )
    )
    if len({operation.operation_id for operation in operations}) != len(operations):
        raise GidneyAdapterError("source operation IDs must be unique")
    units = tuple(
        _parse_unit(value, index)
        for index, value in enumerate(
            _sequence(_field(program, "units", "$.program"), "$.program.units")
        )
    )
    unit_by_operation = {unit.operation_id: unit for unit in units}
    if len(unit_by_operation) != len(units) or set(unit_by_operation) != {
        operation.operation_id for operation in operations
    }:
        raise GidneyAdapterError(
            "operation-atomic units must cover every source operation exactly once"
        )
    source_lifetimes = tuple(
        _parse_lifetime(value, index)
        for index, value in enumerate(
            _sequence(_field(program, "lifetimes", "$.program"), "$.program.lifetimes")
        )
    )
    if len({lifetime.value_id for lifetime in source_lifetimes}) != len(source_lifetimes):
        raise GidneyAdapterError("source lifetime value IDs must be unique")

    nodes: list[DagNode] = []
    classical_values: list[ClassicalValue] = []
    nodes_by_source: dict[str, tuple[DagNode, ...]] = {}
    feed_forward_edges: list[DagEdge] = []
    for operation_index, operation in enumerate(operations):
        unit = unit_by_operation[operation.operation_id]
        expanded: tuple[DagNode, ...]
        if operation.source_opcode == "temporary_and_erase":
            measurement, frame, outcome = _erase_nodes(operation, operation_index, unit)
            expanded = (measurement, frame)
            classical_values.append(outcome)
            feed_forward_edges.append(
                DagEdge(
                    predecessor=measurement.node_id,
                    successor=frame.node_id,
                    kind=DependencyKind.CLASSICAL_FEED_FORWARD,
                    resource_ids=(outcome.value_id,),
                )
            )
        else:
            expanded = (_normal_node(operation, operation_index, unit),)
        nodes.extend(expanded)
        nodes_by_source[operation.operation_id] = expanded

    node_by_id = {node.node_id: node for node in nodes}
    edge_resources: dict[tuple[str, str, DependencyKind], set[str]] = defaultdict(set)
    last_node_by_wire: dict[str, str] = {}
    for node in nodes:
        for wire_id in node.wire_support:
            predecessor_id = last_node_by_wire.get(wire_id)
            if predecessor_id is not None:
                predecessor = node_by_id[predecessor_id]
                kind = (
                    DependencyKind.VALUE_LIFETIME
                    if predecessor.kind is DagNodeKind.ALLOCATE
                    or node.kind is DagNodeKind.RELEASE
                    else DependencyKind.QUANTUM_ORDER
                )
                edge_resources[(predecessor_id, node.node_id, kind)].add(wire_id)
            last_node_by_wire[wire_id] = node.node_id
    for edge in feed_forward_edges:
        edge_resources[(edge.predecessor, edge.successor, edge.kind)].update(
            edge.resource_ids
        )
    node_position = {node.node_id: index for index, node in enumerate(nodes)}
    edges = tuple(
        DagEdge(predecessor, successor, kind, tuple(sorted(resources)))
        for (predecessor, successor, kind), resources in sorted(
            edge_resources.items(),
            key=lambda item: (
                node_position[item[0][0]],
                node_position[item[0][1]],
                item[0][2].value,
            ),
        )
    )

    lifetimes = tuple(
        ValueLifetime(
            value_id=lifetime.value_id,
            wire_id=lifetime.wire_id,
            first_node_id=_expanded_node_for_value(
                lifetime.first_use_operation,
                lifetime.value_id,
                nodes_by_source,
                choose_last=False,
            ),
            last_node_id=_expanded_node_for_value(
                lifetime.last_use_operation,
                lifetime.value_id,
                nodes_by_source,
                choose_last=True,
            ),
            allocation_node_id=(
                _expanded_node_for_value(
                    lifetime.allocation_operation,
                    lifetime.value_id,
                    nodes_by_source,
                    choose_last=False,
                )
                if lifetime.allocation_operation is not None
                else None
            ),
            release_node_id=(
                _expanded_node_for_value(
                    lifetime.release_operation,
                    lifetime.value_id,
                    nodes_by_source,
                    choose_last=True,
                )
                if lifetime.release_operation is not None
                else None
            ),
            initialization=lifetime.initialization,
            release=lifetime.release,
            residency=lifetime.residency,
            role=lifetime.role,
            escapes_owner=lifetime.escapes_owner,
            must_store_on_release=lifetime.must_store_on_release,
            must_preserve_initial_state=lifetime.must_preserve_initial_state,
        )
        for lifetime in source_lifetimes
    )
    return CircuitDag(
        circuit_id=f"gidney-ripple-adder-width-{width}",
        width=width,
        source_operation_count=len(operations),
        source=source,
        evidence_status=evidence_status,
        nodes=tuple(nodes),
        edges=edges,
        classical_values=tuple(classical_values),
        lifetimes=lifetimes,
    )


def load_gidney_oracle_dag(
    path: Path,
    *,
    source_commit: str = PINNED_GIDNEY_SOURCE_COMMIT,
) -> CircuitDag:
    """Load a source oracle JSON file and adapt it through the validated boundary."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GidneyAdapterError(f"cannot read Gidney oracle {path}: {exc}") from exc
    return adapt_gidney_oracle(_mapping(value, "$"), source_commit=source_commit)


def generate_gidney_dag(
    width: int,
    *,
    source_commit: str = PINNED_GIDNEY_SOURCE_COMMIT,
) -> CircuitDag:
    """Generate through an installed external frontend and then cross the JSON boundary.

    ``source_commit`` is recorded provenance, not a checkout verifier.  Artifact
    generation must independently verify that the imported package is from that
    commit; the checked-in fixture generator performs that check.
    """

    try:
        gidney = import_module("runtime_metadata_benchmark.gidney")
        oracle_codec = import_module("runtime_metadata_benchmark.ir.oracle_json")
        generate = gidney.generate_gidney_adder
        to_oracle = gidney.to_oracle_document
        oracle_to_data = oracle_codec.oracle_to_data
    except (ImportError, AttributeError) as exc:
        raise GidneyAdapterError(
            "runtime-metadata-benchmark with the verified Gidney frontend is required"
        ) from exc
    data = oracle_to_data(to_oracle(generate(width)))
    return adapt_gidney_oracle(_mapping(data, "$"), source_commit=source_commit)
