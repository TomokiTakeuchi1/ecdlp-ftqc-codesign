"""Architecture-neutral Bell-bridge ripple-carry workload records.

The source circuits describe a logical wire dependency replaced by a Bell pair,
speculative use of one Bell half, and a destructive Bell measurement after the
producer and consumer segments have both executed.  This module records that
causally without introducing a reverse-time edge and without treating the
bridge as a memory load or store.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from importlib import import_module
from typing import Any

from ecdlp_ftqc.metadata import EvidenceStatus

np: Any = import_module("numpy")

BRIDGE_RIPPLE_SCHEMA = "ecdlp-ftqc/bell-bridge-ripple-trace"
BRIDGE_RIPPLE_SCHEMA_VERSION = 1
XU_ADDER_ARXIV = "2407.18490v1"
XU_ADDER_PDF_SHA256 = (
    "F50363822EE43C0DD0BCB4D0ACB502AA11207FC37B5175E60EADEBF892D38C05"
)
ACTIVE_VOLUME_ARXIV = "2211.15465v1"
ACTIVE_VOLUME_PDF_SHA256 = (
    "BF305E578AEFC986F4E74110EF55155E7C9711401B7D4E18BCB63BE304D2BC45"
)


class BridgeTraceError(ValueError):
    """Raised when a bridge trace or lifecycle violates its contract."""


class BridgeEventKind(str, Enum):
    """Source-level actions exposed by the bounded bridge-adder workload."""

    BELL_PAIR_PREPARE = "bell_pair_prepare"
    SEGMENT_COMPUTE = "segment_compute"
    BELL_MEASURE_XX = "bell_measure_xx"
    BELL_MEASURE_ZZ = "bell_measure_zz"
    CARRIER_REBIND = "carrier_rebind"
    REACTIVE_MEASUREMENT = "reactive_measurement"
    OUTPUT_FINALIZE = "output_finalize"


class BridgeDependencyKind(str, Enum):
    """Why one bridge workload event precedes another."""

    QUANTUM_ORDER = "quantum_order"
    ENTANGLEMENT_READY = "entanglement_ready"
    BELL_OUTCOME = "bell_outcome"
    CLASSICAL_REACTION = "classical_reaction"


@dataclass(frozen=True, slots=True)
class BridgeSourceReference:
    """Pinned literature provenance for the macro circuit."""

    xu_arxiv: str = XU_ADDER_ARXIV
    xu_pdf_sha256: str = XU_ADDER_PDF_SHA256
    xu_figure: str = "Figure 6"
    active_volume_arxiv: str = ACTIVE_VOLUME_ARXIV
    active_volume_pdf_sha256: str = ACTIVE_VOLUME_PDF_SHA256
    active_volume_figures: tuple[str, ...] = ("Figure 10", "Figure 16", "Figure 24")
    semantic_evidence_status: EvidenceStatus = EvidenceStatus.LITERATURE

    def __post_init__(self) -> None:
        for digest in (self.xu_pdf_sha256, self.active_volume_pdf_sha256):
            if len(digest) != 64 or any(
                character not in "0123456789abcdefABCDEF" for character in digest
            ):
                raise BridgeTraceError("source PDF hash must be SHA-256")


@dataclass(frozen=True, slots=True)
class BridgeEvent:
    """One source-level event in the bridge ripple workload."""

    event_id: str
    kind: BridgeEventKind
    logical_support: tuple[str, ...]
    segment_index: int | None = None
    bridge_index: int | None = None
    classical_inputs: tuple[str, ...] = ()
    classical_outputs: tuple[str, ...] = ()
    resource_state_demand: int = 0
    semantic_evidence_status: EvidenceStatus = EvidenceStatus.LITERATURE

    def __post_init__(self) -> None:
        if not self.event_id:
            raise BridgeTraceError("event ID cannot be empty")
        for field_name in (
            "logical_support",
            "classical_inputs",
            "classical_outputs",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise BridgeTraceError(f"{field_name} cannot contain duplicates")
        if self.segment_index is not None and self.segment_index < 0:
            raise BridgeTraceError("segment index cannot be negative")
        if self.bridge_index is not None and self.bridge_index < 0:
            raise BridgeTraceError("bridge index cannot be negative")
        if self.resource_state_demand < 0:
            raise BridgeTraceError("resource-state demand cannot be negative")


@dataclass(frozen=True, slots=True)
class BridgeDependency:
    """One causal dependency between source-level bridge events."""

    predecessor: str
    successor: str
    kind: BridgeDependencyKind
    reason: str

    def __post_init__(self) -> None:
        if not self.predecessor or not self.successor or not self.reason:
            raise BridgeTraceError("dependency fields cannot be empty")
        if self.predecessor == self.successor:
            raise BridgeTraceError("self dependencies are not allowed")


@dataclass(frozen=True, slots=True)
class CarryBridge:
    """Lifecycle binding for one carry connection between adjacent segments."""

    bridge_id: str
    bridge_index: int
    sender_segment: int
    receiver_segment: int
    output_carrier: str
    receiver_carrier: str
    stored_half: str
    prepare_event_id: str
    xx_event_id: str
    zz_event_id: str
    rebind_event_id: str

    def __post_init__(self) -> None:
        if self.receiver_segment != self.sender_segment + 1:
            raise BridgeTraceError("a carry bridge must connect adjacent segments")
        if self.bridge_index != self.sender_segment:
            raise BridgeTraceError("bridge index must equal its sender segment")
        carriers = (self.output_carrier, self.receiver_carrier, self.stored_half)
        if len(carriers) != len(set(carriers)):
            raise BridgeTraceError("bridge carriers must be distinct")


@dataclass(frozen=True, slots=True)
class BridgeRippleTrace:
    """Validated macro trace for the Xu/Active-Volume bridge adder."""

    trace_id: str
    width: int
    source: BridgeSourceReference
    events: tuple[BridgeEvent, ...]
    dependencies: tuple[BridgeDependency, ...]
    bridges: tuple[CarryBridge, ...]
    encoded_patch_families: tuple[str, ...] = ("a", "b", "c", "d", "e")
    reactive_ancilla_patch_count: int = 6
    schema: str = BRIDGE_RIPPLE_SCHEMA
    schema_version: int = BRIDGE_RIPPLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise BridgeTraceError("trace ID cannot be empty")
        if self.width < 2:
            raise BridgeTraceError("bridge ripple width must be at least two")
        if self.schema != BRIDGE_RIPPLE_SCHEMA:
            raise BridgeTraceError("unsupported bridge-ripple schema")
        if self.schema_version != BRIDGE_RIPPLE_SCHEMA_VERSION:
            raise BridgeTraceError("unsupported bridge-ripple schema version")
        if self.encoded_patch_families != ("a", "b", "c", "d", "e"):
            raise BridgeTraceError("the source construction requires five patch families")
        if self.reactive_ancilla_patch_count != 6:
            raise BridgeTraceError("the source construction reports six ancilla patches")
        self._validate()

    @property
    def temporary_and_count(self) -> int:
        return self.width - 1

    @property
    def bridge_count(self) -> int:
        return len(self.bridges)

    @property
    def source_logical_carrier_slots(self) -> int:
        """Logical coordinates across five patches, not one-block capacity."""

        return len(self.encoded_patch_families) * self.width

    @property
    def sequential_segment_depth_reference(self) -> int:
        return self.width

    @property
    def bridge_segment_depth(self) -> int:
        return 1

    def event_by_id(self) -> dict[str, BridgeEvent]:
        return {event.event_id: event for event in self.events}

    def topological_order(self) -> tuple[str, ...]:
        event_ids = tuple(event.event_id for event in self.events)
        position = {event_id: index for index, event_id in enumerate(event_ids)}
        successors: dict[str, list[str]] = defaultdict(list)
        indegree = {event_id: 0 for event_id in event_ids}
        for dependency in self.dependencies:
            successors[dependency.predecessor].append(dependency.successor)
            indegree[dependency.successor] += 1
        queue = deque(
            event_id for event_id in event_ids if indegree[event_id] == 0
        )
        order: list[str] = []
        while queue:
            event_id = queue.popleft()
            order.append(event_id)
            for successor in sorted(
                successors[event_id], key=position.__getitem__
            ):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    queue.append(successor)
        if len(order) != len(event_ids):
            raise BridgeTraceError("bridge trace must be acyclic")
        return tuple(order)

    def _validate(self) -> None:
        event_ids = tuple(event.event_id for event in self.events)
        if len(event_ids) != len(set(event_ids)):
            raise BridgeTraceError("event IDs must be unique")
        known = set(event_ids)
        dependency_keys = tuple(
            (
                dependency.predecessor,
                dependency.successor,
                dependency.kind,
                dependency.reason,
            )
            for dependency in self.dependencies
        )
        if len(dependency_keys) != len(set(dependency_keys)):
            raise BridgeTraceError("dependencies must be unique")
        for dependency in self.dependencies:
            if dependency.predecessor not in known or dependency.successor not in known:
                raise BridgeTraceError("dependency references an unknown event")
        if len(self.bridges) != self.width - 1:
            raise BridgeTraceError("an n-bit bridge adder requires n-1 carry bridges")
        if len({bridge.bridge_id for bridge in self.bridges}) != len(self.bridges):
            raise BridgeTraceError("bridge IDs must be unique")
        events = self.event_by_id()
        expected_segments = set(range(self.width))
        actual_segments = {
            event.segment_index
            for event in self.events
            if event.kind is BridgeEventKind.SEGMENT_COMPUTE
        }
        if actual_segments != expected_segments:
            raise BridgeTraceError("trace must contain exactly one event per segment")
        expected_reactions = set(range(self.width - 1))
        actual_reactions = {
            event.segment_index
            for event in self.events
            if event.kind is BridgeEventKind.REACTIVE_MEASUREMENT
        }
        if actual_reactions != expected_reactions:
            raise BridgeTraceError(
                "trace must contain one sequential reaction per temporary AND"
            )
        for bridge in self.bridges:
            if bridge.bridge_index >= self.width - 1:
                raise BridgeTraceError("bridge index is outside the adder")
            expected_kinds = {
                bridge.prepare_event_id: BridgeEventKind.BELL_PAIR_PREPARE,
                bridge.xx_event_id: BridgeEventKind.BELL_MEASURE_XX,
                bridge.zz_event_id: BridgeEventKind.BELL_MEASURE_ZZ,
                bridge.rebind_event_id: BridgeEventKind.CARRIER_REBIND,
            }
            for event_id, kind in expected_kinds.items():
                if event_id not in events or events[event_id].kind is not kind:
                    raise BridgeTraceError("bridge lifecycle references a wrong event kind")
        self.topological_order()


@dataclass(frozen=True, slots=True)
class BridgeReplaySummary:
    """Independent lifecycle replay outcome."""

    event_count: int
    bridge_count: int
    peak_live_bridge_carriers: int
    final_live_bridge_carriers: int
    all_bridges_rebound: bool


@dataclass(slots=True)
class _MutableBridgeState:
    prepared: bool = False
    receiver_used: bool = False
    sender_output: bool = False
    measured_xx: bool = False
    measured_zz: bool = False
    rebound: bool = False


def build_bridge_ripple_trace(width: int) -> BridgeRippleTrace:
    """Build the source-level n-segment, n-1-bridge workload."""

    if isinstance(width, bool) or not isinstance(width, int) or width < 2:
        raise BridgeTraceError("width must be an integer of at least two")

    events: list[BridgeEvent] = []
    dependencies: list[BridgeDependency] = []
    bridges: list[CarryBridge] = []

    for index in range(width - 1):
        prepare_id = f"bridge:{index}:prepare"
        xx_id = f"bridge:{index}:measure_xx"
        zz_id = f"bridge:{index}:measure_zz"
        rebind_id = f"bridge:{index}:rebind"
        output_carrier = f"d:{index}"
        receiver_carrier = f"c:{index + 1}"
        stored_half = f"e:{index + 1}"
        events.append(
            BridgeEvent(
                event_id=prepare_id,
                kind=BridgeEventKind.BELL_PAIR_PREPARE,
                bridge_index=index,
                logical_support=(receiver_carrier, stored_half),
            )
        )
        bridges.append(
            CarryBridge(
                bridge_id=f"carry-bridge:{index}->{index + 1}",
                bridge_index=index,
                sender_segment=index,
                receiver_segment=index + 1,
                output_carrier=output_carrier,
                receiver_carrier=receiver_carrier,
                stored_half=stored_half,
                prepare_event_id=prepare_id,
                xx_event_id=xx_id,
                zz_event_id=zz_id,
                rebind_event_id=rebind_id,
            )
        )

    for index in range(width):
        support = [f"a:{index}", f"b:{index}"]
        if index > 0:
            support.append(f"c:{index}")
        if index < width - 1:
            support.append(f"d:{index}")
        segment_id = f"segment:{index}:compute"
        events.append(
            BridgeEvent(
                event_id=segment_id,
                kind=BridgeEventKind.SEGMENT_COMPUTE,
                segment_index=index,
                logical_support=tuple(support),
                resource_state_demand=1 if index < width - 1 else 0,
            )
        )
        if index > 0:
            incoming = bridges[index - 1]
            dependencies.append(
                BridgeDependency(
                    predecessor=incoming.prepare_event_id,
                    successor=segment_id,
                    kind=BridgeDependencyKind.ENTANGLEMENT_READY,
                    reason=(
                        f"receiver segment {index} speculatively uses "
                        f"{incoming.receiver_carrier}"
                    ),
                )
            )

    for bridge in bridges:
        sender_id = f"segment:{bridge.sender_segment}:compute"
        receiver_id = f"segment:{bridge.receiver_segment}:compute"
        xx_bit = f"outcome:bridge:{bridge.bridge_index}:xx"
        zz_bit = f"outcome:bridge:{bridge.bridge_index}:zz"
        for event_id, kind, bit in (
            (bridge.xx_event_id, BridgeEventKind.BELL_MEASURE_XX, xx_bit),
            (bridge.zz_event_id, BridgeEventKind.BELL_MEASURE_ZZ, zz_bit),
        ):
            events.append(
                BridgeEvent(
                    event_id=event_id,
                    kind=kind,
                    bridge_index=bridge.bridge_index,
                    logical_support=(bridge.output_carrier, bridge.stored_half),
                    classical_outputs=(bit,),
                )
            )
            dependencies.extend(
                (
                    BridgeDependency(
                        predecessor=bridge.prepare_event_id,
                        successor=event_id,
                        kind=BridgeDependencyKind.ENTANGLEMENT_READY,
                        reason=f"stored Bell half {bridge.stored_half} must exist",
                    ),
                    BridgeDependency(
                        predecessor=sender_id,
                        successor=event_id,
                        kind=BridgeDependencyKind.QUANTUM_ORDER,
                        reason=f"sender output {bridge.output_carrier} must exist",
                    ),
                )
            )
        events.append(
            BridgeEvent(
                event_id=bridge.rebind_event_id,
                kind=BridgeEventKind.CARRIER_REBIND,
                bridge_index=bridge.bridge_index,
                logical_support=(bridge.receiver_carrier,),
                classical_inputs=(xx_bit, zz_bit),
            )
        )
        dependencies.extend(
            (
                BridgeDependency(
                    predecessor=bridge.xx_event_id,
                    successor=bridge.rebind_event_id,
                    kind=BridgeDependencyKind.BELL_OUTCOME,
                    reason=f"XX outcome {xx_bit} validates the receiver carrier",
                ),
                BridgeDependency(
                    predecessor=bridge.zz_event_id,
                    successor=bridge.rebind_event_id,
                    kind=BridgeDependencyKind.BELL_OUTCOME,
                    reason=f"ZZ outcome {zz_bit} validates the receiver carrier",
                ),
                BridgeDependency(
                    predecessor=receiver_id,
                    successor=bridge.rebind_event_id,
                    kind=BridgeDependencyKind.QUANTUM_ORDER,
                    reason="receiver segment completes before deferred carrier validation",
                ),
            )
        )

    for index, bridge in enumerate(bridges):
        reaction_id = f"reaction:{index}:measure"
        reaction_input = f"outcome:reaction:{index - 1}" if index else None
        inputs = [
            f"outcome:bridge:{index}:xx",
            f"outcome:bridge:{index}:zz",
        ]
        if reaction_input is not None:
            inputs.append(reaction_input)
        events.append(
            BridgeEvent(
                event_id=reaction_id,
                kind=BridgeEventKind.REACTIVE_MEASUREMENT,
                segment_index=index,
                logical_support=(f"a:{index}", f"b:{index}"),
                classical_inputs=tuple(inputs),
                classical_outputs=(f"outcome:reaction:{index}",),
            )
        )
        dependencies.extend(
            (
                BridgeDependency(
                    predecessor=bridge.rebind_event_id,
                    successor=reaction_id,
                    kind=BridgeDependencyKind.BELL_OUTCOME,
                    reason="bridge outcomes select the deferred reactive basis",
                ),
                BridgeDependency(
                    predecessor=f"segment:{index}:compute",
                    successor=reaction_id,
                    kind=BridgeDependencyKind.QUANTUM_ORDER,
                    reason="temporary-AND compute precedes its reactive uncompute",
                ),
            )
        )
        if index:
            dependencies.append(
                BridgeDependency(
                    predecessor=f"reaction:{index - 1}:measure",
                    successor=reaction_id,
                    kind=BridgeDependencyKind.CLASSICAL_REACTION,
                    reason="the next reactive basis depends on the previous outcome",
                )
            )

    final_id = "output:finalize"
    events.append(
        BridgeEvent(
            event_id=final_id,
            kind=BridgeEventKind.OUTPUT_FINALIZE,
            logical_support=tuple(
                value
                for index in range(width)
                for value in (f"a:{index}", f"b:{index}")
            ),
        )
    )
    dependencies.extend(
        (
            BridgeDependency(
                predecessor=f"segment:{width - 1}:compute",
                successor=final_id,
                kind=BridgeDependencyKind.QUANTUM_ORDER,
                reason="last bit segment must complete",
            ),
            BridgeDependency(
                predecessor=f"reaction:{width - 2}:measure",
                successor=final_id,
                kind=BridgeDependencyKind.CLASSICAL_REACTION,
                reason="all deferred reactive measurements must complete",
            ),
        )
    )

    return BridgeRippleTrace(
        trace_id=f"bell-bridge-gidney-ripple-width-{width}",
        width=width,
        source=BridgeSourceReference(),
        events=tuple(events),
        dependencies=tuple(dependencies),
        bridges=tuple(bridges),
    )


def replay_bridge_lifecycle(
    trace: BridgeRippleTrace,
    event_order: Iterable[str] | None = None,
) -> BridgeReplaySummary:
    """Replay bridge ownership without trusting the trace builder bookkeeping."""

    events = trace.event_by_id()
    order = tuple(event_order) if event_order is not None else trace.topological_order()
    if len(order) != len(events) or set(order) != set(events):
        raise BridgeTraceError("replay order must contain every event exactly once")
    bridge_by_index = {bridge.bridge_index: bridge for bridge in trace.bridges}
    states = {index: _MutableBridgeState() for index in bridge_by_index}
    alive: set[str] = set()
    peak = 0
    reaction_completed: set[int] = set()

    for event_id in order:
        event = events[event_id]
        if event.kind is BridgeEventKind.BELL_PAIR_PREPARE:
            assert event.bridge_index is not None
            state = states[event.bridge_index]
            bridge = bridge_by_index[event.bridge_index]
            if state.prepared:
                raise BridgeTraceError("Bell pair prepared twice")
            if bridge.receiver_carrier in alive or bridge.stored_half in alive:
                raise BridgeTraceError("Bell preparation would create a free copy")
            state.prepared = True
            alive.update((bridge.receiver_carrier, bridge.stored_half))
        elif event.kind is BridgeEventKind.SEGMENT_COMPUTE:
            assert event.segment_index is not None
            index = event.segment_index
            if index > 0:
                incoming = bridge_by_index[index - 1]
                state = states[index - 1]
                if not state.prepared or incoming.receiver_carrier not in alive:
                    raise BridgeTraceError("receiver used before Bell preparation")
                if state.receiver_used:
                    raise BridgeTraceError("receiver carrier used twice")
                state.receiver_used = True
            if index < trace.width - 1:
                outgoing = bridge_by_index[index]
                state = states[index]
                if state.sender_output or outgoing.output_carrier in alive:
                    raise BridgeTraceError("sender output created twice")
                state.sender_output = True
                alive.add(outgoing.output_carrier)
        elif event.kind in {
            BridgeEventKind.BELL_MEASURE_XX,
            BridgeEventKind.BELL_MEASURE_ZZ,
        }:
            assert event.bridge_index is not None
            bridge = bridge_by_index[event.bridge_index]
            state = states[event.bridge_index]
            if (
                not state.prepared
                or not state.sender_output
                or bridge.output_carrier not in alive
                or bridge.stored_half not in alive
            ):
                raise BridgeTraceError("Bell measurement lacks live producer/stored halves")
            if event.kind is BridgeEventKind.BELL_MEASURE_XX:
                if state.measured_xx:
                    raise BridgeTraceError("XX Bell component measured twice")
                state.measured_xx = True
            else:
                if state.measured_zz:
                    raise BridgeTraceError("ZZ Bell component measured twice")
                state.measured_zz = True
            if state.measured_xx and state.measured_zz:
                alive.remove(bridge.output_carrier)
                alive.remove(bridge.stored_half)
        elif event.kind is BridgeEventKind.CARRIER_REBIND:
            assert event.bridge_index is not None
            bridge = bridge_by_index[event.bridge_index]
            state = states[event.bridge_index]
            if (
                not state.measured_xx
                or not state.measured_zz
                or not state.receiver_used
                or bridge.receiver_carrier not in alive
            ):
                raise BridgeTraceError("carrier rebound before bridge completion")
            if state.rebound:
                raise BridgeTraceError("carrier rebound twice")
            state.rebound = True
        elif event.kind is BridgeEventKind.REACTIVE_MEASUREMENT:
            assert event.segment_index is not None
            index = event.segment_index
            if not states[index].rebound:
                raise BridgeTraceError("reactive measurement preceded bridge rebind")
            if index and index - 1 not in reaction_completed:
                raise BridgeTraceError("reactive measurement chain was reordered")
            reaction_completed.add(index)
        elif event.kind is BridgeEventKind.OUTPUT_FINALIZE:
            if not all(state.rebound for state in states.values()):
                raise BridgeTraceError("output finalized with an open bridge")
            if reaction_completed != set(range(trace.width - 1)):
                raise BridgeTraceError("output finalized before all reactions")
            for bridge in trace.bridges:
                if bridge.receiver_carrier not in alive:
                    raise BridgeTraceError("rebound receiver carrier is missing")
                alive.remove(bridge.receiver_carrier)
        peak = max(peak, len(alive))

    if alive:
        raise BridgeTraceError("bridge replay ended with live bridge carriers")
    return BridgeReplaySummary(
        event_count=len(order),
        bridge_count=len(trace.bridges),
        peak_live_bridge_carriers=peak,
        final_live_bridge_carriers=0,
        all_bridges_rebound=all(state.rebound for state in states.values()),
    )


@dataclass(frozen=True, slots=True)
class BridgeBasisProjection:
    """Classical-basis projection of the intended in-place addition channel."""

    width: int
    input_register: int
    target_register: int
    output_input_register: int
    output_target_register: int
    carries: tuple[int, ...]


def evaluate_bridge_basis_projection(
    width: int, input_register: int, target_register: int
) -> BridgeBasisProjection:
    """Evaluate the full-adder truth-table projection, not a phase proof."""

    if width < 2:
        raise BridgeTraceError("width must be at least two")
    limit = 1 << width
    if not 0 <= input_register < limit or not 0 <= target_register < limit:
        raise BridgeTraceError("register value is outside the declared width")
    carry = 0
    output = 0
    carries = [carry]
    for index in range(width):
        a_bit = (input_register >> index) & 1
        b_bit = (target_register >> index) & 1
        output |= (a_bit ^ b_bit ^ carry) << index
        carry = (a_bit & b_bit) | (carry & (a_bit ^ b_bit))
        carries.append(carry)
    return BridgeBasisProjection(
        width=width,
        input_register=input_register,
        target_register=target_register,
        output_input_register=input_register,
        output_target_register=output,
        carries=tuple(carries),
    )


@dataclass(frozen=True, slots=True)
class BellTeleportationVerification:
    """Seeded branchwise check of the generic one-qubit bridge identity."""

    seed: int
    sample_count: int
    branch_count: int
    maximum_frobenius_error: float
    minimum_branch_probability: float
    passed: bool


def _apply_cnot_q_to_e(state: np.ndarray) -> np.ndarray:
    result = np.zeros_like(state)
    for basis, amplitude in enumerate(state):
        q_bit = (basis >> 2) & 1
        e_bit = (basis >> 1) & 1
        c_bit = basis & 1
        mapped_e = e_bit ^ q_bit
        mapped = (q_bit << 2) | (mapped_e << 1) | c_bit
        result[mapped] += amplitude
    return result


def verify_generic_bell_bridge_identity(
    *, seed: int = 20260824, sample_count: int = 16, tolerance: float = 1e-12
) -> BellTeleportationVerification:
    """Check all four Bell branches on seeded arbitrary one-qubit states."""

    if sample_count < 1 or tolerance <= 0:
        raise BridgeTraceError("verification parameters must be positive")
    rng = np.random.default_rng(seed)
    identity = np.eye(2, dtype=np.complex128)
    x_gate = np.array([[0, 1], [1, 0]], dtype=np.complex128)
    z_gate = np.array([[1, 0], [0, -1]], dtype=np.complex128)
    h_gate = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
    bell = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
    h_on_q = np.kron(np.kron(h_gate, identity), identity)
    maximum_error = 0.0
    minimum_probability = 1.0
    branches = 0

    for _ in range(sample_count):
        psi = rng.normal(size=2) + 1j * rng.normal(size=2)
        psi = psi / np.linalg.norm(psi)
        state = h_on_q @ _apply_cnot_q_to_e(np.kron(psi, bell))
        tensor = state.reshape((2, 2, 2))
        target_density = np.outer(psi, psi.conj())
        for measured_q in range(2):
            for measured_e in range(2):
                branch = tensor[measured_q, measured_e, :]
                probability = float(np.vdot(branch, branch).real)
                minimum_probability = min(minimum_probability, probability)
                if probability <= 0:
                    raise BridgeTraceError("teleportation branch has zero probability")
                branch = branch / np.sqrt(probability)
                correction = (
                    (z_gate if measured_q else identity)
                    @ (x_gate if measured_e else identity)
                )
                corrected = correction @ branch
                density = np.outer(corrected, corrected.conj())
                maximum_error = max(
                    maximum_error,
                    float(np.linalg.norm(density - target_density, ord="fro")),
                )
                branches += 1
    return BellTeleportationVerification(
        seed=seed,
        sample_count=sample_count,
        branch_count=branches,
        maximum_frobenius_error=maximum_error,
        minimum_branch_probability=minimum_probability,
        passed=maximum_error <= tolerance,
    )


def bridge_trace_to_data(trace: BridgeRippleTrace) -> dict[str, Any]:
    """Serialize a trace deterministically."""

    return {
        "bridges": [
            {
                "bridge_id": bridge.bridge_id,
                "bridge_index": bridge.bridge_index,
                "output_carrier": bridge.output_carrier,
                "prepare_event_id": bridge.prepare_event_id,
                "receiver_carrier": bridge.receiver_carrier,
                "receiver_segment": bridge.receiver_segment,
                "rebind_event_id": bridge.rebind_event_id,
                "sender_segment": bridge.sender_segment,
                "stored_half": bridge.stored_half,
                "xx_event_id": bridge.xx_event_id,
                "zz_event_id": bridge.zz_event_id,
            }
            for bridge in trace.bridges
        ],
        "dependencies": [
            {
                "kind": dependency.kind.value,
                "predecessor": dependency.predecessor,
                "reason": dependency.reason,
                "successor": dependency.successor,
            }
            for dependency in trace.dependencies
        ],
        "encoded_patch_families": list(trace.encoded_patch_families),
        "events": [
            {
                "bridge_index": event.bridge_index,
                "classical_inputs": list(event.classical_inputs),
                "classical_outputs": list(event.classical_outputs),
                "event_id": event.event_id,
                "kind": event.kind.value,
                "logical_support": list(event.logical_support),
                "resource_state_demand": event.resource_state_demand,
                "segment_index": event.segment_index,
                "semantic_evidence_status": event.semantic_evidence_status.value,
            }
            for event in trace.events
        ],
        "reactive_ancilla_patch_count": trace.reactive_ancilla_patch_count,
        "schema": trace.schema,
        "schema_version": trace.schema_version,
        "source": {
            "active_volume_arxiv": trace.source.active_volume_arxiv,
            "active_volume_figures": list(trace.source.active_volume_figures),
            "active_volume_pdf_sha256": trace.source.active_volume_pdf_sha256,
            "semantic_evidence_status": trace.source.semantic_evidence_status.value,
            "xu_arxiv": trace.source.xu_arxiv,
            "xu_figure": trace.source.xu_figure,
            "xu_pdf_sha256": trace.source.xu_pdf_sha256,
        },
        "trace_id": trace.trace_id,
        "width": trace.width,
    }


def dumps_bridge_trace(trace: BridgeRippleTrace) -> str:
    return json.dumps(bridge_trace_to_data(trace), indent=2, sort_keys=True) + "\n"
