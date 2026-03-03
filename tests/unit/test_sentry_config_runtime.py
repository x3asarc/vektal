from __future__ import annotations

from src.config.sentry_config import _resolve_dsn, _resolve_profiles_sample_rate, _resolve_traces_sample_rate


def test_resolve_dsn_backend(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "backend-dsn")
    monkeypatch.setenv("SENTRY_WORKERS_DSN", "workers-dsn")
    assert _resolve_dsn("backend") == "backend-dsn"


def test_resolve_dsn_workers_prefers_workers_dsn(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "backend-dsn")
    monkeypatch.setenv("SENTRY_WORKERS_DSN", "workers-dsn")
    assert _resolve_dsn("workers") == "workers-dsn"


def test_workers_sample_rates_fallback(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_WORKERS_TRACES_SAMPLE_RATE", raising=False)
    monkeypatch.delenv("SENTRY_WORKERS_PROFILES_SAMPLE_RATE", raising=False)
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
    monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", "0.15")

    assert _resolve_traces_sample_rate("workers") == 0.25
    assert _resolve_profiles_sample_rate("workers") == 0.15
