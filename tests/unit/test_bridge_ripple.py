from __future__ import annotations

import json

import pytest

from ecdlp_ftqc.circuits import (
    ACTIVE_VOLUME_ARXIV,
    BRIDGE_RIPPLE_SCHEMA,
    XU_ADDER_ARXIV,
    BridgeEventKind,
    BridgeTraceError,
    build_bridge_ripple_trace,
    dumps_bridge_trace,
    evaluate_bridge_basis_projection,
    replay_bridge_lifecycle,
    verify_generic_bell_bridge_identity,
)


@pytest.mark.parametrize("width", [2, 3, 4, 11, 32])
def test_trace_has_source_pinned_segment_and_bridge_counts(width: int) -> None:
    trace = build_bridge_ripple_trace(width)

    assert trace.schema == BRIDGE_RIPPLE_SCHEMA
    assert trace.source.xu_arxiv == XU_ADDER_ARXIV
    assert trace.source.active_volume_arxiv == ACTIVE_VOLUME_ARXIV
    assert trace.temporary_and_count == width - 1
    assert trace.bridge_count == width - 1
    assert trace.source_logical_carrier_slots == 5 * width
    assert trace.sequential_segment_depth_reference == width
    assert trace.bridge_segment_depth == 1
    assert (
        sum(
            event.kind is BridgeEventKind.SEGMENT_COMPUTE
            for event in trace.events
        )
        == width
    )
    assert (
        sum(
            event.kind is BridgeEventKind.REACTIVE_MEASUREMENT
            for event in trace.events
        )
        == width - 1
    )
    assert len(trace.topological_order()) == len(trace.events)


@pytest.mark.parametrize("width", [2, 3, 4])
def test_basis_projection_matches_modular_addition_exhaustively(width: int) -> None:
    limit = 1 << width
    for input_register in range(limit):
        for target_register in range(limit):
            result = evaluate_bridge_basis_projection(
                width, input_register, target_register
            )
            assert result.output_input_register == input_register
            assert result.output_target_register == (
                input_register + target_register
            ) % limit
            assert len(result.carries) == width + 1


def test_generic_bell_bridge_identity_matches_every_seeded_branch() -> None:
    verification = verify_generic_bell_bridge_identity(
        seed=20260824, sample_count=32
    )

    assert verification.passed
    assert verification.branch_count == 128
    assert verification.maximum_frobenius_error < 1e-12
    assert verification.minimum_branch_probability == pytest.approx(0.25)


@pytest.mark.parametrize("width", [2, 4, 32])
def test_independent_replay_closes_every_bridge_without_free_copies(
    width: int,
) -> None:
    trace = build_bridge_ripple_trace(width)
    summary = replay_bridge_lifecycle(trace)

    assert summary.bridge_count == width - 1
    assert summary.peak_live_bridge_carriers == 3 * (width - 1)
    assert summary.final_live_bridge_carriers == 0
    assert summary.all_bridges_rebound


def test_replay_rejects_receiver_use_before_bell_pair_preparation() -> None:
    trace = build_bridge_ripple_trace(3)
    order = list(trace.topological_order())
    receiver = "segment:1:compute"
    order.remove(receiver)
    order.insert(0, receiver)

    with pytest.raises(BridgeTraceError, match="before Bell preparation"):
        replay_bridge_lifecycle(trace, order)


def test_replay_rejects_rebind_before_bell_measurement() -> None:
    trace = build_bridge_ripple_trace(3)
    order = list(trace.topological_order())
    rebind = "bridge:0:rebind"
    order.remove(rebind)
    sender_position = order.index("segment:0:compute")
    order.insert(sender_position + 1, rebind)

    with pytest.raises(BridgeTraceError, match="before bridge completion"):
        replay_bridge_lifecycle(trace, order)


def test_serialization_is_deterministic_and_qualified() -> None:
    trace = build_bridge_ripple_trace(4)

    first = dumps_bridge_trace(trace)
    second = dumps_bridge_trace(trace)
    data = json.loads(first)

    assert first == second
    assert data["source"]["semantic_evidence_status"] == "LITERATURE"
    assert data["encoded_patch_families"] == ["a", "b", "c", "d", "e"]
    assert data["reactive_ancilla_patch_count"] == 6
