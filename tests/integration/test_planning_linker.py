"""
Integration tests for planning linkage.
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from src.graph.commit_parser import parse_commit_message, get_commits_for_files, CommitInfo
from src.graph.planning_linker import link_commit_to_plan, detect_natural_references, resolve_plan_path


def test_commit_phase_plan_extraction():
    """Test various commit message formats."""
    # Phase-Plan
    info = parse_commit_message("feat(13.2-03): add graph oracle adapter")
    assert info.phase_number == "13.2"
    assert info.plan_number == "03"
    assert info.commit_type == "feat"
    
    # Phase-only
    info = parse_commit_message("docs(phase-12): update tier documentation")
    assert info.phase_number == "12"
    assert info.plan_number is None
    
    # Requirement ID
    info = parse_commit_message("refactor(CHAT-05): improve message handling")
    assert info.requirement_id == "CHAT-05"
    
    # Combined (Phase-Plan + Requirement)
    info = parse_commit_message("feat(14-01): implement GRAPH-01")
    assert info.phase_number == "14"
    assert info.plan_number == "01"
    assert info.requirement_id == "GRAPH-01"


@patch("os.path.exists")
@patch("os.listdir")
def test_resolve_plan_path(mock_listdir, mock_exists):
    """Test resolution of phase/plan numbers to file paths."""
    mock_exists.side_effect = lambda p: True
    mock_listdir.return_value = ["14-continuous-optimization-learning", "13.2-oracle-framework-reuse"]
    
    # Resolve 14-01
    path = resolve_plan_path("14", "01")
    assert "14-continuous-optimization-learning/14-01-PLAN.md" in path
    
    # Resolve 13.2-03
    path = resolve_plan_path("13.2", "03")
    assert "13.2-oracle-framework-reuse/13.2-03-PLAN.md" in path


@patch("src.graph.planning_linker.resolve_plan_path")
def test_auto_link_from_commit(mock_resolve):
    """Test that commits create IMPLEMENTS edges."""
    mock_resolve.return_value = ".planning/phases/14-continuous/14-01-PLAN.md"
    
    info = CommitInfo(
        message="feat(14-01): implement schema",
        commit_type="feat",
        phase_number="14",
        plan_number="01",
        description="implement schema"
    )
    
    changed_files = ["src/core/schema.py", "src/graph/init.py"]
    edges = link_commit_to_plan(info, changed_files)
    
    assert len(edges) == 2
    assert edges[0].code_path == "src/core/schema.py"
    assert edges[0].plan_path == ".planning/phases/14-continuous/14-01-PLAN.md"
    assert "Commit: feat(14-01): implement schema" in edges[0].evidence


@patch("src.graph.planning_linker.resolve_plan_path")
@patch("os.path.exists")
def test_natural_reference_detection(mock_exists, mock_resolve):
    """Test detection of references in code comments."""
    mock_exists.return_value = True
    mock_resolve.return_value = ".planning/phases/13.2-oracle/13.2-01-PLAN.md"
    
    file_content = """
    # Related to Phase 13.2-01
    def some_function():
        # See .planning/phases/14-continuous/14-04-PLAN.md
        pass
    """
    file_path = "src/test.py"
    
    edges = detect_natural_references(file_content, file_path)
    
    # Expected 2 edges: one for 13.2-01 and one for the direct path
    assert len(edges) == 2
    
    paths = [e.doc_path for e in edges]
    assert ".planning/phases/13.2-oracle/13.2-01-PLAN.md" in paths
    assert ".planning/phases/14-continuous/14-04-PLAN.md" in paths


@patch("subprocess.run")
def test_get_commits_for_files(mock_run):
    """Test getting commits for files from git log."""
    mock_run.return_value = MagicMock(
        stdout="HASH1\nfeat(14-01): test commit\nBody\n---END-COMMIT---\n",
        check=True
    )
    
    commits = get_commits_for_files(["src/test.py"])
    
    assert len(commits) == 1
    assert commits[0].phase_number == "14"
    assert commits[0].plan_number == "01"
    assert "feat(14-01): test commit" in commits[0].message
