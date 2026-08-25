"""Source-pinned QCLA lowering through an exact 7T CCX into adaptive PBC."""

from __future__ import annotations

import cmath
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGate, QclaGateKind, QclaStage, QclaTrace
from ecdlp_ftqc.compiler.native_lowering import (
    LogicalPrimitive,
    LogicalPrimitiveKind,
    LogicalTrace,
    PrimitiveDependency,
    PrimitiveDependencyKind,
)
from ecdlp_ftqc.compiler.pbc_lowering import (
    PbcTrace,
    lower_to_adaptive_pauli_measurements,
)
from ecdlp_ftqc.metadata import EvidenceStatus

SELINGER_CCX_SOURCE_ID = "arXiv:1210.0974v2"
SELINGER_CCX_SOURCE_PDF_SHA256 = (
    "5C1FBC4571B48F6E6893A8D15045509A08AB5C6764276B44BA1AC69C528129E2"
)
SELINGER_CCX_DECOMPOSITION_ID = "selinger-2013-circuit-1-exact-7t"


@dataclass(frozen=True, slots=True)
class QclaPrimitiveProvenance:
    """Mapping from one logical primitive back to its QCLA source gate."""

    primitive_id: str
    source_gate_id: str
    source_gate_kind: QclaGateKind
    source_algorithmic_layer: int
    expanded_layer: int
    local_column: int
    source_step: int
    stage: str
    direction: str
    decomposition_id: str
    evidence_status: EvidenceStatus = EvidenceStatus.LITERATURE


@dataclass(frozen=True, slots=True)
class QclaLogicalLowering:
    """Phase-exact logical trace plus its source-provenance map."""

    qcla_trace_id: str
    logical_trace: LogicalTrace
    provenance: tuple[QclaPrimitiveProvenance, ...]
    source_id: str = SELINGER_CCX_SOURCE_ID
    source_pdf_sha256: str = SELINGER_CCX_SOURCE_PDF_SHA256
    decomposition_id: str = SELINGER_CCX_DECOMPOSITION_ID

    def __post_init__(self) -> None:
        primitive_ids = {primitive.primitive_id for primitive in self.logical_trace.primitives}
        provenance_ids = {record.primitive_id for record in self.provenance}
        if primitive_ids != provenance_ids:
            raise ValueError("QCLA primitive provenance must cover the logical trace exactly")

    @property
    def primitive_counts(self) -> Counter[LogicalPrimitiveKind]:
        return Counter(primitive.kind for primitive in self.logical_trace.primitives)


@dataclass(frozen=True, slots=True)
class QclaAdaptivePbcLowering:
    """QCLA lowering with both the phase-exact and adaptive-PBC layers."""

    logical: QclaLogicalLowering
    pbc_trace: PbcTrace


@dataclass(frozen=True, slots=True)
class CcxChannelVerification:
    """Independent numerical check of the selected source circuit."""

    decomposition_id: str
    maximum_absolute_error: float
    tolerance: float
    passed: bool
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL


@dataclass(frozen=True, slots=True)
class _PrimitiveSpec:
    suffix: str
    kind: LogicalPrimitiveKind
    support: tuple[str, ...]
    local_column: int
    resource_state_demand: int = 0


def _gate_specs(gate: QclaGate) -> tuple[_PrimitiveSpec, ...]:
    if gate.kind is QclaGateKind.X:
        return (_PrimitiveSpec("00_x", LogicalPrimitiveKind.X, (gate.target,), 0),)
    if gate.kind is QclaGateKind.CNOT:
        return (
            _PrimitiveSpec(
                "00_cnot",
                LogicalPrimitiveKind.CNOT,
                (gate.controls[0], gate.target),
                0,
            ),
        )

    control_one, control_two = gate.controls
    target = gate.target
    # Selinger circuit (1), read left-to-right.  Columns 8 and 13 each contain
    # two disjoint gates and therefore preserve the parallelism shown there.
    return (
        _PrimitiveSpec("00_h_t", LogicalPrimitiveKind.H, (target,), 0),
        _PrimitiveSpec(
            "01_cnot_c2_t", LogicalPrimitiveKind.CNOT, (control_two, target), 1
        ),
        _PrimitiveSpec(
            "02_tdag_t", LogicalPrimitiveKind.T_DAGGER, (target,), 2, 1
        ),
        _PrimitiveSpec(
            "03_cnot_c1_t", LogicalPrimitiveKind.CNOT, (control_one, target), 3
        ),
        _PrimitiveSpec("04_t_t", LogicalPrimitiveKind.T, (target,), 4, 1),
        _PrimitiveSpec(
            "05_cnot_c2_t", LogicalPrimitiveKind.CNOT, (control_two, target), 5
        ),
        _PrimitiveSpec(
            "06_tdag_t", LogicalPrimitiveKind.T_DAGGER, (target,), 6, 1
        ),
        _PrimitiveSpec(
            "07_cnot_c1_t", LogicalPrimitiveKind.CNOT, (control_one, target), 7
        ),
        _PrimitiveSpec(
            "08_tdag_c2", LogicalPrimitiveKind.T_DAGGER, (control_two,), 8, 1
        ),
        _PrimitiveSpec("09_t_t", LogicalPrimitiveKind.T, (target,), 8, 1),
        _PrimitiveSpec("10_h_t", LogicalPrimitiveKind.H, (target,), 9),
        _PrimitiveSpec(
            "11_cnot_c1_c2", LogicalPrimitiveKind.CNOT, (control_one, control_two), 10
        ),
        _PrimitiveSpec(
            "12_tdag_c2", LogicalPrimitiveKind.T_DAGGER, (control_two,), 11, 1
        ),
        _PrimitiveSpec(
            "13_cnot_c1_c2", LogicalPrimitiveKind.CNOT, (control_one, control_two), 12
        ),
        _PrimitiveSpec("14_t_c1", LogicalPrimitiveKind.T, (control_one,), 13, 1),
        _PrimitiveSpec("15_s_c2", LogicalPrimitiveKind.S, (control_two,), 13),
    )


