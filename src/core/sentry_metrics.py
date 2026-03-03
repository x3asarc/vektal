"""Small helpers for custom Sentry metrics emission."""

from __future__ import annotations

from typing import Any


def _metrics_api():
    try:
        from sentry_sdk import metrics  # type: ignore

        return metrics
    except Exception:
        return None


def count(name: str, value: int = 1, **kwargs: Any) -> None:
    metrics = _metrics_api()
    if metrics is None:
        return
    try:
        metrics.count(name, value, **kwargs)
    except Exception:
        return


def gauge(name: str, value: float, **kwargs: Any) -> None:
    metrics = _metrics_api()
    if metrics is None:
        return
    try:
        metrics.gauge(name, value, **kwargs)
    except Exception:
        return


def distribution(name: str, value: float, **kwargs: Any) -> None:
    metrics = _metrics_api()
    if metrics is None:
        return
    try:
        metrics.distribution(name, value, **kwargs)
    except Exception:
        return
