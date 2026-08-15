"""Versioned, evidence-qualified configuration for a Mitten processor block."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.metadata import EvidenceStatus

MITTEN_CONFIG_SCHEMA = "ecdlp-ftqc/mitten-backend-config"
MITTEN_CONFIG_SCHEMA_VERSION = 1


class MittenImplementationKind(str, Enum):
    """Physical gadget or explicitly provisional logical-operation model."""

    CHECK_PREPARE_T = "check_prepare_t"
    CHECK_CNOT_CQLU = "check_cnot_cqlu"
    CHECK_T_GATE = "check_t_gate"
    CHECK_H_CQLU = "check_h_cqlu"
    CHECK_S_CQLU = "check_s_cqlu"
    SEED_X_SURGERY = "seed_x_surgery"
    SEED_Y_SURGERY = "seed_y_surgery"
    SEED_Z_SURGERY = "seed_z_surgery"
    SEED_XX_SURGERY = "seed_xx_surgery"
    SEED_ZZ_SURGERY = "seed_zz_surgery"
    HIGH_RATE_XX_10 = "high_rate_xx_10"
    FULL_EXTRACTOR = "full_extractor"
    CHECK_CONDITIONAL_CZ_FRAME = "check_conditional_cz_frame"
    CHECK_RELEASE = "check_release"


@dataclass(frozen=True, slots=True)
class ResourcePoolSpec:
    """A named exclusive resource with a fixed number of interchangeable slots."""

    name: str
    capacity: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("resource-pool name cannot be empty")
        if self.capacity < 1:
            raise ValueError("resource-pool capacity must be positive")


@dataclass(frozen=True, slots=True)
class MittenOperationCost:
    """One operation model with separate time, space, and evidence fields."""

    implementation: MittenImplementationKind
    rounds: int
    gadget_data_ancilla_qubits: int
    gadget_check_ancilla_qubits: int
    exclusive_resource: str
    evidence_status: EvidenceStatus
    source_note: str

    def __post_init__(self) -> None:
        if self.rounds < 0:
            raise ValueError("operation duration cannot be negative")
        if self.gadget_data_ancilla_qubits < 0:
            raise ValueError("gadget data-ancilla count cannot be negative")
        if self.gadget_check_ancilla_qubits < 0:
            raise ValueError("gadget check-ancilla count cannot be negative")
        if not self.exclusive_resource or not self.source_note:
            raise ValueError("operation resource and source note cannot be empty")

    @property
    def added_physical_qubits(self) -> int:
        return self.gadget_data_ancilla_qubits + self.gadget_check_ancilla_qubits


@dataclass(frozen=True, slots=True)
class HighRateBatchSpec:
    """A source-supported exact high-rate batch size and measured Pauli family."""

    implementation: MittenImplementationKind
    pauli_family: str
    batch_size: int
    disjoint_support_required: bool

    def __post_init__(self) -> None:
        if not self.pauli_family:
            raise ValueError("high-rate Pauli family cannot be empty")
        if self.batch_size < 2:
            raise ValueError("high-rate batch size must be at least two")


@dataclass(frozen=True, slots=True)
class MittenBackendConfig:
    """Finite-size processor and gadget data used by the scheduler."""

    configuration_id: str
    data_physical_qubits: int
    syndrome_ancilla_qubits: int
    logical_qubits: int
    distance: int
    source: str
    resource_pools: tuple[ResourcePoolSpec, ...]
    operation_costs: tuple[MittenOperationCost, ...]
    high_rate_batches: tuple[HighRateBatchSpec, ...]
    schema: str = MITTEN_CONFIG_SCHEMA
    schema_version: int = MITTEN_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.configuration_id or not self.source:
            raise ValueError("configuration ID and source cannot be empty")
        if self.schema != MITTEN_CONFIG_SCHEMA:
            raise ValueError("unsupported Mitten configuration schema")
        if self.schema_version != MITTEN_CONFIG_SCHEMA_VERSION:
            raise ValueError("unsupported Mitten configuration schema version")
        if min(
            self.data_physical_qubits,
            self.syndrome_ancilla_qubits,
            self.logical_qubits,
            self.distance,
        ) < 1:
            raise ValueError("code sizes and distance must be positive")
        resource_names = tuple(resource.name for resource in self.resource_pools)
        if len(resource_names) != len(set(resource_names)):
            raise ValueError("resource-pool names must be unique")
        implementations = tuple(cost.implementation for cost in self.operation_costs)
        if len(implementations) != len(set(implementations)):
            raise ValueError("operation implementations must be unique")
        known_resources = set(resource_names)
        if any(
            cost.exclusive_resource not in known_resources
            for cost in self.operation_costs
        ):
            raise ValueError("operation cost references an unknown resource pool")
        batch_keys = tuple(
            (batch.pauli_family, batch.batch_size) for batch in self.high_rate_batches
        )
        if len(batch_keys) != len(set(batch_keys)):
            raise ValueError("high-rate batch specifications must be unique")
        known_implementations = set(implementations)
        if any(
            batch.implementation not in known_implementations
            for batch in self.high_rate_batches
        ):
            raise ValueError("high-rate batch references an unknown implementation")

    @property
    def known_base_physical_qubits(self) -> int:
        """Data plus one syndrome ancilla per listed independent check."""

        return self.data_physical_qubits + self.syndrome_ancilla_qubits

    def cost(self, implementation: MittenImplementationKind) -> MittenOperationCost:
        """Return the unique cost record for an implementation."""

        for cost in self.operation_costs:
            if cost.implementation is implementation:
                return cost
        raise KeyError(f"no operation cost for {implementation.value!r}")

    def resource_capacity(self, name: str) -> int:
        """Return the number of interchangeable slots in a resource pool."""

        for resource in self.resource_pools:
            if resource.name == name:
                return resource.capacity
        raise KeyError(f"unknown resource pool {name!r}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{path} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{path} keys must be strings")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{path} must be a sequence")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a nonempty string")
    return value


def _integer(value: object, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{path} must be an integer at least {minimum}")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{path} must be Boolean")
    return value


def _required(obj: Mapping[str, object], name: str, path: str) -> object:
    if name not in obj:
        raise ValueError(f"{path} is missing {name!r}")
    return obj[name]


def load_mitten_backend_config(path: Path) -> MittenBackendConfig:
    """Load and validate the versioned Mitten backend configuration."""

    try:
        loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load Mitten configuration {path}: {exc}") from exc
    root = _mapping(loaded, "$")
    schema = _string(_required(root, "schema", "$"), "$.schema")
    schema_version = _integer(
        _required(root, "schema_version", "$"), "$.schema_version", minimum=1
    )
    code = _mapping(_required(root, "code", "$"), "$.code")
    resources = tuple(
        ResourcePoolSpec(
            name=_string(_required(item, "name", item_path), f"{item_path}.name"),
            capacity=_integer(
                _required(item, "capacity", item_path),
                f"{item_path}.capacity",
                minimum=1,
            ),
        )
        for index, raw_item in enumerate(
            _sequence(_required(root, "resource_pools", "$"), "$.resource_pools")
        )
        for item_path in (f"$.resource_pools[{index}]",)
        for item in (_mapping(raw_item, item_path),)
    )
    costs = tuple(
        MittenOperationCost(
            implementation=MittenImplementationKind(
                _string(
                    _required(item, "implementation", item_path),
                    f"{item_path}.implementation",
                )
            ),
            rounds=_integer(
                _required(item, "rounds", item_path), f"{item_path}.rounds"
            ),
            gadget_data_ancilla_qubits=_integer(
                _required(item, "gadget_data_ancilla_qubits", item_path),
                f"{item_path}.gadget_data_ancilla_qubits",
            ),
            gadget_check_ancilla_qubits=_integer(
                _required(item, "gadget_check_ancilla_qubits", item_path),
                f"{item_path}.gadget_check_ancilla_qubits",
            ),
            exclusive_resource=_string(
                _required(item, "exclusive_resource", item_path),
                f"{item_path}.exclusive_resource",
            ),
            evidence_status=EvidenceStatus(
                _string(
                    _required(item, "evidence_status", item_path),
                    f"{item_path}.evidence_status",
                )
            ),
            source_note=_string(
                _required(item, "source_note", item_path),
                f"{item_path}.source_note",
            ),
        )
        for index, raw_item in enumerate(
            _sequence(_required(root, "operation_costs", "$"), "$.operation_costs")
        )
        for item_path in (f"$.operation_costs[{index}]",)
        for item in (_mapping(raw_item, item_path),)
    )
    batches = tuple(
        HighRateBatchSpec(
            implementation=MittenImplementationKind(
                _string(
                    _required(item, "implementation", item_path),
                    f"{item_path}.implementation",
                )
            ),
            pauli_family=_string(
                _required(item, "pauli_family", item_path),
                f"{item_path}.pauli_family",
            ),
            batch_size=_integer(
                _required(item, "batch_size", item_path),
                f"{item_path}.batch_size",
                minimum=2,
            ),
            disjoint_support_required=_boolean(
                _required(item, "disjoint_support_required", item_path),
                f"{item_path}.disjoint_support_required",
            ),
        )
        for index, raw_item in enumerate(
            _sequence(_required(root, "high_rate_batches", "$"), "$.high_rate_batches")
        )
        for item_path in (f"$.high_rate_batches[{index}]",)
        for item in (_mapping(raw_item, item_path),)
    )
    return MittenBackendConfig(
        configuration_id=_string(
            _required(root, "configuration_id", "$"), "$.configuration_id"
        ),
        data_physical_qubits=_integer(
            _required(code, "data_physical_qubits", "$.code"),
            "$.code.data_physical_qubits",
            minimum=1,
        ),
        syndrome_ancilla_qubits=_integer(
            _required(code, "syndrome_ancilla_qubits", "$.code"),
            "$.code.syndrome_ancilla_qubits",
            minimum=1,
        ),
        logical_qubits=_integer(
            _required(code, "logical_qubits", "$.code"),
            "$.code.logical_qubits",
            minimum=1,
        ),
        distance=_integer(
            _required(code, "distance", "$.code"),
            "$.code.distance",
            minimum=1,
        ),
        source=_string(_required(root, "source", "$"), "$.source"),
        resource_pools=resources,
        operation_costs=costs,
        high_rate_batches=batches,
        schema=schema,
        schema_version=schema_version,
    )
