"""Canary baseline and rollback gate helpers for deployment safety."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanaryDecision:
    should_rollback: bool
    availability_drop: float
    threshold_drop: float
    sample_size: int
    sample_floor: int
    scope_match: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "should_rollback": self.should_rollback,
            "availability_drop": self.availability_drop,
            "threshold_drop": self.threshold_drop,
            "sample_size": self.sample_size,
            "sample_floor": self.sample_floor,
            "scope_match": self.scope_match,
            "reason": self.reason,
        }


def evaluate_canary_rollback(
    *,
    baseline_availability: float,
    canary_availability: float,
    sample_size: int,
    scope_match: bool,
    threshold_drop: float = 0.05,
    sample_floor: int = 100,
) -> CanaryDecision:
    """Evaluate rollback gate: baseline/scope/sample-floor + >5% drop."""
    base = float(max(0.0, min(1.0, baseline_availability)))
    canary = float(max(0.0, min(1.0, canary_availability)))
    size = max(0, int(sample_size))
    floor = max(1, int(sample_floor))
    drop = max(0.0, base - canary)
    threshold = float(max(0.0, threshold_drop))

    if not scope_match:
        return CanaryDecision(
            should_rollback=False,
            availability_drop=drop,
            threshold_drop=threshold,
            sample_size=size,
            sample_floor=floor,
            scope_match=False,
            reason="scope_mismatch",
        )
    if size <= floor:
        return CanaryDecision(
            should_rollback=False,
            availability_drop=drop,
            threshold_drop=threshold,
            sample_size=size,
            sample_floor=floor,
            scope_match=True,
            reason="sample_floor_not_met",
        )
    if drop > threshold:
        return CanaryDecision(
            should_rollback=True,
            availability_drop=drop,
            threshold_drop=threshold,
            sample_size=size,
            sample_floor=floor,
            scope_match=True,
            reason="availability_drop_threshold_breached",
        )
    return CanaryDecision(
        should_rollback=False,
        availability_drop=drop,
        threshold_drop=threshold,
        sample_size=size,
        sample_floor=floor,
        scope_match=True,
        reason="within_threshold",
    )