def lower_qcla_phase_exact(trace: QclaTrace) -> QclaLogicalLowering:
    """Expand QCLA gates and derive nearest-wire logical dependencies."""

    gate_position = {gate.gate_id: position for position, gate in enumerate(trace.gates)}
    records: list[tuple[int, int, int, LogicalPrimitive, QclaPrimitiveProvenance]] = []
    for gate in trace.gates:
        for spec_position, spec in enumerate(_gate_specs(gate)):
            expanded_layer = (gate.algorithmic_layer - 1) * 14 + spec.local_column + 1
            primitive = LogicalPrimitive(
                primitive_id=(
                    f"{gate.gate_id}::{SELINGER_CCX_DECOMPOSITION_ID}:{spec.suffix}"
                ),
                source_node_id=gate.gate_id,
                kind=spec.kind,
                logical_support=spec.support,
                resource_state_demand=spec.resource_state_demand,
                evidence_status=EvidenceStatus.LITERATURE,
            )
            provenance = QclaPrimitiveProvenance(
                primitive_id=primitive.primitive_id,
                source_gate_id=gate.gate_id,
                source_gate_kind=gate.kind,
                source_algorithmic_layer=gate.algorithmic_layer,
                expanded_layer=expanded_layer,
                local_column=spec.local_column,
                source_step=gate.source_step,
                stage=gate.stage.value,
                direction=gate.direction.value,
                decomposition_id=(
                    SELINGER_CCX_DECOMPOSITION_ID
                    if gate.kind is QclaGateKind.TOFFOLI
                    else "identity-gate-map"
                ),
            )
            records.append(
                (
                    expanded_layer,
                    gate_position[gate.gate_id],
                    spec_position,
                    primitive,
                    provenance,
                )
            )
    records.sort(key=lambda record: record[:3])

    dependencies: list[PrimitiveDependency] = []
    last_use: dict[str, LogicalPrimitive] = {}
    by_layer: dict[int, list[LogicalPrimitive]] = defaultdict(list)
    for expanded_layer, _, _, primitive, _ in records:
        by_layer[expanded_layer].append(primitive)
    for expanded_layer in sorted(by_layer):
        layer_primitives = by_layer[expanded_layer]
        occupied: set[str] = set()
        for primitive in layer_primitives:
            if occupied.intersection(primitive.logical_support):
                raise ValueError("expanded QCLA layer contains overlapping logical support")
            occupied.update(primitive.logical_support)
            prior_values: dict[str, list[str]] = defaultdict(list)
            for value in primitive.logical_support:
                predecessor = last_use.get(value)
                if predecessor is not None:
                    prior_values[predecessor.primitive_id].append(value)
            primitive_by_id = {
                candidate.primitive_id: candidate for candidate in last_use.values()
            }
            for predecessor_id, values in sorted(prior_values.items()):
                predecessor = primitive_by_id[predecessor_id]
                internal = predecessor.source_node_id == primitive.source_node_id
                dependencies.append(
                    PrimitiveDependency(
                        predecessor=predecessor_id,
                        successor=primitive.primitive_id,
                        kind=(
                            PrimitiveDependencyKind.SOURCE_GATE_DECOMPOSITION
                            if internal
                            else PrimitiveDependencyKind.SOURCE_DAG
                        ),
                        source_reason=(
                            "selinger_circuit_1_wire_order:"
                            if internal
                            else "qcla_nearest_wire_order:"
                        )
                        + ",".join(sorted(values)),
                    )
                )
        for primitive in layer_primitives:
            for value in primitive.logical_support:
                last_use[value] = primitive

    logical_trace = LogicalTrace(
        trace_id=f"{trace.trace_id}:{SELINGER_CCX_DECOMPOSITION_ID}:logical-v1",
        source_circuit_id=trace.trace_id,
        source_dag_schema_version=trace.schema_version,
        source_evidence_status=EvidenceStatus.LITERATURE,
        peak_source_processor_occupancy=2 * trace.width + trace.source_ancilla_count,
        primitives=tuple(record[3] for record in records),
        dependencies=tuple(dependencies),
    )
    return QclaLogicalLowering(
        qcla_trace_id=trace.trace_id,
        logical_trace=logical_trace,
        provenance=tuple(record[4] for record in records),
    )


