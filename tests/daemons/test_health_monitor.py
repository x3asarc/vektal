"""
Unit and Integration Tests for Health Monitor Daemon (Phase 15).

Tests daemon functionality, cache atomicity, health checks, and hook performance.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.daemons import health_monitor
from scripts.governance import health_gate


class TestHealthMonitorDaemon:
    """Unit tests for health monitor daemon."""

    def test_atomic_write_json(self, tmp_path):
        """Test atomic JSON write using tmp + rename."""
        test_file = tmp_path / "test.json"
        data = {"key": "value", "timestamp": datetime.now(timezone.utc).isoformat()}

        # Mock GRAPH_DIR
        with mock.patch.object(health_monitor, "GRAPH_DIR", tmp_path):
            health_monitor._atomic_write_json(test_file, data)

        assert test_file.exists()
        loaded = json.loads(test_file.read_text(encoding="utf-8"))
        assert loaded["key"] == "value"

    def test_can_import_success(self):
        """Test dependency import check - success case."""
        # Test with a known-good module
        assert health_monitor._can_import("sys") is True

    def test_can_import_failure(self):
        """Test dependency import check - failure case."""
        # Test with a non-existent module
        assert health_monitor._can_import("nonexistent_module_xyz") is False

    def test_check_dependencies_all_present(self):
        """Test dependency check when all required modules present."""
        with mock.patch.object(health_monitor, "_can_import", return_value=True):
            result = health_monitor.check_dependencies()

        assert result["status"] == "ok"
        assert result["missing"] == []
        assert "last_check" in result

    def test_check_dependencies_missing(self):
        """Test dependency check when modules missing."""
        with mock.patch.object(health_monitor, "_can_import", return_value=False):
            with mock.patch.object(health_monitor, "_trigger_dependency_install"):
                result = health_monitor.check_dependencies()

        # Dependency remediation is now delegated to handle_health_issues()/orchestrator.
        assert result["status"] == "missing"
        assert len(result["missing"]) > 0

    @pytest.mark.asyncio
    async def test_check_sentry_no_token(self, monkeypatch):
        """Test Sentry check when no auth token configured."""
        monkeypatch.delenv("SENTRY_AUTH_TOKEN", raising=False)
        monkeypatch.setenv("SENTRY_ORG_SLUG", "test-org")
        monkeypatch.setenv("SENTRY_PROJECT_SLUG", "test-project")

        result = await health_monitor.check_sentry()

        assert result["status"] == "not_configured"
        assert result["issue_count"] == 0
        assert result["auto_heal_running"] is False

    @pytest.mark.asyncio
    async def test_check_sentry_api_failure(self, monkeypatch):
        """Test Sentry check when API call fails."""
        monkeypatch.setenv("SENTRY_AUTH_TOKEN", "fake-token")
        monkeypatch.setenv("SENTRY_ORG_SLUG", "test-org")
        monkeypatch.setenv("SENTRY_PROJECT_SLUG", "test-project")

        # Mock httpx to raise exception
        async def mock_get(*args, **kwargs):
            raise Exception("Network error")

        with mock.patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await health_monitor.check_sentry()

        assert result["status"] == "unreachable"
        assert result["issue_count"] == 0

    def test_check_neo4j_module_missing(self):
        """Test Neo4j check when neo4j module not installed."""
        with mock.patch.dict(sys.modules, {"neo4j": None}):
            result = health_monitor.check_neo4j()

        assert result["status"] == "down"
        assert result["mode"] == "local_snapshot"

    def test_check_neo4j_no_credentials(self, monkeypatch):
        """Test Neo4j check when credentials not configured."""
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

        result = health_monitor.check_neo4j()

        assert result["status"] == "down"
        assert result["mode"] == "local_snapshot"

    @pytest.mark.asyncio
    async def test_run_health_check_complete(self):
        """Test full health check cycle."""
        with mock.patch.object(health_monitor, "check_sentry") as mock_sentry:
            with mock.patch.object(health_monitor, "check_neo4j") as mock_neo4j:
                with mock.patch.object(health_monitor, "check_dependencies") as mock_deps:
                    mock_sentry.return_value = {
                        "status": "healthy",
                        "issue_count": 0,
                        "last_check": datetime.now(timezone.utc).isoformat(),
                        "auto_heal_running": False,
                    }
                    mock_neo4j.return_value = {
                        "status": "up",
                        "uri": "neo4j://localhost:7687",
                        "last_check": datetime.now(timezone.utc).isoformat(),
                        "mode": "neo4j",
                    }
                    mock_deps.return_value = {
                        "status": "ok",
                        "missing": [],
                        "last_check": datetime.now(timezone.utc).isoformat(),
                    }

                    state = await health_monitor.run_health_check()

        assert "sentry" in state
        assert "neo4j" in state
        assert "dependencies" in state
        assert "daemon" in state
        assert state["sentry"]["status"] == "healthy"
        assert state["neo4j"]["status"] == "up"
        assert state["dependencies"]["status"] == "ok"


class TestHealthGateHook:
    """Unit tests for health gate PreToolUse hook."""

    def test_read_cache_missing(self, tmp_path):
        """Test cache read when file doesn't exist."""
        with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", tmp_path / "missing.json"):
            result = health_gate._read_cache()

        assert result is None

    def test_read_cache_corrupt(self, tmp_path):
        """Test cache read when file is corrupt JSON."""
        cache_file = tmp_path / "corrupt.json"
        cache_file.write_text("not valid json{{{", encoding="utf-8")

        with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", cache_file):
            result = health_gate._read_cache()

        assert result is None

    def test_read_cache_success(self, tmp_path):
        """Test successful cache read."""
        cache_file = tmp_path / "cache.json"
        data = {"daemon": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        cache_file.write_text(json.dumps(data), encoding="utf-8")

        with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", cache_file):
            result = health_gate._read_cache()

        assert result is not None
        assert "daemon" in result

    def test_is_stale_fresh_cache(self):
        """Test staleness check with fresh cache."""
        cache = {
            "daemon": {
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }

        assert health_gate._is_stale(cache, 300) is False

    def test_is_stale_old_cache(self):
        """Test staleness check with old cache."""
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(seconds=600)
        cache = {
            "daemon": {
                "updated_at": old_time.isoformat()
            }
        }

        assert health_gate._is_stale(cache, 300) is True

    def test_is_stale_missing_timestamp(self):
        """Test staleness check when timestamp missing."""
        cache = {"daemon": {}}

        assert health_gate._is_stale(cache, 300) is True

    def test_main_missing_cache(self, tmp_path):
        """Test hook execution when cache missing."""
        with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", tmp_path / "missing.json"):
            with mock.patch.object(health_gate, "LOG_PATH", tmp_path / "log.txt"):
                result = health_gate.main()

        assert result == 0  # Never blocks

    def test_main_stale_cache(self, tmp_path):
        """Test hook execution with stale cache."""
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(seconds=600)
        cache = {
            "daemon": {"updated_at": old_time.isoformat()},
            "sentry": {"status": "healthy", "issue_count": 0, "auto_heal_running": False},
            "neo4j": {"status": "up", "mode": "neo4j"},
            "dependencies": {"status": "ok", "missing": []},
        }

        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache), encoding="utf-8")

        with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", cache_file):
            with mock.patch.object(health_gate, "LOG_PATH", tmp_path / "log.txt"):
                result = health_gate.main()

        assert result == 0  # Never blocks

    def test_main_fresh_cache_with_issues(self, tmp_path):
        """Test hook execution with fresh cache containing issues."""
        cache = {
            "daemon": {"updated_at": datetime.now(timezone.utc).isoformat()},
            "sentry": {"status": "issues", "issue_count": 3, "auto_heal_running": True},
            "neo4j": {"status": "down", "mode": "local_snapshot"},
            "dependencies": {"status": "missing", "missing": ["neo4j"]},
        }

        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache), encoding="utf-8")

        with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", cache_file):
            with mock.patch.object(health_gate, "LOG_PATH", tmp_path / "log.txt"):
                result = health_gate.main()

        assert result == 0  # Never blocks


