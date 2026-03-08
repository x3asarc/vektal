"""
Unit tests for Wave 3 modules (Consistency Checker, Intent Capture, Query Interface).
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from src.graph.consistency_daemon import check_consistency, repair_divergence, ConsistencyReport
from src.graph.intent_capture import IntentRecord, capture_intent
from src.graph.query_interface import query_graph, match_query_to_template


def test_consistency_report_structure():
    """Test that ConsistencyReport initializes with correct defaults."""
    report = ConsistencyReport()
    assert report.is_consistent is True
    assert len(report.missing_from_graph) == 0
    assert isinstance(report.timestamp, datetime)


@patch("src.graph.consistency_daemon.get_graphiti_client")
@patch("src.graph.consistency_daemon.compute_file_hash")
@patch("os.walk")
@patch("os.path.exists")
@patch("os.listdir")
@patch("os.path.isfile")
def test_check_consistency_detects_missing(mock_isfile, mock_listdir, mock_exists, mock_walk, mock_hash, mock_client):
    """Test that missing files are detected."""
    mock_isfile.return_value = False # No files in root
    mock_listdir.return_value = []
    mock_exists.return_value = True
    # Simulate one file on disk
    mock_walk.return_value = [("src", [], ["test.py"])]
    mock_hash.return_value = "fake_hash"
    
    # Client returns empty graph (simulated)
    mock_client.return_value = MagicMock()
    
    report = check_consistency(include_dirs=["src"])
    
    assert report.files_in_filesystem == 1
    assert "src/test.py" in report.missing_from_graph
    assert report.is_consistent is False


def test_repair_divergence_counts():
    """Test that repair logic returns correct counts."""
    report = ConsistencyReport(
        missing_from_graph=["file1.py"],
        stale_in_graph=["file2.py"],
        hash_mismatches=["file3.py"],
        is_consistent=False
    )
    
    result = repair_divergence(report, dry_run=True)
    
    assert result.files_added == 1
    assert result.files_removed == 1
    assert result.files_updated == 1
    assert result.dry_run is True


@patch("src.tasks.graphiti_sync.emit_episode")
def test_capture_intent_queues_task(mock_emit):
    """Test that capture_intent calls emit_episode.delay."""
    record = IntentRecord(
        file_path="src/test.py",
        entity_type="file",
        entity_name="test.py",
        intent="Test implementation",
        reasoning="Because",
        agent="gemini"
    )
    
    capture_intent(record)
    
    assert mock_emit.delay.called
    args, kwargs = mock_emit.delay.call_args
    assert args[0] == "code_intent"
    assert args[1] == "codebase"
    assert args[2]["intent"] == "Test implementation"


def test_match_query_to_template():
    """Test mapping of NL queries to templates."""
    # Imports
    name, params = match_query_to_template("what imports src/core/db.py")
    assert name == "imported_by"
    assert params["file_path"] == "src/core/db.py"
    
    # Phase code
    name, params = match_query_to_template("what implements phase 14")
    assert name == "phase_code"
    assert params["phase"] == "14"


@patch("src.graph.query_interface.execute_template")
def test_query_graph_template_match(mock_execute):
    """Test that query_graph uses templates when matched."""
    mock_execute.return_value = [{"path": "src/dep.py"}]
    
    result = query_graph("what imports src/main.py")
    
    assert result.success is True
    assert result.template_used == "imported_by"
    assert len(result.data) == 1
    assert result.data[0]["path"] == "src/dep.py"
