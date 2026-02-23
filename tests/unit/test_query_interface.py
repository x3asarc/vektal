"""
Unit tests for query interface provenance and discrepancy behavior.
"""

from unittest.mock import patch, MagicMock

from src.graph.query_interface import query_graph


def test_query_graph_template_success_emits_trace():
    with patch("src.graph.query_interface.execute_template", return_value=[{"path": "src/core/embeddings.py"}]):
        with patch("src.tasks.graphiti_sync.emit_episode") as mock_emit:
            mock_emit.delay = MagicMock()

            result = query_graph("imports")

            assert result.success is True
            assert result.template_used == "imports"
            assert result.source == "template"
            assert isinstance(result.duration_ms, float)
            assert mock_emit.delay.called


def test_query_graph_flags_discrepancy_on_filesystem_fallback():
    with patch("src.graph.query_interface.execute_template", return_value=[]):
        with patch("src.tasks.graphiti_sync.emit_episode") as mock_emit:
            mock_emit.delay = MagicMock()

            result = query_graph("what imports src/core/synthex_entities.py")

            assert result.success is True
            assert result.source == "filesystem_fallback"
            assert result.discrepancy_flagged is True
            assert len(result.data) == 1
            assert result.data[0]["path"] == "src/core/synthex_entities.py"
            assert mock_emit.delay.called


def test_query_graph_uses_bridge_for_unmatched_queries():
    with patch("src.graph.query_interface.search_then_expand") as mock_bridge:
        mock_bridge.return_value.initial_nodes = [{"path": "src/core/codebase_schema.py"}]
        mock_bridge.return_value.expanded_nodes = []
        mock_bridge.return_value.total_tokens_estimated = 50
        mock_bridge.return_value.truncated = False
        mock_bridge.return_value.relationships_followed = ["IMPORTS"]

        with patch("src.tasks.graphiti_sync.emit_episode") as mock_emit:
            mock_emit.delay = MagicMock()
            result = query_graph("explain architecture constraints around schema initialization")

            assert result.query_type == "natural_language"
            assert result.source == "bridge"
            assert result.success is True