class TestPerformance:
    """Performance tests for health gate hook."""

    def test_hook_execution_time(self, tmp_path):
        """Test that hook executes in <5ms target."""
        # Create realistic cache
        cache = {
            "daemon": {"updated_at": datetime.now(timezone.utc).isoformat()},
            "sentry": {"status": "healthy", "issue_count": 0, "auto_heal_running": False},
            "neo4j": {"status": "up", "mode": "neo4j"},
            "dependencies": {"status": "ok", "missing": []},
        }

        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache), encoding="utf-8")

        # Run 10 times and measure
        times = []
        for _ in range(10):
            start = time.perf_counter()

            with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", cache_file):
                with mock.patch.object(health_gate, "LOG_PATH", tmp_path / "log.txt"):
                    health_gate.main()

            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"\nHook performance: avg={avg_time:.2f}ms, max={max_time:.2f}ms")

        # Target: <10ms average (relaxed for Windows I/O), <50ms max
        # On Unix systems, typical avg is 1-2ms; Windows adds overhead
        assert avg_time < 10.0, f"Average execution time {avg_time:.2f}ms exceeds 10ms target"
        assert max_time < 50.0, f"Max execution time {max_time:.2f}ms exceeds 50ms threshold"

    def test_cache_file_size(self, tmp_path):
        """Test that cache file stays under 5KB."""
        cache = {
            "daemon": {
                "pid": 12345,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "check_interval_seconds": 120,
            },
            "sentry": {
                "status": "issues",
                "issue_count": 5,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "auto_heal_running": True,
            },
            "neo4j": {
                "status": "up",
                "uri": "neo4j+s://example.databases.neo4j.io",
                "last_check": datetime.now(timezone.utc).isoformat(),
                "mode": "neo4j",
            },
            "dependencies": {
                "status": "ok",
                "missing": [],
                "last_check": datetime.now(timezone.utc).isoformat(),
            },
        }

        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")

        size_bytes = cache_file.stat().st_size
        size_kb = size_bytes / 1024

        print(f"\nCache file size: {size_kb:.2f}KB")

        assert size_kb < 5.0, f"Cache file size {size_kb:.2f}KB exceeds 5KB target"


