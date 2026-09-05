"""Independent replay of direct-CCZ QCLA logical-support envelopes.

This module imports neither the direct-CCZ compiler nor any scheduler.  It
reconstructs the pinned six-PPM event names and propagates support directly
from the source QCLA trace.  Exact modes use explicit ANF term sets; large
in-place traces use an independent may-support and 512-branch evaluator.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from ecdlp_ftqc.circuits import (
    OopQclaTrace,
    QclaGateKind,
    QclaTrace,
    build_oop_qcla_trace,
    build_qcla_trace,
)

CERTIFICATE_SCHEMA = "ecdlp-ftqc/direct-ccz-qcla-scalable-support-certificate"
SUPPORT_COORDINATE = "logical_support_hypergraph_not_native_geometry"
EXACT_MODEL = "exact-boolean-anf-z-support-components-v1"
SAMPLED_MODEL = "sound-may-envelope-with-concrete-branch-witnesses-v1"
MEASUREMENT_IDS = ("zz_0", "zz_1", "zz_2", "x_0", "x_1", "x_2")
SAMPLE_COUNT = 512
SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"

Poly = frozenset[frozenset[str]]
ONE: Poly = frozenset((frozenset(),))
Variant = Literal["oop", "ip"]


class DirectCczPpmSupportReplayError(ValueError):
    """Raised when serialized support data is malformed."""


@dataclass(frozen=True, slots=True)
class DirectCczPpmSupportReplaySummary:
    """Independent replay result for one sweep and its width-256 hypergraphs."""

    widths: tuple[int, ...]
    certificate_count: int
    width_256_hypergraph_count: int
    checks: tuple[tuple[str, bool], ...]

    @property
    def all_passed(self) -> bool:
        return all(passed for _, passed in self.checks)


@dataclass(frozen=True, slots=True)
class _Profile:
    operation_id: str
    source_gate_id: str
    source_algorithmic_layer: int
    injection_layer: int
    axis: str
    possible: tuple[str, ...]
    witnessed: tuple[str, ...]
    unwitnessed: tuple[str, ...]
    guaranteed: tuple[str, ...]
    branch_dependent: tuple[str, ...]
    possible_exact: bool
    monomial_count: int | None


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) for key in value
    ):
        raise DirectCczPpmSupportReplayError(
            f"{path} must be a string-keyed mapping"
        )
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DirectCczPpmSupportReplayError(f"{path} must be a sequence")
    return value


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _sample_mask(variable: str) -> int:
    byte_count = (SAMPLE_COUNT + 7) // 8
    raw = int.from_bytes(
        hashlib.shake_256(f"{SAMPLE_SEED}|{variable}".encode()).digest(byte_count),
        "little",
    )
    raw &= (1 << SAMPLE_COUNT) - 1
    raw &= ~1
    raw |= 1 << 1
    return raw


def _maximum_parallel_mask_weight(masks: tuple[int, ...]) -> int:
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
    return max(
        sum(
            ((plane >> sample) & 1) << index
            for index, plane in enumerate(planes)
        )
        for sample in range(SAMPLE_COUNT)
    )


def _xor(left: Poly, right: Poly) -> Poly:
    return left.symmetric_difference(right)


def _times_variable(poly: Poly, variable: str) -> Poly:
    return frozenset(frozenset((*monomial, variable)) for monomial in poly)


def _logical_values(trace: QclaTrace | OopQclaTrace) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                logical
                for gate in trace.gates
                for logical in gate.logical_support
            }
        )
    )


def _event_parts(ordinal: int) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    event_id = f"direct-ccz:{ordinal:06d}"
    resources = tuple(f"{event_id}:resource:{index}" for index in range(3))
    operations = tuple(
        f"{event_id}:ppm:{measurement_id}"
        for measurement_id in MEASUREMENT_IDS
    )
    return event_id, resources, operations


def _source_cnot_exact(
    columns: dict[str, dict[str, Poly]],
    control: str,
    target: str,
) -> None:
    target_column = columns[target]
    for logical, poly in tuple(columns[control].items()):
        updated = _xor(target_column.get(logical, frozenset()), poly)
        if updated:
            target_column[logical] = updated
        else:
            target_column.pop(logical, None)
    for column in columns.values():
        target_poly = column.get(target, frozenset())
        updated = _xor(column.get(control, frozenset()), target_poly)
        if updated:
            column[control] = updated
        else:
            column.pop(control, None)


def _conditional_exact(
    columns: dict[str, dict[str, Poly]],
    target: str,
    source: str,
    variable: str,
) -> None:
    target_column = columns[target]
    for logical, poly in tuple(columns[source].items()):
        updated = _xor(
            target_column.get(logical, frozenset()),
            _times_variable(poly, variable),
        )
        if updated:
            target_column[logical] = updated
        else:
            target_column.pop(logical, None)


def _source_cnot_sampled(
    sampled: dict[str, dict[str, int]],
    may: dict[str, set[str]],
    control: str,
    target: str,
) -> None:
    target_column = sampled[target]
    for logical, mask in tuple(sampled[control].items()):
        updated = target_column.get(logical, 0) ^ mask
        if updated:
            target_column[logical] = updated
        else:
            target_column.pop(logical, None)
    may[target].update(may[control])
    for sampled_column in sampled.values():
        updated = sampled_column.get(control, 0) ^ sampled_column.get(target, 0)
        if updated:
            sampled_column[control] = updated
        else:
            sampled_column.pop(control, None)
    for may_column in may.values():
        if target in may_column:
            may_column.add(control)


def _conditional_sampled(
    sampled: dict[str, dict[str, int]],
    may: dict[str, set[str]],
    target: str,
    source: str,
    condition: int,
) -> None:
    target_column = sampled[target]
    for logical, mask in tuple(sampled[source].items()):
        updated = target_column.get(logical, 0) ^ (mask & condition)
        if updated:
            target_column[logical] = updated
        else:
            target_column.pop(logical, None)
    may[target].update(may[source])


def _exact_profiles(trace: QclaTrace | OopQclaTrace) -> tuple[_Profile, ...]:
    logical_values = _logical_values(trace)
    columns = {logical: {logical: ONE} for logical in logical_values}
    profiles: list[_Profile] = []
    ordinal = 0
    for gate in trace.gates:
        if gate.kind is QclaGateKind.X:
            continue
        if gate.kind is QclaGateKind.CNOT:
            _source_cnot_exact(columns, gate.controls[0], gate.target)
            continue
        if gate.kind is not QclaGateKind.TOFFOLI:
            raise DirectCczPpmSupportReplayError("unsupported source gate")
        event_id, resources, operations = _event_parts(ordinal)
        data = (gate.controls[0], gate.controls[1], gate.target)
        for index, operation_id in enumerate(operations):
            if index < 3:
                values = dict(columns[data[index]])
                values[resources[index]] = ONE
                possible = tuple(sorted(values))
                guaranteed = tuple(
                    logical for logical in possible if values[logical] == ONE
                )
                branch = tuple(
                    logical
                    for logical in possible
                    if values[logical] not in {frozenset(), ONE}
                )
                monomial_count = sum(len(poly) for poly in values.values())
                layer = 1
                axis = "Z"
            else:
                possible = (resources[index - 3],)
                guaranteed = possible
                branch = ()
                monomial_count = 1
                layer = 2
                axis = "X"
            profiles.append(
                _Profile(
                    operation_id=operation_id,
                    source_gate_id=gate.gate_id,
                    source_algorithmic_layer=gate.algorithmic_layer,
                    injection_layer=layer,
                    axis=axis,
                    possible=possible,
                    witnessed=possible,
                    unwitnessed=(),
                    guaranteed=guaranteed,
                    branch_dependent=branch,
                    possible_exact=True,
                    monomial_count=monomial_count,
                )
            )
        _conditional_exact(
            columns,
            data[2],
            data[1],
            f"{event_id}:outcome:zz_0",
        )
        _conditional_exact(
            columns,
            data[2],
            data[0],
            f"{event_id}:outcome:zz_1",
        )
        ordinal += 1
    return tuple(profiles)


def _sampled_profiles(
    trace: QclaTrace | OopQclaTrace,
) -> tuple[tuple[_Profile, ...], int]:
    logical_values = _logical_values(trace)
    all_mask = (1 << SAMPLE_COUNT) - 1
    sampled = {logical: {logical: all_mask} for logical in logical_values}
    may = {logical: {logical} for logical in logical_values}
    profiles: list[_Profile] = []
    maximum_sampled_branch_weight = 1
    ordinal = 0
    for gate in trace.gates:
        if gate.kind is QclaGateKind.X:
            continue
        if gate.kind is QclaGateKind.CNOT:
            _source_cnot_sampled(sampled, may, gate.controls[0], gate.target)
            continue
        if gate.kind is not QclaGateKind.TOFFOLI:
            raise DirectCczPpmSupportReplayError("unsupported source gate")
        event_id, resources, operations = _event_parts(ordinal)
        data = (gate.controls[0], gate.controls[1], gate.target)
        for index, operation_id in enumerate(operations):
            if index < 3:
                possible = tuple(sorted({resources[index], *may[data[index]]}))
                masks = dict(sampled[data[index]])
                masks[resources[index]] = all_mask
                witnessed_size = sum(mask != 0 for mask in masks.values())
                if witnessed_size > maximum_sampled_branch_weight:
                    maximum_sampled_branch_weight = max(
                        maximum_sampled_branch_weight,
                        _maximum_parallel_mask_weight(
                            tuple(mask for mask in masks.values() if mask)
                        ),
                    )
                witnessed = tuple(
                    logical for logical in possible if masks.get(logical, 0)
                )
                unwitnessed = tuple(
                    logical for logical in possible if not masks.get(logical, 0)
                )
                guaranteed = (resources[index],)
                branch = tuple(
                    logical
                    for logical in possible
                    if logical != resources[index]
                    and masks.get(logical, 0) not in {0, all_mask}
                )
                layer = 1
                axis = "Z"
            else:
                possible = (resources[index - 3],)
                witnessed = possible
                unwitnessed = ()
                guaranteed = possible
                branch = ()
                layer = 2
                axis = "X"
            profiles.append(
                _Profile(
                    operation_id=operation_id,
                    source_gate_id=gate.gate_id,
                    source_algorithmic_layer=gate.algorithmic_layer,
                    injection_layer=layer,
                    axis=axis,
                    possible=possible,
                    witnessed=witnessed,
                    unwitnessed=unwitnessed,
                    guaranteed=guaranteed,
                    branch_dependent=branch,
                    possible_exact=not unwitnessed,
                    monomial_count=None,
                )
            )
        _conditional_sampled(
            sampled,
            may,
            data[2],
            data[1],
            _sample_mask(f"{event_id}:outcome:zz_0"),
        )
        _conditional_sampled(
            sampled,
            may,
            data[2],
            data[0],
            _sample_mask(f"{event_id}:outcome:zz_1"),
        )
        ordinal += 1
    return tuple(profiles), maximum_sampled_branch_weight


def _profile_data(profile: _Profile) -> dict[str, object]:
    return {
        "axis": profile.axis,
        "branch_dependent_logical_support": list(profile.branch_dependent),
        "evidence_status": "PROVED",
        "guaranteed_logical_support": list(profile.guaranteed),
        "injection_layer": profile.injection_layer,
        "maximum_weight_upper_bound": len(profile.possible),
        "minimum_weight_lower_bound": len(profile.guaranteed),
        "operation_id": profile.operation_id,
        "possible_logical_support": list(profile.possible),
        "possible_support_exact": profile.possible_exact,
        "possible_support_sha256": _digest(profile.possible),
        "source_algorithmic_layer": profile.source_algorithmic_layer,
        "source_gate_id": profile.source_gate_id,
        "unwitnessed_may_logical_support": list(profile.unwitnessed),
        "witnessed_logical_support": list(profile.witnessed),
    }


def _batch_data(profiles: tuple[_Profile, ...], level: int) -> dict[str, object]:
    possible_counts = Counter(
        logical for profile in profiles for logical in profile.possible
    )
    witnessed_counts = Counter(
        logical for profile in profiles for logical in profile.witnessed
    )
    maximum_contact = max(possible_counts.values())
    operation_ids = tuple(profile.operation_id for profile in profiles)
    possible_union = tuple(sorted(possible_counts))
    return {
        "batch_level": level,
        "branch_dependent_profile_count": sum(
            bool(profile.branch_dependent) for profile in profiles
        ),
        "coordinate": SUPPORT_COORDINATE,
        "evidence_status": (
            "PROVED" if all(profile.possible_exact for profile in profiles) else "CHECK"
        ),
        "exact_hyperedge_count": len(profiles),
        "guaranteed_support_union": sorted(
            {
                logical
                for profile in profiles
                for logical in profile.guaranteed
            }
        ),
        "injection_layer": profiles[0].injection_layer,
        "maximum_possible_contact_count": maximum_contact,
        "maximum_possible_contact_logical_values": [
            logical
            for logical, count in sorted(possible_counts.items())
            if count == maximum_contact
        ],
        "maximum_ppm_weight_upper_bound": max(
            len(profile.possible) for profile in profiles
        ),
        "maximum_witnessed_contact_count": max(witnessed_counts.values()),
        "maximum_witnessed_support_union_size": max(
            len(profile.witnessed) for profile in profiles
        ),
        "operation_id_sha256": _digest(operation_ids),
        "operation_ids": list(operation_ids),
        "pair_records_materialized": False,
        "possible_contact_counts": [
            {"contact_count": count, "logical_value": logical}
            for logical, count in sorted(possible_counts.items())
        ],
        "possible_support_union": list(possible_union),
        "possible_support_union_sha256": _digest(possible_union),
        "ppm_count": len(profiles),
        "source_algorithmic_layer": profiles[0].source_algorithmic_layer,
        "total_possible_support_incidence": sum(
            len(profile.possible) for profile in profiles
        ),
        "total_witnessed_support_incidence": sum(
            len(profile.witnessed) for profile in profiles
        ),
        "witnessed_support_union": sorted(
            {logical for profile in profiles for logical in profile.witnessed}
        ),
    }


def _batches(profiles: tuple[_Profile, ...]) -> tuple[dict[str, object], ...]:
    grouped: dict[tuple[int, int], list[_Profile]] = {}
    for profile in profiles:
        grouped.setdefault(
            (profile.source_algorithmic_layer, profile.injection_layer), []
        ).append(profile)
    return tuple(
        _batch_data(tuple(items), level)
        for level, (_, items) in enumerate(sorted(grouped.items()), start=1)
    )


def _integer_value(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DirectCczPpmSupportReplayError("expected an integer replay value")
    return value


def _expected_scalars(
    trace: QclaTrace | OopQclaTrace,
    variant: Variant,
    profiles: tuple[_Profile, ...],
    batches: tuple[dict[str, object], ...],
    maximum_sampled_branch_weight: int | None,
) -> dict[str, object]:
    exact = variant == "oop" or trace.width <= 8
    all_exact = all(profile.possible_exact for profile in profiles)
    first_branch = next(
        (
            (profile.operation_id, profile.source_gate_id,
             profile.source_algorithmic_layer, profile.branch_dependent[0])
            for profile in profiles
            if profile.branch_dependent
        ),
        None,
    )
    event_count = len(profiles) // 6
    return {
        "all_possible_supports_exact": all_exact,
        "asymptotic_certificate_size": (
            "output-sensitive sparse Boolean matrix plus emitted support incidences; "
            "no global PPM-pair table"
            if exact
            else "output-sensitive may-support matrix plus 512 parallel concrete "
            "branch witnesses and emitted support incidences; no global PPM-pair table"
        ),
        "branch_dependent_profile_count": sum(
            bool(profile.branch_dependent) for profile in profiles
        ),
        "candidate_batch_level_count": len(batches),
        "complete_native_schedule": False,
        "direct_ccz_event_count": event_count,
        "deterministic_branch_sample_count": 0 if exact else SAMPLE_COUNT,
        "deterministic_branch_sample_seed": None if exact else SAMPLE_SEED,
        "event_trace_id": f"{trace.trace_id}:direct-ccz-events-v2",
        "exact_activity_monomial_count": (
            sum(profile.monomial_count or 0 for profile in profiles)
            if exact
            else None
        ),
        "failure_probability": None,
        "maximum_batch_possible_contact_count": max(
            _integer_value(batch["maximum_possible_contact_count"])
            for batch in batches
        ),
        "maximum_batch_witnessed_contact_count": max(
            _integer_value(batch["maximum_witnessed_contact_count"])
            for batch in batches
        ),
        "maximum_ppm_weight_upper_bound": max(
            len(profile.possible) for profile in profiles
        ),
        "maximum_sampled_branch_weight": maximum_sampled_branch_weight,
        "maximum_witnessed_support_union_size": max(
            len(profile.witnessed) for profile in profiles
        ),
        "nonclifford_source_layer_count": len(batches) // 2,
        "outcome_independent_support_evidence_status": (
            "FALSIFIED" if first_branch is not None else (
                "PROVED" if exact else "INCONCLUSIVE"
            )
        ),
        "physical_qubits": None,
        "ppm_count": len(profiles),
        "records_checked": (
            len(trace.gates)
            + len(trace.dependencies)
            + event_count
            + len(profiles)
            + sum(len(profile.possible) for profile in profiles)
        ),
        "runtime_seconds": None,
        "schema": CERTIFICATE_SCHEMA,
        "schema_version": 1,
        "source_logical_value_count": len(_logical_values(trace)),
        "source_trace_id": trace.trace_id,
        "support_envelope_evidence_status": "PROVED" if all_exact else "CHECK",
        "support_model": EXACT_MODEL if exact else SAMPLED_MODEL,
        "surgery_rounds": None,
        "validation_counterexample": None,
        "variant": variant,
        "width": trace.width,
        "first_branch": first_branch,
    }


def _matches_scalars(
    item: Mapping[str, object],
    expected: Mapping[str, object],
) -> bool:
    for key, value in expected.items():
        if key == "first_branch":
            continue
        if item.get(key) != value:
            return False
    expected_branch = expected["first_branch"]
    raw_witness = item.get("branch_dependence_witness")
    if expected_branch is None:
        return raw_witness is None
    witness = _mapping(raw_witness, "$.branch_dependence_witness")
    branch = _sequence(expected_branch, "$.expected.first_branch")
    if len(branch) != 4:
        raise DirectCczPpmSupportReplayError("invalid expected branch witness")
    return (
        witness.get("operation_id") == branch[0]
        and witness.get("source_gate_id") == branch[1]
        and witness.get("source_algorithmic_layer") == branch[2]
        and witness.get("logical_value") == branch[3]
        and witness.get("evidence_status") == "FALSIFIED"
    )


def replay_direct_ccz_ppm_support(
    aggregate_certificates_data: object,
    width_256_hypergraphs_data: object,
    *,
    expected_widths: tuple[int, ...],
    independent_widths: tuple[int, ...] = (5, 8, 256),
) -> DirectCczPpmSupportReplaySummary:
    """Check the sweep and independently rebuild anchor support hypergraphs."""

    if not expected_widths or tuple(sorted(set(expected_widths))) != expected_widths:
        raise DirectCczPpmSupportReplayError(
            "expected widths must be sorted and unique"
        )
    raw_certificates = _sequence(
        aggregate_certificates_data, "$.aggregate_certificates"
    )
    replay_widths = tuple(
        width for width in independent_widths if width in set(expected_widths)
    )
    if tuple(sorted(set(replay_widths))) != replay_widths:
        raise DirectCczPpmSupportReplayError(
            "independent widths must be sorted and unique"
        )
    expected_order = tuple(
        (variant, width)
        for width in expected_widths
        for variant in ("oop", "ip")
    )
    observed_order: list[tuple[str, int]] = []
    reconstructed: dict[
        tuple[str, int],
        tuple[tuple[_Profile, ...], tuple[dict[str, object], ...], int | None],
    ] = {}
    scalar_match = True
    lightweight_match = True
    for index, raw in enumerate(raw_certificates):
        item = _mapping(raw, f"$.aggregate_certificates[{index}]")
        variant_raw = item.get("variant")
        width_raw = item.get("width")
        if variant_raw not in {"oop", "ip"} or not isinstance(width_raw, int):
            raise DirectCczPpmSupportReplayError("invalid certificate key")
        variant: Variant = variant_raw
        width = width_raw
        trace = (
            build_oop_qcla_trace(width)
            if variant == "oop"
            else build_qcla_trace(width)
        )
        toffoli_count = sum(
            gate.kind is QclaGateKind.TOFFOLI for gate in trace.gates
        )
        lightweight_match &= (
            item.get("schema") == CERTIFICATE_SCHEMA
            and item.get("schema_version") == 1
            and item.get("source_trace_id") == trace.trace_id
            and item.get("event_trace_id")
            == f"{trace.trace_id}:direct-ccz-events-v2"
            and item.get("direct_ccz_event_count") == toffoli_count
            and item.get("ppm_count") == 6 * toffoli_count
            and item.get("validation_counterexample") is None
        )
        if width not in replay_widths:
            observed_order.append((variant, width))
            continue
        if variant == "oop" or width <= 8:
            profiles = _exact_profiles(trace)
            maximum_sampled_branch_weight = None
        else:
            profiles, maximum_sampled_branch_weight = _sampled_profiles(trace)
        batches = _batches(profiles)
        reconstructed[(variant, width)] = (
            profiles,
            batches,
            maximum_sampled_branch_weight,
        )
        scalar_match &= _matches_scalars(
            item,
            _expected_scalars(
                trace,
                variant,
                profiles,
                batches,
                maximum_sampled_branch_weight,
            ),
        )
        observed_order.append((variant, width))

    raw_hypergraphs = _sequence(
        width_256_hypergraphs_data, "$.width_256_hypergraphs"
    )
    observed_hypergraph_order: list[tuple[str, int]] = []
    hypergraph_match = True
    for index, raw in enumerate(raw_hypergraphs):
        item = _mapping(raw, f"$.width_256_hypergraphs[{index}]")
        variant_raw = item.get("variant")
        width_raw = item.get("width")
        if variant_raw not in {"oop", "ip"} or width_raw != 256:
            raise DirectCczPpmSupportReplayError("invalid width-256 hypergraph key")
        variant = variant_raw
        profiles, batches, maximum_sampled_branch_weight = reconstructed[
            (variant, 256)
        ]
        hypergraph_match &= item.get("profiles") == [
            _profile_data(profile) for profile in profiles
        ]
        hypergraph_match &= item.get("batches") == list(batches)
        aggregate = dict(item)
        aggregate.pop("profiles", None)
        aggregate.pop("batches", None)
        trace = (
            build_oop_qcla_trace(256)
            if variant == "oop"
            else build_qcla_trace(256)
        )
        hypergraph_match &= _matches_scalars(
            aggregate,
            _expected_scalars(
                trace,
                variant,
                profiles,
                batches,
                maximum_sampled_branch_weight,
            ),
        )
        observed_hypergraph_order.append((variant, 256))

    return DirectCczPpmSupportReplaySummary(
        widths=expected_widths,
        certificate_count=len(raw_certificates),
        width_256_hypergraph_count=len(raw_hypergraphs),
        checks=(
            ("aggregate_order_and_coverage", tuple(observed_order) == expected_order),
            ("all_width_source_and_count_checks", lightweight_match),
            ("aggregate_scalar_reconstruction", scalar_match),
            (
                "width_256_hypergraph_order",
                tuple(observed_hypergraph_order) == (("oop", 256), ("ip", 256)),
            ),
            ("width_256_hypergraph_reconstruction", hypergraph_match),
            (
                "finite_architecture_outputs_absent",
                all(
                    _mapping(raw, "certificate").get(field) is None
                    for raw in (*raw_certificates, *raw_hypergraphs)
                    for field in (
                        "surgery_rounds",
                        "runtime_seconds",
                        "physical_qubits",
                        "failure_probability",
                    )
                ),
            ),
        ),
    )


def direct_ccz_ppm_support_replay_to_data(
    replay: DirectCczPpmSupportReplaySummary,
) -> dict[str, Any]:
    """Serialize an independent support replay summary."""

    return {
        "all_passed": replay.all_passed,
        "certificate_count": replay.certificate_count,
        "checks": [
            {"check": check, "passed": passed}
            for check, passed in replay.checks
        ],
        "schema": "ecdlp-ftqc/direct-ccz-qcla-support-independent-replay",
        "schema_version": 1,
        "width_256_hypergraph_count": replay.width_256_hypergraph_count,
        "widths": list(replay.widths),
    }
