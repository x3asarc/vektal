"""Unit tests for batch MCP tools."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from src.graph.mcp_server import dispatch_tool_call


@pytest.mark.asyncio
async def test_batch_query_handler_success():
    """Verify batch_query calls query_graph multiple times and aggregates."""
    mock_result = MagicMock()
    mock_result.data = [{"path": "file1.py"}]
    mock_result.success = True
    mock_result.source = "template"

    with patch("src.graph.batch_handlers.query_graph", return_value=mock_result):
        result = await dispatch_tool_call("batch_query", {
            "queries": ["query 1", "query 2"],
            "aggregate_mode": "separate"
        })

        assert result["total_queries"] == 2
        assert result["successful"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["query"] == "query 1"
        assert result["results"][1]["query"] == "query 2"


@pytest.mark.asyncio
async def test_batch_query_handler_merged():
    """Verify batch_query with aggregate_mode='merged' dedupes results."""
    mock_result1 = MagicMock()
    mock_result1.data = [{"path": "common.py", "type": "file"}]
    mock_result1.success = True
    
    mock_result2 = MagicMock()
    mock_result2.data = [{"path": "common.py", "type": "file"}, {"path": "unique.py"}]
    mock_result2.success = True

    with patch("src.graph.batch_handlers.query_graph") as mock_qg:
        mock_qg.side_effect = [mock_result1, mock_result2]
        
        result = await dispatch_tool_call("batch_query", {
            "queries": ["q1", "q2"],
            "aggregate_mode": "merged"
        })

        assert result["mode"] == "merged"
        assert len(result["results"]) == 2  # common.py (deduped) + unique.py


@pytest.mark.asyncio
async def test_batch_dependencies_handler():
    """Verify batch_dependencies aggregates from multiple files."""
    mock_deps1 = {"dependencies": [{"path": "dep1.py", "purpose": "util"}]}
    mock_deps2 = {"dependencies": [{"path": "dep1.py", "purpose": "util"}, {"path": "dep2.py"}]}

    # patch get_dependencies_tool in mcp_server where it is defined/imported
    with patch("src.graph.mcp_server.get_dependencies_tool", side_effect=[mock_deps1, mock_deps2]):
        result = await dispatch_tool_call("batch_dependencies", {
            "file_paths": ["file1.py", "file2.py"]
        })

        assert result["total_files"] == 2
        assert result["successful"] == 2
        # dep1.py (deduped by path+purpose) + dep2.py
        assert len(result["combined_dependencies"]) == 2
        assert result["impact_radius"] == 2
