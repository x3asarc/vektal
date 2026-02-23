"""
Contract tests for MCP graph server tool surface.
"""

from unittest.mock import patch

from src.graph.mcp_server import (
    _SESSION_CONTEXT,
    get_dependencies_tool,
    initialize_session_context,
    list_tool_contracts,
    query_graph_tool,
    retrieve_intent_tool,
)


def _reset_session_context():
    _SESSION_CONTEXT["initialized"] = False
    _SESSION_CONTEXT["system_context_emitted"] = False
    _SESSION_CONTEXT["conventions"] = []


def test_mcp_server_lists_expected_tools():
    tools = list_tool_contracts()
    names = {tool["name"] for tool in tools}
    assert {"query_graph", "get_dependencies", "retrieve_intent"} <= names


def test_initialize_session_context_loads_top_conventions_once():
    _reset_session_context()
    with patch("src.graph.mcp_server.execute_template") as mock_exec:
        mock_exec.return_value = [
            {"rule": "Always use RFC 7807 errors", "scope": "global", "enforcement": "hard"},
        ]
        first = initialize_session_context()
        second = initialize_session_context()
        assert len(first) == 1
        assert first == second
        assert mock_exec.call_count == 1


def test_query_graph_tool_contract():
    _reset_session_context()
    with patch("src.graph.mcp_server.initialize_session_context") as mock_init:
        mock_init.side_effect = lambda force=False: _SESSION_CONTEXT.update(
            {"initialized": True, "system_context_emitted": False, "conventions": [{"rule": "rule-a"}]}
        ) or _SESSION_CONTEXT["conventions"]
        with patch("src.graph.mcp_server.query_graph") as mock_query:
            mock_query.return_value.data = [{"path": "src/core/synthex_entities.py"}]
            mock_query.return_value.source = "template"
            mock_query.return_value.duration_ms = 12.3
            mock_query.return_value.success = True
            mock_query.return_value.error = None
            mock_query.return_value.conventions_checked = ["rule-a"]

            result = query_graph_tool("what imports src/core/synthex_entities.py")
            assert result["source"] == "template"
            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["conventions_checked"] == ["rule-a"]
            assert "system_context" in result
            assert mock_init.called


def test_get_dependencies_tool_contract():
    _reset_session_context()
    _SESSION_CONTEXT["initialized"] = True
    _SESSION_CONTEXT["conventions"] = [{"rule": "rule-a"}]
    with patch("src.graph.mcp_server.query_graph") as mock_query:
        mock_query.side_effect = [
            type("R", (), {"data": [{"path": "src/a.py", "purpose": "a"}]})(),
            type("R", (), {"data": [{"path": "src/a.py", "purpose": "a"}, {"path": "src/b.py", "purpose": "b"}]})(),
        ]
        result = get_dependencies_tool("src/core/synthex_entities.py", direction="both", depth=1)
        assert result["file"] == "src/core/synthex_entities.py"
        assert result["impact_radius"] == 2
        assert "system_context" in result


def test_retrieve_intent_tool_contract():
    _reset_session_context()
    _SESSION_CONTEXT["initialized"] = True
    _SESSION_CONTEXT["conventions"] = [{"rule": "Do not bypass gates", "scope": "global", "enforcement": "hard"}]
    with patch("src.graph.mcp_server.query_graph") as mock_query:
        mock_query.return_value.data = []
        mock_query.return_value.source = "bridge"
        with patch("src.graph.mcp_server.check_against_conventions") as mock_check:
            mock_check.return_value = []
            result = retrieve_intent_tool("what conventions govern query fallbacks")
            assert result["source"] == "bridge"
            assert result["confidence"] == 0.0
            assert len(result["conventions"]) == 1
            assert "system_context" in result
            assert mock_check.called
