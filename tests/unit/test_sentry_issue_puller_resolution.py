from __future__ import annotations

from scripts.observability.sentry_issue_puller import _resolve_sentry_project


def test_resolve_sentry_project_prefers_explicit_env(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_ORG_SLUG", "my-org")
    monkeypatch.setenv("SENTRY_PROJECT_SLUG", "my-project")
    monkeypatch.setenv(
        "SENTRY_DSN",
        "https://key@o1111111111111111.ingest.de.sentry.io/2222222222222222",
    )

    org, project = _resolve_sentry_project()

    assert org == "my-org"
    assert project == "my-project"


def test_resolve_sentry_project_uses_dsn_ids(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_ORG_SLUG", raising=False)
    monkeypatch.delenv("SENTRY_PROJECT_SLUG", raising=False)
    monkeypatch.setenv(
        "SENTRY_DSN",
        "https://abc123@o4510917867929600.ingest.de.sentry.io/4510917894930512",
    )

    org, project = _resolve_sentry_project()

    assert org == "4510917867929600"
    assert project == "4510917894930512"


def test_resolve_sentry_project_falls_back_to_legacy_defaults(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_ORG_SLUG", raising=False)
    monkeypatch.delenv("SENTRY_PROJECT_SLUG", raising=False)
    monkeypatch.delenv("SENTRY_DSN", raising=False)

    org, project = _resolve_sentry_project()

    assert org == "shopify-scraping-script"
    assert project == "shopify-scraping-script"
