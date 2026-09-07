"""Width-5 joint direct-CCZ validation records.

This module builds a separate, implementation-neutral candidate record.  It
does not modify the reviewed source-aligned QCLA trace and does not create a
native schedule.  Pairwise CCX commutation is decided exactly by exhaustive
truth-table comparison on the union of the two supports.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGateKind
from ecdlp_ftqc.circuits.qcla_oop import OopQclaGate, OopQclaStage, OopQclaTrace
from ecdlp_ftqc.metadata import EvidenceStatus

JOINT_DIRECT_CCZ_SCHEMA = "ecdlp-ftqc/width5-joint-direct-ccz-validation-plan"
JOINT_DIRECT_CCZ_SCHEMA_VERSION = 1


class JointDirectCczPlanError(ValueError):
    """Raised when a joint-CCX candidate violates its validation contract."""


class CcxOverlapKind(str, Enum):
    """Role-sensitive overlap class for two positive-control CCX gates."""

    DISJOINT = "disjoint"
    SHARED_CONTROL = "shared_control"
    SHARED_TARGET = "shared_target"
    LEFT_TARGET_RIGHT_CONTROL = "left_target_right_control"
    RIGHT_TARGET_LEFT_CONTROL = "right_target_left_control"
    BIDIRECTIONAL_TARGET_CONTROL = "bidirectional_target_control"


@dataclass(frozen=True, slots=True)
class CcxOperation:
    """One source CCX used by the joint-lowering validation record."""

    source_gate_id: str
    controls: tuple[str, str]
    target: str
    source_algorithmic_layer: int
    source_stage: str

    def __post_init__(self) -> None:
        if (
            not self.source_gate_id
            or len(set(self.controls)) != 2
            or self.target in self.controls
            or self.source_algorithmic_layer < 1
            or not self.source_stage
        ):
            raise JointDirectCczPlanError("invalid CCX operation")

    @property
    def logical_support(self) -> tuple[str, str, str]:
        return (*self.controls, self.target)


@dataclass(frozen=True, slots=True)
class CcxPairCertificate:
    """Exact truth-table commutation result for a pair of CCX gates."""

    left_source_gate_id: str
    right_source_gate_id: str
    overlap_kind: CcxOverlapKind
    shared_controls: tuple[str, ...]
    shared_target: str | None
    left_target_in_right_controls: bool
    right_target_in_left_controls: bool
    union_support: tuple[str, ...]
    truth_table_rows_checked: int
    commutes: bool
    witness_input: tuple[tuple[str, int], ...] | None
    left_then_right_output: tuple[tuple[str, int], ...] | None
    right_then_left_output: tuple[tuple[str, int], ...] | None
    evidence_status: EvidenceStatus = EvidenceStatus.PROVED

    def __post_init__(self) -> None:
        if self.left_source_gate_id == self.right_source_gate_id:
            raise JointDirectCczPlanError("pair endpoints must be distinct")
        if self.truth_table_rows_checked != 1 << len(self.union_support):
            raise JointDirectCczPlanError("pair truth-table size is inconsistent")
        witnesses = (
            self.witness_input,
            self.left_then_right_output,
            self.right_then_left_output,
        )
        if self.commutes and any(item is not None for item in witnesses):
            raise JointDirectCczPlanError("commuting pair cannot carry a witness")
        if not self.commutes and any(item is None for item in witnesses):
            raise JointDirectCczPlanError("noncommuting pair needs a complete witness")


@dataclass(frozen=True, slots=True)
class JointPpmRecord:
    """One logical PPM in a joint direct-CCZ macro-layer."""

    operation_id: str
    source_gate_id: str
    phase: int
    logical_support: tuple[str, ...]
    pauli_terms: tuple[str, ...]
    outcome_token: str

    def __post_init__(self) -> None:
        if self.phase not in {1, 2}:
            raise JointDirectCczPlanError("joint PPM phase must be one or two")
        if (
            not self.operation_id
            or not self.source_gate_id
            or not self.outcome_token
            or not self.logical_support
            or len(self.logical_support) != len(self.pauli_terms)
            or len(set(self.logical_support)) != len(self.logical_support)
            or any(term not in {"X", "Z"} for term in self.pauli_terms)
        ):
            raise JointDirectCczPlanError("invalid joint PPM record")


@dataclass(frozen=True, slots=True)
class JointCczResourceRecord:
    """Fresh resource triple consumed by exactly one source CCX."""

    event_id: str
    source_gate_id: str
    resource_values: tuple[str, str, str]
    consumed: bool = True

    def __post_init__(self) -> None:
        if (
            not self.event_id
            or not self.source_gate_id
            or len(set(self.resource_values)) != 3
            or not self.consumed
        ):
            raise JointDirectCczPlanError("invalid joint CCZ resource record")


@dataclass(frozen=True, slots=True)
class JointCcxMacroLayer:
    """A causally proposed commuting CCX set under one incoming frame."""

    macro_layer_id: str
    operations: tuple[CcxOperation, ...]
    pair_certificates: tuple[CcxPairCertificate, ...]
    common_incoming_frame: str
    target_basis_change_values: tuple[str, ...]
    resources: tuple[JointCczResourceRecord, ...]
    phase_one_ppms: tuple[JointPpmRecord, ...]
    phase_two_ppms: tuple[JointPpmRecord, ...]
    correction_maps: tuple[tuple[str, tuple[str, ...]], ...]
    event_to_event_reaction_edges: tuple[tuple[str, str], ...]
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL

    def __post_init__(self) -> None:
        if not self.macro_layer_id or not self.operations:
            raise JointDirectCczPlanError("joint macro-layer cannot be empty")
        operation_ids = tuple(item.source_gate_id for item in self.operations)
        if len(operation_ids) != len(set(operation_ids)):
            raise JointDirectCczPlanError("macro-layer source gates must be unique")
        expected_pairs = len(self.operations) * (len(self.operations) - 1) // 2
        if len(self.pair_certificates) != expected_pairs or any(
            not item.commutes for item in self.pair_certificates
        ):
            raise JointDirectCczPlanError("macro-layer contains an uncertified pair")
        expected_targets = tuple(sorted({item.target for item in self.operations}))
        if self.target_basis_change_values != expected_targets:
            raise JointDirectCczPlanError("target H set must contain each target once")
        if len(self.resources) != len(self.operations):
            raise JointDirectCczPlanError("each CCX needs one resource triple")
        if len(self.phase_one_ppms) != 3 * len(self.operations) or len(
            self.phase_two_ppms
        ) != 3 * len(self.operations):
            raise JointDirectCczPlanError("each CCX needs three PPMs in each phase")
        if len(self.correction_maps) != len(self.operations):
            raise JointDirectCczPlanError("each CCX needs one exact correction map")
        if self.event_to_event_reaction_edges:
            raise JointDirectCczPlanError(
                "admitted joint macro-layers cannot contain event reaction edges"
            )


@dataclass(frozen=True, slots=True)
class MeasurementUncomputeRecord:
    """Destructive-X cleanup replacing the final prefix CCX uncompute."""

    source_gate_id_replaced: str
    controls: tuple[str, str]
    measured_target: str
    last_quantum_use_source_gate_id: str
    measurement_operation_id: str
    outcome_token: str
    conditional_frame_update: str
    later_source_gate_ids: tuple[str, ...]
    frame_propagating_gate_ids: tuple[str, ...]
    later_ppm_source_gate_ids: tuple[str, ...]
    final_frame_support_upper_bound: tuple[str, ...]
    outcome_dependency_persists_to_output: bool
    release_count: int
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL

    def __post_init__(self) -> None:
        if (
            not self.source_gate_id_replaced
            or len(set(self.controls)) != 2
            or self.measured_target in self.controls
            or not self.last_quantum_use_source_gate_id
            or not self.measurement_operation_id
            or not self.outcome_token
            or not self.later_source_gate_ids
            or not self.frame_propagating_gate_ids
            or self.later_ppm_source_gate_ids
            or not self.final_frame_support_upper_bound
            or not self.outcome_dependency_persists_to_output
            or self.release_count != 1
        ):
            raise JointDirectCczPlanError("invalid measurement-uncompute record")
        expected = (
            f"CZ({self.controls[0]},{self.controls[1]})^{{{self.outcome_token}}}"
        )
        if self.conditional_frame_update != expected:
            raise JointDirectCczPlanError("measurement-uncompute correction is not canonical")


@dataclass(frozen=True, slots=True)
class WidthFiveJointCcxValidationPlan:
    """Separate width-5 candidates plus exact logical validation metadata."""

    trace_id: str
    source_trace_id: str
    source_trace_schema_version: int
    width: int
    source_ccx_operations: tuple[CcxOperation, ...]
    all_pair_certificates: tuple[CcxPairCertificate, ...]
    synthetic_overlap_certificates: tuple[CcxPairCertificate, ...]
    unitary_macro_layers: tuple[JointCcxMacroLayer, ...]
    measured_cleanup_macro_layers: tuple[JointCcxMacroLayer, ...]
    measurement_uncompute: MeasurementUncomputeRecord
    baseline_ccx_count: int
    baseline_toffoli_bearing_layers: int
    baseline_candidate_levels: int
    unitary_candidate_ccx_count: int
    unitary_candidate_macro_depth: int
    unitary_candidate_levels: int
    measured_candidate_ccx_count: int
    measured_candidate_macro_depth: int
    measured_candidate_levels: int
    complete_native_schedule: bool
    native_cycles: int | None
    runtime_seconds: float | None
    physical_qubits: int | None
    failure_probability: float | None
    schema: str = JOINT_DIRECT_CCZ_SCHEMA
    schema_version: int = JOINT_DIRECT_CCZ_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema != JOINT_DIRECT_CCZ_SCHEMA or self.schema_version != 1:
            raise JointDirectCczPlanError("unsupported joint direct-CCZ schema")
        if self.width != 5 or len(self.source_ccx_operations) != 10:
            raise JointDirectCczPlanError("this validation plan is pinned to width five")
        if len(self.all_pair_certificates) != 45:
            raise JointDirectCczPlanError("all ten source CCX pairs must be classified")
        if (self.baseline_ccx_count, self.baseline_toffoli_bearing_layers) != (10, 6):
            raise JointDirectCczPlanError("reviewed width-5 baseline changed")
        if self.baseline_candidate_levels != 12:
            raise JointDirectCczPlanError("reviewed width-5 PPM baseline changed")
        if (
            self.unitary_candidate_ccx_count,
            self.unitary_candidate_macro_depth,
            self.unitary_candidate_levels,
        ) != (10, 4, 8):
            raise JointDirectCczPlanError("unitary candidate headline changed")
        if (
            self.measured_candidate_ccx_count,
            self.measured_candidate_macro_depth,
            self.measured_candidate_levels,
        ) != (9, 3, 6):
            raise JointDirectCczPlanError("measured-cleanup candidate headline changed")
        if len(self.unitary_macro_layers) != 4 or len(
            self.measured_cleanup_macro_layers
        ) != 3:
            raise JointDirectCczPlanError("candidate macro-layer count is inconsistent")
        if self.measured_cleanup_macro_layers != self.unitary_macro_layers[:3]:
            raise JointDirectCczPlanError("measured candidate must replace only final cleanup")
        if self.complete_native_schedule or any(
            item is not None
            for item in (
                self.native_cycles,
                self.runtime_seconds,
                self.physical_qubits,
                self.failure_probability,
            )
        ):
            raise JointDirectCczPlanError("finite-backend outputs must remain null")


def _apply_ccx(operation: CcxOperation, state: dict[str, int]) -> None:
    if state[operation.controls[0]] and state[operation.controls[1]]:
        state[operation.target] ^= 1


def classify_ccx_pair(
    left: CcxOperation,
    right: CcxOperation,
) -> CcxPairCertificate:
    """Classify and exactly compare both application orders on all inputs."""

    union_support = tuple(sorted(set(left.logical_support) | set(right.logical_support)))
    shared_controls = tuple(sorted(set(left.controls) & set(right.controls)))
    shared_target = left.target if left.target == right.target else None
    left_cross = left.target in right.controls
    right_cross = right.target in left.controls
    if left_cross and right_cross:
        overlap_kind = CcxOverlapKind.BIDIRECTIONAL_TARGET_CONTROL
    elif left_cross:
        overlap_kind = CcxOverlapKind.LEFT_TARGET_RIGHT_CONTROL
    elif right_cross:
        overlap_kind = CcxOverlapKind.RIGHT_TARGET_LEFT_CONTROL
    elif shared_target is not None:
        overlap_kind = CcxOverlapKind.SHARED_TARGET
    elif shared_controls:
        overlap_kind = CcxOverlapKind.SHARED_CONTROL
    else:
        overlap_kind = CcxOverlapKind.DISJOINT

    witness: tuple[tuple[str, int], ...] | None = None
    left_then_right: tuple[tuple[str, int], ...] | None = None
    right_then_left: tuple[tuple[str, int], ...] | None = None
    for raw_bits in product((0, 1), repeat=len(union_support)):
        initial = dict(zip(union_support, raw_bits, strict=True))
        lr = dict(initial)
        rl = dict(initial)
        _apply_ccx(left, lr)
        _apply_ccx(right, lr)
        _apply_ccx(right, rl)
        _apply_ccx(left, rl)
        if lr != rl:
            witness = tuple(sorted(initial.items()))
            left_then_right = tuple(sorted(lr.items()))
            right_then_left = tuple(sorted(rl.items()))
            break
    commutes = witness is None
    predicted = not (left_cross or right_cross)
    if commutes != predicted:
        raise JointDirectCczPlanError("truth table contradicts CCX overlap theorem")
    return CcxPairCertificate(
        left_source_gate_id=left.source_gate_id,
        right_source_gate_id=right.source_gate_id,
        overlap_kind=overlap_kind,
        shared_controls=shared_controls,
        shared_target=shared_target,
        left_target_in_right_controls=left_cross,
        right_target_in_left_controls=right_cross,
        union_support=union_support,
        truth_table_rows_checked=1 << len(union_support),
        commutes=commutes,
        witness_input=witness,
        left_then_right_output=left_then_right,
        right_then_left_output=right_then_left,
    )


def _operation(gate: OopQclaGate) -> CcxOperation:
    if gate.kind is not QclaGateKind.TOFFOLI or len(gate.controls) != 2:
        raise JointDirectCczPlanError("joint candidate accepts only source Toffolis")
    return CcxOperation(
        source_gate_id=gate.gate_id,
        controls=(gate.controls[0], gate.controls[1]),
        target=gate.target,
        source_algorithmic_layer=gate.algorithmic_layer,
        source_stage=gate.stage.value,
    )


def _pair_certificates(
    operations: tuple[CcxOperation, ...],
) -> tuple[CcxPairCertificate, ...]:
    return tuple(
        classify_ccx_pair(left, right)
        for index, left in enumerate(operations)
        for right in operations[index + 1 :]
    )


def _correction_map(
    operation: CcxOperation,
    event_id: str,
) -> tuple[str, ...]:
    c0, c1 = operation.controls
    target = operation.target
    a = f"{event_id}:outcome:zz_0"
    b = f"{event_id}:outcome:zz_1"
    c = f"{event_id}:outcome:zz_2"
    x0 = f"{event_id}:outcome:x_0"
    x1 = f"{event_id}:outcome:x_1"
    x2 = f"{event_id}:outcome:x_2"
    return (
        f"CZ({c1},{target})^{{{a}}}",
        f"CZ({c0},{target})^{{{b}}}",
        f"CZ({c0},{c1})^{{{c}}}",
        f"Z({c0})^({{{x0}}} XOR ({{{b}}} AND {{{c}}}))",
        f"Z({c1})^({{{x1}}} XOR ({{{a}}} AND {{{c}}}))",
        f"X({target})^({{{x2}}} XOR ({{{a}}} AND {{{b}}}))",
    )


def _build_macro_layer(
    layer_index: int,
    operations: tuple[CcxOperation, ...],
) -> JointCcxMacroLayer:
    layer_id = f"width5-joint-ccx:T{layer_index}"
    pair_certificates = _pair_certificates(operations)
    if any(not item.commutes for item in pair_certificates):
        raise JointDirectCczPlanError("requested macro-layer contains noncommuting CCXs")
    resources: list[JointCczResourceRecord] = []
    phase_one: list[JointPpmRecord] = []
    phase_two: list[JointPpmRecord] = []
    correction_maps: list[tuple[str, tuple[str, ...]]] = []
    for event_index, operation in enumerate(operations):
        event_id = f"{layer_id}:event:{event_index}"
        resource = tuple(f"{event_id}:resource:{index}" for index in range(3))
        typed_resource = (resource[0], resource[1], resource[2])
        resources.append(
            JointCczResourceRecord(
                event_id=event_id,
                source_gate_id=operation.source_gate_id,
                resource_values=typed_resource,
            )
        )
        for index, data_value in enumerate(operation.logical_support):
            measurement_id = f"zz_{index}"
            outcome = f"{event_id}:outcome:{measurement_id}"
            phase_one.append(
                JointPpmRecord(
                    operation_id=f"{event_id}:ppm:{measurement_id}",
                    source_gate_id=operation.source_gate_id,
                    phase=1,
                    logical_support=(typed_resource[index], data_value),
                    pauli_terms=("Z", "Z"),
                    outcome_token=outcome,
                )
            )
            x_measurement_id = f"x_{index}"
            x_outcome = f"{event_id}:outcome:{x_measurement_id}"
            phase_two.append(
                JointPpmRecord(
                    operation_id=f"{event_id}:ppm:{x_measurement_id}",
                    source_gate_id=operation.source_gate_id,
                    phase=2,
                    logical_support=(typed_resource[index],),
                    pauli_terms=("X",),
                    outcome_token=x_outcome,
                )
            )
        correction_maps.append((operation.source_gate_id, _correction_map(operation, event_id)))
    all_resource_values = [
        value for resource in resources for value in resource.resource_values
    ]
    all_data_values = [
        value for operation in operations for value in operation.logical_support
    ]
    if len(all_resource_values) != len(set(all_resource_values)) or set(
        all_resource_values
    ) & set(all_data_values):
        raise JointDirectCczPlanError("joint CCZ resources are not globally fresh")
    return JointCcxMacroLayer(
        macro_layer_id=layer_id,
        operations=operations,
        pair_certificates=pair_certificates,
        common_incoming_frame="macro_layer_entry_frame",
        target_basis_change_values=tuple(sorted({item.target for item in operations})),
        resources=tuple(resources),
        phase_one_ppms=tuple(phase_one),
        phase_two_ppms=tuple(phase_two),
        correction_maps=tuple(correction_maps),
        event_to_event_reaction_edges=(),
    )


def _synthetic_certificates() -> tuple[CcxPairCertificate, ...]:
    cases = (
        (
            CcxOperation("synthetic:disjoint:left", ("a", "b"), "t", 1, "synthetic"),
            CcxOperation("synthetic:disjoint:right", ("c", "d"), "u", 1, "synthetic"),
        ),
        (
            CcxOperation("synthetic:shared-control:left", ("a", "b"), "t", 1, "synthetic"),
            CcxOperation("synthetic:shared-control:right", ("a", "c"), "u", 1, "synthetic"),
        ),
        (
            CcxOperation("synthetic:shared-target:left", ("a", "b"), "t", 1, "synthetic"),
            CcxOperation("synthetic:shared-target:right", ("c", "d"), "t", 1, "synthetic"),
        ),
        (
            CcxOperation("synthetic:left-target:left", ("a", "b"), "t", 1, "synthetic"),
            CcxOperation("synthetic:left-target:right", ("t", "c"), "u", 1, "synthetic"),
        ),
        (
            CcxOperation("synthetic:right-target:left", ("u", "a"), "t", 1, "synthetic"),
            CcxOperation("synthetic:right-target:right", ("b", "c"), "u", 1, "synthetic"),
        ),
        (
            CcxOperation("synthetic:bidirectional:left", ("a", "u"), "t", 1, "synthetic"),
            CcxOperation("synthetic:bidirectional:right", ("b", "t"), "u", 1, "synthetic"),
        ),
    )
    return tuple(classify_ccx_pair(left, right) for left, right in cases)


def _source_signature(operation: CcxOperation) -> tuple[str, tuple[str, str], str]:
    return operation.source_stage, operation.controls, operation.target


def build_width5_joint_ccx_validation_plan(
    trace: OopQclaTrace,
) -> WidthFiveJointCcxValidationPlan:
    """Build the pinned width-5 unitary and measured-cleanup candidates."""

    if trace.width != 5:
        raise JointDirectCczPlanError("joint-CCX validation requires width five")
    operations = tuple(
        _operation(gate) for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI
    )
    expected_signatures = (
        (OopQclaStage.INITIAL_GENERATE.value, ("a:0", "b:0"), "z:1"),
        (OopQclaStage.INITIAL_GENERATE.value, ("a:1", "b:1"), "z:2"),
        (OopQclaStage.INITIAL_GENERATE.value, ("a:2", "b:2"), "z:3"),
        (OopQclaStage.INITIAL_GENERATE.value, ("a:3", "b:3"), "z:4"),
        (OopQclaStage.PREFIX_PROPAGATE.value, ("b:2", "b:3"), "p:1:1"),
        (OopQclaStage.PREFIX_GENERATE.value, ("z:1", "b:1"), "z:2"),
        (OopQclaStage.PREFIX_GENERATE.value, ("z:3", "b:3"), "z:4"),
        (OopQclaStage.PREFIX_GENERATE.value, ("z:2", "p:1:1"), "z:4"),
        (OopQclaStage.PREFIX_CARRY.value, ("z:2", "b:2"), "z:3"),
        (OopQclaStage.PREFIX_UNCOMPUTE.value, ("b:2", "b:3"), "p:1:1"),
    )
    if tuple(_source_signature(item) for item in operations) != expected_signatures:
        raise JointDirectCczPlanError("width-5 source CCX signature changed")

    groups = (
        operations[0:4],
        operations[4:7],
        operations[7:9],
        operations[9:10],
    )
    unitary_layers = tuple(
        _build_macro_layer(index, group) for index, group in enumerate(groups, start=1)
    )
    cleanup_gate = operations[9]
    last_quantum_use = operations[7]
    cleanup_source_index = next(
        index for index, gate in enumerate(trace.gates) if gate.gate_id == cleanup_gate.source_gate_id
    )
    suffix_gates = trace.gates[cleanup_source_index + 1 :]
    active_frame_support = set(cleanup_gate.controls)
    propagating_gate_ids: list[str] = []
    for gate in suffix_gates:
        support = set(gate.logical_support)
        if support & active_frame_support:
            propagating_gate_ids.append(gate.gate_id)
            active_frame_support.update(support)
    later_ppm_gate_ids = tuple(
        gate.gate_id for gate in suffix_gates if gate.kind is QclaGateKind.TOFFOLI
    )
    cleanup_outcome = "width5-measured-cleanup:outcome:x"
    return WidthFiveJointCcxValidationPlan(
        trace_id=f"{trace.trace_id}:joint-direct-ccz-validation-v1",
        source_trace_id=trace.trace_id,
        source_trace_schema_version=trace.schema_version,
        width=trace.width,
        source_ccx_operations=operations,
        all_pair_certificates=_pair_certificates(operations),
        synthetic_overlap_certificates=_synthetic_certificates(),
        unitary_macro_layers=unitary_layers,
        measured_cleanup_macro_layers=unitary_layers[:3],
        measurement_uncompute=MeasurementUncomputeRecord(
            source_gate_id_replaced=cleanup_gate.source_gate_id,
            controls=cleanup_gate.controls,
            measured_target=cleanup_gate.target,
            last_quantum_use_source_gate_id=last_quantum_use.source_gate_id,
            measurement_operation_id="width5-measured-cleanup:measure-x:p:1:1",
            outcome_token=cleanup_outcome,
            conditional_frame_update=(
                f"CZ({cleanup_gate.controls[0]},{cleanup_gate.controls[1]})^"
                f"{{{cleanup_outcome}}}"
            ),
            later_source_gate_ids=tuple(gate.gate_id for gate in suffix_gates),
            frame_propagating_gate_ids=tuple(propagating_gate_ids),
            later_ppm_source_gate_ids=later_ppm_gate_ids,
            final_frame_support_upper_bound=tuple(sorted(active_frame_support)),
            outcome_dependency_persists_to_output=True,
            release_count=1,
        ),
        baseline_ccx_count=10,
        baseline_toffoli_bearing_layers=6,
        baseline_candidate_levels=12,
        unitary_candidate_ccx_count=10,
        unitary_candidate_macro_depth=4,
        unitary_candidate_levels=8,
        measured_candidate_ccx_count=9,
        measured_candidate_macro_depth=3,
        measured_candidate_levels=6,
        complete_native_schedule=False,
        native_cycles=None,
        runtime_seconds=None,
        physical_qubits=None,
        failure_probability=None,
    )


def _operation_to_data(operation: CcxOperation) -> dict[str, Any]:
    return {
        "controls": list(operation.controls),
        "source_algorithmic_layer": operation.source_algorithmic_layer,
        "source_gate_id": operation.source_gate_id,
        "source_stage": operation.source_stage,
        "target": operation.target,
    }


def _pairs_to_data(
    certificates: Iterable[CcxPairCertificate],
) -> list[dict[str, Any]]:
    return [
        {
            "commutes": item.commutes,
            "evidence_status": item.evidence_status.value,
            "left_source_gate_id": item.left_source_gate_id,
            "left_target_in_right_controls": item.left_target_in_right_controls,
            "left_then_right_output": (
                dict(item.left_then_right_output)
                if item.left_then_right_output is not None
                else None
            ),
            "overlap_kind": item.overlap_kind.value,
            "right_source_gate_id": item.right_source_gate_id,
            "right_target_in_left_controls": item.right_target_in_left_controls,
            "right_then_left_output": (
                dict(item.right_then_left_output)
                if item.right_then_left_output is not None
                else None
            ),
            "shared_controls": list(item.shared_controls),
            "shared_target": item.shared_target,
            "truth_table_rows_checked": item.truth_table_rows_checked,
            "union_support": list(item.union_support),
            "witness_input": (
                dict(item.witness_input) if item.witness_input is not None else None
            ),
        }
        for item in certificates
    ]


def _ppm_to_data(record: JointPpmRecord) -> dict[str, Any]:
    return {
        "logical_support": list(record.logical_support),
        "operation_id": record.operation_id,
        "outcome_token": record.outcome_token,
        "pauli_terms": list(record.pauli_terms),
        "phase": record.phase,
        "source_gate_id": record.source_gate_id,
    }


def _macro_layer_to_data(layer: JointCcxMacroLayer) -> dict[str, Any]:
    return {
        "common_incoming_frame": layer.common_incoming_frame,
        "correction_maps": [
            {"expressions": list(expressions), "source_gate_id": source_gate_id}
            for source_gate_id, expressions in layer.correction_maps
        ],
        "event_to_event_reaction_edges": [list(item) for item in layer.event_to_event_reaction_edges],
        "evidence_status": layer.evidence_status.value,
        "macro_layer_id": layer.macro_layer_id,
        "operations": [_operation_to_data(item) for item in layer.operations],
        "pair_certificates": _pairs_to_data(layer.pair_certificates),
        "phase_one_ppms": [_ppm_to_data(item) for item in layer.phase_one_ppms],
        "phase_two_ppms": [_ppm_to_data(item) for item in layer.phase_two_ppms],
        "resources": [
            {
                "consumed": item.consumed,
                "event_id": item.event_id,
                "resource_values": list(item.resource_values),
                "source_gate_id": item.source_gate_id,
            }
            for item in layer.resources
        ],
        "target_basis_change_values": list(layer.target_basis_change_values),
    }


def width5_joint_ccx_validation_plan_to_data(
    plan: WidthFiveJointCcxValidationPlan,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible validation-plan data."""

    cleanup = plan.measurement_uncompute
    return {
        "all_pair_certificates": _pairs_to_data(plan.all_pair_certificates),
        "baseline": {
            "candidate_levels": plan.baseline_candidate_levels,
            "ccx_count": plan.baseline_ccx_count,
            "toffoli_bearing_layers": plan.baseline_toffoli_bearing_layers,
        },
        "complete_native_schedule": plan.complete_native_schedule,
        "finite_outputs": {
            "failure_probability": plan.failure_probability,
            "native_cycles": plan.native_cycles,
            "physical_qubits": plan.physical_qubits,
            "runtime_seconds": plan.runtime_seconds,
        },
        "measured_cleanup_candidate": {
            "candidate_levels": plan.measured_candidate_levels,
            "candidate_level_coordinate": "two_phase_macro_envelope_not_schedule_or_time",
            "candidate_level_status": "CHECK_PENDING_T-20260906-003",
            "ccx_count": plan.measured_candidate_ccx_count,
            "macro_depth": plan.measured_candidate_macro_depth,
            "macro_layers": [
                _macro_layer_to_data(item) for item in plan.measured_cleanup_macro_layers
            ],
            "measurement_uncompute": {
                "conditional_frame_update": cleanup.conditional_frame_update,
                "controls": list(cleanup.controls),
                "evidence_status": cleanup.evidence_status.value,
                "final_frame_support_upper_bound": list(
                    cleanup.final_frame_support_upper_bound
                ),
                "frame_propagating_gate_ids": list(cleanup.frame_propagating_gate_ids),
                "last_quantum_use_source_gate_id": cleanup.last_quantum_use_source_gate_id,
                "later_ppm_source_gate_ids": list(cleanup.later_ppm_source_gate_ids),
                "later_source_gate_ids": list(cleanup.later_source_gate_ids),
                "measured_target": cleanup.measured_target,
                "measurement_operation_id": cleanup.measurement_operation_id,
                "outcome_token": cleanup.outcome_token,
                "outcome_dependency_persists_to_output": (
                    cleanup.outcome_dependency_persists_to_output
                ),
                "release_count": cleanup.release_count,
                "source_gate_id_replaced": cleanup.source_gate_id_replaced,
            },
        },
        "outcome_bit_convention": "0 denotes +1 eigenvalue; 1 denotes -1 eigenvalue",
        "schema": plan.schema,
        "schema_version": plan.schema_version,
        "source_ccx_operations": [_operation_to_data(item) for item in plan.source_ccx_operations],
        "source_trace_id": plan.source_trace_id,
        "source_trace_schema_version": plan.source_trace_schema_version,
        "synthetic_overlap_certificates": _pairs_to_data(plan.synthetic_overlap_certificates),
        "trace_id": plan.trace_id,
        "unitary_candidate": {
            "candidate_levels": plan.unitary_candidate_levels,
            "candidate_level_coordinate": "two_phase_macro_envelope_not_schedule_or_time",
            "candidate_level_status": "CHECK_PENDING_T-20260906-003",
            "ccx_count": plan.unitary_candidate_ccx_count,
            "macro_depth": plan.unitary_candidate_macro_depth,
            "macro_layers": [_macro_layer_to_data(item) for item in plan.unitary_macro_layers],
        },
        "width": plan.width,
    }


def dumps_width5_joint_ccx_validation_plan(
    plan: WidthFiveJointCcxValidationPlan,
) -> str:
    """Serialize the width-5 validation plan canonically."""

    return json.dumps(
        width5_joint_ccx_validation_plan_to_data(plan),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
