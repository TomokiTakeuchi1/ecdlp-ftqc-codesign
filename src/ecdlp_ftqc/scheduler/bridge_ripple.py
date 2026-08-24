"""Deterministic resource sensitivity for the Bell-bridge ripple workload."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ecdlp_ftqc.circuits import (
    BridgeEvent,
    BridgeEventKind,
    BridgeReplaySummary,
    BridgeRippleTrace,
    BridgeTraceError,
    replay_bridge_lifecycle,
)
from ecdlp_ftqc.metadata import EvidenceStatus

BRIDGE_TIMING_SCHEMA = "ecdlp-ftqc/bridge-ripple-timing-config"
BRIDGE_TIMING_SCHEMA_VERSION = 1
BRIDGE_SCHEDULE_POLICY = "deterministic_reserved_exact_ten_xx_v1"
NORMALIZED_SENSITIVITY_UNIT = "normalized_sensitivity_step"


class UnsupportedBridgeTimingError(ValueError):
    """Raised when strict scheduling would consume unresolved bridge timing."""


class BridgeScheduleError(ValueError):
    """Raised when a bridge schedule violates its independent contract."""


@dataclass(frozen=True, slots=True)
class BridgeTimingConfig:
    """Explicit resource lanes and unitless sensitivity durations."""

    configuration_id: str
    bell_pair_lanes: int
    segment_lanes: int
    bell_measurement_lanes: int
    reactive_measurement_lanes: int
    bell_pair_prepare_steps: int
    segment_compute_steps: int
    bell_component_steps: int
    high_rate_xx_batch_steps: int
    reactive_measurement_steps: int
    high_rate_xx_batch_size: int
    timing_evidence_status: EvidenceStatus
    source_note: str
    time_unit: str = NORMALIZED_SENSITIVITY_UNIT
    policy: str = BRIDGE_SCHEDULE_POLICY
    schema: str = BRIDGE_TIMING_SCHEMA
    schema_version: int = BRIDGE_TIMING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.configuration_id or not self.source_note:
            raise ValueError("bridge timing provenance cannot be empty")
        for name, value, minimum in (
            ("bell_pair_lanes", self.bell_pair_lanes, 1),
            ("segment_lanes", self.segment_lanes, 1),
            ("bell_measurement_lanes", self.bell_measurement_lanes, 1),
            ("reactive_measurement_lanes", self.reactive_measurement_lanes, 1),
            ("bell_pair_prepare_steps", self.bell_pair_prepare_steps, 0),
            ("segment_compute_steps", self.segment_compute_steps, 0),
            ("bell_component_steps", self.bell_component_steps, 0),
            ("high_rate_xx_batch_steps", self.high_rate_xx_batch_steps, 0),
            ("reactive_measurement_steps", self.reactive_measurement_steps, 0),
            ("high_rate_xx_batch_size", self.high_rate_xx_batch_size, 2),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer of at least {minimum}")
        if self.reactive_measurement_lanes != 1:
            raise ValueError("source-dependent reactive measurements require one lane")
        if self.high_rate_xx_batch_size != 10:
            raise ValueError("only the source-supported exact-ten-XX rule is admitted")
        if self.time_unit != NORMALIZED_SENSITIVITY_UNIT:
            raise ValueError("bridge timing must remain a normalized sensitivity unit")
        if self.policy != BRIDGE_SCHEDULE_POLICY:
            raise ValueError("unsupported bridge scheduling policy")
        if self.schema != BRIDGE_TIMING_SCHEMA:
            raise ValueError("unsupported bridge timing schema")
        if self.schema_version != BRIDGE_TIMING_SCHEMA_VERSION:
            raise ValueError("unsupported bridge timing schema version")


@dataclass(frozen=True, slots=True)
class ScheduledBridgeEvent:
    """One scheduled source event or exact-ten XX batch."""

    scheduled_id: str
    source_event_ids: tuple[str, ...]
    implementation: str
    start_step: int
    end_step: int
    logical_support: tuple[str, ...]
    exclusive_resource: str
    resource_lane: int
    dependency_ready_step: int
    carrier_ready_step: int
    resource_ready_step: int
    timing_evidence_status: EvidenceStatus

    @property
    def duration_steps(self) -> int:
        return self.end_step - self.start_step

    @property
    def primary_bottleneck(self) -> str:
        candidates = (
            ("dependency", self.dependency_ready_step),
            ("carrier", self.carrier_ready_step),
            ("exclusive_resource", self.resource_ready_step),
        )
        return max(candidates, key=lambda item: (item[1], -candidates.index(item)))[0]


@dataclass(frozen=True, slots=True)
class BridgeRippleSchedule:
    """Qualified deterministic schedule for one bridge workload."""

    trace_id: str
    configuration_id: str
    allow_check_assumptions: bool
    high_rate_enabled: bool
    time_unit: str
    policy: str
    algorithmic_critical_path_steps: int
    scheduled_steps: int
    eligible_xx_measurements: int
    high_rate_batch_count: int
    high_rate_operation_count: int
    total_resource_state_demand: int
    peak_resource_state_demand_per_step: int
    peak_live_bridge_carriers: int
    source_logical_carrier_slots: int
    encoded_patch_family_count: int
    reactive_ancilla_patch_count: int
    timing_evidence_status: EvidenceStatus
    events: tuple[ScheduledBridgeEvent, ...]
    replay_summary: BridgeReplaySummary

    @property
    def strict_executable(self) -> bool:
        return self.timing_evidence_status is not EvidenceStatus.CHECK

    @property
    def implementation_counts(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        for event in self.events:
            counts[event.implementation] += len(event.source_event_ids)
        return counts

    @property
    def primary_bottleneck_counts(self) -> Counter[str]:
        return Counter(event.primary_bottleneck for event in self.events)


@dataclass(frozen=True, slots=True)
class _Candidate:
    source_events: tuple[BridgeEvent, ...]
    implementation: str
    start_step: int
    end_step: int
    logical_support: tuple[str, ...]
    exclusive_resource: str
    resource_lane: int
    dependency_ready_step: int
    carrier_ready_step: int
    resource_ready_step: int


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{path} must be a mapping")
    return value


def _required(obj: Mapping[str, object], key: str, path: str) -> object:
    if key not in obj:
        raise ValueError(f"{path}.{key} is required")
    return obj[key]


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a nonempty string")
    return value


def _integer(value: object, path: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{path} must be an integer of at least {minimum}")
    return value


def load_bridge_timing_config(path: Path) -> BridgeTimingConfig:
    """Load a fail-closed normalized bridge sensitivity configuration."""

    try:
        root = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "$")
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load bridge timing config {path}: {exc}") from exc
    lanes = _mapping(_required(root, "lanes", "$"), "$.lanes")
    durations = _mapping(_required(root, "durations", "$"), "$.durations")
    high_rate = _mapping(_required(root, "high_rate_xx", "$"), "$.high_rate_xx")
    evidence_text = _string(
        _required(root, "timing_evidence_status", "$"), "$.timing_evidence_status"
    )
    try:
        evidence = EvidenceStatus(evidence_text)
    except ValueError as exc:
        raise ValueError("$.timing_evidence_status is unsupported") from exc
    return BridgeTimingConfig(
        configuration_id=_string(
            _required(root, "configuration_id", "$"), "$.configuration_id"
        ),
        bell_pair_lanes=_integer(
            _required(lanes, "bell_pair", "$.lanes"), "$.lanes.bell_pair", 1
        ),
        segment_lanes=_integer(
            _required(lanes, "segment", "$.lanes"), "$.lanes.segment", 1
        ),
        bell_measurement_lanes=_integer(
            _required(lanes, "bell_measurement", "$.lanes"),
            "$.lanes.bell_measurement",
            1,
        ),
        reactive_measurement_lanes=_integer(
            _required(lanes, "reactive_measurement", "$.lanes"),
            "$.lanes.reactive_measurement",
            1,
        ),
        bell_pair_prepare_steps=_integer(
            _required(durations, "bell_pair_prepare", "$.durations"),
            "$.durations.bell_pair_prepare",
            0,
        ),
        segment_compute_steps=_integer(
            _required(durations, "segment_compute", "$.durations"),
            "$.durations.segment_compute",
            0,
        ),
        bell_component_steps=_integer(
            _required(durations, "bell_component", "$.durations"),
            "$.durations.bell_component",
            0,
        ),
        high_rate_xx_batch_steps=_integer(
            _required(high_rate, "batch_steps", "$.high_rate_xx"),
            "$.high_rate_xx.batch_steps",
            0,
        ),
        reactive_measurement_steps=_integer(
            _required(durations, "reactive_measurement", "$.durations"),
            "$.durations.reactive_measurement",
            0,
        ),
        high_rate_xx_batch_size=_integer(
            _required(high_rate, "batch_size", "$.high_rate_xx"),
            "$.high_rate_xx.batch_size",
            2,
        ),
        timing_evidence_status=evidence,
        source_note=_string(_required(root, "source_note", "$"), "$.source_note"),
        time_unit=_string(_required(root, "time_unit", "$"), "$.time_unit"),
        policy=_string(_required(root, "policy", "$"), "$.policy"),
        schema=_string(_required(root, "schema", "$"), "$.schema"),
        schema_version=_integer(
            _required(root, "schema_version", "$"), "$.schema_version", 1
        ),
    )


def _resource_and_duration(
    event: BridgeEvent, config: BridgeTimingConfig
) -> tuple[str, int, int]:
    if event.kind is BridgeEventKind.BELL_PAIR_PREPARE:
        return "bell_pair_preparation", config.bell_pair_lanes, config.bell_pair_prepare_steps
    if event.kind is BridgeEventKind.SEGMENT_COMPUTE:
        return "segment_compute", config.segment_lanes, config.segment_compute_steps
    if event.kind in {
        BridgeEventKind.BELL_MEASURE_XX,
        BridgeEventKind.BELL_MEASURE_ZZ,
    }:
        return (
            "bell_measurement",
            config.bell_measurement_lanes,
            config.bell_component_steps,
        )
    if event.kind is BridgeEventKind.REACTIVE_MEASUREMENT:
        return (
            "reactive_measurement",
            config.reactive_measurement_lanes,
            config.reactive_measurement_steps,
        )
    return "bookkeeping", 1, 0


def _dependency_maps(
    trace: BridgeRippleTrace,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    predecessors: dict[str, set[str]] = {
        event.event_id: set() for event in trace.events
    }
    successors: dict[str, set[str]] = {
        event.event_id: set() for event in trace.events
    }
    for dependency in trace.dependencies:
        predecessors[dependency.successor].add(dependency.predecessor)
        successors[dependency.predecessor].add(dependency.successor)
    return predecessors, successors


def _critical_path(trace: BridgeRippleTrace, config: BridgeTimingConfig) -> int:
    events = trace.event_by_id()
    predecessors, _ = _dependency_maps(trace)
    finish: dict[str, int] = {}
    for event_id in trace.topological_order():
        _, _, duration = _resource_and_duration(events[event_id], config)
        start = max((finish[value] for value in predecessors[event_id]), default=0)
        finish[event_id] = start + duration
    return max(finish.values(), default=0)


def _lane_choice(availability: list[int]) -> tuple[int, int]:
    lane = min(range(len(availability)), key=lambda index: (availability[index], index))
    return lane, availability[lane]


def _single_candidate(
    event: BridgeEvent,
    *,
    predecessors: dict[str, set[str]],
    scheduled_end: dict[str, int],
    carrier_available: dict[str, int],
    resource_available: dict[str, list[int]],
    config: BridgeTimingConfig,
) -> _Candidate:
    resource, lane_count, duration = _resource_and_duration(event, config)
    dependency_ready = max(
        (scheduled_end[value] for value in predecessors[event.event_id]), default=0
    )
    carrier_ready = max(
        (carrier_available[value] for value in event.logical_support), default=0
    )
    if resource not in resource_available:
        resource_available[resource] = [0] * lane_count
    lane, resource_ready = _lane_choice(resource_available[resource])
    start = max(dependency_ready, carrier_ready, resource_ready)
    return _Candidate(
        source_events=(event,),
        implementation=event.kind.value,
        start_step=start,
        end_step=start + duration,
        logical_support=event.logical_support,
        exclusive_resource=resource,
        resource_lane=lane,
        dependency_ready_step=dependency_ready,
        carrier_ready_step=carrier_ready,
        resource_ready_step=resource_ready,
    )


def _high_rate_candidate(
    ready: list[BridgeEvent],
    *,
    predecessors: dict[str, set[str]],
    scheduled_end: dict[str, int],
    carrier_available: dict[str, int],
    resource_available: dict[str, list[int]],
    config: BridgeTimingConfig,
) -> _Candidate | None:
    selected: list[BridgeEvent] = []
    occupied: set[str] = set()
    for event in ready:
        if event.kind is not BridgeEventKind.BELL_MEASURE_XX:
            continue
        support = set(event.logical_support)
        if support & occupied:
            continue
        selected.append(event)
        occupied.update(support)
        if len(selected) == config.high_rate_xx_batch_size:
            break
    if len(selected) != config.high_rate_xx_batch_size:
        return None
    dependency_ready = max(
        scheduled_end[predecessor]
        for event in selected
        for predecessor in predecessors[event.event_id]
    )
    carrier_ready = max(
        (carrier_available[value] for value in occupied), default=0
    )
    resource = "bell_measurement"
    if resource not in resource_available:
        resource_available[resource] = [0] * config.bell_measurement_lanes
    lane, resource_ready = _lane_choice(resource_available[resource])
    start = max(dependency_ready, carrier_ready, resource_ready)
    return _Candidate(
        source_events=tuple(selected),
        implementation=f"high_rate_xx_{config.high_rate_xx_batch_size}",
        start_step=start,
        end_step=start + config.high_rate_xx_batch_steps,
        logical_support=tuple(sorted(occupied)),
        exclusive_resource=resource,
        resource_lane=lane,
        dependency_ready_step=dependency_ready,
        carrier_ready_step=carrier_ready,
        resource_ready_step=resource_ready,
    )


def _resource_state_peak(
    trace: BridgeRippleTrace, events: tuple[ScheduledBridgeEvent, ...]
) -> int:
    by_source = trace.event_by_id()
    demand_by_start: Counter[int] = Counter()
    for event in events:
        demand_by_start[event.start_step] += sum(
            by_source[source_id].resource_state_demand
            for source_id in event.source_event_ids
        )
    return max(demand_by_start.values(), default=0)


def schedule_bridge_ripple(
    trace: BridgeRippleTrace,
    config: BridgeTimingConfig,
    *,
    allow_check_assumptions: bool = False,
    high_rate_enabled: bool = True,
) -> BridgeRippleSchedule:
    """Schedule a fixed source trace with deterministic earliest-start lanes."""

    if (
        not allow_check_assumptions
        and config.timing_evidence_status is EvidenceStatus.CHECK
    ):
        raise UnsupportedBridgeTimingError(
            "strict bridge schedule rejected CHECK normalized timing"
        )
    source_events = trace.event_by_id()
    position = {
        event.event_id: index for index, event in enumerate(trace.events)
    }
    predecessors, _ = _dependency_maps(trace)
    xx_events = tuple(
        event
        for event in trace.events
        if event.kind is BridgeEventKind.BELL_MEASURE_XX
    )
    reserved_groups: tuple[tuple[BridgeEvent, ...], ...] = (
        tuple(
            tuple(xx_events[index : index + config.high_rate_xx_batch_size])
            for index in range(0, len(xx_events), config.high_rate_xx_batch_size)
            if len(xx_events[index : index + config.high_rate_xx_batch_size])
            == config.high_rate_xx_batch_size
        )
        if high_rate_enabled
        else ()
    )
    reserved_ids = {
        event.event_id for group in reserved_groups for event in group
    }
    unscheduled = set(source_events)
    scheduled_end: dict[str, int] = {}
    carrier_available: dict[str, int] = defaultdict(int)
    resource_available: dict[str, list[int]] = {}
    scheduled: list[ScheduledBridgeEvent] = []
    batch_index = 0

    while unscheduled:
        ready = sorted(
            (
                source_events[event_id]
                for event_id in unscheduled
                if predecessors[event_id] <= scheduled_end.keys()
            ),
            key=lambda event: position[event.event_id],
        )
        if not ready:
            raise BridgeScheduleError("scheduler found no ready bridge event")
        candidates = [
            _single_candidate(
                event,
                predecessors=predecessors,
                scheduled_end=scheduled_end,
                carrier_available=carrier_available,
                resource_available=resource_available,
                config=config,
            )
            for event in ready
            if event.event_id not in reserved_ids
        ]
        if high_rate_enabled:
            for group in reserved_groups:
                group_ids = {event.event_id for event in group}
                if group_ids <= unscheduled and all(
                    predecessors[event.event_id] <= scheduled_end.keys()
                    for event in group
                ):
                    high_rate = _high_rate_candidate(
                        list(group),
                        predecessors=predecessors,
                        scheduled_end=scheduled_end,
                        carrier_available=carrier_available,
                        resource_available=resource_available,
                        config=config,
                    )
                    if high_rate is not None:
                        candidates.append(high_rate)
        if not candidates:
            raise BridgeScheduleError(
                "reserved XX batch has no ready predecessor-complete group"
            )
        candidate = min(
            candidates,
            key=lambda value: (
                value.start_step,
                0 if value.implementation.startswith("high_rate_xx_") else 1,
                min(position[event.event_id] for event in value.source_events),
            ),
        )
        if candidate.implementation.startswith("high_rate_xx_"):
            scheduled_id = f"batch:xx:{batch_index:04d}"
            batch_index += 1
        else:
            scheduled_id = candidate.source_events[0].event_id
        scheduled_event = ScheduledBridgeEvent(
            scheduled_id=scheduled_id,
            source_event_ids=tuple(
                event.event_id for event in candidate.source_events
            ),
            implementation=candidate.implementation,
            start_step=candidate.start_step,
            end_step=candidate.end_step,
            logical_support=candidate.logical_support,
            exclusive_resource=candidate.exclusive_resource,
            resource_lane=candidate.resource_lane,
            dependency_ready_step=candidate.dependency_ready_step,
            carrier_ready_step=candidate.carrier_ready_step,
            resource_ready_step=candidate.resource_ready_step,
            timing_evidence_status=config.timing_evidence_status,
        )
        scheduled.append(scheduled_event)
        for event in candidate.source_events:
            unscheduled.remove(event.event_id)
            scheduled_end[event.event_id] = candidate.end_step
        for carrier in candidate.logical_support:
            carrier_available[carrier] = candidate.end_step
        resource_available[candidate.exclusive_resource][
            candidate.resource_lane
        ] = candidate.end_step

    flattened_order = tuple(
        source_id
        for event in sorted(
            scheduled,
            key=lambda value: (
                value.start_step,
                value.end_step,
                value.scheduled_id,
            ),
        )
        for source_id in sorted(
            event.source_event_ids, key=position.__getitem__
        )
    )
    try:
        replay_summary = replay_bridge_lifecycle(trace, flattened_order)
    except BridgeTraceError as exc:
        raise BridgeScheduleError(f"scheduled lifecycle replay failed: {exc}") from exc
    schedule = BridgeRippleSchedule(
        trace_id=trace.trace_id,
        configuration_id=config.configuration_id,
        allow_check_assumptions=allow_check_assumptions,
        high_rate_enabled=high_rate_enabled,
        time_unit=config.time_unit,
        policy=config.policy,
        algorithmic_critical_path_steps=_critical_path(trace, config),
        scheduled_steps=max((event.end_step for event in scheduled), default=0),
        eligible_xx_measurements=trace.bridge_count,
        high_rate_batch_count=sum(
            event.implementation.startswith("high_rate_xx_")
            for event in scheduled
        ),
        high_rate_operation_count=sum(
            len(event.source_event_ids)
            for event in scheduled
            if event.implementation.startswith("high_rate_xx_")
        ),
        total_resource_state_demand=sum(
            event.resource_state_demand for event in trace.events
        ),
        peak_resource_state_demand_per_step=_resource_state_peak(
            trace, tuple(scheduled)
        ),
        peak_live_bridge_carriers=replay_summary.peak_live_bridge_carriers,
        source_logical_carrier_slots=trace.source_logical_carrier_slots,
        encoded_patch_family_count=len(trace.encoded_patch_families),
        reactive_ancilla_patch_count=trace.reactive_ancilla_patch_count,
        timing_evidence_status=config.timing_evidence_status,
        events=tuple(scheduled),
        replay_summary=replay_summary,
    )
    validate_bridge_schedule(trace, config, schedule)
    return schedule


def validate_bridge_schedule(
    trace: BridgeRippleTrace,
    config: BridgeTimingConfig,
    schedule: BridgeRippleSchedule,
) -> None:
    """Independently validate coverage, dependencies, lanes, and exact batches."""

    source = trace.event_by_id()
    flattened = tuple(
        source_id
        for event in schedule.events
        for source_id in event.source_event_ids
    )
    if len(flattened) != len(source) or set(flattened) != set(source):
        raise BridgeScheduleError("schedule must cover every source event exactly once")
    if len({event.scheduled_id for event in schedule.events}) != len(schedule.events):
        raise BridgeScheduleError("scheduled IDs must be unique")
    owner = {
        source_id: event
        for event in schedule.events
        for source_id in event.source_event_ids
    }
    for dependency in trace.dependencies:
        if owner[dependency.predecessor].end_step > owner[dependency.successor].start_step:
            raise BridgeScheduleError("schedule violates a source dependency")
    for event in schedule.events:
        if event.start_step < 0 or event.end_step < event.start_step:
            raise BridgeScheduleError("scheduled interval is invalid")
        if event.implementation.startswith("high_rate_xx_"):
            if len(event.source_event_ids) != config.high_rate_xx_batch_size:
                raise BridgeScheduleError("high-rate batch must contain exactly ten XXs")
            batch_source = [source[event_id] for event_id in event.source_event_ids]
            if any(
                value.kind is not BridgeEventKind.BELL_MEASURE_XX
                for value in batch_source
            ):
                raise BridgeScheduleError("high-rate batch contains a non-XX event")
            supports = [set(value.logical_support) for value in batch_source]
            for index, support in enumerate(supports):
                if any(support & other for other in supports[index + 1 :]):
                    raise BridgeScheduleError(
                        "high-rate XX supports must be pairwise disjoint"
                    )
            if event.duration_steps != config.high_rate_xx_batch_steps:
                raise BridgeScheduleError("high-rate batch duration is inconsistent")
        elif len(event.source_event_ids) != 1:
            raise BridgeScheduleError("non-batch schedule event has multiple sources")
        else:
            _, _, expected_duration = _resource_and_duration(
                source[event.source_event_ids[0]], config
            )
            if event.duration_steps != expected_duration:
                raise BridgeScheduleError("source event duration is inconsistent")
    positive_events = [
        event for event in schedule.events if event.duration_steps > 0
    ]
    by_lane: dict[tuple[str, int], list[ScheduledBridgeEvent]] = defaultdict(list)
    by_carrier: dict[str, list[ScheduledBridgeEvent]] = defaultdict(list)
    for event in positive_events:
        by_lane[(event.exclusive_resource, event.resource_lane)].append(event)
        for carrier in event.logical_support:
            by_carrier[carrier].append(event)
    for events in (*by_lane.values(), *by_carrier.values()):
        ordered = sorted(events, key=lambda value: (value.start_step, value.end_step))
        for previous, following in pairwise(ordered):
            if previous.end_step > following.start_step:
                raise BridgeScheduleError("resource intervals overlap")
    if schedule.scheduled_steps != max(
        (event.end_step for event in schedule.events), default=0
    ):
        raise BridgeScheduleError("scheduled makespan is inconsistent")
    if schedule.high_rate_operation_count != (
        schedule.high_rate_batch_count * config.high_rate_xx_batch_size
    ):
        raise BridgeScheduleError("high-rate operation count is inconsistent")
    if schedule.total_resource_state_demand != trace.width - 1:
        raise BridgeScheduleError("temporary-AND resource-state demand is inconsistent")
    if schedule.replay_summary != replay_bridge_lifecycle(
        trace,
        tuple(
            source_id
            for event in sorted(
                schedule.events,
                key=lambda value: (
                    value.start_step,
                    value.end_step,
                    value.scheduled_id,
                ),
            )
            for source_id in sorted(
                event.source_event_ids,
                key=lambda value: next(
                    index
                    for index, source_event in enumerate(trace.events)
                    if source_event.event_id == value
                ),
            )
        ),
    ):
        raise BridgeScheduleError("stored replay summary is inconsistent")


def bridge_schedule_to_data(schedule: BridgeRippleSchedule) -> dict[str, Any]:
    """Serialize a bridge schedule deterministically."""

    return {
        "algorithmic_critical_path_steps": schedule.algorithmic_critical_path_steps,
        "allow_check_assumptions": schedule.allow_check_assumptions,
        "configuration_id": schedule.configuration_id,
        "eligible_xx_measurements": schedule.eligible_xx_measurements,
        "encoded_patch_family_count": schedule.encoded_patch_family_count,
        "events": [
            {
                "carrier_ready_step": event.carrier_ready_step,
                "dependency_ready_step": event.dependency_ready_step,
                "end_step": event.end_step,
                "exclusive_resource": event.exclusive_resource,
                "implementation": event.implementation,
                "logical_support": list(event.logical_support),
                "resource_lane": event.resource_lane,
                "resource_ready_step": event.resource_ready_step,
                "scheduled_id": event.scheduled_id,
                "source_event_ids": list(event.source_event_ids),
                "start_step": event.start_step,
                "timing_evidence_status": event.timing_evidence_status.value,
            }
            for event in schedule.events
        ],
        "high_rate_batch_count": schedule.high_rate_batch_count,
        "high_rate_enabled": schedule.high_rate_enabled,
        "high_rate_operation_count": schedule.high_rate_operation_count,
        "peak_live_bridge_carriers": schedule.peak_live_bridge_carriers,
        "peak_resource_state_demand_per_step": (
            schedule.peak_resource_state_demand_per_step
        ),
        "policy": schedule.policy,
        "primary_bottleneck_counts": dict(
            sorted(schedule.primary_bottleneck_counts.items())
        ),
        "reactive_ancilla_patch_count": schedule.reactive_ancilla_patch_count,
        "replay_summary": {
            "all_bridges_rebound": schedule.replay_summary.all_bridges_rebound,
            "bridge_count": schedule.replay_summary.bridge_count,
            "event_count": schedule.replay_summary.event_count,
            "final_live_bridge_carriers": (
                schedule.replay_summary.final_live_bridge_carriers
            ),
            "peak_live_bridge_carriers": (
                schedule.replay_summary.peak_live_bridge_carriers
            ),
        },
        "scheduled_steps": schedule.scheduled_steps,
        "source_logical_carrier_slots": schedule.source_logical_carrier_slots,
        "strict_executable": schedule.strict_executable,
        "time_unit": schedule.time_unit,
        "timing_evidence_status": schedule.timing_evidence_status.value,
        "total_resource_state_demand": schedule.total_resource_state_demand,
        "trace_id": schedule.trace_id,
    }


def dumps_bridge_schedule(schedule: BridgeRippleSchedule) -> str:
    return json.dumps(bridge_schedule_to_data(schedule), indent=2, sort_keys=True) + "\n"
