"""Fail-closed direct-CCZ event adapter for clean OOP-QCLA Toffolis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ecdlp_ftqc.architectures import DirectCczCapability, DirectCczCapabilityError
from ecdlp_ftqc.circuits.qcla import QclaGateKind
from ecdlp_ftqc.circuits.qcla_oop import OopQclaGate, OopQclaTrace
from ecdlp_ftqc.metadata import EvidenceStatus

DIRECT_CCZ_EVENT_SCHEMA = "ecdlp-ftqc/direct-ccz-injection-event-trace"
DIRECT_CCZ_EVENT_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class DirectCczPpmEvent:
    """One exact PPM with its mapped logical support and outcome token."""

    event_id: str
    layer: int
    logical_support: tuple[str, ...]
    pauli_terms: tuple[str, ...]
    outcome_token: str
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.event_id or not self.outcome_token or self.layer < 1:
            raise DirectCczCapabilityError("PPM event fields cannot be empty")
        if not self.logical_support or len(self.logical_support) != len(self.pauli_terms):
            raise DirectCczCapabilityError("PPM support must align with Pauli terms")
        if len(self.logical_support) != len(set(self.logical_support)):
            raise DirectCczCapabilityError("PPM support must be unique")


@dataclass(frozen=True, slots=True)
class DirectCczSourceDependency:
    """One preserved architecture-neutral dependency between source gates."""

    predecessor_source_gate_id: str
    successor_source_gate_id: str
    logical_values: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        if (
            not self.predecessor_source_gate_id
            or not self.successor_source_gate_id
            or self.predecessor_source_gate_id == self.successor_source_gate_id
        ):
            raise DirectCczCapabilityError("source dependency endpoints are invalid")
        if not self.logical_values or len(self.logical_values) != len(
            set(self.logical_values)
        ):
            raise DirectCczCapabilityError("source dependency values must be unique")
        if self.reason != "wire_order":
            raise DirectCczCapabilityError("unsupported source dependency reason")


@dataclass(frozen=True, slots=True)
class DirectCczInjectionEvent:
    """One source CCX represented as H--CCZ-injection--H."""

    event_id: str
    source_gate_id: str
    source_algorithmic_layer: int
    data: tuple[str, str, str]
    resource: tuple[str, str, str]
    basis_changes_before: tuple[str, ...]
    ppms: tuple[DirectCczPpmEvent, ...]
    correction_frame: tuple[str, ...]
    basis_changes_after: tuple[str, ...]
    reaction_dependencies: tuple[str, ...]
    resource_consumed: bool
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.event_id or not self.source_gate_id or self.source_algorithmic_layer < 1:
            raise DirectCczCapabilityError("injection event identity is invalid")
        if len(set(self.data)) != 3 or len(set(self.resource)) != 3:
            raise DirectCczCapabilityError("data and CCZ resource supports must each have arity three")
        if set(self.data) & set(self.resource):
            raise DirectCczCapabilityError("data and resource supports must be disjoint")
        if not self.resource_consumed:
            raise DirectCczCapabilityError("CCZ injection must consume its resource")
        outcome_tokens = tuple(ppm.outcome_token for ppm in self.ppms)
        if len(outcome_tokens) != 6 or len(outcome_tokens) != len(set(outcome_tokens)):
            raise DirectCczCapabilityError("direct CCZ injection requires six unique outcomes")
        if set(self.reaction_dependencies) != set(outcome_tokens):
            raise DirectCczCapabilityError("reaction dependencies must name every PPM outcome")
        expected_basis = (f"H({self.data[2]})",)
        if self.basis_changes_before != expected_basis or self.basis_changes_after != expected_basis:
            raise DirectCczCapabilityError("source CCX requires H basis changes around CCZ")
        if not self.correction_frame:
            raise DirectCczCapabilityError("admitted injection requires an exact correction map")


@dataclass(frozen=True, slots=True)
class DirectCczEventTrace:
    """Direct-CCZ candidates plus logical Clifford pass-through gates."""

    trace_id: str
    source_trace_id: str
    source_trace_schema_version: int
    capability_id: str
    injection_events: tuple[DirectCczInjectionEvent, ...]
    passthrough_clifford_gate_ids: tuple[str, ...]
    source_dependencies: tuple[DirectCczSourceDependency, ...]
    complete_native_schedule: bool = False
    schema: str = DIRECT_CCZ_EVENT_SCHEMA
    schema_version: int = DIRECT_CCZ_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trace_id or not self.source_trace_id or not self.capability_id:
            raise DirectCczCapabilityError("direct-CCZ trace identity cannot be empty")
        if self.source_trace_schema_version < 1:
            raise DirectCczCapabilityError("source trace schema version must be positive")
        if self.schema != DIRECT_CCZ_EVENT_SCHEMA or self.schema_version != DIRECT_CCZ_EVENT_SCHEMA_VERSION:
            raise DirectCczCapabilityError("unsupported direct-CCZ event schema")
        event_ids = tuple(event.event_id for event in self.injection_events)
        source_ids = tuple(event.source_gate_id for event in self.injection_events)
        if len(event_ids) != len(set(event_ids)) or len(source_ids) != len(set(source_ids)):
            raise DirectCczCapabilityError("direct-CCZ event and source IDs must be unique")
        if len(self.passthrough_clifford_gate_ids) != len(set(self.passthrough_clifford_gate_ids)):
            raise DirectCczCapabilityError("passthrough Clifford IDs must be unique")
        source_gate_ids = {*source_ids, *self.passthrough_clifford_gate_ids}
        dependency_pairs: set[tuple[str, str]] = set()
        for dependency in self.source_dependencies:
            endpoints = {
                dependency.predecessor_source_gate_id,
                dependency.successor_source_gate_id,
            }
            if not endpoints <= source_gate_ids:
                raise DirectCczCapabilityError("source dependency names an unknown gate")
            pair = (
                dependency.predecessor_source_gate_id,
                dependency.successor_source_gate_id,
            )
            if pair in dependency_pairs:
                raise DirectCczCapabilityError("source dependency endpoints must be unique")
            dependency_pairs.add(pair)
        if self.complete_native_schedule:
            raise DirectCczCapabilityError("this adapter does not create a native schedule")


def _map_role(
    role: str,
    data: tuple[str, str, str],
    resource: tuple[str, str, str],
) -> str:
    family, raw_index = role.split("_", maxsplit=1)
    index = int(raw_index)
    if family == "data":
        return data[index]
    if family == "resource":
        return resource[index]
    raise DirectCczCapabilityError(f"unsupported direct-CCZ operand role {role!r}")


def _require_event_capability(capability: DirectCczCapability) -> None:
    missing = capability.missing_for_event_lowering
    if missing:
        raise DirectCczCapabilityError(
            "direct-CCZ event lowering is not admitted; missing: " + ", ".join(missing)
        )


def lower_oop_toffoli_to_direct_ccz_event(
    gate: OopQclaGate,
    capability: DirectCczCapability,
    *,
    ordinal: int,
) -> DirectCczInjectionEvent:
    """Lower one source Toffoli only when the exact capability is admitted."""

    _require_event_capability(capability)
    if gate.kind is not QclaGateKind.TOFFOLI or len(gate.controls) != 2:
        raise DirectCczCapabilityError("direct-CCZ lowering accepts only source Toffolis")
    data = (gate.controls[0], gate.controls[1], gate.target)
    event_id = f"direct-ccz:{ordinal:06d}"
    resource = tuple(f"{event_id}:resource:{index}" for index in range(3))
    typed_resource = (resource[0], resource[1], resource[2])
    ppms = tuple(
        DirectCczPpmEvent(
            event_id=f"{event_id}:ppm:{measurement.measurement_id}",
            layer=measurement.layer,
            logical_support=tuple(
                _map_role(role, data, typed_resource)
                for role in measurement.operand_roles
            ),
            pauli_terms=measurement.pauli_terms,
            outcome_token=f"{event_id}:outcome:{measurement.measurement_id}",
            evidence_status=measurement.evidence_status,
        )
        for measurement in capability.injection.measurements
    )
    outcome_by_measurement = {
        measurement.measurement_id: ppm.outcome_token
        for measurement, ppm in zip(capability.injection.measurements, ppms, strict=True)
    }
    exact_map = capability.injection.correction.exact_boolean_map
    if exact_map is None:
        raise DirectCczCapabilityError("exact correction map disappeared after admission")
    corrections = []
    for expression in exact_map:
        mapped = expression
        for index, logical in enumerate(data):
            mapped = mapped.replace(f"data_{index}", logical)
        for measurement_id, token in outcome_by_measurement.items():
            mapped = mapped.replace(f"{{{measurement_id}}}", token)
        if "{" in mapped or "}" in mapped:
            raise DirectCczCapabilityError(
                "exact correction map contains an unresolved placeholder"
            )
        corrections.append(mapped)
    evidence = min(
        (
            *(measurement.evidence_status for measurement in ppms),
            capability.injection.correction.evidence_status,
        ),
        key=lambda status: _evidence_rank(status),
    )
    return DirectCczInjectionEvent(
        event_id=event_id,
        source_gate_id=gate.gate_id,
        source_algorithmic_layer=gate.algorithmic_layer,
        data=data,
        resource=typed_resource,
        basis_changes_before=(f"H({data[2]})",),
        ppms=ppms,
        correction_frame=tuple(corrections),
        basis_changes_after=(f"H({data[2]})",),
        reaction_dependencies=tuple(ppm.outcome_token for ppm in ppms),
        resource_consumed=capability.injection.resource_consumed,
        evidence_status=evidence,
    )


def _evidence_rank(status: EvidenceStatus) -> int:
    order = {
        EvidenceStatus.PROVED: 8,
        EvidenceStatus.NUMERICAL: 7,
        EvidenceStatus.LITERATURE: 6,
        EvidenceStatus.CHECK: 5,
        EvidenceStatus.CONJECTURE: 4,
        EvidenceStatus.OPEN: 3,
        EvidenceStatus.INCONCLUSIVE: 2,
        EvidenceStatus.FALSIFIED: 1,
    }
    return order[status]


def lower_oop_qcla_to_direct_ccz_events(
    trace: OopQclaTrace,
    capability: DirectCczCapability,
) -> DirectCczEventTrace:
    """Emit direct-CCZ events and retain CNOTs as unscheduled Cliffords."""

    _require_event_capability(capability)
    toffolis = tuple(gate for gate in trace.gates if gate.kind is QclaGateKind.TOFFOLI)
    cliffords = tuple(gate.gate_id for gate in trace.gates if gate.kind is QclaGateKind.CNOT)
    events = tuple(
        lower_oop_toffoli_to_direct_ccz_event(
            gate,
            capability,
            ordinal=ordinal,
        )
        for ordinal, gate in enumerate(toffolis)
    )
    return DirectCczEventTrace(
        trace_id=f"{trace.trace_id}:direct-ccz-events-v2",
        source_trace_id=trace.trace_id,
        source_trace_schema_version=trace.schema_version,
        capability_id=capability.capability_id,
        injection_events=events,
        passthrough_clifford_gate_ids=cliffords,
        source_dependencies=tuple(
            DirectCczSourceDependency(
                predecessor_source_gate_id=dependency.predecessor,
                successor_source_gate_id=dependency.successor,
                logical_values=dependency.values,
                reason=dependency.reason,
            )
            for dependency in trace.dependencies
        ),
    )


def direct_ccz_event_trace_to_data(trace: DirectCczEventTrace) -> dict[str, Any]:
    """Return a deterministic JSON-compatible direct-CCZ event trace."""

    return {
        "capability_id": trace.capability_id,
        "complete_native_schedule": trace.complete_native_schedule,
        "injection_events": [
            {
                "basis_changes_after": list(event.basis_changes_after),
                "basis_changes_before": list(event.basis_changes_before),
                "correction_frame": list(event.correction_frame),
                "data": list(event.data),
                "event_id": event.event_id,
                "evidence_status": event.evidence_status.value,
                "ppms": [
                    {
                        "event_id": ppm.event_id,
                        "evidence_status": ppm.evidence_status.value,
                        "layer": ppm.layer,
                        "logical_support": list(ppm.logical_support),
                        "outcome_token": ppm.outcome_token,
                        "pauli_terms": list(ppm.pauli_terms),
                    }
                    for ppm in event.ppms
                ],
                "reaction_dependencies": list(event.reaction_dependencies),
                "resource": list(event.resource),
                "resource_consumed": event.resource_consumed,
                "source_algorithmic_layer": event.source_algorithmic_layer,
                "source_gate_id": event.source_gate_id,
            }
            for event in trace.injection_events
        ],
        "passthrough_clifford_gate_ids": list(trace.passthrough_clifford_gate_ids),
        "schema": trace.schema,
        "schema_version": trace.schema_version,
        "source_trace_id": trace.source_trace_id,
        "source_trace_schema_version": trace.source_trace_schema_version,
        "source_dependencies": [
            {
                "logical_values": list(dependency.logical_values),
                "predecessor_source_gate_id": (
                    dependency.predecessor_source_gate_id
                ),
                "reason": dependency.reason,
                "successor_source_gate_id": dependency.successor_source_gate_id,
            }
            for dependency in trace.source_dependencies
        ],
        "trace_id": trace.trace_id,
    }


def dumps_direct_ccz_event_trace(trace: DirectCczEventTrace) -> str:
    """Serialize an admitted event trace canonically."""

    return json.dumps(
        direct_ccz_event_trace_to_data(trace),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
