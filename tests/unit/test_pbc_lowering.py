from __future__ import annotations

from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import load_gidney_oracle_dag
from ecdlp_ftqc.compiler import (
    AncillaRole,
    LogicalPrimitive,
    LogicalPrimitiveKind,
    LogicalTrace,
    PbcOperationKind,
    lower_gidney_phase_exact,
    lower_to_adaptive_pauli_measurements,
    pbc_trace_to_data,
    verify_reference_gadget_channels,
)
from ecdlp_ftqc.metadata import EvidenceStatus

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "gidney_oracle"


def _single_primitive_trace(primitive: LogicalPrimitive) -> LogicalTrace:
    return LogicalTrace(
        trace_id=f"test:{primitive.kind.value}",
        source_circuit_id="gidney-ripple-adder-width-test",
        source_dag_schema_version=1,
        source_evidence_status=EvidenceStatus.LITERATURE,
        peak_source_processor_occupancy=len(primitive.logical_support),
        primitives=(primitive,),
        dependencies=(),
    )


def _primitive(
    kind: LogicalPrimitiveKind,
    support: tuple[str, ...],
    *,
    resource_state_demand: int = 0,
) -> LogicalPrimitive:
    return LogicalPrimitive(
        primitive_id=f"source::{kind.value}",
        source_node_id="source-node",
        kind=kind,
        logical_support=support,
        resource_state_demand=resource_state_demand,
        evidence_status=EvidenceStatus.LITERATURE,
    )


def test_source_x_is_an_unconditional_zero_round_pauli_frame_update() -> None:
    trace = lower_to_adaptive_pauli_measurements(
        _single_primitive_trace(_primitive(LogicalPrimitiveKind.X, ("q",)))
    )

    assert len(trace.operations) == 1
    operation = trace.operations[0]
    assert operation.kind is PbcOperationKind.PAULI_FRAME_UPDATE
    assert operation.classical_inputs == ()
    assert len(operation.frame_updates) == 1
    update = operation.frame_updates[0]
    assert update.carrier_id == "carrier:source:q"
    assert update.pauli == "X"
    assert update.parity_tokens == ()
    assert update.constant == 1


def test_cnot_exposes_exact_three_measurements_and_pauli_corrections() -> None:
    trace = lower_to_adaptive_pauli_measurements(
        _single_primitive_trace(_primitive(LogicalPrimitiveKind.CNOT, ("c", "t")))
    )

    measurements = tuple(
        operation
        for operation in trace.operations
        if operation.kind is PbcOperationKind.MEASURE_PAULI
    )
    assert tuple(operation.pauli_terms for operation in measurements) == (
        (
            "Z:carrier:source:c",
            "Z:carrier:compiler:source::cnot:cnot_scratch",
        ),
        (
            "X:carrier:compiler:source::cnot:cnot_scratch",
            "X:carrier:source:t",
        ),
        ("Z:carrier:compiler:source::cnot:cnot_scratch",),
    )
    frame = next(
        operation
        for operation in trace.operations
        if operation.kind is PbcOperationKind.PAULI_FRAME_UPDATE
    )
    assert tuple(
        (update.carrier_id, update.pauli, update.parity_tokens)
        for update in frame.frame_updates
    ) == (
        ("carrier:source:c", "Z", ("bit:source::cnot:xx",)),
        (
            "carrier:source:t",
            "X",
            ("bit:source::cnot:zz", "bit:source::cnot:z_scratch"),
        ),
    )
    assert len(trace.compiler_ancillas) == 1
    assert trace.compiler_ancillas[0].role is AncillaRole.CNOT_SCRATCH


