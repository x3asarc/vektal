"""Contract test for ops sentry metrics smoke endpoint."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.user import AccountStatus, User, UserTier
from tests.api.conftest import TestConfig


@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    with client.application.app_context():
        user = User(
            email="ops-smoke@example.com",
            tier=UserTier.TIER_2,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client


def test_ops_sentry_metrics_smoke_queues_task(authenticated_client):
    with patch("src.celery_app.app.send_task", return_value=SimpleNamespace(id="task-123")) as mock_send:
        response = authenticated_client.post(
            "/api/v1/ops/sentry-metrics-smoke",
            json={"source": "contract-test", "queue": "control"},
            headers={"X-Correlation-Id": "corr-smoke-1"},
        )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["status"] == "queued"
    assert payload["task_id"] == "task-123"
    assert payload["queue"] == "control"
    assert payload["correlation_id"] == "corr-smoke-1"

    mock_send.assert_called_once_with(
        "src.tasks.control.sentry_metrics_smoke",
        kwargs={"source": "contract-test", "correlation_id": "corr-smoke-1"},
        queue="control",
    )
