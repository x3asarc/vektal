"""Unit tests for compact output and scoring multipliers."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from src.graph.search_expand_bridge import serialize_node, score_node, apply_temporal_decay


def test_serialize_node_compact():
    """Verify serialize_node strips verbose fields in compact mode."""
    node = {
        "path": "src/core/graphiti_client.py",
        "entity_type": "File",
        "description": "This is a very long description that should be truncated when generating a summary for the compact output mode."
    }
    
    # Full mode
    full = serialize_node(node, compact=False)
    assert full == node
    assert "description" in full
    
    # Compact mode
    compact = serialize_node(node, compact=True)
    assert "description" not in compact
    assert "path" in compact
    assert "type" in compact
    assert "summary" in compact
    assert len(compact["summary"]) <= 100
    assert compact["summary"].endswith("...")


def test_score_node_multipliers():
    """Verify edge-type multipliers affect scoring correctly."""
    base_score = 1.0
    
    # IMPLEMENTS should increase score (1.3x)
    implements_score = score_node(base_score, edge_type="IMPLEMENTS")
    assert implements_score > base_score
    assert implements_score == pytest.approx(1.3)
    
    # REFERENCES should decrease score (0.7x)
    references_score = score_node(base_score, edge_type="REFERENCES")
    assert references_score < base_score
    assert references_score == pytest.approx(0.7)
    
    # Unknown should not change score
    unknown_score = score_node(base_score, edge_type="UNKNOWN")
    assert unknown_score == base_score


def test_temporal_decay():
    """Verify scores decay over time."""
    base_score = 1.0
    now = datetime.now(timezone.utc)
    
    # Recent node (no decay)
    recent_score = apply_temporal_decay(base_score, now.isoformat())
    assert recent_score == pytest.approx(base_score)
    
    # 6-month-old node (~180 days)
    # decay = exp(-0.003 * 180) = exp(-0.54) ~= 0.58
    six_months_ago = (now - timedelta(days=180)).isoformat()
    old_score = apply_temporal_decay(base_score, six_months_ago)
    assert old_score < base_score
    assert old_score == pytest.approx(0.58, rel=0.05)
    
    # 2-year-old node (should be floored at 0.5)
    two_years_ago = (now - timedelta(days=730)).isoformat()
    very_old_score = apply_temporal_decay(base_score, two_years_ago)
    assert very_old_score == 0.5
