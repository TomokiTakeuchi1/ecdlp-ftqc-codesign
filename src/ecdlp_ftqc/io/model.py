"""Architecture-neutral logical-state movement records.

The records in this module distinguish memory--processor teleportation moves
from circuit-level Bell teleportation.  A value has one usable location at a
time; a load removes it from memory conceptually and a store returns it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

MEMORY_IO_SCHEMA = "ecdlp-ftqc/memory-io-overlay"
MEMORY_IO_SCHEMA_VERSION = 1
MEMORY_TRANSFER_SEMANTICS = "memory_processor_teleportation_move"
FIXED_ORDER_BELADY_POLICY = "fixed_order_persistent_belady_v1"
MAXIMAL_PREFIX_PARTITION_POLICY = "maximal_prefix_partition_v1"
SMALL_WIDTH_PARTITION_REFERENCE_POLICY = "exact_small_width_partition_reference_v1"


class MemoryIoError(ValueError):
    """Raised when a memory-I/O record violates its declared contract."""


class MemoryValueOrigin(str, Enum):
    """Origins admitted by the bounded Gidney I/O cycle."""

    MEMORY_INPUT_OR_INOUT = "memory_input_or_inout"
    PROCESSOR_GENERATED_TEMPORARY = "processor_generated_temporary"


class InitialLocation(str, Enum):
    """Location before a value's first executable use."""

    MEMORY = "memory"
    PROCESSOR_AT_CREATION = "processor_at_creation"


class TransferKind(str, Enum):
    """Direction of one logical-state teleportation move."""

    LOAD = "load"
    STORE = "store"


class TransferReason(str, Enum):
    """Auditable cause for one transfer action."""

    REQUIRED_LOAD = "required_load"
    EVICTION_RETURN = "eviction_return"
    FINAL_RETURN = "final_return"
    BASELINE_INTERFACE_TRANSFER = "baseline_interface_transfer"
    PARTITION_BOUNDARY_SPILL = "partition_boundary_spill"
    PARTITION_BOUNDARY_RELOAD = "partition_boundary_reload"


@dataclass(frozen=True, slots=True)
class MemoryValue:
    """Origin and lifetime facts needed for placement decisions."""

    value_id: str
    origin: MemoryValueOrigin
    initial_location: InitialLocation
    birth_unit_index: int | None
    release_unit_index: int | None
    requires_memory_residency: bool
    must_store_on_release: bool | None
    must_preserve_initial_state: bool | None

    def __post_init__(self) -> None:
        if not self.value_id:
            raise MemoryIoError("memory value ID cannot be empty")
        if self.origin is MemoryValueOrigin.MEMORY_INPUT_OR_INOUT:
            if self.initial_location is not InitialLocation.MEMORY:
                raise MemoryIoError("memory input must begin in memory")
            if not self.requires_memory_residency:
                raise MemoryIoError("memory input must require memory residency")
            if self.birth_unit_index is not None or self.release_unit_index is not None:
                raise MemoryIoError("memory input cannot have processor creation bounds")
        else:
            if self.initial_location is not InitialLocation.PROCESSOR_AT_CREATION:
                raise MemoryIoError("processor-generated value must begin at creation")
            if self.requires_memory_residency:
                raise MemoryIoError("processor-generated temporary cannot be strict memory")
            if self.birth_unit_index is None or self.release_unit_index is None:
                raise MemoryIoError("processor-generated value requires birth and release units")
            if self.birth_unit_index > self.release_unit_index:
                raise MemoryIoError("processor-generated value releases before creation")


@dataclass(frozen=True, slots=True)
class MemoryUnit:
    """One fixed-order source unit with separate memory and occupancy support."""

    unit_id: str
    source_operation_id: str
    source_operation_index: int
    node_ids: tuple[str, ...]
    memory_support: tuple[str, ...]
    occupancy_support: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.unit_id or not self.source_operation_id or not self.node_ids:
            raise MemoryIoError("memory unit identifiers cannot be empty")
        if self.source_operation_index < 0:
            raise MemoryIoError("source operation index cannot be negative")
        for field_name in ("node_ids", "memory_support", "occupancy_support"):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise MemoryIoError(f"{field_name} cannot contain duplicates")
        if not set(self.memory_support).issubset(self.occupancy_support):
            raise MemoryIoError("memory support must be included in occupancy support")


