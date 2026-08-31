"""Clean out-of-place modulo-2**n QCLA source trace.

This module implements Draper--Kutin--Rains--Svore Sections 4.1 and 5.1.
The trace maps ``(A, B, 0)`` to ``(A, B, A + B mod 2**n)``.  Its source
layers expose arithmetic parallelism only; they are not QEC cycles or runtime.
The reviewed forward carry network is selected from the existing in-place
frontend so both variants share exactly the same prefix-round construction.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ecdlp_ftqc.circuits.qcla import (
    QclaDirection,
    QclaGateKind,
    QclaSourceReference,
    QclaStage,
    build_qcla_trace,
)
from ecdlp_ftqc.metadata import EvidenceStatus

OOP_QCLA_SCHEMA = "ecdlp-ftqc/qcla-clean-oop-mod2n-trace"
OOP_QCLA_SCHEMA_VERSION = 1


class OopQclaTraceError(ValueError):
    """Raised when a clean OOP-QCLA trace violates its source contract."""


class OopQclaStage(str, Enum):
    """Source role of a gate in the clean OOP construction."""

    INITIAL_GENERATE = "initial_generate"
    INITIAL_PROPAGATE = "initial_propagate"
    PREFIX_PROPAGATE = "prefix_propagate"
    PREFIX_GENERATE = "prefix_generate"
    PREFIX_CARRY = "prefix_carry"
    PREFIX_UNCOMPUTE = "prefix_uncompute"
    SUM_WRITE = "sum_write"
    INPUT_RESTORE = "input_restore"
    TOP_BIT_WRITE = "top_bit_write"


@dataclass(frozen=True, slots=True)
class OopQclaGate:
    """One architecture-neutral reversible source gate."""

    gate_id: str
    kind: QclaGateKind
    controls: tuple[str, ...]
    target: str
    algorithmic_layer: int
    source_step: int
    stage: OopQclaStage
    round_index: int | None = None
    prefix_interval: tuple[int, int, int] | None = None
    semantic_evidence_status: EvidenceStatus = EvidenceStatus.LITERATURE

    def __post_init__(self) -> None:
        if not self.gate_id or self.algorithmic_layer < 1:
            raise OopQclaTraceError("gate ID and positive layer are required")
        if not 1 <= self.source_step <= 5:
            raise OopQclaTraceError("OOP-QCLA source step must be in 1..5")
        expected_controls = {
            QclaGateKind.X: 0,
            QclaGateKind.CNOT: 1,
            QclaGateKind.TOFFOLI: 2,
        }[self.kind]
        if len(self.controls) != expected_controls:
            raise OopQclaTraceError("gate kind has the wrong number of controls")
        if len(self.controls) != len(set(self.controls)) or self.target in self.controls:
            raise OopQclaTraceError("gate support must contain distinct values")
        if self.round_index is not None and self.round_index < 1:
            raise OopQclaTraceError("prefix round index must be positive")
        if self.prefix_interval is not None:
            left, middle, right = self.prefix_interval
            if not 0 <= left < middle < right:
                raise OopQclaTraceError("invalid prefix interval")

    @property
    def logical_support(self) -> tuple[str, ...]:
        return (*self.controls, self.target)


@dataclass(frozen=True, slots=True)
class OopQclaDependency:
    """Nearest prior use of one or more logical values."""

    predecessor: str
    successor: str
    values: tuple[str, ...]
    reason: str = "wire_order"

    def __post_init__(self) -> None:
        if not self.predecessor or not self.successor:
            raise OopQclaTraceError("dependency endpoints cannot be empty")
        if self.predecessor == self.successor:
            raise OopQclaTraceError("self dependencies are not allowed")
        if not self.values or len(self.values) != len(set(self.values)):
            raise OopQclaTraceError("dependency values must be nonempty and unique")
        if self.reason != "wire_order":
            raise OopQclaTraceError("unsupported dependency reason")


@dataclass(frozen=True, slots=True)
class OopQclaAncillaInterval:
    """Lifetime of one clean prefix-scratch logical value."""

    value_id: str
    start_layer: int
    end_layer: int

    def __post_init__(self) -> None:
        if not self.value_id.startswith("p:"):
            raise OopQclaTraceError("OOP auxiliary values must be prefix scratch")
        if not 1 <= self.start_layer <= self.end_layer:
            raise OopQclaTraceError("invalid OOP ancilla interval")


@dataclass(frozen=True, slots=True)
class OopQclaReplaySummary:
    """Independent computational-basis replay result."""

    width: int
    input_a: int
    input_b: int
    output_a: int
    output_b: int
    output_sum: int
    expected_sum: int
    final_nonzero_ancillas: tuple[str, ...]
    passed: bool


@dataclass(frozen=True, slots=True)
class OopQclaMetrics:
    """Architecture-neutral workload metrics."""

    gate_count: int
    cnot_count: int
    toffoli_count: int
    source_layer_count: int
    dependency_critical_path_gates: int
    source_auxiliary_count: int
    fully_resident_source_values: int
    peak_toffoli_per_layer: int
    peak_toffoli_layer: int
    toffoli_demand_by_layer: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class OopQclaTrace:
    """Validated clean out-of-place modulo-QCLA trace."""

    trace_id: str
    width: int
    source: QclaSourceReference
    gates: tuple[OopQclaGate, ...]
    dependencies: tuple[OopQclaDependency, ...]
    ancilla_intervals: tuple[OopQclaAncillaInterval, ...]
    arithmetic_contract: str = "(A,B,0)->(A,B,A+B mod 2^n)"
    incoming_carry: bool = False
    exported_overflow: bool = False
    schema: str = OOP_QCLA_SCHEMA
    schema_version: int = OOP_QCLA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trace_id or self.width < 2:
            raise OopQclaTraceError("trace ID and width at least two are required")
        if self.schema != OOP_QCLA_SCHEMA or self.schema_version != OOP_QCLA_SCHEMA_VERSION:
            raise OopQclaTraceError("unsupported OOP-QCLA schema")
        if self.arithmetic_contract != "(A,B,0)->(A,B,A+B mod 2^n)":
            raise OopQclaTraceError("unsupported OOP-QCLA arithmetic contract")
        if self.incoming_carry or self.exported_overflow:
            raise OopQclaTraceError("this variant has neither carry-in nor overflow")
        self._validate()

    @property
    def carry_length(self) -> int:
        return self.width - 1

    @property
    def expected_toffoli_count(self) -> int:
        length = self.carry_length
        return 5 * self.width - 3 * length.bit_count() - 3 * _floor_log2(length) - 6

    @property
    def expected_cnot_count(self) -> int:
        return 3 * self.width - 2

    @property
    def expected_source_auxiliary_count(self) -> int:
        length = self.carry_length
        return length - length.bit_count() - _floor_log2(length)

    @property
    def expected_fully_resident_source_values(self) -> int:
        return 3 * self.width + self.expected_source_auxiliary_count

    @property
    def expected_source_layer_count(self) -> int | None:
        # Section 5.1 prints n >= 4, while Section 3 explicitly says its carry
        # depth expression overcounts carry lengths <= 3.  The modulo circuit
        # uses carry length n-1, so admit the closed form only from width 5.
        if self.width < 5:
            return None
        length = self.carry_length
        return _floor_log2(length) + _floor_log2_fraction(length, 3) + 7

    def topological_order(self) -> tuple[str, ...]:
        original = {gate.gate_id: index for index, gate in enumerate(self.gates)}
        indegree = {gate_id: 0 for gate_id in original}
        successors: dict[str, list[str]] = defaultdict(list)
        for dependency in self.dependencies:
            successors[dependency.predecessor].append(dependency.successor)
            indegree[dependency.successor] += 1
        ready = deque(gate_id for gate_id in original if indegree[gate_id] == 0)
        result: list[str] = []
        while ready:
            gate_id = ready.popleft()
            result.append(gate_id)
            for successor in sorted(successors[gate_id], key=original.__getitem__):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
        if len(result) != len(self.gates):
            raise OopQclaTraceError("OOP-QCLA trace must be acyclic")
        return tuple(result)

    def _validate(self) -> None:
        if self.source != QclaSourceReference():
            raise OopQclaTraceError("OOP-QCLA must use the pinned Draper source")
        gate_ids = tuple(gate.gate_id for gate in self.gates)
        if len(gate_ids) != len(set(gate_ids)):
            raise OopQclaTraceError("gate IDs must be unique")
        position = {gate_id: index for index, gate_id in enumerate(gate_ids)}
        expected_order = sorted(
            self.gates,
            key=lambda gate: (gate.algorithmic_layer, position[gate.gate_id]),
        )
        if list(self.gates) != expected_order:
            raise OopQclaTraceError("gates must be ordered by source layer")

        allowed = {
            *(_a(index) for index in range(self.width)),
            *(_b(index) for index in range(self.width)),
            *(_z(index) for index in range(self.width)),
            *(interval.value_id for interval in self.ancilla_intervals),
        }
        by_layer: dict[int, set[str]] = defaultdict(set)
        for gate in self.gates:
            if not set(gate.logical_support) <= allowed:
                raise OopQclaTraceError("gate support contains an unknown value")
            support = set(gate.logical_support)
            if by_layer[gate.algorithmic_layer] & support:
                raise OopQclaTraceError("gates in one source layer must be disjoint")
            by_layer[gate.algorithmic_layer].update(support)
        if self.dependencies != _derive_dependencies(self.gates):
            raise OopQclaTraceError("dependencies must be exact nearest-wire dependencies")
        self.topological_order()

        counts = _gate_counts(self.gates)
        if counts[QclaGateKind.TOFFOLI] != self.expected_toffoli_count:
            raise OopQclaTraceError("Toffoli count disagrees with the source formula")
        if counts[QclaGateKind.CNOT] != self.expected_cnot_count:
            raise OopQclaTraceError("CNOT count disagrees with the source formula")
        if counts[QclaGateKind.X] != 0:
            raise OopQclaTraceError("clean OOP-QCLA should not contain X gates")
        if len(self.ancilla_intervals) != self.expected_source_auxiliary_count:
            raise OopQclaTraceError("auxiliary count disagrees with the source formula")
        expected_layers = self.expected_source_layer_count
        if expected_layers is not None and max(by_layer) != expected_layers:
            raise OopQclaTraceError("source depth disagrees with the source formula")
        _validate_ancilla_intervals(self)


def _floor_log2(value: int) -> int:
    if value < 1:
        raise OopQclaTraceError("logarithm input must be positive")
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


def _derive_dependencies(
    gates: tuple[OopQclaGate, ...],
) -> tuple[OopQclaDependency, ...]:
    last_use: dict[str, str] = {}
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for gate in gates:
        predecessors: dict[str, list[str]] = defaultdict(list)
        for value in gate.logical_support:
            predecessor = last_use.get(value)
            if predecessor is not None:
                predecessors[predecessor].append(value)
        for predecessor, values in predecessors.items():
            grouped[(predecessor, gate.gate_id)].extend(values)
        for value in gate.logical_support:
            last_use[value] = gate.gate_id
    return tuple(
        OopQclaDependency(
            predecessor=predecessor,
            successor=successor,
            values=tuple(sorted(set(values))),
        )
        for (predecessor, successor), values in grouped.items()
    )


def _ancilla_intervals(
    gates: tuple[OopQclaGate, ...],
) -> tuple[OopQclaAncillaInterval, ...]:
    layers: dict[str, list[int]] = defaultdict(list)
    for gate in gates:
        for value in gate.logical_support:
            if value.startswith("p:"):
                layers[value].append(gate.algorithmic_layer)
    return tuple(
        OopQclaAncillaInterval(
            value_id=value,
            start_layer=min(value_layers),
            end_layer=max(value_layers),
        )
        for value, value_layers in sorted(layers.items())
    )


def _validate_ancilla_intervals(trace: OopQclaTrace) -> None:
    expected = _ancilla_intervals(trace.gates)
    if trace.ancilla_intervals != expected:
        raise OopQclaTraceError("ancilla intervals must match exact prefix uses")


def _gate_counts(gates: tuple[OopQclaGate, ...]) -> dict[QclaGateKind, int]:
    result = {kind: 0 for kind in QclaGateKind}
    for gate in gates:
        result[gate.kind] += 1
    return result


def _stage_from_forward_carry(stage: QclaStage) -> OopQclaStage:
    mapping = {
        QclaStage.PREFIX_PROPAGATE: OopQclaStage.PREFIX_PROPAGATE,
        QclaStage.PREFIX_GENERATE: OopQclaStage.PREFIX_GENERATE,
        QclaStage.PREFIX_CARRY: OopQclaStage.PREFIX_CARRY,
        QclaStage.PREFIX_UNCOMPUTE: OopQclaStage.PREFIX_UNCOMPUTE,
    }
    try:
        return mapping[stage]
    except KeyError as exc:
        raise OopQclaTraceError("unexpected gate in forward carry network") from exc


def build_oop_qcla_trace(width: int) -> OopQclaTrace:
    """Build the clean out-of-place modulo-2**n QCLA source trace."""

    if width < 2:
        raise OopQclaTraceError("OOP-QCLA width must be at least two")
    raw: list[
        tuple[
            int,
            int,
            OopQclaStage,
            QclaGateKind,
            tuple[str, ...],
            str,
            int | None,
            tuple[int, int, int] | None,
        ]
    ] = []

    def append(
        layer: int,
        source_step: int,
        stage: OopQclaStage,
        kind: QclaGateKind,
        controls: tuple[str, ...],
        target: str,
        round_index: int | None = None,
        prefix_interval: tuple[int, int, int] | None = None,
    ) -> None:
        raw.append(
            (
                layer,
                source_step,
                stage,
                kind,
                controls,
                target,
                round_index,
                prefix_interval,
            )
        )

    length = width - 1
    for index in range(length):
        append(
            1,
            1,
            OopQclaStage.INITIAL_GENERATE,
            QclaGateKind.TOFFOLI,
            (_a(index), _b(index)),
            _z(index + 1),
        )
    for index in range(1, length):
        append(
            2,
            2,
            OopQclaStage.INITIAL_PROPAGATE,
            QclaGateKind.CNOT,
            (_a(index),),
            _b(index),
        )

    reviewed = build_qcla_trace(width)
    forward_carry = tuple(
        gate
        for gate in reviewed.gates
        if gate.source_step == 3 and gate.direction is QclaDirection.FORWARD
    )
    for gate in forward_carry:
        append(
            gate.algorithmic_layer,
            3,
            _stage_from_forward_carry(gate.stage),
            gate.kind,
            gate.controls,
            gate.target,
            gate.round_index,
            gate.prefix_interval,
        )
    carry_end = max((gate.algorithmic_layer for gate in forward_carry), default=2)
    sum_layer = carry_end + 1
    restore_layer = carry_end + 2

    for index in range(length):
        append(
            sum_layer,
            4,
            OopQclaStage.SUM_WRITE,
            QclaGateKind.CNOT,
            (_b(index),),
            _z(index),
        )
    append(
        sum_layer,
        4,
        OopQclaStage.TOP_BIT_WRITE,
        QclaGateKind.CNOT,
        (_b(width - 1),),
        _z(width - 1),
    )
    append(
        restore_layer,
        5,
        OopQclaStage.INPUT_RESTORE,
        QclaGateKind.CNOT,
        (_a(0),),
        _z(0),
    )
    for index in range(1, length):
        append(
            restore_layer,
            5,
            OopQclaStage.INPUT_RESTORE,
            QclaGateKind.CNOT,
            (_a(index),),
            _b(index),
        )
    append(
        restore_layer,
        5,
        OopQclaStage.TOP_BIT_WRITE,
        QclaGateKind.CNOT,
        (_a(width - 1),),
        _z(width - 1),
    )

    raw.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2].value,
            item[6] or 0,
            item[5],
            item[4],
        )
    )
    layer_map = {
        layer: compact
        for compact, layer in enumerate(sorted({item[0] for item in raw}), start=1)
    }
    gates = tuple(
        OopQclaGate(
            gate_id=f"qcla-oop:{sequence:06d}",
            kind=kind,
            controls=controls,
            target=target,
            algorithmic_layer=layer_map[layer],
            source_step=source_step,
            stage=stage,
            round_index=round_index,
            prefix_interval=prefix_interval,
        )
        for sequence, (
            layer,
            source_step,
            stage,
            kind,
            controls,
            target,
            round_index,
            prefix_interval,
        ) in enumerate(raw)
    )
    intervals = _ancilla_intervals(gates)
    return OopQclaTrace(
        trace_id=f"draper-qcla-clean-oop-mod2n-width-{width}",
        width=width,
        source=QclaSourceReference(),
        gates=gates,
        dependencies=_derive_dependencies(gates),
        ancilla_intervals=intervals,
    )


def replay_oop_qcla(
    trace: OopQclaTrace,
    input_a: int,
    input_b: int,
) -> OopQclaReplaySummary:
    """Replay the trace from zero output/scratch and verify its full contract."""

    limit = 1 << trace.width
    if not 0 <= input_a < limit or not 0 <= input_b < limit:
        raise OopQclaTraceError("input registers must fit the trace width")
    state: dict[str, int] = {}
    for index in range(trace.width):
        state[_a(index)] = (input_a >> index) & 1
        state[_b(index)] = (input_b >> index) & 1
        state[_z(index)] = 0
    for interval in trace.ancilla_intervals:
        state[interval.value_id] = 0
    for gate in trace.gates:
        fire = 1
        for control in gate.controls:
            fire &= state[control]
        state[gate.target] ^= fire

    output_a = sum(state[_a(index)] << index for index in range(trace.width))
    output_b = sum(state[_b(index)] << index for index in range(trace.width))
    output_sum = sum(state[_z(index)] << index for index in range(trace.width))
    expected_sum = (input_a + input_b) % limit
    nonzero = tuple(
        interval.value_id
        for interval in trace.ancilla_intervals
        if state[interval.value_id]
    )
    passed = (
        output_a == input_a
        and output_b == input_b
        and output_sum == expected_sum
        and not nonzero
    )
    if not passed:
        raise OopQclaTraceError("OOP-QCLA replay failed preservation, sum, or cleanup")
    return OopQclaReplaySummary(
        width=trace.width,
        input_a=input_a,
        input_b=input_b,
        output_a=output_a,
        output_b=output_b,
        output_sum=output_sum,
        expected_sum=expected_sum,
        final_nonzero_ancillas=nonzero,
        passed=True,
    )


def oop_qcla_metrics(trace: OopQclaTrace) -> OopQclaMetrics:
    """Compute source metrics without attaching backend timing."""

    counts = _gate_counts(trace.gates)
    by_layer: dict[int, int] = defaultdict(int)
    for gate in trace.gates:
        if gate.kind is QclaGateKind.TOFFOLI:
            by_layer[gate.algorithmic_layer] += 1
    demand = tuple(sorted(by_layer.items()))

    predecessors: dict[str, set[str]] = defaultdict(set)
    for dependency in trace.dependencies:
        predecessors[dependency.successor].add(dependency.predecessor)
    depth: dict[str, int] = {}
    for gate_id in trace.topological_order():
        depth[gate_id] = 1 + max(
            (depth[predecessor] for predecessor in predecessors[gate_id]),
            default=0,
        )
    peak_layer, peak_demand = max(demand, key=lambda item: item[1])
    return OopQclaMetrics(
        gate_count=len(trace.gates),
        cnot_count=counts[QclaGateKind.CNOT],
        toffoli_count=counts[QclaGateKind.TOFFOLI],
        source_layer_count=max(gate.algorithmic_layer for gate in trace.gates),
        dependency_critical_path_gates=max(depth.values()),
        source_auxiliary_count=len(trace.ancilla_intervals),
        fully_resident_source_values=trace.expected_fully_resident_source_values,
        peak_toffoli_per_layer=peak_demand,
        peak_toffoli_layer=peak_layer,
        toffoli_demand_by_layer=demand,
    )


def oop_qcla_trace_to_data(trace: OopQclaTrace) -> dict[str, Any]:
    """Return a deterministic JSON-compatible trace record."""

    metrics = oop_qcla_metrics(trace)
    return {
        "arithmetic_contract": trace.arithmetic_contract,
        "ancilla_intervals": [
            {
                "end_layer": interval.end_layer,
                "start_layer": interval.start_layer,
                "value_id": interval.value_id,
            }
            for interval in trace.ancilla_intervals
        ],
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
                "gate_id": gate.gate_id,
                "kind": gate.kind.value,
                "logical_support": list(gate.logical_support),
                "prefix_interval": (
                    list(gate.prefix_interval) if gate.prefix_interval is not None else None
                ),
                "round_index": gate.round_index,
                "semantic_evidence_status": gate.semantic_evidence_status.value,
                "source_step": gate.source_step,
                "stage": gate.stage.value,
                "target": gate.target,
            }
            for gate in trace.gates
        ],
        "incoming_carry": trace.incoming_carry,
        "metrics": {
            "cnot_count": metrics.cnot_count,
            "dependency_critical_path_gates": metrics.dependency_critical_path_gates,
            "fully_resident_source_values": metrics.fully_resident_source_values,
            "gate_count": metrics.gate_count,
            "peak_toffoli_layer": metrics.peak_toffoli_layer,
            "peak_toffoli_per_layer": metrics.peak_toffoli_per_layer,
            "source_auxiliary_count": metrics.source_auxiliary_count,
            "source_layer_count": metrics.source_layer_count,
            "toffoli_count": metrics.toffoli_count,
            "toffoli_demand_by_layer": [list(item) for item in metrics.toffoli_demand_by_layer],
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


def dumps_oop_qcla_trace(trace: OopQclaTrace) -> str:
    """Serialize a trace canonically for reproducibility checks."""

    return json.dumps(
        oop_qcla_trace_to_data(trace),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
