"""Source-qualified, fail-closed direct-CCZ capability records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.metadata import EvidenceStatus

DIRECT_CCZ_CAPABILITY_SCHEMA = "ecdlp-ftqc/direct-ccz-high-rate-capability"
DIRECT_CCZ_CAPABILITY_SCHEMA_VERSION = 1
DIRECT_CCZ_OUTCOME_BIT_CONVENTION = (
    "0 denotes +1 eigenvalue; 1 denotes -1 eigenvalue"
)
DIRECT_CCZ_FIGURE14_CORRECTION_MAP = (
    "CZ(data_1,data_2)^{zz_0}",
    "CZ(data_0,data_2)^{zz_1}",
    "CZ(data_0,data_1)^{zz_2}",
    "Z(data_0)^({x_0} XOR ({zz_1} AND {zz_2}))",
    "Z(data_1)^({x_1} XOR ({zz_0} AND {zz_2}))",
    "X(data_2)^({x_2} XOR ({zz_0} AND {zz_1}))",
)


class DirectCczCapabilityError(ValueError):
    """Raised when a capability record is malformed or not admitted."""


@dataclass(frozen=True, slots=True)
class DirectCczSourcePin:
    """One exact local primary-source pin used by the capability record."""

    source_id: str
    local_pdf: str
    pdf_sha256: str
    pages: tuple[int, ...]
    establishes: tuple[str, ...]
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.source_id or not self.local_pdf or not self.establishes:
            raise DirectCczCapabilityError("source pin fields cannot be empty")
        if len(self.pdf_sha256) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in self.pdf_sha256
        ):
            raise DirectCczCapabilityError("source pin requires a SHA-256 digest")
        if not self.pages or any(page < 1 for page in self.pages):
            raise DirectCczCapabilityError("source pages must be positive")


@dataclass(frozen=True, slots=True)
class DirectCczPpmSpec:
    """One Pauli-product measurement in a resource-state injection."""

    measurement_id: str
    layer: int
    pauli_terms: tuple[str, ...]
    operand_roles: tuple[str, ...]
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.measurement_id or self.layer < 1:
            raise DirectCczCapabilityError("PPM requires an ID and positive layer")
        if not self.pauli_terms or len(self.pauli_terms) != len(self.operand_roles):
            raise DirectCczCapabilityError("PPM Pauli terms must align with operand roles")
        if any(term not in {"X", "Y", "Z"} for term in self.pauli_terms):
            raise DirectCczCapabilityError("PPM terms must be X, Y, or Z")
        if len(self.operand_roles) != len(set(self.operand_roles)):
            raise DirectCczCapabilityError("PPM operand roles must be unique")
        allowed = {
            *(f"data_{index}" for index in range(3)),
            *(f"resource_{index}" for index in range(3)),
        }
        if not set(self.operand_roles) <= allowed:
            raise DirectCczCapabilityError("PPM contains an unknown operand role")


@dataclass(frozen=True, slots=True)
class DirectCczCorrectionSpec:
    """Correction family and optional exact outcome-to-correction map."""

    family: str
    exact_boolean_map: tuple[str, ...] | None
    outcome_bit_convention: str | None
    source_reference: str | None
    verification_reference: str | None
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.family:
            raise DirectCczCapabilityError("correction family cannot be empty")
        if self.exact_boolean_map is not None and (
            not self.exact_boolean_map or any(not item for item in self.exact_boolean_map)
        ):
            raise DirectCczCapabilityError("exact correction map cannot contain blanks")


@dataclass(frozen=True, slots=True)
class DirectCczInjectionSpec:
    """Architecture-independent resource-state injection semantics."""

    resource_state: str
    data_qubits: int
    resource_qubits: int
    measurements: tuple[DirectCczPpmSpec, ...]
    correction: DirectCczCorrectionSpec
    resource_consumed: bool
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if self.resource_state != "CCZ" or self.data_qubits != 3 or self.resource_qubits != 3:
            raise DirectCczCapabilityError("this schema admits only three-data-qubit CCZ injection")
        measurement_ids = tuple(item.measurement_id for item in self.measurements)
        if len(measurement_ids) != len(set(measurement_ids)):
            raise DirectCczCapabilityError("measurement IDs must be unique")
        if not self.resource_consumed:
            raise DirectCczCapabilityError("direct CCZ injection must consume its resource state")


@dataclass(frozen=True, slots=True)
class DirectCczFactoryEvidence:
    """Finite factory observation, separate from delivery and schedule admission."""

    resource_state: str
    batch_size: int | None
    production_cycles: int | None
    output_error_probability: float | None
    delivery_latency_cycles: int | None
    buffer_capacity: int | None
    storage_error_per_cycle: float | None
    evidence_status: EvidenceStatus
    source_note: str

    def __post_init__(self) -> None:
        if self.resource_state != "CCZ" or not self.source_note:
            raise DirectCczCapabilityError("factory resource and source note are required")
        for name, value in (
            ("batch_size", self.batch_size),
            ("production_cycles", self.production_cycles),
            ("delivery_latency_cycles", self.delivery_latency_cycles),
            ("buffer_capacity", self.buffer_capacity),
        ):
            if value is not None and value < 0:
                raise DirectCczCapabilityError(f"factory {name} cannot be negative")
        for probability in (self.output_error_probability, self.storage_error_per_cycle):
            if probability is not None and not 0.0 <= probability <= 1.0:
                raise DirectCczCapabilityError("factory probabilities must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class DirectCczHighRateSpec:
    """Fields required to turn injection events into a finite high-rate schedule."""

    admitted_batch_sizes: tuple[int, ...]
    admitted_parallel_ppm_layers: int | None
    admitted_duration_rounds: int | None
    logical_error_per_batch: float | None
    decoder_measurements_per_second: float | None
    classical_reaction_latency_seconds: float | None
    injection_port_capacity: int | None
    processor_logical_capacity: int | None
    routing_model: str | None
    assumed_parallel_ppm_layers: int | None
    assumed_duration_surgery_cycles: int | None
    evidence_status: EvidenceStatus
    source_note: str

    def __post_init__(self) -> None:
        if any(batch_size < 1 for batch_size in self.admitted_batch_sizes):
            raise DirectCczCapabilityError("batch sizes must be positive")
        optional_nonnegative = (
            self.admitted_parallel_ppm_layers,
            self.admitted_duration_rounds,
            self.classical_reaction_latency_seconds,
            self.injection_port_capacity,
            self.processor_logical_capacity,
            self.assumed_parallel_ppm_layers,
            self.assumed_duration_surgery_cycles,
        )
        if any(value is not None and value < 0 for value in optional_nonnegative):
            raise DirectCczCapabilityError("high-rate numeric fields cannot be negative")
        if (
            self.decoder_measurements_per_second is not None
            and self.decoder_measurements_per_second < 0
        ):
            raise DirectCczCapabilityError("decoder throughput cannot be negative")
        if self.logical_error_per_batch is not None and not 0 <= self.logical_error_per_batch <= 1:
            raise DirectCczCapabilityError("logical error must be in [0, 1]")
        if not self.source_note:
            raise DirectCczCapabilityError("high-rate source note cannot be empty")


@dataclass(frozen=True, slots=True)
class DirectCczCapability:
    """Complete evidence record with derived fail-closed admission decisions."""

    capability_id: str
    sources: tuple[DirectCczSourcePin, ...]
    injection: DirectCczInjectionSpec
    factory: DirectCczFactoryEvidence
    high_rate: DirectCczHighRateSpec
    recorded_event_lowering_admitted: bool
    recorded_high_rate_schedule_admitted: bool
    schema: str = DIRECT_CCZ_CAPABILITY_SCHEMA
    schema_version: int = DIRECT_CCZ_CAPABILITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.capability_id or not self.sources:
            raise DirectCczCapabilityError("capability ID and sources are required")
        if self.schema != DIRECT_CCZ_CAPABILITY_SCHEMA:
            raise DirectCczCapabilityError("unsupported direct-CCZ capability schema")
        if self.schema_version != DIRECT_CCZ_CAPABILITY_SCHEMA_VERSION:
            raise DirectCczCapabilityError("unsupported direct-CCZ capability schema version")
        source_ids = tuple(source.source_id for source in self.sources)
        if len(source_ids) != len(set(source_ids)):
            raise DirectCczCapabilityError("source IDs must be unique")
        if self.recorded_event_lowering_admitted != self.event_lowering_admitted:
            raise DirectCczCapabilityError("recorded event admission disagrees with required fields")
        if self.recorded_high_rate_schedule_admitted != self.high_rate_schedule_admitted:
            raise DirectCczCapabilityError("recorded high-rate admission disagrees with required fields")

    @property
    def missing_for_event_lowering(self) -> tuple[str, ...]:
        missing: list[str] = []
        measurement_roles = {
            (measurement.layer, measurement.pauli_terms, measurement.operand_roles)
            for measurement in self.injection.measurements
        }
        expected = {
            *(
                (1, ("Z", "Z"), (f"resource_{index}", f"data_{index}"))
                for index in range(3)
            ),
            *((2, ("X",), (f"resource_{index}",)) for index in range(3)),
        }
        if measurement_roles != expected:
            missing.append("injection.measurements.exact_six_ppm_sequence")
        exact_map = self.injection.correction.exact_boolean_map
        if exact_map is None:
            missing.append("injection.correction.exact_boolean_map")
        else:
            if exact_map != DIRECT_CCZ_FIGURE14_CORRECTION_MAP:
                missing.append("injection.correction.figure14_boolean_map")
            if (
                self.injection.correction.outcome_bit_convention
                != DIRECT_CCZ_OUTCOME_BIT_CONVENTION
            ):
                missing.append("injection.correction.outcome_bit_convention")
            if self.injection.correction.source_reference is None:
                missing.append("injection.correction.source_reference")
            if self.injection.correction.verification_reference is None:
                missing.append("injection.correction.verification_reference")
        if self.injection.correction.evidence_status in {
            EvidenceStatus.OPEN,
            EvidenceStatus.CHECK,
            EvidenceStatus.CONJECTURE,
            EvidenceStatus.INCONCLUSIVE,
        }:
            missing.append("injection.correction.admissible_evidence")
        return tuple(missing)

    @property
    def event_lowering_admitted(self) -> bool:
        return not self.missing_for_event_lowering

    @property
    def missing_for_high_rate_schedule(self) -> tuple[str, ...]:
        missing = list(self.missing_for_event_lowering)
        required = (
            ("high_rate.admitted_batch_sizes", bool(self.high_rate.admitted_batch_sizes)),
            (
                "high_rate.admitted_parallel_ppm_layers",
                self.high_rate.admitted_parallel_ppm_layers is not None,
            ),
            ("high_rate.admitted_duration_rounds", self.high_rate.admitted_duration_rounds is not None),
            ("high_rate.logical_error_per_batch", self.high_rate.logical_error_per_batch is not None),
            (
                "high_rate.decoder_measurements_per_second",
                self.high_rate.decoder_measurements_per_second is not None,
            ),
            (
                "high_rate.classical_reaction_latency_seconds",
                self.high_rate.classical_reaction_latency_seconds is not None,
            ),
            ("high_rate.injection_port_capacity", self.high_rate.injection_port_capacity is not None),
            (
                "high_rate.processor_logical_capacity",
                self.high_rate.processor_logical_capacity is not None,
            ),
            ("high_rate.routing_model", self.high_rate.routing_model is not None),
            ("factory.delivery_latency_cycles", self.factory.delivery_latency_cycles is not None),
            ("factory.buffer_capacity", self.factory.buffer_capacity is not None),
            ("factory.storage_error_per_cycle", self.factory.storage_error_per_cycle is not None),
        )
        missing.extend(name for name, present in required if not present)
        if self.high_rate.evidence_status in {
            EvidenceStatus.OPEN,
            EvidenceStatus.CHECK,
            EvidenceStatus.CONJECTURE,
            EvidenceStatus.INCONCLUSIVE,
        }:
            missing.append("high_rate.admissible_evidence")
        return tuple(missing)

    @property
    def high_rate_schedule_admitted(self) -> bool:
        return not self.missing_for_high_rate_schedule

    def with_exact_correction_map(
        self,
        exact_boolean_map: tuple[str, ...],
        *,
        evidence_status: EvidenceStatus,
    ) -> DirectCczCapability:
        """Return a test/research variant with an explicit correction map."""

        correction = replace(
            self.injection.correction,
            exact_boolean_map=exact_boolean_map,
            outcome_bit_convention=DIRECT_CCZ_OUTCOME_BIT_CONVENTION,
            source_reference="synthetic test fixture",
            verification_reference="synthetic test fixture",
            evidence_status=evidence_status,
        )
        provisional = replace(
            self,
            injection=replace(self.injection, correction=correction),
            recorded_event_lowering_admitted=True,
        )
        return provisional


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise DirectCczCapabilityError(f"{path} must be a string-keyed mapping")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DirectCczCapabilityError(f"{path} must be a sequence")
    return value


def _required(obj: Mapping[str, object], key: str, path: str) -> object:
    if key not in obj:
        raise DirectCczCapabilityError(f"{path} is missing {key!r}")
    return obj[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczCapabilityError(f"{path} must be a nonempty string")
    return value


def _optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _integer(value: object, path: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DirectCczCapabilityError(f"{path} must be an integer at least {minimum}")
    return value


def _optional_integer(value: object, path: str, minimum: int = 0) -> int | None:
    if value is None:
        return None
    return _integer(value, path, minimum)


def _number(value: object, path: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DirectCczCapabilityError(f"{path} must be numeric")
    result = float(value)
    if result < minimum:
        raise DirectCczCapabilityError(f"{path} must be at least {minimum}")
    return result


def _optional_number(value: object, path: str, minimum: float = 0.0) -> float | None:
    if value is None:
        return None
    return _number(value, path, minimum)


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DirectCczCapabilityError(f"{path} must be Boolean")
    return value


def _string_tuple(value: object, path: str) -> tuple[str, ...]:
    return tuple(
        _string(item, f"{path}[{index}]")
        for index, item in enumerate(_sequence(value, path))
    )


def _optional_string_tuple(value: object, path: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    return _string_tuple(value, path)


def _integer_tuple(value: object, path: str) -> tuple[int, ...]:
    return tuple(
        _integer(item, f"{path}[{index}]", 1)
        for index, item in enumerate(_sequence(value, path))
    )


def load_direct_ccz_capability(path: Path) -> DirectCczCapability:
    """Load and strictly validate a direct-CCZ capability YAML record."""

    try:
        loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DirectCczCapabilityError(f"cannot load capability {path}: {exc}") from exc
    root = _mapping(loaded, "$")
    injection = _mapping(_required(root, "injection", "$"), "$.injection")
    correction = _mapping(
        _required(injection, "correction", "$.injection"),
        "$.injection.correction",
    )
    factory = _mapping(_required(root, "factory", "$"), "$.factory")
    high_rate = _mapping(_required(root, "high_rate", "$"), "$.high_rate")
    admission = _mapping(_required(root, "admission", "$"), "$.admission")

    sources = tuple(
        DirectCczSourcePin(
            source_id=_string(_required(item, "source_id", item_path), f"{item_path}.source_id"),
            local_pdf=_string(_required(item, "local_pdf", item_path), f"{item_path}.local_pdf"),
            pdf_sha256=_string(
                _required(item, "pdf_sha256", item_path), f"{item_path}.pdf_sha256"
            ),
            pages=_integer_tuple(_required(item, "pages", item_path), f"{item_path}.pages"),
            establishes=_string_tuple(
                _required(item, "establishes", item_path), f"{item_path}.establishes"
            ),
            evidence_status=EvidenceStatus(
                _string(
                    _required(item, "evidence_status", item_path),
                    f"{item_path}.evidence_status",
                )
            ),
        )
        for index, raw in enumerate(_sequence(_required(root, "sources", "$"), "$.sources"))
        for item_path in (f"$.sources[{index}]",)
        for item in (_mapping(raw, item_path),)
    )
    measurements = tuple(
        DirectCczPpmSpec(
            measurement_id=_string(
                _required(item, "measurement_id", item_path), f"{item_path}.measurement_id"
            ),
            layer=_integer(_required(item, "layer", item_path), f"{item_path}.layer", 1),
            pauli_terms=_string_tuple(
                _required(item, "pauli_terms", item_path), f"{item_path}.pauli_terms"
            ),
            operand_roles=_string_tuple(
                _required(item, "operand_roles", item_path), f"{item_path}.operand_roles"
            ),
            evidence_status=EvidenceStatus(
                _string(
                    _required(item, "evidence_status", item_path),
                    f"{item_path}.evidence_status",
                )
            ),
        )
        for index, raw in enumerate(
            _sequence(_required(injection, "measurements", "$.injection"), "$.injection.measurements")
        )
        for item_path in (f"$.injection.measurements[{index}]",)
        for item in (_mapping(raw, item_path),)
    )

    capability = DirectCczCapability(
        capability_id=_string(_required(root, "capability_id", "$"), "$.capability_id"),
        sources=sources,
        injection=DirectCczInjectionSpec(
            resource_state=_string(
                _required(injection, "resource_state", "$.injection"),
                "$.injection.resource_state",
            ),
            data_qubits=_integer(
                _required(injection, "data_qubits", "$.injection"),
                "$.injection.data_qubits",
                1,
            ),
            resource_qubits=_integer(
                _required(injection, "resource_qubits", "$.injection"),
                "$.injection.resource_qubits",
                1,
            ),
            measurements=measurements,
            correction=DirectCczCorrectionSpec(
                family=_string(
                    _required(correction, "family", "$.injection.correction"),
                    "$.injection.correction.family",
                ),
                exact_boolean_map=_optional_string_tuple(
                    _required(correction, "exact_boolean_map", "$.injection.correction"),
                    "$.injection.correction.exact_boolean_map",
                ),
                outcome_bit_convention=_optional_string(
                    correction.get("outcome_bit_convention"),
                    "$.injection.correction.outcome_bit_convention",
                ),
                source_reference=_optional_string(
                    correction.get("source_reference"),
                    "$.injection.correction.source_reference",
                ),
                verification_reference=_optional_string(
                    correction.get("verification_reference"),
                    "$.injection.correction.verification_reference",
                ),
                evidence_status=EvidenceStatus(
                    _string(
                        _required(correction, "evidence_status", "$.injection.correction"),
                        "$.injection.correction.evidence_status",
                    )
                ),
            ),
            resource_consumed=_boolean(
                _required(injection, "resource_consumed", "$.injection"),
                "$.injection.resource_consumed",
            ),
            evidence_status=EvidenceStatus(
                _string(
                    _required(injection, "evidence_status", "$.injection"),
                    "$.injection.evidence_status",
                )
            ),
        ),
        factory=DirectCczFactoryEvidence(
            resource_state=_string(
                _required(factory, "resource_state", "$.factory"), "$.factory.resource_state"
            ),
            batch_size=_optional_integer(
                _required(factory, "batch_size", "$.factory"), "$.factory.batch_size", 1
            ),
            production_cycles=_optional_integer(
                _required(factory, "production_cycles", "$.factory"),
                "$.factory.production_cycles",
                1,
            ),
            output_error_probability=_optional_number(
                _required(factory, "output_error_probability", "$.factory"),
                "$.factory.output_error_probability",
            ),
            delivery_latency_cycles=_optional_integer(
                _required(factory, "delivery_latency_cycles", "$.factory"),
                "$.factory.delivery_latency_cycles",
            ),
            buffer_capacity=_optional_integer(
                _required(factory, "buffer_capacity", "$.factory"),
                "$.factory.buffer_capacity",
            ),
            storage_error_per_cycle=_optional_number(
                _required(factory, "storage_error_per_cycle", "$.factory"),
                "$.factory.storage_error_per_cycle",
            ),
            evidence_status=EvidenceStatus(
                _string(
                    _required(factory, "evidence_status", "$.factory"),
                    "$.factory.evidence_status",
                )
            ),
            source_note=_string(
                _required(factory, "source_note", "$.factory"), "$.factory.source_note"
            ),
        ),
        high_rate=DirectCczHighRateSpec(
            admitted_batch_sizes=_integer_tuple(
                _required(high_rate, "admitted_batch_sizes", "$.high_rate"),
                "$.high_rate.admitted_batch_sizes",
            ),
            admitted_parallel_ppm_layers=_optional_integer(
                _required(high_rate, "admitted_parallel_ppm_layers", "$.high_rate"),
                "$.high_rate.admitted_parallel_ppm_layers",
                1,
            ),
            admitted_duration_rounds=_optional_integer(
                _required(high_rate, "admitted_duration_rounds", "$.high_rate"),
                "$.high_rate.admitted_duration_rounds",
                1,
            ),
            logical_error_per_batch=_optional_number(
                _required(high_rate, "logical_error_per_batch", "$.high_rate"),
                "$.high_rate.logical_error_per_batch",
            ),
            decoder_measurements_per_second=_optional_number(
                _required(high_rate, "decoder_measurements_per_second", "$.high_rate"),
                "$.high_rate.decoder_measurements_per_second",
            ),
            classical_reaction_latency_seconds=_optional_number(
                _required(high_rate, "classical_reaction_latency_seconds", "$.high_rate"),
                "$.high_rate.classical_reaction_latency_seconds",
            ),
            injection_port_capacity=_optional_integer(
                _required(high_rate, "injection_port_capacity", "$.high_rate"),
                "$.high_rate.injection_port_capacity",
                1,
            ),
            processor_logical_capacity=_optional_integer(
                _required(high_rate, "processor_logical_capacity", "$.high_rate"),
                "$.high_rate.processor_logical_capacity",
                1,
            ),
            routing_model=_optional_string(
                _required(high_rate, "routing_model", "$.high_rate"),
                "$.high_rate.routing_model",
            ),
            assumed_parallel_ppm_layers=_optional_integer(
                _required(high_rate, "assumed_parallel_ppm_layers", "$.high_rate"),
                "$.high_rate.assumed_parallel_ppm_layers",
                1,
            ),
            assumed_duration_surgery_cycles=_optional_integer(
                _required(high_rate, "assumed_duration_surgery_cycles", "$.high_rate"),
                "$.high_rate.assumed_duration_surgery_cycles",
                1,
            ),
            evidence_status=EvidenceStatus(
                _string(
                    _required(high_rate, "evidence_status", "$.high_rate"),
                    "$.high_rate.evidence_status",
                )
            ),
            source_note=_string(
                _required(high_rate, "source_note", "$.high_rate"),
                "$.high_rate.source_note",
            ),
        ),
        recorded_event_lowering_admitted=_boolean(
            _required(admission, "event_lowering_admitted", "$.admission"),
            "$.admission.event_lowering_admitted",
        ),
        recorded_high_rate_schedule_admitted=_boolean(
            _required(admission, "high_rate_schedule_admitted", "$.admission"),
            "$.admission.high_rate_schedule_admitted",
        ),
        schema=_string(_required(root, "schema", "$"), "$.schema"),
        schema_version=_integer(_required(root, "schema_version", "$"), "$.schema_version", 1),
    )
    return capability


def direct_ccz_capability_to_data(capability: DirectCczCapability) -> dict[str, Any]:
    """Return a canonical JSON-compatible evidence and gap record."""

    return {
        "admission": {
            "event_lowering_admitted": capability.event_lowering_admitted,
            "high_rate_schedule_admitted": capability.high_rate_schedule_admitted,
            "missing_for_event_lowering": list(capability.missing_for_event_lowering),
            "missing_for_high_rate_schedule": list(capability.missing_for_high_rate_schedule),
        },
        "capability_id": capability.capability_id,
        "factory": {
            "batch_size": capability.factory.batch_size,
            "buffer_capacity": capability.factory.buffer_capacity,
            "delivery_latency_cycles": capability.factory.delivery_latency_cycles,
            "evidence_status": capability.factory.evidence_status.value,
            "output_error_probability": capability.factory.output_error_probability,
            "production_cycles": capability.factory.production_cycles,
            "resource_state": capability.factory.resource_state,
            "source_note": capability.factory.source_note,
            "storage_error_per_cycle": capability.factory.storage_error_per_cycle,
        },
        "high_rate": {
            "admitted_batch_sizes": list(capability.high_rate.admitted_batch_sizes),
            "admitted_duration_rounds": capability.high_rate.admitted_duration_rounds,
            "admitted_parallel_ppm_layers": capability.high_rate.admitted_parallel_ppm_layers,
            "assumed_duration_surgery_cycles": capability.high_rate.assumed_duration_surgery_cycles,
            "assumed_parallel_ppm_layers": capability.high_rate.assumed_parallel_ppm_layers,
            "classical_reaction_latency_seconds": capability.high_rate.classical_reaction_latency_seconds,
            "decoder_measurements_per_second": capability.high_rate.decoder_measurements_per_second,
            "evidence_status": capability.high_rate.evidence_status.value,
            "injection_port_capacity": capability.high_rate.injection_port_capacity,
            "logical_error_per_batch": capability.high_rate.logical_error_per_batch,
            "processor_logical_capacity": capability.high_rate.processor_logical_capacity,
            "routing_model": capability.high_rate.routing_model,
            "source_note": capability.high_rate.source_note,
        },
        "injection": {
            "correction": {
                "evidence_status": capability.injection.correction.evidence_status.value,
                "exact_boolean_map": (
                    list(capability.injection.correction.exact_boolean_map)
                    if capability.injection.correction.exact_boolean_map is not None
                    else None
                ),
                "family": capability.injection.correction.family,
                "outcome_bit_convention": (
                    capability.injection.correction.outcome_bit_convention
                ),
                "source_reference": capability.injection.correction.source_reference,
                "verification_reference": (
                    capability.injection.correction.verification_reference
                ),
            },
            "data_qubits": capability.injection.data_qubits,
            "evidence_status": capability.injection.evidence_status.value,
            "measurements": [
                {
                    "evidence_status": measurement.evidence_status.value,
                    "layer": measurement.layer,
                    "measurement_id": measurement.measurement_id,
                    "operand_roles": list(measurement.operand_roles),
                    "pauli_terms": list(measurement.pauli_terms),
                }
                for measurement in capability.injection.measurements
            ],
            "resource_consumed": capability.injection.resource_consumed,
            "resource_qubits": capability.injection.resource_qubits,
            "resource_state": capability.injection.resource_state,
        },
        "schema": capability.schema,
        "schema_version": capability.schema_version,
        "sources": [
            {
                "establishes": list(source.establishes),
                "evidence_status": source.evidence_status.value,
                "local_pdf": source.local_pdf,
                "pages": list(source.pages),
                "pdf_sha256": source.pdf_sha256,
                "source_id": source.source_id,
            }
            for source in capability.sources
        ],
    }
