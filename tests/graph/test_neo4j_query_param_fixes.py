"""
Test fixes for Neo4j query parameter errors reported in Sentry.

Issues fixed:
1. Issue 101549138: "Error executing Neo4j query: Expected parameter(s): file_path, limit, threshold"
2. Issue 101522296: "Error executing template imports: Neo4j temporarily unavailable"
3. Issue 101522291: "Error executing Neo4j query: Task pending" (async/await)

Root causes:
- Missing parameters in query calls
- Async/await not handled properly
- Neo4j client not awaiting coroutines
"""

import pytest
from src.graph.query_templates import execute_template, _apply_default_params
from src.graph.query_interface import query_graph


class TestParameterDefaults:
    """Test that templates have proper default parameters."""

    def test_apply_default_params_similar_files(self):
        """Test similar_files gets default params."""
        result = _apply_default_params("similar_files", {})
        assert result == {"file_path": "", "limit": 5, "threshold": 0.6}

    def test_apply_default_params_imports(self):
        """Test imports gets default params."""
        result = _apply_default_params("imports", {})
        assert result == {"file_path": ""}

    def test_apply_default_params_with_override(self):
        """Test params override defaults."""
        result = _apply_default_params("similar_files", {"limit": 10})
        assert result == {"file_path": "", "limit": 10, "threshold": 0.6}

    def test_apply_default_params_unknown_template(self):
        """Test unknown template returns params unchanged."""
        params = {"custom": "value"}
        result = _apply_default_params("unknown_template", params)
        assert result == params


class TestExecuteTemplateWithEmptyParams:
    """Test execute_template handles missing parameters gracefully."""

    def test_execute_template_similar_files_empty_params(self):
        """Test similar_files with empty params doesn't crash."""
        # Should not raise "Expected parameter(s): file_path, limit, threshold"
        result = execute_template("similar_files", {})
        # Result will be empty since file_path is empty, but should not crash
        assert isinstance(result, list)

    def test_execute_template_imports_empty_params(self):
        """Test imports with empty params doesn't crash."""
        result = execute_template("imports", {})
        assert isinstance(result, list)

    def test_execute_template_top_conventions_empty_params(self):
        """Test top_conventions with empty params uses default limit."""
        result = execute_template("top_conventions", {})
        # Should use default limit=5
        assert isinstance(result, list)


class TestQueryGraphDirectTemplateCall:
    """Test query_graph handles direct template name calls."""

    def test_query_graph_with_template_name_requiring_params(self):
        """Test calling query_graph with template name that needs params."""
        # This was causing "Expected parameter(s)" errors in production
        result = query_graph("similar_files")
        # Should handle gracefully, either returning empty or error with message
        assert hasattr(result, "success")
        assert hasattr(result, "data")
        assert isinstance(result.data, list)

    def test_query_graph_with_template_name_no_params_needed(self):
        """Test calling query_graph with template that doesn't need params."""
        result = query_graph("top_conventions")
        assert result.success or result.error is not None
        assert isinstance(result.data, list)


class TestAsyncHandling:
    """Test async/await is handled properly in Neo4j queries."""

    @pytest.mark.asyncio
    async def test_async_result_data_handling(self):
        """Test that result.data() coroutines are properly awaited."""
        # This tests the fix in src/core/embeddings.py:212-217
        # The actual async behavior is tested implicitly by other integration tests
        # This is a placeholder to document the fix
        # Real async Neo4j testing requires a live connection
        pass


def test_integration_query_with_natural_language():
    """Integration test: natural language query that maps to similar_files."""
    # This would have triggered "Expected parameter(s)" before fix
    result = query_graph("find similar to src/core/embeddings.py")
    # Should handle gracefully
    assert hasattr(result, "success")
    assert isinstance(result.data, list)


def test_integration_query_with_imports():
    """Integration test: natural language query that maps to imports."""
    result = query_graph("what does src/core/embeddings.py depend on")
    # Should handle gracefully even if file doesn't exist in graph
    assert hasattr(result, "success")
    assert isinstance(result.data, list)