def lower_qcla_to_adaptive_pbc(trace: QclaTrace) -> QclaAdaptivePbcLowering:
    """Lower QCLA through the selected phase-exact CCX and reviewed PBC gadgets."""

    logical = lower_qcla_phase_exact(trace)
    return QclaAdaptivePbcLowering(
        logical=logical,
        pbc_trace=lower_to_adaptive_pauli_measurements(logical.logical_trace),
    )


def verify_selinger_ccx_channel(tolerance: float = 1e-12) -> CcxChannelVerification:
    """Numerically compare circuit (1) with an ideal CCX, up to global phase."""

    if tolerance <= 0:
        raise ValueError("verification tolerance must be positive")
    unitary = [[0j for _ in range(8)] for _ in range(8)]
    ideal = [[0j for _ in range(8)] for _ in range(8)]
    source_gate = QclaGate(
        gate_id="verification:ccx",
        kind=QclaGateKind.TOFFOLI,
        controls=("c1", "c2"),
        target="t",
        algorithmic_layer=1,
        source_step=1,
        stage=QclaStage.INITIAL_GENERATE,
    )
    bit_for_value = {"c1": 2, "c2": 1, "t": 0}
    root_two = math.sqrt(2.0)
    for basis in range(8):
        state = [0j for _ in range(8)]
        state[basis] = 1.0
        for spec in _gate_specs(source_gate):
            bits = tuple(bit_for_value[value] for value in spec.support)
            if spec.kind is LogicalPrimitiveKind.CNOT:
                control, target = bits
                updated = [0j for _ in range(8)]
                for index, amplitude in enumerate(state):
                    output = index ^ (1 << target) if (index >> control) & 1 else index
                    updated[output] += amplitude
                state = updated
            elif spec.kind is LogicalPrimitiveKind.H:
                target = bits[0]
                updated = [0j for _ in range(8)]
                for index, amplitude in enumerate(state):
                    zero = index & ~(1 << target)
                    sign = -1.0 if (index >> target) & 1 else 1.0
                    updated[zero] += amplitude / root_two
                    updated[zero | (1 << target)] += sign * amplitude / root_two
                state = updated
            else:
                target = bits[0]
                phase = {
                    LogicalPrimitiveKind.T: cmath.exp(1j * math.pi / 4),
                    LogicalPrimitiveKind.T_DAGGER: cmath.exp(-1j * math.pi / 4),
                    LogicalPrimitiveKind.S: 1j,
                }[spec.kind]
                for index in range(8):
                    if (index >> target) & 1:
                        state[index] *= phase
        for output_index, amplitude in enumerate(state):
            unitary[output_index][basis] = amplitude
        output = basis ^ 1 if (basis & 0b110) == 0b110 else basis
        ideal[output][basis] = 1.0
    overlap = sum(
        ideal[row][column].conjugate() * unitary[row][column]
        for row in range(8)
        for column in range(8)
    )
    phase = overlap / abs(overlap)
    error = max(
        abs(unitary[row][column] - phase * ideal[row][column])
        for row in range(8)
        for column in range(8)
    )
    return CcxChannelVerification(
        decomposition_id=SELINGER_CCX_DECOMPOSITION_ID,
        maximum_absolute_error=error,
        tolerance=tolerance,
        passed=error <= tolerance,
    )


def qcla_logical_lowering_to_data(lowering: QclaLogicalLowering) -> dict[str, Any]:
    """Return a compact deterministic summary without emitting the full trace."""

    counts = lowering.primitive_counts
    return {
        "decomposition_id": lowering.decomposition_id,
        "logical_dependency_count": len(lowering.logical_trace.dependencies),
        "logical_primitive_count": len(lowering.logical_trace.primitives),
        "peak_source_processor_occupancy": (
            lowering.logical_trace.peak_source_processor_occupancy
        ),
        "primitive_counts": {
            kind.value: counts[kind]
            for kind in LogicalPrimitiveKind
            if counts[kind]
        },
        "qcla_trace_id": lowering.qcla_trace_id,
        "resource_state_demand": sum(
            primitive.resource_state_demand
            for primitive in lowering.logical_trace.primitives
        ),
        "source_id": lowering.source_id,
        "source_pdf_sha256": lowering.source_pdf_sha256,
    }
