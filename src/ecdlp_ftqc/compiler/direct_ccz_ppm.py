"""Symbolic direct-CCZ PPM and Clifford-frame traces for reviewed QCLA circuits.

The trace is architecture independent.  Source layers remain dependency
boundaries, not surgery rounds.  Deferred corrections use Boolean algebraic
normal form (ANF), and the compiler records the exact branch-dependent Pauli
observable presented by the incoming Clifford frame.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, cast

from ecdlp_ftqc.architectures import DirectCczCapability
from ecdlp_ftqc.circuits.qcla import QclaGate, QclaGateKind, QclaTrace
from ecdlp_ftqc.circuits.qcla_oop import OopQclaGate, OopQclaTrace
from ecdlp_ftqc.compiler.direct_ccz import (
    DirectCczEventTrace,
    DirectCczInjectionEvent,
    DirectCczSourceDependency,
    lower_oop_qcla_to_direct_ccz_events,
    lower_qcla_to_direct_ccz_events,
)
from ecdlp_ftqc.metadata import EvidenceStatus

DIRECT_CCZ_PPM_TRACE_SCHEMA = "ecdlp-ftqc/symbolic-direct-ccz-ppm-trace"
DIRECT_CCZ_PPM_TRACE_SCHEMA_VERSION = 1
FRAME_NORMAL_FORM = "ordered-conditional-cliffords-with-anf-conditions-v1"
OUTCOME_BIT_CONVENTION = "0 denotes +1 eigenvalue; 1 denotes -1 eigenvalue"


class DirectCczPpmTraceError(ValueError):
    """Raised when the symbolic PPM/frame trace is not canonical or complete."""


def _monomial_key(monomial: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    return (len(monomial), monomial)


@dataclass(frozen=True, slots=True)
class BooleanPolynomial:
    """A Boolean function in canonical algebraic normal form."""

    monomials: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        canonical: list[tuple[str, ...]] = []
        for monomial in self.monomials:
            if any(not variable for variable in monomial):
                raise DirectCczPpmTraceError("Boolean variables cannot be empty")
            if tuple(sorted(set(monomial))) != monomial:
                raise DirectCczPpmTraceError(
                    "ANF monomials must contain sorted unique variables"
                )
            canonical.append(monomial)
        if tuple(sorted(canonical, key=_monomial_key)) != self.monomials:
            raise DirectCczPpmTraceError("ANF monomials must use canonical order")
        if len(canonical) != len(set(canonical)):
            raise DirectCczPpmTraceError("duplicate ANF monomials must cancel")

    @classmethod
    def zero(cls) -> BooleanPolynomial:
        return cls(())

    @classmethod
    def one(cls) -> BooleanPolynomial:
        return cls(((),))

    @classmethod
    def variable(cls, name: str) -> BooleanPolynomial:
        if not name:
            raise DirectCczPpmTraceError("Boolean variable cannot be empty")
        return cls(((name,),))

    @classmethod
    def from_monomials(
        cls,
        monomials: Iterable[Iterable[str]],
    ) -> BooleanPolynomial:
        parity: set[tuple[str, ...]] = set()
        for raw in monomials:
            monomial = tuple(sorted(set(raw)))
            if monomial in parity:
                parity.remove(monomial)
            else:
                parity.add(monomial)
        return cls(tuple(sorted(parity, key=_monomial_key)))

    @property
    def is_zero(self) -> bool:
        return not self.monomials

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(
            sorted({variable for monomial in self.monomials for variable in monomial})
        )

    def xor(self, other: BooleanPolynomial) -> BooleanPolynomial:
        return BooleanPolynomial.from_monomials((*self.monomials, *other.monomials))

    def multiply(self, other: BooleanPolynomial) -> BooleanPolynomial:
        return BooleanPolynomial.from_monomials(
            (*left, *right)
            for left in self.monomials
            for right in other.monomials
        )

    def evaluate(self, assignment: dict[str, int]) -> int:
        result = 0
        for monomial in self.monomials:
            value = 1
            for variable in monomial:
                bit = assignment.get(variable)
                if bit not in {0, 1}:
                    raise DirectCczPpmTraceError(
                        f"missing Boolean assignment for {variable!r}"
                    )
                value &= bit
            result ^= value
        return result

    def to_expression(self) -> str:
        if self.is_zero:
            return "0"
        terms = []
        for monomial in self.monomials:
            if not monomial:
                terms.append("1")
            elif len(monomial) == 1:
                terms.append(monomial[0])
            else:
                terms.append("(" + " AND ".join(monomial) + ")")
        return " XOR ".join(terms)


class FrameGateKind(str, Enum):
    """Self-inverse Clifford primitives used by the frame normal form."""

    H = "H"
    X = "X"
    Z = "Z"
    CNOT = "CNOT"
    CZ = "CZ"


@dataclass(frozen=True, slots=True)
class FrameGate:
    """One fixed Clifford primitive in application order."""

    kind: FrameGateKind
    support: tuple[str, ...]

    def __post_init__(self) -> None:
        expected = 2 if self.kind in {FrameGateKind.CNOT, FrameGateKind.CZ} else 1
        if len(self.support) != expected or len(set(self.support)) != expected:
            raise DirectCczPpmTraceError("Clifford primitive has invalid support")


@dataclass(frozen=True, slots=True)
class SymbolicFrameTerm:
    """A conditionally applied fixed Clifford circuit."""

    term_id: str
    origin_event_id: str
    condition: BooleanPolynomial
    circuit: tuple[FrameGate, ...]
    correction_role: str

    def __post_init__(self) -> None:
        if not self.term_id or not self.origin_event_id or not self.correction_role:
            raise DirectCczPpmTraceError("frame-term identity cannot be empty")
        if self.condition.is_zero or not self.circuit:
            raise DirectCczPpmTraceError("frame term must have a condition and circuit")
        if _normalize_circuit(self.circuit) != self.circuit:
            raise DirectCczPpmTraceError("frame circuit is not in canonical normal form")


def _normalize_circuit(circuit: Iterable[FrameGate]) -> tuple[FrameGate, ...]:
    stack: list[FrameGate] = []
    for gate in circuit:
        if stack and stack[-1] == gate:
            stack.pop()
        else:
            stack.append(gate)
    return tuple(stack)


def _poly_get(
    components: dict[str, BooleanPolynomial],
    logical_value: str,
) -> BooleanPolynomial:
    return components.get(logical_value, BooleanPolynomial.zero())


def _poly_set(
    components: dict[str, BooleanPolynomial],
    logical_value: str,
    value: BooleanPolynomial,
) -> None:
    if value.is_zero:
        components.pop(logical_value, None)
    else:
        components[logical_value] = value


@dataclass(frozen=True, slots=True)
class SymbolicPauliWord:
    """A branch-dependent Hermitian Pauli observable in canonical ANF form."""

    x_components: tuple[tuple[str, BooleanPolynomial], ...]
    z_components: tuple[tuple[str, BooleanPolynomial], ...]
    sign: BooleanPolynomial

    def __post_init__(self) -> None:
        for components in (self.x_components, self.z_components):
            if tuple(sorted(components, key=lambda item: item[0])) != components:
                raise DirectCczPpmTraceError("Pauli components must be ordered")
            names = tuple(name for name, _ in components)
            if len(names) != len(set(names)) or any(poly.is_zero for _, poly in components):
                raise DirectCczPpmTraceError("Pauli components must be unique and nonzero")

    @classmethod
    def from_terms(
        cls,
        logical_support: tuple[str, ...],
        pauli_terms: tuple[str, ...],
    ) -> SymbolicPauliWord:
        if len(logical_support) != len(pauli_terms) or not logical_support:
            raise DirectCczPpmTraceError("Pauli support and terms must align")
        x: dict[str, BooleanPolynomial] = {}
        z: dict[str, BooleanPolynomial] = {}
        for logical, term in zip(logical_support, pauli_terms, strict=True):
            if term not in {"X", "Y", "Z"}:
                raise DirectCczPpmTraceError(f"unsupported Pauli term {term!r}")
            if term in {"X", "Y"}:
                x[logical] = BooleanPolynomial.one()
            if term in {"Z", "Y"}:
                z[logical] = BooleanPolynomial.one()
        return cls._from_dicts(x, z, BooleanPolynomial.zero())

    @classmethod
    def _from_dicts(
        cls,
        x: dict[str, BooleanPolynomial],
        z: dict[str, BooleanPolynomial],
        sign: BooleanPolynomial,
    ) -> SymbolicPauliWord:
        return cls(
            x_components=tuple(sorted(x.items())),
            z_components=tuple(sorted(z.items())),
            sign=sign,
        )

    def _dicts(
        self,
    ) -> tuple[
        dict[str, BooleanPolynomial],
        dict[str, BooleanPolynomial],
        BooleanPolynomial,
    ]:
        return dict(self.x_components), dict(self.z_components), self.sign

    def apply_gate(self, gate: FrameGate) -> SymbolicPauliWord:
        """Return ``gate * self * gate†`` exactly as Boolean polynomials."""

        x, z, sign = self._dicts()
        if gate.kind is FrameGateKind.H:
            qubit = gate.support[0]
            old_x = _poly_get(x, qubit)
            old_z = _poly_get(z, qubit)
            sign = sign.xor(old_x.multiply(old_z))
            _poly_set(x, qubit, old_z)
            _poly_set(z, qubit, old_x)
        elif gate.kind is FrameGateKind.X:
            sign = sign.xor(_poly_get(z, gate.support[0]))
        elif gate.kind is FrameGateKind.Z:
            sign = sign.xor(_poly_get(x, gate.support[0]))
        elif gate.kind is FrameGateKind.CNOT:
            control, target = gate.support
            xc = _poly_get(x, control)
            xt = _poly_get(x, target)
            zc = _poly_get(z, control)
            zt = _poly_get(z, target)
            phase = xc.multiply(zt).multiply(
                xt.xor(zc).xor(BooleanPolynomial.one())
            )
            sign = sign.xor(phase)
            _poly_set(x, target, xt.xor(xc))
            _poly_set(z, control, zc.xor(zt))
        elif gate.kind is FrameGateKind.CZ:
            control, target = gate.support
            return (
                self.apply_gate(FrameGate(FrameGateKind.H, (target,)))
                .apply_gate(FrameGate(FrameGateKind.CNOT, (control, target)))
                .apply_gate(FrameGate(FrameGateKind.H, (target,)))
            )
        else:  # pragma: no cover - Enum makes this unreachable
            raise DirectCczPpmTraceError("unsupported frame gate")
        return self._from_dicts(x, z, sign)

    def select(
        self,
        transformed: SymbolicPauliWord,
        condition: BooleanPolynomial,
    ) -> SymbolicPauliWord:
        """Choose ``transformed`` iff ``condition`` evaluates to one."""

        old_x, old_z, old_sign = self._dicts()
        new_x, new_z, new_sign = transformed._dicts()
        selected_x: dict[str, BooleanPolynomial] = {}
        selected_z: dict[str, BooleanPolynomial] = {}
        for logical in sorted(set(old_x) | set(new_x)):
            old = _poly_get(old_x, logical)
            new = _poly_get(new_x, logical)
            _poly_set(selected_x, logical, old.xor(condition.multiply(old.xor(new))))
        for logical in sorted(set(old_z) | set(new_z)):
            old = _poly_get(old_z, logical)
            new = _poly_get(new_z, logical)
            _poly_set(selected_z, logical, old.xor(condition.multiply(old.xor(new))))
        selected_sign = old_sign.xor(condition.multiply(old_sign.xor(new_sign)))
        return self._from_dicts(selected_x, selected_z, selected_sign)

    def apply_frame_term(self, term: SymbolicFrameTerm) -> SymbolicPauliWord:
        transformed = self
        for gate in term.circuit:
            transformed = transformed.apply_gate(gate)
        return self.select(transformed, term.condition)

    def presented_under_correction_frame(
        self,
        frame_terms: tuple[SymbolicFrameTerm, ...],
    ) -> SymbolicPauliWord:
        """Return the physical observable ``C† self C`` for correction ``C``."""

        observable = self
        for term in reversed(frame_terms):
            observable = observable.apply_frame_term(term)
        return observable

    def evaluate(
        self,
        assignment: dict[str, int],
    ) -> tuple[int, tuple[tuple[str, str], ...]]:
        x = {logical: poly.evaluate(assignment) for logical, poly in self.x_components}
        z = {logical: poly.evaluate(assignment) for logical, poly in self.z_components}
        support = []
        for logical in sorted(set(x) | set(z)):
            bits = (x.get(logical, 0), z.get(logical, 0))
            term = {(0, 0): "I", (1, 0): "X", (0, 1): "Z", (1, 1): "Y"}[bits]
            if term != "I":
                support.append((logical, term))
        return self.sign.evaluate(assignment), tuple(support)


def _presented_observable(
    logical_support: tuple[str, ...],
    pauli_terms: tuple[str, ...],
    frame_terms: tuple[SymbolicFrameTerm, ...],
) -> SymbolicPauliWord:
    observable = SymbolicPauliWord.from_terms(logical_support, pauli_terms)
    # The ordered terms encode the correction-to-apply C in circuit order, so
    # the uncorrected physical state is C†|logical>. A later logical PPM P must
    # therefore be presented physically as C† P C. Applying the conditional
    # conjugations in reverse term order implements that inverse circuit.
    return observable.presented_under_correction_frame(frame_terms)


def _split_top_level(expression: str, operator: str) -> tuple[str, ...]:
    depth = 0
    start = 0
    pieces: list[str] = []
    needle = f" {operator} "
    index = 0
    while index < len(expression):
        character = expression[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                raise DirectCczPpmTraceError("unbalanced Boolean expression")
        elif depth == 0 and expression.startswith(needle, index):
            pieces.append(expression[start:index])
            index += len(needle)
            start = index
            continue
        index += 1
    if depth != 0:
        raise DirectCczPpmTraceError("unbalanced Boolean expression")
    pieces.append(expression[start:])
    return tuple(pieces)


def _strip_outer_parentheses(expression: str) -> str:
    result = expression.strip()
    while result.startswith("(") and result.endswith(")"):
        depth = 0
        encloses_all = True
        for index, character in enumerate(result):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(result) - 1:
                    encloses_all = False
                    break
        if not encloses_all or depth != 0:
            break
        result = result[1:-1].strip()
    return result


def parse_boolean_expression(expression: str) -> BooleanPolynomial:
    """Parse the exact-map XOR/AND language into canonical ANF."""

    normalized = _strip_outer_parentheses(expression)
    xor_parts = _split_top_level(normalized, "XOR")
    if len(xor_parts) > 1:
        result = BooleanPolynomial.zero()
        for part in xor_parts:
            result = result.xor(parse_boolean_expression(part))
        return result
    and_parts = _split_top_level(normalized, "AND")
    if len(and_parts) > 1:
        result = BooleanPolynomial.one()
        for part in and_parts:
            result = result.multiply(parse_boolean_expression(part))
        return result
    if normalized == "0":
        return BooleanPolynomial.zero()
    if normalized == "1":
        return BooleanPolynomial.one()
    if not normalized or any(character.isspace() for character in normalized):
        raise DirectCczPpmTraceError(f"invalid Boolean token {normalized!r}")
    return BooleanPolynomial.variable(normalized)


_CORRECTION_RE = re.compile(r"^(CZ|X|Z)\(([^)]*)\)\^(.*)$")


def _parse_correction(expression: str) -> tuple[FrameGate, BooleanPolynomial]:
    match = _CORRECTION_RE.fullmatch(expression)
    if match is None:
        raise DirectCczPpmTraceError(f"unsupported correction expression {expression!r}")
    raw_kind, raw_support, raw_condition = match.groups()
    support = tuple(item.strip() for item in raw_support.split(","))
    return (
        FrameGate(FrameGateKind(raw_kind), support),
        parse_boolean_expression(raw_condition),
    )


def _end_of_injection_correction_terms(
    event: DirectCczInjectionEvent,
) -> tuple[SymbolicFrameTerm, ...]:
    """Move pre-H CZ fixups to the event boundary, then append post-H Paulis."""

    target = event.data[2]
    result: list[SymbolicFrameTerm] = []
    for index, expression in enumerate(event.correction_frame):
        gate, condition = _parse_correction(expression)
        role = "post_h_pauli"
        if index < 3:
            role = "pre_h_cz_conjugated_to_event_boundary"
            if gate.kind is not FrameGateKind.CZ:
                raise DirectCczPpmTraceError("first three corrections must be CZ")
            if target in gate.support:
                control = gate.support[0] if gate.support[1] == target else gate.support[1]
                gate = FrameGate(FrameGateKind.CNOT, (control, target))
        result.append(
            SymbolicFrameTerm(
                term_id=f"{event.event_id}:frame-term:{index}",
                origin_event_id=event.event_id,
                condition=condition,
                circuit=(gate,),
                correction_role=role,
            )
        )
    return tuple(result)


def _conjugate_frame_by_gate(
    terms: tuple[SymbolicFrameTerm, ...],
    gate: FrameGate,
) -> tuple[SymbolicFrameTerm, ...]:
    return tuple(
        replace(term, circuit=_normalize_circuit((gate, *term.circuit, gate)))
        for term in terms
    )


def _polynomial_to_data(polynomial: BooleanPolynomial) -> dict[str, Any]:
    return {
        "anf_monomials": [list(monomial) for monomial in polynomial.monomials],
        "expression": polynomial.to_expression(),
        "variables": list(polynomial.variables),
    }


def _frame_gate_to_data(gate: FrameGate) -> dict[str, Any]:
    return {"kind": gate.kind.value, "support": list(gate.support)}


def _frame_term_to_data(term: SymbolicFrameTerm) -> dict[str, Any]:
    return {
        "circuit": [_frame_gate_to_data(gate) for gate in term.circuit],
        "condition": _polynomial_to_data(term.condition),
        "correction_role": term.correction_role,
        "origin_event_id": term.origin_event_id,
        "term_id": term.term_id,
    }


def _frame_signature(terms: tuple[SymbolicFrameTerm, ...]) -> str:
    payload = json.dumps(
        [_frame_term_to_data(term) for term in terms],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest().upper()


@dataclass(frozen=True, slots=True)
class SymbolicFrameSnapshot:
    """One canonical frame at a source macro-layer boundary."""

    signature: str
    terms: tuple[SymbolicFrameTerm, ...]

    def __post_init__(self) -> None:
        if self.signature != _frame_signature(self.terms):
            raise DirectCczPpmTraceError("frame signature does not match its terms")
        term_ids = tuple(term.term_id for term in self.terms)
        if len(term_ids) != len(set(term_ids)):
            raise DirectCczPpmTraceError("frame term IDs must be unique")


def _snapshot(terms: tuple[SymbolicFrameTerm, ...]) -> SymbolicFrameSnapshot:
    return SymbolicFrameSnapshot(signature=_frame_signature(terms), terms=terms)


@dataclass(frozen=True, slots=True)
class SymbolicPpmMeasurement:
    """One injection PPM after exact conjugation by the incoming frame."""

    operation_id: str
    source_gate_id: str
    injection_event_id: str
    source_algorithmic_layer: int
    injection_layer: int
    logical_support: tuple[str, ...]
    pauli_terms: tuple[str, ...]
    outcome_token: str
    frame_in_signature: str
    presented_observable: SymbolicPauliWord
    predecessor_operation_ids: tuple[str, ...]
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.operation_id or not self.source_gate_id or not self.outcome_token:
            raise DirectCczPpmTraceError("PPM identity cannot be empty")
        if self.source_algorithmic_layer < 1 or self.injection_layer not in {1, 2}:
            raise DirectCczPpmTraceError("PPM layers are invalid")
        if len(self.logical_support) != len(self.pauli_terms):
            raise DirectCczPpmTraceError("PPM support and terms must align")


@dataclass(frozen=True, slots=True)
class SymbolicCliffordInstruction:
    """An implementation-neutral logical Clifford with frame context."""

    operation_id: str
    source_gate_id: str
    role: str
    logical_gate: FrameGate
    frame_in_signature: str
    frame_out_signature: str
    presented_as: str
    predecessor_operation_ids: tuple[str, ...]
    evidence_status: EvidenceStatus
    finite_cost_status: EvidenceStatus = EvidenceStatus.OPEN


@dataclass(frozen=True, slots=True)
class SymbolicCorrectionUpdate:
    """One deferred correction inserted into the symbolic frame."""

    update_id: str
    source_gate_id: str
    injection_event_id: str
    frame_term: SymbolicFrameTerm
    outcome_dependencies: tuple[str, ...]
    resulting_frame_signature: str

    def __post_init__(self) -> None:
        if set(self.outcome_dependencies) != set(self.frame_term.condition.variables):
            raise DirectCczPpmTraceError(
                "correction dependencies must equal condition variables"
            )


@dataclass(frozen=True, slots=True)
class SymbolicInjectionRecord:
    """One source Toffoli expanded into the symbolic injection program."""

    event_id: str
    completion_id: str
    source_gate_id: str
    source_algorithmic_layer: int
    data: tuple[str, str, str]
    resource: tuple[str, str, str]
    basis_change_before_id: str
    ppm_operation_ids: tuple[str, ...]
    correction_update_ids: tuple[str, ...]
    basis_change_after_id: str
    completion_predecessor_ids: tuple[str, ...]
    frame_in_signature: str
    frame_out_signature: str


@dataclass(frozen=True, slots=True)
class SymbolicSourceOperation:
    """One source gate and its complete lowering provenance."""

    source_gate_id: str
    source_kind: str
    source_algorithmic_layer: int
    source_stage: str
    logical_support: tuple[str, ...]
    lowering_kind: str
    emitted_operation_ids: tuple[str, ...]
    frame_in_signature: str
    frame_out_signature: str


@dataclass(frozen=True, slots=True)
class MacroLayerFrame:
    """Canonical frame transition across one source macro layer."""

    source_algorithmic_layer: int
    source_gate_ids: tuple[str, ...]
    frame_in: SymbolicFrameSnapshot
    frame_out: SymbolicFrameSnapshot


@dataclass(frozen=True, slots=True)
class LogicalLifetime:
    """Source logical-value lifetime in source-operation coordinates."""

    logical_value: str
    role: str
    origin: str
    first_source_gate_id: str
    last_source_gate_id: str
    first_source_layer: int
    last_source_layer: int


@dataclass(frozen=True, slots=True)
class ResourceLifetime:
    """One consumed CCZ resource triple's measured lifetime."""

    injection_event_id: str
    resource_values: tuple[str, str, str]
    first_ppm_operation_ids: tuple[str, ...]
    terminal_ppm_operation_ids: tuple[str, ...]
    consumed: bool


