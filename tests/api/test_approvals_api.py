import pytest
from src.models.pending_approvals import PendingApproval, ApprovalStatus
from src.models.user import User, UserTier, AccountStatus
from src.api.app import create_openapi_app
from unittest.mock import patch, MagicMock
from flask import url_for

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-key'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True

@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.email = 'admin@example.com'
    return user

def test_list_approvals(client, app):
    with app.app_context():
        # Mock the query
        mock_approval = MagicMock()
        mock_approval.approval_id = "123"
        mock_approval.type = "code_change"
        mock_approval.title = "Fix bug"
        mock_approval.confidence = 0.85
        mock_approval.blast_radius_files = 1
        mock_approval.status = ApprovalStatus.PENDING
        mock_approval.priority = MagicMock(value="normal")
        mock_approval.created_at = MagicMock()
        mock_approval.created_at.isoformat.return_value = "2026-03-02T12:00:00"
        mock_approval.expires_at = None

        with patch('src.api.v1.approvals.PendingApproval.query') as mock_query:
            mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_approval]
            
            response = client.get('/api/v1/approvals/')
            assert response.status_code == 200
            assert len(response.json['approvals']) == 1
            assert response.json['approvals'][0]['approval_id'] == "123"

def test_get_approval_details(client, app):
    with app.app_context():
        mock_approval = MagicMock()
        mock_approval.approval_id = "123"
        mock_approval.type = "code_change"
        mock_approval.title = "Fix bug"
        mock_approval.description = "Detailed description"
        mock_approval.diff = "--- a/file.py\n+++ b/file.py"
        mock_approval.confidence = 0.85
        mock_approval.sandbox_run_id = "run_abc"
        mock_approval.status = ApprovalStatus.PENDING
        mock_approval.priority = MagicMock(value="normal")
        mock_approval.created_at = MagicMock()
        mock_approval.created_at.isoformat.return_value = "2026-03-02T12:00:00"
        mock_approval.expires_at = None
        mock_approval.metadata_json = {"meta": "data"}

        with patch('src.api.v1.approvals.PendingApproval.query') as mock_query:
            mock_query.filter_by.return_value.first_or_404.return_value = mock_approval
            
            response = client.get('/api/v1/approvals/123')
            assert response.status_code == 200
            assert response.json['diff'] == "--- a/file.py\n+++ b/file.py"

def test_approve_flow(client, app, mock_user):
    with app.app_context():
        mock_approval = MagicMock()
        mock_approval.approval_id = "123"
        mock_approval.status = ApprovalStatus.PENDING

        with patch('src.api.v1.approvals.PendingApproval.query') as mock_query:
            mock_query.filter_by.return_value.first_or_404.return_value = mock_approval
            with patch('src.api.v1.approvals.current_user', mock_user):
                response = client.post('/api/v1/approvals/123/approve', json={'note': 'Looks good'})
                assert response.status_code == 200
                mock_approval.approve.assert_called_with(user_id=mock_user.id, note='Looks good')

def test_reject_flow(client, app, mock_user):
    with app.app_context():
        mock_approval = MagicMock()
        mock_approval.approval_id = "123"
        mock_approval.status = ApprovalStatus.PENDING

        with patch('src.api.v1.approvals.PendingApproval.query') as mock_query:
            mock_query.filter_by.return_value.first_or_404.return_value = mock_approval
            with patch('src.api.v1.approvals.current_user', mock_user):
                response = client.post('/api/v1/approvals/123/reject', json={'note': 'Bad'})
                assert response.status_code == 200
                mock_approval.reject.assert_called_with(user_id=mock_user.id, note='Bad')
