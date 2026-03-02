import pytest
from src.graph.orchestrate_healers import normalize_sentry_issue, orchestrate_remediation
from src.graph.root_cause_classifier import FailureCategory
from src.graph.sentry_ingestor import ingest_sentry_issue, normalize_sentry_issue as normalize_ingestor_issue
from unittest.mock import MagicMock, patch, AsyncMock

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
