"""Unit tests for deferred tool loading."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
from src.graph.mcp_server import list_tool_contracts, _search_tools_handler


def test_list_tool_contracts_respects_deferred_loading():
    """Verify only base tools are returned when deferred_loading is enabled."""
    mock_config = {
        "mcp_server": {
            "deferred_loading": True,
            "base_tools": ["search_tools"]
        }
    }
    
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=json.dumps(mock_config))
    ):
        
        tools = list_tool_contracts()
        
        assert len(tools) == 1
        assert tools[0]["name"] == "search_tools"


def test_list_tool_contracts_loads_all_if_disabled():
    """Verify all tools are returned when deferred_loading is disabled."""
    mock_config = {
        "mcp_server": {
            "deferred_loading": False
        }
    }
    
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=json.dumps(mock_config))
    ):
        
        tools = list_tool_contracts()
        
        # We have at least 4 tools defined now
        assert len(tools) >= 4
        names = [t["name"] for t in tools]
        assert "query_graph" in names
        assert "search_tools" in names


def test_search_tools_returns_full_schema():
    """Verify _search_tools_handler returns fullSchema for deferred loading."""
    mock_results = [
        {
            "name": "test_tool",
            "description": "Test tool description",
            "schema": json.dumps({"name": "test_tool", "inputSchema": {"type": "object"}}),
            "examples": "[]",
            "score": 0.9
        }
    ]

    with (
        patch("src.core.embeddings.generate_embedding", return_value=[0.1] * 384),
        patch("src.graph.query_templates.execute_template", return_value=mock_results)
    ):
        
        result = _search_tools_handler(query="test")
        
        assert len(result["tools"]) == 1
        tool = result["tools"][0]
        assert "fullSchema" in tool
        assert tool["fullSchema"]["name"] == "test_tool"
        assert "inputSchema" in tool["fullSchema"]