@dataclass(frozen=True, slots=True)
class MemoryProgram:
    """Replayable I/O overlay derived from a circuit DAG."""

    circuit_id: str
    width: int
    source_commit: str
    units: tuple[MemoryUnit, ...]
    values: tuple[MemoryValue, ...]
    schema: str = MEMORY_IO_SCHEMA
    schema_version: int = MEMORY_IO_SCHEMA_VERSION
    transfer_semantics: str = MEMORY_TRANSFER_SEMANTICS

    def __post_init__(self) -> None:
        if not self.circuit_id or not self.source_commit:
            raise MemoryIoError("memory program provenance cannot be empty")
        if self.width < 2 or not self.units or not self.values:
            raise MemoryIoError("memory program requires width, units, and values")
        if self.schema != MEMORY_IO_SCHEMA or self.schema_version != MEMORY_IO_SCHEMA_VERSION:
            raise MemoryIoError("unsupported memory-I/O schema")
        if self.transfer_semantics != MEMORY_TRANSFER_SEMANTICS:
            raise MemoryIoError("unsupported memory transfer semantics")
        unit_ids = tuple(unit.unit_id for unit in self.units)
        value_ids = tuple(value.value_id for value in self.values)
        if len(unit_ids) != len(set(unit_ids)):
            raise MemoryIoError("memory unit IDs must be unique")
        if len(value_ids) != len(set(value_ids)):
            raise MemoryIoError("memory value IDs must be unique")
        expected_indices = tuple(range(len(self.units)))
        observed_indices = tuple(unit.source_operation_index for unit in self.units)
        if observed_indices != expected_indices:
            raise MemoryIoError("memory units must follow contiguous source operation order")
        known_values = set(value_ids)
        strict_memory = self.memory_value_ids
        for unit in self.units:
            if not set(unit.occupancy_support).issubset(known_values):
                raise MemoryIoError("memory unit references an unknown logical value")
            if set(unit.memory_support) != set(unit.occupancy_support) & strict_memory:
                raise MemoryIoError("unit memory and occupancy supports disagree")
        for value in self.values:
            if value.origin is not MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY:
                continue
            assert value.birth_unit_index is not None
            assert value.release_unit_index is not None
            if value.release_unit_index >= len(self.units):
                raise MemoryIoError("processor-generated value releases outside the program")
            for unit_index in range(value.birth_unit_index, value.release_unit_index + 1):
                if value.value_id not in self.units[unit_index].occupancy_support:
                    raise MemoryIoError(
                        f"processor-generated value {value.value_id!r} is absent while live"
                    )

    @property
    def memory_value_ids(self) -> set[str]:
        return {
            value.value_id for value in self.values if value.requires_memory_residency
        }

    @property
    def values_by_id(self) -> dict[str, MemoryValue]:
        return {value.value_id: value for value in self.values}


@dataclass(frozen=True, slots=True)
class TransferAction:
    """One move at a unit or partition boundary."""

    boundary_index: int
    value_id: str
    kind: TransferKind
    reason: TransferReason


@dataclass(frozen=True, slots=True)
class UnitPlacement:
    """Processor contents while one fixed-order unit executes."""

    unit_id: str
    resident_memory: tuple[str, ...]
    local_occupancy: tuple[str, ...]
    processor_occupancy: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FixedOrderSchedule:
    """Deterministic fixed-order transfer schedule."""

    circuit_id: str
    capacity: int
    load_cost: int
    store_cost: int
    actions: tuple[TransferAction, ...]
    placements: tuple[UnitPlacement, ...]
    loads: int
    stores: int
    objective_cost: int
    policy_identity: str = FIXED_ORDER_BELADY_POLICY
    transfer_semantics: str = MEMORY_TRANSFER_SEMANTICS


@dataclass(frozen=True, slots=True)
class MemoryPartition:
    """One maximal feasible interval of source units."""

    partition_index: int
    start_unit_index: int
    stop_unit_index: int
    unit_ids: tuple[str, ...]
    memory_interface: tuple[str, ...]
    peak_live_local_occupancy: int
    footprint: int


@dataclass(frozen=True, slots=True)
class PartitionLayout:
    """Maximal-prefix layout under a stated processor capacity."""

    circuit_id: str
    width: int
    capacity: int
    strict_memory_values: tuple[str, ...]
    partitions: tuple[MemoryPartition, ...]
    policy_identity: str = MAXIMAL_PREFIX_PARTITION_POLICY


@dataclass(frozen=True, slots=True)
class PartitionPlacement:
    """Entry, live, and retained values for one partition."""

    partition_index: int
    entry_resident: tuple[str, ...]
    post_partition_live_resident: tuple[str, ...]
    exit_resident: tuple[str, ...]
    peak_processor_occupancy: int


@dataclass(frozen=True, slots=True)
class PartitionSchedule:
    """Exact small-width origin-aware partition reference."""

    circuit_id: str
    width: int
    capacity: int
    load_cost: int
    store_cost: int
    actions: tuple[TransferAction, ...]
    placements: tuple[PartitionPlacement, ...]
    loads: int
    stores: int
    objective_cost: int
    states_explored: int
    transitions_explored: int
    policy_identity: str = SMALL_WIDTH_PARTITION_REFERENCE_POLICY
    transfer_semantics: str = MEMORY_TRANSFER_SEMANTICS


