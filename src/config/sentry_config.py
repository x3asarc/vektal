"""
Sentry configuration helpers for Flask runtime observability.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


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


def configure_sentry() -> bool:
    """
    Initialize Sentry SDK from environment variables.

    Returns:
        True when Sentry is initialized, False otherwise.
    """
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:
        logger.warning("sentry-sdk is not installed; skipping Sentry initialization")
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        send_default_pii=_env_bool("SENTRY_SEND_DEFAULT_PII", True),
        enable_logs=_env_bool("SENTRY_ENABLE_LOGS", True),
        traces_sample_rate=_env_float("SENTRY_TRACES_SAMPLE_RATE", 1.0),
        profile_session_sample_rate=_env_float("SENTRY_PROFILE_SESSION_SAMPLE_RATE", 1.0),
        profile_lifecycle=os.getenv("SENTRY_PROFILE_LIFECYCLE", "trace"),
        environment=os.getenv("SENTRY_ENVIRONMENT") or os.getenv("FLASK_ENV", "development"),
        release=os.getenv("SENTRY_RELEASE") or None,
    )
    logger.info("Sentry initialized")
    return True

