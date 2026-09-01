"""Independent replay for a serialized symbolic direct-CCZ PPM trace.

This module intentionally does not import the symbolic compiler.  It rebuilds
source provenance, correction truth tables, frame transitions, and concrete
Pauli probes from JSON-compatible data.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import product
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGateKind
from ecdlp_ftqc.circuits.qcla_oop import OopQclaGate, OopQclaTrace, replay_oop_qcla
from ecdlp_ftqc.verification.direct_ccz_injection import (
    direct_ccz_branch_correction,
    verify_direct_ccz_injection_channel,
)

EXPECTED_SCHEMA = "ecdlp-ftqc/symbolic-direct-ccz-ppm-trace"
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_FRAME_NORMAL_FORM = "ordered-conditional-cliffords-with-anf-conditions-v1"


class DirectCczPpmReplayError(ValueError):
    """Raised when independent replay rejects a serialized trace."""


@dataclass(frozen=True, slots=True)
class SymbolicDirectCczPpmReplaySummary:
    """Independent structural, frame, and semantic verification counts."""

    width: int
    source_operation_count: int
    injection_count: int
    ppm_count: int
    passthrough_cnot_count: int
    correction_update_count: int
    macro_layer_count: int
    source_dependency_count: int
    logical_lifetime_count: int
    resource_lifetime_count: int
    compiler_ancilla_count: int
    correction_truth_table_rows_checked: int
    frame_transition_count_checked: int
    frame_probe_assignment_count: int
    presented_observable_checks: int
    source_basis_input_pairs_checked: int
    local_injection_branch_count: int
    local_injection_maximum_operator_error: float
    complete_native_schedule: bool
    all_passed: bool


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DirectCczPpmReplayError(f"{label} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _sequence(value: object, *, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise DirectCczPpmReplayError(f"{label} must be a sequence")
    return list(value)


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczPpmReplayError(f"{label} must be a nonempty string")
    return value


def _integer(value: object, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DirectCczPpmReplayError(f"{label} must be an integer")
    return value


def _strings(value: object, *, label: str) -> tuple[str, ...]:
    return tuple(_string(item, label=label) for item in _sequence(value, label=label))


def _eval_polynomial(value: object, assignment: Mapping[str, int]) -> int:
    polynomial = _mapping(value, label="Boolean polynomial")
    monomials = _sequence(polynomial.get("anf_monomials"), label="ANF monomials")
    result = 0
    canonical: list[tuple[str, ...]] = []
    for raw_monomial in monomials:
        monomial = _strings(raw_monomial, label="ANF monomial")
        if tuple(sorted(set(monomial))) != monomial:
            raise DirectCczPpmReplayError("ANF monomial is not canonical")
        canonical.append(monomial)
        term = 1
        for variable in monomial:
            bit = assignment.get(variable)
            if bit not in {0, 1}:
                raise DirectCczPpmReplayError(
                    f"missing assignment for Boolean variable {variable!r}"
                )
            term &= bit
        result ^= term
    expected_order = sorted(canonical, key=lambda item: (len(item), item))
    if canonical != expected_order or len(canonical) != len(set(canonical)):
        raise DirectCczPpmReplayError("ANF polynomial is not canonical")
    variables = tuple(sorted({name for monomial in canonical for name in monomial}))
    if _strings(polynomial.get("variables"), label="ANF variables") != variables:
        raise DirectCczPpmReplayError("ANF variable list is inconsistent")
    return result


def _gate(kind: str, support: tuple[str, ...]) -> dict[str, Any]:
    return {"kind": kind, "support": list(support)}


def _normalize_circuit(circuit: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    stack: list[dict[str, Any]] = []
    for raw_gate in circuit:
        gate = {str(key): value for key, value in raw_gate.items()}
        kind = _string(gate.get("kind"), label="frame gate kind")
        support = _strings(gate.get("support"), label="frame gate support")
        expected = 2 if kind in {"CNOT", "CZ"} else 1
        if kind not in {"H", "X", "Z", "CNOT", "CZ"} or len(support) != expected:
            raise DirectCczPpmReplayError("invalid frame gate")
        canonical = _gate(kind, support)
        if stack and stack[-1] == canonical:
            stack.pop()
        else:
            stack.append(canonical)
    return stack


def _term_signature(terms: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(
        list(terms),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _snapshot_terms(snapshot_value: object) -> list[dict[str, Any]]:
    snapshot = _mapping(snapshot_value, label="frame snapshot")
    if snapshot.get("normal_form") != EXPECTED_FRAME_NORMAL_FORM:
        raise DirectCczPpmReplayError("unexpected frame normal form")
    terms = [
        _mapping(term, label="frame term")
        for term in _sequence(snapshot.get("terms"), label="frame terms")
    ]
    signature = _string(snapshot.get("signature"), label="frame signature")
    if signature != _term_signature(terms):
        raise DirectCczPpmReplayError("frame snapshot signature mismatch")
    return terms


def _conjugate_terms_by_cnot(
    terms: Sequence[Mapping[str, Any]],
    control: str,
    target: str,
) -> list[dict[str, Any]]:
    cnot = _gate("CNOT", (control, target))
    result: list[dict[str, Any]] = []
    for raw_term in terms:
        term = {str(key): value for key, value in raw_term.items()}
        circuit = [
            _mapping(item, label="frame circuit gate")
            for item in _sequence(term.get("circuit"), label="frame circuit")
        ]
        term["circuit"] = _normalize_circuit((cnot, *circuit, cnot))
        result.append(term)
    return result


@dataclass(slots=True)
class _ConcretePauli:
    sign: int
    x: set[str]
    z: set[str]

    @classmethod
    def from_terms(
        cls,
        support: tuple[str, ...],
        terms: tuple[str, ...],
    ) -> _ConcretePauli:
        if len(support) != len(terms):
            raise DirectCczPpmReplayError("Pauli support and terms do not align")
        x: set[str] = set()
        z: set[str] = set()
        for logical, term in zip(support, terms, strict=True):
            if term in {"X", "Y"}:
                x.add(logical)
            if term in {"Z", "Y"}:
                z.add(logical)
            if term not in {"X", "Y", "Z"}:
                raise DirectCczPpmReplayError("unsupported Pauli term")
        return cls(sign=0, x=x, z=z)

    def apply_gate(self, raw_gate: Mapping[str, Any]) -> None:
        gate = _mapping(raw_gate, label="concrete frame gate")
        kind = _string(gate.get("kind"), label="concrete frame gate kind")
        support = _strings(gate.get("support"), label="concrete frame gate support")
        if kind == "H":
            qubit = support[0]
            if qubit in self.x and qubit in self.z:
                self.sign ^= 1
            old_x = qubit in self.x
            old_z = qubit in self.z
            self.x.discard(qubit)
            self.z.discard(qubit)
            if old_z:
                self.x.add(qubit)
            if old_x:
                self.z.add(qubit)
        elif kind == "X":
            self.sign ^= int(support[0] in self.z)
        elif kind == "Z":
            self.sign ^= int(support[0] in self.x)
        elif kind == "CNOT":
            control, target = support
            xc = int(control in self.x)
            xt = int(target in self.x)
            zc = int(control in self.z)
            zt = int(target in self.z)
            self.sign ^= xc & zt & (xt ^ zc ^ 1)
            if xc:
                self.x.symmetric_difference_update({target})
            if zt:
                self.z.symmetric_difference_update({control})
        elif kind == "CZ":
            control, target = support
            self.apply_gate(_gate("H", (target,)))
            self.apply_gate(_gate("CNOT", (control, target)))
            self.apply_gate(_gate("H", (target,)))
        else:
            raise DirectCczPpmReplayError("unsupported concrete frame gate")

    def canonical(self) -> tuple[int, tuple[tuple[str, str], ...]]:
        result = []
        for logical in sorted(self.x | self.z):
            bits = (logical in self.x, logical in self.z)
            term = {
                (True, False): "X",
                (False, True): "Z",
                (True, True): "Y",
            }[bits]
            result.append((logical, term))
        return self.sign, tuple(result)


def _evaluate_serialized_pauli(
    value: object,
    assignment: Mapping[str, int],
) -> tuple[int, tuple[tuple[str, str], ...]]:
    pauli = _mapping(value, label="serialized Pauli")
    x: set[str] = set()
    z: set[str] = set()
    for raw_component in _sequence(pauli.get("x_components"), label="Pauli X components"):
        component = _mapping(raw_component, label="Pauli X component")
        logical = _string(component.get("logical_value"), label="Pauli logical value")
        if _eval_polynomial(component.get("coefficient"), assignment):
            x.add(logical)
    for raw_component in _sequence(pauli.get("z_components"), label="Pauli Z components"):
        component = _mapping(raw_component, label="Pauli Z component")
        logical = _string(component.get("logical_value"), label="Pauli logical value")
        if _eval_polynomial(component.get("coefficient"), assignment):
            z.add(logical)
    sign = _eval_polynomial(pauli.get("sign"), assignment)
    return _ConcretePauli(sign=sign, x=x, z=z).canonical()


def _probe_assignments(outcomes: tuple[str, ...]) -> tuple[dict[str, int], ...]:
    assignments: list[dict[str, int]] = [
        {outcome: 0 for outcome in outcomes},
        {outcome: 1 for outcome in outcomes},
    ]
    for selected in outcomes:
        assignments.append(
            {outcome: int(outcome == selected) for outcome in outcomes}
        )
    assignments.append(
        {outcome: index % 2 for index, outcome in enumerate(outcomes)}
    )
    assignments.append(
        {outcome: (index + 1) % 2 for index, outcome in enumerate(outcomes)}
    )
    return tuple(assignments)


def _source_gate_map(source: OopQclaTrace) -> dict[str, OopQclaGate]:
    return {gate.gate_id: gate for gate in source.gates}


def _validate_source_projection(
    source: OopQclaTrace,
    trace: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    operations = [
        _mapping(item, label="source operation")
        for item in _sequence(trace.get("source_operations"), label="source operations")
    ]
    if len(operations) != len(source.gates):
        raise DirectCczPpmReplayError("source operation count changed")
    operation_by_id = {
        _string(operation.get("source_gate_id"), label="source gate ID"): operation
        for operation in operations
    }
    if len(operation_by_id) != len(operations):
        raise DirectCczPpmReplayError("source operation IDs are not unique")
    for gate in source.gates:
        operation = operation_by_id.get(gate.gate_id)
        if operation is None:
            raise DirectCczPpmReplayError("source gate disappeared during lowering")
        expected = (
            gate.kind.value,
            gate.algorithmic_layer,
            gate.stage.value,
            gate.logical_support,
        )
        observed = (
            operation.get("source_kind"),
            operation.get("source_algorithmic_layer"),
            operation.get("source_stage"),
            _strings(operation.get("logical_support"), label="source logical support"),
        )
        if observed != expected:
            raise DirectCczPpmReplayError("source operation provenance changed")
    expected_dependencies = [
        {
            "logical_values": list(dependency.values),
            "predecessor_source_gate_id": dependency.predecessor,
            "reason": dependency.reason,
            "successor_source_gate_id": dependency.successor,
        }
        for dependency in source.dependencies
    ]
    observed_dependencies = _sequence(
        trace.get("source_dependencies"), label="source dependencies"
    )
    if observed_dependencies != expected_dependencies:
        raise DirectCczPpmReplayError("source dependencies changed")
    return operations, operation_by_id


def _validate_injections_and_corrections(
    source: OopQclaTrace,
    trace: Mapping[str, Any],
) -> int:
    gates = _source_gate_map(source)
    injections = [
        _mapping(item, label="injection")
        for item in _sequence(trace.get("injections"), label="injections")
    ]
    ppms = [
        _mapping(item, label="PPM")
        for item in _sequence(trace.get("ppms"), label="PPMs")
    ]
    ppm_by_id = {
        _string(ppm.get("operation_id"), label="PPM ID"): ppm for ppm in ppms
    }
    updates = [
        _mapping(item, label="correction update")
        for item in _sequence(trace.get("correction_updates"), label="correction updates")
    ]
    update_by_id = {
        _string(update.get("update_id"), label="correction update ID"): update
        for update in updates
    }
    rows = 0
    for injection in injections:
        source_id = _string(injection.get("source_gate_id"), label="injection source ID")
        gate = gates.get(source_id)
        if gate is None or gate.kind is not QclaGateKind.TOFFOLI:
            raise DirectCczPpmReplayError("injection does not map a source Toffoli")
        data = _strings(injection.get("data"), label="injection data")
        resource = _strings(injection.get("resource"), label="injection resource")
        if data != (*gate.controls, gate.target) or len(resource) != 3:
            raise DirectCczPpmReplayError("injection support changed")
        event_ppms = [
            ppm_by_id[ppm_id]
            for ppm_id in _strings(
                injection.get("ppm_operation_ids"), label="injection PPM IDs"
            )
        ]
        expected_ppms = (
            ((resource[0], data[0]), ("Z", "Z"), 1),
            ((resource[1], data[1]), ("Z", "Z"), 1),
            ((resource[2], data[2]), ("Z", "Z"), 1),
            ((resource[0],), ("X",), 2),
            ((resource[1],), ("X",), 2),
            ((resource[2],), ("X",), 2),
        )
        if len(event_ppms) != 6:
            raise DirectCczPpmReplayError("injection PPM count changed")
        for ppm, (support, terms, layer) in zip(event_ppms, expected_ppms, strict=True):
            observed = (
                _strings(ppm.get("logical_support"), label="PPM support"),
                _strings(ppm.get("pauli_terms"), label="PPM terms"),
                _integer(ppm.get("injection_layer"), label="PPM injection layer"),
            )
            if observed != (support, terms, layer):
                raise DirectCczPpmReplayError("injection PPM pattern changed")
        outcome_tokens = tuple(
            _string(ppm.get("outcome_token"), label="PPM outcome")
            for ppm in event_ppms
        )
        event_updates = [
            update_by_id[update_id]
            for update_id in _strings(
                injection.get("correction_update_ids"),
                label="injection correction IDs",
            )
        ]
        expected_gates = (
            _gate("CNOT", (data[1], data[2])),
            _gate("CNOT", (data[0], data[2])),
            _gate("CZ", (data[0], data[1])),
            _gate("Z", (data[0],)),
            _gate("Z", (data[1],)),
            _gate("X", (data[2],)),
        )
        if len(event_updates) != 6:
            raise DirectCczPpmReplayError("injection correction count changed")
        for update, expected_gate in zip(event_updates, expected_gates, strict=True):
            frame_term = _mapping(update.get("frame_term"), label="correction frame term")
            circuit = _sequence(frame_term.get("circuit"), label="correction circuit")
            if circuit != [expected_gate]:
                raise DirectCczPpmReplayError("event-boundary correction gate changed")
        for raw_bits in product((0, 1), repeat=6):
            assignment = dict(zip(outcome_tokens, raw_bits, strict=True))
            expected = direct_ccz_branch_correction(
                (raw_bits[0], raw_bits[1], raw_bits[2]),
                (raw_bits[3], raw_bits[4], raw_bits[5]),
            )
            expected_exponents = (
                *expected.conditional_cz_exponents,
                *expected.pauli_exponents,
            )
            observed_exponents = tuple(
                _eval_polynomial(
                    _mapping(update.get("frame_term"), label="frame term").get(
                        "condition"
                    ),
                    assignment,
                )
                for update in event_updates
            )
            if observed_exponents != expected_exponents:
                raise DirectCczPpmReplayError("correction truth table changed")
            rows += 1
    return rows


def _validate_operation_dependencies(
    source: OopQclaTrace,
    trace: Mapping[str, Any],
    operations: Mapping[str, Mapping[str, Any]],
) -> None:
    """Rebuild the symbolic operation graph from the source and event contract."""

    injections = {
        _string(item.get("source_gate_id"), label="injection source ID"): item
        for item in (
            _mapping(raw, label="injection")
            for raw in _sequence(trace.get("injections"), label="injections")
        )
    }
    ppms = {
        _string(item.get("operation_id"), label="PPM ID"): item
        for item in (
            _mapping(raw, label="PPM")
            for raw in _sequence(trace.get("ppms"), label="PPMs")
        )
    }
    cliffords = {
        _string(item.get("operation_id"), label="Clifford ID"): item
        for item in (
            _mapping(raw, label="Clifford")
            for raw in _sequence(
                trace.get("clifford_instructions"), label="Cliffords"
            )
        )
    }
    updates = {
        _string(item.get("update_id"), label="correction update ID"): item
        for item in (
            _mapping(raw, label="correction update")
            for raw in _sequence(
                trace.get("correction_updates"), label="correction updates"
            )
        )
    }
    source_predecessors: dict[str, list[str]] = {
        gate.gate_id: [] for gate in source.gates
    }
    source_order = {gate.gate_id: index for index, gate in enumerate(source.gates)}
    for dependency in source.dependencies:
        source_predecessors[dependency.successor].append(dependency.predecessor)
    for predecessors in source_predecessors.values():
        predecessors.sort(key=source_order.__getitem__)

    terminal_by_source: dict[str, str] = {}
    expected_cliffords: set[str] = set()
    expected_ppms: set[str] = set()
    expected_updates: set[str] = set()
    for gate in source.gates:
        operation = operations[gate.gate_id]
        predecessor_ids = tuple(
            terminal_by_source[item] for item in source_predecessors[gate.gate_id]
        )
        if gate.kind is QclaGateKind.CNOT:
            operation_id = f"{gate.gate_id}:passthrough-cnot"
            instruction = cliffords.get(operation_id)
            if instruction is None:
                raise DirectCczPpmReplayError("pass-through CNOT disappeared")
            if (
                instruction.get("source_gate_id"),
                instruction.get("role"),
                _mapping(instruction.get("logical_gate"), label="CNOT gate"),
                _strings(
                    instruction.get("predecessor_operation_ids"),
                    label="CNOT predecessors",
                ),
            ) != (
                gate.gate_id,
                "passthrough_cnot",
                _gate("CNOT", (gate.controls[0], gate.target)),
                predecessor_ids,
            ):
                raise DirectCczPpmReplayError("pass-through CNOT dependency changed")
            if _strings(
                operation.get("emitted_operation_ids"), label="emitted CNOT IDs"
            ) != (operation_id,):
                raise DirectCczPpmReplayError("pass-through CNOT provenance changed")
            expected_cliffords.add(operation_id)
            terminal_by_source[gate.gate_id] = operation_id
            continue

        injection = injections.get(gate.gate_id)
        if injection is None:
            raise DirectCczPpmReplayError("source Toffoli injection disappeared")
        event_id = _string(injection.get("event_id"), label="injection event ID")
        basis_before_id = _string(
            injection.get("basis_change_before_id"), label="basis-before ID"
        )
        basis_after_id = _string(
            injection.get("basis_change_after_id"), label="basis-after ID"
        )
        completion_id = _string(
            injection.get("completion_id"), label="completion ID"
        )
        ppm_ids = _strings(injection.get("ppm_operation_ids"), label="PPM IDs")
        update_ids = _strings(
            injection.get("correction_update_ids"), label="correction IDs"
        )
        before = cliffords.get(basis_before_id)
        after = cliffords.get(basis_after_id)
        if before is None or after is None:
            raise DirectCczPpmReplayError("injection basis change disappeared")
        expected_h = _gate("H", (gate.target,))
        if (
            before.get("source_gate_id"),
            before.get("role"),
            _mapping(before.get("logical_gate"), label="basis-before gate"),
            _strings(
                before.get("predecessor_operation_ids"),
                label="basis-before predecessors",
            ),
        ) != (
            gate.gate_id,
            "injection_basis_change_before",
            expected_h,
            predecessor_ids,
        ):
            raise DirectCczPpmReplayError("basis-before dependency changed")
        layer_one = ppm_ids[:3]
        for index, ppm_id in enumerate(ppm_ids):
            ppm = ppms.get(ppm_id)
            if ppm is None:
                raise DirectCczPpmReplayError("injection PPM disappeared")
            expected_predecessors = (basis_before_id,) if index < 3 else layer_one
            if (
                ppm.get("source_gate_id"),
                ppm.get("injection_event_id"),
                _strings(
                    ppm.get("predecessor_operation_ids"), label="PPM predecessors"
                ),
            ) != (gate.gate_id, event_id, expected_predecessors):
                raise DirectCczPpmReplayError("PPM dependency changed")
            expected_ppms.add(ppm_id)
        if (
            after.get("source_gate_id"),
            after.get("role"),
            _mapping(after.get("logical_gate"), label="basis-after gate"),
            _strings(
                after.get("predecessor_operation_ids"),
                label="basis-after predecessors",
            ),
        ) != (
            gate.gate_id,
            "injection_basis_change_after",
            expected_h,
            layer_one,
        ):
            raise DirectCczPpmReplayError("basis-after dependency changed")
        for update_id in update_ids:
            update = updates.get(update_id)
            if update is None:
                raise DirectCczPpmReplayError("correction update disappeared")
            frame_term = _mapping(update.get("frame_term"), label="frame term")
            condition = _mapping(frame_term.get("condition"), label="condition")
            if (
                update.get("source_gate_id"),
                update.get("injection_event_id"),
                set(
                    _strings(
                        update.get("outcome_dependencies"),
                        label="correction outcome dependencies",
                    )
                ),
            ) != (
                gate.gate_id,
                event_id,
                set(_strings(condition.get("variables"), label="condition variables")),
            ):
                raise DirectCczPpmReplayError("correction dependency changed")
            expected_updates.add(update_id)
        if _strings(
            injection.get("completion_predecessor_ids"),
            label="completion predecessors",
        ) != (basis_after_id, *update_ids):
            raise DirectCczPpmReplayError("injection completion dependency changed")
        if _strings(
            operation.get("emitted_operation_ids"), label="emitted injection IDs"
        ) != (
            basis_before_id,
            *ppm_ids,
            *update_ids,
            basis_after_id,
            completion_id,
        ):
            raise DirectCczPpmReplayError("injection provenance changed")
        expected_cliffords.update((basis_before_id, basis_after_id))
        terminal_by_source[gate.gate_id] = completion_id

    if set(cliffords) != expected_cliffords:
        raise DirectCczPpmReplayError("unexpected Clifford instruction")
    if set(ppms) != expected_ppms:
        raise DirectCczPpmReplayError("unexpected PPM instruction")
    if set(updates) != expected_updates:
        raise DirectCczPpmReplayError("unexpected correction update")


def _replay_frames(
    source: OopQclaTrace,
    trace: Mapping[str, Any],
) -> tuple[int, dict[str, list[dict[str, Any]]]]:
    operations = {
        _string(item.get("source_gate_id"), label="source operation ID"): item
        for item in (
            _mapping(raw, label="source operation")
            for raw in _sequence(trace.get("source_operations"), label="source operations")
        )
    }
    injections = {
        _string(item.get("source_gate_id"), label="injection source ID"): item
        for item in (
            _mapping(raw, label="injection")
            for raw in _sequence(trace.get("injections"), label="injections")
        )
    }
    updates = {
        _string(item.get("update_id"), label="correction update ID"): item
        for item in (
            _mapping(raw, label="correction update")
            for raw in _sequence(trace.get("correction_updates"), label="updates")
        )
    }
    layers = [
        _mapping(raw, label="macro layer")
        for raw in _sequence(trace.get("macro_layer_frames"), label="macro layers")
    ]
    layer_by_number = {
        _integer(layer.get("source_algorithmic_layer"), label="macro layer number"): layer
        for layer in layers
    }
    terms: list[dict[str, Any]] = []
    frame_in_by_source: dict[str, list[dict[str, Any]]] = {}
    transitions = 0
    for layer_number in range(1, max(gate.algorithmic_layer for gate in source.gates) + 1):
        layer = layer_by_number.get(layer_number)
        if layer is None:
            raise DirectCczPpmReplayError("macro layer disappeared")
        observed_in = _snapshot_terms(layer.get("frame_in"))
        if observed_in != terms:
            raise DirectCczPpmReplayError("macro-layer frame-in changed")
        layer_gates = tuple(
            gate for gate in source.gates if gate.algorithmic_layer == layer_number
        )
        if _strings(layer.get("source_gate_ids"), label="macro source IDs") != tuple(
            gate.gate_id for gate in layer_gates
        ):
            raise DirectCczPpmReplayError("macro-layer source membership changed")
        for gate in layer_gates:
            frame_in_by_source[gate.gate_id] = [dict(term) for term in terms]
            operation = operations[gate.gate_id]
            if operation.get("frame_in_signature") != _term_signature(terms):
                raise DirectCczPpmReplayError("source operation frame-in changed")
            if gate.kind is QclaGateKind.CNOT:
                terms = _conjugate_terms_by_cnot(
                    terms,
                    gate.controls[0],
                    gate.target,
                )
            else:
                injection = injections[gate.gate_id]
                new_terms = [
                    _mapping(
                        updates[update_id].get("frame_term"),
                        label="new correction frame term",
                    )
                    for update_id in _strings(
                        injection.get("correction_update_ids"),
                        label="correction IDs",
                    )
                ]
                accumulated: list[dict[str, Any]] = []
                for update_id, term in zip(
                    _strings(
                        injection.get("correction_update_ids"),
                        label="correction IDs",
                    ),
                    new_terms,
                    strict=True,
                ):
                    accumulated.append(term)
                    if updates[update_id].get("resulting_frame_signature") != (
                        _term_signature([*terms, *accumulated])
                    ):
                        raise DirectCczPpmReplayError(
                            "partial correction frame signature changed"
                        )
                terms = terms + new_terms
            if operation.get("frame_out_signature") != _term_signature(terms):
                raise DirectCczPpmReplayError("source operation frame-out changed")
            transitions += 1
        observed_out = _snapshot_terms(layer.get("frame_out"))
        if observed_out != terms:
            raise DirectCczPpmReplayError("macro-layer frame-out changed")
    return transitions, frame_in_by_source


def _validate_presented_observables(
    trace: Mapping[str, Any],
    frame_in_by_source: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[int, int]:
    ppms = [
        _mapping(raw, label="PPM")
        for raw in _sequence(trace.get("ppms"), label="PPMs")
    ]
    outcomes = tuple(
        _string(ppm.get("outcome_token"), label="PPM outcome") for ppm in ppms
    )
    assignments = _probe_assignments(outcomes)
    checks = 0
    for ppm in ppms:
        source_id = _string(ppm.get("source_gate_id"), label="PPM source ID")
        frame_terms = frame_in_by_source[source_id]
        support = _strings(ppm.get("logical_support"), label="PPM support")
        pauli_terms = _strings(ppm.get("pauli_terms"), label="PPM terms")
        for assignment in assignments:
            expected = _ConcretePauli.from_terms(support, pauli_terms)
            # Serialized terms are correction-to-apply circuit order. The
            # physical observable is C† P C, hence inverse/reverse traversal.
            for raw_term in reversed(frame_terms):
                term = _mapping(raw_term, label="probe frame term")
                condition = _mapping(term.get("condition"), label="probe condition")
                if _eval_polynomial(condition, assignment):
                    for raw_gate in _sequence(term.get("circuit"), label="probe circuit"):
                        expected.apply_gate(_mapping(raw_gate, label="probe gate"))
            observed = _evaluate_serialized_pauli(
                ppm.get("presented_observable"),
                assignment,
            )
            if observed != expected.canonical():
                raise DirectCczPpmReplayError("presented Pauli observable changed")
            checks += 1
    return len(assignments), checks


def _validate_lifetimes(source: OopQclaTrace, trace: Mapping[str, Any]) -> None:
    observed = {
        _string(item.get("logical_value"), label="lifetime logical value"): item
        for item in (
            _mapping(raw, label="logical lifetime")
            for raw in _sequence(trace.get("logical_lifetimes"), label="lifetimes")
        )
    }
    uses: dict[str, list[OopQclaGate]] = {}
    for gate in source.gates:
        for logical in gate.logical_support:
            uses.setdefault(logical, []).append(gate)
    if set(observed) != set(uses):
        raise DirectCczPpmReplayError("logical lifetime set changed")
    for logical, gates in uses.items():
        lifetime = observed[logical]
        if (
            lifetime.get("first_source_gate_id"),
            lifetime.get("last_source_gate_id"),
            lifetime.get("first_source_layer"),
            lifetime.get("last_source_layer"),
        ) != (
            gates[0].gate_id,
            gates[-1].gate_id,
            gates[0].algorithmic_layer,
            gates[-1].algorithmic_layer,
        ):
            raise DirectCczPpmReplayError("logical lifetime interval changed")
    if _sequence(trace.get("compiler_ancilla_lifetimes"), label="compiler ancillas"):
        raise DirectCczPpmReplayError("unexpected compiler ancilla lifetime")
    resource_lifetimes = _sequence(
        trace.get("resource_lifetimes"), label="resource lifetimes"
    )
    toffoli_count = sum(gate.kind is QclaGateKind.TOFFOLI for gate in source.gates)
    if len(resource_lifetimes) != toffoli_count:
        raise DirectCczPpmReplayError("resource lifetime count changed")


def replay_symbolic_direct_ccz_ppm_trace(
    source: OopQclaTrace,
    trace_data: Mapping[str, Any],
) -> SymbolicDirectCczPpmReplaySummary:
    """Independently verify one serialized symbolic PPM/frame trace."""

    trace = {str(key): value for key, value in trace_data.items()}
    if trace.get("schema") != EXPECTED_SCHEMA or trace.get("schema_version") != 1:
        raise DirectCczPpmReplayError("unsupported symbolic PPM schema")
    if trace.get("frame_normal_form") != EXPECTED_FRAME_NORMAL_FORM:
        raise DirectCczPpmReplayError("unsupported frame normal form")
    if trace.get("source_trace_id") != source.trace_id:
        raise DirectCczPpmReplayError("source trace ID changed")
    if trace.get("source_trace_schema_version") != source.schema_version:
        raise DirectCczPpmReplayError("source schema version changed")
    if trace.get("width") != source.width:
        raise DirectCczPpmReplayError("source width changed")
    if trace.get("complete_native_schedule") is not False:
        raise DirectCczPpmReplayError("Phase-A trace claimed a native schedule")

    operations, operation_by_id = _validate_source_projection(source, trace)
    truth_rows = _validate_injections_and_corrections(source, trace)
    _validate_operation_dependencies(source, trace, operation_by_id)
    transitions, frame_in_by_source = _replay_frames(source, trace)
    probe_count, observable_checks = _validate_presented_observables(
        trace,
        frame_in_by_source,
    )
    _validate_lifetimes(source, trace)

    basis_pairs = 0
    limit = 1 << source.width
    for input_a in range(limit):
        for input_b in range(limit):
            replay_oop_qcla(source, input_a, input_b)
            basis_pairs += 1
    local = verify_direct_ccz_injection_channel()
    if not local.all_passed:
        raise DirectCczPpmReplayError("local direct-CCZ channel check failed")

    injections = _sequence(trace.get("injections"), label="injections")
    ppms = _sequence(trace.get("ppms"), label="PPMs")
    cliffords = [
        _mapping(raw, label="Clifford instruction")
        for raw in _sequence(
            trace.get("clifford_instructions"), label="Clifford instructions"
        )
    ]
    passthrough_count = sum(
        instruction.get("role") == "passthrough_cnot" for instruction in cliffords
    )
    corrections = _sequence(trace.get("correction_updates"), label="corrections")
    layers = _sequence(trace.get("macro_layer_frames"), label="macro layers")
    dependencies = _sequence(trace.get("source_dependencies"), label="dependencies")
    lifetimes = _sequence(trace.get("logical_lifetimes"), label="lifetimes")
    resource_lifetimes = _sequence(
        trace.get("resource_lifetimes"), label="resource lifetimes"
    )
    compiler_ancillas = _sequence(
        trace.get("compiler_ancilla_lifetimes"), label="compiler ancillas"
    )
    return SymbolicDirectCczPpmReplaySummary(
        width=source.width,
        source_operation_count=len(operations),
        injection_count=len(injections),
        ppm_count=len(ppms),
        passthrough_cnot_count=passthrough_count,
        correction_update_count=len(corrections),
        macro_layer_count=len(layers),
        source_dependency_count=len(dependencies),
        logical_lifetime_count=len(lifetimes),
        resource_lifetime_count=len(resource_lifetimes),
        compiler_ancilla_count=len(compiler_ancillas),
        correction_truth_table_rows_checked=truth_rows,
        frame_transition_count_checked=transitions,
        frame_probe_assignment_count=probe_count,
        presented_observable_checks=observable_checks,
        source_basis_input_pairs_checked=basis_pairs,
        local_injection_branch_count=local.branch_count,
        local_injection_maximum_operator_error=(
            local.maximum_operator_frobenius_error
        ),
        complete_native_schedule=False,
        all_passed=True,
    )


def symbolic_direct_ccz_ppm_replay_to_data(
    summary: SymbolicDirectCczPpmReplaySummary,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible replay data."""

    return asdict(summary)
