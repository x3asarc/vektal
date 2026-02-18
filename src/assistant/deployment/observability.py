"""Observability utilities for correlation lineage and SLI/error-budget math."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


AVAILABILITY_TARGET = 0.999
ERROR_BUDGET_SECONDS_30D = 2592  # 43m 12s


@dataclass(frozen=True)
class AvailabilityComputation:
    successful_requests: int
    total_requests: int
    user_errors: int
    denominator: int
    sli: float
    target: float
    error_budget_seconds_30d: int
    downtime_seconds_30d: int
    budget_remaining_seconds_30d: int
    freeze_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "successful_requests": self.successful_requests,
            "total_requests": self.total_requests,
            "user_errors": self.user_errors,
            "denominator": self.denominator,
            "availability_sli": self.sli,
            "availability_target": self.target,
            "error_budget_seconds_30d": self.error_budget_seconds_30d,
            "downtime_seconds_30d": self.downtime_seconds_30d,
            "budget_remaining_seconds_30d": self.budget_remaining_seconds_30d,
            "freeze_required": self.freeze_required,
        }


def resolve_correlation_id(*, provided: str | None = None) -> str:
    """Resolve deterministic correlation ID with UUID fallback."""
    token = str(provided or "").strip()
    if token:
        return token
    return f"corr-{uuid.uuid4().hex}"


def compute_availability_sli(
    *,
    successful_requests: int,
    total_requests: int,
    user_errors: int,
    downtime_seconds_30d: int,
    target: float = AVAILABILITY_TARGET,
    error_budget_seconds_30d: int = ERROR_BUDGET_SECONDS_30D,
) -> AvailabilityComputation:
    """Compute locked availability formula and error-budget decision."""
    safe_success = max(0, int(successful_requests))
    safe_total = max(0, int(total_requests))
    safe_user_errors = max(0, int(user_errors))
    denominator = max(1, safe_total - safe_user_errors)
    sli = float(safe_success) / float(denominator)

    used = max(0, int(downtime_seconds_30d))
    remaining = error_budget_seconds_30d - used
    freeze_required = remaining < 0
    return AvailabilityComputation(
        successful_requests=safe_success,
        total_requests=safe_total,
        user_errors=safe_user_errors,
        denominator=denominator,
        sli=sli,
        target=float(target),
        error_budget_seconds_30d=int(error_budget_seconds_30d),
        downtime_seconds_30d=used,
        budget_remaining_seconds_30d=max(0, remaining),
        freeze_required=freeze_required,
    )

