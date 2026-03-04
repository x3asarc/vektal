from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import mock_open, patch

from src.graph.backend_resolver import (
    BACKEND_ENUM,
    BackendStatus,
    read_runtime_manifest,
    write_runtime_manifest,
)


def _with_manifest(monkeypatch, payload: dict):
    manifest_path = ".graph/runtime-backend-test.json"
    monkeypatch.setattr("src.graph.backend_resolver.MANIFEST_PATH", manifest_path)
    with patch("src.graph.backend_resolver.os.path.exists", return_value=True), patch(
        "src.graph.backend_resolver.open",
        mock_open(read_data=json.dumps(payload)),
    ):
        return read_runtime_manifest()


def test_read_runtime_manifest_supports_legacy_mode_schema(monkeypatch) -> None:
    status = _with_manifest(
        monkeypatch,
        {"mode": "neo4j", "detail": "neo4j+s://example.databases.neo4j.io"},
    )

    assert status is not None
    assert status.backend == BACKEND_ENUM.LOCAL_NEO4J
    assert "neo4j+s://example.databases.neo4j.io" in status.reason
    assert status.checked_at


def test_read_runtime_manifest_ignores_unknown_fields(monkeypatch) -> None:
    status = _with_manifest(
        monkeypatch,
        {
            "backend": "aura",
            "checked_at": "2026-03-03T18:00:00",
            "reason": "Aura reachable",
            "freshness_hours": 0.2,
            "is_degraded": False,
            "probe_latency_ms": 12.5,
            "mode": "legacy-field",
            "detail": "legacy-detail",
        },
    )

    assert status is not None
    assert status.backend == BACKEND_ENUM.AURA
    assert status.reason == "Aura reachable"
    assert status.probe_latency_ms == 12.5


def test_read_runtime_manifest_returns_none_for_unknown_legacy_mode(monkeypatch) -> None:
    status = _with_manifest(monkeypatch, {"mode": "mystery"})

    assert status is None


def test_read_runtime_manifest_supports_backend_neo4j_alias(monkeypatch) -> None:
    status = _with_manifest(
        monkeypatch,
        {"backend": "neo4j", "reason": "legacy backend alias"},
    )

    assert status is not None
    assert status.backend == BACKEND_ENUM.LOCAL_NEO4J
    assert status.reason == "legacy backend alias"


def test_write_runtime_manifest_emits_legacy_compat_fields(monkeypatch) -> None:
    mock_file = mock_open()
    with patch("src.graph.backend_resolver.os.makedirs"), patch(
        "src.graph.backend_resolver.open",
        mock_file,
    ):
        write_runtime_manifest(
            BackendStatus(
                backend=BACKEND_ENUM.SNAPSHOT,
                checked_at=datetime.now().isoformat(),
                reason="snapshot fallback",
                is_degraded=True,
            )
        )

    written = "".join(call.args[0] for call in mock_file().write.call_args_list)
    payload = json.loads(written)
    assert payload["backend"] == "local_snapshot"
    assert payload["mode"] == "local_snapshot"
    assert payload["detail"] == "snapshot fallback"
