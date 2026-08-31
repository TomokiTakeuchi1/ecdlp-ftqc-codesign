"""Fail-closed compatibility audit for a finite direct-CCZ backend."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.metadata import EvidenceStatus

DIRECT_CCZ_BACKEND_AUDIT_SCHEMA = "ecdlp-ftqc/direct-ccz-backend-audit"
DIRECT_CCZ_BACKEND_AUDIT_SCHEMA_VERSION = 1

_PORTABLE_FIELD_IDS = frozenset({"consumer.event_semantics"})
REQUIRED_DIRECT_CCZ_BACKEND_FIELDS = (
    "consumer.event_semantics",
    "consumer.batch_size",
    "consumer.parallel_ppm_layers",
    "consumer.duration_rounds",
    "consumer.logical_error_per_batch",
    "controller.decoder_throughput",
    "controller.reaction_latency",
    "processor.injection_port_capacity",
    "processor.logical_capacity",
    "processor.routing_model",
    "factory.batch_size",
    "factory.production_cycles",
    "factory.output_error_probability",
    "factory.delivery_latency",
    "factory.buffer_capacity",
    "factory.storage_error_per_cycle",
    "compatibility.factory_to_consumer_adapter",
)
_ADMISSIBLE_EVIDENCE = frozenset(
    {EvidenceStatus.PROVED, EvidenceStatus.NUMERICAL, EvidenceStatus.LITERATURE}
)


class DirectCczBackendAuditError(ValueError):
    """Raised when a finite-backend audit is malformed or forged."""


@dataclass(frozen=True, slots=True)
class DirectCczBackendAuditSource:
    """One pinned primary source used by the compatibility audit."""

    source_id: str
    local_pdf: str
    pdf_sha256: str
    pages: tuple[int, ...]
    establishes: tuple[str, ...]
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        if not self.source_id or not self.local_pdf or not self.establishes:
            raise DirectCczBackendAuditError("source pin fields cannot be empty")
        if len(self.pdf_sha256) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in self.pdf_sha256
        ):
            raise DirectCczBackendAuditError("source pin requires a SHA-256 digest")
        if not self.pages or any(page < 1 for page in self.pages):
            raise DirectCczBackendAuditError("source pages must be positive")


@dataclass(frozen=True, slots=True)
class DirectCczBackendFieldEvidence:
    """One required field, its reported value, and its compatibility scope."""

    field_id: str
    reported_value: str | None
    admitted_value: str | None
    unit: str | None
    evidence_status: EvidenceStatus
    source_ids: tuple[str, ...]
    compatibility_domain: str
    note: str

    def __post_init__(self) -> None:
        if self.field_id not in REQUIRED_DIRECT_CCZ_BACKEND_FIELDS:
            raise DirectCczBackendAuditError(f"unknown required field: {self.field_id}")
        if not self.compatibility_domain or not self.note:
            raise DirectCczBackendAuditError("field domain and note cannot be empty")
        if self.admitted_value is not None:
            if self.reported_value is None:
                raise DirectCczBackendAuditError("an admitted value requires a reported value")
            if self.evidence_status not in _ADMISSIBLE_EVIDENCE:
                raise DirectCczBackendAuditError("an admitted value requires admissible evidence")
            if not self.source_ids:
                raise DirectCczBackendAuditError("an admitted value requires a source")


@dataclass(frozen=True, slots=True)
class DirectCczScreenedComponent:
    """A source-backed component considered but not silently composed."""

    component_id: str
    role: str
    compatibility_domain: str
    source_ids: tuple[str, ...]
    contribution: str
    exclusion: str
    evidence_status: EvidenceStatus

    def __post_init__(self) -> None:
        text = (
            self.component_id,
            self.role,
            self.compatibility_domain,
            self.contribution,
            self.exclusion,
        )
        if any(not value for value in text) or not self.source_ids:
            raise DirectCczBackendAuditError("screened-component fields cannot be empty")


@dataclass(frozen=True, slots=True)
class DirectCczBackendCandidate:
    """One candidate backend and a complete required-field matrix."""

    candidate_id: str
    compatibility_domain: str
    field_evidence: tuple[DirectCczBackendFieldEvidence, ...]
    evidence_status: EvidenceStatus
    conclusion: str

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.compatibility_domain or not self.conclusion:
            raise DirectCczBackendAuditError("candidate fields cannot be empty")
        field_ids = tuple(item.field_id for item in self.field_evidence)
        if len(field_ids) != len(set(field_ids)):
            raise DirectCczBackendAuditError("candidate field IDs must be unique")
        if field_ids != REQUIRED_DIRECT_CCZ_BACKEND_FIELDS:
            raise DirectCczBackendAuditError(
                "candidate must record every required field exactly once in schema order"
            )

    @property
    def missing_fields(self) -> tuple[str, ...]:
        """Fields without a source-qualified finite value."""

        by_id = {item.field_id: item for item in self.field_evidence}
        return tuple(
            field_id
            for field_id in REQUIRED_DIRECT_CCZ_BACKEND_FIELDS
            if by_id[field_id].admitted_value is None
        )

    @property
    def incompatible_fields(self) -> tuple[str, ...]:
        """Qualified values taken from a different physical backend domain."""

        return tuple(
            item.field_id
            for item in self.field_evidence
            if item.admitted_value is not None
            and item.field_id not in _PORTABLE_FIELD_IDS
            and item.compatibility_domain != self.compatibility_domain
        )

    @property
    def backend_admitted(self) -> bool:
        """Whether all required finite values close in one compatible backend."""

        return not self.missing_fields and not self.incompatible_fields


@dataclass(frozen=True, slots=True)
class DirectCczBackendAudit:
    """Complete audit with a derived, fail-closed admission decision."""

    audit_id: str
    task_id: str
    sources: tuple[DirectCczBackendAuditSource, ...]
    candidate: DirectCczBackendCandidate
    screened_components: tuple[DirectCczScreenedComponent, ...]
    recorded_backend_admitted: bool
    schema: str = DIRECT_CCZ_BACKEND_AUDIT_SCHEMA
    schema_version: int = DIRECT_CCZ_BACKEND_AUDIT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.audit_id or not self.task_id or not self.sources:
            raise DirectCczBackendAuditError("audit ID, task ID, and sources are required")
        if self.schema != DIRECT_CCZ_BACKEND_AUDIT_SCHEMA:
            raise DirectCczBackendAuditError("unsupported direct-CCZ backend audit schema")
        if self.schema_version != DIRECT_CCZ_BACKEND_AUDIT_SCHEMA_VERSION:
            raise DirectCczBackendAuditError("unsupported direct-CCZ backend audit version")
        source_ids = tuple(source.source_id for source in self.sources)
        if len(source_ids) != len(set(source_ids)):
            raise DirectCczBackendAuditError("source IDs must be unique")
        component_ids = tuple(item.component_id for item in self.screened_components)
        if len(component_ids) != len(set(component_ids)):
            raise DirectCczBackendAuditError("screened-component IDs must be unique")
        known_sources = set(source_ids)
        referenced_sources = {
            source_id
            for item in self.candidate.field_evidence
            for source_id in item.source_ids
        } | {
            source_id
            for component in self.screened_components
            for source_id in component.source_ids
        }
        unknown = referenced_sources - known_sources
        if unknown:
            raise DirectCczBackendAuditError(
                f"audit references unknown sources: {', '.join(sorted(unknown))}"
            )
        if self.recorded_backend_admitted != self.candidate.backend_admitted:
            raise DirectCczBackendAuditError(
                "recorded backend admission disagrees with required fields"
            )


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise DirectCczBackendAuditError(f"{path} must be a string-keyed mapping")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DirectCczBackendAuditError(f"{path} must be a sequence")
    return value


def _required(obj: Mapping[str, object], key: str, path: str) -> object:
    if key not in obj:
        raise DirectCczBackendAuditError(f"{path} is missing {key!r}")
    return obj[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczBackendAuditError(f"{path} must be a nonempty string")
    return value


def _optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _integer(value: object, path: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DirectCczBackendAuditError(f"{path} must be an integer at least {minimum}")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DirectCczBackendAuditError(f"{path} must be Boolean")
    return value


def _string_tuple(value: object, path: str) -> tuple[str, ...]:
    return tuple(
        _string(item, f"{path}[{index}]")
        for index, item in enumerate(_sequence(value, path))
    )


def _load_source(raw: object, index: int) -> DirectCczBackendAuditSource:
    path = f"$.sources[{index}]"
    item = _mapping(raw, path)
    return DirectCczBackendAuditSource(
        source_id=_string(_required(item, "source_id", path), f"{path}.source_id"),
        local_pdf=_string(_required(item, "local_pdf", path), f"{path}.local_pdf"),
        pdf_sha256=_string(_required(item, "pdf_sha256", path), f"{path}.pdf_sha256"),
        pages=tuple(
            _integer(value, f"{path}.pages[{page_index}]")
            for page_index, value in enumerate(
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


def _load_field(raw: object, index: int) -> DirectCczBackendFieldEvidence:
    path = f"$.candidate.fields[{index}]"
    item = _mapping(raw, path)
    return DirectCczBackendFieldEvidence(
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


def _load_component(raw: object, index: int) -> DirectCczScreenedComponent:
    path = f"$.screened_components[{index}]"
    item = _mapping(raw, path)
    return DirectCczScreenedComponent(
        component_id=_string(_required(item, "component_id", path), f"{path}.component_id"),
        role=_string(_required(item, "role", path), f"{path}.role"),
        compatibility_domain=_string(
            _required(item, "compatibility_domain", path),
            f"{path}.compatibility_domain",
        ),
        source_ids=_string_tuple(
            _required(item, "source_ids", path), f"{path}.source_ids"
        ),
        contribution=_string(
            _required(item, "contribution", path), f"{path}.contribution"
        ),
        exclusion=_string(_required(item, "exclusion", path), f"{path}.exclusion"),
        evidence_status=EvidenceStatus(
            _string(_required(item, "evidence_status", path), f"{path}.evidence_status")
        ),
    )


def load_direct_ccz_backend_audit(path: Path) -> DirectCczBackendAudit:
    """Load and strictly validate a finite direct-CCZ backend audit."""

    try:
        loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DirectCczBackendAuditError(f"cannot load backend audit {path}: {exc}") from exc
    root = _mapping(loaded, "$")
    required_fields = _string_tuple(
        _required(root, "required_fields", "$"), "$.required_fields"
    )
    if required_fields != REQUIRED_DIRECT_CCZ_BACKEND_FIELDS:
        raise DirectCczBackendAuditError("required field list disagrees with audit schema")
    candidate_raw = _mapping(_required(root, "candidate", "$"), "$.candidate")
    candidate = DirectCczBackendCandidate(
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
    return DirectCczBackendAudit(
        audit_id=_string(_required(root, "audit_id", "$"), "$.audit_id"),
        task_id=_string(_required(root, "task_id", "$"), "$.task_id"),
        sources=tuple(
            _load_source(raw, index)
            for index, raw in enumerate(
                _sequence(_required(root, "sources", "$"), "$.sources")
            )
        ),
        candidate=candidate,
        screened_components=tuple(
            _load_component(raw, index)
            for index, raw in enumerate(
                _sequence(
                    _required(root, "screened_components", "$"),
                    "$.screened_components",
                )
            )
        ),
        recorded_backend_admitted=_boolean(
            _required(root, "recorded_backend_admitted", "$"),
            "$.recorded_backend_admitted",
        ),
        schema=_string(_required(root, "schema", "$"), "$.schema"),
        schema_version=_integer(
            _required(root, "schema_version", "$"), "$.schema_version"
        ),
    )


def direct_ccz_backend_audit_to_data(audit: DirectCczBackendAudit) -> dict[str, Any]:
    """Return a canonical JSON-compatible audit and compatibility matrix."""

    candidate = audit.candidate
    return {
        "admission": {
            "backend_admitted": candidate.backend_admitted,
            "incompatible_fields": list(candidate.incompatible_fields),
            "missing_fields": list(candidate.missing_fields),
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
        "required_fields": list(REQUIRED_DIRECT_CCZ_BACKEND_FIELDS),
        "schema": audit.schema,
        "schema_version": audit.schema_version,
        "screened_components": [
            {
                "compatibility_domain": item.compatibility_domain,
                "component_id": item.component_id,
                "contribution": item.contribution,
                "evidence_status": item.evidence_status.value,
                "exclusion": item.exclusion,
                "role": item.role,
                "source_ids": list(item.source_ids),
            }
            for item in audit.screened_components
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
