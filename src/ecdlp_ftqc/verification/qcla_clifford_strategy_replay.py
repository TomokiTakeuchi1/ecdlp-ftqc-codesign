"""Independent replay for the QCLA H/CNOT strategy audit."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from importlib import import_module
from itertools import product
from typing import Any

from ecdlp_ftqc.circuits import build_oop_qcla_trace, build_qcla_trace
from ecdlp_ftqc.circuits.qcla import QclaGateKind

np: Any = import_module("numpy")
ComplexArray = Any

OUTCOME_BIT_CONVENTION = "0 denotes +1 eigenvalue; 1 denotes -1 eigenvalue"
I = np.eye(2, dtype=np.complex128)
X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
ZERO = np.array([1, 0], dtype=np.complex128)


class QclaCliffordStrategyReplayError(ValueError):
    """Raised when the serialized strategy audit is inconsistent."""


@dataclass(frozen=True, slots=True)
class QclaCliffordStrategyReplaySummary:
    """Compact independent-replay result."""

    strategy_rows_checked: int
    execution_options_checked: int
    variants_checked: int
    source_layers_checked: int
    h_teleportation_branches_checked: int
    h_teleportation_maximum_probability_error: float
    h_teleportation_maximum_operator_frobenius_error: float
    all_passed: bool


@dataclass(frozen=True, slots=True)
class OneBitHTeleportationChannelVerification:
    """Exact operator-level verification of the self-derived ZX/X H gadget."""

    outcome_bit_convention: str
    branch_count: int
    nonzero_branch_count: int
    expected_branch_probability: float
    minimum_branch_probability: float
    maximum_branch_probability: float
    maximum_probability_error: float
    maximum_operator_frobenius_error: float
    branch_corrections: tuple[str, ...]
    tolerance: float
    all_passed: bool


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise QclaCliffordStrategyReplayError(message)


def _measurement_projector(observable: ComplexArray, bit: int) -> ComplexArray:
    dimension = observable.shape[0]
    return (np.eye(dimension, dtype=np.complex128) + (-1) ** bit * observable) / 2


def _h_teleportation_branch_operator(zx_bit: int, x_bit: int) -> ComplexArray:
    """Return the corrected output map for one ZX-then-X measurement branch."""

    zx_projector = _measurement_projector(np.kron(Z, X), zx_bit)
    x_bra = np.array([1, (-1) ** x_bit], dtype=np.complex128) / np.sqrt(2)
    correction = I
    if x_bit:
        correction = X @ correction
    if zx_bit:
        correction = Z @ correction

    columns = []
    for basis in range(2):
        input_state = np.eye(2, dtype=np.complex128)[:, basis]
        joint = zx_projector @ np.kron(input_state, ZERO)
        output = x_bra @ joint.reshape((2, 2))
        columns.append(correction @ output)
    return np.column_stack(columns)


def verify_one_bit_h_teleportation_channel(
    *,
    tolerance: float = 1e-12,
) -> OneBitHTeleportationChannelVerification:
    """Compare all four self-derived H-teleportation branches with ideal H."""

    expected_probability = 0.25
    probabilities: list[float] = []
    maximum_probability_error = 0.0
    maximum_operator_error = 0.0
    nonzero_branches = 0
    corrections = ("I", "X", "Z", "ZX_up_to_phase_Y")

    for zx_bit, x_bit in product((0, 1), repeat=2):
        branch = _h_teleportation_branch_operator(zx_bit, x_bit)
        scalar = np.vdot(H, branch) / H.shape[0]
        probability = float(np.linalg.norm(branch, ord="fro") ** 2 / H.shape[0])
        probabilities.append(probability)
        if probability > tolerance:
            nonzero_branches += 1
        maximum_probability_error = max(
            maximum_probability_error,
            abs(probability - expected_probability),
        )
        maximum_operator_error = max(
            maximum_operator_error,
            float(np.linalg.norm(branch - scalar * H, ord="fro")),
        )

    all_passed = (
        nonzero_branches == 4
        and maximum_probability_error <= tolerance
        and maximum_operator_error <= tolerance
    )
    return OneBitHTeleportationChannelVerification(
        outcome_bit_convention=OUTCOME_BIT_CONVENTION,
        branch_count=4,
        nonzero_branch_count=nonzero_branches,
        expected_branch_probability=expected_probability,
        minimum_branch_probability=min(probabilities),
        maximum_branch_probability=max(probabilities),
        maximum_probability_error=maximum_probability_error,
        maximum_operator_frobenius_error=maximum_operator_error,
        branch_corrections=corrections,
        tolerance=tolerance,
        all_passed=all_passed,
    )


def _replay_strategy_matrix(rows: list[dict[str, Any]]) -> None:
    _require(len(rows) == 6, "strategy matrix must contain six rows")
    keys = {(str(row["gate"]), str(row["mode"])) for row in rows}
    _require(len(keys) == 6, "strategy gate/mode pairs must be unique")
    expected_modes = {
        "clifford_conjugated_logical",
        "bare_logical",
        "clifford_frame_tracking",
    }
    for gate in ("H", "CNOT"):
        _require(
            {mode for row_gate, mode in keys if row_gate == gate} == expected_modes,
            f"{gate} strategy modes are incomplete",
        )
    for row in rows:
        phase_two = str(row["direct_ccz_phase_two_axis"])
        _require(phase_two.startswith("X_ONLY_PROVED"), "resource-X guarantee changed")
        phase_one = str(row["direct_ccz_phase_one_axis"])
        if row["gate"] == "CNOT":
            _require("Z_ONLY_PROVED" in phase_one, "CNOT must preserve Z-only phase one")
            _require(not bool(row["downstream_y_possible"]), "CNOT cannot add Y to Z PPMs")
        elif row["mode"] == "clifford_conjugated_logical":
            _require("Z_ONLY_PROVED" in phase_one, "frame-conjugated H must retain frame")
            _require(not bool(row["downstream_y_possible"]), "retained frame cannot add H risk")
        else:
            _require("NOT_GUARANTEED" in phase_one, "bare/tracked H must remain qualified")
            _require(bool(row["downstream_y_possible"]), "bare/tracked H must expose Y risk")


def _source_rows(variant: str) -> list[dict[str, int | bool]]:
    trace = build_oop_qcla_trace(256) if variant == "oop" else build_qcla_trace(256)
    by_layer: dict[int, list[Any]] = defaultdict(list)
    for gate in trace.gates:
        by_layer[gate.algorithmic_layer].append(gate)
    rows: list[dict[str, int | bool]] = []
    for source_layer, gates in sorted(by_layer.items()):
        counts = Counter(gate.kind for gate in gates)
        support = [logical for gate in gates for logical in gate.logical_support]
        toffoli = counts[QclaGateKind.TOFFOLI]
        rows.append(
            {
                "closing_h_gate_count": toffoli,
                "cnot_gate_count": counts[QclaGateKind.CNOT],
                "direct_ccz_ppm_candidate_levels": 2 if toffoli else 0,
                "gate_supports_disjoint": len(support) == len(set(support)),
                "opening_h_gate_count": toffoli,
                "source_layer": source_layer,
                "toffoli_gate_count": toffoli,
                "x_gate_count": counts[QclaGateKind.X],
            }
        )
    return rows


def _replay_variant(row: dict[str, Any]) -> int:
    variant = str(row["variant"])
    _require(variant in {"oop", "ip"}, "unexpected variant")
    _require(int(row["width"]) == 256, "strategy audit must use width 256")
    expected_layers = _source_rows(variant)
    _require(row["source_layers"] == expected_layers, f"{variant} source-layer audit mismatch")
    cnot_bearing = sum(int(item["cnot_gate_count"]) > 0 for item in expected_layers)
    toffoli_bearing = sum(
        int(item["toffoli_gate_count"]) > 0 for item in expected_layers
    )
    cnot_only = sum(
        int(item["cnot_gate_count"]) > 0 and int(item["toffoli_gate_count"]) == 0
        for item in expected_layers
    )
    mixed = sum(
        int(item["cnot_gate_count"]) > 0 and int(item["toffoli_gate_count"]) > 0
        for item in expected_layers
    )
    cnot_total = sum(int(item["cnot_gate_count"]) for item in expected_layers)
    toffoli_total = sum(int(item["toffoli_gate_count"]) for item in expected_layers)
    x_total = sum(int(item["x_gate_count"]) for item in expected_layers)
    expected_scalars = {
        "closing_h_gate_count": toffoli_total,
        "cnot_bearing_source_layer_count": cnot_bearing,
        "cnot_only_source_layer_count": cnot_only,
        "cnot_teleport_axis_aligned_added_ppm_layers": 3 * cnot_only + mixed,
        "cnot_teleport_strict_added_ppm_layers": 3 * cnot_bearing,
        "direct_ccz_ppm_candidate_level_count": 2 * toffoli_bearing,
        "direct_h_closing_overlap_added_gate_layers": toffoli_bearing,
        "direct_h_strict_added_gate_layers": 2 * toffoli_bearing,
        "h_gate_count": 2 * toffoli_total,
        "h_parallel_layer_count": 2 * toffoli_bearing,
        "h_teleport_closing_overlap_added_ppm_layers": 3 * toffoli_bearing,
        "h_teleport_strict_added_ppm_layers": 4 * toffoli_bearing,
        "mixed_cnot_toffoli_source_layer_count": mixed,
        "opening_h_gate_count": toffoli_total,
        "simd_cnot_logical_overlap_added_gate_layers": cnot_only,
        "simd_cnot_strict_added_gate_layers": cnot_bearing,
        "source_cnot_gate_count": cnot_total,
        "source_gate_count": cnot_total + toffoli_total + x_total,
        "source_layer_count": len(expected_layers),
        "source_toffoli_gate_count": toffoli_total,
        "source_x_gate_count": x_total,
        "toffoli_bearing_source_layer_count": toffoli_bearing,
    }
    for field, expected in expected_scalars.items():
        _require(int(row[field]) == expected, f"{variant} {field} mismatch")
    _require(row["finite_runtime_seconds"] is None, "finite runtime must remain null")
    return len(expected_layers)


def _replay_execution_options(rows: list[dict[str, Any]]) -> None:
    expected_ids = {
        "co_designed_whole_event_instruction",
        "simd_h_swap",
        "one_bit_h_teleportation",
        "addressable_code_deformation_h",
        "co_designed_layer_automorphism",
        "simd_transversal_cnot",
        "measurement_cnot",
    }
    _require({str(row["option_id"]) for row in rows} == expected_ids, "option set changed")
    for row in rows:
        _require(
            not bool(row["applies_to_current_high_rate_backend"]),
            "an execution option was falsely admitted",
        )
        _require(bool(row["directly_implements_modes"]), "handling-mode scope is missing")
    h_teleport = next(row for row in rows if row["option_id"] == "one_bit_h_teleportation")
    cnot = next(row for row in rows if row["option_id"] == "measurement_cnot")
    _require(h_teleport["added_ppm_axes"] == ["ZX", "X"], "H teleport axes changed")
    _require(
        h_teleport["evidence_status"] == "NUMERICAL",
        "self-derived H teleport must remain NUMERICAL",
    )
    _require("Xu" not in str(h_teleport["source"]), "H teleport cannot cite Xu Figure 11")
    _require(cnot["added_ppm_axes"] == ["ZZ", "XX", "Z"], "CNOT axes changed")
    _require(cnot["evidence_status"] == "LITERATURE", "CNOT source status changed")
    _require("Figure 11(c)" in str(cnot["source"]), "CNOT Figure 11(c) source changed")


def replay_qcla_clifford_strategy(
    strategy_rows: list[dict[str, Any]],
    demand_rows: list[dict[str, Any]],
    execution_rows: list[dict[str, Any]],
) -> QclaCliffordStrategyReplaySummary:
    """Rebuild source demand and reject unqualified finite results."""

    _replay_strategy_matrix(strategy_rows)
    _require(len(demand_rows) == 2, "both OOP and IP demand rows are required")
    _require({str(row["variant"]) for row in demand_rows} == {"oop", "ip"}, "variant set changed")
    layer_count = sum(_replay_variant(row) for row in demand_rows)
    _replay_execution_options(execution_rows)
    h_teleportation = verify_one_bit_h_teleportation_channel()
    _require(h_teleportation.all_passed, "H teleportation channel verification failed")
    return QclaCliffordStrategyReplaySummary(
        strategy_rows_checked=len(strategy_rows),
        execution_options_checked=len(execution_rows),
        variants_checked=len(demand_rows),
        source_layers_checked=layer_count,
        h_teleportation_branches_checked=h_teleportation.branch_count,
        h_teleportation_maximum_probability_error=(
            h_teleportation.maximum_probability_error
        ),
        h_teleportation_maximum_operator_frobenius_error=(
            h_teleportation.maximum_operator_frobenius_error
        ),
        all_passed=True,
    )


def qcla_clifford_strategy_replay_to_data(
    value: QclaCliffordStrategyReplaySummary,
) -> dict[str, int | bool | float]:
    return {
        "all_passed": value.all_passed,
        "execution_options_checked": value.execution_options_checked,
        "h_teleportation_branches_checked": value.h_teleportation_branches_checked,
        "h_teleportation_maximum_operator_frobenius_error": (
            value.h_teleportation_maximum_operator_frobenius_error
        ),
        "h_teleportation_maximum_probability_error": (
            value.h_teleportation_maximum_probability_error
        ),
        "source_layers_checked": value.source_layers_checked,
        "strategy_rows_checked": value.strategy_rows_checked,
        "variants_checked": value.variants_checked,
    }
