from __future__ import annotations

from src.core.sentry_client import SentryClient


def test_resolve_base_url_from_override(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_API_BASE_URL", "https://de.sentry.io/api/0")
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    client = SentryClient(api_key="token")
    assert client.base_url == "https://de.sentry.io/api/0"


def test_resolve_base_url_from_dsn_region(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_API_BASE_URL", raising=False)
    monkeypatch.setenv(
        "SENTRY_DSN",
        "https://abc@o4510917867929600.ingest.de.sentry.io/4510917894930512",
    )
    client = SentryClient(api_key="token")
    assert client.base_url == "https://de.sentry.io/api/0"
