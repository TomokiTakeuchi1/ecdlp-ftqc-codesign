"""Paired conditional Clifford budgets, not a native-runtime comparison."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from ecdlp_ftqc.scheduler.parallel_low_rate import Limits, Lowering, Timing, schedule_macro


@dataclass(frozen=True, slots=True)
class Services:
    surgery: int = 0
    prepare: int = 0
    readout: int = 0
    reaction: int = 0

    def __post_init__(self) -> None:
        if any(type(v) is not int or v < 0 for v in asdict(self).values()):
            raise ValueError("nonnegative integer service counts required")

    def duration(self, timing: Timing) -> float:
        return round(
            self.surgery * timing.surgery
            + self.prepare * timing.prepare_zero
            + self.readout * timing.readout
            + self.reaction * timing.reaction,
            12,
        )


def scheduled_services(
    lowerings: Iterable[Lowering], readouts: Iterable[int], limits: Limits, timing: Timing
) -> Services | None:
    """None denotes PPM infeasibility only, never an uncharged fallback."""
    totals = [0, 0, 0, 0]
    for lo, read in zip(lowerings, readouts, strict=True):
        result = schedule_macro(lo, limits, timing, read)
        if not result.feasible:
            return None
        assert result.surgery_steps is not None
        for i, value in enumerate(
            (
                result.surgery_steps,
                result.prepare_steps,
                result.readout_steps,
                result.reaction_steps,
            )
        ):
            totals[i] += value
    return Services(*totals)


def paired_budget(
    tracked: Services | None, legacy: Services | None, timing: Timing
) -> dict[str, Any]:
    """T_legacy_complete = T_legacy_PPM + B, with serial unknown B >= 0.

    B includes ALL additional physical legacy Cliffords and their service costs.
    Even when PPMs fit, no legacy Clifford implementation is hereby admitted.
    """
    status = (
        "both_ppm_feasible"
        if tracked is not None and legacy is not None
        else "tracked_ppm_only"
        if tracked is not None
        else "legacy_ppm_only"
        if legacy is not None
        else "neither_ppm_feasible"
    )
    tc = tracked.duration(timing) if tracked is not None else None
    lc = legacy.duration(timing) if legacy is not None else None
    coefficients = (
        {key: asdict(tracked)[key] - asdict(legacy)[key] for key in asdict(tracked)}
        if tracked is not None and legacy is not None
        else None
    )
    return {
        "status": status,
        "tracked_services": asdict(tracked) if tracked is not None else None,
        "legacy_ppm_services": asdict(legacy) if legacy is not None else None,
        "tracked_conditional_units": tc,
        "legacy_ppm_conditional_units": lc,
        "delta_service_counts": coefficients,
        "b_crit_units": round(tc - lc, 12) if tc is not None and lc is not None else None,
        "legacy_clifford_cost_units": None,
        "legacy_complete_duration": None,
        "native_runtime_seconds": None,
    }


def distribution(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    if any(not math.isfinite(v) for v in values):
        raise ValueError("finite sample values required")
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "p50": ordered[math.ceil(len(ordered) * 0.5) - 1],
        "p95": ordered[math.ceil(len(ordered) * 0.95) - 1],
        "max": ordered[-1],
    }


def summarize_pairs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Caller supplies one config and HASHED branches only; keep pairing intact."""
    states = ("both_ppm_feasible", "tracked_ppm_only", "legacy_ppm_only", "neither_ppm_feasible")
    if any(row["status"] not in states for row in rows):
        raise ValueError("unknown pair status")
    common = [row for row in rows if row["status"] == "both_ppm_feasible"]
    budgets = [row["b_crit_units"] for row in common]
    return {
        "hashed_witness_count": len(rows),
        "status_counts": {state: sum(row["status"] == state for row in rows) for state in states},
        "b_crit_units": distribution(budgets),
        "negative_budget_count": sum(v < 0 for v in budgets),
        "zero_budget_count": sum(v == 0 for v in budgets),
        "tracked_common_units": distribution([row["tracked_conditional_units"] for row in common]),
        "legacy_ppm_common_units": distribution(
            [row["legacy_ppm_conditional_units"] for row in common]
        ),
    }
