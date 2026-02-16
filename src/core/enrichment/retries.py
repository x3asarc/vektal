"""Transient retry policy for enrichment execution steps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


TRANSIENT_CLASSES = {"rate_limit", "timeout", "connectivity", "server_error"}
NON_RETRYABLE_CLASSES = {"schema_error", "policy_error", "validation_error"}


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3


@dataclass(frozen=True)
class RetryResult:
    result: object | None
    attempts: int
    exhausted: bool
    reason_codes: tuple[str, ...]


class RetryExhaustedError(RuntimeError):
    """Raised when retry policy is exhausted or non-retryable failure occurs."""

    def __init__(self, message: str, reason_codes: tuple[str, ...], attempts: int):
        super().__init__(message)
        self.reason_codes = reason_codes
        self.attempts = attempts


def execute_with_retry(
    *,
    operation: Callable[[], object],
    classify_error: Callable[[Exception], str],
    policy: RetryPolicy | None = None,
) -> RetryResult:
    """
    Execute operation with bounded retries based on error classification.
    """
    resolved_policy = policy or RetryPolicy()
    attempts = 0
    reason_codes: list[str] = []
    while attempts < max(1, int(resolved_policy.max_attempts)):
        attempts += 1
        try:
            value = operation()
            return RetryResult(
                result=value,
                attempts=attempts,
                exhausted=False,
                reason_codes=tuple(reason_codes),
            )
        except Exception as exc:  # noqa: BLE001
            error_class = classify_error(exc)
            reason_codes.append(f"error:{error_class}")

            if error_class in NON_RETRYABLE_CLASSES:
                raise RetryExhaustedError(
                    f"Non-retryable enrichment failure: {error_class}",
                    tuple(reason_codes + ["non_retryable"]),
                    attempts,
                ) from exc

            if error_class not in TRANSIENT_CLASSES:
                raise RetryExhaustedError(
                    f"Unknown enrichment failure class: {error_class}",
                    tuple(reason_codes + ["unknown_non_retryable"]),
                    attempts,
                ) from exc

            if attempts >= max(1, int(resolved_policy.max_attempts)):
                raise RetryExhaustedError(
                    f"Retry exhausted for enrichment operation: {error_class}",
                    tuple(reason_codes + ["retry_exhausted"]),
                    attempts,
                ) from exc

    raise RetryExhaustedError(
        "Retry policy loop exited unexpectedly.",
        tuple(reason_codes + ["retry_loop_unexpected_exit"]),
        attempts,
    )

