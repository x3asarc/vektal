from __future__ import annotations

import pytest

from scripts.observability.sentry_issue_puller import (
    PullResult,
    _parse_next_cursor,
    _resolve_sentry_project,
    normalize_issue,
    pull_sentry_issues,
    run_ingestion_cycle,
)
from src.graph.sentry_ingestor import FailureEvent


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


def test_parse_next_cursor_returns_cursor_for_next_results_true() -> None:
    header = (
        '<https://sentry.io/api/0/projects/org/proj/issues/?cursor=a>; rel="previous"; results="false"; cursor="a",'
        ' <https://sentry.io/api/0/projects/org/proj/issues/?cursor=b>; rel="next"; results="true"; cursor="b"'
    )
    assert _parse_next_cursor(header) == "b"


def test_parse_next_cursor_returns_none_when_next_has_no_results() -> None:
    header = (
        '<https://sentry.io/api/0/projects/org/proj/issues/?cursor=b>; rel="next"; results="false"; cursor="b"'
    )
    assert _parse_next_cursor(header) is None


def test_normalize_issue_sets_required_phase_15_1_fields() -> None:
    issue = {
        "id": "123",
        "title": "ConnectionRefusedError: local neo4j down",
        "culprit": "src/graph/query_interface.py",
        "metadata": {"type": "ConnectionRefusedError"},
        "lastSeen": "2026-03-04T12:00:00Z",
        "level": "error",
        "tags": [{"key": "environment", "value": "prod"}],
    }

    event = normalize_issue(issue)

    assert event.event_id == "123"
    assert event.level == "error"
    assert event.timestamp == "2026-03-04T12:00:00Z"
    assert event.tags["issue_id"] == "123"
    assert event.tags["error_type"] == "ConnectionRefusedError"
    assert event.tags["affected_module"] == "src/graph/query_interface.py"


@pytest.mark.asyncio
async def test_pull_sentry_issues_manual_returns_cursor_state() -> None:
    result = await pull_sentry_issues(manual=True)
    assert isinstance(result, PullResult)
    assert result.error is None
    assert result.cursor_state["mode"] == "manual"
    assert result.events


@pytest.mark.asyncio
async def test_run_ingestion_cycle_emits_processed_count(monkeypatch) -> None:
    fake_event = FailureEvent(
        event_id="i-1",
        title="Neo4jError: ServiceUnavailable",
        category="AURA_UNREACHABLE",
        culprit="src/core/graphiti_client.py",
        timestamp="2026-03-04T13:00:00Z",
        tags={"error_type": "Neo4jError", "affected_module": "src/core/graphiti_client.py"},
        level="error",
    )

    async def _fake_pull(manual: bool = False) -> PullResult:
        return PullResult(
            events=[fake_event],
            cursor_state={"mode": "api", "last_cursor": "abc", "pages_fetched": 1},
            error=None,
        )

    async def _fake_ingest(event: FailureEvent) -> bool:
        return True

    calls: dict[str, int] = {"refresh": 0}

    def _fake_refresh() -> None:
        calls["refresh"] += 1

    monkeypatch.setattr("scripts.observability.sentry_issue_puller.pull_sentry_issues", _fake_pull)
    monkeypatch.setattr("scripts.observability.sentry_issue_puller.ingest_failure_event", _fake_ingest)
    monkeypatch.setattr("scripts.observability.sentry_issue_puller._refresh_materialized_views", _fake_refresh)

    cycle = await run_ingestion_cycle(manual=False)

    assert cycle["events_processed"] == 1
    assert cycle["ingested"] == 1
    assert cycle["cursor_state"]["last_cursor"] == "abc"
    assert calls["refresh"] == 1