@dataclass(frozen=True, slots=True)
class SymbolicDirectCczPpmTrace:
    """Validated Phase-A symbolic PPM/frame trace."""

    trace_id: str
    source_trace_id: str
    source_trace_schema_version: int
    width: int
    capability_id: str
    source_operations: tuple[SymbolicSourceOperation, ...]
    injections: tuple[SymbolicInjectionRecord, ...]
    ppms: tuple[SymbolicPpmMeasurement, ...]
    clifford_instructions: tuple[SymbolicCliffordInstruction, ...]
    correction_updates: tuple[SymbolicCorrectionUpdate, ...]
    macro_layer_frames: tuple[MacroLayerFrame, ...]
    source_dependencies: tuple[DirectCczSourceDependency, ...]
    logical_lifetimes: tuple[LogicalLifetime, ...]
    resource_lifetimes: tuple[ResourceLifetime, ...]
    compiler_ancilla_lifetimes: tuple[LogicalLifetime, ...]
    outcome_bit_convention: str = OUTCOME_BIT_CONVENTION
    frame_normal_form: str = FRAME_NORMAL_FORM
    complete_native_schedule: bool = False
    schema: str = DIRECT_CCZ_PPM_TRACE_SCHEMA
    schema_version: int = DIRECT_CCZ_PPM_TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trace_id or not self.source_trace_id or self.width < 2:
            raise DirectCczPpmTraceError("trace identity and width are required")
        if self.schema != DIRECT_CCZ_PPM_TRACE_SCHEMA or self.schema_version != 1:
            raise DirectCczPpmTraceError("unsupported symbolic PPM schema")
        if self.frame_normal_form != FRAME_NORMAL_FORM:
            raise DirectCczPpmTraceError("unsupported frame normal form")
        if self.outcome_bit_convention != OUTCOME_BIT_CONVENTION:
            raise DirectCczPpmTraceError("unsupported outcome convention")
        if self.complete_native_schedule:
            raise DirectCczPpmTraceError("Phase A cannot claim a native schedule")
        source_ids = tuple(operation.source_gate_id for operation in self.source_operations)
        if len(source_ids) != len(set(source_ids)):
            raise DirectCczPpmTraceError("source operations must be unique")
        event_source_ids = {injection.source_gate_id for injection in self.injections}
        clifford_source_ids = {
            instruction.source_gate_id
            for instruction in self.clifford_instructions
            if instruction.role in {"passthrough_cnot", "passthrough_x"}
        }
        if event_source_ids | clifford_source_ids != set(source_ids):
            raise DirectCczPpmTraceError("every source gate must be lowered exactly once")
        outcome_tokens = tuple(ppm.outcome_token for ppm in self.ppms)
        if len(outcome_tokens) != len(set(outcome_tokens)):
            raise DirectCczPpmTraceError("PPM outcomes must be unique")
        if len(self.ppms) != 6 * len(self.injections):
            raise DirectCczPpmTraceError("each injection must contain six PPMs")
        if len(self.correction_updates) != 6 * len(self.injections):
            raise DirectCczPpmTraceError("each injection must contain six corrections")
        known_outcomes = set(outcome_tokens)
        if any(
            not set(update.outcome_dependencies) <= known_outcomes
            for update in self.correction_updates
        ):
            raise DirectCczPpmTraceError("correction references an unknown outcome")
        expected_layers = tuple(range(1, len(self.macro_layer_frames) + 1))
        observed_layers = tuple(
            layer.source_algorithmic_layer for layer in self.macro_layer_frames
        )
        if observed_layers != expected_layers:
            raise DirectCczPpmTraceError("macro-layer frames must be contiguous")
        for previous, current in zip(
            self.macro_layer_frames,
            self.macro_layer_frames[1:],
            strict=False,
        ):
            if previous.frame_out.signature != current.frame_in.signature:
                raise DirectCczPpmTraceError("macro-layer frame chain is broken")
        if self.compiler_ancilla_lifetimes:
            raise DirectCczPpmTraceError(
                "the direct six-PPM contract introduces no compiler ancilla"
            )


