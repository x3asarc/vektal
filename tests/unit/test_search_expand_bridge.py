"""
Unit tests for search-then-expand bridge.
"""

from unittest.mock import patch

from src.graph.search_expand_bridge import BridgeConfig, search_then_expand


def test_bridge_respects_max_initial_nodes():
    fake_nodes = [{"path": f"src/file_{i}.py", "entity_type": "File", "score": 0.9} for i in range(10)]
    with patch("src.graph.search_expand_bridge.similarity_search", return_value=fake_nodes):
        result = search_then_expand(
            "find similar architecture files",
            query_embedding=[0.0] * 384,
            config=BridgeConfig(max_initial_nodes=5),
        )
        assert len(result.initial_nodes) == 5


def test_bridge_respects_token_budget():
    fake_nodes = [{"path": "a" * 10000 + ".py", "entity_type": "File", "score": 0.9}]
    with patch("src.graph.search_expand_bridge.similarity_search", return_value=fake_nodes):
        result = search_then_expand(
            "oversized context",
            query_embedding=[0.0] * 384,
            config=BridgeConfig(max_initial_nodes=5, max_context_tokens=50),
        )
        assert result.truncated is True
        assert result.total_tokens_estimated > 50


def test_bridge_deduplicates_expanded_nodes():
    fake_nodes = [{"path": "src/core/synthex_entities.py", "entity_type": "File", "score": 0.9}]

    def fake_execute(template_name, params):
        return [
            {"path": "src/core/synthex_entities.py", "purpose": "duplicate"},
            {"path": "src/core/graphiti_client.py", "purpose": "new"},
        ]

    with patch("src.graph.search_expand_bridge.similarity_search", return_value=fake_nodes):
        with patch("src.graph.search_expand_bridge.execute_template", side_effect=fake_execute):
            result = search_then_expand(
                "what imports src/core/synthex_entities.py",
                query_embedding=[0.0] * 384,
            )
            paths = [item.get("path") for item in result.expanded_nodes]
            assert "src/core/synthex_entities.py" not in paths
            assert "src/core/graphiti_client.py" in paths
