import pytest
from pathlib import Path
from src.graph.orchestrate_healers import normalize_sentry_issue, orchestrate_remediation
from src.graph.root_cause_classifier import FailureCategory
from src.graph.sentry_ingestor import ingest_sentry_issue, normalize_sentry_issue as normalize_ingestor_issue
from unittest.mock import MagicMock, patch, AsyncMock
from scripts.daemons import health_monitor

@pytest.mark.asyncio
async def test_infrastructure_failure_flow():
    """Redis connection error -> infrastructure category -> Redis remediator."""
    sentry_issue = {
        'id': 'SENTRY-123',
        'title': 'ConnectionError',
        'culprit': 'src/core/redis.py',
        'type': 'error',
        'metadata': {
            'type': 'ConnectionError',
            'value': 'redis connection refused'
        },
        'entries': [{
            'type': 'exception',
            'data': {
                'values': [{
                    'stacktrace': {
                        'frames': [
                            {'filename': 'src/core/redis.py', 'lineno': 42}
                        ]
                    }
                }]
            }
        }]
    }

    # Mock classifier to ensure infrastructure category
    with patch("src.graph.orchestrate_healers.RootCauseClassifier") as mock_classifier_cls:
        mock_classifier = mock_classifier_cls.return_value
        mock_classifier.classify.return_value = (FailureCategory.INFRASTRUCTURE, 0.95, {"reason": "mock"})
        
        # Mock fixer to avoid actual side effects
        with patch("src.graph.orchestrate_healers.NanoFixerLoop") as mock_fixer_cls:
            mock_fixer = mock_fixer_cls.return_value
            from src.graph.universal_fixer import RemediationResult
            from unittest.mock import AsyncMock
            mock_fixer.fix_service = AsyncMock(return_value=RemediationResult(True, "Mock fix applied", ["Action 1"]))
            
            result = await orchestrate_remediation(sentry_issue, classifier=mock_classifier, fixer=mock_fixer)
            
            assert result['status'] == 'remediated'
            assert result['category'] == 'infrastructure'
            assert result['service'] == 'redis'

@pytest.mark.asyncio
async def test_code_failure_flow():
    """ImportError -> code category -> code_fix remediator."""
    sentry_issue = {
        'id': 'SENTRY-456',
        'title': 'ImportError',
        'culprit': 'src/tasks/enrichment.py',
        'type': 'error',
        'metadata': {
            'type': 'ImportError',
            'value': 'No module named missing_lib'
        }
    }

    with patch("src.graph.orchestrate_healers.RootCauseClassifier") as mock_classifier_cls:
        mock_classifier = mock_classifier_cls.return_value
        mock_classifier.classify.return_value = (FailureCategory.CODE, 0.9, {"reason": "mock"})
        
        with patch("src.graph.orchestrate_healers.NanoFixerLoop") as mock_fixer_cls:
            mock_fixer = mock_fixer_cls.return_value
            from src.graph.universal_fixer import RemediationResult
            from unittest.mock import AsyncMock
            mock_fixer.fix_service = AsyncMock(return_value=RemediationResult(True, "Mock LLM fix", ["Action LLM"]))
            
            result = await orchestrate_remediation(sentry_issue, classifier=mock_classifier, fixer=mock_fixer)
            
            assert result['category'] == 'code'
            assert result['service'] == 'code_fix'

@pytest.mark.asyncio
async def test_config_failure_flow():
    """Timeout -> config category."""
    sentry_issue = {
        'id': 'SENTRY-789',
        'title': 'TimeoutError',
        'culprit': 'src/tasks/enrichment.py',
        'metadata': {
            'type': 'TimeoutError',
            'value': 'Task execution timeout'
        }
    }

    with patch("src.graph.orchestrate_healers.RootCauseClassifier") as mock_classifier_cls:
        mock_classifier = mock_classifier_cls.return_value
        mock_classifier.classify.return_value = (FailureCategory.CONFIG, 0.85, {"reason": "mock"})
        
        with patch("src.graph.orchestrate_healers.NanoFixerLoop") as mock_fixer_cls:
            mock_fixer = mock_fixer_cls.return_value
            from src.graph.universal_fixer import RemediationResult
            from unittest.mock import AsyncMock
            mock_fixer.fix_service = AsyncMock(return_value=RemediationResult(True, "Mock config fix", ["Action Config"]))
            
            result = await orchestrate_remediation(sentry_issue, classifier=mock_classifier, fixer=mock_fixer)
            
            assert result['category'] == 'config'

