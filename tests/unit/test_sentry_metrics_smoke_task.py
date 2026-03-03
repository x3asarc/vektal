from __future__ import annotations

from unittest.mock import patch

from src.tasks.control import sentry_metrics_smoke


def test_sentry_metrics_smoke_emits_expected_metrics() -> None:
    with patch("src.tasks.control.sentry_count") as mock_count, patch(
        "src.tasks.control.sentry_gauge"
    ) as mock_gauge, patch("src.tasks.control.sentry_distribution") as mock_distribution:
        result = sentry_metrics_smoke(source="test-source", correlation_id="corr-123")

    assert result["status"] == "ok"
    assert result["source"] == "test-source"
    assert result["correlation_id"] == "corr-123"
    assert "workers.sentry.smoke.count" in result["metrics"]
    mock_count.assert_called_once_with(
        "workers.sentry.smoke.count",
        1,
        tags={"source": "test-source"},
    )
    mock_gauge.assert_called_once_with(
        "workers.sentry.smoke.gauge",
        42,
        tags={"source": "test-source"},
    )
    mock_distribution.assert_called_once_with(
        "workers.sentry.smoke.distribution",
        187.5,
        tags={"source": "test-source"},
    )
