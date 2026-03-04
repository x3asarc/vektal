from __future__ import annotations

from scripts.daemons.health_monitor import _issue_fingerprint
from scripts.observability.sentry_issue_puller import normalize_issue
from src.core.sentry_client import SentryClient
from src.memory.event_schema import EventType


def test_phase15_1_event_types_are_registered() -> None:
    assert EventType.SENTRY_ISSUE_PULLED.value == "sentry_issue_pulled"
    assert EventType.SENTRY_ISSUE_ROUTED.value == "sentry_issue_routed"
    assert EventType.SENTRY_ISSUE_VERIFIED.value == "sentry_issue_verified"


def test_phase15_1_sentry_client_never_mock_resolved_without_token(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_AUTH_TOKEN", raising=False)
    client = SentryClient(api_key=None, organization_slug="org", project_slug="proj")

    result = client.get_issue("SENTRY-999")

    assert result["status"] == "pending"
    assert result["status"] != "resolved"


def test_phase15_1_issue_fingerprint_is_stable() -> None:
    issue_a = {"id": "SENTRY-123", "title": " Neo4j Down ", "culprit": "SRC/CORE/GRAPHITI_CLIENT.PY"}
    issue_b = {"id": "sentry-123", "title": "neo4j down", "culprit": "src/core/graphiti_client.py"}

    assert _issue_fingerprint(issue_a) == _issue_fingerprint(issue_b)


def test_phase15_1_normalization_keeps_required_fields() -> None:
    event = normalize_issue(
        {
            "id": "SENTRY-321",
            "title": "ConnectionRefusedError: database unavailable",
            "culprit": "src/db/client.py",
            "metadata": {"type": "ConnectionRefusedError"},
            "lastSeen": "2026-03-04T20:00:00Z",
            "level": "error",
            "tags": [],
        }
    )

    assert event.event_id == "SENTRY-321"
    assert event.tags["issue_id"] == "SENTRY-321"
    assert event.tags["error_type"] == "ConnectionRefusedError"
    assert event.tags["affected_module"] == "src/db/client.py"
