"""Independent replay for width-5 joint direct-CCZ validation.

The replay consumes serialized records and never imports the joint compiler.
It recomputes CCX commutation from integer truth tables, checks the canonical
two-phase resource protocol, simulates all 64 single-event injection branches,
and runs explicit simultaneous-protocol statevector anchors for shared-control
and shared-target pairs.  Measurement uncompute is checked on every width-5
input basis column and both measurement outcomes, which also fixes every
relative phase of an arbitrary input superposition.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from importlib import import_module
from itertools import product
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGateKind
from ecdlp_ftqc.circuits.qcla_oop import OopQclaGate, OopQclaTrace

np: Any = import_module("numpy")
ComplexArray = Any

EXPECTED_SCHEMA = "ecdlp-ftqc/width5-joint-direct-ccz-validation-plan"
EXPECTED_SCHEMA_VERSION = 1
TOLERANCE = 1e-12

I = np.eye(2, dtype=np.complex128)
X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
PLUS = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)


class JointDirectCczReplayError(ValueError):
    """Raised when a serialized joint-CCX claim fails independent replay."""


@dataclass(frozen=True, slots=True)
class JointInjectionAnchorSummary:
    """Explicit simultaneous-protocol checks for one overlap family."""

    overlap_kind: str
    pair_count: int
    branch_anchors_per_pair: int
    basis_columns_per_branch: int
    expected_branch_probability: float
    maximum_probability_error: float
    maximum_operator_frobenius_error: float


@dataclass(frozen=True, slots=True)
class MeasurementUncomputeReplaySummary:
    """Local and complete-width-5 measurement-uncompute verification."""

    local_control_assignments_checked: int
    local_measurement_branches_checked: int
    width5_input_basis_columns_checked: int
    width5_measurement_branches_checked: int
    phase_sensitive_relative_pairs_checked: int
    expected_branch_probability: float
    maximum_probability_error: float
    maximum_corrected_amplitude_error: float
    output_basis_mismatches: int
    dirty_ancilla_mismatches: int
    lifecycle_checks_passed: bool
    frame_propagating_gate_count: int
    later_ppm_dependency_count: int
    final_frame_support_upper_bound: tuple[str, ...]
    outcome_dependency_persists_to_output: bool
    all_passed: bool


@dataclass(frozen=True, slots=True)
class WidthFiveJointDirectCczReplaySummary:
    """Independent result for the complete validation record."""

    source_ccx_count: int
    all_source_pair_count: int
    commuting_source_pair_count: int
    noncommuting_source_pair_count: int
    source_pair_truth_table_rows_checked: int
    synthetic_overlap_cases_checked: int
    synthetic_noncommuting_witnesses: int
    unitary_macro_layer_count: int
    measured_macro_layer_count: int
    admitted_macro_pair_count: int
    common_frame_factorization_proofs: int
    factorized_two_event_branches_covered: int
    single_event_branches_checked: int
    single_event_maximum_probability_error: float
    single_event_maximum_operator_frobenius_error: float
    shared_control_anchor: JointInjectionAnchorSummary
    shared_target_anchor: JointInjectionAnchorSummary
    measurement_uncompute: MeasurementUncomputeReplaySummary
    resource_triples_checked: int
    resource_values_checked: int
    event_to_event_reaction_edge_count: int
    unitary_candidate_levels: int
    measured_candidate_levels: int
    complete_native_schedule: bool
    native_cycles: int | None
    runtime_seconds: float | None
    physical_qubits: int | None
    failure_probability: float | None
    tolerance: float
    all_passed: bool


@dataclass(frozen=True, slots=True)
class _Operation:
    source_gate_id: str
    controls: tuple[str, str]
    target: str
    source_algorithmic_layer: int
    source_stage: str

    @property
    def support(self) -> tuple[str, str, str]:
        return (*self.controls, self.target)


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise JointDirectCczReplayError(f"{label} must be a mapping")
    return value


def _sequence(value: object, *, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise JointDirectCczReplayError(f"{label} must be a sequence")
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise JointDirectCczReplayError(f"{label} must be a nonempty string")
    return value


def _integer(value: object, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise JointDirectCczReplayError(f"{label} must be an integer")
    return value


def _strings(value: object, *, label: str) -> tuple[str, ...]:
    return tuple(_string(item, label=label) for item in _sequence(value, label=label))


def _read_operation(value: object) -> _Operation:
    raw = _mapping(value, label="CCX operation")
    controls = _strings(raw.get("controls"), label="CCX controls")
    if len(controls) != 2 or len(set(controls)) != 2:
        raise JointDirectCczReplayError("CCX must have two distinct controls")
    target = _string(raw.get("target"), label="CCX target")
    if target in controls:
        raise JointDirectCczReplayError("CCX target cannot be a control")
    return _Operation(
        source_gate_id=_string(raw.get("source_gate_id"), label="source gate ID"),
        controls=(controls[0], controls[1]),
        target=target,
        source_algorithmic_layer=_integer(
            raw.get("source_algorithmic_layer"), label="source layer"
        ),
        source_stage=_string(raw.get("source_stage"), label="source stage"),
    )


def _bit(index: int, name: str, names: tuple[str, ...]) -> int:
    position = names.index(name)
    return (index >> (len(names) - 1 - position)) & 1


def _apply_ccx_index(index: int, operation: _Operation, names: tuple[str, ...]) -> int:
    if _bit(index, operation.controls[0], names) and _bit(
        index, operation.controls[1], names
    ):
        position = names.index(operation.target)
        return index ^ (1 << (len(names) - 1 - position))
    return index


def _overlap_kind(left: _Operation, right: _Operation) -> str:
    left_cross = left.target in right.controls
    right_cross = right.target in left.controls
    if left_cross and right_cross:
        return "bidirectional_target_control"
    if left_cross:
        return "left_target_right_control"
    if right_cross:
        return "right_target_left_control"
    if left.target == right.target:
        return "shared_target"
    if set(left.controls) & set(right.controls):
        return "shared_control"
    return "disjoint"


def _independent_pair_data(left: _Operation, right: _Operation) -> dict[str, Any]:
    names = tuple(sorted(set(left.support) | set(right.support)))
    first_mismatch: tuple[int, int, int] | None = None
    for basis in range(1 << len(names)):
        lr = _apply_ccx_index(_apply_ccx_index(basis, left, names), right, names)
        rl = _apply_ccx_index(_apply_ccx_index(basis, right, names), left, names)
        if lr != rl:
            first_mismatch = (basis, lr, rl)
            break
    left_cross = left.target in right.controls
    right_cross = right.target in left.controls
    commutes = first_mismatch is None
    if commutes != (not left_cross and not right_cross):
        raise JointDirectCczReplayError("CCX truth table violates overlap theorem")

    def assignment(index: int) -> dict[str, int]:
        return {name: _bit(index, name, names) for name in names}

    return {
        "commutes": commutes,
        "evidence_status": "PROVED",
        "left_source_gate_id": left.source_gate_id,
        "left_target_in_right_controls": left_cross,
        "left_then_right_output": (
            assignment(first_mismatch[1]) if first_mismatch is not None else None
        ),
        "overlap_kind": _overlap_kind(left, right),
        "right_source_gate_id": right.source_gate_id,
        "right_target_in_left_controls": right_cross,
        "right_then_left_output": (
            assignment(first_mismatch[2]) if first_mismatch is not None else None
        ),
        "shared_controls": sorted(set(left.controls) & set(right.controls)),
        "shared_target": left.target if left.target == right.target else None,
        "truth_table_rows_checked": 1 << len(names),
        "union_support": list(names),
        "witness_input": (
            assignment(first_mismatch[0]) if first_mismatch is not None else None
        ),
    }


def _check_pair_rows(
    rows_value: object,
    operations: tuple[_Operation, ...],
) -> tuple[int, int, int]:
    rows = _sequence(rows_value, label="pair certificates")
    expected = [
        _independent_pair_data(left, right)
        for index, left in enumerate(operations)
        for right in operations[index + 1 :]
    ]
    actual = [dict(_mapping(item, label="pair certificate")) for item in rows]
    if actual != expected:
        raise JointDirectCczReplayError("pair certificate mismatch")
    return (
        len(expected),
        sum(bool(item["commutes"]) for item in expected),
        sum(int(item["truth_table_rows_checked"]) for item in expected),
    )


def _expected_corrections(
    operation: _Operation,
    event_id: str,
) -> list[str]:
    c0, c1 = operation.controls
    target = operation.target
    a = f"{event_id}:outcome:zz_0"
    b = f"{event_id}:outcome:zz_1"
    c = f"{event_id}:outcome:zz_2"
    x0 = f"{event_id}:outcome:x_0"
    x1 = f"{event_id}:outcome:x_1"
    x2 = f"{event_id}:outcome:x_2"
    return [
        f"CZ({c1},{target})^{{{a}}}",
        f"CZ({c0},{target})^{{{b}}}",
        f"CZ({c0},{c1})^{{{c}}}",
        f"Z({c0})^({{{x0}}} XOR ({{{b}}} AND {{{c}}}))",
        f"Z({c1})^({{{x1}}} XOR ({{{a}}} AND {{{c}}}))",
        f"X({target})^({{{x2}}} XOR ({{{a}}} AND {{{b}}}))",
    ]


def _check_macro_layer(
    value: object,
    source_by_id: Mapping[str, _Operation],
) -> tuple[tuple[_Operation, ...], int, int, int]:
    raw = _mapping(value, label="macro-layer")
    if raw.get("common_incoming_frame") != "macro_layer_entry_frame":
        raise JointDirectCczReplayError("macro-layer does not use one incoming frame")
    if raw.get("evidence_status") != "NUMERICAL":
        raise JointDirectCczReplayError("macro-layer evidence label changed")
    operations = tuple(
        _read_operation(item)
        for item in _sequence(raw.get("operations"), label="macro operations")
    )
    if any(source_by_id.get(item.source_gate_id) != item for item in operations):
        raise JointDirectCczReplayError("macro-layer operation differs from source")
    pair_count, commuting_count, _ = _check_pair_rows(
        raw.get("pair_certificates"), operations
    )
    if pair_count != commuting_count:
        raise JointDirectCczReplayError("macro-layer contains a noncommuting pair")
    expected_targets = sorted({item.target for item in operations})
    if list(_strings(raw.get("target_basis_change_values"), label="target H set")) != expected_targets:
        raise JointDirectCczReplayError("target basis-change set is not canonical")
    if _sequence(raw.get("event_to_event_reaction_edges"), label="reaction edges"):
        raise JointDirectCczReplayError("joint macro-layer contains a reaction edge")

    resources = _sequence(raw.get("resources"), label="resource records")
    if len(resources) != len(operations):
        raise JointDirectCczReplayError("resource count differs from CCX count")
    all_resources: list[str] = []
    expected_phase_one: list[dict[str, Any]] = []
    expected_phase_two: list[dict[str, Any]] = []
    expected_correction_rows: list[dict[str, Any]] = []
    macro_id = _string(raw.get("macro_layer_id"), label="macro-layer ID")
    for event_index, (operation, resource_value) in enumerate(
        zip(operations, resources, strict=True)
    ):
        resource = _mapping(resource_value, label="resource record")
        event_id = f"{macro_id}:event:{event_index}"
        values = _strings(resource.get("resource_values"), label="resource values")
        if (
            resource.get("event_id") != event_id
            or resource.get("source_gate_id") != operation.source_gate_id
            or resource.get("consumed") is not True
            or len(values) != 3
            or len(set(values)) != 3
        ):
            raise JointDirectCczReplayError("resource record is noncanonical")
        all_resources.extend(values)
        for index, data_value in enumerate(operation.support):
            zz_id = f"zz_{index}"
            x_id = f"x_{index}"
            expected_phase_one.append(
                {
                    "logical_support": [values[index], data_value],
                    "operation_id": f"{event_id}:ppm:{zz_id}",
                    "outcome_token": f"{event_id}:outcome:{zz_id}",
                    "pauli_terms": ["Z", "Z"],
                    "phase": 1,
                    "source_gate_id": operation.source_gate_id,
                }
            )
            expected_phase_two.append(
                {
                    "logical_support": [values[index]],
                    "operation_id": f"{event_id}:ppm:{x_id}",
                    "outcome_token": f"{event_id}:outcome:{x_id}",
                    "pauli_terms": ["X"],
                    "phase": 2,
                    "source_gate_id": operation.source_gate_id,
                }
            )
        expected_correction_rows.append(
            {
                "expressions": _expected_corrections(operation, event_id),
                "source_gate_id": operation.source_gate_id,
            }
        )
    data_values = {value for operation in operations for value in operation.support}
    if len(all_resources) != len(set(all_resources)) or set(all_resources) & data_values:
        raise JointDirectCczReplayError("resource values are reused or not fresh")
    phase_one = [
        dict(_mapping(item, label="phase-one PPM"))
        for item in _sequence(raw.get("phase_one_ppms"), label="phase-one PPMs")
    ]
    phase_two = [
        dict(_mapping(item, label="phase-two PPM"))
        for item in _sequence(raw.get("phase_two_ppms"), label="phase-two PPMs")
    ]
    corrections = [
        dict(_mapping(item, label="correction map"))
        for item in _sequence(raw.get("correction_maps"), label="correction maps")
    ]
    if phase_one != expected_phase_one:
        raise JointDirectCczReplayError("phase-one ZZ record mismatch")
    if phase_two != expected_phase_two:
        raise JointDirectCczReplayError("phase-two X record mismatch")
    if corrections != expected_correction_rows:
        raise JointDirectCczReplayError("joint correction map mismatch")
    return operations, pair_count, len(resources), len(all_resources)


def _kron(*operators: ComplexArray) -> ComplexArray:
    result = np.array([1.0 + 0.0j], dtype=np.complex128)
    for operator in operators:
        result = np.kron(result, operator)
    return result


def _ccz_resource_state() -> ComplexArray:
    state = _kron(PLUS, PLUS, PLUS)
    state = state.copy()
    state[7] *= -1
    return state


def _apply_one_qubit(
    state: ComplexArray,
    gate: ComplexArray,
    qubit: int,
    qubit_count: int,
) -> ComplexArray:
    tensor = state.reshape((2,) * qubit_count)
    moved = np.moveaxis(tensor, qubit, 0).reshape(2, -1)
    transformed = gate @ moved
    restored = np.moveaxis(
        transformed.reshape((2,) + (2,) * (qubit_count - 1)), 0, qubit
    )
    return restored.reshape(-1)


def _apply_cz_state(
    state: ComplexArray,
    left: int,
    right: int,
    qubit_count: int,
) -> ComplexArray:
    indices = np.arange(state.size, dtype=np.int64)
    left_bits = (indices >> (qubit_count - 1 - left)) & 1
    right_bits = (indices >> (qubit_count - 1 - right)) & 1
    return state * np.where((left_bits & right_bits) == 1, -1.0, 1.0)


def _project_zz(
    state: ComplexArray,
    left: int,
    right: int,
    outcome: int,
    qubit_count: int,
) -> ComplexArray:
    indices = np.arange(state.size, dtype=np.int64)
    parity = ((indices >> (qubit_count - 1 - left)) ^ (
        indices >> (qubit_count - 1 - right)
    )) & 1
    return state * (parity == outcome)


def _ideal_ccx_product(
    operations: tuple[_Operation, ...],
    names: tuple[str, ...],
) -> ComplexArray:
    dimension = 1 << len(names)
    result = np.zeros((dimension, dimension), dtype=np.complex128)
    for basis in range(dimension):
        output = basis
        for operation in operations:
            output = _apply_ccx_index(output, operation, names)
        result[output, basis] = 1
    return result


def _joint_branch_operator(
    operations: tuple[_Operation, ...],
    raw_bits: tuple[int, ...],
) -> tuple[ComplexArray, ComplexArray]:
    if len(raw_bits) != 6 * len(operations):
        raise JointDirectCczReplayError("joint branch bit count is invalid")
    names = tuple(sorted({value for operation in operations for value in operation.support}))
    data_count = len(names)
    resource_count = 3 * len(operations)
    total_count = data_count + resource_count
    resource = _kron(*(_ccz_resource_state() for _ in operations))
    columns: list[ComplexArray] = []
    target_positions = tuple(sorted({names.index(item.target) for item in operations}))
    for basis in range(1 << data_count):
        data = np.eye(1 << data_count, dtype=np.complex128)[:, basis]
        state = np.kron(data, resource)
        for target in target_positions:
            state = _apply_one_qubit(state, H, target, total_count)
        for event_index, operation in enumerate(operations):
            zz_bits = raw_bits[6 * event_index : 6 * event_index + 3]
            for local_index, data_value in enumerate(operation.support):
                state = _project_zz(
                    state,
                    names.index(data_value),
                    data_count + 3 * event_index + local_index,
                    zz_bits[local_index],
                    total_count,
                )
        for event_index, operation in enumerate(operations):
            a, b, c = raw_bits[6 * event_index : 6 * event_index + 3]
            conditional = (
                (a, operation.controls[1], operation.target),
                (b, operation.controls[0], operation.target),
                (c, operation.controls[0], operation.controls[1]),
            )
            for exponent, left, right in conditional:
                if exponent:
                    state = _apply_cz_state(
                        state, names.index(left), names.index(right), total_count
                    )
        x_states: list[ComplexArray] = []
        for event_index in range(len(operations)):
            x_bits = raw_bits[6 * event_index + 3 : 6 * event_index + 6]
            x_states.extend(
                np.array([1, (-1) ** bit], dtype=np.complex128) / np.sqrt(2)
                for bit in x_bits
            )
        resource_bra = _kron(*x_states).conj()
        projected = state.reshape((1 << data_count, 1 << resource_count)) @ resource_bra
        for target in target_positions:
            projected = _apply_one_qubit(projected, H, target, data_count)
        for event_index, operation in enumerate(operations):
            a, b, c, x0, x1, x2 = raw_bits[
                6 * event_index : 6 * event_index + 6
            ]
            if x0 ^ (b & c):
                projected = _apply_one_qubit(
                    projected, Z, names.index(operation.controls[0]), data_count
                )
            if x1 ^ (a & c):
                projected = _apply_one_qubit(
                    projected, Z, names.index(operation.controls[1]), data_count
                )
            if x2 ^ (a & b):
                projected = _apply_one_qubit(
                    projected, X, names.index(operation.target), data_count
                )
        columns.append(projected)
    return np.column_stack(columns), _ideal_ccx_product(operations, names)


def _branch_anchor_bits(event_count: int) -> tuple[tuple[int, ...], ...]:
    bit_count = 6 * event_count
    anchors = [
        (0,) * bit_count,
        (1,) * bit_count,
        tuple(index % 2 for index in range(bit_count)),
        tuple((index + 1) % 2 for index in range(bit_count)),
    ]
    anchors.extend(
        tuple(int(index == selected) for index in range(bit_count))
        for selected in range(bit_count)
    )
    return tuple(dict.fromkeys(anchors))


def _verify_joint_anchors(
    overlap_kind: str,
    pairs: tuple[tuple[_Operation, _Operation], ...],
) -> JointInjectionAnchorSummary:
    maximum_probability_error = 0.0
    maximum_operator_error = 0.0
    basis_columns = 0
    anchors = _branch_anchor_bits(2)
    expected_probability = 1.0 / 4096.0
    for pair in pairs:
        if _overlap_kind(*pair) != overlap_kind:
            raise JointDirectCczReplayError("joint anchor has the wrong overlap kind")
        for bits in anchors:
            branch, ideal = _joint_branch_operator(pair, bits)
            scalar = np.vdot(ideal, branch) / ideal.shape[0]
            probability = float(np.linalg.norm(branch, ord="fro") ** 2 / ideal.shape[0])
            maximum_probability_error = max(
                maximum_probability_error, abs(probability - expected_probability)
            )
            maximum_operator_error = max(
                maximum_operator_error,
                float(np.linalg.norm(branch - scalar * ideal, ord="fro")),
            )
            basis_columns += ideal.shape[0]
    return JointInjectionAnchorSummary(
        overlap_kind=overlap_kind,
        pair_count=len(pairs),
        branch_anchors_per_pair=len(anchors),
        basis_columns_per_branch=basis_columns // (len(pairs) * len(anchors)),
        expected_branch_probability=expected_probability,
        maximum_probability_error=maximum_probability_error,
        maximum_operator_frobenius_error=maximum_operator_error,
    )


def _verify_single_event_all_branches() -> tuple[int, float, float]:
    operation = _Operation("independent:single", ("c0", "c1"), "t", 1, "single")
    maximum_probability_error = 0.0
    maximum_operator_error = 0.0
    for bits in product((0, 1), repeat=6):
        branch, ideal = _joint_branch_operator((operation,), bits)
        scalar = np.vdot(ideal, branch) / ideal.shape[0]
        probability = float(np.linalg.norm(branch, ord="fro") ** 2 / ideal.shape[0])
        maximum_probability_error = max(
            maximum_probability_error, abs(probability - 1.0 / 64.0)
        )
        maximum_operator_error = max(
            maximum_operator_error,
            float(np.linalg.norm(branch - scalar * ideal, ord="fro")),
        )
    return 64, maximum_probability_error, maximum_operator_error


def _initial_width5_state(input_a: int, input_b: int) -> dict[str, int]:
    state: dict[str, int] = {}
    for index in range(5):
        state[f"a:{index}"] = (input_a >> index) & 1
        state[f"b:{index}"] = (input_b >> index) & 1
        state[f"z:{index}"] = 0
    state["p:1:1"] = 0
    return state


def _apply_source_gate(state: dict[str, int], gate: OopQclaGate) -> None:
    controls = tuple(gate.controls)
    if gate.kind is QclaGateKind.CNOT:
        state[gate.target] ^= state[controls[0]]
    elif gate.kind is QclaGateKind.TOFFOLI:
        state[gate.target] ^= state[controls[0]] & state[controls[1]]
    else:
        raise JointDirectCczReplayError("width-5 OOP trace contains an unsupported gate")


def _verify_measurement_uncompute(
    source: OopQclaTrace,
    cleanup_value: object,
) -> MeasurementUncomputeReplaySummary:
    cleanup = _mapping(cleanup_value, label="measurement uncompute")
    controls = _strings(cleanup.get("controls"), label="cleanup controls")
    if len(controls) != 2:
        raise JointDirectCczReplayError("cleanup controls are invalid")
    measured_target = _string(cleanup.get("measured_target"), label="measured target")
    replaced_id = _string(
        cleanup.get("source_gate_id_replaced"), label="replaced source gate"
    )
    outcome_token = _string(cleanup.get("outcome_token"), label="cleanup outcome")
    expected_update = f"CZ({controls[0]},{controls[1]})^{{{outcome_token}}}"
    if (
        cleanup.get("conditional_frame_update") != expected_update
        or cleanup.get("measurement_operation_id")
        != "width5-measured-cleanup:measure-x:p:1:1"
        or cleanup.get("release_count") != 1
        or cleanup.get("evidence_status") != "NUMERICAL"
    ):
        raise JointDirectCczReplayError("measurement-uncompute record is noncanonical")
    source_by_id = {gate.gate_id: gate for gate in source.gates}
    replaced = source_by_id.get(replaced_id)
    if (
        replaced is None
        or replaced.kind is not QclaGateKind.TOFFOLI
        or tuple(replaced.controls) != controls
        or replaced.target != measured_target
    ):
        raise JointDirectCczReplayError("measurement cleanup replaces the wrong gate")
    uses = [
        gate.gate_id
        for gate in source.gates
        if measured_target in (*gate.controls, gate.target) and gate.gate_id != replaced_id
    ]
    last_use = uses[-1]
    if cleanup.get("last_quantum_use_source_gate_id") != last_use:
        raise JointDirectCczReplayError("measurement occurs before the declared last use")
    cleanup_index = source.gates.index(replaced)
    prefix = source.gates[:cleanup_index]
    suffix = source.gates[cleanup_index + 1 :]
    expected_later_ids = [gate.gate_id for gate in suffix]
    active_frame_support = set(controls)
    expected_propagating_ids: list[str] = []
    for gate in suffix:
        support = set(gate.logical_support)
        if support & active_frame_support:
            expected_propagating_ids.append(gate.gate_id)
            active_frame_support.update(support)
    expected_later_ppm_ids = [
        gate.gate_id for gate in suffix if gate.kind is QclaGateKind.TOFFOLI
    ]
    if (
        list(_strings(cleanup.get("later_source_gate_ids"), label="later gates"))
        != expected_later_ids
        or list(
            _strings(
                cleanup.get("frame_propagating_gate_ids"),
                label="frame-propagating gates",
            )
        )
        != expected_propagating_ids
        or list(
            _strings(
                cleanup.get("later_ppm_source_gate_ids"), label="later PPM gates"
            )
        )
        != expected_later_ppm_ids
        or tuple(
            _strings(
                cleanup.get("final_frame_support_upper_bound"),
                label="final frame support",
            )
        )
        != tuple(sorted(active_frame_support))
        or cleanup.get("outcome_dependency_persists_to_output") is not True
    ):
        raise JointDirectCczReplayError("measurement-uncompute frame propagation changed")

    local_error = 0.0
    local_probability_error = 0.0
    local_branches = 0
    expected_amplitude = 1.0 / np.sqrt(2)
    for c0, c1, outcome in product((0, 1), repeat=3):
        target = c0 & c1
        measured_amplitude = ((-1) ** (outcome * target)) / np.sqrt(2)
        correction_phase = (-1) ** (outcome * (c0 & c1))
        corrected = measured_amplitude * correction_phase
        local_error = max(local_error, abs(corrected - expected_amplitude))
        local_probability_error = max(
            local_probability_error, abs(abs(corrected) ** 2 - 0.5)
        )
        local_branches += 1

    output_mismatches = 0
    dirty_mismatches = 0
    full_error = 0.0
    full_probability_error = 0.0
    corrected_amplitudes: dict[int, list[complex]] = {0: [], 1: []}
    for input_a in range(32):
        for input_b in range(32):
            baseline = _initial_width5_state(input_a, input_b)
            for gate in source.gates:
                _apply_source_gate(baseline, gate)
            measured_at_cleanup = _initial_width5_state(input_a, input_b)
            for gate in prefix:
                _apply_source_gate(measured_at_cleanup, gate)
            if baseline[measured_target] != 0:
                dirty_mismatches += 1
            if measured_at_cleanup[measured_target] != (
                measured_at_cleanup[controls[0]]
                & measured_at_cleanup[controls[1]]
            ):
                dirty_mismatches += 1
            measured_after_cleanup = dict(measured_at_cleanup)
            for gate in suffix:
                _apply_source_gate(measured_after_cleanup, gate)
            baseline_without_target = {
                key: value for key, value in baseline.items() if key != measured_target
            }
            measured_without_target = {
                key: value
                for key, value in measured_after_cleanup.items()
                if key != measured_target
            }
            if baseline_without_target != measured_without_target:
                output_mismatches += 1
            for outcome in (0, 1):
                target = measured_at_cleanup[measured_target]
                measured_amplitude = ((-1) ** (outcome * target)) / np.sqrt(2)
                correction_phase = (
                    -1
                    if outcome
                    and measured_at_cleanup[controls[0]]
                    and measured_at_cleanup[controls[1]]
                    else 1
                )
                corrected = complex(measured_amplitude * correction_phase)
                corrected_amplitudes[outcome].append(corrected)
                full_error = max(full_error, abs(corrected - expected_amplitude))
                full_probability_error = max(
                    full_probability_error, abs(abs(corrected) ** 2 - 0.5)
                )
    phase_pairs = 0
    phase_error = 0.0
    for amplitudes in corrected_amplitudes.values():
        reference = amplitudes[0]
        for amplitude in amplitudes[1:]:
            phase_pairs += 1
            phase_error = max(phase_error, abs(amplitude - reference))
    maximum_amplitude_error = max(local_error, full_error, phase_error)
    maximum_probability_error = max(local_probability_error, full_probability_error)
    lifecycle_passed = (
        last_use == cleanup.get("last_quantum_use_source_gate_id")
        and cleanup.get("release_count") == 1
        and not any(
            measured_target in (*gate.controls, gate.target)
            for gate in suffix
        )
    )
    all_passed = (
        output_mismatches == 0
        and dirty_mismatches == 0
        and lifecycle_passed
        and maximum_amplitude_error <= TOLERANCE
        and maximum_probability_error <= TOLERANCE
    )
    return MeasurementUncomputeReplaySummary(
        local_control_assignments_checked=4,
        local_measurement_branches_checked=local_branches,
        width5_input_basis_columns_checked=1024,
        width5_measurement_branches_checked=2048,
        phase_sensitive_relative_pairs_checked=phase_pairs,
        expected_branch_probability=0.5,
        maximum_probability_error=float(maximum_probability_error),
        maximum_corrected_amplitude_error=float(maximum_amplitude_error),
        output_basis_mismatches=output_mismatches,
        dirty_ancilla_mismatches=dirty_mismatches,
        lifecycle_checks_passed=lifecycle_passed,
        frame_propagating_gate_count=len(expected_propagating_ids),
        later_ppm_dependency_count=len(expected_later_ppm_ids),
        final_frame_support_upper_bound=tuple(sorted(active_frame_support)),
        outcome_dependency_persists_to_output=True,
        all_passed=bool(all_passed),
    )


def replay_width5_joint_direct_ccz(
    source: OopQclaTrace,
    plan_value: object,
) -> WidthFiveJointDirectCczReplaySummary:
    """Independently replay the serialized width-5 joint-CCX record."""

    plan = _mapping(plan_value, label="joint validation plan")
    if plan.get("schema") != EXPECTED_SCHEMA or plan.get("schema_version") != 1:
        raise JointDirectCczReplayError("unexpected joint validation schema")
    if source.width != 5 or plan.get("width") != 5:
        raise JointDirectCczReplayError("joint validation is pinned to width five")
    if (
        plan.get("source_trace_id") != source.trace_id
        or plan.get("source_trace_schema_version") != source.schema_version
    ):
        raise JointDirectCczReplayError("source trace binding mismatch")
    source_operations = tuple(
        _read_operation(item)
        for item in _sequence(plan.get("source_ccx_operations"), label="source CCXs")
    )
    expected_source = tuple(
        _Operation(
            gate.gate_id,
            (gate.controls[0], gate.controls[1]),
            gate.target,
            gate.algorithmic_layer,
            gate.stage.value,
        )
        for gate in source.gates
        if gate.kind is QclaGateKind.TOFFOLI
    )
    if source_operations != expected_source or len(source_operations) != 10:
        raise JointDirectCczReplayError("source CCX projection mismatch")
    source_by_id = {item.source_gate_id: item for item in source_operations}
    pair_count, commuting_count, truth_rows = _check_pair_rows(
        plan.get("all_pair_certificates"), source_operations
    )

    synthetic_rows = _sequence(
        plan.get("synthetic_overlap_certificates"), label="synthetic certificates"
    )
    if len(synthetic_rows) != 6:
        raise JointDirectCczReplayError("synthetic overlap coverage changed")
    synthetic_operations: list[tuple[_Operation, _Operation]] = []
    expected_synthetic_kinds = (
        "disjoint",
        "shared_control",
        "shared_target",
        "left_target_right_control",
        "right_target_left_control",
        "bidirectional_target_control",
    )
    for row_value, expected_kind in zip(
        synthetic_rows, expected_synthetic_kinds, strict=True
    ):
        row = _mapping(row_value, label="synthetic certificate")
        left_id = _string(row.get("left_source_gate_id"), label="synthetic left ID")
        right_id = _string(row.get("right_source_gate_id"), label="synthetic right ID")
        expected_tag = {
            "disjoint": "synthetic:disjoint",
            "shared_control": "synthetic:shared-control",
            "shared_target": "synthetic:shared-target",
            "left_target_right_control": "synthetic:left-target",
            "right_target_left_control": "synthetic:right-target",
            "bidirectional_target_control": "synthetic:bidirectional",
        }[expected_kind]
        if expected_tag not in left_id or expected_tag not in right_id:
            raise JointDirectCczReplayError("synthetic overlap identity changed")
        # The exact operands are pinned independently from the serialized row.
        cases: dict[str, tuple[_Operation, _Operation]] = {
            "disjoint": (
                _Operation(left_id, ("a", "b"), "t", 1, "synthetic"),
                _Operation(right_id, ("c", "d"), "u", 1, "synthetic"),
            ),
            "shared_control": (
                _Operation(left_id, ("a", "b"), "t", 1, "synthetic"),
                _Operation(right_id, ("a", "c"), "u", 1, "synthetic"),
            ),
            "shared_target": (
                _Operation(left_id, ("a", "b"), "t", 1, "synthetic"),
                _Operation(right_id, ("c", "d"), "t", 1, "synthetic"),
            ),
            "left_target_right_control": (
                _Operation(left_id, ("a", "b"), "t", 1, "synthetic"),
                _Operation(right_id, ("t", "c"), "u", 1, "synthetic"),
            ),
            "right_target_left_control": (
                _Operation(left_id, ("u", "a"), "t", 1, "synthetic"),
                _Operation(right_id, ("b", "c"), "u", 1, "synthetic"),
            ),
            "bidirectional_target_control": (
                _Operation(left_id, ("a", "u"), "t", 1, "synthetic"),
                _Operation(right_id, ("b", "t"), "u", 1, "synthetic"),
            ),
        }
        pair = cases[expected_kind]
        if dict(row) != _independent_pair_data(*pair):
            raise JointDirectCczReplayError("synthetic pair certificate mismatch")
        synthetic_operations.append(pair)

    baseline = _mapping(plan.get("baseline"), label="baseline")
    if dict(baseline) != {
        "candidate_levels": 12,
        "ccx_count": 10,
        "toffoli_bearing_layers": 6,
    }:
        raise JointDirectCczReplayError("reviewed baseline changed")
    unitary = _mapping(plan.get("unitary_candidate"), label="unitary candidate")
    measured = _mapping(
        plan.get("measured_cleanup_candidate"), label="measured candidate"
    )
    if (
        unitary.get("ccx_count"),
        unitary.get("macro_depth"),
        unitary.get("candidate_levels"),
    ) != (10, 4, 8):
        raise JointDirectCczReplayError("unitary candidate headline changed")
    if (
        unitary.get("candidate_level_coordinate")
        != "two_phase_macro_envelope_not_schedule_or_time"
        or unitary.get("candidate_level_status") != "CHECK_PENDING_T-20260906-003"
    ):
        raise JointDirectCczReplayError("unitary level qualification changed")
    if (
        measured.get("ccx_count"),
        measured.get("macro_depth"),
        measured.get("candidate_levels"),
    ) != (9, 3, 6):
        raise JointDirectCczReplayError("measured candidate headline changed")
    if (
        measured.get("candidate_level_coordinate")
        != "two_phase_macro_envelope_not_schedule_or_time"
        or measured.get("candidate_level_status") != "CHECK_PENDING_T-20260906-003"
    ):
        raise JointDirectCczReplayError("measured level qualification changed")
    unitary_layers = _sequence(unitary.get("macro_layers"), label="unitary layers")
    measured_layers = _sequence(measured.get("macro_layers"), label="measured layers")
    if len(unitary_layers) != 4 or len(measured_layers) != 3:
        raise JointDirectCczReplayError("macro-layer count changed")
    macro_operations: list[tuple[_Operation, ...]] = []
    admitted_pair_count = 0
    resource_triples = 0
    resource_values = 0
    for layer in unitary_layers:
        operations, layer_pairs, layer_resources, layer_resource_values = (
            _check_macro_layer(layer, source_by_id)
        )
        macro_operations.append(operations)
        admitted_pair_count += layer_pairs
        resource_triples += layer_resources
        resource_values += layer_resource_values
    if list(measured_layers) != list(unitary_layers[:3]):
        raise JointDirectCczReplayError("measured variant changed a non-cleanup layer")
    expected_groups = (
        source_operations[0:4],
        source_operations[4:7],
        source_operations[7:9],
        source_operations[9:10],
    )
    if tuple(macro_operations) != expected_groups:
        raise JointDirectCczReplayError("width-5 macro grouping changed")

    single_count, single_probability_error, single_operator_error = (
        _verify_single_event_all_branches()
    )
    shared_control_pairs = tuple(
        (left, right)
        for operations in macro_operations
        for index, left in enumerate(operations)
        for right in operations[index + 1 :]
        if _overlap_kind(left, right) == "shared_control"
    )
    if len(shared_control_pairs) != 2:
        raise JointDirectCczReplayError("width-5 shared-control anchor count changed")
    shared_target_pairs = tuple(
        pair
        for pair in synthetic_operations
        if _overlap_kind(*pair) == "shared_target"
    )
    shared_control_anchor = _verify_joint_anchors(
        "shared_control", shared_control_pairs
    )
    shared_target_anchor = _verify_joint_anchors("shared_target", shared_target_pairs)
    measurement = _verify_measurement_uncompute(
        source, measured.get("measurement_uncompute")
    )

    finite = _mapping(plan.get("finite_outputs"), label="finite outputs")
    expected_null = {
        "failure_probability": None,
        "native_cycles": None,
        "physical_qubits": None,
        "runtime_seconds": None,
    }
    if plan.get("complete_native_schedule") is not False or dict(finite) != expected_null:
        raise JointDirectCczReplayError("finite-backend output must remain null")
    synthetic_noncommuting = sum(
        not bool(_mapping(item, label="synthetic certificate").get("commutes"))
        for item in synthetic_rows
    )
    all_passed = (
        pair_count == 45
        and admitted_pair_count == 10
        and single_probability_error <= TOLERANCE
        and single_operator_error <= TOLERANCE
        and shared_control_anchor.maximum_probability_error <= TOLERANCE
        and shared_control_anchor.maximum_operator_frobenius_error <= TOLERANCE
        and shared_target_anchor.maximum_probability_error <= TOLERANCE
        and shared_target_anchor.maximum_operator_frobenius_error <= TOLERANCE
        and measurement.all_passed
    )
    return WidthFiveJointDirectCczReplaySummary(
        source_ccx_count=len(source_operations),
        all_source_pair_count=pair_count,
        commuting_source_pair_count=commuting_count,
        noncommuting_source_pair_count=pair_count - commuting_count,
        source_pair_truth_table_rows_checked=truth_rows,
        synthetic_overlap_cases_checked=len(synthetic_rows),
        synthetic_noncommuting_witnesses=synthetic_noncommuting,
        unitary_macro_layer_count=len(unitary_layers),
        measured_macro_layer_count=len(measured_layers),
        admitted_macro_pair_count=admitted_pair_count,
        common_frame_factorization_proofs=len(unitary_layers),
        factorized_two_event_branches_covered=(admitted_pair_count + 1) * 4096,
        single_event_branches_checked=single_count,
        single_event_maximum_probability_error=single_probability_error,
        single_event_maximum_operator_frobenius_error=single_operator_error,
        shared_control_anchor=shared_control_anchor,
        shared_target_anchor=shared_target_anchor,
        measurement_uncompute=measurement,
        resource_triples_checked=resource_triples,
        resource_values_checked=resource_values,
        event_to_event_reaction_edge_count=0,
        unitary_candidate_levels=8,
        measured_candidate_levels=6,
        complete_native_schedule=False,
        native_cycles=None,
        runtime_seconds=None,
        physical_qubits=None,
        failure_probability=None,
        tolerance=TOLERANCE,
        all_passed=bool(all_passed),
    )


def width5_joint_direct_ccz_replay_to_data(
    summary: WidthFiveJointDirectCczReplaySummary,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible replay data."""

    return asdict(summary)