def _source_predecessors(
    trace: OopQclaTrace | QclaTrace,
) -> dict[str, tuple[str, ...]]:
    gates = cast(tuple[OopQclaGate | QclaGate, ...], trace.gates)
    result: dict[str, list[str]] = {gate.gate_id: [] for gate in gates}
    for dependency in trace.dependencies:
        result[dependency.successor].append(dependency.predecessor)
    order = {gate.gate_id: index for index, gate in enumerate(gates)}
    return {
        gate_id: tuple(sorted(predecessors, key=order.__getitem__))
        for gate_id, predecessors in result.items()
    }


def _oop_logical_lifetimes(trace: OopQclaTrace) -> tuple[LogicalLifetime, ...]:
    uses: dict[str, list[OopQclaGate]] = {}
    for gate in trace.gates:
        for logical in gate.logical_support:
            uses.setdefault(logical, []).append(gate)
    result = []
    for logical, gates in sorted(uses.items()):
        if logical.startswith("p:"):
            role = "source_clean_ancilla"
            origin = "clean_zero"
        elif logical.startswith("z:"):
            role = "source_output_workspace"
            origin = "clean_zero"
        else:
            role = "source_input_inout"
            origin = "source_input"
        result.append(
            LogicalLifetime(
                logical_value=logical,
                role=role,
                origin=origin,
                first_source_gate_id=gates[0].gate_id,
                last_source_gate_id=gates[-1].gate_id,
                first_source_layer=gates[0].algorithmic_layer,
                last_source_layer=gates[-1].algorithmic_layer,
            )
        )
    return tuple(result)


