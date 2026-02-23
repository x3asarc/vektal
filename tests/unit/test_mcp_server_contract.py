"""
Contract tests for MCP graph server tool surface.
"""

from unittest.mock import patch

from src.graph.mcp_server import (
    list_tool_contracts,
    query_graph_tool,
    get_dependencies_tool,
    retrieve_intent_tool,
)


def test_mcp_server_lists_expected_tools():
    tools = list_tool_contracts()
    names = {tool["name"] for tool in tools}
    assert {"query_graph", "get_dependencies", "retrieve_intent"} <= names


def test_query_graph_tool_contract():
    with patch("src.graph.mcp_server.query_graph") as mock_query:
        mock_query.return_value.data = [{"path": "src/core/synthex_entities.py"}]
        mock_query.return_value.source = "template"
        mock_query.return_value.duration_ms = 12.3
        mock_query.return_value.success = True
        mock_query.return_value.error = None

        result = query_graph_tool("what imports src/core/synthex_entities.py")
        assert result["source"] == "template"
        assert result["success"] is True
        assert len(result["results"]) == 1


def test_get_dependencies_tool_contract():
    with patch("src.graph.mcp_server.query_graph") as mock_query:
        mock_query.side_effect = [
            type("R", (), {"data": [{"path": "src/a.py", "purpose": "a"}]})(),
            type("R", (), {"data": [{"path": "src/a.py", "purpose": "a"}, {"path": "src/b.py", "purpose": "b"}]})(),
        ]
        result = get_dependencies_tool("src/core/synthex_entities.py", direction="both", depth=1)
        assert result["file"] == "src/core/synthex_entities.py"
        assert result["impact_radius"] == 2


def test_retrieve_intent_tool_contract():
    with patch("src.graph.mcp_server.query_graph") as mock_query:
        mock_query.return_value.data = []
        mock_query.return_value.source = "bridge"
        result = retrieve_intent_tool("what conventions govern query fallbacks")
        assert result["source"] == "bridge"
        assert result["confidence"] == 0.0
