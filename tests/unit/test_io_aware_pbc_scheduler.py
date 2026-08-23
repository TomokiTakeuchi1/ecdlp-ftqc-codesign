from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ecdlp_ftqc.circuits import load_gidney_oracle_dag
from ecdlp_ftqc.codes import load_pbc_mitten_backend_config
from ecdlp_ftqc.compiler import (
    lower_gidney_phase_exact,
    lower_to_adaptive_pauli_measurements,
)
from ecdlp_ftqc.io import MemoryIoError
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler import (
    MemoryIoTimingConfig,
    UnsupportedMemoryIoTimingError,
    dumps_io_aware_schedule,
    load_memory_io_timing_config,
    schedule_adaptive_pbc_greedy,
    schedule_io_aware_adaptive_pbc,
    validate_io_aware_adaptive_pbc,
)

ROOT = Path(__file__).resolve().parents[2]
GIDNEY_ROOT = ROOT / "tests" / "fixtures" / "gidney_oracle"
PBC_CONFIG = ROOT / "configs" / "codes" / "mitten_j300_pbc_v2.yaml"
IO_CONFIG = ROOT / "configs" / "architectures" / "j300_memory_io_v1.yaml"


def _cycle(width: int = 2):  # type: ignore[no-untyped-def]
    dag = load_gidney_oracle_dag(
        GIDNEY_ROOT / f"gidney_width{width}_oracle_v3.json"
    )
    logical = lower_gidney_phase_exact(dag)
    pbc = lower_to_adaptive_pauli_measurements(logical)
    base = schedule_adaptive_pbc_greedy(
        pbc,
        load_pbc_mitten_backend_config(PBC_CONFIG),
        allow_check_assumptions=True,
    )
    return dag, logical, pbc, base


def test_zero_latency_io_preserves_reviewed_schedule_exactly() -> None:
    dag, logical, pbc, base = _cycle()
    config = MemoryIoTimingConfig(
        configuration_id="memory-io-ideal-zero-latency-test-v1",
        logical_qubits=60,
        transfer_lanes=1,
        load_rounds=0,
        store_rounds=0,
        timing_evidence_status=EvidenceStatus.PROVED,
        source_note="Zero-duration regression boundary only",
    )
    schedule = schedule_io_aware_adaptive_pbc(dag, logical, pbc, base, config)

    assert schedule.scheduled_rounds == base.scheduled_rounds
    assert schedule.added_rounds == 0
    assert (schedule.loads, schedule.stores) == (4, 4)
    assert tuple(
        (event.start_round, event.end_round) for event in schedule.compute_events
    ) == tuple((event.start_round, event.end_round) for event in base.events)


def test_check_transfer_timing_fails_closed_then_emits_sensitivity_upper_bound() -> None:
    dag, logical, pbc, base = _cycle()
    config = load_memory_io_timing_config(IO_CONFIG)
    with pytest.raises(UnsupportedMemoryIoTimingError, match="CHECK"):
        schedule_io_aware_adaptive_pbc(dag, logical, pbc, base, config)

    schedule = schedule_io_aware_adaptive_pbc(
        dag,
        logical,
        pbc,
        base,
        config,
        allow_check_assumptions=True,
    )
    assert schedule.base_scheduled_rounds == 846
    assert schedule.scheduled_rounds == 854
    assert schedule.added_rounds == 8
    assert (schedule.loads, schedule.stores) == (4, 4)
    assert not schedule.strict_executable
    assert schedule.timing_evidence_status is EvidenceStatus.CHECK
    assert dumps_io_aware_schedule(schedule) == dumps_io_aware_schedule(
        schedule_io_aware_adaptive_pbc(
            dag,
            logical,
            pbc,
            base,
            config,
            allow_check_assumptions=True,
        )
    )


def test_more_transfer_lanes_do_not_increase_the_upper_bound() -> None:
    dag, logical, pbc, base = _cycle(4)
    one_lane = load_memory_io_timing_config(IO_CONFIG)
    two_lanes = replace(one_lane, configuration_id="two-lane-test", transfer_lanes=2)
    serial = schedule_io_aware_adaptive_pbc(
        dag, logical, pbc, base, one_lane, allow_check_assumptions=True
    )
    parallel = schedule_io_aware_adaptive_pbc(
        dag, logical, pbc, base, two_lanes, allow_check_assumptions=True
    )

    assert parallel.loads == serial.loads
    assert parallel.stores == serial.stores
    assert parallel.scheduled_rounds <= serial.scheduled_rounds


def test_capacity_and_timeline_mutations_are_rejected() -> None:
    dag, logical, pbc, base = _cycle()
    config = load_memory_io_timing_config(IO_CONFIG)
    with pytest.raises(MemoryIoError, match="capacity"):
        schedule_io_aware_adaptive_pbc(
            dag,
            logical,
            pbc,
            base,
            replace(config, logical_qubits=3),
            allow_check_assumptions=True,
        )

    schedule = schedule_io_aware_adaptive_pbc(
        dag, logical, pbc, base, config, allow_check_assumptions=True
    )
    first = schedule.transfers[0]
    corrupted = replace(
        schedule,
        transfers=(replace(first, end_round=first.end_round + 1), *schedule.transfers[1:]),
    )
    with pytest.raises(MemoryIoError):
        validate_io_aware_adaptive_pbc(base, config, corrupted)
