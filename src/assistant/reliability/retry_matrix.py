"""Class-based retry policy evaluation for runtime failures."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RETRY_CLASS_RATE_LIMIT = "rate_limit"
RETRY_CLASS_SERVER_ERROR = "server_error"
RETRY_CLASS_TIMEOUT = "timeout"
RETRY_CLASS_CONNECTIVITY = "connectivity"
RETRY_CLASS_SCHEMA_VALIDATION = "schema_validation"
RETRY_CLASS_UNKNOWN = "unknown"


@dataclass(frozen=True)
class RetryDecision:
    """Deterministic retry decision for one error class and attempt."""

    retry_class: str
    should_retry: bool
    delay_seconds: float
    max_retries: int
    strategy: str
    increment_breaker_error: bool
    invoke_reflexive_fixer: bool

    @property
    def terminal(self) -> bool:
        return not self.should_retry


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def classify_retry_class(
    *,
    status_code: int | None = None,
    error_class: str | None = None,
    exception: Exception | None = None,
) -> str:
    """Classify one failure into the retry matrix bucket."""
    if error_class:
        normalized = str(error_class).strip().lower()
        aliases = {
            "429": RETRY_CLASS_RATE_LIMIT,
            "rate_limit": RETRY_CLASS_RATE_LIMIT,
            "server_error": RETRY_CLASS_SERVER_ERROR,
            "5xx": RETRY_CLASS_SERVER_ERROR,
            "timeout": RETRY_CLASS_TIMEOUT,
            "connectivity": RETRY_CLASS_CONNECTIVITY,
            "schema": RETRY_CLASS_SCHEMA_VALIDATION,
            "schema_validation": RETRY_CLASS_SCHEMA_VALIDATION,
            "validation": RETRY_CLASS_SCHEMA_VALIDATION,
        }
        if normalized in aliases:
            return aliases[normalized]

    if status_code == 429:
        return RETRY_CLASS_RATE_LIMIT
    if status_code is not None and status_code >= 500:
        return RETRY_CLASS_SERVER_ERROR

    if isinstance(exception, TimeoutError):
        return RETRY_CLASS_TIMEOUT
    if isinstance(exception, ConnectionError):
        return RETRY_CLASS_CONNECTIVITY
    return RETRY_CLASS_UNKNOWN


def evaluate_retry_decision(
    *,
    retry_class: str,
    attempt_number: int,
    retry_after_seconds: int | None = None,
    retry_policy: dict[str, Any] | None = None,
) -> RetryDecision:
    """
    Evaluate retry/backoff behavior for one attempt.

    `attempt_number` is 1-indexed.
    """
    policy = retry_policy or {}
    class_policy = policy.get(retry_class) if isinstance(policy, dict) else None
    max_retries = _coerce_int((class_policy or {}).get("max_retries"), 0)
    strategy = str((class_policy or {}).get("strategy") or "none")
    should_retry = attempt_number <= max_retries
    delay_seconds = 0.0
    increment_breaker_error = retry_class in {
        RETRY_CLASS_RATE_LIMIT,
        RETRY_CLASS_SERVER_ERROR,
        RETRY_CLASS_TIMEOUT,
    }
    invoke_reflexive_fixer = retry_class == RETRY_CLASS_SCHEMA_VALIDATION

    if should_retry:
        if retry_class == RETRY_CLASS_RATE_LIMIT:
            if retry_after_seconds is not None and retry_after_seconds > 0:
                delay_seconds = float(retry_after_seconds)
            else:
                base = float(2 ** attempt_number)
                delay_seconds = base * 1.1  # deterministic +10% jitter
        elif retry_class == RETRY_CLASS_SERVER_ERROR:
            linear_steps = {1: 5.0, 2: 10.0}
            delay_seconds = linear_steps.get(attempt_number, 10.0)
        elif retry_class == RETRY_CLASS_TIMEOUT:
            delay_seconds = 0.0
        elif retry_class == RETRY_CLASS_CONNECTIVITY:
            delay_seconds = 0.0
        elif retry_class == RETRY_CLASS_SCHEMA_VALIDATION:
            delay_seconds = 0.0
        else:
            delay_seconds = 0.0
    else:
        delay_seconds = 0.0

    return RetryDecision(
        retry_class=retry_class,
        should_retry=should_retry,
        delay_seconds=delay_seconds,
        max_retries=max_retries,
        strategy=strategy,
        increment_breaker_error=increment_breaker_error,
        invoke_reflexive_fixer=invoke_reflexive_fixer,
    )

