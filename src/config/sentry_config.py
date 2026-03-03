"""
Sentry configuration helpers for Flask runtime observability.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)
_SENTRY_INITIALIZED = False


def _env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid float for %s=%r, using default %s", key, value, default)
        return default


def _resolve_dsn(runtime: str) -> str:
    runtime = (runtime or "backend").strip().lower()
    if runtime == "workers":
        return (os.getenv("SENTRY_WORKERS_DSN") or os.getenv("SENTRY_DSN") or "").strip()
    if runtime == "frontend":
        return (os.getenv("NEXT_PUBLIC_SENTRY_DSN") or "").strip()
    return (os.getenv("SENTRY_DSN") or "").strip()


def _resolve_profiles_sample_rate(runtime: str) -> float:
    runtime = (runtime or "backend").strip().lower()
    if runtime == "workers":
        return _env_float(
            "SENTRY_WORKERS_PROFILES_SAMPLE_RATE",
            _env_float("SENTRY_PROFILES_SAMPLE_RATE", _env_float("SENTRY_PROFILE_SESSION_SAMPLE_RATE", 1.0)),
        )
    return _env_float("SENTRY_PROFILES_SAMPLE_RATE", _env_float("SENTRY_PROFILE_SESSION_SAMPLE_RATE", 1.0))


def _resolve_traces_sample_rate(runtime: str) -> float:
    runtime = (runtime or "backend").strip().lower()
    if runtime == "workers":
        return _env_float(
            "SENTRY_WORKERS_TRACES_SAMPLE_RATE",
            _env_float("SENTRY_TRACES_SAMPLE_RATE", 1.0),
        )
    return _env_float("SENTRY_TRACES_SAMPLE_RATE", 1.0)


def configure_sentry(runtime: str = "backend") -> bool:
    """
    Initialize Sentry SDK from environment variables.

    Returns:
        True when Sentry is initialized, False otherwise.
    """
    global _SENTRY_INITIALIZED
    if _SENTRY_INITIALIZED:
        return True

    dsn = _resolve_dsn(runtime)
    if not dsn:
        logger.info("Sentry disabled (%s DSN not set)", runtime)
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
    except ImportError:
        logger.warning("sentry-sdk is not installed; skipping Sentry initialization")
        return False

    integrations = []
    if runtime == "workers":
        integrations.append(CeleryIntegration(monitor_beat_tasks=True))
    else:
        integrations.append(FlaskIntegration())

    sentry_sdk.init(
        dsn=dsn,
        integrations=integrations,
        send_default_pii=_env_bool("SENTRY_SEND_DEFAULT_PII", True),
        enable_logs=_env_bool("SENTRY_ENABLE_LOGS", True),
        traces_sample_rate=_resolve_traces_sample_rate(runtime),
        profiles_sample_rate=_resolve_profiles_sample_rate(runtime),
        environment=os.getenv("SENTRY_ENVIRONMENT") or os.getenv("APP_ENVIRONMENT") or os.getenv("FLASK_ENV", "development"),
        release=os.getenv("SENTRY_RELEASE") or None,
    )
    _SENTRY_INITIALIZED = True
    logger.info("Sentry initialized for runtime=%s", runtime)
    return True