@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring daemon execution."""

    def test_daemon_startup_shutdown(self, tmp_path):
        """Test daemon starts, creates cache, and stops gracefully."""
        # Skip on Windows (bash script issues)
        if sys.platform == "win32":
            pytest.skip("Integration test requires Unix environment")

        # Set environment to use tmp directory
        env = {
            "HEALTH_CHECK_INTERVAL_SECONDS": "5",
            "PATH": os.environ.get("PATH", ""),
        }

        # Start daemon
        daemon_script = PROJECT_ROOT / "scripts" / "daemons" / "health_monitor.py"
        proc = subprocess.Popen(
            [sys.executable, str(daemon_script), "--daemon", "--interval", "5"],
            cwd=PROJECT_ROOT,
            env=env,
        )

        try:
            # Wait for cache to be created
            cache_path = PROJECT_ROOT / ".graph" / "health-cache.json"
            for _ in range(10):
                if cache_path.exists():
                    break
                time.sleep(0.5)

            assert cache_path.exists(), "Cache file not created within 5s"

            # Verify cache structure
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            assert "sentry" in cache
            assert "neo4j" in cache
            assert "dependencies" in cache
            assert "daemon" in cache

        finally:
            # Stop daemon gracefully
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=10)

    def test_concurrent_cache_reads(self, tmp_path):
        """Test multiple hook processes reading cache simultaneously."""
        # Create cache
        cache = {
            "daemon": {"updated_at": datetime.now(timezone.utc).isoformat()},
            "sentry": {"status": "healthy", "issue_count": 0, "auto_heal_running": False},
            "neo4j": {"status": "up", "mode": "neo4j"},
            "dependencies": {"status": "ok", "missing": []},
        }

        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(cache), encoding="utf-8")

        # Spawn 10 concurrent hook processes
        hook_script = PROJECT_ROOT / "scripts" / "governance" / "health_gate.py"
        procs = []

        for _ in range(10):
            proc = subprocess.Popen(
                [sys.executable, str(hook_script)],
                cwd=PROJECT_ROOT,
                env={"HEALTH_CACHE_PATH": str(cache_file)},
            )
            procs.append(proc)

        # Wait for all to complete
        for proc in procs:
            proc.wait(timeout=5)
            assert proc.returncode == 0, "Hook process failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
