"""Quantum-output-preserving lowering to adaptive Pauli measurements.

The lowering in this module is deliberately semantic rather than temporal.
It exposes the Pauli products, compiler carriers, measurement outcomes, and
frame updates needed by a CQLU backend, but it does not assign syndrome-round
durations to those actions.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ecdlp_ftqc.compiler.native_lowering import (
    LogicalPrimitive,
    LogicalPrimitiveKind,
    LogicalTrace,
)
from ecdlp_ftqc.metadata import EvidenceStatus

PBC_TRACE_SCHEMA = "ecdlp-ftqc/adaptive-pauli-measurement-trace"
PBC_TRACE_SCHEMA_VERSION = 1


class PbcOperationKind(str, Enum):
    """Semantic actions in the adaptive Pauli-measurement trace."""

    PREPARE = "prepare"
    MEASURE_PAULI = "measure_pauli"
    PAULI_FRAME_UPDATE = "pauli_frame_update"
    CONDITIONAL_CLIFFORD_FRAME = "conditional_clifford_frame"
    RELEASE = "release"
    REBIND_LOGICAL_VALUE = "rebind_logical_value"


class PbcDependencyKind(str, Enum):
    """Reason why one PBC operation precedes another."""

    GADGET_SEQUENCE = "gadget_sequence"
    SOURCE_TRACE = "source_trace"
    CLASSICAL_FEED_FORWARD = "classical_feed_forward"


class AncillaRole(str, Enum):
    """Compiler-created carrier roles, distinct from source logical values."""

    CNOT_SCRATCH = "cnot_scratch"
    MAGIC_T = "magic_t"
    TELEPORT_OUTPUT = "teleport_output"


@dataclass(frozen=True, slots=True)
class ClassicalLiteral:
    """A required measurement bit, using 0 for +1 and 1 for -1."""

    token: str
    value: int

    def __post_init__(self) -> None:
        if not self.token:
            raise ValueError("classical-literal token cannot be empty")
        if self.value not in (0, 1):
            raise ValueError("measurement bits must be zero or one")


@dataclass(frozen=True, slots=True)
class PreparedStateChoice:
    """One branch of an adaptive stabilizer or magic-state preparation."""

    state: str
    condition: tuple[ClassicalLiteral, ...] = ()

    def __post_init__(self) -> None:
        if not self.state:
            raise ValueError("prepared state cannot be empty")
        tokens = tuple(literal.token for literal in self.condition)
        if len(tokens) != len(set(tokens)):
            raise ValueError("a prepared-state condition cannot repeat a token")


@dataclass(frozen=True, slots=True)
class FrameUpdate:
    """A Pauli-frame update controlled by a parity and optional branch."""

    carrier_id: str
    pauli: str
    parity_tokens: tuple[str, ...]
    condition: tuple[ClassicalLiteral, ...] = ()

    def __post_init__(self) -> None:
        if not self.carrier_id:
            raise ValueError("frame-update carrier cannot be empty")
        if self.pauli not in {"X", "Y", "Z"}:
            raise ValueError("a Pauli-frame update must be X, Y, or Z")
        if not self.parity_tokens:
            raise ValueError("a frame update requires a nonempty parity")
        if len(self.parity_tokens) != len(set(self.parity_tokens)):
            raise ValueError("frame-update parity cannot repeat a token")
        condition_tokens = tuple(literal.token for literal in self.condition)
        if len(condition_tokens) != len(set(condition_tokens)):
            raise ValueError("a frame-update condition cannot repeat a token")


@dataclass(frozen=True, slots=True)
class PbcOperation:
    """One exact semantic operation without an asserted native duration."""

    operation_id: str
    source_primitive_id: str
    kind: PbcOperationKind
    logical_support: tuple[str, ...]
    carrier_support: tuple[str, ...]
    pauli_terms: tuple[str, ...] = ()
    classical_inputs: tuple[str, ...] = ()
    classical_outputs: tuple[str, ...] = ()
    prepared_states: tuple[PreparedStateChoice, ...] = ()
    frame_updates: tuple[FrameUpdate, ...] = ()
    resource_state_demand: int = 0
    semantic_evidence_status: EvidenceStatus = EvidenceStatus.CHECK
    runtime_evidence_status: EvidenceStatus = EvidenceStatus.CHECK
    note: str = ""

    def __post_init__(self) -> None:
        if not self.operation_id or not self.source_primitive_id:
            raise ValueError("PBC operation and source-primitive IDs cannot be empty")
        for values in (
            self.logical_support,
            self.carrier_support,
            self.pauli_terms,
            self.classical_inputs,
            self.classical_outputs,
        ):
            if len(values) != len(set(values)):
                raise ValueError("PBC support and token lists cannot contain duplicates")
        if self.resource_state_demand < 0:
            raise ValueError("resource-state demand cannot be negative")
        if self.kind is PbcOperationKind.PREPARE and not self.prepared_states:
            raise ValueError("a preparation requires at least one state choice")
        if self.kind is not PbcOperationKind.PREPARE and self.prepared_states:
            raise ValueError("only a preparation can contain prepared states")
        if self.kind is PbcOperationKind.MEASURE_PAULI:
            if not self.pauli_terms or len(self.classical_outputs) != 1:
                raise ValueError("a Pauli measurement requires support and one result")
        elif self.pauli_terms:
            raise ValueError("only a Pauli measurement can contain Pauli terms")
        if self.kind is PbcOperationKind.PAULI_FRAME_UPDATE and not self.frame_updates:
            raise ValueError("a Pauli-frame operation requires at least one update")
        if self.kind is not PbcOperationKind.PAULI_FRAME_UPDATE and self.frame_updates:
            raise ValueError("only a Pauli-frame operation can contain frame updates")


@dataclass(frozen=True, slots=True)
class PbcDependency:
    """A causal edge in the adaptive measurement trace."""

    predecessor: str
    successor: str
    kind: PbcDependencyKind
    reason: str

    def __post_init__(self) -> None:
        if not self.predecessor or not self.successor or not self.reason:
            raise ValueError("PBC dependency fields cannot be empty")
        if self.predecessor == self.successor:
            raise ValueError("a PBC operation cannot depend on itself")


@dataclass(frozen=True, slots=True)
class CompilerAncillaLifetime:
    """Allocation and release boundary of one compiler-created carrier."""

    carrier_id: str
    role: AncillaRole
    source_primitive_id: str
    allocation_operation_id: str
    release_operation_id: str

    def __post_init__(self) -> None:
        if any(
            not value
            for value in (
                self.carrier_id,
                self.source_primitive_id,
                self.allocation_operation_id,
                self.release_operation_id,
            )
        ):
            raise ValueError("compiler-ancilla lifetime fields cannot be empty")


@dataclass(frozen=True, slots=True)
class PbcTrace:
    """Validated adaptive measurement trace for a quantum-output subroutine."""

    trace_id: str
    source_trace_id: str
    source_evidence_status: EvidenceStatus
    peak_source_processor_occupancy: int
    minimum_reusable_compiler_scratch_slots: int
    operations: tuple[PbcOperation, ...]
    dependencies: tuple[PbcDependency, ...]
    compiler_ancillas: tuple[CompilerAncillaLifetime, ...]
    final_carriers: tuple[tuple[str, str], ...]
    schema: str = PBC_TRACE_SCHEMA
    schema_version: int = PBC_TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trace_id or not self.source_trace_id:
            raise ValueError("PBC trace IDs cannot be empty")
        if self.peak_source_processor_occupancy < 1:
            raise ValueError("source occupancy must be positive")
        if self.minimum_reusable_compiler_scratch_slots < 0:
            raise ValueError("compiler scratch count cannot be negative")
        if self.schema != PBC_TRACE_SCHEMA or self.schema_version != PBC_TRACE_SCHEMA_VERSION:
            raise ValueError("unsupported PBC trace schema identity")
        self._validate()

    @property
    def minimum_serial_processor_occupancy(self) -> int:
        """Necessary slots when one scratch carrier is reused serially."""

        return (
            self.peak_source_processor_occupancy
            + self.minimum_reusable_compiler_scratch_slots
        )

    @property
    def measurement_count(self) -> int:
        return sum(
            operation.kind is PbcOperationKind.MEASURE_PAULI
            for operation in self.operations
        )

    @property
    def resource_state_demand(self) -> int:
        return sum(operation.resource_state_demand for operation in self.operations)

    @property
    def pauli_supports(self) -> tuple[tuple[str, ...], ...]:
        return tuple(
            operation.pauli_terms
            for operation in self.operations
            if operation.kind is PbcOperationKind.MEASURE_PAULI
        )

    def _validate(self) -> None:
        operation_ids = tuple(operation.operation_id for operation in self.operations)
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("PBC operation IDs must be unique")
        known = set(operation_ids)
        for dependency in self.dependencies:
            if dependency.predecessor not in known or dependency.successor not in known:
                raise ValueError("PBC dependency references an unknown operation")
        produced_tokens: dict[str, str] = {}
        for operation in self.operations:
            for token in operation.classical_outputs:
                if token in produced_tokens:
                    raise ValueError("classical measurement tokens must be unique")
                produced_tokens[token] = operation.operation_id
        dependency_pairs = {
            (dependency.predecessor, dependency.successor)
            for dependency in self.dependencies
        }
        for operation in self.operations:
            referenced_tokens = set(operation.classical_inputs)
            for state in operation.prepared_states:
                referenced_tokens.update(literal.token for literal in state.condition)
            for update in operation.frame_updates:
                referenced_tokens.update(update.parity_tokens)
                referenced_tokens.update(literal.token for literal in update.condition)
            for token in referenced_tokens:
                producer = produced_tokens.get(token)
                if producer is None:
                    raise ValueError("PBC operation consumes an unknown classical token")
                if (producer, operation.operation_id) not in dependency_pairs:
                    raise ValueError("classical token lacks a direct feed-forward dependency")
        ancilla_ids = tuple(lifetime.carrier_id for lifetime in self.compiler_ancillas)
        if len(ancilla_ids) != len(set(ancilla_ids)):
            raise ValueError("compiler carriers must have unique IDs")
        for lifetime in self.compiler_ancillas:
            if (
                lifetime.allocation_operation_id not in known
                or lifetime.release_operation_id not in known
            ):
                raise ValueError("compiler-ancilla lifetime references an unknown operation")
        final_values = tuple(value for value, _ in self.final_carriers)
        if len(final_values) != len(set(final_values)):
            raise ValueError("final logical-value bindings must be unique")
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        """Return a deterministic order or reject a PBC dependency cycle."""

        original_order = {
            operation.operation_id: index
            for index, operation in enumerate(self.operations)
        }
        indegree = {operation_id: 0 for operation_id in original_order}
        successors: dict[str, set[str]] = defaultdict(set)
        for dependency in self.dependencies:
            if dependency.successor not in successors[dependency.predecessor]:
                successors[dependency.predecessor].add(dependency.successor)
                indegree[dependency.successor] += 1
        ready = deque(
            operation_id
            for operation_id in original_order
            if indegree[operation_id] == 0
        )
        result: list[str] = []
        while ready:
            operation_id = ready.popleft()
            result.append(operation_id)
            for successor in sorted(
                successors[operation_id], key=original_order.__getitem__
            ):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
        if len(result) != len(self.operations):
            raise ValueError("PBC trace contains a dependency cycle")
        return tuple(result)


@dataclass(slots=True)
class _GadgetBuilder:
    primitive: LogicalPrimitive
    operations: list[PbcOperation]
    dependencies: list[PbcDependency]
    ancillas: list[CompilerAncillaLifetime]
    local_counter: int = 0

    def operation_id(self, suffix: str) -> str:
        operation_id = f"{self.primitive.primitive_id}::pbc:{self.local_counter:02d}_{suffix}"
        self.local_counter += 1
        return operation_id

    def add(self, operation: PbcOperation) -> None:
        if self.operations:
            self.dependencies.append(
                PbcDependency(
                    predecessor=self.operations[-1].operation_id,
                    successor=operation.operation_id,
                    kind=PbcDependencyKind.GADGET_SEQUENCE,
                    reason="quantum-output-preserving gadget order",
                )
            )
        self.operations.append(operation)

    def add_direct_classical_dependencies(self, operation: PbcOperation) -> None:
        producers = {
            token: candidate.operation_id
            for candidate in self.operations
            for token in candidate.classical_outputs
        }
        tokens = set(operation.classical_inputs)
        for state in operation.prepared_states:
            tokens.update(literal.token for literal in state.condition)
        for update in operation.frame_updates:
            tokens.update(update.parity_tokens)
            tokens.update(literal.token for literal in update.condition)
        existing = {
            (dependency.predecessor, dependency.successor)
            for dependency in self.dependencies
        }
        for token in sorted(tokens):
            producer = producers[token]
            if (producer, operation.operation_id) not in existing:
                self.dependencies.append(
                    PbcDependency(
                        predecessor=producer,
                        successor=operation.operation_id,
                        kind=PbcDependencyKind.CLASSICAL_FEED_FORWARD,
                        reason=f"measurement outcome {token}",
                    )
                )


def _source_carrier(value_id: str) -> str:
    return f"carrier:source:{value_id}"


def _ancilla_carrier(primitive: LogicalPrimitive, role: AncillaRole) -> str:
    return f"carrier:compiler:{primitive.primitive_id}:{role.value}"


def _token(primitive: LogicalPrimitive, suffix: str) -> str:
    return f"bit:{primitive.primitive_id}:{suffix}"


def _pauli(axis: str, carrier: str) -> str:
    return f"{axis}:{carrier}"


def _prepare(
    builder: _GadgetBuilder,
    suffix: str,
    carrier: str,
    logical_support: tuple[str, ...],
    choices: tuple[PreparedStateChoice, ...],
    *,
    resource_state_demand: int = 0,
    note: str,
) -> PbcOperation:
    operation = PbcOperation(
        operation_id=builder.operation_id(suffix),
        source_primitive_id=builder.primitive.primitive_id,
        kind=PbcOperationKind.PREPARE,
        logical_support=logical_support,
        carrier_support=(carrier,),
        classical_inputs=tuple(
            dict.fromkeys(
                literal.token
                for choice in choices
                for literal in choice.condition
            )
        ),
        prepared_states=choices,
        resource_state_demand=resource_state_demand,
        semantic_evidence_status=EvidenceStatus.LITERATURE,
        note=note,
    )
    builder.add(operation)
    builder.add_direct_classical_dependencies(operation)
    return operation


def _measure(
    builder: _GadgetBuilder,
    suffix: str,
    logical_support: tuple[str, ...],
    carriers: tuple[str, ...],
    pauli_terms: tuple[str, ...],
    result: str,
    *,
    note: str,
) -> PbcOperation:
    operation = PbcOperation(
        operation_id=builder.operation_id(suffix),
        source_primitive_id=builder.primitive.primitive_id,
        kind=PbcOperationKind.MEASURE_PAULI,
        logical_support=logical_support,
        carrier_support=carriers,
        pauli_terms=pauli_terms,
        classical_outputs=(result,),
        semantic_evidence_status=EvidenceStatus.LITERATURE,
        note=note,
    )
    builder.add(operation)
    return operation


def _frame(
    builder: _GadgetBuilder,
    suffix: str,
    logical_support: tuple[str, ...],
    carriers: tuple[str, ...],
    updates: tuple[FrameUpdate, ...],
    *,
    note: str,
) -> PbcOperation:
    inputs = tuple(
        dict.fromkeys(
            token
            for update in updates
            for token in (
                *update.parity_tokens,
                *(literal.token for literal in update.condition),
            )
        )
    )
    operation = PbcOperation(
        operation_id=builder.operation_id(suffix),
        source_primitive_id=builder.primitive.primitive_id,
        kind=PbcOperationKind.PAULI_FRAME_UPDATE,
        logical_support=logical_support,
        carrier_support=carriers,
        classical_inputs=inputs,
        frame_updates=updates,
        semantic_evidence_status=EvidenceStatus.LITERATURE,
        note=note,
    )
    builder.add(operation)
    builder.add_direct_classical_dependencies(operation)
    return operation


def _release(
    builder: _GadgetBuilder,
    suffix: str,
    carrier: str,
    logical_support: tuple[str, ...],
    *,
    note: str,
) -> PbcOperation:
    operation = PbcOperation(
        operation_id=builder.operation_id(suffix),
        source_primitive_id=builder.primitive.primitive_id,
        kind=PbcOperationKind.RELEASE,
        logical_support=logical_support,
        carrier_support=(carrier,),
        semantic_evidence_status=EvidenceStatus.LITERATURE,
        note=note,
    )
    builder.add(operation)
    return operation


def _rebind(
    builder: _GadgetBuilder,
    value: str,
    old_carrier: str,
    new_carrier: str,
) -> PbcOperation:
    operation = PbcOperation(
        operation_id=builder.operation_id("rebind_output"),
        source_primitive_id=builder.primitive.primitive_id,
        kind=PbcOperationKind.REBIND_LOGICAL_VALUE,
        logical_support=(value,),
        carrier_support=(old_carrier, new_carrier),
        semantic_evidence_status=EvidenceStatus.PROVED,
        note="Compiler bookkeeping: the teleported output now carries the source value",
    )
    builder.add(operation)
    return operation


def _lower_cnot(
    primitive: LogicalPrimitive,
    carriers: dict[str, str],
) -> tuple[_GadgetBuilder, dict[str, str]]:
    if len(primitive.logical_support) != 2:
        raise ValueError("CNOT requires a control and target")
    control, target = primitive.logical_support
    control_carrier = carriers[control]
    target_carrier = carriers[target]
    scratch = _ancilla_carrier(primitive, AncillaRole.CNOT_SCRATCH)
    a = _token(primitive, "zz")
    b = _token(primitive, "xx")
    c = _token(primitive, "z_scratch")
    builder = _GadgetBuilder(primitive, [], [], [])
    allocation = _prepare(
        builder,
        "prepare_plus",
        scratch,
        primitive.logical_support,
        (PreparedStateChoice("plus"),),
        note="Xu et al. Figure 11(c) CNOT scratch |+>",
    )
    _measure(
        builder,
        "measure_zz_control_scratch",
        primitive.logical_support,
        (control_carrier, scratch),
        (_pauli("Z", control_carrier), _pauli("Z", scratch)),
        a,
        note="First Bell measurement of Xu et al. Figure 11(c)",
    )
    _measure(
        builder,
        "measure_xx_scratch_target",
        primitive.logical_support,
        (scratch, target_carrier),
        (_pauli("X", scratch), _pauli("X", target_carrier)),
        b,
        note="Second Bell measurement of Xu et al. Figure 11(c)",
    )
    _measure(
        builder,
        "measure_z_scratch",
        primitive.logical_support,
        (scratch,),
        (_pauli("Z", scratch),),
        c,
        note="Destructive scratch measurement of Xu et al. Figure 11(c)",
    )
    _frame(
        builder,
        "pauli_corrections",
        primitive.logical_support,
        (control_carrier, target_carrier),
        (
            FrameUpdate(control_carrier, "Z", (b,)),
            FrameUpdate(target_carrier, "X", (a, c)),
        ),
        note="Apply Z_control^b X_target^(a xor c) in the Pauli frame",
    )
    release = _release(
        builder,
        "release_scratch",
        scratch,
        primitive.logical_support,
        note="Release the measured CNOT scratch carrier",
    )
    builder.ancillas.append(
        CompilerAncillaLifetime(
            carrier_id=scratch,
            role=AncillaRole.CNOT_SCRATCH,
            source_primitive_id=primitive.primitive_id,
            allocation_operation_id=allocation.operation_id,
            release_operation_id=release.operation_id,
        )
    )
    return builder, carriers


def _teleport_clifford(
    primitive: LogicalPrimitive,
    carriers: dict[str, str],
    *,
    gate: str,
) -> tuple[_GadgetBuilder, dict[str, str]]:
    if len(primitive.logical_support) != 1:
        raise ValueError("a single-qubit Clifford requires one logical value")
    value = primitive.logical_support[0]
    old_carrier = carriers[value]
    output = _ancilla_carrier(primitive, AncillaRole.TELEPORT_OUTPUT)
    parity = _token(primitive, "teleport_parity")
    x_result = _token(primitive, "teleport_x")
    if gate == "H":
        state = "zero"
        second_axis = "X"
        updates = (
            FrameUpdate(output, "Z", (parity,)),
            FrameUpdate(output, "X", (x_result,)),
        )
    elif gate == "S":
        state = "i_plus"
        second_axis = "Z"
        updates = (
            FrameUpdate(output, "Y", (parity,)),
            FrameUpdate(output, "Z", (x_result,)),
        )
    else:
        raise ValueError(f"unsupported teleported Clifford {gate!r}")
    builder = _GadgetBuilder(primitive, [], [], [])
    allocation = _prepare(
        builder,
        f"prepare_{state}",
        output,
        (value,),
        (PreparedStateChoice(state),),
        note=f"Prepare {gate}|+> for one-bit Clifford teleportation",
    )
    _measure(
        builder,
        "measure_teleport_parity",
        (value,),
        (old_carrier, output),
        (_pauli("Z", old_carrier), _pauli(second_axis, output)),
        parity,
        note=f"Measure Z tensor ({gate} Z {gate}^dagger) for Clifford teleportation",
    )
    _measure(
        builder,
        "measure_x_old_carrier",
        (value,),
        (old_carrier,),
        (_pauli("X", old_carrier),),
        x_result,
        note="Complete one-bit teleportation by measuring the input in X",
    )
    _frame(
        builder,
        "pauli_corrections",
        (value,),
        (output,),
        updates,
        note=f"Conjugated Pauli corrections for teleported {gate}",
    )
    rebind = _rebind(builder, value, old_carrier, output)
    builder.ancillas.append(
        CompilerAncillaLifetime(
            carrier_id=output,
            role=AncillaRole.TELEPORT_OUTPUT,
            source_primitive_id=primitive.primitive_id,
            allocation_operation_id=allocation.operation_id,
            release_operation_id=rebind.operation_id,
        )
    )
    updated = dict(carriers)
    updated[value] = output
    return builder, updated


def _lower_t_gate(
    primitive: LogicalPrimitive,
    carriers: dict[str, str],
) -> tuple[_GadgetBuilder, dict[str, str]]:
    if len(primitive.logical_support) != 1:
        raise ValueError("T teleportation requires one logical value")
    value = primitive.logical_support[0]
    old_carrier = carriers[value]
    magic = _ancilla_carrier(primitive, AncillaRole.MAGIC_T)
    output = _ancilla_carrier(primitive, AncillaRole.TELEPORT_OUTPUT)
    r = _token(primitive, "magic_zz")
    b = _token(primitive, "magic_x")
    c = _token(primitive, "correction_teleport_zz")
    d = _token(primitive, "correction_teleport_x")
    dagger = primitive.kind is LogicalPrimitiveKind.T_DAGGER
    builder = _GadgetBuilder(primitive, [], [], [])
    magic_allocation = _prepare(
        builder,
        "prepare_magic_t",
        magic,
        (value,),
        (PreparedStateChoice("magic_t"),),
        resource_state_demand=primitive.resource_state_demand,
        note="Bravyi-Smith-Smolin Figure 4 |T> injection ancilla",
    )
    _measure(
        builder,
        "measure_magic_zz",
        (value,),
        (old_carrier, magic),
        (_pauli("Z", old_carrier), _pauli("Z", magic)),
        r,
        note="First measurement of the Bravyi-Smith-Smolin T gadget",
    )
    _measure(
        builder,
        "measure_magic_x",
        (value,),
        (magic,),
        (_pauli("X", magic),),
        b,
        note="Second measurement of the Bravyi-Smith-Smolin T gadget",
    )
    magic_release = _release(
        builder,
        "release_magic",
        magic,
        (value,),
        note="Release the measured magic-state carrier before allocating correction output",
    )
    if dagger:
        choices = (
            PreparedStateChoice("minus_i", (ClassicalLiteral(r, 0),)),
            PreparedStateChoice("plus", (ClassicalLiteral(r, 1),)),
        )
        axis_updates = (
            FrameUpdate(output, "Y", (c,), (ClassicalLiteral(r, 0),)),
            FrameUpdate(output, "X", (c,), (ClassicalLiteral(r, 1),)),
        )
        branch_note = "Teleport S^dagger for r=0 and identity for r=1"
    else:
        choices = (
            PreparedStateChoice("plus", (ClassicalLiteral(r, 0),)),
            PreparedStateChoice("i_plus", (ClassicalLiteral(r, 1),)),
        )
        axis_updates = (
            FrameUpdate(output, "X", (c,), (ClassicalLiteral(r, 0),)),
            FrameUpdate(output, "Y", (c,), (ClassicalLiteral(r, 1),)),
        )
        branch_note = "Teleport identity for r=0 and S for r=1"
    output_allocation = _prepare(
        builder,
        "prepare_adaptive_correction_output",
        output,
        (value,),
        choices,
        note=branch_note,
    )
    _measure(
        builder,
        "measure_correction_teleport_zz",
        (value,),
        (old_carrier, output),
        (_pauli("Z", old_carrier), _pauli("Z", output)),
        c,
        note="Parity measurement for the adaptive I/S correction teleport",
    )
    _measure(
        builder,
        "measure_correction_teleport_x",
        (value,),
        (old_carrier,),
        (_pauli("X", old_carrier),),
        d,
        note="Complete the adaptive correction teleport",
    )
    _frame(
        builder,
        "pauli_corrections",
        (value,),
        (output,),
        (
            *axis_updates,
            FrameUpdate(output, "Z", (b, d)),
        ),
        note="Pauli-only correction after physical removal of the adaptive S frame",
    )
    rebind = _rebind(builder, value, old_carrier, output)
    builder.ancillas.extend(
        (
            CompilerAncillaLifetime(
                carrier_id=magic,
                role=AncillaRole.MAGIC_T,
                source_primitive_id=primitive.primitive_id,
                allocation_operation_id=magic_allocation.operation_id,
                release_operation_id=magic_release.operation_id,
            ),
            CompilerAncillaLifetime(
                carrier_id=output,
                role=AncillaRole.TELEPORT_OUTPUT,
                source_primitive_id=primitive.primitive_id,
                allocation_operation_id=output_allocation.operation_id,
                release_operation_id=rebind.operation_id,
            ),
        )
    )
    updated = dict(carriers)
    updated[value] = output
    return builder, updated


def _lower_passthrough(
    primitive: LogicalPrimitive,
    carriers: dict[str, str],
) -> tuple[_GadgetBuilder, dict[str, str]]:
    support = tuple(carriers[value] for value in primitive.logical_support)
    builder = _GadgetBuilder(primitive, [], [], [])
    if primitive.kind is LogicalPrimitiveKind.PREPARE_T:
        operation = PbcOperation(
            operation_id=builder.operation_id("prepare_source_magic_t"),
            source_primitive_id=primitive.primitive_id,
            kind=PbcOperationKind.PREPARE,
            logical_support=primitive.logical_support,
            carrier_support=support,
            prepared_states=(PreparedStateChoice("magic_t"),),
            resource_state_demand=primitive.resource_state_demand,
            semantic_evidence_status=EvidenceStatus.LITERATURE,
            note="Source temporary is initialized directly in |T>",
        )
    elif primitive.kind is LogicalPrimitiveKind.MEASURE_X:
        output = primitive.classical_outputs[0]
        operation = PbcOperation(
            operation_id=builder.operation_id("measure_source_x"),
            source_primitive_id=primitive.primitive_id,
            kind=PbcOperationKind.MEASURE_PAULI,
            logical_support=primitive.logical_support,
            carrier_support=support,
            pauli_terms=tuple(_pauli("X", carrier) for carrier in support),
            classical_outputs=(output,),
            semantic_evidence_status=EvidenceStatus.LITERATURE,
            note="Source destructive X-basis measurement",
        )
    elif primitive.kind is LogicalPrimitiveKind.CONDITIONAL_CZ_FRAME:
        operation = PbcOperation(
            operation_id=builder.operation_id("conditional_cz_frame"),
            source_primitive_id=primitive.primitive_id,
            kind=PbcOperationKind.CONDITIONAL_CLIFFORD_FRAME,
            logical_support=primitive.logical_support,
            carrier_support=support,
            classical_inputs=primitive.classical_inputs,
            semantic_evidence_status=EvidenceStatus.LITERATURE,
            note="Exact source CZ frame dependency; no native runtime is asserted",
        )
    elif primitive.kind is LogicalPrimitiveKind.RELEASE:
        operation = PbcOperation(
            operation_id=builder.operation_id("release_source_value"),
            source_primitive_id=primitive.primitive_id,
            kind=PbcOperationKind.RELEASE,
            logical_support=primitive.logical_support,
            carrier_support=support,
            semantic_evidence_status=EvidenceStatus.PROVED,
            note="Release a source logical value after its destructive measurement",
        )
    else:
        raise ValueError(f"unsupported passthrough primitive {primitive.kind.value}")
    builder.add(operation)
    return builder, carriers


def _lower_primitive(
    primitive: LogicalPrimitive,
    carriers: dict[str, str],
) -> tuple[_GadgetBuilder, dict[str, str]]:
    for value in primitive.logical_support:
        carriers.setdefault(value, _source_carrier(value))
    if primitive.kind is LogicalPrimitiveKind.CNOT:
        return _lower_cnot(primitive, carriers)
    if primitive.kind in {LogicalPrimitiveKind.T, LogicalPrimitiveKind.T_DAGGER}:
        return _lower_t_gate(primitive, carriers)
    if primitive.kind is LogicalPrimitiveKind.H:
        return _teleport_clifford(primitive, carriers, gate="H")
    if primitive.kind is LogicalPrimitiveKind.S:
        return _teleport_clifford(primitive, carriers, gate="S")
    return _lower_passthrough(primitive, carriers)


def lower_to_adaptive_pauli_measurements(trace: LogicalTrace) -> PbcTrace:
    """Lower a phase-exact Gidney trace while preserving its quantum output.

    CNOT uses the three-measurement circuit in Xu et al. Figure 11(c).  T and
    T-dagger use the Bravyi-Smith-Smolin Figure 4 injection followed by an
    adaptive one-bit Clifford teleport, so the residual correction is Pauli
    rather than an unpropagated S frame.  H and S use the same one-bit
    Clifford-teleportation identity.  One compiler carrier can be reused when
    gadgets share a serialized operation zone.
    """

    if not trace.source_circuit_id.startswith("gidney-ripple-adder-width-"):
        raise ValueError("adaptive PBC lowering received a different circuit")
    primitive_by_id = {
        primitive.primitive_id: primitive for primitive in trace.primitives
    }
    operations: list[PbcOperation] = []
    dependencies: list[PbcDependency] = []
    ancillas: list[CompilerAncillaLifetime] = []
    boundaries: dict[str, tuple[str, str]] = {}
    carriers: dict[str, str] = {}
    for primitive_id in trace.topological_order():
        primitive = primitive_by_id[primitive_id]
        builder, carriers = _lower_primitive(primitive, carriers)
        operations.extend(builder.operations)
        dependencies.extend(builder.dependencies)
        ancillas.extend(builder.ancillas)
        boundaries[primitive_id] = (
            builder.operations[0].operation_id,
            builder.operations[-1].operation_id,
        )
    existing_edges = {
        (dependency.predecessor, dependency.successor)
        for dependency in dependencies
    }
    for source_dependency in trace.dependencies:
        predecessor = boundaries[source_dependency.predecessor][1]
        successor = boundaries[source_dependency.successor][0]
        if (predecessor, successor) not in existing_edges:
            dependencies.append(
                PbcDependency(
                    predecessor=predecessor,
                    successor=successor,
                    kind=PbcDependencyKind.SOURCE_TRACE,
                    reason=(
                        f"{source_dependency.kind.value}:"
                        f"{source_dependency.source_reason}"
                    ),
                )
            )
            existing_edges.add((predecessor, successor))
    produced_tokens = {
        token: operation.operation_id
        for operation in operations
        for token in operation.classical_outputs
    }
    for operation in operations:
        for token in operation.classical_inputs:
            producer = produced_tokens.get(token)
            if producer is None:
                continue
            if (producer, operation.operation_id) not in existing_edges:
                dependencies.append(
                    PbcDependency(
                        predecessor=producer,
                        successor=operation.operation_id,
                        kind=PbcDependencyKind.CLASSICAL_FEED_FORWARD,
                        reason=f"source measurement outcome {token}",
                    )
                )
                existing_edges.add((producer, operation.operation_id))
    return PbcTrace(
        trace_id=f"{trace.trace_id}:adaptive-pbc-v1",
        source_trace_id=trace.trace_id,
        source_evidence_status=trace.source_evidence_status,
        peak_source_processor_occupancy=trace.peak_source_processor_occupancy,
        minimum_reusable_compiler_scratch_slots=(1 if ancillas else 0),
        operations=tuple(operations),
        dependencies=tuple(dependencies),
        compiler_ancillas=tuple(ancillas),
        final_carriers=tuple(sorted(carriers.items())),
    )


def pbc_trace_to_data(trace: PbcTrace) -> dict[str, Any]:
    """Convert a PBC trace to a deterministic JSON-compatible object."""

    def literal_data(literal: ClassicalLiteral) -> dict[str, Any]:
        return {"token": literal.token, "value": literal.value}

    return {
        "compiler_ancillas": [
            {
                "allocation_operation_id": lifetime.allocation_operation_id,
                "carrier_id": lifetime.carrier_id,
                "release_operation_id": lifetime.release_operation_id,
                "role": lifetime.role.value,
                "source_primitive_id": lifetime.source_primitive_id,
            }
            for lifetime in trace.compiler_ancillas
        ],
        "dependencies": [
            {
                "kind": dependency.kind.value,
                "predecessor": dependency.predecessor,
                "reason": dependency.reason,
                "successor": dependency.successor,
            }
            for dependency in trace.dependencies
        ],
        "final_carriers": dict(trace.final_carriers),
        "measurement_count": trace.measurement_count,
        "minimum_reusable_compiler_scratch_slots": (
            trace.minimum_reusable_compiler_scratch_slots
        ),
        "minimum_serial_processor_occupancy": trace.minimum_serial_processor_occupancy,
        "operations": [
            {
                "carrier_support": list(operation.carrier_support),
                "classical_inputs": list(operation.classical_inputs),
                "classical_outputs": list(operation.classical_outputs),
                "frame_updates": [
                    {
                        "carrier_id": update.carrier_id,
                        "condition": [literal_data(value) for value in update.condition],
                        "parity_tokens": list(update.parity_tokens),
                        "pauli": update.pauli,
                    }
                    for update in operation.frame_updates
                ],
                "kind": operation.kind.value,
                "logical_support": list(operation.logical_support),
                "note": operation.note,
                "operation_id": operation.operation_id,
                "pauli_terms": list(operation.pauli_terms),
                "prepared_states": [
                    {
                        "condition": [literal_data(value) for value in choice.condition],
                        "state": choice.state,
                    }
                    for choice in operation.prepared_states
                ],
                "resource_state_demand": operation.resource_state_demand,
                "runtime_evidence_status": operation.runtime_evidence_status.value,
                "semantic_evidence_status": operation.semantic_evidence_status.value,
                "source_primitive_id": operation.source_primitive_id,
            }
            for operation in trace.operations
        ],
        "peak_source_processor_occupancy": trace.peak_source_processor_occupancy,
        "resource_state_demand": trace.resource_state_demand,
        "schema": trace.schema,
        "schema_version": trace.schema_version,
        "source_evidence_status": trace.source_evidence_status.value,
        "source_trace_id": trace.source_trace_id,
        "trace_id": trace.trace_id,
    }


def dumps_pbc_trace(trace: PbcTrace) -> str:
    """Serialize a PBC trace canonically."""

    return json.dumps(pbc_trace_to_data(trace), indent=2, sort_keys=True) + "\n"
