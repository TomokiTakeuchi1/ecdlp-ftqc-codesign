"""All-branch channel verification for the source-pinned CCZ-consumption circuit.

This module intentionally does not import the capability loader or event
compiler.  It reconstructs Figure 14(a) of Litinski--Nickerson independently
from six-qubit projectors and compares every measurement branch with ideal
CCX.  Outcome bit 0 denotes the +1 eigenspace and bit 1 the -1 eigenspace.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import import_module
from itertools import product
from typing import Any

np: Any = import_module("numpy")
ComplexArray = Any

OUTCOME_BIT_CONVENTION = "0 denotes +1 eigenvalue; 1 denotes -1 eigenvalue"

I = np.eye(2, dtype=np.complex128)
X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
PLUS = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)


@dataclass(frozen=True, slots=True)
class DirectCczBranchCorrection:
    """Corrections for one six-bit measurement branch of Figure 14(a)."""

    zz_bits: tuple[int, int, int]
    x_bits: tuple[int, int, int]
    conditional_cz_exponents: tuple[int, int, int]
    pauli_exponents: tuple[int, int, int]

    def __post_init__(self) -> None:
        bits = (*self.zz_bits, *self.x_bits)
        if any(bit not in {0, 1} for bit in bits):
            raise ValueError("direct-CCZ measurement outcomes must be bits")


@dataclass(frozen=True, slots=True)
class DirectCczInjectionChannelVerification:
    """Operator-level result for all measurement branches."""

    outcome_bit_convention: str
    branch_count: int
    nonzero_branch_count: int
    expected_branch_probability: float
    minimum_branch_probability: float
    maximum_branch_probability: float
    maximum_probability_error: float
    maximum_operator_frobenius_error: float
    tolerance: float
    all_passed: bool


def direct_ccz_branch_correction(
    zz_bits: tuple[int, int, int],
    x_bits: tuple[int, int, int],
) -> DirectCczBranchCorrection:
    """Return the Figure-14(a) corrections under the declared bit convention."""

    a, b, c = zz_bits
    x0, x1, x2 = x_bits
    return DirectCczBranchCorrection(
        zz_bits=zz_bits,
        x_bits=x_bits,
        # CZ(data_1,data_2)^a, CZ(data_0,data_2)^b,
        # CZ(data_0,data_1)^c.
        conditional_cz_exponents=(a, b, c),
        # Figure 14 applies these after the target Hadamard.
        pauli_exponents=(x0 ^ (b & c), x1 ^ (a & c), x2 ^ (a & b)),
    )


def _kron(*operators: ComplexArray) -> ComplexArray:
    result = np.array([[1]], dtype=np.complex128)
    for operator in operators:
        result = np.kron(result, operator)
    return result


def _on_qubit(operator: ComplexArray, qubit: int, qubit_count: int) -> ComplexArray:
    return _kron(
        *(operator if index == qubit else I for index in range(qubit_count))
    )


def _controlled_z(left: int, right: int, qubit_count: int) -> ComplexArray:
    if left == right:
        raise ValueError("CZ support must contain two distinct qubits")
    diagonal = np.ones(2**qubit_count, dtype=np.complex128)
    for basis in range(2**qubit_count):
        left_bit = (basis >> (qubit_count - 1 - left)) & 1
        right_bit = (basis >> (qubit_count - 1 - right)) & 1
        if left_bit and right_bit:
            diagonal[basis] = -1
    return np.diag(diagonal)


def _ccz_resource_state() -> ComplexArray:
    state = _kron(PLUS, PLUS, PLUS).reshape(8)
    state = state.copy()
    state[7] *= -1
    return state


def _ccx() -> ComplexArray:
    result = np.eye(8, dtype=np.complex128)
    result[6, 6] = 0
    result[7, 7] = 0
    result[6, 7] = 1
    result[7, 6] = 1
    return result


def _measurement_projector(observable: ComplexArray, bit: int) -> ComplexArray:
    dimension = observable.shape[0]
    return (np.eye(dimension, dtype=np.complex128) + (-1) ** bit * observable) / 2


def _branch_operator(
    zz_bits: tuple[int, int, int],
    x_bits: tuple[int, int, int],
) -> ComplexArray:
    qubit_count = 6
    data_qubits = 3
    full_identity = np.eye(2**qubit_count, dtype=np.complex128)
    h_target = _on_qubit(H, 2, qubit_count)
    resource = _ccz_resource_state()

    zz_projector = full_identity
    for index, bit in enumerate(zz_bits):
        observable = _on_qubit(Z, index, qubit_count) @ _on_qubit(
            Z, data_qubits + index, qubit_count
        )
        zz_projector = _measurement_projector(observable, bit) @ zz_projector

    correction = direct_ccz_branch_correction(zz_bits, x_bits)
    conditional_cz = full_identity
    for exponent, support in zip(
        correction.conditional_cz_exponents,
        ((1, 2), (0, 2), (0, 1)),
        strict=True,
    ):
        if exponent:
            conditional_cz = _controlled_z(*support, qubit_count) @ conditional_cz

    x_eigenstates = tuple(
        np.array([1, (-1) ** bit], dtype=np.complex128) / np.sqrt(2)
        for bit in x_bits
    )
    resource_bra = _kron(*x_eigenstates).reshape(8).conj()

    pauli = np.eye(2**data_qubits, dtype=np.complex128)
    if correction.pauli_exponents[0]:
        pauli = _on_qubit(Z, 0, data_qubits) @ pauli
    if correction.pauli_exponents[1]:
        pauli = _on_qubit(Z, 1, data_qubits) @ pauli
    if correction.pauli_exponents[2]:
        pauli = _on_qubit(X, 2, data_qubits) @ pauli

    columns = []
    for basis in range(2**data_qubits):
        data = np.eye(2**data_qubits, dtype=np.complex128)[:, basis]
        joint = np.kron(data, resource)
        joint = h_target @ joint
        joint = zz_projector @ joint
        joint = conditional_cz @ joint
        joint = h_target @ joint
        projected_data = joint.reshape((8, 8)) @ resource_bra
        columns.append(pauli @ projected_data)
    return np.column_stack(columns)


def verify_direct_ccz_injection_channel(
    *,
    tolerance: float = 1e-12,
) -> DirectCczInjectionChannelVerification:
    """Compare every nonzero Figure-14(a) branch with ideal CCX."""

    ideal = _ccx()
    expected_probability = 1.0 / 64.0
    probabilities: list[float] = []
    maximum_operator_error = 0.0
    maximum_probability_error = 0.0
    nonzero_branches = 0

    for raw_bits in product((0, 1), repeat=6):
        zz_bits = (raw_bits[0], raw_bits[1], raw_bits[2])
        x_bits = (raw_bits[3], raw_bits[4], raw_bits[5])
        branch = _branch_operator(zz_bits, x_bits)
        scalar = np.vdot(ideal, branch) / ideal.shape[0]
        probability = float(
            np.linalg.norm(branch, ord="fro") ** 2 / ideal.shape[0]
        )
        probabilities.append(probability)
        if probability > tolerance:
            nonzero_branches += 1
        maximum_operator_error = max(
            maximum_operator_error,
            float(np.linalg.norm(branch - scalar * ideal, ord="fro")),
        )
        maximum_probability_error = max(
            maximum_probability_error,
            abs(probability - expected_probability),
        )

    all_passed = (
        nonzero_branches == 64
        and maximum_operator_error <= tolerance
        and maximum_probability_error <= tolerance
    )
    return DirectCczInjectionChannelVerification(
        outcome_bit_convention=OUTCOME_BIT_CONVENTION,
        branch_count=64,
        nonzero_branch_count=nonzero_branches,
        expected_branch_probability=expected_probability,
        minimum_branch_probability=min(probabilities),
        maximum_branch_probability=max(probabilities),
        maximum_probability_error=maximum_probability_error,
        maximum_operator_frobenius_error=maximum_operator_error,
        tolerance=tolerance,
        all_passed=all_passed,
    )


def direct_ccz_injection_verification_to_data(
    verification: DirectCczInjectionChannelVerification,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible verification data."""

    return asdict(verification)
