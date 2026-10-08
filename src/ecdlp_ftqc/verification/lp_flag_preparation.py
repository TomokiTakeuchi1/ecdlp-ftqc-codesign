"""Independent dense replay of two-pass, all-bracket flag preparation.

This module imports no construction or analysis implementation. The four-data
qubit fixture has overlapping and dependent checks, and enumerates the actual
ancilla measurement branches. It is a discriminating circuit check, not by
itself a full-size LP fault-tolerance certificate.

The branch-independent argument for Z-check preparation is as follows. Write
H for the measured check matrix. The uniform-plus target has Z stabilizers
row(H) and X stabilizers ker(H). An unflagged single fault in an all-bracket
gadget leaves either one data Pauli, a full measured Z check, or no data error.
In particular, Z_f Z_s after the opening flag CNOT can cancel its flag, but
its propagated data Z is the FULL check, hence harmless. A syndrome-Z fault
inside the data-CNOT sequence flags. All opposite-axis data error propagation
only changes measurement records, never another data qubit.

For a fault in pass one, the clean second pass reports delta = H e_x relative
to its ideal branch. Accepted equal records and any exact syndrome correction
therefore remove the X component modulo ker(H); the remaining Z component is
at most one-site modulo row(H). For a fault in pass two, clean pass one forces
accepted record delta = 0, and the unflagged output is already one-site modulo
row(H). Preparation and readout faults obey the same argument. This uses the
ACTUAL repeated same-axis records, not an ideal opposite-axis syndrome. The
X-check / uniform-zero case is the global-H dual. The full implementation must
add a declared schedule and exhaust its locations before claiming coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache, lru_cache
from typing import Any

import numpy as np
from numpy.typing import NDArray

_Array = NDArray[np.complex128]
_N = 4
_S = 4
_F = 5
_ROWS = (0b1111, 0b0101, 0b1010)
_TOL = 1e-12


@dataclass(frozen=True)
class _Fault:
    check: int
    stage: str
    gate: int = -1
    x: int = 0
    z: int = 0


@dataclass(frozen=True)
class _Branch:
    state: _Array
    syndrome: int
    flags: int
    probability: float


def _pauli(state: _Array, x: int, z: int) -> _Array:
    indices = np.arange(state.size)
    signs = np.array([1 - 2 * ((int(i) & z).bit_count() % 2) for i in indices])
    result = np.empty_like(state)
    result[indices ^ x] = state * signs
    return result


def _h(state: _Array, qubit: int) -> _Array:
    indices = np.arange(state.size)
    low = indices[indices & (1 << qubit) == 0]
    high = low | (1 << qubit)
    result = np.empty_like(state)
    result[low] = (state[low] + state[high]) / np.sqrt(2)
    result[high] = (state[low] - state[high]) / np.sqrt(2)
    return result


@cache
def _cnot_permutation(size: int, control: int, target: int) -> NDArray[np.int64]:
    indices = np.arange(size, dtype=np.int64)
    return indices ^ (((indices >> control) & 1) << target)


def _gates(row: int, axis: str) -> tuple[tuple[int, int], ...]:
    data = tuple(q for q in range(_N) if row >> q & 1)
    if axis == "Z":
        return ((_F, _S), *((q, _S) for q in data), (_F, _S))
    return ((_S, _F), *((_S, q) for q in data), (_S, _F))


def _initial_data(axis: str) -> _Array:
    state = np.zeros(1 << _N, dtype=np.complex128)
    state[0] = 1
    if axis == "Z":
        for qubit in range(_N):
            state = _h(state, qubit)
    return state


def _target(rows: tuple[int, ...], axis: str) -> _Array:
    # Independent projector definition; it does not replay a measurement gadget.
    state = np.array([
        1 if all((index & row).bit_count() % 2 == 0 for row in rows) else 0
        for index in range(1 << _N)
    ], dtype=np.complex128)
    state /= np.linalg.norm(state)
    if axis == "X":
        for qubit in range(_N):
            state = _h(state, qubit)
    return state


def _correction(rows: tuple[int, ...], syndrome: int) -> int | None:
    # Brute force is intentionally independent of the LP right-inverse solver.
    for support in range(1 << _N):
        actual = sum(((row & support).bit_count() % 2) << j for j, row in enumerate(rows))
        if actual == syndrome:
            return support
    return None


def _gadget(
    branch: _Branch, row: int, check: int, axis: str, fault: _Fault | None,
) -> list[_Branch]:
    state = np.zeros(1 << (_N + 2), dtype=np.complex128)
    state[:1 << _N] = branch.state
    state = _h(state, _F if axis == "Z" else _S)
    local = fault is not None and fault.check == check
    if local and fault is not None and fault.stage == "prep":
        state = _pauli(state, fault.x, fault.z)
    for index, (control, target) in enumerate(_gates(row, axis)):
        state = state[_cnot_permutation(state.size, control, target)]
        if (
            local and fault is not None and fault.gate == index
            and fault.stage in ("gate", "idle")
        ):
            state = _pauli(state, fault.x, fault.z)
    state = _h(state, _F if axis == "Z" else _S)
    result: list[_Branch] = []
    for syndrome in range(2):
        for flag in range(2):
            offset = (syndrome << _S) | (flag << _F)
            data = state[offset:offset + (1 << _N)].copy()
            probability = float(np.vdot(data, data).real)
            if probability < _TOL:
                continue
            data /= np.sqrt(probability)
            observed_syndrome, observed_flag = syndrome, flag
            if local and fault is not None and fault.stage == "readout":
                observed_syndrome ^= fault.x
                observed_flag ^= fault.z
            result.append(_Branch(
                data,
                branch.syndrome | (observed_syndrome << check),
                branch.flags | (observed_flag << check),
                branch.probability * probability,
            ))
    return result


def _run(
    rows: tuple[int, ...], axis: str, passes: int, fault: _Fault | None = None,
    *, require_flags: bool = True,
) -> tuple[list[_Branch], float]:
    state = _initial_data(axis)
    if fault is not None and fault.stage == "initial":
        state = _pauli(state, fault.x, fault.z)
    branches = [_Branch(state, 0, 0, 1.0)]
    for check in range(len(rows) * passes):
        branches = [
            child for branch in branches
            for child in _gadget(branch, rows[check % len(rows)], check, axis, fault)
        ]
    total_probability = sum(branch.probability for branch in branches)
    accepted: list[_Branch] = []
    mask = (1 << len(rows)) - 1
    for branch in branches:
        if require_flags and branch.flags:
            continue
        syndrome = branch.syndrome & mask
        if any((branch.syndrome >> (p * len(rows))) & mask != syndrome for p in range(passes)):
            continue
        support = _correction(rows, syndrome)
        if support is None:
            continue
        state = _pauli(branch.state, support if axis == "Z" else 0,
                       support if axis == "X" else 0)
        if fault is not None and fault.stage == "final_idle":
            state = _pauli(state, fault.x, fault.z)
        accepted.append(_Branch(state, branch.syndrome, branch.flags, branch.probability))
    return accepted, total_probability


def _single_paulis(qubit: int) -> tuple[tuple[int, int], ...]:
    return ((1 << qubit, 0), (0, 1 << qubit), (1 << qubit, 1 << qubit))


def _faults(rows: tuple[int, ...], axis: str, passes: int) -> tuple[_Fault, ...]:
    faults: list[_Fault] = []
    for qubit in range(_N):
        for x, z in _single_paulis(qubit):
            faults.extend((_Fault(-1, "initial", x=x, z=z),
                           _Fault(-1, "final_idle", x=x, z=z)))
    for check in range(len(rows) * passes):
        for qubit in (_S, _F):
            faults.extend(_Fault(check, "prep", x=x, z=z) for x, z in _single_paulis(qubit))
        faults.extend((_Fault(check, "readout", x=1), _Fault(check, "readout", z=1)))
        for gate, (control, target) in enumerate(_gates(rows[check % len(rows)], axis)):
            for left in ((0, 0), *_single_paulis(control)):
                for right in ((0, 0), *_single_paulis(target)):
                    x, z = left[0] | right[0], left[1] | right[1]
                    if x or z:
                        faults.append(_Fault(check, "gate", gate, x, z))
            for qubit in range(_N + 2):
                if qubit not in (control, target):
                    faults.extend(_Fault(check, "idle", gate, x, z)
                                  for x, z in _single_paulis(qubit))
    return tuple(faults)


def _orbit_fidelity(state: _Array, target: _Array) -> float:
    candidates = [target]
    candidates.extend(_pauli(target, x, z) for q in range(_N) for x, z in _single_paulis(q))
    return max(float(abs(np.vdot(candidate, state)) ** 2) for candidate in candidates)


@lru_cache(maxsize=1)
def dense_uniform_preparation_audit() -> dict[str, Any]:
    """Enumerate tiny-circuit branches for every declared single-fault event.

    The serial replay includes all 15 post-CNOT Paulis, all three post-prep
    Paulis, each syndrome/flag readout flip, all three idle Paulis on every
    inactive qubit after every CNOT, and initial/final data faults. Ancillas
    are freshly reset/prepared per check. Physical reset/prep/readout timing
    and their extra idle windows belong to the full scheduled LP audit.
    """
    reports: dict[str, Any] = {}
    for axis in ("Z", "X"):
        target = _target(_ROWS, axis)
        ideal, ideal_total = _run(_ROWS, axis, 2)
        faults = _faults(_ROWS, axis, 2)
        accepted_events = rejected_events = accepted_branches = bad_branches = 0
        max_infidelity = max_probability_error = 0.0
        category_counts: dict[str, int] = {}
        for fault in faults:
            category_counts[fault.stage] = category_counts.get(fault.stage, 0) + 1
            branches, total = _run(_ROWS, axis, 2, fault)
            max_probability_error = max(max_probability_error, abs(1 - total))
            if branches:
                accepted_events += 1
            else:
                rejected_events += 1
            for branch in branches:
                accepted_branches += 1
                infidelity = max(0.0, 1 - _orbit_fidelity(branch.state, target))
                max_infidelity = max(max_infidelity, infidelity)
                bad_branches += infidelity > _TOL
        hook = _Fault(0, "gate", 2, z=1 << _S) if axis == "Z" else _Fault(
            0, "gate", 2, x=1 << _S,
        )
        hooked, _ = _run(_ROWS, axis, 2, hook)
        unflagged, _ = _run(_ROWS, axis, 2, hook, require_flags=False)
        one_pass, _ = _run(_ROWS[:2], axis, 1, _Fault(1, "readout", x=1))
        reports[axis] = {
            "no_fault_valid_branches": len(ideal),
            "no_fault_total_probability": ideal_total,
            "no_fault_acceptance_probability": sum(b.probability for b in ideal),
            "no_fault_branch_probabilities": [b.probability for b in ideal],
            "no_fault_target_fidelity_minimum": min(
                float(abs(np.vdot(target, branch.state)) ** 2) for branch in ideal
            ),
            "declared_single_fault_events": len(faults),
            "event_categories": category_counts,
            "events_with_accepted_branches": accepted_events,
            "fully_rejected_events": rejected_events,
            "accepted_fault_branches": accepted_branches,
            "bad_accepted_branches": bad_branches,
            "accepted_one_pauli_orbit_max_infidelity": max_infidelity,
            "max_total_probability_error": max_probability_error,
            "weight_two_hook_flagged_and_rejected": not hooked,
            "drop_flags_negative_control_accepted_branches": len(unflagged),
            "drop_flags_negative_control_best_orbit_fidelity": max(
                _orbit_fidelity(branch.state, target) for branch in unflagged
            ),
            "one_pass_readout_negative_control_accepted_branches": len(one_pass),
            "one_pass_readout_negative_control_best_orbit_fidelity": max(
                _orbit_fidelity(branch.state, _target(_ROWS[:2], axis)) for branch in one_pass
            ),
        }
    return {
        "physical_data_qubits": _N,
        "simulated_qubits_including_ancillas": _N + 2,
        "measured_rows_lsb_first": list(_ROWS),
        "dependent_relation": "row0 XOR row1 XOR row2 = 0",
        "passes": 2,
        "same_axis_checks_only": True,
        "interpass_correction": False,
        "actual_measurement_branch_enumeration": True,
        "full_LP_certificate_from_this_replay_alone": False,
        "axis_reports": reports,
        "all_checks_passed": all(
            report["bad_accepted_branches"] == 0
            and report["no_fault_target_fidelity_minimum"] > 1 - _TOL
            and abs(report["no_fault_acceptance_probability"] - 1) < _TOL
            and report["weight_two_hook_flagged_and_rejected"]
            and report["drop_flags_negative_control_best_orbit_fidelity"] < _TOL
            and report["one_pass_readout_negative_control_best_orbit_fidelity"] < _TOL
            for report in reports.values()
        ),
    }