def _ip_logical_lifetimes(trace: QclaTrace) -> tuple[LogicalLifetime, ...]:
    uses: dict[str, list[QclaGate]] = {}
    for gate in trace.gates:
        for logical in gate.logical_support:
            uses.setdefault(logical, []).append(gate)
    result = []
    for logical, gates in sorted(uses.items()):
        if logical.startswith("p:"):
            role = "source_prefix_scratch_ancilla"
            origin = "clean_zero"
        elif logical.startswith("z:"):
            role = "source_carry_ancilla"
            origin = "clean_zero"
        else:
            role = "source_input_inout"
            origin = "source_input"
        result.append(
            LogicalLifetime(
                logical_value=logical,
                role=role,
                origin=origin,
                first_source_gate_id=gates[0].gate_id,
                last_source_gate_id=gates[-1].gate_id,
                first_source_layer=gates[0].algorithmic_layer,
                last_source_layer=gates[-1].algorithmic_layer,
            )
        )
    return tuple(result)


def _lower_qcla_to_symbolic_direct_ccz_ppm(
    trace: OopQclaTrace | QclaTrace,
    event_trace: DirectCczEventTrace,
    logical_lifetimes: tuple[LogicalLifetime, ...],
) -> SymbolicDirectCczPpmTrace:
    """Lower one supported QCLA trace to the shared unscheduled PPM/frame IR."""

    events_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    predecessors = _source_predecessors(trace)
    terminal_by_source: dict[str, str] = {}
    frame_terms: tuple[SymbolicFrameTerm, ...] = ()

    source_operations: list[SymbolicSourceOperation] = []
    injections: list[SymbolicInjectionRecord] = []
    ppms: list[SymbolicPpmMeasurement] = []
    cliffords: list[SymbolicCliffordInstruction] = []
    corrections: list[SymbolicCorrectionUpdate] = []
    macro_frames: list[MacroLayerFrame] = []
    resources: list[ResourceLifetime] = []

    by_layer: dict[int, list[OopQclaGate | QclaGate]] = {}
    for gate in trace.gates:
        by_layer.setdefault(gate.algorithmic_layer, []).append(gate)

    for layer in sorted(by_layer):
        layer_in = _snapshot(frame_terms)
        layer_gate_ids = tuple(gate.gate_id for gate in by_layer[layer])
        for gate in by_layer[layer]:
            operation_frame_in = _snapshot(frame_terms)
            source_predecessor_operations = tuple(
                terminal_by_source[source_id]
                for source_id in predecessors[gate.gate_id]
            )
            if gate.kind in {QclaGateKind.CNOT, QclaGateKind.X}:
                if gate.kind is QclaGateKind.CNOT:
                    logical_gate = FrameGate(
                        FrameGateKind.CNOT,
                        (gate.controls[0], gate.target),
                    )
                    passthrough_role = "passthrough_cnot"
                    operation_id = f"{gate.gate_id}:passthrough-cnot"
                    presented_name = "CNOT"
                else:
                    logical_gate = FrameGate(FrameGateKind.X, (gate.target,))
                    passthrough_role = "passthrough_x"
                    operation_id = f"{gate.gate_id}:passthrough-x"
                    presented_name = "X"
                frame_terms = _conjugate_frame_by_gate(frame_terms, logical_gate)
                operation_frame_out = _snapshot(frame_terms)
                cliffords.append(
                    SymbolicCliffordInstruction(
                        operation_id=operation_id,
                        source_gate_id=gate.gate_id,
                        role=passthrough_role,
                        logical_gate=logical_gate,
                        frame_in_signature=operation_frame_in.signature,
                        frame_out_signature=operation_frame_out.signature,
                        presented_as=(
                            f"BARE_LOGICAL_{presented_name}_FRAME_UPDATE("
                            f"{operation_frame_in.signature},"
                            f"{presented_name}({','.join(logical_gate.support)}))"
                        ),
                        predecessor_operation_ids=source_predecessor_operations,
                        evidence_status=gate.semantic_evidence_status,
                    )
                )
                terminal_by_source[gate.gate_id] = operation_id
                source_operations.append(
                    SymbolicSourceOperation(
                        source_gate_id=gate.gate_id,
                        source_kind=gate.kind.value,
                        source_algorithmic_layer=gate.algorithmic_layer,
                        source_stage=gate.stage.value,
                        logical_support=gate.logical_support,
                        lowering_kind=(
                            f"implementation_neutral_{passthrough_role}"
                        ),
                        emitted_operation_ids=(operation_id,),
                        frame_in_signature=operation_frame_in.signature,
                        frame_out_signature=operation_frame_out.signature,
                    )
                )
                continue
            if gate.kind is not QclaGateKind.TOFFOLI:
                raise DirectCczPpmTraceError(
                    "direct-CCZ QCLA compiler accepts X/CNOT/CCX"
                )

            event = events_by_source[gate.gate_id]
            basis_before_id = f"{event.event_id}:basis-before"
            basis_after_id = f"{event.event_id}:basis-after"
            cliffords.append(
                SymbolicCliffordInstruction(
                    operation_id=basis_before_id,
                    source_gate_id=gate.gate_id,
                    role="injection_basis_change_before",
                    logical_gate=FrameGate(FrameGateKind.H, (gate.target,)),
                    frame_in_signature=operation_frame_in.signature,
                    frame_out_signature=operation_frame_in.signature,
                    presented_as=(
                        f"FRAME_CONJUGATE({operation_frame_in.signature},H({gate.target}))"
                    ),
                    predecessor_operation_ids=source_predecessor_operations,
                    evidence_status=event.evidence_status,
                )
            )
            layer_one_ids = tuple(
                ppm.event_id for ppm in event.ppms if ppm.layer == 1
            )
            event_ppm_ids: list[str] = []
            for ppm in event.ppms:
                ppm_predecessors: tuple[str, ...]
                if ppm.layer == 1:
                    ppm_predecessors = (basis_before_id,)
                else:
                    ppm_predecessors = layer_one_ids
                ppms.append(
                    SymbolicPpmMeasurement(
                        operation_id=ppm.event_id,
                        source_gate_id=gate.gate_id,
                        injection_event_id=event.event_id,
                        source_algorithmic_layer=gate.algorithmic_layer,
                        injection_layer=ppm.layer,
                        logical_support=ppm.logical_support,
                        pauli_terms=ppm.pauli_terms,
                        outcome_token=ppm.outcome_token,
                        frame_in_signature=operation_frame_in.signature,
                        presented_observable=_presented_observable(
                            ppm.logical_support,
                            ppm.pauli_terms,
                            frame_terms,
                        ),
                        predecessor_operation_ids=ppm_predecessors,
                        evidence_status=ppm.evidence_status,
                    )
                )
                event_ppm_ids.append(ppm.event_id)

            cliffords.append(
                SymbolicCliffordInstruction(
                    operation_id=basis_after_id,
                    source_gate_id=gate.gate_id,
                    role="injection_basis_change_after",
                    logical_gate=FrameGate(FrameGateKind.H, (gate.target,)),
                    frame_in_signature=operation_frame_in.signature,
                    frame_out_signature=operation_frame_in.signature,
                    presented_as=(
                        f"FRAME_CONJUGATE({operation_frame_in.signature},H({gate.target}))"
                    ),
                    predecessor_operation_ids=layer_one_ids,
                    evidence_status=event.evidence_status,
                )
            )

            new_terms = _end_of_injection_correction_terms(event)
            accumulated_new: list[SymbolicFrameTerm] = []
            for term in new_terms:
                accumulated_new.append(term)
                partial_frame = _snapshot(frame_terms + tuple(accumulated_new))
                corrections.append(
                    SymbolicCorrectionUpdate(
                        update_id=f"{term.term_id}:update",
                        source_gate_id=gate.gate_id,
                        injection_event_id=event.event_id,
                        frame_term=term,
                        outcome_dependencies=term.condition.variables,
                        resulting_frame_signature=partial_frame.signature,
                    )
                )
            # The list is circuit order for the correction-to-apply. Appending
            # the event corrections encodes C_new C_in at the operator level.
            frame_terms = frame_terms + new_terms
            operation_frame_out = _snapshot(frame_terms)
            completion_id = f"{event.event_id}:complete"
            terminal_by_source[gate.gate_id] = completion_id
            correction_ids = tuple(
                f"{term.term_id}:update" for term in new_terms
            )
            injections.append(
                SymbolicInjectionRecord(
                    event_id=event.event_id,
                    completion_id=completion_id,
                    source_gate_id=gate.gate_id,
                    source_algorithmic_layer=gate.algorithmic_layer,
                    data=event.data,
                    resource=event.resource,
                    basis_change_before_id=basis_before_id,
                    ppm_operation_ids=tuple(event_ppm_ids),
                    correction_update_ids=correction_ids,
                    basis_change_after_id=basis_after_id,
                    completion_predecessor_ids=(basis_after_id, *correction_ids),
                    frame_in_signature=operation_frame_in.signature,
                    frame_out_signature=operation_frame_out.signature,
                )
            )
            source_operations.append(
                SymbolicSourceOperation(
                    source_gate_id=gate.gate_id,
                    source_kind=gate.kind.value,
                    source_algorithmic_layer=gate.algorithmic_layer,
                    source_stage=gate.stage.value,
                    logical_support=gate.logical_support,
                    lowering_kind="direct_ccz_six_ppm_symbolic_frame",
                    emitted_operation_ids=(
                        basis_before_id,
                        *event_ppm_ids,
                        *correction_ids,
                        basis_after_id,
                        completion_id,
                    ),
                    frame_in_signature=operation_frame_in.signature,
                    frame_out_signature=operation_frame_out.signature,
                )
            )
            resources.append(
                ResourceLifetime(
                    injection_event_id=event.event_id,
                    resource_values=event.resource,
                    first_ppm_operation_ids=layer_one_ids,
                    terminal_ppm_operation_ids=tuple(
                        ppm.event_id for ppm in event.ppms if ppm.layer == 2
                    ),
                    consumed=event.resource_consumed,
                )
            )
        macro_frames.append(
            MacroLayerFrame(
                source_algorithmic_layer=layer,
                source_gate_ids=layer_gate_ids,
                frame_in=layer_in,
                frame_out=_snapshot(frame_terms),
            )
        )

    return SymbolicDirectCczPpmTrace(
        trace_id=f"{trace.trace_id}:symbolic-direct-ccz-ppm-v1",
        source_trace_id=trace.trace_id,
        source_trace_schema_version=trace.schema_version,
        width=trace.width,
        capability_id=event_trace.capability_id,
        source_operations=tuple(source_operations),
        injections=tuple(injections),
        ppms=tuple(ppms),
        clifford_instructions=tuple(cliffords),
        correction_updates=tuple(corrections),
        macro_layer_frames=tuple(macro_frames),
        source_dependencies=event_trace.source_dependencies,
        logical_lifetimes=logical_lifetimes,
        resource_lifetimes=tuple(resources),
        compiler_ancilla_lifetimes=(),
    )


