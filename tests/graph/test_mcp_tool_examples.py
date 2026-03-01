"""Unit tests for MCP tool input examples."""
from __future__ import annotations

import pytest
from src.graph.mcp_server import list_tool_contracts


def test_mcp_tools_have_examples():
    """Verify all MCP tools have non-empty input_examples."""
    tools = list_tool_contracts()
    assert len(tools) >= 3

    for tool in tools:
        assert "input_examples" in tool, f"Tool {tool['name']} missing input_examples"
        examples = tool["input_examples"]
        assert isinstance(examples, list)
        assert len(examples) > 0, f"Tool {tool['name']} has empty input_examples"

        # Validate examples match schema (basic check)
        schema = tool["inputSchema"]
        required = schema.get("required", [])
        for example in examples:
            assert isinstance(example, dict)
            for req in required:
                assert req in example, f"Example for {tool['name']} missing required field: {req}"


def test_tool_projection_propagates_examples():
    """Verify tool_projection includes input_examples in the output."""
    from src.assistant import tool_projection
    from unittest.mock import MagicMock, patch

    # Mock user with tier_3
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.tier = "tier_3"

    # Mock dependencies to avoid DB access
    with patch("src.assistant.tool_projection._load_registry", return_value=tool_projection._DEFAULT_TOOLS), \
         patch("src.assistant.tool_projection._resolve_enabled_skill_set", return_value=None):
        
        toolset, notes = tool_projection.project_effective_toolset(user=mock_user, store_id=None)

    assert len(toolset) > 0
    found_respond = False
    for tool in toolset:
        assert "input_examples" in tool
        # Some default tools have examples we added
        if tool["tool_id"] == "chat.respond":
            found_respond = True
            assert len(tool["input_examples"]) > 0
            assert tool["input_examples"][0]["content"] == "I have found 5 products matching your search."
    
    assert found_respond, "chat.respond tool not found in effective toolset"
