"""Phase-exact logical lowering before selecting a QEC-native gadget."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from ecdlp_ftqc.metadata import CircuitDag, DagNode, DagNodeKind, EvidenceStatus

LOGICAL_TRACE_SCHEMA = "ecdlp-ftqc/phase-exact-logical-trace"
LOGICAL_TRACE_SCHEMA_VERSION = 1


class LogicalPrimitiveKind(str, Enum):
    """Logical actions whose phase semantics are fixed before QEC compilation."""

    PREPARE_T = "prepare_t"
    X = "x"
    CNOT = "cnot"
    T = "t"
    T_DAGGER = "t_dagger"
    H = "h"
    S = "s"
    MEASURE_X = "measure_x"
    MEASURE_Y = "measure_y"
    MEASURE_Z = "measure_z"
    MEASURE_XX = "measure_xx"
    MEASURE_ZZ = "measure_zz"
    MEASURE_GENERAL_PAULI = "measure_general_pauli"
    CONDITIONAL_CZ_FRAME = "conditional_cz_frame"
    RELEASE = "release"


class PrimitiveDependencyKind(str, Enum):
    """Origin of a dependency in the phase-exact trace."""

    FIGURE_3_SEQUENCE = "figure_3_sequence"
    SOURCE_GATE_DECOMPOSITION = "source_gate_decomposition"
    SOURCE_DAG = "source_dag"


@dataclass(frozen=True, slots=True)
class LogicalPrimitive:
    """One exact logical action, with no claimed QEC implementation or duration."""

    primitive_id: str
    source_node_id: str
    kind: LogicalPrimitiveKind
    logical_support: tuple[str, ...]
    pauli_terms: tuple[str, ...] = ()
    classical_inputs: tuple[str, ...] = ()
    classical_outputs: tuple[str, ...] = ()
    resource_state_demand: int = 0
    evidence_status: EvidenceStatus = EvidenceStatus.CHECK

    def __post_init__(self) -> None:
        if not self.primitive_id or not self.source_node_id:
            raise ValueError("primitive and source-node IDs cannot be empty")
        for values in (
            self.logical_support,
            self.pauli_terms,
            self.classical_inputs,
            self.classical_outputs,
        ):
            if len(values) != len(set(values)):
                raise ValueError("primitive support and token lists cannot contain duplicates")
        if self.resource_state_demand < 0:
            raise ValueError("resource-state demand cannot be negative")


@dataclass(frozen=True, slots=True)
class PrimitiveDependency:
    """A dependency between phase-exact primitives."""

    predecessor: str
    successor: str
    kind: PrimitiveDependencyKind
    source_reason: str

    def __post_init__(self) -> None:
        if not self.predecessor or not self.successor or not self.source_reason:
            raise ValueError("primitive dependency fields cannot be empty")
        if self.predecessor == self.successor:
            raise ValueError("a primitive cannot depend on itself")


@dataclass(frozen=True, slots=True)
class LogicalTrace:
    """Validated phase-exact trace derived from a QEC-neutral source DAG."""

    trace_id: str
    source_circuit_id: str
    source_dag_schema_version: int
    source_evidence_status: EvidenceStatus
    peak_source_processor_occupancy: int
    primitives: tuple[LogicalPrimitive, ...]
    dependencies: tuple[PrimitiveDependency, ...]
    schema: str = LOGICAL_TRACE_SCHEMA
    schema_version: int = LOGICAL_TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trace_id or not self.source_circuit_id:
            raise ValueError("trace and source-circuit IDs cannot be empty")
        if self.source_dag_schema_version < 1:
            raise ValueError("source DAG schema version must be positive")
        if self.peak_source_processor_occupancy < 1:
            raise ValueError("peak source processor occupancy must be positive")
        if self.schema != LOGICAL_TRACE_SCHEMA:
            raise ValueError("unsupported logical-trace schema")
        if self.schema_version != LOGICAL_TRACE_SCHEMA_VERSION:
            raise ValueError("unsupported logical-trace schema version")
        self._validate()

    def _validate(self) -> None:
        primitive_ids = tuple(primitive.primitive_id for primitive in self.primitives)
        if len(primitive_ids) != len(set(primitive_ids)):
            raise ValueError("logical primitive IDs must be unique")
        known = set(primitive_ids)
        dependency_keys = tuple(
            (
                dependency.predecessor,
                dependency.successor,
                dependency.kind,
                dependency.source_reason,
            )
            for dependency in self.dependencies
        )
        if len(dependency_keys) != len(set(dependency_keys)):
            raise ValueError("logical primitive dependencies must be unique")
        for dependency in self.dependencies:
            if dependency.predecessor not in known or dependency.successor not in known:
                raise ValueError("primitive dependency references an unknown primitive")
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        """Return a deterministic primitive order or reject a dependency cycle."""

        original_order = {
            primitive.primitive_id: position
            for position, primitive in enumerate(self.primitives)
        }
        indegree = {primitive_id: 0 for primitive_id in original_order}
        successors: dict[str, set[str]] = defaultdict(set)
        for dependency in self.dependencies:
            if dependency.successor not in successors[dependency.predecessor]:
                successors[dependency.predecessor].add(dependency.successor)
                indegree[dependency.successor] += 1
        ready = deque(
            primitive_id for primitive_id in original_order if indegree[primitive_id] == 0
        )
        result: list[str] = []
        while ready:
            primitive_id = ready.popleft()
            result.append(primitive_id)
            for successor in sorted(
                successors[primitive_id], key=original_order.__getitem__
            ):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
        if len(result) != len(self.primitives):
            raise ValueError("logical trace contains a dependency cycle")
        return tuple(result)


def _primitive(
    node: DagNode,
    suffix: str,
    kind: LogicalPrimitiveKind,
    logical_support: tuple[str, ...],
    *,
    pauli_terms: tuple[str, ...] = (),
    classical_inputs: tuple[str, ...] = (),
    classical_outputs: tuple[str, ...] = (),
    resource_state_demand: int = 0,
    evidence_status: EvidenceStatus,
) -> LogicalPrimitive:
    return LogicalPrimitive(
        primitive_id=f"{node.node_id}::logical:{suffix}",
        source_node_id=node.node_id,
        kind=kind,
        logical_support=logical_support,
        pauli_terms=pauli_terms,
        classical_inputs=classical_inputs,
        classical_outputs=classical_outputs,
        resource_state_demand=resource_state_demand,
        evidence_status=evidence_status,
    )


def _expand_figure_3_compute(
    node: DagNode, evidence_status: EvidenceStatus
) -> tuple[tuple[LogicalPrimitive, ...], tuple[PrimitiveDependency, ...]]:
    if len(node.value_support) != 3:
        raise ValueError("temporary logical AND requires two controls and one target")
    control_x, control_y, temporary = node.value_support
    specifications = (
        ("00_cnot_x_to_a", LogicalPrimitiveKind.CNOT, (control_x, temporary), 0),
        ("01_cnot_y_to_a", LogicalPrimitiveKind.CNOT, (control_y, temporary), 0),
        ("02_cnot_a_to_x", LogicalPrimitiveKind.CNOT, (temporary, control_x), 0),
        ("03_cnot_a_to_y", LogicalPrimitiveKind.CNOT, (temporary, control_y), 0),
        ("04_t_dagger_x", LogicalPrimitiveKind.T_DAGGER, (control_x,), 1),
        ("05_t_dagger_y", LogicalPrimitiveKind.T_DAGGER, (control_y,), 1),
        ("06_t_a", LogicalPrimitiveKind.T, (temporary,), 1),
        ("07_cnot_a_to_x", LogicalPrimitiveKind.CNOT, (temporary, control_x), 0),
        ("08_cnot_a_to_y", LogicalPrimitiveKind.CNOT, (temporary, control_y), 0),
        ("09_h_a", LogicalPrimitiveKind.H, (temporary,), 0),
        ("10_s_a", LogicalPrimitiveKind.S, (temporary,), 0),
    )
    primitives = tuple(
        _primitive(
            node,
            suffix,
            kind,
            support,
            resource_state_demand=demand,
            evidence_status=evidence_status,
        )
        for suffix, kind, support, demand in specifications
    )
    by_suffix = {primitive.primitive_id.rsplit(":", maxsplit=1)[-1]: primitive for primitive in primitives}

    sequence_edges = (
        ("00_cnot_x_to_a", "01_cnot_y_to_a"),
        ("01_cnot_y_to_a", "02_cnot_a_to_x"),
        ("02_cnot_a_to_x", "03_cnot_a_to_y"),
        ("03_cnot_a_to_y", "04_t_dagger_x"),
        ("03_cnot_a_to_y", "05_t_dagger_y"),
        ("03_cnot_a_to_y", "06_t_a"),
        ("04_t_dagger_x", "07_cnot_a_to_x"),
        ("05_t_dagger_y", "07_cnot_a_to_x"),
        ("06_t_a", "07_cnot_a_to_x"),
        ("07_cnot_a_to_x", "08_cnot_a_to_y"),
        ("08_cnot_a_to_y", "09_h_a"),
        ("09_h_a", "10_s_a"),
    )
    dependencies = tuple(
        PrimitiveDependency(
            predecessor=by_suffix[predecessor].primitive_id,
            successor=by_suffix[successor].primitive_id,
            kind=PrimitiveDependencyKind.FIGURE_3_SEQUENCE,
            source_reason="Gidney Figure 3 exact gate order",
        )
        for predecessor, successor in sequence_edges
    )
    return primitives, dependencies


def _expand_node(
    node: DagNode, evidence_status: EvidenceStatus
) -> tuple[tuple[LogicalPrimitive, ...], tuple[PrimitiveDependency, ...]]:
    if node.kind is DagNodeKind.TEMPORARY_AND_COMPUTE:
        return _expand_figure_3_compute(node, evidence_status)
    if node.kind is DagNodeKind.ALLOCATE:
        primitives = (
            _primitive(
                node,
                "prepare_t",
                LogicalPrimitiveKind.PREPARE_T,
                node.value_support,
                resource_state_demand=1,
                evidence_status=evidence_status,
            ),
        )
    elif node.kind is DagNodeKind.CNOT:
        primitives = (
            _primitive(
                node,
                "cnot",
                LogicalPrimitiveKind.CNOT,
                node.value_support,
                evidence_status=evidence_status,
            ),
        )
    elif node.kind is DagNodeKind.MEASUREMENT:
        if node.semantic_action != "measure_temporary_in_x_basis":
            raise ValueError(f"unsupported Gidney measurement {node.semantic_action!r}")
        primitives = (
            _primitive(
                node,
                "measure_x",
                LogicalPrimitiveKind.MEASURE_X,
                node.value_support,
                pauli_terms=node.pauli_terms,
                classical_outputs=node.classical_outputs,
                evidence_status=evidence_status,
            ),
        )
    elif node.kind is DagNodeKind.CLASSICAL_FRAME_UPDATE:
        if node.semantic_action != "conditional_cz_on_measurement_one":
            raise ValueError(f"unsupported Gidney frame update {node.semantic_action!r}")
        primitives = (
            _primitive(
                node,
                "conditional_cz_frame",
                LogicalPrimitiveKind.CONDITIONAL_CZ_FRAME,
                node.value_support,
                classical_inputs=node.classical_inputs,
                evidence_status=evidence_status,
            ),
        )
    elif node.kind is DagNodeKind.RELEASE:
        primitives = (
            _primitive(
                node,
                "release",
                LogicalPrimitiveKind.RELEASE,
                node.value_support,
                evidence_status=evidence_status,
            ),
        )
    else:
        raise ValueError(f"unsupported Gidney DAG node kind {node.kind.value!r}")
    return primitives, ()


def lower_gidney_phase_exact(dag: CircuitDag) -> LogicalTrace:
    """Expand the accepted Gidney DAG into its exact Figure-3 Clifford+T trace.

    This function does not claim that CNOT, H, S, or T is native to a mitten
    block.  A backend must still compile these primitives to its instruction
    set.  The initial ``|T>`` preparation and the three T/T-dagger gates in
    each temporary-AND computation retain the paper's four-resource count.
    """

    if not dag.circuit_id.startswith("gidney-ripple-adder-width-"):
        raise ValueError("phase-exact Gidney lowering received a different circuit")
    primitives: list[LogicalPrimitive] = []
    dependencies: list[PrimitiveDependency] = []
    boundaries: dict[str, tuple[str, str]] = {}
    for node in dag.nodes:
        expanded, internal_dependencies = _expand_node(node, dag.evidence_status)
        primitives.extend(expanded)
        dependencies.extend(internal_dependencies)
        boundaries[node.node_id] = (
            expanded[0].primitive_id,
            expanded[-1].primitive_id,
        )
    for edge in dag.edges:
        predecessor = boundaries[edge.predecessor][1]
        successor = boundaries[edge.successor][0]
        dependencies.append(
            PrimitiveDependency(
                predecessor=predecessor,
                successor=successor,
                kind=PrimitiveDependencyKind.SOURCE_DAG,
                source_reason=f"{edge.kind.value}:{','.join(edge.resource_ids)}",
            )
        )
    peak_occupancy = max(
        len(node.required_processor_values) for node in dag.nodes
    )
    return LogicalTrace(
        trace_id=f"{dag.circuit_id}:figure-3-logical-v1",
        source_circuit_id=dag.circuit_id,
        source_dag_schema_version=dag.schema_version,
        source_evidence_status=dag.evidence_status,
        peak_source_processor_occupancy=peak_occupancy,
        primitives=tuple(primitives),
        dependencies=tuple(dependencies),
    )
