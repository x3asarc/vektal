"""Unit tests for search_tools MCP tool."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
from src.graph.mcp_server import _search_tools_handler


def test_search_tools_handler_calls_templates():
    """Verify search_tools_handler calls the correct templates and formats results."""
    mock_results = [
        {
            "name": "product_mutation_tool",
            "description": "Update product prices and inventory",
            "schema": json.dumps({"type": "object", "properties": {"sku": {"type": "string"}}}),
            "examples": json.dumps([{"sku": "ABC", "action": "update_price"}]),
            "score": 0.95
        }
    ]

    with patch("src.core.embeddings.generate_embedding", return_value=[0.1] * 384), \
         patch("src.graph.query_templates.execute_template", return_value=mock_results) as mock_exec:
        
        result = _search_tools_handler(query="update price", tier=2, top_k=5)

        # Verify template call
        mock_exec.assert_called_once()
        args, kwargs = mock_exec.call_args
        assert args[0] == "tool_search"
        assert args[1]["tier"] == 2
        assert args[1]["top_k"] == 5
        assert len(args[1]["query_embedding"]) == 384

        # Verify result formatting
        assert result["query"] == "update price"
        assert result["tier_filter"] == 2
        assert len(result["tools"]) == 1
        tool = result["tools"][0]
        assert tool["name"] == "product_mutation_tool"
        assert tool["schema"]["type"] == "object"
        assert len(tool["examples"]) == 1
        assert tool["relevance_score"] == 0.95


def test_search_tools_handler_fallback_to_text():
    """Verify fallback to text search if vector search returns no results."""
    mock_text_results = [
        {
            "name": "text_match_tool",
            "description": "Found via text search",
            "schema": "{}",
            "examples": "[]",
            "score": 1.0
        }
    ]

    with patch("src.core.embeddings.generate_embedding", return_value=[0.1] * 384), \
         patch("src.graph.query_templates.execute_template") as mock_exec:
        
        # First call (tool_search) returns empty, second (tool_search_text) returns mock_text_results
        mock_exec.side_effect = [[], mock_text_results]
        
        result = _search_tools_handler(query="graph query")

        assert mock_exec.call_count == 2
        assert mock_exec.call_args_list[0][0][0] == "tool_search"
        assert mock_exec.call_args_list[1][0][0] == "tool_search_text"
        assert result["tools"][0]["name"] == "text_match_tool"


def test_search_tools_handler_handles_parse_errors():
    """Verify handler skips records with invalid JSON."""
    mock_bad_results = [
        {
            "name": "bad_tool",
            "description": "Invalid JSON in schema",
            "schema": "{ invalid }",
            "examples": "[]",
            "score": 0.8
        },
        {
            "name": "good_tool",
            "description": "Valid record",
            "schema": "{}",
            "examples": "[]",
            "score": 0.9
        }
    ]

    with patch("src.core.embeddings.generate_embedding", return_value=[0.1] * 384), \
         patch("src.graph.query_templates.execute_template", return_value=mock_bad_results):
        
        result = _search_tools_handler(query="test")

        # Should only have one tool (the good one)
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "good_tool"