def lower_oop_qcla_to_symbolic_direct_ccz_ppm(
    trace: OopQclaTrace,
    capability: DirectCczCapability,
) -> SymbolicDirectCczPpmTrace:
    """Lower an OOP-QCLA trace to an unscheduled symbolic PPM/frame program."""

    return _lower_qcla_to_symbolic_direct_ccz_ppm(
        trace,
        lower_oop_qcla_to_direct_ccz_events(trace, capability),
        _oop_logical_lifetimes(trace),
    )


def lower_qcla_to_symbolic_direct_ccz_ppm(
    trace: QclaTrace,
    capability: DirectCczCapability,
) -> SymbolicDirectCczPpmTrace:
    """Lower reviewed in-place QCLA without routing through seven-T expansion."""

    return _lower_qcla_to_symbolic_direct_ccz_ppm(
        trace,
        lower_qcla_to_direct_ccz_events(trace, capability),
        _ip_logical_lifetimes(trace),
    )


def _pauli_to_data(pauli: SymbolicPauliWord) -> dict[str, Any]:
    return {
        "sign": _polynomial_to_data(pauli.sign),
        "x_components": [
            {"logical_value": logical, "coefficient": _polynomial_to_data(poly)}
            for logical, poly in pauli.x_components
        ],
        "z_components": [
            {"logical_value": logical, "coefficient": _polynomial_to_data(poly)}
            for logical, poly in pauli.z_components
        ],
    }