def _transfer_data(action: TransferAction) -> dict[str, Any]:
    return {
        "boundary_index": action.boundary_index,
        "kind": action.kind.value,
        "reason": action.reason.value,
        "value_id": action.value_id,
    }


def memory_program_to_data(program: MemoryProgram) -> dict[str, Any]:
    """Return deterministic JSON-compatible memory-program data."""

    return {
        "circuit_id": program.circuit_id,
        "schema": program.schema,
        "schema_version": program.schema_version,
        "source_commit": program.source_commit,
        "transfer_semantics": program.transfer_semantics,
        "units": [
            {
                "memory_support": list(unit.memory_support),
                "node_ids": list(unit.node_ids),
                "occupancy_support": list(unit.occupancy_support),
                "source_operation_id": unit.source_operation_id,
                "source_operation_index": unit.source_operation_index,
                "unit_id": unit.unit_id,
            }
            for unit in program.units
        ],
        "values": [
            {
                "birth_unit_index": value.birth_unit_index,
                "initial_location": value.initial_location.value,
                "must_preserve_initial_state": value.must_preserve_initial_state,
                "must_store_on_release": value.must_store_on_release,
                "origin": value.origin.value,
                "release_unit_index": value.release_unit_index,
                "requires_memory_residency": value.requires_memory_residency,
                "value_id": value.value_id,
            }
            for value in program.values
        ],
        "width": program.width,
    }


def fixed_order_schedule_to_data(schedule: FixedOrderSchedule) -> dict[str, Any]:
    """Return deterministic JSON-compatible fixed-order schedule data."""

    return {
        "actions": [_transfer_data(action) for action in schedule.actions],
        "capacity": schedule.capacity,
        "circuit_id": schedule.circuit_id,
        "load_cost": schedule.load_cost,
        "loads": schedule.loads,
        "objective_cost": schedule.objective_cost,
        "placements": [
            {
                "local_occupancy": list(placement.local_occupancy),
                "processor_occupancy": list(placement.processor_occupancy),
                "resident_memory": list(placement.resident_memory),
                "unit_id": placement.unit_id,
            }
            for placement in schedule.placements
        ],
        "policy_identity": schedule.policy_identity,
        "store_cost": schedule.store_cost,
        "stores": schedule.stores,
        "transfer_semantics": schedule.transfer_semantics,
    }


def partition_schedule_to_data(
    layout: PartitionLayout, schedule: PartitionSchedule
) -> dict[str, Any]:
    """Return deterministic JSON-compatible partition-reference data."""

    return {
        "actions": [_transfer_data(action) for action in schedule.actions],
        "capacity": schedule.capacity,
        "circuit_id": schedule.circuit_id,
        "layout": {
            "partitions": [
                {
                    "footprint": partition.footprint,
                    "memory_interface": list(partition.memory_interface),
                    "partition_index": partition.partition_index,
                    "peak_live_local_occupancy": partition.peak_live_local_occupancy,
                    "start_unit_index": partition.start_unit_index,
                    "stop_unit_index": partition.stop_unit_index,
                    "unit_ids": list(partition.unit_ids),
                }
                for partition in layout.partitions
            ],
            "policy_identity": layout.policy_identity,
            "strict_memory_values": list(layout.strict_memory_values),
        },
        "load_cost": schedule.load_cost,
        "loads": schedule.loads,
        "objective_cost": schedule.objective_cost,
        "placements": [
            {
                "entry_resident": list(placement.entry_resident),
                "exit_resident": list(placement.exit_resident),
                "partition_index": placement.partition_index,
                "peak_processor_occupancy": placement.peak_processor_occupancy,
                "post_partition_live_resident": list(
                    placement.post_partition_live_resident
                ),
            }
            for placement in schedule.placements
        ],
        "policy_identity": schedule.policy_identity,
        "states_explored": schedule.states_explored,
        "store_cost": schedule.store_cost,
        "stores": schedule.stores,
        "transfer_semantics": schedule.transfer_semantics,
        "transitions_explored": schedule.transitions_explored,
        "width": schedule.width,
    }


def dumps_memory_program(program: MemoryProgram) -> str:
    """Serialize a memory program canonically."""

    return json.dumps(memory_program_to_data(program), indent=2, sort_keys=True) + "\n"


def dumps_fixed_order_schedule(schedule: FixedOrderSchedule) -> str:
    """Serialize a fixed-order schedule canonically."""

    return json.dumps(fixed_order_schedule_to_data(schedule), indent=2, sort_keys=True) + "\n"


def dumps_partition_schedule(
    layout: PartitionLayout, schedule: PartitionSchedule
) -> str:
    """Serialize a partition schedule canonically."""

    return json.dumps(
        partition_schedule_to_data(layout, schedule), indent=2, sort_keys=True
    ) + "\n"
