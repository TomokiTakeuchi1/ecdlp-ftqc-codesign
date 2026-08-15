"""Small-system channel checks for the adaptive measurement gadgets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import import_module
from typing import Any

np: Any = import_module("numpy")
ComplexArray = Any

I = np.eye(2, dtype=np.complex128)
X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
S = np.diag([1, 1j]).astype(np.complex128)
S_DAGGER = S.conj().T
T = np.diag([1, np.exp(1j * np.pi / 4)]).astype(np.complex128)
T_DAGGER = T.conj().T
PLUS = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
ZERO = np.array([1, 0], dtype=np.complex128)
MAGIC_T = T @ PLUS
CNOT = np.array(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
    dtype=np.complex128,
)


@dataclass(frozen=True, slots=True)
class GadgetChannelVerification:
    """Numerical branchwise errors for the source-pinned gadget identities."""

    random_seed: int
    one_qubit_state_count: int
    two_qubit_state_count: int
    cnot_nonzero_branches: int
    h_nonzero_branches: int
    s_nonzero_branches: int
    t_nonzero_branches: int
    t_dagger_nonzero_branches: int
    cnot_max_frobenius_error: float
    h_max_frobenius_error: float
    s_max_frobenius_error: float
    t_max_frobenius_error: float
    t_dagger_max_frobenius_error: float

    @property
    def maximum_frobenius_error(self) -> float:
        return max(
            self.cnot_max_frobenius_error,
            self.h_max_frobenius_error,
            self.s_max_frobenius_error,
            self.t_max_frobenius_error,
            self.t_dagger_max_frobenius_error,
        )


def _kron(*operators: ComplexArray) -> ComplexArray:
    result = np.array([[1]], dtype=np.complex128)
    for operator in operators:
        result = np.kron(result, operator)
    return result


def _density(state: ComplexArray) -> ComplexArray:
    return np.outer(state, state.conj())


def _measure_branch(
    rho: ComplexArray,
    observable: ComplexArray,
    bit: int,
) -> tuple[float, ComplexArray]:
    projector = (np.eye(observable.shape[0], dtype=np.complex128) + (-1) ** bit * observable) / 2
    projected = projector @ rho @ projector
    probability = float(np.trace(projected).real)
    if probability <= 1e-14:
        return probability, projected
    return probability, projected / probability


def _partial_trace(
    rho: ComplexArray,
    *,
    keep: tuple[int, ...],
    qubit_count: int,
) -> ComplexArray:
    traced = [index for index in range(qubit_count) if index not in keep]
    tensor = rho.reshape((2,) * (2 * qubit_count))
    remaining = qubit_count
    for qubit in sorted(traced, reverse=True):
        tensor = np.trace(tensor, axis1=qubit, axis2=qubit + remaining)
        remaining -= 1
    return tensor.reshape((2 ** len(keep), 2 ** len(keep)))


def _normalized_random_state(rng: Any, dimension: int) -> ComplexArray:
    state = rng.normal(size=dimension) + 1j * rng.normal(size=dimension)
    return np.asarray(state / np.linalg.norm(state), dtype=np.complex128)


def _one_qubit_states(rng: Any) -> tuple[ComplexArray, ...]:
    basis = (
        ZERO,
        np.array([0, 1], dtype=np.complex128),
        PLUS,
        np.array([1, 1j], dtype=np.complex128) / np.sqrt(2),
    )
    return (*basis, *(_normalized_random_state(rng, 2) for _ in range(6)))


def _two_qubit_states(rng: Any) -> tuple[ComplexArray, ...]:
    basis = tuple(np.eye(4, dtype=np.complex128)[:, index] for index in range(4))
    bell = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
    return (*basis, bell, *(_normalized_random_state(rng, 4) for _ in range(6)))


def _verify_cnot(states: tuple[ComplexArray, ...]) -> tuple[float, int]:
    zz_control_scratch = _kron(Z, I, Z)
    xx_scratch_target = _kron(I, X, X)
    z_scratch = _kron(I, I, Z)
    maximum_error = 0.0
    branch_count = 0
    for state in states:
        initial = _density(np.kron(state, PLUS))
        expected = _density(CNOT @ state)
        for a in (0, 1):
            probability_a, after_a = _measure_branch(initial, zz_control_scratch, a)
            if probability_a <= 1e-14:
                continue
            for b in (0, 1):
                probability_b, after_b = _measure_branch(after_a, xx_scratch_target, b)
                if probability_b <= 1e-14:
                    continue
                for c in (0, 1):
                    probability_c, after_c = _measure_branch(after_b, z_scratch, c)
                    if probability_c <= 1e-14:
                        continue
                    correction = _kron(
                        Z if b else I,
                        X if a ^ c else I,
                        I,
                    )
                    corrected = correction @ after_c @ correction.conj().T
                    output = _partial_trace(corrected, keep=(0, 1), qubit_count=3)
                    maximum_error = max(
                        maximum_error,
                        float(np.linalg.norm(output - expected)),
                    )
                    branch_count += 1
    return maximum_error, branch_count


def _teleport_clifford_branch_errors(
    states: tuple[ComplexArray, ...],
    unitary: ComplexArray,
) -> tuple[float, int]:
    prepared = unitary @ PLUS
    conjugated_z = unitary @ Z @ unitary.conj().T
    conjugated_x = unitary @ X @ unitary.conj().T
    parity_observable = _kron(Z, conjugated_z)
    x_observable = _kron(X, I)
    maximum_error = 0.0
    branch_count = 0
    for state in states:
        initial = np.kron(_density(state), _density(prepared))
        expected = _density(unitary @ state)
        for parity_bit in (0, 1):
            probability_parity, after_parity = _measure_branch(
                initial, parity_observable, parity_bit
            )
            if probability_parity <= 1e-14:
                continue
            for x_bit in (0, 1):
                probability_x, after_x = _measure_branch(
                    after_parity, x_observable, x_bit
                )
                if probability_x <= 1e-14:
                    continue
                correction = np.linalg.matrix_power(conjugated_x, parity_bit)
                correction = correction @ np.linalg.matrix_power(conjugated_z, x_bit)
                full_correction = _kron(I, correction)
                corrected = full_correction @ after_x @ full_correction.conj().T
                output = _partial_trace(corrected, keep=(1,), qubit_count=2)
                maximum_error = max(
                    maximum_error,
                    float(np.linalg.norm(output - expected)),
                )
                branch_count += 1
    return maximum_error, branch_count


def _teleport_density_branch(
    input_density: ComplexArray,
    unitary: ComplexArray,
    parity_bit: int,
    x_bit: int,
) -> tuple[float, ComplexArray]:
    prepared = unitary @ PLUS
    initial = np.kron(input_density, _density(prepared))
    conjugated_z = unitary @ Z @ unitary.conj().T
    conjugated_x = unitary @ X @ unitary.conj().T
    probability_parity, after_parity = _measure_branch(
        initial, _kron(Z, conjugated_z), parity_bit
    )
    if probability_parity <= 1e-14:
        return probability_parity, after_parity
    probability_x, after_x = _measure_branch(after_parity, _kron(X, I), x_bit)
    if probability_x <= 1e-14:
        return probability_x, after_x
    correction = np.linalg.matrix_power(conjugated_x, parity_bit)
    correction = correction @ np.linalg.matrix_power(conjugated_z, x_bit)
    full_correction = _kron(I, correction)
    corrected = full_correction @ after_x @ full_correction.conj().T
    return probability_parity * probability_x, _partial_trace(
        corrected, keep=(1,), qubit_count=2
    )


def _verify_t(
    states: tuple[ComplexArray, ...],
    *,
    dagger: bool,
) -> tuple[float, int]:
    zz = _kron(Z, Z)
    magic_x = _kron(I, X)
    target = T_DAGGER if dagger else T
    maximum_error = 0.0
    branch_count = 0
    for state in states:
        initial = np.kron(_density(state), _density(MAGIC_T))
        expected = target @ _density(state) @ target.conj().T
        for r in (0, 1):
            probability_r, after_r = _measure_branch(initial, zz, r)
            if probability_r <= 1e-14:
                continue
            for b in (0, 1):
                probability_b, after_b = _measure_branch(after_r, magic_x, b)
                if probability_b <= 1e-14:
                    continue
                raw_data = _partial_trace(after_b, keep=(0,), qubit_count=2)
                if dagger:
                    adaptive_clifford = S_DAGGER if r == 0 else I
                else:
                    adaptive_clifford = I if r == 0 else S
                for c in (0, 1):
                    for d in (0, 1):
                        probability_cd, output = _teleport_density_branch(
                            raw_data,
                            adaptive_clifford,
                            c,
                            d,
                        )
                        if probability_cd <= 1e-14:
                            continue
                        if b:
                            output = Z @ output @ Z
                        maximum_error = max(
                            maximum_error,
                            float(np.linalg.norm(output - expected)),
                        )
                        branch_count += 1
    return maximum_error, branch_count


def verify_reference_gadget_channels(
    *,
    random_seed: int = 20260815,
) -> GadgetChannelVerification:
    """Verify every nonzero measurement branch on fixed and seeded states."""

    rng = np.random.default_rng(random_seed)
    one_qubit_states = _one_qubit_states(rng)
    two_qubit_states = _two_qubit_states(rng)
    cnot_error, cnot_branches = _verify_cnot(two_qubit_states)
    h_error, h_branches = _teleport_clifford_branch_errors(one_qubit_states, H)
    s_error, s_branches = _teleport_clifford_branch_errors(one_qubit_states, S)
    t_error, t_branches = _verify_t(one_qubit_states, dagger=False)
    t_dagger_error, t_dagger_branches = _verify_t(one_qubit_states, dagger=True)
    return GadgetChannelVerification(
        random_seed=random_seed,
        one_qubit_state_count=len(one_qubit_states),
        two_qubit_state_count=len(two_qubit_states),
        cnot_nonzero_branches=cnot_branches,
        h_nonzero_branches=h_branches,
        s_nonzero_branches=s_branches,
        t_nonzero_branches=t_branches,
        t_dagger_nonzero_branches=t_dagger_branches,
        cnot_max_frobenius_error=cnot_error,
        h_max_frobenius_error=h_error,
        s_max_frobenius_error=s_error,
        t_max_frobenius_error=t_error,
        t_dagger_max_frobenius_error=t_dagger_error,
    )


def gadget_verification_to_data(
    verification: GadgetChannelVerification,
) -> dict[str, Any]:
    """Return deterministic JSON data for an experiment artifact."""

    data = asdict(verification)
    data["maximum_frobenius_error"] = verification.maximum_frobenius_error
    return data
