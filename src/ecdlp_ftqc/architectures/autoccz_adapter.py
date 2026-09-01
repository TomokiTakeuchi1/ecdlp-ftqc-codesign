"""Fail-closed qualification of one AutoCCZ surface-code service domain."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.metadata import EvidenceStatus

AUTOCCZ_ADAPTER_SCHEMA = "ecdlp-ftqc/autoccz-surface-code-adapter"
AUTOCCZ_ADAPTER_SCHEMA_VERSION = 1

REQUIRED_AUTOCCZ_SERVICE_FIELDS = (
    "consumer.event_semantics",
    "consumer.resource_type",
    "consumer.consumption_interval_cycles",
    "consumer.logical_error_per_event",
    "controller.decoder_throughput",
    "controller.reaction_latency_seconds",
    "processor.injection_port_capacity",
    "processor.logical_capacity",
    "processor.routing_model",
    "factory.batch_size",
    "factory.production_cycles",
    "factory.output_error_probability",
    "factory.delivery_latency_cycles",
    "factory.buffer_capacity",
    "factory.storage_error_per_cycle",
    "compatibility.factory_to_consumer_adapter",
    "compatibility.same_domain_failure_budget",
)

_ADMISSIBLE_EVIDENCE = frozenset(
    {EvidenceStatus.PROVED, EvidenceStatus.NUMERICAL, EvidenceStatus.LITERATURE}
)


class AutoCczAdapterError(ValueError):
    """Raised when the AutoCCZ service record is malformed or forged."""


@dataclass(frozen=True, slots=True)
class AutoCczServiceSource:
    """One version-pinned primary PDF."""

    source_id: str
    local_pdf: str
    pdf_sha256: str
    pages: tuple[int, ...]
    establishes: tuple[str, ...]
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.source_id or not self.local_pdf or not self.establishes:
            raise AutoCczAdapterError("source fields cannot be empty")
        _validate_sha256(self.pdf_sha256, "source PDF")
        if not self.pages or any(page < 1 for page in self.pages):
            raise AutoCczAdapterError("source pages must be positive")


@dataclass(frozen=True, slots=True)
class AutoCczServiceAsset:
    """One official non-PDF source artifact."""

    asset_id: str
    source_id: str
    local_path: str
    sha256: str
    media_type: str
    role: str

    def __post_init__(self) -> None:
        if any(
            not value
            for value in (
                self.asset_id,
                self.source_id,
                self.local_path,
                self.media_type,
                self.role,
            )
        ):
            raise AutoCczAdapterError("source asset fields cannot be empty")
        _validate_sha256(self.sha256, "source asset")


@dataclass(frozen=True, slots=True)
class AutoCczServiceFieldEvidence:
    """One required service field and its compatibility scope."""

    field_id: str
    reported_value: str | None
    admitted_value: str | None
    unit: str | None
    evidence_status: EvidenceStatus
    source_ids: tuple[str, ...]
    compatibility_domain: str
    note: str

    def __post_init__(self) -> None:
        if self.field_id not in REQUIRED_AUTOCCZ_SERVICE_FIELDS:
            raise AutoCczAdapterError(f"unknown AutoCCZ service field: {self.field_id}")
        if not self.compatibility_domain or not self.note:
            raise AutoCczAdapterError("field compatibility domain and note are required")
        if self.admitted_value is not None:
            if self.reported_value is None:
                raise AutoCczAdapterError("an admitted value requires a reported value")
            if self.evidence_status not in _ADMISSIBLE_EVIDENCE:
                raise AutoCczAdapterError("an admitted value requires admissible evidence")
            if not self.source_ids:
                raise AutoCczAdapterError("an admitted value requires a pinned source")


@dataclass(frozen=True, slots=True)
class AutoCczServiceModel:
    """Finite source example used only for deterministic arithmetic checks."""

    compatibility_domain: str
    physical_gate_error_probability: float
    surface_code_cycle_seconds: float
    reaction_latency_seconds: float
    level_1_distance: int
    level_2_distance: int
    level_1_factory_count: int
    level_1_states_per_ccz: int
    level_1_depth_coefficient: float
    level_2_depth_coefficient: float

    def __post_init__(self) -> None:
        if not self.compatibility_domain:
            raise AutoCczAdapterError("service model requires a compatibility domain")
        if not 0 < self.physical_gate_error_probability < 1:
            raise AutoCczAdapterError("physical gate error probability must lie in (0, 1)")
        positive_floats = (
            self.surface_code_cycle_seconds,
            self.reaction_latency_seconds,
            self.level_1_depth_coefficient,
            self.level_2_depth_coefficient,
        )
        if any(value <= 0 or not math.isfinite(value) for value in positive_floats):
            raise AutoCczAdapterError("service model durations must be finite and positive")
        positive_ints = (
            self.level_1_distance,
            self.level_2_distance,
            self.level_1_factory_count,
            self.level_1_states_per_ccz,
        )
        if any(value <= 0 for value in positive_ints):
            raise AutoCczAdapterError("service model counts and distances must be positive")

    @property
    def level_1_effective_cycles_per_ccz(self) -> float:
        """Level-1 supply interval after accounting for eight inputs and six factories."""

        return (
            self.level_1_depth_coefficient
            * self.level_1_distance
            * self.level_1_states_per_ccz
            / self.level_1_factory_count
        )

    @property
    def level_2_cycles_per_ccz(self) -> float:
        """Level-2 CCZ output interval in surface-code cycles."""

        return self.level_2_depth_coefficient * self.level_2_distance

    @property
    def level_1_rate_hz(self) -> float:
        """Level-1-limited CCZ supply rate."""

        return 1.0 / (
            self.level_1_effective_cycles_per_ccz * self.surface_code_cycle_seconds
        )

    @property
    def level_2_rate_hz(self) -> float:
        """Level-2-limited CCZ supply rate."""

        return 1.0 / (self.level_2_cycles_per_ccz * self.surface_code_cycle_seconds)

    @property
    def bottleneck(self) -> str:
        """Factory level with the slower output rate."""

        return "level_1" if self.level_1_rate_hz < self.level_2_rate_hz else "level_2"

    @property
    def factory_rate_hz(self) -> float:
        """Per-factory source-model output rate."""

        return min(self.level_1_rate_hz, self.level_2_rate_hz)

    @property
    def reaction_demand_rate_hz(self) -> float:
        """One serial AutoCCZ consumption per assumed reaction interval."""

        return 1.0 / self.reaction_latency_seconds

    @property
    def factories_for_reaction_limited_demand(self) -> int:
        """Factories needed to meet the source-model average demand rate."""

        return math.ceil(self.reaction_demand_rate_hz / self.factory_rate_hz)


@dataclass(frozen=True, slots=True)
class AutoCczRecordedDerived:
    """Values copied into the record and recomputed by the loader."""

    level_1_effective_cycles_per_ccz: float
    level_2_cycles_per_ccz: float
    level_1_rate_hz: float
    level_2_rate_hz: float
    bottleneck: str
    reaction_demand_rate_hz: float
    factories_for_reaction_limited_demand: int


@dataclass(frozen=True, slots=True)
class AutoCczServiceCandidate:
    """Complete field matrix for one source-defined compatibility domain."""

    candidate_id: str
    compatibility_domain: str
    field_evidence: tuple[AutoCczServiceFieldEvidence, ...]
    evidence_status: EvidenceStatus
    conclusion: str

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.compatibility_domain or not self.conclusion:
            raise AutoCczAdapterError("candidate fields cannot be empty")
        field_ids = tuple(item.field_id for item in self.field_evidence)
        if len(field_ids) != len(set(field_ids)):
            raise AutoCczAdapterError("candidate field IDs must be unique")
        if field_ids != REQUIRED_AUTOCCZ_SERVICE_FIELDS:
            raise AutoCczAdapterError(
                "candidate must record every AutoCCZ service field in schema order"
            )

    @property
    def missing_fields(self) -> tuple[str, ...]:
        """Fields without an admitted finite value."""

        return tuple(
            item.field_id for item in self.field_evidence if item.admitted_value is None
        )

    @property
    def incompatible_fields(self) -> tuple[str, ...]:
        """Qualified values belonging to a different physical model."""

        return tuple(
            item.field_id
            for item in self.field_evidence
            if item.admitted_value is not None
            and item.compatibility_domain != self.compatibility_domain
        )

    @property
    def adapter_admitted(self) -> bool:
        """Whether the factory output is explicitly connected to the consumer."""

        field = next(
            item
            for item in self.field_evidence
            if item.field_id == "compatibility.factory_to_consumer_adapter"
        )
        return (
            field.admitted_value is not None
            and field.compatibility_domain == self.compatibility_domain
        )

    @property
    def service_admitted(self) -> bool:
        """Whether every required field closes in one compatibility domain."""

        return not self.missing_fields and not self.incompatible_fields


@dataclass(frozen=True, slots=True)
class AutoCczServiceAudit:
    """Complete AutoCCZ audit with fail-closed derived decisions."""

    audit_id: str
    task_id: str
    sources: tuple[AutoCczServiceSource, ...]
    source_assets: tuple[AutoCczServiceAsset, ...]
    model: AutoCczServiceModel
    recorded_derived: AutoCczRecordedDerived
    candidate: AutoCczServiceCandidate
    recorded_adapter_admitted: bool
    recorded_service_admitted: bool
    schema: str = AUTOCCZ_ADAPTER_SCHEMA
    schema_version: int = AUTOCCZ_ADAPTER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.audit_id or not self.task_id or not self.sources:
            raise AutoCczAdapterError("audit ID, task ID, and sources are required")
        if self.schema != AUTOCCZ_ADAPTER_SCHEMA:
            raise AutoCczAdapterError("unsupported AutoCCZ adapter schema")
        if self.schema_version != AUTOCCZ_ADAPTER_SCHEMA_VERSION:
            raise AutoCczAdapterError("unsupported AutoCCZ adapter schema version")
        if self.model.compatibility_domain != self.candidate.compatibility_domain:
            raise AutoCczAdapterError("model and candidate compatibility domains disagree")

        source_ids = tuple(source.source_id for source in self.sources)
        if len(source_ids) != len(set(source_ids)):
            raise AutoCczAdapterError("source IDs must be unique")
        asset_ids = tuple(asset.asset_id for asset in self.source_assets)
        if len(asset_ids) != len(set(asset_ids)):
            raise AutoCczAdapterError("source asset IDs must be unique")
        asset_paths = tuple(asset.local_path for asset in self.source_assets)
        if len(asset_paths) != len(set(asset_paths)):
            raise AutoCczAdapterError("source asset paths must be unique")

        known_sources = set(source_ids)
        referenced_sources = {
            source_id
            for field in self.candidate.field_evidence
            for source_id in field.source_ids
        } | {asset.source_id for asset in self.source_assets}
        unknown = referenced_sources - known_sources
        if unknown:
            raise AutoCczAdapterError(
                f"audit references unknown sources: {', '.join(sorted(unknown))}"
            )

        checks = (
            (
                self.recorded_derived.level_1_effective_cycles_per_ccz,
                self.model.level_1_effective_cycles_per_ccz,
                "level-1 effective cycles",
            ),
            (
                self.recorded_derived.level_2_cycles_per_ccz,
                self.model.level_2_cycles_per_ccz,
                "level-2 cycles",
            ),
            (
                self.recorded_derived.level_1_rate_hz,
                self.model.level_1_rate_hz,
                "level-1 rate",
            ),
            (
                self.recorded_derived.level_2_rate_hz,
                self.model.level_2_rate_hz,
                "level-2 rate",
            ),
            (
                self.recorded_derived.reaction_demand_rate_hz,
                self.model.reaction_demand_rate_hz,
                "reaction demand rate",
            ),
        )
        for recorded, derived, label in checks:
            if not math.isclose(recorded, derived, rel_tol=1e-12, abs_tol=1e-12):
                raise AutoCczAdapterError(f"recorded {label} disagrees with the model")
        if self.recorded_derived.bottleneck != self.model.bottleneck:
            raise AutoCczAdapterError("recorded factory bottleneck disagrees with the model")
        if (
            self.recorded_derived.factories_for_reaction_limited_demand
            != self.model.factories_for_reaction_limited_demand
        ):
            raise AutoCczAdapterError("recorded factory count disagrees with the model")
        if self.recorded_adapter_admitted != self.candidate.adapter_admitted:
            raise AutoCczAdapterError("recorded adapter admission disagrees with fields")
        if self.recorded_service_admitted != self.candidate.service_admitted:
            raise AutoCczAdapterError("recorded service admission disagrees with fields")


def _validate_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdefABCDEF" for character in value
    ):
        raise AutoCczAdapterError(f"{label} requires a SHA-256 digest")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise AutoCczAdapterError(f"{path} must be a string-keyed mapping")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AutoCczAdapterError(f"{path} must be a sequence")
    return value


def _required(obj: Mapping[str, object], key: str, path: str) -> object:
    if key not in obj:
        raise AutoCczAdapterError(f"{path} is missing {key!r}")
    return obj[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise AutoCczAdapterError(f"{path} must be a nonempty string")
    return value


def _optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _integer(value: object, path: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise AutoCczAdapterError(f"{path} must be an integer at least {minimum}")
    return value


def _number(value: object, path: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AutoCczAdapterError(f"{path} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= minimum:
        raise AutoCczAdapterError(f"{path} must be finite and greater than {minimum}")
    return result


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise AutoCczAdapterError(f"{path} must be Boolean")
    return value


def _string_tuple(value: object, path: str) -> tuple[str, ...]:
    return tuple(
        _string(item, f"{path}[{index}]")
        for index, item in enumerate(_sequence(value, path))
    )


def _load_source(raw: object, index: int) -> AutoCczServiceSource:
    path = f"$.sources[{index}]"
    item = _mapping(raw, path)
    return AutoCczServiceSource(
        source_id=_string(_required(item, "source_id", path), f"{path}.source_id"),
        local_pdf=_string(_required(item, "local_pdf", path), f"{path}.local_pdf"),
        pdf_sha256=_string(_required(item, "pdf_sha256", path), f"{path}.pdf_sha256"),
        pages=tuple(
            _integer(page, f"{path}.pages[{page_index}]")
            for page_index, page in enumerate(
                _sequence(_required(item, "pages", path), f"{path}.pages")
            )
        ),
        establishes=_string_tuple(
            _required(item, "establishes", path), f"{path}.establishes"
        ),
        evidence_status=EvidenceStatus(
            _string(_required(item, "evidence_status", path), f"{path}.evidence_status")
        ),
    )


def _load_asset(raw: object, index: int) -> AutoCczServiceAsset:
    path = f"$.source_assets[{index}]"
    item = _mapping(raw, path)
    return AutoCczServiceAsset(
        asset_id=_string(_required(item, "asset_id", path), f"{path}.asset_id"),
        source_id=_string(_required(item, "source_id", path), f"{path}.source_id"),
        local_path=_string(_required(item, "local_path", path), f"{path}.local_path"),
        sha256=_string(_required(item, "sha256", path), f"{path}.sha256"),
        media_type=_string(_required(item, "media_type", path), f"{path}.media_type"),
        role=_string(_required(item, "role", path), f"{path}.role"),
    )


def _load_field(raw: object, index: int) -> AutoCczServiceFieldEvidence:
    path = f"$.candidate.fields[{index}]"
    item = _mapping(raw, path)
    return AutoCczServiceFieldEvidence(
        field_id=_string(_required(item, "field_id", path), f"{path}.field_id"),
        reported_value=_optional_string(
            _required(item, "reported_value", path), f"{path}.reported_value"
        ),
        admitted_value=_optional_string(
            _required(item, "admitted_value", path), f"{path}.admitted_value"
        ),
        unit=_optional_string(_required(item, "unit", path), f"{path}.unit"),
        evidence_status=EvidenceStatus(
            _string(_required(item, "evidence_status", path), f"{path}.evidence_status")
        ),
        source_ids=_string_tuple(
            _required(item, "source_ids", path), f"{path}.source_ids"
        ),
        compatibility_domain=_string(
            _required(item, "compatibility_domain", path),
            f"{path}.compatibility_domain",
        ),
        note=_string(_required(item, "note", path), f"{path}.note"),
    )


def load_autoccz_service_audit(path: Path) -> AutoCczServiceAudit:
    """Load and strictly validate an AutoCCZ surface-code service audit."""

    try:
        loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AutoCczAdapterError(f"cannot load AutoCCZ audit {path}: {exc}") from exc
    root = _mapping(loaded, "$")
    required_fields = _string_tuple(
        _required(root, "required_fields", "$"), "$.required_fields"
    )
    if required_fields != REQUIRED_AUTOCCZ_SERVICE_FIELDS:
        raise AutoCczAdapterError("required field list disagrees with AutoCCZ schema")

    model_raw = _mapping(_required(root, "model", "$"), "$.model")
    model = AutoCczServiceModel(
        compatibility_domain=_string(
            _required(model_raw, "compatibility_domain", "$.model"),
            "$.model.compatibility_domain",
        ),
        physical_gate_error_probability=_number(
            _required(model_raw, "physical_gate_error_probability", "$.model"),
            "$.model.physical_gate_error_probability",
        ),
        surface_code_cycle_seconds=_number(
            _required(model_raw, "surface_code_cycle_seconds", "$.model"),
            "$.model.surface_code_cycle_seconds",
        ),
        reaction_latency_seconds=_number(
            _required(model_raw, "reaction_latency_seconds", "$.model"),
            "$.model.reaction_latency_seconds",
        ),
        level_1_distance=_integer(
            _required(model_raw, "level_1_distance", "$.model"),
            "$.model.level_1_distance",
        ),
        level_2_distance=_integer(
            _required(model_raw, "level_2_distance", "$.model"),
            "$.model.level_2_distance",
        ),
        level_1_factory_count=_integer(
            _required(model_raw, "level_1_factory_count", "$.model"),
            "$.model.level_1_factory_count",
        ),
        level_1_states_per_ccz=_integer(
            _required(model_raw, "level_1_states_per_ccz", "$.model"),
            "$.model.level_1_states_per_ccz",
        ),
        level_1_depth_coefficient=_number(
            _required(model_raw, "level_1_depth_coefficient", "$.model"),
            "$.model.level_1_depth_coefficient",
        ),
        level_2_depth_coefficient=_number(
            _required(model_raw, "level_2_depth_coefficient", "$.model"),
            "$.model.level_2_depth_coefficient",
        ),
    )

    derived_raw = _mapping(_required(root, "recorded_derived", "$"), "$.recorded_derived")
    recorded_derived = AutoCczRecordedDerived(
        level_1_effective_cycles_per_ccz=_number(
            _required(
                derived_raw, "level_1_effective_cycles_per_ccz", "$.recorded_derived"
            ),
            "$.recorded_derived.level_1_effective_cycles_per_ccz",
        ),
        level_2_cycles_per_ccz=_number(
            _required(derived_raw, "level_2_cycles_per_ccz", "$.recorded_derived"),
            "$.recorded_derived.level_2_cycles_per_ccz",
        ),
        level_1_rate_hz=_number(
            _required(derived_raw, "level_1_rate_hz", "$.recorded_derived"),
            "$.recorded_derived.level_1_rate_hz",
        ),
        level_2_rate_hz=_number(
            _required(derived_raw, "level_2_rate_hz", "$.recorded_derived"),
            "$.recorded_derived.level_2_rate_hz",
        ),
        bottleneck=_string(
            _required(derived_raw, "bottleneck", "$.recorded_derived"),
            "$.recorded_derived.bottleneck",
        ),
        reaction_demand_rate_hz=_number(
            _required(derived_raw, "reaction_demand_rate_hz", "$.recorded_derived"),
            "$.recorded_derived.reaction_demand_rate_hz",
        ),
        factories_for_reaction_limited_demand=_integer(
            _required(
                derived_raw,
                "factories_for_reaction_limited_demand",
                "$.recorded_derived",
            ),
            "$.recorded_derived.factories_for_reaction_limited_demand",
        ),
    )

    candidate_raw = _mapping(_required(root, "candidate", "$"), "$.candidate")
    candidate = AutoCczServiceCandidate(
        candidate_id=_string(
            _required(candidate_raw, "candidate_id", "$.candidate"),
            "$.candidate.candidate_id",
        ),
        compatibility_domain=_string(
            _required(candidate_raw, "compatibility_domain", "$.candidate"),
            "$.candidate.compatibility_domain",
        ),
        field_evidence=tuple(
            _load_field(raw, index)
            for index, raw in enumerate(
                _sequence(
                    _required(candidate_raw, "fields", "$.candidate"),
                    "$.candidate.fields",
                )
            )
        ),
        evidence_status=EvidenceStatus(
            _string(
                _required(candidate_raw, "evidence_status", "$.candidate"),
                "$.candidate.evidence_status",
            )
        ),
        conclusion=_string(
            _required(candidate_raw, "conclusion", "$.candidate"),
            "$.candidate.conclusion",
        ),
    )

    return AutoCczServiceAudit(
        audit_id=_string(_required(root, "audit_id", "$"), "$.audit_id"),
        task_id=_string(_required(root, "task_id", "$"), "$.task_id"),
        sources=tuple(
            _load_source(raw, index)
            for index, raw in enumerate(
                _sequence(_required(root, "sources", "$"), "$.sources")
            )
        ),
        source_assets=tuple(
            _load_asset(raw, index)
            for index, raw in enumerate(
                _sequence(_required(root, "source_assets", "$"), "$.source_assets")
            )
        ),
        model=model,
        recorded_derived=recorded_derived,
        candidate=candidate,
        recorded_adapter_admitted=_boolean(
            _required(root, "recorded_adapter_admitted", "$"),
            "$.recorded_adapter_admitted",
        ),
        recorded_service_admitted=_boolean(
            _required(root, "recorded_service_admitted", "$"),
            "$.recorded_service_admitted",
        ),
        schema=_string(_required(root, "schema", "$"), "$.schema"),
        schema_version=_integer(
            _required(root, "schema_version", "$"), "$.schema_version"
        ),
    )


def autoccz_service_audit_to_data(audit: AutoCczServiceAudit) -> dict[str, Any]:
    """Return a canonical JSON-compatible audit and derived service arithmetic."""

    candidate = audit.candidate
    model = audit.model
    return {
        "admission": {
            "adapter_admitted": candidate.adapter_admitted,
            "incompatible_fields": list(candidate.incompatible_fields),
            "missing_fields": list(candidate.missing_fields),
            "service_admitted": candidate.service_admitted,
        },
        "audit_id": audit.audit_id,
        "candidate": {
            "candidate_id": candidate.candidate_id,
            "compatibility_domain": candidate.compatibility_domain,
            "conclusion": candidate.conclusion,
            "evidence_status": candidate.evidence_status.value,
            "fields": [
                {
                    "admitted_value": item.admitted_value,
                    "compatibility_domain": item.compatibility_domain,
                    "evidence_status": item.evidence_status.value,
                    "field_id": item.field_id,
                    "note": item.note,
                    "reported_value": item.reported_value,
                    "source_ids": list(item.source_ids),
                    "unit": item.unit,
                }
                for item in candidate.field_evidence
            ],
        },
        "derived": {
            "bottleneck": model.bottleneck,
            "factories_for_reaction_limited_demand": (
                model.factories_for_reaction_limited_demand
            ),
            "factory_rate_hz": model.factory_rate_hz,
            "level_1_effective_cycles_per_ccz": (
                model.level_1_effective_cycles_per_ccz
            ),
            "level_1_rate_hz": model.level_1_rate_hz,
            "level_2_cycles_per_ccz": model.level_2_cycles_per_ccz,
            "level_2_rate_hz": model.level_2_rate_hz,
            "reaction_demand_rate_hz": model.reaction_demand_rate_hz,
        },
        "model": {
            "compatibility_domain": model.compatibility_domain,
            "level_1_depth_coefficient": model.level_1_depth_coefficient,
            "level_1_distance": model.level_1_distance,
            "level_1_factory_count": model.level_1_factory_count,
            "level_1_states_per_ccz": model.level_1_states_per_ccz,
            "level_2_depth_coefficient": model.level_2_depth_coefficient,
            "level_2_distance": model.level_2_distance,
            "physical_gate_error_probability": model.physical_gate_error_probability,
            "reaction_latency_seconds": model.reaction_latency_seconds,
            "surface_code_cycle_seconds": model.surface_code_cycle_seconds,
        },
        "required_fields": list(REQUIRED_AUTOCCZ_SERVICE_FIELDS),
        "schema": audit.schema,
        "schema_version": audit.schema_version,
        "source_assets": [
            {
                "asset_id": asset.asset_id,
                "local_path": asset.local_path,
                "media_type": asset.media_type,
                "role": asset.role,
                "sha256": asset.sha256,
                "source_id": asset.source_id,
            }
            for asset in audit.source_assets
        ],
        "sources": [
            {
                "establishes": list(source.establishes),
                "evidence_status": source.evidence_status.value,
                "local_pdf": source.local_pdf,
                "pages": list(source.pages),
                "pdf_sha256": source.pdf_sha256,
                "source_id": source.source_id,
            }
            for source in audit.sources
        ],
        "task_id": audit.task_id,
    }
