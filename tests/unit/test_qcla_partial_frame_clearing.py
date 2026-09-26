from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ecdlp_ftqc.analysis.qcla_partial_frame_clearing import (
    FramePolicy,
    build_partial_frame_clearing_study,
    partial_frame_clearing_study_to_data,
)
from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import build_qcla_trace
from ecdlp_ftqc.compiler import lower_qcla_to_direct_ccz_events
from ecdlp_ftqc.verification.qcla_partial_frame_clearing import (
    PartialFrameClearingReplayError,
    replay_partial_frame_clearing_studies,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = (
    PROJECT_ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
)


@pytest.fixture(scope="module")
def records() -> list[dict[str, Any]]:
    capability = load_direct_ccz_capability(CAPABILITY)
    result: list[dict[str, Any]] = []
    for width in (5, 256):
        trace = build_qcla_trace(width)
        events = lower_qcla_to_direct_ccz_events(trace, capability)
        study = build_partial_frame_clearing_study(
            trace,
            events,
            branch_sample_count=2,
        )
        result.append(partial_frame_clearing_study_to_data(study))
    return result


def test_exact_width5_replay_and_width256_structure(
    records: list[dict[str, Any]],
) -> None:
    summary = replay_partial_frame_clearing_studies(records)
    assert summary.all_passed
    assert summary.widths == (5, 256)
    assert summary.source_ccx_counts == (20, 2458)
    assert summary.macro_depths == (8, 30)
    assert summary.width5_projective_checks == 1440


def test_partial_policy_preserves_axis_family_and_reduces_support(
    records: list[dict[str, Any]],
) -> None:
    width256 = records[1]
    policies = {row["policy"]: row for row in width256["policies"]}
    partial = policies[FramePolicy.PARTIAL_CLEARING.value]
    complete = policies[FramePolicy.FULL_CLEARING.value]
    conjugated = policies[FramePolicy.FULL_CONJUGATION.value]
    bare = policies[FramePolicy.BARE_PROPAGATION.value]
    tracked = policies[FramePolicy.FRAME_TRACKING.value]

    assert partial["z_x_only_high_rate_family_admitted"]
    assert complete["z_x_only_high_rate_family_admitted"]
    assert not bare["z_x_only_high_rate_family_admitted"]
    assert not tracked["z_x_only_high_rate_family_admitted"]
    assert complete["maximum_presented_ppm_weight"]["maximum"] == 2
    assert (
        partial["maximum_presented_ppm_weight"]["maximum"]
        <= conjugated["maximum_presented_ppm_weight"]["maximum"]
    )
    assert (
        partial["literal_cnot_occurrences"]["maximum"]
        <= complete["literal_cnot_occurrences"]["maximum"]
    )


def test_replay_rejects_changed_distribution(records: list[dict[str, Any]]) -> None:
    changed = deepcopy(records)
    changed[1]["policies"][0]["maximum_presented_ppm_weight"]["p50"] += 1
    with pytest.raises(PartialFrameClearingReplayError, match="p50 changed"):
        replay_partial_frame_clearing_studies(changed)


def test_replay_rejects_fabricated_native_depth(records: list[dict[str, Any]]) -> None:
    changed = deepcopy(records)
    changed[1]["policies"][0]["native_scheduled_depth"] = 60
    with pytest.raises(PartialFrameClearingReplayError, match="finite output"):
        replay_partial_frame_clearing_studies(changed)
