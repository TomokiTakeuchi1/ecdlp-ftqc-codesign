"""Compare logical H/CNOT handling and extract QCLA layer demand.

The module uses the reviewed correction convention ``physical = C_dagger logical``.
It deliberately separates a logical handling rule from a QEC realization.  The
reported layer counts are architecture-independent opportunities, not surgery
rounds or wall-clock time.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ecdlp_ftqc.circuits.qcla import QclaGate, QclaGateKind, QclaTrace
from ecdlp_ftqc.circuits.qcla_oop import OopQclaGate, OopQclaTrace
from ecdlp_ftqc.metadata import EvidenceStatus

CLIFFORD_STRATEGY_SCHEMA = "ecdlp-ftqc/qcla-h-cnot-strategy-audit"
CLIFFORD_STRATEGY_SCHEMA_VERSION = 1
FRAME_STATE_CONVENTION = "physical_state=C_dagger|logical_state>"
FRAME_GENERATORS = ("X", "Z", "CNOT", "CZ")


class CliffordStrategyError(ValueError):
    """Raised when a strategy record or source-demand audit is inconsistent."""


class GateKind(str, Enum):
    """Logical gates compared in this cycle."""

    H = "H"
    CNOT = "CNOT"


class HandlingMode(str, Enum):
    """Three ways to realize a desired logical Clifford U."""

    FRAME_CONJUGATED_LOGICAL = "clifford_conjugated_logical"
    BARE_LOGICAL = "bare_logical"
    CLIFFORD_FRAME_TRACKING = "clifford_frame_tracking"


@dataclass(frozen=True, slots=True)
class StrategyEffect:
    """One logical handling rule and its downstream PPM consequences."""

    gate: GateKind
    mode: HandlingMode
    physical_action: str
    output_frame_rule: str
    direct_ccz_phase_one_axis: str
    direct_ccz_phase_two_axis: str
    downstream_y_possible: bool
    support_effect: str
    branch_dependence_effect: str
    gate_realization_ppm_axis: str
    materialization_obligation: str
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        text_fields = (
            self.physical_action,
            self.output_frame_rule,
            self.direct_ccz_phase_one_axis,
            self.direct_ccz_phase_two_axis,
            self.support_effect,
            self.branch_dependence_effect,
            self.gate_realization_ppm_axis,
            self.materialization_obligation,
        )
        if any(not value for value in text_fields):
            raise CliffordStrategyError("strategy text fields cannot be empty")


@dataclass(frozen=True, slots=True)
class SourceLayerCliffordDemand:
    """H/CNOT demand induced by one reviewed QCLA source layer."""

    source_layer: int
    x_gate_count: int
    cnot_gate_count: int
    toffoli_gate_count: int
    opening_h_gate_count: int
    closing_h_gate_count: int
    direct_ccz_ppm_candidate_levels: int
    gate_supports_disjoint: bool

    def __post_init__(self) -> None:
        counts = (
            self.x_gate_count,
            self.cnot_gate_count,
            self.toffoli_gate_count,
            self.opening_h_gate_count,
            self.closing_h_gate_count,
            self.direct_ccz_ppm_candidate_levels,
        )
        if self.source_layer < 1 or any(value < 0 for value in counts):
            raise CliffordStrategyError("source-layer counts must be nonnegative")
        if self.opening_h_gate_count != self.toffoli_gate_count:
            raise CliffordStrategyError("each direct CCZ requires one opening H")
        if self.closing_h_gate_count != self.toffoli_gate_count:
            raise CliffordStrategyError("each direct CCZ requires one closing H")
        expected_ppm_levels = 2 if self.toffoli_gate_count else 0
        if self.direct_ccz_ppm_candidate_levels != expected_ppm_levels:
            raise CliffordStrategyError("direct-CCZ candidate-level count is inconsistent")
        if not self.gate_supports_disjoint:
            raise CliffordStrategyError("reviewed source layers must have disjoint support")

    @property
    def contains_cnot(self) -> bool:
        return self.cnot_gate_count > 0

    @property
    def contains_toffoli(self) -> bool:
        return self.toffoli_gate_count > 0


@dataclass(frozen=True, slots=True)
class VariantCliffordDemand:
    """Exact logical counts and parameterized added-layer formulas."""

    variant: str
    width: int
    source_gate_count: int
    source_layer_count: int
    source_x_gate_count: int
    source_cnot_gate_count: int
    source_toffoli_gate_count: int
    cnot_bearing_source_layer_count: int
    cnot_only_source_layer_count: int
    mixed_cnot_toffoli_source_layer_count: int
    toffoli_bearing_source_layer_count: int
    opening_h_gate_count: int
    closing_h_gate_count: int
    h_gate_count: int
    h_parallel_layer_count: int
    maximum_parallel_cnot_gate_count: int
    maximum_parallel_h_gate_count: int
    direct_ccz_ppm_candidate_level_count: int
    direct_h_strict_added_gate_layers: int
    direct_h_closing_overlap_added_gate_layers: int
    h_teleport_strict_added_ppm_layers: int
    h_teleport_closing_overlap_added_ppm_layers: int
    simd_cnot_strict_added_gate_layers: int
    simd_cnot_logical_overlap_added_gate_layers: int
    cnot_teleport_strict_added_ppm_layers: int
    cnot_teleport_axis_aligned_added_ppm_layers: int
    source_layers: tuple[SourceLayerCliffordDemand, ...]
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL
    finite_runtime_seconds: None = None

    def __post_init__(self) -> None:
        if self.variant not in {"oop", "ip"} or self.width < 2:
            raise CliffordStrategyError("unsupported QCLA variant or width")
        if self.source_layer_count != len(self.source_layers):
            raise CliffordStrategyError("source-layer count does not match layer records")
        if self.h_gate_count != self.opening_h_gate_count + self.closing_h_gate_count:
            raise CliffordStrategyError("H total must equal opening plus closing H gates")
        if self.h_parallel_layer_count != 2 * self.toffoli_bearing_source_layer_count:
            raise CliffordStrategyError("H parallel-layer count is inconsistent")
        if self.direct_ccz_ppm_candidate_level_count != (
            2 * self.toffoli_bearing_source_layer_count
        ):
            raise CliffordStrategyError("direct-CCZ PPM candidate count is inconsistent")
        if self.finite_runtime_seconds is not None:
            raise CliffordStrategyError("this architecture-independent audit has null runtime")


@dataclass(frozen=True, slots=True)
class ExecutionOption:
    """One code-side realization option with an explicit evidence boundary."""

    gate: GateKind
    option_id: str
    family: str
    directly_implements_modes: tuple[HandlingMode, ...]
    online_primitive_layers_per_logical_layer: str
    provisioned_logical_ancillas: str
    added_ppm_axes: tuple[str, ...]
    resource_state: str
    addressability: str
    qec_requirements: tuple[str, ...]
    source: str
    evidence_status: EvidenceStatus
    reported_execution_seconds: float | None = None
    reported_relabel_debt_seconds: float | None = None
    applies_to_current_high_rate_backend: bool = False

    def __post_init__(self) -> None:
        if not self.option_id or not self.family or not self.source:
            raise CliffordStrategyError("execution option identity cannot be empty")
        if not self.directly_implements_modes:
            raise CliffordStrategyError("execution option must implement at least one mode")
        if self.reported_execution_seconds is not None and self.reported_execution_seconds < 0:
            raise CliffordStrategyError("reported execution time cannot be negative")
        if self.reported_relabel_debt_seconds is not None and self.reported_relabel_debt_seconds < 0:
            raise CliffordStrategyError("reported relabel debt cannot be negative")
        if self.applies_to_current_high_rate_backend:
            raise CliffordStrategyError("no finite high-rate backend is admitted in this task")


def build_strategy_matrix() -> tuple[StrategyEffect, ...]:
    """Return the six logical handling cases under one correction convention."""

    phase_two = "X_ONLY_PROVED_on_fresh_unframed_resource_values"
    return (
        StrategyEffect(
            gate=GateKind.H,
            mode=HandlingMode.FRAME_CONJUGATED_LOGICAL,
            physical_action="apply C_dagger H C and retain C",
            output_frame_rule="C_out=C",
            direct_ccz_phase_one_axis="Z_ONLY_PROVED_under_existing_frame_normal_form",
            direct_ccz_phase_two_axis=phase_two,
            downstream_y_possible=False,
            support_effect="downstream PPM support law is unchanged; the H realization itself may be nonlocal",
            branch_dependence_effect="moves incoming conditional-frame dependence into the physical H realization",
            gate_realization_ppm_axis="UNRESTRICTED_if_C_dagger_H_C_is_teleported_or_synthesized",
            materialization_obligation="realize a possibly branch-dependent multi-qubit Clifford before continuing",
            evidence_status=EvidenceStatus.PROVED,
        ),
        StrategyEffect(
            gate=GateKind.H,
            mode=HandlingMode.BARE_LOGICAL,
            physical_action="apply bare H",
            output_frame_rule="C_out=H C H",
            direct_ccz_phase_one_axis="NOT_GUARANTEED_Z_ONLY",
            direct_ccz_phase_two_axis=phase_two,
            downstream_y_possible=True,
            support_effect="can rotate Z support to X and, with an incoming CNOT/CZ frame, create mixed support or Y",
            branch_dependence_effect="retains branch dependence in the conjugated output frame",
            gate_realization_ppm_axis="NONE_for_a_native_H;_code_specific_for_surgery_or_teleportation",
            materialization_obligation="prove H C H remains Z-preserving for the actual target or clear the frame first",
            evidence_status=EvidenceStatus.PROVED,
        ),
        StrategyEffect(
            gate=GateKind.H,
            mode=HandlingMode.CLIFFORD_FRAME_TRACKING,
            physical_action="apply no quantum gate",
            output_frame_rule="C_out=H C",
            direct_ccz_phase_one_axis="NOT_GUARANTEED_Z_ONLY",
            direct_ccz_phase_two_axis=phase_two,
            downstream_y_possible=True,
            support_effect="the next logical Z on the target is presented as an X before the old frame acts",
            branch_dependence_effect="postpones cost but can spread branch-dependent mixed-axis support",
            gate_realization_ppm_axis="NONE_now;_future_materialization_is_unrestricted",
            materialization_obligation="materialize before a Z-only high-rate region unless an exact safe boundary is proved",
            evidence_status=EvidenceStatus.PROVED,
        ),
        StrategyEffect(
            gate=GateKind.CNOT,
            mode=HandlingMode.FRAME_CONJUGATED_LOGICAL,
            physical_action="apply C_dagger CNOT C and retain C",
            output_frame_rule="C_out=C",
            direct_ccz_phase_one_axis="Z_ONLY_PROVED_under_existing_frame_normal_form",
            direct_ccz_phase_two_axis=phase_two,
            downstream_y_possible=False,
            support_effect="downstream support law is unchanged; the conjugated CNOT can itself be dense",
            branch_dependence_effect="moves incoming conditional-frame dependence into the physical CNOT realization",
            gate_realization_ppm_axis="UNRESTRICTED_if_the_conjugated_Clifford_is_teleported",
            materialization_obligation="synthesize the branch-dependent conjugated Clifford",
            evidence_status=EvidenceStatus.PROVED,
        ),
        StrategyEffect(
            gate=GateKind.CNOT,
            mode=HandlingMode.BARE_LOGICAL,
            physical_action="apply bare CNOT",
            output_frame_rule="C_out=CNOT C CNOT",
            direct_ccz_phase_one_axis="Z_ONLY_PROVED_by_Z_preserving_subgroup_closure",
            direct_ccz_phase_two_axis=phase_two,
            downstream_y_possible=False,
            support_effect="can grow, shrink, or reroute Z support while preserving its Pauli axis",
            branch_dependence_effect="support may remain outcome dependent after frame conjugation",
            gate_realization_ppm_axis="ZZ_then_XX_then_Z_for_the_reviewed_measurement_gadget",
            materialization_obligation="pay one addressable CNOT now; no axis-restoration barrier is required",
            evidence_status=EvidenceStatus.PROVED,
        ),
        StrategyEffect(
            gate=GateKind.CNOT,
            mode=HandlingMode.CLIFFORD_FRAME_TRACKING,
            physical_action="apply no quantum gate",
            output_frame_rule="C_out=CNOT C",
            direct_ccz_phase_one_axis="Z_ONLY_PROVED_by_Z_preserving_subgroup_closure",
            direct_ccz_phase_two_axis=phase_two,
            downstream_y_possible=False,
            support_effect="future Z PPMs remain Z type but can acquire larger and branch-dependent support",
            branch_dependence_effect="defers deterministic CNOT topology into every later presented observable",
            gate_realization_ppm_axis="NONE_now",
            materialization_obligation="clear before H or when support/routing cost exceeds an addressable CNOT layer",
            evidence_status=EvidenceStatus.PROVED,
        ),
    )


def _supports_are_disjoint(gates: list[OopQclaGate | QclaGate]) -> bool:
    support = [logical for gate in gates for logical in gate.logical_support]
    return len(support) == len(set(support))


def analyze_qcla_clifford_demand(
    trace: OopQclaTrace | QclaTrace,
    *,
    variant: str,
) -> VariantCliffordDemand:
    """Extract exact gate and parallel-layer demand from one reviewed source trace."""

    if variant not in {"oop", "ip"}:
        raise CliffordStrategyError("variant must be oop or ip")
    by_layer: dict[int, list[OopQclaGate | QclaGate]] = defaultdict(list)
    total = Counter[QclaGateKind]()
    for gate in trace.gates:
        by_layer[gate.algorithmic_layer].append(gate)
        total[gate.kind] += 1

    layers: list[SourceLayerCliffordDemand] = []
    for source_layer, gates in sorted(by_layer.items()):
        counts = Counter(gate.kind for gate in gates)
        toffoli_count = counts[QclaGateKind.TOFFOLI]
        layers.append(
            SourceLayerCliffordDemand(
                source_layer=source_layer,
                x_gate_count=counts[QclaGateKind.X],
                cnot_gate_count=counts[QclaGateKind.CNOT],
                toffoli_gate_count=toffoli_count,
                opening_h_gate_count=toffoli_count,
                closing_h_gate_count=toffoli_count,
                direct_ccz_ppm_candidate_levels=2 if toffoli_count else 0,
                gate_supports_disjoint=_supports_are_disjoint(gates),
            )
        )

    cnot_bearing = sum(layer.contains_cnot for layer in layers)
    toffoli_bearing = sum(layer.contains_toffoli for layer in layers)
    cnot_only = sum(layer.contains_cnot and not layer.contains_toffoli for layer in layers)
    mixed = sum(layer.contains_cnot and layer.contains_toffoli for layer in layers)
    opening_h = total[QclaGateKind.TOFFOLI]
    closing_h = opening_h
    return VariantCliffordDemand(
        variant=variant,
        width=trace.width,
        source_gate_count=len(trace.gates),
        source_layer_count=len(layers),
        source_x_gate_count=total[QclaGateKind.X],
        source_cnot_gate_count=total[QclaGateKind.CNOT],
        source_toffoli_gate_count=total[QclaGateKind.TOFFOLI],
        cnot_bearing_source_layer_count=cnot_bearing,
        cnot_only_source_layer_count=cnot_only,
        mixed_cnot_toffoli_source_layer_count=mixed,
        toffoli_bearing_source_layer_count=toffoli_bearing,
        opening_h_gate_count=opening_h,
        closing_h_gate_count=closing_h,
        h_gate_count=opening_h + closing_h,
        h_parallel_layer_count=2 * toffoli_bearing,
        maximum_parallel_cnot_gate_count=max(
            (layer.cnot_gate_count for layer in layers), default=0
        ),
        maximum_parallel_h_gate_count=max(
            (layer.toffoli_gate_count for layer in layers), default=0
        ),
        direct_ccz_ppm_candidate_level_count=2 * toffoli_bearing,
        direct_h_strict_added_gate_layers=2 * toffoli_bearing,
        direct_h_closing_overlap_added_gate_layers=toffoli_bearing,
        h_teleport_strict_added_ppm_layers=4 * toffoli_bearing,
        h_teleport_closing_overlap_added_ppm_layers=3 * toffoli_bearing,
        simd_cnot_strict_added_gate_layers=cnot_bearing,
        simd_cnot_logical_overlap_added_gate_layers=cnot_only,
        cnot_teleport_strict_added_ppm_layers=3 * cnot_bearing,
        cnot_teleport_axis_aligned_added_ppm_layers=3 * cnot_only + mixed,
        source_layers=tuple(layers),
    )


def build_execution_options() -> tuple[ExecutionOption, ...]:
    """Return implementation choices without composing incompatible timings."""

    rascql = "Yang et al. 2026, arXiv:2602.14273v2, Table 2"
    xu_cnot = "Xu et al. 2024, arXiv:2407.18490v1, Figure 11(c)"
    return (
        ExecutionOption(
            gate=GateKind.H,
            option_id="co_designed_whole_event_instruction",
            family="code_co_design",
            directly_implements_modes=(HandlingMode.FRAME_CONJUGATED_LOGICAL,),
            online_primitive_layers_per_logical_layer="0 stand-alone H layers if absorbed into an admitted event instruction",
            provisioned_logical_ancillas="code- and instruction-dependent",
            added_ppm_axes=(),
            resource_state="none established; direct-CCZ resource remains separate",
            addressability="only the embedded instruction orbit; not arbitrary subsets",
            qec_requirements=(
                "automorphism or code-switching proof for the complete event action",
                "distance-preserving fault-tolerant implementation",
                "decoder and routing contract for every admitted branch",
            ),
            source="project co-design proposal constrained by the RASCqL method",
            evidence_status=EvidenceStatus.CONJECTURE,
        ),
        ExecutionOption(
            gate=GateKind.H,
            option_id="simd_h_swap",
            family="global_or_fold_transversal_SIMD",
            directly_implements_modes=(HandlingMode.BARE_LOGICAL,),
            online_primitive_layers_per_logical_layer="1 global H-SWAP layer plus logical transpose bookkeeping",
            provisioned_logical_ancillas="0, but unused SIMD lanes require known or disposable occupants",
            added_ppm_axes=(),
            resource_state="none",
            addressability="all logicals in a compatible block; subset H requires packing or a fallback",
            qec_requirements=(
                "self-dual or symmetric code admitting H-SWAP",
                "logical transpose/permutation tracking",
                "block packing and movement schedule for each H target mask",
            ),
            source=rascql,
            evidence_status=EvidenceStatus.LITERATURE,
            reported_execution_seconds=0.0019,
        ),
        ExecutionOption(
            gate=GateKind.H,
            option_id="one_bit_h_teleportation",
            family="gate_teleportation_plus_PPM_surgery",
            directly_implements_modes=(HandlingMode.BARE_LOGICAL,),
            online_primitive_layers_per_logical_layer="2 ordered PPM layers after offline output preparation",
            provisioned_logical_ancillas="1 |0> output logical per simultaneous H",
            added_ppm_axes=("ZX", "X"),
            resource_state="stabilizer |0>; no T/CCZ magic state",
            addressability="arbitrary selected logical values if the two PPM supports are native",
            qec_requirements=(
                "addressable ZX and X measurements",
                "destructive input measurement and output-carrier rebinding",
                "decoded outcome reaction and Pauli-frame update",
            ),
            source=(
                "self-derived ZX/X one-bit H identity; exact all-branch operator "
                "verification in qcla_clifford_strategy_replay"
            ),
            evidence_status=EvidenceStatus.NUMERICAL,
        ),
        ExecutionOption(
            gate=GateKind.H,
            option_id="addressable_code_deformation_h",
            family="surgery_or_code_deformation",
            directly_implements_modes=(HandlingMode.BARE_LOGICAL,),
            online_primitive_layers_per_logical_layer="1 parameterized H gadget layer; native cycles OPEN",
            provisioned_logical_ancillas="code-specific workspace, no magic state",
            added_ppm_axes=(),
            resource_state="none beyond stabilizer workspace",
            addressability="code/layout-specific selected patches; not established for generic high-rate qLDPC",
            qec_requirements=(
                "distance-preserving deformation or gauge-fixing sequence",
                "workspace geometry and syndrome-round count",
                "decoder handoff across the deformation",
            ),
            source="surface-code deformation literature; no compatible qLDPC timing is pinned",
            evidence_status=EvidenceStatus.OPEN,
        ),
        ExecutionOption(
            gate=GateKind.CNOT,
            option_id="co_designed_layer_automorphism",
            family="code_co_design",
            directly_implements_modes=(HandlingMode.BARE_LOGICAL,),
            online_primitive_layers_per_logical_layer="0 if the complete parallel GF(2) layer is a virtual automorphism",
            provisioned_logical_ancillas="0",
            added_ppm_axes=(),
            resource_state="none",
            addressability="only embedded autoCNOT/dirty-shift patterns",
            qec_requirements=(
                "membership of every QCLA CNOT-layer matrix in the generated automorphism ISA",
                "code-rate/check-weight/distance audit after code modification",
                "relabel debt before later transversal interactions",
            ),
            source=rascql,
            evidence_status=EvidenceStatus.LITERATURE,
            reported_execution_seconds=0.0,
            reported_relabel_debt_seconds=0.0024,
        ),
        ExecutionOption(
            gate=GateKind.CNOT,
            option_id="simd_transversal_cnot",
            family="blockwise_transversal_SIMD",
            directly_implements_modes=(HandlingMode.BARE_LOGICAL,),
            online_primitive_layers_per_logical_layer="1 tCNOT layer per matched CNOT source layer",
            provisioned_logical_ancillas="0 logical scratch, but a matched partner block and dummy lanes may be needed",
            added_ppm_axes=(),
            resource_state="none",
            addressability="corresponding logical pairs across whole blocks, not arbitrary sparse pairs",
            qec_requirements=(
                "two compatible encoded blocks with aligned logical bases",
                "packing/permutation of disjoint source-layer pairs",
                "movement and correlated-decoding contract",
            ),
            source=rascql,
            evidence_status=EvidenceStatus.LITERATURE,
            reported_execution_seconds=0.003,
            reported_relabel_debt_seconds=0.0024,
        ),
        ExecutionOption(
            gate=GateKind.CNOT,
            option_id="measurement_cnot",
            family="gate_teleportation_plus_PPM_surgery",
            directly_implements_modes=(HandlingMode.BARE_LOGICAL,),
            online_primitive_layers_per_logical_layer="3 ordered PPM layers after offline scratch preparation",
            provisioned_logical_ancillas="1 |+> scratch per simultaneous CNOT",
            added_ppm_axes=("ZZ", "XX", "Z"),
            resource_state="stabilizer |+>; no T/CCZ magic state",
            addressability="arbitrary selected pairs if each PPM support is native",
            qec_requirements=(
                "addressable ZZ, XX, and Z measurements",
                "one live scratch per parallel CNOT",
                "decoded three-bit reaction and Pauli-frame update",
            ),
            source=xu_cnot,
            evidence_status=EvidenceStatus.LITERATURE,
        ),
    )


def strategy_effect_to_data(value: StrategyEffect) -> dict[str, Any]:
    return {
        "branch_dependence_effect": value.branch_dependence_effect,
        "direct_ccz_phase_one_axis": value.direct_ccz_phase_one_axis,
        "direct_ccz_phase_two_axis": value.direct_ccz_phase_two_axis,
        "downstream_y_possible": value.downstream_y_possible,
        "evidence_status": value.evidence_status.value,
        "gate": value.gate.value,
        "gate_realization_ppm_axis": value.gate_realization_ppm_axis,
        "materialization_obligation": value.materialization_obligation,
        "mode": value.mode.value,
        "output_frame_rule": value.output_frame_rule,
        "physical_action": value.physical_action,
        "support_effect": value.support_effect,
    }


def source_layer_clifford_demand_to_data(
    value: SourceLayerCliffordDemand,
) -> dict[str, Any]:
    return {
        "closing_h_gate_count": value.closing_h_gate_count,
        "cnot_gate_count": value.cnot_gate_count,
        "direct_ccz_ppm_candidate_levels": value.direct_ccz_ppm_candidate_levels,
        "gate_supports_disjoint": value.gate_supports_disjoint,
        "opening_h_gate_count": value.opening_h_gate_count,
        "source_layer": value.source_layer,
        "toffoli_gate_count": value.toffoli_gate_count,
        "x_gate_count": value.x_gate_count,
    }


def variant_clifford_demand_to_data(value: VariantCliffordDemand) -> dict[str, Any]:
    return {
        "cnot_bearing_source_layer_count": value.cnot_bearing_source_layer_count,
        "cnot_only_source_layer_count": value.cnot_only_source_layer_count,
        "cnot_teleport_axis_aligned_added_ppm_layers": (
            value.cnot_teleport_axis_aligned_added_ppm_layers
        ),
        "cnot_teleport_strict_added_ppm_layers": value.cnot_teleport_strict_added_ppm_layers,
        "direct_ccz_ppm_candidate_level_count": value.direct_ccz_ppm_candidate_level_count,
        "direct_h_closing_overlap_added_gate_layers": (
            value.direct_h_closing_overlap_added_gate_layers
        ),
        "direct_h_strict_added_gate_layers": value.direct_h_strict_added_gate_layers,
        "evidence_status": value.evidence_status.value,
        "finite_runtime_seconds": value.finite_runtime_seconds,
        "h_gate_count": value.h_gate_count,
        "h_parallel_layer_count": value.h_parallel_layer_count,
        "h_teleport_closing_overlap_added_ppm_layers": (
            value.h_teleport_closing_overlap_added_ppm_layers
        ),
        "h_teleport_strict_added_ppm_layers": value.h_teleport_strict_added_ppm_layers,
        "maximum_parallel_cnot_gate_count": value.maximum_parallel_cnot_gate_count,
        "maximum_parallel_h_gate_count": value.maximum_parallel_h_gate_count,
        "mixed_cnot_toffoli_source_layer_count": value.mixed_cnot_toffoli_source_layer_count,
        "opening_h_gate_count": value.opening_h_gate_count,
        "closing_h_gate_count": value.closing_h_gate_count,
        "simd_cnot_logical_overlap_added_gate_layers": (
            value.simd_cnot_logical_overlap_added_gate_layers
        ),
        "simd_cnot_strict_added_gate_layers": value.simd_cnot_strict_added_gate_layers,
        "source_cnot_gate_count": value.source_cnot_gate_count,
        "source_gate_count": value.source_gate_count,
        "source_layer_count": value.source_layer_count,
        "source_layers": [source_layer_clifford_demand_to_data(item) for item in value.source_layers],
        "source_toffoli_gate_count": value.source_toffoli_gate_count,
        "source_x_gate_count": value.source_x_gate_count,
        "toffoli_bearing_source_layer_count": value.toffoli_bearing_source_layer_count,
        "variant": value.variant,
        "width": value.width,
    }


def execution_option_to_data(value: ExecutionOption) -> dict[str, Any]:
    return {
        "added_ppm_axes": list(value.added_ppm_axes),
        "addressability": value.addressability,
        "applies_to_current_high_rate_backend": value.applies_to_current_high_rate_backend,
        "directly_implements_modes": [item.value for item in value.directly_implements_modes],
        "evidence_status": value.evidence_status.value,
        "family": value.family,
        "gate": value.gate.value,
        "online_primitive_layers_per_logical_layer": (
            value.online_primitive_layers_per_logical_layer
        ),
        "option_id": value.option_id,
        "provisioned_logical_ancillas": value.provisioned_logical_ancillas,
        "qec_requirements": list(value.qec_requirements),
        "reported_execution_seconds": value.reported_execution_seconds,
        "reported_relabel_debt_seconds": value.reported_relabel_debt_seconds,
        "resource_state": value.resource_state,
        "source": value.source,
    }
