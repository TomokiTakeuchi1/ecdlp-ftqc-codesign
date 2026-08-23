"""Evidence-qualified Mitten J300 costs for adaptive Pauli computation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.metadata import EvidenceStatus

PBC_MITTEN_CONFIG_SCHEMA = "ecdlp-ftqc/pbc-mitten-backend-config"
PBC_MITTEN_CONFIG_SCHEMA_VERSION = 2


class PbcMittenImplementationKind(str, Enum):
    """Native gadget or explicitly provisional implementation choice."""

    STABILIZER_PREPARATION = "stabilizer_preparation"
    MAGIC_T_PREPARATION = "magic_t_preparation"
    SEED_X = "seed_x"
    SEED_Y = "seed_y"
    SEED_Z = "seed_z"
    SEED_XX = "seed_xx"
    SEED_ZZ = "seed_zz"
    HIGH_RATE_XX_10 = "high_rate_xx_10"
    FULL_EXTRACTOR = "full_extractor"
    PAULI_FRAME_UPDATE = "pauli_frame_update"
    CONDITIONAL_CZ = "conditional_cz"
    BOOKKEEPING = "bookkeeping"


@dataclass(frozen=True, slots=True)
class PbcMittenResourcePool:
    name: str
    capacity: int

    def __post_init__(self) -> None:
        if not self.name or self.capacity < 1:
            raise ValueError("resource pool requires a name and positive capacity")


@dataclass(frozen=True, slots=True)
class PbcMittenOperationCost:
    """Time and additional-space claims with deliberately separate evidence."""

    implementation: PbcMittenImplementationKind
    rounds: int
    gadget_data_ancilla_qubits: int
    gadget_check_ancilla_qubits: int
    exclusive_resource: str
    timing_evidence_status: EvidenceStatus
    space_evidence_status: EvidenceStatus
    source_note: str

    def __post_init__(self) -> None:
        if min(
            self.rounds,
            self.gadget_data_ancilla_qubits,
            self.gadget_check_ancilla_qubits,
        ) < 0:
            raise ValueError("operation time and space counts cannot be negative")
        if not self.exclusive_resource or not self.source_note:
            raise ValueError("operation resource and source note cannot be empty")

    @property
    def added_physical_qubits(self) -> int:
        return self.gadget_data_ancilla_qubits + self.gadget_check_ancilla_qubits


@dataclass(frozen=True, slots=True)
class PbcMittenHighRateSpec:
    implementation: PbcMittenImplementationKind
    pauli_family: str
    batch_size: int
    disjoint_logical_support_required: bool
    distinct_scratch_slots_required: bool

    def __post_init__(self) -> None:
        if not self.pauli_family or self.batch_size < 2:
            raise ValueError("high-rate batch requires a family and size at least two")


@dataclass(frozen=True, slots=True)
class PbcMittenBackendConfig:
    """Finite-size J300 processor profile used by the adaptive-PBC scheduler."""

    configuration_id: str
    data_physical_qubits: int
    syndrome_ancilla_qubits: int
    logical_qubits: int
    distance: int
    default_scratch_slots: int
    classical_reaction_rounds: int
    classical_reaction_evidence_status: EvidenceStatus
    source: str
    resource_pools: tuple[PbcMittenResourcePool, ...]
    operation_costs: tuple[PbcMittenOperationCost, ...]
    high_rate_batches: tuple[PbcMittenHighRateSpec, ...]
    schema: str = PBC_MITTEN_CONFIG_SCHEMA
    schema_version: int = PBC_MITTEN_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema != PBC_MITTEN_CONFIG_SCHEMA:
            raise ValueError("unsupported PBC Mitten configuration schema")
        if self.schema_version != PBC_MITTEN_CONFIG_SCHEMA_VERSION:
            raise ValueError("unsupported PBC Mitten configuration schema version")
        if not self.configuration_id or not self.source:
            raise ValueError("configuration ID and source cannot be empty")
        if min(
            self.data_physical_qubits,
            self.syndrome_ancilla_qubits,
            self.logical_qubits,
            self.distance,
        ) < 1:
            raise ValueError("code sizes and distance must be positive")
        if self.default_scratch_slots < 0 or self.classical_reaction_rounds < 0:
            raise ValueError("scratch slots and reaction rounds cannot be negative")
        resource_names = tuple(pool.name for pool in self.resource_pools)
        if len(resource_names) != len(set(resource_names)):
            raise ValueError("resource-pool names must be unique")
        implementations = tuple(cost.implementation for cost in self.operation_costs)
        if len(implementations) != len(set(implementations)):
            raise ValueError("operation implementations must be unique")
        if any(cost.exclusive_resource not in resource_names for cost in self.operation_costs):
            raise ValueError("operation cost references an unknown resource pool")
        known = set(implementations)
        if any(batch.implementation not in known for batch in self.high_rate_batches):
            raise ValueError("high-rate batch references an unknown implementation")

    @property
    def known_base_physical_qubits(self) -> int:
        return self.data_physical_qubits + self.syndrome_ancilla_qubits

    def cost(
        self, implementation: PbcMittenImplementationKind
    ) -> PbcMittenOperationCost:
        for cost in self.operation_costs:
            if cost.implementation is implementation:
                return cost
        raise KeyError(f"no PBC Mitten cost for {implementation.value!r}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise TypeError(f"{path} must be a string-keyed mapping")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{path} must be a sequence")
    return value


def _required(obj: Mapping[str, object], key: str, path: str) -> object:
    if key not in obj:
        raise ValueError(f"{path} is missing {key!r}")
    return obj[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a nonempty string")
    return value


def _integer(value: object, path: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{path} must be an integer at least {minimum}")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{path} must be Boolean")
    return value


def load_pbc_mitten_backend_config(path: Path) -> PbcMittenBackendConfig:
    """Load and validate the version-two adaptive-PBC backend profile."""

    try:
        loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load PBC Mitten configuration {path}: {exc}") from exc
    root = _mapping(loaded, "$")
    code = _mapping(_required(root, "code", "$"), "$.code")
    reaction = _mapping(_required(root, "classical_reaction", "$"), "$.classical_reaction")

    resources: list[PbcMittenResourcePool] = []
    for index, raw in enumerate(_sequence(_required(root, "resource_pools", "$"), "$.resource_pools")):
        path_name = f"$.resource_pools[{index}]"
        item = _mapping(raw, path_name)
        resources.append(
            PbcMittenResourcePool(
                name=_string(_required(item, "name", path_name), f"{path_name}.name"),
                capacity=_integer(_required(item, "capacity", path_name), f"{path_name}.capacity", 1),
            )
        )

    costs: list[PbcMittenOperationCost] = []
    for index, raw in enumerate(_sequence(_required(root, "operation_costs", "$"), "$.operation_costs")):
        path_name = f"$.operation_costs[{index}]"
        item = _mapping(raw, path_name)
        costs.append(
            PbcMittenOperationCost(
                implementation=PbcMittenImplementationKind(
                    _string(_required(item, "implementation", path_name), f"{path_name}.implementation")
                ),
                rounds=_integer(_required(item, "rounds", path_name), f"{path_name}.rounds"),
                gadget_data_ancilla_qubits=_integer(
                    _required(item, "gadget_data_ancilla_qubits", path_name),
                    f"{path_name}.gadget_data_ancilla_qubits",
                ),
                gadget_check_ancilla_qubits=_integer(
                    _required(item, "gadget_check_ancilla_qubits", path_name),
                    f"{path_name}.gadget_check_ancilla_qubits",
                ),
                exclusive_resource=_string(
                    _required(item, "exclusive_resource", path_name),
                    f"{path_name}.exclusive_resource",
                ),
                timing_evidence_status=EvidenceStatus(
                    _string(_required(item, "timing_evidence_status", path_name), f"{path_name}.timing_evidence_status")
                ),
                space_evidence_status=EvidenceStatus(
                    _string(_required(item, "space_evidence_status", path_name), f"{path_name}.space_evidence_status")
                ),
                source_note=_string(_required(item, "source_note", path_name), f"{path_name}.source_note"),
            )
        )

    batches: list[PbcMittenHighRateSpec] = []
    for index, raw in enumerate(_sequence(_required(root, "high_rate_batches", "$"), "$.high_rate_batches")):
        path_name = f"$.high_rate_batches[{index}]"
        item = _mapping(raw, path_name)
        batches.append(
            PbcMittenHighRateSpec(
                implementation=PbcMittenImplementationKind(
                    _string(_required(item, "implementation", path_name), f"{path_name}.implementation")
                ),
                pauli_family=_string(_required(item, "pauli_family", path_name), f"{path_name}.pauli_family"),
                batch_size=_integer(_required(item, "batch_size", path_name), f"{path_name}.batch_size", 2),
                disjoint_logical_support_required=_boolean(
                    _required(item, "disjoint_logical_support_required", path_name),
                    f"{path_name}.disjoint_logical_support_required",
                ),
                distinct_scratch_slots_required=_boolean(
                    _required(item, "distinct_scratch_slots_required", path_name),
                    f"{path_name}.distinct_scratch_slots_required",
                ),
            )
        )

    return PbcMittenBackendConfig(
        configuration_id=_string(_required(root, "configuration_id", "$"), "$.configuration_id"),
        data_physical_qubits=_integer(_required(code, "data_physical_qubits", "$.code"), "$.code.data_physical_qubits", 1),
        syndrome_ancilla_qubits=_integer(_required(code, "syndrome_ancilla_qubits", "$.code"), "$.code.syndrome_ancilla_qubits", 1),
        logical_qubits=_integer(_required(code, "logical_qubits", "$.code"), "$.code.logical_qubits", 1),
        distance=_integer(_required(code, "distance", "$.code"), "$.code.distance", 1),
        default_scratch_slots=_integer(_required(root, "default_scratch_slots", "$"), "$.default_scratch_slots"),
        classical_reaction_rounds=_integer(_required(reaction, "rounds", "$.classical_reaction"), "$.classical_reaction.rounds"),
        classical_reaction_evidence_status=EvidenceStatus(
            _string(_required(reaction, "evidence_status", "$.classical_reaction"), "$.classical_reaction.evidence_status")
        ),
        source=_string(_required(root, "source", "$"), "$.source"),
        resource_pools=tuple(resources),
        operation_costs=tuple(costs),
        high_rate_batches=tuple(batches),
        schema=_string(_required(root, "schema", "$"), "$.schema"),
        schema_version=_integer(_required(root, "schema_version", "$"), "$.schema_version", 1),
    )