def _snapshot_to_data(snapshot: SymbolicFrameSnapshot) -> dict[str, Any]:
    return {
        "normal_form": FRAME_NORMAL_FORM,
        "signature": snapshot.signature,
        "terms": [_frame_term_to_data(term) for term in snapshot.terms],
    }


def symbolic_direct_ccz_ppm_trace_to_data(
    trace: SymbolicDirectCczPpmTrace,
) -> dict[str, Any]:
    """Return a deterministic JSON-compatible symbolic PPM/frame trace."""

    return {
        "capability_id": trace.capability_id,
        "clifford_instructions": [
            {
                "evidence_status": instruction.evidence_status.value,
                "finite_cost_status": instruction.finite_cost_status.value,
                "frame_in_signature": instruction.frame_in_signature,
                "frame_out_signature": instruction.frame_out_signature,
                "logical_gate": _frame_gate_to_data(instruction.logical_gate),
                "operation_id": instruction.operation_id,
                "predecessor_operation_ids": list(
                    instruction.predecessor_operation_ids
                ),
                "presented_as": instruction.presented_as,
                "role": instruction.role,
                "source_gate_id": instruction.source_gate_id,
            }
            for instruction in trace.clifford_instructions
        ],
        "compiler_ancilla_lifetimes": [],
        "complete_native_schedule": trace.complete_native_schedule,
        "correction_updates": [
            {
                "frame_term": _frame_term_to_data(update.frame_term),
                "injection_event_id": update.injection_event_id,
                "outcome_dependencies": list(update.outcome_dependencies),
                "resulting_frame_signature": update.resulting_frame_signature,
                "source_gate_id": update.source_gate_id,
                "update_id": update.update_id,
            }
            for update in trace.correction_updates
        ],
        "frame_normal_form": trace.frame_normal_form,
        "injections": [
            {
                "basis_change_after_id": event.basis_change_after_id,
                "basis_change_before_id": event.basis_change_before_id,
                "completion_id": event.completion_id,
                "completion_predecessor_ids": list(
                    event.completion_predecessor_ids
                ),
                "correction_update_ids": list(event.correction_update_ids),
                "data": list(event.data),
                "event_id": event.event_id,
                "frame_in_signature": event.frame_in_signature,
                "frame_out_signature": event.frame_out_signature,
                "ppm_operation_ids": list(event.ppm_operation_ids),
                "resource": list(event.resource),
                "source_algorithmic_layer": event.source_algorithmic_layer,
                "source_gate_id": event.source_gate_id,
            }
            for event in trace.injections
        ],
        "logical_lifetimes": [
            {
                "first_source_gate_id": lifetime.first_source_gate_id,
                "first_source_layer": lifetime.first_source_layer,
                "last_source_gate_id": lifetime.last_source_gate_id,
                "last_source_layer": lifetime.last_source_layer,
                "logical_value": lifetime.logical_value,
                "origin": lifetime.origin,
                "role": lifetime.role,
            }
            for lifetime in trace.logical_lifetimes
        ],
        "macro_layer_frames": [
            {
                "frame_in": _snapshot_to_data(layer.frame_in),
                "frame_out": _snapshot_to_data(layer.frame_out),
                "source_algorithmic_layer": layer.source_algorithmic_layer,
                "source_gate_ids": list(layer.source_gate_ids),
            }
            for layer in trace.macro_layer_frames
        ],
        "outcome_bit_convention": trace.outcome_bit_convention,
        "ppms": [
            {
                "evidence_status": ppm.evidence_status.value,
                "frame_in_signature": ppm.frame_in_signature,
                "injection_event_id": ppm.injection_event_id,
                "injection_layer": ppm.injection_layer,
                "logical_support": list(ppm.logical_support),
                "operation_id": ppm.operation_id,
                "outcome_token": ppm.outcome_token,
                "pauli_terms": list(ppm.pauli_terms),
                "predecessor_operation_ids": list(ppm.predecessor_operation_ids),
                "presented_observable": _pauli_to_data(ppm.presented_observable),
                "source_algorithmic_layer": ppm.source_algorithmic_layer,
                "source_gate_id": ppm.source_gate_id,
            }
            for ppm in trace.ppms
        ],
        "resource_lifetimes": [
            {
                "consumed": lifetime.consumed,
                "first_ppm_operation_ids": list(lifetime.first_ppm_operation_ids),
                "injection_event_id": lifetime.injection_event_id,
                "resource_values": list(lifetime.resource_values),
                "terminal_ppm_operation_ids": list(
                    lifetime.terminal_ppm_operation_ids
                ),
            }
            for lifetime in trace.resource_lifetimes
        ],
        "schema": trace.schema,
        "schema_version": trace.schema_version,
        "source_dependencies": [
            {
                "logical_values": list(dependency.logical_values),
                "predecessor_source_gate_id": dependency.predecessor_source_gate_id,
                "reason": dependency.reason,
                "successor_source_gate_id": dependency.successor_source_gate_id,
            }
            for dependency in trace.source_dependencies
        ],
        "source_operations": [
            {
                "emitted_operation_ids": list(operation.emitted_operation_ids),
                "frame_in_signature": operation.frame_in_signature,
                "frame_out_signature": operation.frame_out_signature,
                "logical_support": list(operation.logical_support),
                "lowering_kind": operation.lowering_kind,
                "source_algorithmic_layer": operation.source_algorithmic_layer,
                "source_gate_id": operation.source_gate_id,
                "source_kind": operation.source_kind,
                "source_stage": operation.source_stage,
            }
            for operation in trace.source_operations
        ],
        "source_trace_id": trace.source_trace_id,
        "source_trace_schema_version": trace.source_trace_schema_version,
        "trace_id": trace.trace_id,
        "width": trace.width,
    }


def dumps_symbolic_direct_ccz_ppm_trace(trace: SymbolicDirectCczPpmTrace) -> str:
    """Serialize the trace canonically."""

    return json.dumps(
        symbolic_direct_ccz_ppm_trace_to_data(trace),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