def test_normalization_integration():
    """Verify Phase 14.3 normalization works with classifier."""
    raw_issue = {
        'id': 'SENTRY-999',
        'title': 'Error',
        'culprit': 'src/test.py',
        'metadata': {'type': 'RuntimeError', 'value': 'test error'}
    }

    normalized = normalize_sentry_issue(raw_issue)
    assert normalized['issue_id'] == 'SENTRY-999'
    assert normalized['error_type'] == 'RuntimeError'
    assert normalized['error_message'] == 'test error'
    assert normalized['affected_module'] == 'src/test.py'


@pytest.mark.asyncio
async def test_ingestor_classifier_link():
    """Verify sentry_ingestor performs normalize -> classifier.classify -> ingest."""
    sentry_issue = {
        "id": "SENTRY-INGEST-1",
        "title": "TaskTimeout",
        "culprit": "src/jobs/sync_worker.py",
        "metadata": {"type": "TimeoutError", "value": "sync timeout while processing"},
    }

    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = (
        FailureCategory.INFRASTRUCTURE,
        0.91,
        {"reason": "timeout keyword"},
    )

    with patch("src.graph.sentry_ingestor.ingest_failure_event", new=AsyncMock(return_value=True)) as mock_ingest:
        ok = await ingest_sentry_issue(sentry_issue, classifier=mock_classifier)

    assert ok is True
    mock_classifier.classify.assert_called_once()
    mock_ingest.assert_awaited_once()
    event = mock_ingest.await_args.args[0]
    normalized = mock_ingest.await_args.kwargs["normalized_issue"]
    assert event.category == "SYNC_TIMEOUT"
    assert normalized["category"] == FailureCategory.INFRASTRUCTURE


def test_ingestor_normalization_shape():
    issue = {"id": "SENTRY-NORM", "culprit": "src/a.py", "metadata": {"type": "ValueError", "value": "bad cfg"}}
    normalized = normalize_ingestor_issue(issue)
    assert normalized["issue_id"] == "SENTRY-NORM"
    assert normalized["error_type"] == "ValueError"
    assert normalized["error_message"] == "bad cfg"


@pytest.mark.asyncio
async def test_health_monitor_trigger_auto_heal_dedupes_same_cycle(monkeypatch):
    cache_path = Path.cwd() / ".graph" / "pytest-health-cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(health_monitor, "HEALTH_CACHE_PATH", cache_path)

    issues = [
        {"id": "SENTRY-1", "title": "Neo4j down", "culprit": "src/core/graphiti_client.py", "level": "error"},
        {"id": "SENTRY-1", "title": "Neo4j down", "culprit": "src/core/graphiti_client.py", "level": "error"},
    ]

    popen_calls = {"count": 0}
    routed_statuses = []

    class _DummyProc:
        pass

    def _fake_popen(*args, **kwargs):
        popen_calls["count"] += 1
        return _DummyProc()

    def _fake_emit(issue, *, routing_status, context_telemetry, detail=""):
        routed_statuses.append(routing_status)

    monkeypatch.setattr("scripts.daemons.health_monitor.subprocess.Popen", _fake_popen)
    monkeypatch.setattr("scripts.daemons.health_monitor._emit_issue_routed_event", _fake_emit)

    try:
        result = await health_monitor._trigger_auto_heal(issues)
    finally:
        cache_path.unlink(missing_ok=True)

    assert popen_calls["count"] == 1
    assert result["auto_heal_running"] is True
    assert result["active_issue_ids"] == ["SENTRY-1"]
    assert "triggered" in routed_statuses
    assert "skipped_duplicate_same_cycle" in routed_statuses


@pytest.mark.asyncio
async def test_health_monitor_check_sentry_returns_issue_telemetry(monkeypatch):
    monkeypatch.setenv("SENTRY_AUTH_TOKEN", "token")
    monkeypatch.setenv("SENTRY_ORG_SLUG", "org")
    monkeypatch.setenv("SENTRY_PROJECT_SLUG", "proj")

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return [{"id": "SENTRY-42", "title": "Timeout", "culprit": "src/jobs/sync.py", "level": "error"}]

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("scripts.daemons.health_monitor.httpx.AsyncClient", lambda *args, **kwargs: _FakeClient())
    monkeypatch.setattr(
        "scripts.daemons.health_monitor._trigger_auto_heal",
        AsyncMock(
            return_value={
                "auto_heal_running": True,
                "active_issue_ids": ["SENTRY-42"],
                "active_issue_fingerprints": ["sentry-42|timeout|src/jobs/sync.py"],
                "last_triggered_at": "2026-03-04T00:00:00Z",
                "context_telemetry": health_monitor._default_context_telemetry(),
            }
        ),
    )

    result = await health_monitor.check_sentry()

    assert result["status"] == "issues"
    assert result["auto_heal_running"] is True
    assert result["active_issue_ids"] == ["SENTRY-42"]
    assert "context_telemetry" in result
    assert "graph_attempted" in result["context_telemetry"]