@pytest.mark.parametrize(
    ("kind", "states", "conditional_axes"),
    (
        (LogicalPrimitiveKind.T, ("plus", "i_plus"), ("X", "Y")),
        (LogicalPrimitiveKind.T_DAGGER, ("minus_i", "plus"), ("Y", "X")),
    ),
)
def test_t_gadget_physically_removes_adaptive_s_frame(
    kind: LogicalPrimitiveKind,
    states: tuple[str, str],
    conditional_axes: tuple[str, str],
) -> None:
    trace = lower_to_adaptive_pauli_measurements(
        _single_primitive_trace(_primitive(kind, ("q",), resource_state_demand=1))
    )

    assert trace.measurement_count == 4
    assert trace.resource_state_demand == 1
    assert tuple(lifetime.role for lifetime in trace.compiler_ancillas) == (
        AncillaRole.MAGIC_T,
        AncillaRole.TELEPORT_OUTPUT,
    )
    adaptive_prepare = next(
        operation
        for operation in trace.operations
        if tuple(choice.state for choice in operation.prepared_states) == states
    )
    assert tuple(
        (choice.condition[0].token, choice.condition[0].value)
        for choice in adaptive_prepare.prepared_states
    ) == (
        (f"bit:source::{kind.value}:magic_zz", 0),
        (f"bit:source::{kind.value}:magic_zz", 1),
    )
    frame = next(
        operation
        for operation in trace.operations
        if operation.kind is PbcOperationKind.PAULI_FRAME_UPDATE
    )
    assert tuple(update.pauli for update in frame.frame_updates[:2]) == conditional_axes
    assert frame.frame_updates[-1].parity_tokens == (
        f"bit:source::{kind.value}:magic_x",
        f"bit:source::{kind.value}:correction_teleport_x",
    )
    assert trace.minimum_reusable_compiler_scratch_slots == 1


@pytest.mark.parametrize(
    ("kind", "prepared_state", "parity_axes", "correction_axes"),
    (
        (LogicalPrimitiveKind.H, "zero", ("Z", "X"), ("Z", "X")),
        (LogicalPrimitiveKind.S, "i_plus", ("Z", "Z"), ("Y", "Z")),
    ),
)
def test_single_qubit_cliffords_use_one_bit_teleportation(
    kind: LogicalPrimitiveKind,
    prepared_state: str,
    parity_axes: tuple[str, str],
    correction_axes: tuple[str, str],
) -> None:
    trace = lower_to_adaptive_pauli_measurements(
        _single_primitive_trace(_primitive(kind, ("q",)))
    )

    prepare = trace.operations[0]
    assert prepare.prepared_states[0].state == prepared_state
    measurements = tuple(
        operation
        for operation in trace.operations
        if operation.kind is PbcOperationKind.MEASURE_PAULI
    )
    assert tuple(term.split(":", maxsplit=1)[0] for term in measurements[0].pauli_terms) == (
        parity_axes
    )
    frame = next(
        operation
        for operation in trace.operations
        if operation.kind is PbcOperationKind.PAULI_FRAME_UPDATE
    )
    assert tuple(update.pauli for update in frame.frame_updates) == correction_axes
    assert dict(trace.final_carriers)["q"].endswith(AncillaRole.TELEPORT_OUTPUT.value)


@pytest.mark.parametrize("width", (2, 3, 4))
def test_full_gidney_trace_has_deterministic_scaling_and_dependencies(width: int) -> None:
    dag = load_gidney_oracle_dag(
        FIXTURE_ROOT / f"gidney_width{width}_oracle_v3.json"
    )
    trace = lower_to_adaptive_pauli_measurements(lower_gidney_phase_exact(dag))

    assert len(trace.operations) == 113 * width - 131
    assert trace.measurement_count == 53 * width - 62
    assert len(trace.compiler_ancillas) == 20 * width - 23
    assert trace.resource_state_demand == 4 * width - 4
    assert trace.peak_source_processor_occupancy == width + 1
    assert trace.minimum_serial_processor_occupancy == width + 2
    assert len(trace.topological_order()) == len(trace.operations)
    assert pbc_trace_to_data(trace)["minimum_serial_processor_occupancy"] == width + 2


def test_reference_gadget_channels_match_every_nonzero_branch() -> None:
    verification = verify_reference_gadget_channels(random_seed=20260815)

    assert verification.cnot_nonzero_branches == 88
    assert verification.h_nonzero_branches == 40
    assert verification.s_nonzero_branches == 40
    assert verification.t_nonzero_branches == 160
    assert verification.t_dagger_nonzero_branches == 160
    assert verification.maximum_frobenius_error < 1e-12
