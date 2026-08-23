"""Adapt the reviewed Gidney DAG to the memory-I/O overlay."""

from __future__ import annotations

from collections import defaultdict

from ecdlp_ftqc.io.model import (
    InitialLocation,
    MemoryIoError,
    MemoryProgram,
    MemoryUnit,
    MemoryValue,
    MemoryValueOrigin,
)
from ecdlp_ftqc.metadata import CircuitDag, DagNode, ValueLifetime


def _requires_memory_residency(lifetime: ValueLifetime) -> bool:
    if lifetime.residency != "local":
        return True
    return any(
        flag is not False
        for flag in (
            lifetime.escapes_owner,
            lifetime.must_store_on_release,
            lifetime.must_preserve_initial_state,
        )
    )


def _memory_value(
    lifetime: ValueLifetime,
    node_to_unit_index: dict[str, int],
) -> MemoryValue:
    requires_memory = _requires_memory_residency(lifetime)
    if (
        requires_memory
        and lifetime.initialization == "input"
        and lifetime.release == "output"
        and lifetime.allocation_node_id is None
    ):
        return MemoryValue(
            value_id=lifetime.value_id,
            origin=MemoryValueOrigin.MEMORY_INPUT_OR_INOUT,
            initial_location=InitialLocation.MEMORY,
            birth_unit_index=None,
            release_unit_index=None,
            requires_memory_residency=True,
            must_store_on_release=lifetime.must_store_on_release,
            must_preserve_initial_state=lifetime.must_preserve_initial_state,
        )
    if (
        not requires_memory
        and lifetime.residency == "local"
        and lifetime.allocation_node_id is not None
        and lifetime.release_node_id is not None
        and lifetime.initialization not in {"input", "unknown"}
        and lifetime.release != "unknown"
        and lifetime.escapes_owner is False
        and lifetime.must_store_on_release is False
        and lifetime.must_preserve_initial_state is False
    ):
        try:
            birth = node_to_unit_index[lifetime.allocation_node_id]
            release = node_to_unit_index[lifetime.release_node_id]
        except KeyError as exc:
            raise MemoryIoError(
                f"value {lifetime.value_id!r} has a lifetime boundary outside source units"
            ) from exc
        return MemoryValue(
            value_id=lifetime.value_id,
            origin=MemoryValueOrigin.PROCESSOR_GENERATED_TEMPORARY,
            initial_location=InitialLocation.PROCESSOR_AT_CREATION,
            birth_unit_index=birth,
            release_unit_index=release,
            requires_memory_residency=False,
            must_store_on_release=False,
            must_preserve_initial_state=False,
        )
    raise MemoryIoError(
        f"value {lifetime.value_id!r} lacks an admitted explicit Gidney I/O origin"
    )


def adapt_gidney_dag_to_memory_program(dag: CircuitDag) -> MemoryProgram:
    """Collapse expanded DAG nodes back to source-operation I/O units.

    The expansion of measurement-assisted erase into a measurement and a
    conditional frame update remains visible through ``node_ids``.  Its
    memory and occupancy supports are conservatively unioned to reproduce the
    source oracle's operation-atomic unit.
    """

    if not dag.circuit_id.startswith("gidney-ripple-adder-width-"):
        raise MemoryIoError("Gidney I/O adapter received a different circuit")
    grouped: dict[int, list[DagNode]] = defaultdict(list)
    source_ids: dict[int, str] = {}
    for node in dag.nodes:
        existing = source_ids.setdefault(
            node.source_operation_index, node.source_operation_id
        )
        if existing != node.source_operation_id:
            raise MemoryIoError("one source operation index maps to multiple IDs")
        grouped[node.source_operation_index].append(node)
    if set(grouped) != set(range(dag.source_operation_count)):
        raise MemoryIoError("source operation indices are not contiguous")

    units: list[MemoryUnit] = []
    node_to_unit_index: dict[str, int] = {}
    for source_index in range(dag.source_operation_count):
        nodes = grouped[source_index]
        memory_support = tuple(
            sorted({value for node in nodes for value in node.required_memory_values})
        )
        occupancy_support = tuple(
            sorted({value for node in nodes for value in node.required_processor_values})
        )
        unit = MemoryUnit(
            unit_id=f"memory-unit:{source_index:06d}",
            source_operation_id=source_ids[source_index],
            source_operation_index=source_index,
            node_ids=tuple(node.node_id for node in nodes),
            memory_support=memory_support,
            occupancy_support=occupancy_support,
        )
        units.append(unit)
        for node in nodes:
            node_to_unit_index[node.node_id] = source_index

    values = tuple(
        _memory_value(lifetime, node_to_unit_index) for lifetime in dag.lifetimes
    )
    return MemoryProgram(
        circuit_id=dag.circuit_id,
        width=dag.width,
        source_commit=dag.source.commit,
        units=tuple(units),
        values=values,
    )
