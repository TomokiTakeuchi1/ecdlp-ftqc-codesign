"""Source-pinned reversible DAG for Draper et al.'s in-place QCLA.

The admitted variant implements ``(A, B) -> (A, A + B mod 2**n)`` with no
incoming carry and no exported overflow bit.  Records in this module are
architecture neutral: an algorithmic layer is a source circuit time slice,
not a QEC cycle, surgery round, or wall-clock duration.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ecdlp_ftqc.metadata import EvidenceStatus

QCLA_SCHEMA = "ecdlp-ftqc/qcla-inplace-mod2n-trace"
QCLA_SCHEMA_VERSION = 1
QCLA_SOURCE_ID = "quant-ph/0406142v1"
QCLA_SOURCE_PDF_SHA256 = (
    "30B68CC62C73E5AA6E4D59A6C3CF3C582FB62420F8BDE420DE142506A2BB11D6"
)


class QclaTraceError(ValueError):
    """Raised when a QCLA trace or replay violates its contract."""


class QclaGateKind(str, Enum):
    """Reversible classical gate kinds used by the source circuit."""

    X = "x"
    CNOT = "cnot"
    TOFFOLI = "toffoli"


class QclaDirection(str, Enum):
    """Whether a gate belongs to the forward or reverse carry circuit."""

    NONE = "none"
    FORWARD = "forward"
    REVERSE = "reverse"


class QclaStage(str, Enum):
    """Source step or carry-round role for a gate."""

    INITIAL_GENERATE = "initial_generate"
    INITIAL_PROPAGATE = "initial_propagate"
    PREFIX_PROPAGATE = "prefix_propagate"
    PREFIX_GENERATE = "prefix_generate"
    PREFIX_CARRY = "prefix_carry"
    PREFIX_UNCOMPUTE = "prefix_uncompute"
    SUM_CARRY_WRITE = "sum_carry_write"
    COMPLEMENT_PREPARE = "complement_prepare"
    REVERSE_PROPAGATE_PREPARE = "reverse_propagate_prepare"
    FINAL_PROPAGATE_RESTORE = "final_propagate_restore"
    INITIAL_GENERATE_UNCOMPUTE = "initial_generate_uncompute"
    OUTPUT_COMPLEMENT_RESTORE = "output_complement_restore"


@dataclass(frozen=True, slots=True)
class QclaSourceReference:
    """Pinned source and exact circuit sections used by this frontend."""

    source_id: str = QCLA_SOURCE_ID
    pdf_sha256: str = QCLA_SOURCE_PDF_SHA256
    title: str = "A logarithmic-depth quantum carry-lookahead adder"
    sections: tuple[str, ...] = ("3", "4.2", "5.1")
    figures: tuple[str, ...] = ("Figure 4", "Figure 5")
    tables: tuple[str, ...] = ("Table 1", "Table 2")
    semantic_evidence_status: EvidenceStatus = EvidenceStatus.LITERATURE

    def __post_init__(self) -> None:
        digest = self.pdf_sha256
        if len(digest) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in digest
        ):
            raise QclaTraceError("source PDF hash must be SHA-256")


@dataclass(frozen=True, slots=True)
class QclaGate:
    """One reversible gate with source-round and prefix metadata."""

    gate_id: str
    kind: QclaGateKind
    controls: tuple[str, ...]
    target: str
    algorithmic_layer: int
    source_step: int
    stage: QclaStage
    direction: QclaDirection = QclaDirection.NONE
    round_index: int | None = None
    prefix_interval: tuple[int, int, int] | None = None
    semantic_evidence_status: EvidenceStatus = EvidenceStatus.LITERATURE

    def __post_init__(self) -> None:
        if not self.gate_id:
            raise QclaTraceError("gate ID cannot be empty")
        if self.algorithmic_layer < 1:
            raise QclaTraceError("algorithmic layer must be positive")
        if not 1 <= self.source_step <= 10:
            raise QclaTraceError("source step must be in 1..10")
        expected_controls = {
            QclaGateKind.X: 0,
            QclaGateKind.CNOT: 1,
            QclaGateKind.TOFFOLI: 2,
        }[self.kind]
        if len(self.controls) != expected_controls:
            raise QclaTraceError("gate kind has the wrong number of controls")
        if len(self.controls) != len(set(self.controls)):
            raise QclaTraceError("gate controls cannot contain duplicates")
        if self.target in self.controls:
            raise QclaTraceError("gate target cannot also be a control")
        if self.round_index is not None and self.round_index < 1:
            raise QclaTraceError("round index must be positive")
        if self.prefix_interval is not None:
            left, middle, right = self.prefix_interval
            if not 0 <= left < middle < right:
                raise QclaTraceError("prefix interval must satisfy 0 <= i < k < j")

    @property
    def logical_support(self) -> tuple[str, ...]:
        return (*self.controls, self.target)

    @property
    def read_values(self) -> tuple[str, ...]:
        return self.logical_support

    @property
    def write_values(self) -> tuple[str, ...]:
        return (self.target,)


@dataclass(frozen=True, slots=True)
class QclaDependency:
    """Nearest prior use of one or more logical wires."""

    predecessor: str
    successor: str
    values: tuple[str, ...]
    reason: str = "wire_order"

    def __post_init__(self) -> None:
        if not self.predecessor or not self.successor:
            raise QclaTraceError("dependency endpoints cannot be empty")
        if self.predecessor == self.successor:
            raise QclaTraceError("self dependencies are not allowed")
        if not self.values or len(self.values) != len(set(self.values)):
            raise QclaTraceError("dependency values must be nonempty and unique")
        if self.reason != "wire_order":
            raise QclaTraceError("unsupported QCLA dependency reason")


@dataclass(frozen=True, slots=True)
class QclaAncillaInterval:
    """One allocation interval; scratch prefix ancillas have two reuse epochs."""

    value_id: str
    family: str
    reuse_epoch: int
    start_layer: int
    end_layer: int

    def __post_init__(self) -> None:
        if self.family not in {"carry", "prefix_scratch"}:
            raise QclaTraceError("unsupported QCLA ancilla family")
        if self.reuse_epoch < 1:
            raise QclaTraceError("reuse epoch must be positive")
        if not 1 <= self.start_layer <= self.end_layer:
            raise QclaTraceError("invalid ancilla interval")


@dataclass(frozen=True, slots=True)
class QclaReplaySummary:
    """Independent computational-basis replay result."""

    width: int
    input_a: int
    input_b: int
    output_a: int
    output_b: int
    expected_b: int
    final_nonzero_ancillas: tuple[str, ...]
    passed: bool


@dataclass(frozen=True, slots=True)
class QclaMetrics:
    """Architecture-neutral trace metrics."""

    gate_count: int
    x_count: int
    cnot_count: int
    toffoli_count: int
    source_layer_count: int
    dependency_critical_path_gates: int
    source_ancilla_count: int
    prefix_scratch_count: int
    peak_live_ancillas: int
    peak_toffoli_per_layer: int
    toffoli_demand_by_layer: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class QclaTrace:
    """Validated architecture-neutral in-place modulo-QCLA trace."""

    trace_id: str
    width: int
    source: QclaSourceReference
    gates: tuple[QclaGate, ...]
    dependencies: tuple[QclaDependency, ...]
    ancilla_intervals: tuple[QclaAncillaInterval, ...]
    arithmetic_contract: str = "(A,B)->(A,A+B mod 2^n)"
    incoming_carry: bool = False
    exported_overflow: bool = False
    schema: str = QCLA_SCHEMA
    schema_version: int = QCLA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise QclaTraceError("trace ID cannot be empty")
        if self.width < 2:
            raise QclaTraceError("QCLA width must be at least two")
        if self.schema != QCLA_SCHEMA or self.schema_version != QCLA_SCHEMA_VERSION:
            raise QclaTraceError("unsupported QCLA schema")
        if self.incoming_carry or self.exported_overflow:
            raise QclaTraceError("this schema admits neither carry-in nor overflow")
        if self.arithmetic_contract != "(A,B)->(A,A+B mod 2^n)":
            raise QclaTraceError("unsupported arithmetic contract")
        self._validate()

    @property
    def carry_length(self) -> int:
        return self.width - 1

    @property
    def source_ancilla_count(self) -> int:
        length = self.carry_length
        return 2 * self.width - 2 - length.bit_count() - _floor_log2(length)

    @property
    def expected_toffoli_count(self) -> int:
        length = self.carry_length
        return (
            10 * self.width
            - 6 * length.bit_count()
            - 6 * _floor_log2(length)
            - 12
        )

    @property
    def expected_cnot_count(self) -> int:
        return 4 * self.width - 5

    @property
    def expected_x_count(self) -> int:
        return 2 * self.width - 2

    @property
    def expected_source_layer_count(self) -> int | None:
        """Paper formula, restricted to its stated normal-size regime n >= 5."""

        if self.width < 5:
            return None
        length = self.carry_length
        return (
            2 * _floor_log2(length)
            + 2 * _floor_log2_fraction(length, 3)
            + 14
        )

    def gate_by_id(self) -> dict[str, QclaGate]:
        return {gate.gate_id: gate for gate in self.gates}

    def topological_order(self) -> tuple[str, ...]:
        gate_ids = tuple(gate.gate_id for gate in self.gates)
        position = {gate_id: index for index, gate_id in enumerate(gate_ids)}
        successors: dict[str, list[str]] = defaultdict(list)
        indegree = {gate_id: 0 for gate_id in gate_ids}
        for dependency in self.dependencies:
            successors[dependency.predecessor].append(dependency.successor)
            indegree[dependency.successor] += 1
        queue = deque(gate_id for gate_id in gate_ids if indegree[gate_id] == 0)
        order: list[str] = []
        while queue:
            gate_id = queue.popleft()
            order.append(gate_id)
            for successor in sorted(successors[gate_id], key=position.__getitem__):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    queue.append(successor)
        if len(order) != len(gate_ids):
            raise QclaTraceError("QCLA trace must be acyclic")
        return tuple(order)

    def _validate(self) -> None:
        if self.source != QclaSourceReference():
            raise QclaTraceError("QCLA trace must use the exact pinned source")
        gate_ids = tuple(gate.gate_id for gate in self.gates)
        if len(gate_ids) != len(set(gate_ids)):
            raise QclaTraceError("gate IDs must be unique")
        positions = {gate_id: index for index, gate_id in enumerate(gate_ids)}
        expected_order = sorted(
            self.gates,
            key=lambda gate: (gate.algorithmic_layer, positions[gate.gate_id]),
        )
        if list(self.gates) != expected_order:
            raise QclaTraceError("gates must be ordered by algorithmic layer")
        by_layer: dict[int, set[str]] = defaultdict(set)
        length = self.carry_length
        allowed_values = {
            *(_a(index) for index in range(self.width)),
            *(_b(index) for index in range(self.width)),
            *(_z(index) for index in range(1, self.width)),
            *(
                _p(round_index, node_index)
                for round_index in range(1, _floor_log2(length))
                for node_index in range(1, length // (1 << round_index))
            ),
        }
        carry_stages = {
            QclaStage.PREFIX_PROPAGATE,
            QclaStage.PREFIX_GENERATE,
            QclaStage.PREFIX_CARRY,
            QclaStage.PREFIX_UNCOMPUTE,
        }
        step_stages = {
            1: QclaStage.INITIAL_GENERATE,
            2: QclaStage.INITIAL_PROPAGATE,
            4: QclaStage.SUM_CARRY_WRITE,
            5: QclaStage.COMPLEMENT_PREPARE,
            6: QclaStage.REVERSE_PROPAGATE_PREPARE,
            8: QclaStage.FINAL_PROPAGATE_RESTORE,
            9: QclaStage.INITIAL_GENERATE_UNCOMPUTE,
            10: QclaStage.OUTPUT_COMPLEMENT_RESTORE,
        }
        for gate in self.gates:
            if not set(gate.logical_support) <= allowed_values:
                raise QclaTraceError("gate support contains an unknown logical value")
            if gate.source_step in {3, 7}:
                expected_direction = (
                    QclaDirection.FORWARD
                    if gate.source_step == 3
                    else QclaDirection.REVERSE
                )
                if (
                    gate.stage not in carry_stages
                    or gate.direction is not expected_direction
                    or gate.round_index is None
                    or gate.prefix_interval is None
                ):
                    raise QclaTraceError("carry gate has inconsistent source metadata")
            elif (
                step_stages.get(gate.source_step) is not gate.stage
                or gate.direction is not QclaDirection.NONE
                or gate.round_index is not None
                or gate.prefix_interval is not None
            ):
                raise QclaTraceError("non-carry gate has inconsistent source metadata")
            support = set(gate.logical_support)
            if by_layer[gate.algorithmic_layer] & support:
                raise QclaTraceError("gates in one algorithmic layer must be disjoint")
            by_layer[gate.algorithmic_layer].update(support)
        known = set(gate_ids)
        for dependency in self.dependencies:
            if dependency.predecessor not in known or dependency.successor not in known:
                raise QclaTraceError("dependency references an unknown gate")
        if self.dependencies != _derive_dependencies(self.gates):
            raise QclaTraceError("dependencies must be exact nearest-wire dependencies")
        self.topological_order()
        count_by_kind = _count_gate_kinds(self.gates)
        if count_by_kind[QclaGateKind.TOFFOLI] != self.expected_toffoli_count:
            raise QclaTraceError("Toffoli count disagrees with the source formula")
        if count_by_kind[QclaGateKind.CNOT] != self.expected_cnot_count:
            raise QclaTraceError("CNOT count disagrees with the source formula")
        if count_by_kind[QclaGateKind.X] != self.expected_x_count:
            raise QclaTraceError("X count disagrees with the source formula")
        expected_layers = self.expected_source_layer_count
        if expected_layers is not None and max(by_layer) != expected_layers:
            raise QclaTraceError("source layer count disagrees with the source formula")
        _validate_ancilla_intervals(self)


@dataclass(frozen=True, slots=True)
class _GateSpec:
    kind: QclaGateKind
    controls: tuple[str, ...]
    target: str
    local_layer: int
    stage: QclaStage
    round_index: int | None
    prefix_interval: tuple[int, int, int] | None


def _floor_log2(value: int) -> int:
    if value < 1:
        raise QclaTraceError("logarithm input must be positive")
    return value.bit_length() - 1


def _floor_log2_fraction(numerator: int, denominator: int) -> int:
    if numerator < denominator:
        return -1
    return _floor_log2(numerator // denominator)


def _a(index: int) -> str:
    return f"a:{index}"


def _b(index: int) -> str:
    return f"b:{index}"


def _z(index: int) -> str:
    return f"z:{index}"


def _p(round_index: int, node_index: int) -> str:
    if round_index == 0:
        return _b(node_index)
    return f"p:{round_index}:{node_index}"


def _carry_specs(length: int) -> tuple[tuple[_GateSpec, ...], int]:
    """Build Section 3's carry circuit with its permitted layer overlaps."""

    if length < 1:
        raise QclaTraceError("carry length must be positive")
    if length == 1:
        return (), 0
    log_length = _floor_log2(length)
    propagate_max = log_length - 1
    carry_max = _floor_log2((2 * length) // 3)
    specs: list[_GateSpec] = []

    for round_index in range(1, propagate_max + 1):
        for node_index in range(1, length // (1 << round_index)):
            left = (1 << round_index) * node_index
            middle = left + (1 << (round_index - 1))
            right = left + (1 << round_index)
            specs.append(
                _GateSpec(
                    kind=QclaGateKind.TOFFOLI,
                    controls=(
                        _p(round_index - 1, 2 * node_index),
                        _p(round_index - 1, 2 * node_index + 1),
                    ),
                    target=_p(round_index, node_index),
                    local_layer=round_index,
                    stage=QclaStage.PREFIX_PROPAGATE,
                    round_index=round_index,
                    prefix_interval=(left, middle, right),
                )
            )

    generate_offset = 1 if propagate_max >= 1 else 0
    for round_index in range(1, log_length + 1):
        for node_index in range(length // (1 << round_index)):
            left = (1 << round_index) * node_index
            middle = left + (1 << (round_index - 1))
            right = left + (1 << round_index)
            specs.append(
                _GateSpec(
                    kind=QclaGateKind.TOFFOLI,
                    controls=(
                        _z(middle),
                        _p(round_index - 1, 2 * node_index + 1),
                    ),
                    target=_z(right),
                    local_layer=round_index + generate_offset,
                    stage=QclaStage.PREFIX_GENERATE,
                    round_index=round_index,
                    prefix_interval=(left, middle, right),
                )
            )

    generate_end = log_length + generate_offset
    for round_index in range(carry_max, 0, -1):
        local_layer = generate_end + (carry_max - round_index + 1)
        upper = (length - (1 << (round_index - 1))) // (1 << round_index)
        for node_index in range(1, upper + 1):
            left = (1 << round_index) * node_index
            middle = left + (1 << (round_index - 1))
            right = left + (1 << round_index)
            specs.append(
                _GateSpec(
                    kind=QclaGateKind.TOFFOLI,
                    controls=(
                        _z(left),
                        _p(round_index - 1, 2 * node_index),
                    ),
                    target=_z(middle),
                    local_layer=local_layer,
                    stage=QclaStage.PREFIX_CARRY,
                    round_index=round_index,
                    prefix_interval=(left, middle, right),
                )
            )

    for round_index in range(propagate_max, 0, -1):
        if round_index == 1:
            local_layer = generate_end + carry_max + 1
        else:
            local_layer = generate_end + (carry_max - round_index + 2)
        for node_index in range(1, length // (1 << round_index)):
            left = (1 << round_index) * node_index
            middle = left + (1 << (round_index - 1))
            right = left + (1 << round_index)
            specs.append(
                _GateSpec(
                    kind=QclaGateKind.TOFFOLI,
                    controls=(
                        _p(round_index - 1, 2 * node_index),
                        _p(round_index - 1, 2 * node_index + 1),
                    ),
                    target=_p(round_index, node_index),
                    local_layer=local_layer,
                    stage=QclaStage.PREFIX_UNCOMPUTE,
                    round_index=round_index,
                    prefix_interval=(left, middle, right),
                )
            )

    depth = generate_end + carry_max + (1 if propagate_max >= 1 else 0)
    return tuple(
        sorted(
            specs,
            key=lambda spec: (
                spec.local_layer,
                spec.stage.value,
                spec.round_index or 0,
                spec.target,
            ),
        )
    ), depth


def _derive_dependencies(gates: tuple[QclaGate, ...]) -> tuple[QclaDependency, ...]:
    last_use: dict[str, str] = {}
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for gate in gates:
        for value in gate.logical_support:
            predecessor = last_use.get(value)
            if predecessor is not None:
                grouped[(predecessor, gate.gate_id)].add(value)
            last_use[value] = gate.gate_id
    position = {gate.gate_id: index for index, gate in enumerate(gates)}
    return tuple(
        QclaDependency(
            predecessor=predecessor,
            successor=successor,
            values=tuple(sorted(values)),
        )
        for (predecessor, successor), values in sorted(
            grouped.items(),
            key=lambda item: (
                position[item[0][1]],
                position[item[0][0]],
                item[0],
            ),
        )
    )


def _ancilla_intervals(gates: tuple[QclaGate, ...], width: int) -> tuple[QclaAncillaInterval, ...]:
    target_layers: dict[str, list[int]] = defaultdict(list)
    for gate in gates:
        if gate.target.startswith(("z:", "p:")):
            target_layers[gate.target].append(gate.algorithmic_layer)
    intervals: list[QclaAncillaInterval] = []
    for index in range(1, width):
        value = _z(index)
        layers = target_layers[value]
        intervals.append(
            QclaAncillaInterval(
                value_id=value,
                family="carry",
                reuse_epoch=1,
                start_layer=min(layers),
                end_layer=max(layers),
            )
        )
    for value in sorted(key for key in target_layers if key.startswith("p:")):
        layers = target_layers[value]
        if len(layers) != 4:
            raise QclaTraceError("prefix scratch must have two compute/uncompute epochs")
        intervals.extend(
            (
                QclaAncillaInterval(value, "prefix_scratch", 1, layers[0], layers[1]),
                QclaAncillaInterval(value, "prefix_scratch", 2, layers[2], layers[3]),
            )
        )
    return tuple(intervals)


def _validate_ancilla_intervals(trace: QclaTrace) -> None:
    expected = _ancilla_intervals(trace.gates, trace.width)
    if trace.ancilla_intervals != expected:
        raise QclaTraceError("ancilla intervals do not match gate targets")
    distinct = {interval.value_id for interval in trace.ancilla_intervals}
    if len(distinct) != trace.source_ancilla_count:
        raise QclaTraceError("ancilla count disagrees with the source formula")


def _count_gate_kinds(gates: tuple[QclaGate, ...]) -> dict[QclaGateKind, int]:
    counts = {kind: 0 for kind in QclaGateKind}
    for gate in gates:
        counts[gate.kind] += 1
    return counts


def build_qcla_trace(width: int) -> QclaTrace:
    """Build the selected source-exact in-place modulo-QCLA trace."""

    if width < 2:
        raise QclaTraceError("QCLA width must be at least two")
    raw: list[tuple[int, int, QclaStage, QclaDirection, _GateSpec]] = []

    def append_simple(
        *,
        layer: int,
        source_step: int,
        stage: QclaStage,
        kind: QclaGateKind,
        controls: tuple[str, ...],
        target: str,
    ) -> None:
        raw.append(
            (
                layer,
                source_step,
                stage,
                QclaDirection.NONE,
                _GateSpec(kind, controls, target, 0, stage, None, None),
            )
        )

    for index in range(width - 1):
        append_simple(
            layer=1,
            source_step=1,
            stage=QclaStage.INITIAL_GENERATE,
            kind=QclaGateKind.TOFFOLI,
            controls=(_a(index), _b(index)),
            target=_z(index + 1),
        )
    for index in range(width):
        append_simple(
            layer=2,
            source_step=2,
            stage=QclaStage.INITIAL_PROPAGATE,
            kind=QclaGateKind.CNOT,
            controls=(_a(index),),
            target=_b(index),
        )

    carry, carry_depth = _carry_specs(width - 1)
    for spec in carry:
        raw.append(
            (
                2 + spec.local_layer,
                3,
                spec.stage,
                QclaDirection.FORWARD,
                spec,
            )
        )
    layer = 2 + carry_depth
    for index in range(1, width):
        append_simple(
            layer=layer + 1,
            source_step=4,
            stage=QclaStage.SUM_CARRY_WRITE,
            kind=QclaGateKind.CNOT,
            controls=(_z(index),),
            target=_b(index),
        )
    for index in range(width - 1):
        append_simple(
            layer=layer + 2,
            source_step=5,
            stage=QclaStage.COMPLEMENT_PREPARE,
            kind=QclaGateKind.X,
            controls=(),
            target=_b(index),
        )
    for index in range(1, width - 1):
        append_simple(
            layer=layer + 3,
            source_step=6,
            stage=QclaStage.REVERSE_PROPAGATE_PREPARE,
            kind=QclaGateKind.CNOT,
            controls=(_a(index),),
            target=_b(index),
        )

    reverse_start = layer + 3
    for spec in carry:
        reverse_local_layer = carry_depth + 1 - spec.local_layer
        raw.append(
            (
                reverse_start + reverse_local_layer,
                7,
                spec.stage,
                QclaDirection.REVERSE,
                spec,
            )
        )
    layer = reverse_start + carry_depth
    for index in range(1, width - 1):
        append_simple(
            layer=layer + 1,
            source_step=8,
            stage=QclaStage.FINAL_PROPAGATE_RESTORE,
            kind=QclaGateKind.CNOT,
            controls=(_a(index),),
            target=_b(index),
        )
    for index in range(width - 1):
        append_simple(
            layer=layer + 2,
            source_step=9,
            stage=QclaStage.INITIAL_GENERATE_UNCOMPUTE,
            kind=QclaGateKind.TOFFOLI,
            controls=(_a(index), _b(index)),
            target=_z(index + 1),
        )
    for index in range(width - 1):
        append_simple(
            layer=layer + 3,
            source_step=10,
            stage=QclaStage.OUTPUT_COMPLEMENT_RESTORE,
            kind=QclaGateKind.X,
            controls=(),
            target=_b(index),
        )

    raw.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2].value,
            item[4].round_index or 0,
            item[4].target,
            item[4].controls,
        )
    )
    # Width two has empty source steps 6--8.  Empty time slices carry no
    # operation or dependency and are therefore removed from the trace.
    used_layers = {
        layer_value: compact
        for compact, layer_value in enumerate(
            sorted({item[0] for item in raw}), start=1
        )
    }
    gates = tuple(
        QclaGate(
            gate_id=f"qcla:{sequence:06d}",
            kind=spec.kind,
            controls=spec.controls,
            target=spec.target,
            algorithmic_layer=used_layers[algorithmic_layer],
            source_step=source_step,
            stage=stage,
            direction=direction,
            round_index=spec.round_index,
            prefix_interval=spec.prefix_interval,
        )
        for sequence, (
            algorithmic_layer,
            source_step,
            stage,
            direction,
            spec,
        ) in enumerate(raw)
    )
    dependencies = _derive_dependencies(gates)
    intervals = _ancilla_intervals(gates, width)
    return QclaTrace(
        trace_id=f"draper-qcla-inplace-mod2n-width-{width}",
        width=width,
        source=QclaSourceReference(),
        gates=gates,
        dependencies=dependencies,
        ancilla_intervals=intervals,
    )


def replay_qcla(trace: QclaTrace, input_a: int, input_b: int) -> QclaReplaySummary:
    """Replay gate records from zero ancillas and verify the arithmetic contract."""

    limit = 1 << trace.width
    if not 0 <= input_a < limit or not 0 <= input_b < limit:
        raise QclaTraceError("input registers must fit the trace width")
    state: dict[str, int] = {}
    for index in range(trace.width):
        state[_a(index)] = (input_a >> index) & 1
        state[_b(index)] = (input_b >> index) & 1
    for interval in trace.ancilla_intervals:
        state[interval.value_id] = 0
    for gate in trace.gates:
        if gate.kind is QclaGateKind.X:
            fire = 1
        else:
            fire = 1
            for control in gate.controls:
                fire &= state[control]
        state[gate.target] ^= fire
    output_a = sum(state[_a(index)] << index for index in range(trace.width))
    output_b = sum(state[_b(index)] << index for index in range(trace.width))
    ancillas = sorted(
        {interval.value_id for interval in trace.ancilla_intervals}
    )
    nonzero = tuple(value for value in ancillas if state[value])
    expected_b = (input_a + input_b) % limit
    passed = output_a == input_a and output_b == expected_b and not nonzero
    if not passed:
        raise QclaTraceError(
            "QCLA replay failed arithmetic preservation or ancilla cleanup"
        )
    return QclaReplaySummary(
        width=trace.width,
        input_a=input_a,
        input_b=input_b,
        output_a=output_a,
        output_b=output_b,
        expected_b=expected_b,
        final_nonzero_ancillas=nonzero,
        passed=passed,
    )


def qcla_metrics(trace: QclaTrace) -> QclaMetrics:
    """Compute exact architecture-neutral gate, DAG, layer, and demand metrics."""

    counts = _count_gate_kinds(trace.gates)
    by_layer: dict[int, int] = defaultdict(int)
    for gate in trace.gates:
        if gate.kind is QclaGateKind.TOFFOLI:
            by_layer[gate.algorithmic_layer] += 1
    live_by_layer: dict[int, int] = defaultdict(int)
    for interval in trace.ancilla_intervals:
        for layer in range(interval.start_layer, interval.end_layer + 1):
            live_by_layer[layer] += 1

    predecessors: dict[str, list[str]] = defaultdict(list)
    for dependency in trace.dependencies:
        predecessors[dependency.successor].append(dependency.predecessor)
    longest: dict[str, int] = {}
    for gate_id in trace.topological_order():
        longest[gate_id] = 1 + max(
            (longest[pred] for pred in predecessors[gate_id]), default=0
        )
    scratch = {
        interval.value_id
        for interval in trace.ancilla_intervals
        if interval.family == "prefix_scratch"
    }
    return QclaMetrics(
        gate_count=len(trace.gates),
        x_count=counts[QclaGateKind.X],
        cnot_count=counts[QclaGateKind.CNOT],
        toffoli_count=counts[QclaGateKind.TOFFOLI],
        source_layer_count=max(gate.algorithmic_layer for gate in trace.gates),
        dependency_critical_path_gates=max(longest.values()),
        source_ancilla_count=trace.source_ancilla_count,
        prefix_scratch_count=len(scratch),
        peak_live_ancillas=max(live_by_layer.values()),
        peak_toffoli_per_layer=max(by_layer.values()),
        toffoli_demand_by_layer=tuple(sorted(by_layer.items())),
    )


def qcla_trace_to_data(trace: QclaTrace) -> dict[str, Any]:
    """Return deterministic JSON-compatible trace data."""

    metrics = qcla_metrics(trace)
    return {
        "ancilla_intervals": [
            {
                "end_layer": interval.end_layer,
                "family": interval.family,
                "reuse_epoch": interval.reuse_epoch,
                "start_layer": interval.start_layer,
                "value_id": interval.value_id,
            }
            for interval in trace.ancilla_intervals
        ],
        "arithmetic_contract": trace.arithmetic_contract,
        "dependencies": [
            {
                "predecessor": dependency.predecessor,
                "reason": dependency.reason,
                "successor": dependency.successor,
                "values": list(dependency.values),
            }
            for dependency in trace.dependencies
        ],
        "exported_overflow": trace.exported_overflow,
        "gates": [
            {
                "algorithmic_layer": gate.algorithmic_layer,
                "controls": list(gate.controls),
                "direction": gate.direction.value,
                "gate_id": gate.gate_id,
                "kind": gate.kind.value,
                "logical_support": list(gate.logical_support),
                "prefix_interval": (
                    list(gate.prefix_interval)
                    if gate.prefix_interval is not None
                    else None
                ),
                "read_values": list(gate.read_values),
                "round_index": gate.round_index,
                "semantic_evidence_status": gate.semantic_evidence_status.value,
                "source_step": gate.source_step,
                "stage": gate.stage.value,
                "target": gate.target,
                "write_values": list(gate.write_values),
            }
            for gate in trace.gates
        ],
        "incoming_carry": trace.incoming_carry,
        "metrics": {
            "cnot_count": metrics.cnot_count,
            "dependency_critical_path_gates": metrics.dependency_critical_path_gates,
            "gate_count": metrics.gate_count,
            "peak_live_ancillas": metrics.peak_live_ancillas,
            "peak_toffoli_per_layer": metrics.peak_toffoli_per_layer,
            "prefix_scratch_count": metrics.prefix_scratch_count,
            "source_ancilla_count": metrics.source_ancilla_count,
            "source_layer_count": metrics.source_layer_count,
            "toffoli_count": metrics.toffoli_count,
            "toffoli_demand_by_layer": [
                {"algorithmic_layer": layer, "toffoli_demand": demand}
                for layer, demand in metrics.toffoli_demand_by_layer
            ],
            "x_count": metrics.x_count,
        },
        "schema": trace.schema,
        "schema_version": trace.schema_version,
        "source": {
            "figures": list(trace.source.figures),
            "pdf_sha256": trace.source.pdf_sha256,
            "sections": list(trace.source.sections),
            "semantic_evidence_status": trace.source.semantic_evidence_status.value,
            "source_id": trace.source.source_id,
            "tables": list(trace.source.tables),
            "title": trace.source.title,
        },
        "trace_id": trace.trace_id,
        "width": trace.width,
    }


def dumps_qcla_trace(trace: QclaTrace) -> str:
    """Serialize a trace deterministically."""

    return json.dumps(qcla_trace_to_data(trace), indent=2, sort_keys=True) + "\n"
