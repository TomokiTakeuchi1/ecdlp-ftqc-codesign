"""Deterministic branchwise PPM-weight sampling for compressed width-256 QCLA.

The sampled quantity is the maximum presented PPM support weight within one
candidate level and one global sampled branch.  Samples are numerical lower
witnesses beneath the reviewed exact/may-support envelopes; they are not
exhaustive maxima or native surgery geometry.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Literal

from ecdlp_ftqc.circuits import (
    OopQclaGate,
    OopQclaTrace,
    QclaGate,
    QclaGateKind,
    QclaTrace,
)
from ecdlp_ftqc.compiler import DirectCczEventTrace
from ecdlp_ftqc.metadata import EvidenceStatus

from .width256_commutation_aware_qcla import Width256CommutationAwareStudy
from .width256_ip_commutation_aware_qcla import Width256IpCommutationAwareStudy

WIDTH256_BRANCH_WEIGHT_SCHEMA = (
    "ecdlp-ftqc/width256-oop-ip-branch-maximum-ppm-weight-sampling"
)
WIDTH256_BRANCH_WEIGHT_SCHEMA_VERSION = 1
BRANCH_SAMPLE_COUNT = 512
BRANCH_SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"
QUANTILE_METHOD = "nearest_rank_order_statistic"
WEIGHT_COORDINATE = (
    "maximum_presented_logical_ppm_support_weight_per_candidate_level_and_branch"
)


class Width256BranchWeightSamplingError(ValueError):
    """Raised when branch-sampling data violates its evidence contract."""


@dataclass(frozen=True, slots=True)
class SampledLevelWeightDistribution:
    """Branch-maximum PPM weights for one logical candidate level."""

    candidate_level: int
    macro_layer: int
    phase: int
    axis: str
    ppm_count: int
    branch_maximum_weights: tuple[int, ...]
    forced_all_zero_weight: int
    forced_all_one_weight: int
    hashed_branch_maximum: int
    minimum: int
    p50: int
    p95: int
    p99: int
    sampled_maximum: int
    support_weight_upper_bound: int
    sampled_to_upper_gap: int
    upper_bound_kind: str
    upper_bound_evidence_status: EvidenceStatus
    sampled_maximum_is_true_maximum: bool
    sample_vector_sha256: str
    sample_count: int = BRANCH_SAMPLE_COUNT
    hashed_branch_sample_count: int = BRANCH_SAMPLE_COUNT - 2
    sample_seed: str = BRANCH_SAMPLE_SEED
    quantile_method: str = QUANTILE_METHOD
    coordinate: str = WEIGHT_COORDINATE
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.branch_maximum_weights))
        expected_level = 2 * self.macro_layer - (2 - self.phase)
        if (
            self.phase not in {1, 2}
            or self.axis != {1: "Z", 2: "X"}[self.phase]
            or self.candidate_level != expected_level
            or self.ppm_count < 1
            or self.sample_count != BRANCH_SAMPLE_COUNT
            or len(self.branch_maximum_weights) != self.sample_count
            or self.forced_all_zero_weight != self.branch_maximum_weights[0]
            or self.forced_all_one_weight != self.branch_maximum_weights[1]
            or self.hashed_branch_maximum
            != max(self.branch_maximum_weights[2:])
            or min(self.branch_maximum_weights) < 1
            or self.minimum != ordered[0]
            or self.p50 != _nearest_rank(ordered, 50)
            or self.p95 != _nearest_rank(ordered, 95)
            or self.p99 != _nearest_rank(ordered, 99)
            or self.sampled_maximum != ordered[-1]
            or self.support_weight_upper_bound < self.sampled_maximum
            or self.sampled_to_upper_gap
            != self.support_weight_upper_bound - self.sampled_maximum
            or self.sample_seed != BRANCH_SAMPLE_SEED
            or self.hashed_branch_sample_count != BRANCH_SAMPLE_COUNT - 2
            or self.quantile_method != QUANTILE_METHOD
            or self.coordinate != WEIGHT_COORDINATE
            or len(self.sample_vector_sha256) != 64
            or self.sample_vector_sha256
            != _digest(self.branch_maximum_weights)
        ):
            raise Width256BranchWeightSamplingError(
                "invalid sampled level-weight distribution"
            )
        if self.phase == 2:
            if (
                set(self.branch_maximum_weights) != {1}
                or self.support_weight_upper_bound != 1
                or not self.sampled_maximum_is_true_maximum
                or self.evidence_status is not EvidenceStatus.PROVED
            ):
                raise Width256BranchWeightSamplingError(
                    "fresh-resource X phase must have exact unit weight"
                )
        elif (
            self.sampled_maximum_is_true_maximum
            or self.evidence_status is not EvidenceStatus.NUMERICAL
        ):
            raise Width256BranchWeightSamplingError(
                "Z-phase sampling cannot claim an exhaustive maximum"
            )


@dataclass(frozen=True, slots=True)
class VariantBranchWeightSampling:
    """One reviewed compressed QCLA schedule under the shared sampler."""

    variant: Literal["oop", "ip"]
    arithmetic_contract: str
    macro_depth: int
    candidate_level_count: int
    direct_ccz_event_count: int
    ppm_count: int
    macro_layer_source_gate_ids: tuple[tuple[str, ...], ...]
    sampled_outcome_token_count: int
    evaluated_branch_ppm_instance_count: int
    levels: tuple[SampledLevelWeightDistribution, ...]
    global_sampled_maximum: int
    global_support_weight_upper_bound: int
    maximum_level_sampled_to_upper_gap: int
    support_relevant_assignment_sha256: str
    sampled_level_matrix_sha256: str
    sampled_z_level_count: int
    exact_x_level_count: int
    sample_count: int = BRANCH_SAMPLE_COUNT
    sample_seed: str = BRANCH_SAMPLE_SEED
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL

    def __post_init__(self) -> None:
        if (
            self.variant not in {"oop", "ip"}
            or self.macro_depth < 1
            or self.candidate_level_count != 2 * self.macro_depth
            or len(self.levels) != self.candidate_level_count
            or len(self.macro_layer_source_gate_ids) != self.macro_depth
            or sum(len(layer) for layer in self.macro_layer_source_gate_ids)
            != self.direct_ccz_event_count
            or self.ppm_count != 6 * self.direct_ccz_event_count
            or self.sampled_outcome_token_count != 2 * self.direct_ccz_event_count
            or self.evaluated_branch_ppm_instance_count
            != self.sample_count * self.ppm_count
            or self.global_sampled_maximum
            != max(level.sampled_maximum for level in self.levels)
            or self.global_support_weight_upper_bound
            != max(level.support_weight_upper_bound for level in self.levels)
            or self.maximum_level_sampled_to_upper_gap
            != max(level.sampled_to_upper_gap for level in self.levels)
            or len(self.support_relevant_assignment_sha256) != 64
            or self.sampled_level_matrix_sha256
            != _digest(
                tuple(level.branch_maximum_weights for level in self.levels)
            )
            or self.sampled_z_level_count != self.macro_depth
            or self.exact_x_level_count != self.macro_depth
            or self.sample_count != BRANCH_SAMPLE_COUNT
            or self.sample_seed != BRANCH_SAMPLE_SEED
            or self.evidence_status is not EvidenceStatus.NUMERICAL
        ):
            raise Width256BranchWeightSamplingError(
                "invalid variant branch-weight study"
            )


@dataclass(frozen=True, slots=True)
class Width256OopIpBranchWeightStudy:
    """Shared OOP/IP branchwise PPM-weight comparison."""

    task_id: str
    experiment_id: str
    width: int
    oop: VariantBranchWeightSampling
    ip: VariantBranchWeightSampling
    total_evaluated_branch_ppm_instance_count: int
    comparison_claim: str
    sample_count: int = BRANCH_SAMPLE_COUNT
    sample_seed: str = BRANCH_SAMPLE_SEED
    sampled_maximum_is_global_true_maximum: bool = False
    complete_native_schedule: bool = False
    native_cycles: int | None = None
    runtime_seconds: float | None = None
    physical_qubits: int | None = None
    failure_probability: float | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL
    validation_status: str = "pending_independent_replay"
    schema: str = WIDTH256_BRANCH_WEIGHT_SCHEMA
    schema_version: int = WIDTH256_BRANCH_WEIGHT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        finite = (
            self.native_cycles,
            self.runtime_seconds,
            self.physical_qubits,
            self.failure_probability,
        )
        if (
            self.task_id != "T-20260907-002"
            or self.experiment_id != "E-20260907-002"
            or self.width != 256
            or self.oop.variant != "oop"
            or self.ip.variant != "ip"
            or self.total_evaluated_branch_ppm_instance_count
            != self.oop.evaluated_branch_ppm_instance_count
            + self.ip.evaluated_branch_ppm_instance_count
            or self.sample_count != BRANCH_SAMPLE_COUNT
            or self.sample_seed != BRANCH_SAMPLE_SEED
            or self.sampled_maximum_is_global_true_maximum
            or self.complete_native_schedule
            or any(value is not None for value in finite)
            or self.evidence_status is not EvidenceStatus.NUMERICAL
            or self.schema != WIDTH256_BRANCH_WEIGHT_SCHEMA
            or self.schema_version != WIDTH256_BRANCH_WEIGHT_SCHEMA_VERSION
        ):
            raise Width256BranchWeightSamplingError(
                "invalid width-256 OOP/IP comparison"
            )


Gate = OopQclaGate | QclaGate
Trace = OopQclaTrace | QclaTrace


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest().upper()


def _nearest_rank(ordered: tuple[int, ...], percentile: int) -> int:
    if not ordered or not 1 <= percentile <= 100:
        raise Width256BranchWeightSamplingError("invalid nearest-rank request")
    index = (percentile * len(ordered) + 99) // 100 - 1
    return ordered[index]


def _sample_mask(variable: str) -> int:
    byte_count = (BRANCH_SAMPLE_COUNT + 7) // 8
    raw = int.from_bytes(
        hashlib.shake_256(f"{BRANCH_SAMPLE_SEED}|{variable}".encode()).digest(
            byte_count
        ),
        "little",
    )
    all_mask = (1 << BRANCH_SAMPLE_COUNT) - 1
    raw &= all_mask
    raw &= ~1
    raw |= 1 << 1
    return raw


def _parallel_mask_weights(masks: tuple[int, ...]) -> tuple[int, ...]:
    """Count active logical values for all packed samples using bit planes."""

    planes: list[int] = []
    for mask in masks:
        carry = mask
        plane = 0
        while carry:
            if plane == len(planes):
                planes.append(0)
            next_carry = planes[plane] & carry
            planes[plane] ^= carry
            carry = next_carry
            plane += 1
    return tuple(
        sum(
            ((plane >> sample) & 1) << bit
            for bit, plane in enumerate(planes)
        )
        for sample in range(BRANCH_SAMPLE_COUNT)
    )


def _column_xor(
    columns: dict[str, dict[str, int]],
    target: str,
    source: str,
    condition_mask: int,
) -> None:
    target_column = columns[target]
    for logical, source_mask in tuple(columns[source].items()):
        updated = target_column.get(logical, 0) ^ (source_mask & condition_mask)
        if updated == 0:
            target_column.pop(logical, None)
        else:
            target_column[logical] = updated


def _source_cnot_conjugate(
    columns: dict[str, dict[str, int]], control: str, target: str
) -> None:
    target_column = columns[target]
    for logical, mask in tuple(columns[control].items()):
        updated = target_column.get(logical, 0) ^ mask
        if updated == 0:
            target_column.pop(logical, None)
        else:
            target_column[logical] = updated
    for column in columns.values():
        target_mask = column.get(target, 0)
        updated = column.get(control, 0) ^ target_mask
        if updated == 0:
            column.pop(control, None)
        else:
            column[control] = updated


def _assignment_digest(token_masks: dict[str, int]) -> str:
    width = (BRANCH_SAMPLE_COUNT + 7) // 8
    payload = tuple(
        (token, mask.to_bytes(width, "little").hex())
        for token, mask in sorted(token_masks.items())
    )
    return _digest(payload)


def _distribution(
    *,
    candidate_level: int,
    macro_layer: int,
    phase: int,
    ppm_count: int,
    weights: tuple[int, ...],
    upper_bound: int,
    upper_bound_kind: str,
    upper_evidence: EvidenceStatus,
) -> SampledLevelWeightDistribution:
    ordered = tuple(sorted(weights))
    exact = phase == 2
    return SampledLevelWeightDistribution(
        candidate_level=candidate_level,
        macro_layer=macro_layer,
        phase=phase,
        axis={1: "Z", 2: "X"}[phase],
        ppm_count=ppm_count,
        branch_maximum_weights=weights,
        forced_all_zero_weight=weights[0],
        forced_all_one_weight=weights[1],
        hashed_branch_maximum=max(weights[2:]),
        minimum=ordered[0],
        p50=_nearest_rank(ordered, 50),
        p95=_nearest_rank(ordered, 95),
        p99=_nearest_rank(ordered, 99),
        sampled_maximum=ordered[-1],
        support_weight_upper_bound=upper_bound,
        sampled_to_upper_gap=upper_bound - ordered[-1],
        upper_bound_kind=upper_bound_kind,
        upper_bound_evidence_status=upper_evidence,
        sampled_maximum_is_true_maximum=exact,
        sample_vector_sha256=_digest(weights),
        evidence_status=(EvidenceStatus.PROVED if exact else EvidenceStatus.NUMERICAL),
    )


def _sample_variant(
    *,
    variant: Literal["oop", "ip"],
    trace: Trace,
    event_trace: DirectCczEventTrace,
    macro_layer_ids: tuple[tuple[str, ...], ...],
    upper_levels: tuple[Any, ...],
    upper_bound_kind: str,
    arithmetic_contract: str,
) -> VariantBranchWeightSampling:
    gate_by_id: dict[str, Gate] = {gate.gate_id: gate for gate in trace.gates}
    event_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    groups = tuple(
        tuple(gate_by_id[gate_id] for gate_id in layer)
        for layer in macro_layer_ids
    )
    logical_values = tuple(
        sorted({value for gate in trace.gates for value in gate.logical_support})
    )
    all_mask = (1 << BRANCH_SAMPLE_COUNT) - 1
    columns = {value: {value: all_mask} for value in logical_values}
    cnot_by_layer: dict[int, list[Gate]] = {}
    for gate in trace.gates:
        if gate.kind is QclaGateKind.CNOT:
            cnot_by_layer.setdefault(gate.algorithmic_layer, []).append(gate)
    applied_cnot_layers: set[int] = set()
    token_masks: dict[str, int] = {}
    levels_by_number = {level.candidate_level: level for level in upper_levels}
    sampled_levels: list[SampledLevelWeightDistribution] = []
    for macro_layer, group in enumerate(groups, start=1):
        lower = min(gate.algorithmic_layer for gate in group)
        upper = max(gate.algorithmic_layer for gate in group)
        if any(lower <= layer <= upper for layer in cnot_by_layer):
            raise Width256BranchWeightSamplingError(
                "reviewed macro unexpectedly crosses a CNOT barrier"
            )
        for layer in sorted(cnot_by_layer):
            if layer >= lower or layer in applied_cnot_layers:
                continue
            for gate in cnot_by_layer[layer]:
                _source_cnot_conjugate(
                    columns, gate.controls[0], gate.target
                )
            applied_cnot_layers.add(layer)
        branch_maximum = [1] * BRANCH_SAMPLE_COUNT
        for gate in group:
            event = event_by_source[gate.gate_id]
            for data_value in event.data:
                weights = _parallel_mask_weights(
                    (*columns[data_value].values(), all_mask)
                )
                for sample, weight in enumerate(weights):
                    branch_maximum[sample] = max(
                        branch_maximum[sample], weight
                    )
        z_level_number = 2 * macro_layer - 1
        x_level_number = 2 * macro_layer
        z_upper = levels_by_number[z_level_number]
        x_upper = levels_by_number[x_level_number]
        z_evidence = z_upper.evidence_status
        x_evidence = x_upper.evidence_status
        sampled_levels.append(
            _distribution(
                candidate_level=z_level_number,
                macro_layer=macro_layer,
                phase=1,
                ppm_count=z_upper.logical_ppm_count,
                weights=tuple(branch_maximum),
                upper_bound=z_upper.maximum_ppm_weight_upper_bound,
                upper_bound_kind=upper_bound_kind,
                upper_evidence=z_evidence,
            )
        )
        sampled_levels.append(
            _distribution(
                candidate_level=x_level_number,
                macro_layer=macro_layer,
                phase=2,
                ppm_count=x_upper.logical_ppm_count,
                weights=(1,) * BRANCH_SAMPLE_COUNT,
                upper_bound=x_upper.maximum_ppm_weight_upper_bound,
                upper_bound_kind="exact_fresh_resource_singleton",
                upper_evidence=x_evidence,
            )
        )
        for gate in group:
            event = event_by_source[gate.gate_id]
            c0, c1, target = event.data
            for source, ppm_index in ((c1, 0), (c0, 1)):
                token = event.ppms[ppm_index].outcome_token
                mask = token_masks.setdefault(token, _sample_mask(token))
                _column_xor(columns, target, source, mask)
    ppm_count = sum(level.ppm_count for level in sampled_levels)
    result = VariantBranchWeightSampling(
        variant=variant,
        arithmetic_contract=arithmetic_contract,
        macro_depth=len(groups),
        candidate_level_count=len(sampled_levels),
        direct_ccz_event_count=len(event_trace.injection_events),
        ppm_count=ppm_count,
        macro_layer_source_gate_ids=macro_layer_ids,
        sampled_outcome_token_count=len(token_masks),
        evaluated_branch_ppm_instance_count=BRANCH_SAMPLE_COUNT * ppm_count,
        levels=tuple(sampled_levels),
        global_sampled_maximum=max(
            level.sampled_maximum for level in sampled_levels
        ),
        global_support_weight_upper_bound=max(
            level.support_weight_upper_bound for level in sampled_levels
        ),
        maximum_level_sampled_to_upper_gap=max(
            level.sampled_to_upper_gap for level in sampled_levels
        ),
        support_relevant_assignment_sha256=_assignment_digest(token_masks),
        sampled_level_matrix_sha256=_digest(
            tuple(level.branch_maximum_weights for level in sampled_levels)
        ),
        sampled_z_level_count=len(groups),
        exact_x_level_count=len(groups),
    )
    return result


def build_width256_oop_ip_branch_weight_study(
    *,
    oop_source: OopQclaTrace,
    oop_events: DirectCczEventTrace,
    oop_study: Width256CommutationAwareStudy,
    ip_source: QclaTrace,
    ip_events: DirectCczEventTrace,
    ip_study: Width256IpCommutationAwareStudy,
) -> Width256OopIpBranchWeightStudy:
    """Build the common deterministic OOP/IP branch-weight comparison."""

    if oop_source.width != 256 or ip_source.width != 256:
        raise Width256BranchWeightSamplingError("both source widths must be 256")
    if (
        oop_events.source_trace_id != oop_source.trace_id
        or ip_events.source_trace_id != ip_source.trace_id
    ):
        raise Width256BranchWeightSamplingError("event/source trace mismatch")
    oop = _sample_variant(
        variant="oop",
        trace=oop_source,
        event_trace=oop_events,
        macro_layer_ids=oop_study.unitary.macro_layers,
        upper_levels=oop_study.unitary.candidate_levels,
        upper_bound_kind="exact_possible_support_envelope",
        arithmetic_contract=oop_source.arithmetic_contract,
    )
    ip = _sample_variant(
        variant="ip",
        trace=ip_source,
        event_trace=ip_events,
        macro_layer_ids=ip_study.macro_layers,
        upper_levels=ip_study.candidate_levels,
        upper_bound_kind="sound_may_support_envelope",
        arithmetic_contract=ip_source.arithmetic_contract,
    )
    return Width256OopIpBranchWeightStudy(
        task_id="T-20260907-002",
        experiment_id="E-20260907-002",
        width=256,
        oop=oop,
        ip=ip,
        total_evaluated_branch_ppm_instance_count=(
            oop.evaluated_branch_ppm_instance_count
            + ip.evaluated_branch_ppm_instance_count
        ),
        comparison_claim=(
            "sampled branch maxima and nearest-rank quantiles are NUMERICAL "
            "lower witnesses; reviewed support envelopes remain separate ceilings"
        ),
    )


def width256_oop_ip_branch_weight_study_to_data(
    study: Width256OopIpBranchWeightStudy,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible study data."""

    def convert(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, tuple):
            return [convert(item) for item in value]
        if isinstance(value, list):
            return [convert(item) for item in value]
        if isinstance(value, dict):
            return {str(key): convert(item) for key, item in value.items()}
        return value

    data = convert(asdict(study))
    if not isinstance(data, dict):  # pragma: no cover - dataclass invariant
        raise Width256BranchWeightSamplingError("study serialization failed")
    return data


def dumps_width256_oop_ip_branch_weight_study(
    study: Width256OopIpBranchWeightStudy,
) -> str:
    """Serialize the study deterministically."""

    return json.dumps(
        width256_oop_ip_branch_weight_study_to_data(study),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
