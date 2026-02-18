"""Phase 13-03 observability correlation and SLI contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.assistant.deployment.observability import compute_availability_sli, resolve_correlation_id
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
            email="ops-observability@example.com",
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


def test_resolve_correlation_id_uses_input_or_uuid_fallback():
    assert resolve_correlation_id(provided="corr-explicit") == "corr-explicit"
    generated = resolve_correlation_id()
    assert generated.startswith("corr-")
    assert len(generated) > 10


def test_compute_availability_sli_uses_locked_formula_and_error_budget_gate():
    result = compute_availability_sli(
        successful_requests=980,
        total_requests=1000,
        user_errors=20,
        downtime_seconds_30d=1200,
    )
    assert result.denominator == 980
    assert result.sli == pytest.approx(1.0)
    assert result.freeze_required is False
    assert result.budget_remaining_seconds_30d == 1392

    exhausted = compute_availability_sli(
        successful_requests=900,
        total_requests=1000,
        user_errors=10,
        downtime_seconds_30d=3000,
    )
    assert exhausted.denominator == 990
    assert exhausted.sli == pytest.approx(900 / 990)
    assert exhausted.freeze_required is True
    assert exhausted.budget_remaining_seconds_30d == 0


def test_ops_sli_endpoint_returns_correlation_and_snapshot(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/ops/observability/sli",
        json={
            "successful_requests": 995,
            "total_requests": 1000,
            "user_errors": 3,
            "downtime_seconds_30d": 60,
        },
        headers={"X-Correlation-Id": "corr-ops-sli"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["correlation_id"] == "corr-ops-sli"
    assert payload["sli"]["denominator"] == 997
    assert payload["sli"]["availability_sli"] == pytest.approx(995 / 997)
    assert payload["sli"]["error_budget_seconds_30d"] == 2592
