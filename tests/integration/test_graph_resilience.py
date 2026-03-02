"""
Integration tests for Knowledge Graph Resilience (Phase 14.3).
Verifies the fallback cascade and autonomous remediation logic.
"""

import os
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from src.graph.backend_resolver import resolve_backend, BACKEND_ENUM, write_runtime_manifest, _failure_cache
from src.graph.remediation_registry import registry
from src.assistant.governance.mutation_guard import check_mutation_allowed

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the backend resolver failure cache before each test."""
    _failure_cache.clear()

@pytest.mark.asyncio
async def test_fallback_cascade_order():
    """
    Verifies the cascade: Aura -> Local -> Snapshot.
    We mock the probes to simulate failures.
    """
    # 1. Simulate Aura Success
    with patch("src.graph.infra_probe.probe_aura", new_callable=AsyncMock) as mock_aura:
        mock_aura.return_value = True
        with patch("src.graph.infra_probe.probe_local_neo4j", new_callable=AsyncMock) as mock_local:
            mock_local.return_value = False
            status = await resolve_backend(force=True)
            assert status.backend == BACKEND_ENUM.AURA

    # 2. Simulate Aura Fail, Local Success
    _failure_cache.clear()
    with patch("src.graph.infra_probe.probe_aura", new_callable=AsyncMock) as mock_aura:
        mock_aura.return_value = False
        with patch("src.graph.infra_probe.probe_local_neo4j", new_callable=AsyncMock) as mock_local:
            mock_local.return_value = True
            status = await resolve_backend(force=True)
            assert status.backend == BACKEND_ENUM.LOCAL_NEO4J

    # 3. Simulate Total Failure -> Snapshot
    _failure_cache.clear()
    with patch("src.graph.infra_probe.probe_aura", new_callable=AsyncMock) as mock_aura:
        mock_aura.return_value = False
        with patch("src.graph.infra_probe.probe_local_neo4j", new_callable=AsyncMock) as mock_local:
            mock_local.return_value = False
            with patch("src.graph.backend_resolver.attempt_docker_start", new_callable=AsyncMock) as mock_start:
                mock_start.return_value = False
                status = await resolve_backend(force=True)
                assert status.backend == BACKEND_ENUM.SNAPSHOT

@pytest.mark.asyncio
async def test_docker_auto_start_remediation():
    """
    Verifies that resolve_backend attempts to start Docker if local probe fails.
    """
    with patch("src.graph.infra_probe.probe_aura", new_callable=AsyncMock) as mock_aura:
        mock_aura.return_value = False
        with patch("src.graph.infra_probe.probe_local_neo4j", new_callable=AsyncMock) as mock_probe:
            # First probe fails, second probe (after start) succeeds
            mock_probe.side_effect = [False, True]
            
            with patch("src.graph.backend_resolver.attempt_docker_start", new_callable=AsyncMock) as mock_start:
                mock_start.return_value = True
                status = await resolve_backend(force=True)
                
                assert mock_start.called
                assert status.backend == BACKEND_ENUM.LOCAL_NEO4J
                assert "started via Docker" in status.reason

@pytest.mark.asyncio
async def test_mutation_guard_enforcement():
    """
    Verifies that MutationGuard correctly blocks write operations in snapshot mode.
    """
    # Simulate snapshot mode in manifest
    from src.graph.backend_resolver import BackendStatus
    
    mock_manifest = BackendStatus(
        backend=BACKEND_ENUM.SNAPSHOT,
        checked_at=datetime.now().isoformat(),
        reason="Test snapshot mode",
        is_degraded=True
    )
    
    with patch("src.assistant.governance.mutation_guard.read_runtime_manifest", return_value=mock_manifest):
        allowed, reason = check_mutation_allowed()
        assert allowed is False
        assert "SNAPSHOT" in reason

@pytest.mark.asyncio
async def test_registry_tool_resolution():
    """
    Verifies that all required remediation tools are in the registry.
    """
    registry.auto_discover()
    required_tools = ["aura", "docker", "local_snapshot", "graph_sync"]
    
    for tool_name in required_tools:
        tool = registry.get_tool(tool_name)
        assert tool is not None
        assert tool.service_name == tool_name
