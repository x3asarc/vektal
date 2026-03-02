import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from src.graph.sentry_feedback_loop import SentryFeedbackLoop
from src.models.sandbox_runs import SandboxRun, SandboxVerdict

@pytest.fixture
def mock_sentry():
    return MagicMock()

@pytest.fixture
def db_session():
    with patch("src.graph.sentry_feedback_loop.db.session") as mock:
        yield mock

@pytest.fixture
def mock_run():
    run = MagicMock()
    run.run_id = "run_123"
    run.failure_fingerprint = "SENTRY-1:mod:err"
    run.verdict = SandboxVerdict.GREEN
    run.completed_at = datetime.now(timezone.utc) - timedelta(hours=2)
    run.changed_files = {"a.py": "content"}
    run.confidence = 0.95
    return run

def test_validate_success(mock_sentry, mock_run, db_session):
    # Setup: Issue is resolved, no new activity
    mock_sentry.get_issue.return_value = {
        'status': 'resolved',
        'activity': []
    }
    
    with patch("src.graph.sentry_feedback_loop.SandboxRun.query") as mock_query:
        mock_query.filter.return_value.all.return_value = [mock_run]
        
        with patch("src.graph.sentry_feedback_loop.TemplateExtractor") as mock_extractor_cls:
            mock_extractor = mock_extractor_cls.return_value
            loop = SentryFeedbackLoop(mock_sentry)
            results = loop.validate_pending_remediations()
            
            assert len(results) == 1
            assert results[0]['status'] == 'validated'
            mock_extractor.extract_and_promote.assert_called()

def test_validate_recurring(mock_sentry, mock_run, db_session):
    # Setup: Issue has activity AFTER remediation
    new_activity_date = (mock_run.completed_at + timedelta(minutes=10)).isoformat()
    mock_sentry.get_issue.return_value = {
        'status': 'unresolved',
        'activity': [{'dateCreated': new_activity_date}]
    }
    
    with patch("src.graph.sentry_feedback_loop.SandboxRun.query") as mock_query:
        mock_query.filter.return_value.all.return_value = [mock_run]
        
        loop = SentryFeedbackLoop(mock_sentry)
        results = loop.validate_pending_remediations()
        
        assert len(results) == 1
        assert results[0]['status'] == 'failed'
        assert "issue recurring" in mock_run.rollback_notes

def test_validate_pending(mock_sentry, mock_run, db_session):
    # Setup: Not resolved, but no new activity yet
    mock_sentry.get_issue.return_value = {
        'status': 'unresolved',
        'activity': []
    }
    
    with patch("src.graph.sentry_feedback_loop.SandboxRun.query") as mock_query:
        mock_query.filter.return_value.all.return_value = [mock_run]
        
        loop = SentryFeedbackLoop(mock_sentry)
        results = loop.validate_pending_remediations()
        
        assert len(results) == 1
        assert results[0]['status'] == 'pending'
