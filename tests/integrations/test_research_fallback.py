"""Unit tests for research tools and fallback cascade."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from src.graph.research_tools import research_vendor, search_documentation


@pytest.mark.asyncio
async def test_research_vendor_perplexity_success():
    """Verify fallback to Perplexity when Firecrawl is skipped/fails."""
    mock_perplexity_res = {
        "status": "success",
        "answer": "Perplexity found information about Pentart.",
        "citations": ["https://pentart.hu"]
    }

    with patch("src.integrations.perplexity_client.PerplexityClient.search", return_value=mock_perplexity_res):
        # We skip Firecrawl for simplicity in this test (limiter or logic)
        result = await research_vendor("pentart", "API changes", use_firecrawl=False)

        assert result["source"] == "perplexity"
        assert result["status"] == "success"
        assert "Pentart" in result["content"]
        assert result["fallback_used"] is True


@pytest.mark.asyncio
async def test_research_vendor_local_fallback():
    """Verify fallback to local graph when external tools fail/are unavailable."""
    mock_query_res = MagicMock()
    mock_query_res.data = [{"rule": "Use Pentart SKU pattern"}]
    mock_query_res.success = True

    with (
        patch("src.integrations.perplexity_client.PerplexityClient.search", return_value={"status": "error"}),
        patch("src.graph.research_tools.query_graph", return_value=mock_query_res)
    ):
        
        result = await research_vendor("pentart", "conventions", use_firecrawl=False)

        assert result["source"] == "local_graph"
        assert "Pentart" in result["content"]


@pytest.mark.asyncio
async def test_search_documentation_perplexity():
    """Verify search_documentation uses Perplexity."""
    mock_perplexity_res = {
        "status": "success",
        "answer": "Doc content for Neo4j.",
        "citations": []
    }

    with patch("src.integrations.perplexity_client.PerplexityClient.search", return_value=mock_perplexity_res):
        result = await search_documentation("vector search", library="Neo4j")

        assert result["status"] == "success"
        assert "Neo4j" in result["answer"]
        assert "Neo4j" in result["query"]
