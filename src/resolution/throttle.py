"""Adaptive throttling helpers for Shopify API pressure signals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ThrottleSignal:
    """Normalized throttle state from GraphQL or REST response metadata."""

    currently_available: float
    maximum_available: float
    restore_rate: float

    @property
    def utilization(self) -> float:
        if self.maximum_available <= 0:
            return 1.0
        used = max(0.0, self.maximum_available - self.currently_available)
        return min(1.0, used / self.maximum_available)


def parse_throttle_signal(
    *,
    graphql_payload: dict[str, Any] | None = None,
    response_headers: dict[str, str] | None = None,
) -> ThrottleSignal | None:
    """Parse throttle metadata from GraphQL payload or REST headers."""
    if graphql_payload:
        throttle = (
            graphql_payload.get("extensions", {})
            .get("cost", {})
            .get("throttleStatus", {})
        )
        if throttle:
            return ThrottleSignal(
                currently_available=float(throttle.get("currentlyAvailable", 0)),
                maximum_available=float(throttle.get("maximumAvailable", 0)),
                restore_rate=float(throttle.get("restoreRate", 0)),
            )

    if response_headers:
        limit = response_headers.get("X-Shopify-Shop-Api-Call-Limit")
        if limit and "/" in limit:
            used_raw, max_raw = limit.split("/", 1)
            used = float(used_raw.strip())
            maximum = float(max_raw.strip())
            return ThrottleSignal(
                currently_available=max(0.0, maximum - used),
                maximum_available=maximum,
                restore_rate=2.0,
            )
    return None


class AdaptiveThrottleController:
    """Simple adaptive controller for concurrency and dynamic backoff."""

    def __init__(self, *, initial_concurrency: int = 5, min_concurrency: int = 1, max_concurrency: int = 10):
        self.current_concurrency = initial_concurrency
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.last_signal: ThrottleSignal | None = None

    def observe(self, signal: ThrottleSignal | None) -> None:
        if signal is None:
            return
        self.last_signal = signal
        if signal.utilization >= 0.85:
            self.current_concurrency = max(self.min_concurrency, self.current_concurrency - 1)
        elif signal.utilization <= 0.40:
            self.current_concurrency = min(self.max_concurrency, self.current_concurrency + 1)

    def recommended_backoff_seconds(self, signal: ThrottleSignal | None = None) -> float:
        signal = signal or self.last_signal
        if signal is None:
            return 0.0
        if signal.currently_available <= 0:
            return max(1.0, 2.0 / max(signal.restore_rate, 1.0))
        headroom_ratio = signal.currently_available / max(signal.maximum_available, 1.0)
        if headroom_ratio < 0.10:
            return max(0.5, 1.0 / max(signal.restore_rate, 1.0))
        if headroom_ratio < 0.20:
            return max(0.25, 0.5 / max(signal.restore_rate, 1.0))
        return 0.0
