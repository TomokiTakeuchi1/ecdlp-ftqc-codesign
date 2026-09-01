"""Independent logical-channel check for the AutoCCZ consumption adapter.

The AutoCCZ source proves each delayed-choice cell implements either CZ or
identity.  This module treats those three cells as the source-native carriers
of the standard CCZ-teleportation CZ corrections, reconstructs every
measurement branch without importing the direct-CCZ compiler or capability,
and compares the corrected data channel with ideal CCX.  It does not simulate
surface-code noise or prove the 3D lattice-surgery layout.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import import_module
from itertools import product
from typing import Any

np: Any = import_module("numpy")
ComplexArray = Any

AUTOCCZ_OUTCOME_BIT_CONVENTION = "0 denotes +1 eigenvalue; 1 denotes -1 eigenvalue"
AUTOCCZ_DELAYED_CHOICE_CZ_COUNT = 3
AUTOCCZ_ROUTING_QUBIT_COUNT = 6

I = np.eye(2, dtype=np.complex128)
X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
PLUS = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)


@dataclass(frozen=True, slots=True)
class AutoCczChannelVerification:
    """Operator-level verification of the abstract AutoCCZ consumption contract."""

    source_contract: str
    outcome_bit_convention: str
    delayed_choice_cz_count: int
    routing_qubit_count: int
    branch_count: int
    nonzero_branch_count: int
    expected_branch_probability: float
    minimum_branch_probability: float
    maximum_branch_probability: float
    maximum_probability_error: float
    maximum_operator_frobenius_error: float
    delayed_choice_truth_table_passed: bool
    tolerance: float
    all_passed: bool


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
    state = _kron(PLUS, PLUS, PLUS).reshape(8).copy()
    state[7] *= -1
    return state


def _ideal_ccx() -> ComplexArray:
    result = np.eye(8, dtype=np.complex128)
    result[6, 6] = 0
    result[7, 7] = 0
    result[6, 7] = 1
    result[7, 6] = 1
    return result


def _measurement_projector(observable: ComplexArray, bit: int) -> ComplexArray:
    dimension = observable.shape[0]
    return (np.eye(dimension, dtype=np.complex128) + (-1) ** bit * observable) / 2


def _delayed_choice_cz(
    choice_bit: int,
    left: int,
    right: int,
    qubit_count: int,
) -> ComplexArray:
    """Abstract Figure-3 cell: identity for 0 and CZ for 1."""

    if choice_bit not in {0, 1}:
        raise ValueError("delayed-choice control must be a bit")
    if choice_bit == 0:
        return np.eye(2**qubit_count, dtype=np.complex128)
    return _controlled_z(left, right, qubit_count)


def _branch_operator(raw_bits: tuple[int, ...]) -> ComplexArray:
    if len(raw_bits) != 6 or any(bit not in {0, 1} for bit in raw_bits):
        raise ValueError("AutoCCZ branch requires six measurement bits")
    a, b, c, x0, x1, x2 = raw_bits
    qubit_count = 6
    data_qubits = 3
    full_identity = np.eye(2**qubit_count, dtype=np.complex128)
    h_target = _on_qubit(H, 2, qubit_count)

    zz_projector = full_identity
    for index, bit in enumerate((a, b, c)):
        observable = _on_qubit(Z, index, qubit_count) @ _on_qubit(
            Z, data_qubits + index, qubit_count
        )
        zz_projector = _measurement_projector(observable, bit) @ zz_projector

    delayed_choices = full_identity
    for choice_bit, support in zip(
        (a, b, c),
        ((1, 2), (0, 2), (0, 1)),
        strict=True,
    ):
        delayed_choices = (
            _delayed_choice_cz(choice_bit, *support, qubit_count) @ delayed_choices
        )

    x_eigenstates = tuple(
        np.array([1, (-1) ** bit], dtype=np.complex128) / np.sqrt(2)
        for bit in (x0, x1, x2)
    )
    resource_bra = _kron(*x_eigenstates).reshape(8).conj()

    pauli = np.eye(2**data_qubits, dtype=np.complex128)
    if x0 ^ (b & c):
        pauli = _on_qubit(Z, 0, data_qubits) @ pauli
    if x1 ^ (a & c):
        pauli = _on_qubit(Z, 1, data_qubits) @ pauli
    if x2 ^ (a & b):
        pauli = _on_qubit(X, 2, data_qubits) @ pauli

    columns = []
    resource = _ccz_resource_state()
    for basis in range(2**data_qubits):
        data = np.eye(2**data_qubits, dtype=np.complex128)[:, basis]
        joint = np.kron(data, resource)
        joint = h_target @ joint
        joint = zz_projector @ joint
        joint = delayed_choices @ joint
        joint = h_target @ joint
        projected_data = joint.reshape((8, 8)) @ resource_bra
        columns.append(pauli @ projected_data)
    return np.column_stack(columns)


def _verify_delayed_choice_truth_table(tolerance: float) -> bool:
    identity = np.eye(8, dtype=np.complex128)
    cz = _controlled_z(0, 1, 3)
    return bool(
        np.linalg.norm(_delayed_choice_cz(0, 0, 1, 3) - identity, ord="fro")
        <= tolerance
        and np.linalg.norm(_delayed_choice_cz(1, 0, 1, 3) - cz, ord="fro")
        <= tolerance
    )


def verify_autoccz_consumption_channel(
    *, tolerance: float = 1e-12
) -> AutoCczChannelVerification:
    """Check all 64 abstract AutoCCZ-consumption branches against ideal CCX."""

    ideal = _ideal_ccx()
    expected_probability = 1.0 / 64.0
    probabilities: list[float] = []
    maximum_operator_error = 0.0
    maximum_probability_error = 0.0
    nonzero_branches = 0

    for raw_bits in product((0, 1), repeat=6):
        branch = _branch_operator(raw_bits)
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

    truth_table_passed = _verify_delayed_choice_truth_table(tolerance)
    all_passed = (
        nonzero_branches == 64
        and maximum_operator_error <= tolerance
        and maximum_probability_error <= tolerance
        and truth_table_passed
    )
    return AutoCczChannelVerification(
        source_contract=(
            "Gidney-Fowler AutoCCZ Figures 3-6 with each delayed-choice cell "
            "treated as the source-proved CZ/identity carrier"
        ),
        outcome_bit_convention=AUTOCCZ_OUTCOME_BIT_CONVENTION,
        delayed_choice_cz_count=AUTOCCZ_DELAYED_CHOICE_CZ_COUNT,
        routing_qubit_count=AUTOCCZ_ROUTING_QUBIT_COUNT,
        branch_count=64,
        nonzero_branch_count=nonzero_branches,
        expected_branch_probability=expected_probability,
        minimum_branch_probability=min(probabilities),
        maximum_branch_probability=max(probabilities),
        maximum_probability_error=maximum_probability_error,
        maximum_operator_frobenius_error=maximum_operator_error,
        delayed_choice_truth_table_passed=truth_table_passed,
        tolerance=tolerance,
        all_passed=all_passed,
    )


def autoccz_channel_verification_to_data(
    verification: AutoCczChannelVerification,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible verification data."""

    return asdict(verification)
