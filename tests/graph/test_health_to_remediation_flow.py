"""Integration tests for health monitor → orchestrator → remediator flow."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, call
from src.graph.remediation_registry import RemediationRegistry
from src.graph.remediators.dependency_remediator import DependencyRemediator
from src.graph.remediators.neo4j_health_remediator import Neo4jHealthRemediator


@pytest.mark.asyncio
async def test_registry_discovers_new_remediators():
    """Test that new remediators are auto-discovered by registry."""
    registry = RemediationRegistry()
    registry.auto_discover()

    # Verify new remediators are registered
    assert "dependencies" in registry.list_tools()
    assert "neo4j_health" in registry.list_tools()

    # Verify they can be retrieved
    dep_tool = registry.get_tool("dependencies")
    assert dep_tool is not None
    assert isinstance(dep_tool, DependencyRemediator)

    neo4j_tool = registry.get_tool("neo4j_health")
    assert neo4j_tool is not None
    assert isinstance(neo4j_tool, Neo4jHealthRemediator)


@pytest.mark.asyncio
async def test_orchestrator_routes_dependency_issue():
    """Test that orchestrator correctly routes dependency issues."""
    from src.graph.orchestrate_healers import route_service_for_classification, CATEGORY_SERVICE_MAP
    from src.graph.root_cause_classifier import FailureCategory

    # Test direct category mapping (highest priority)
    normalized_with_category = {
        "error_message": "Module 'sentry_sdk' not found",
        "affected_module": "dependencies",
        "category": "DEPENDENCY_MISSING",
    }

    service = route_service_for_classification(FailureCategory.CONFIG, normalized_with_category)
    assert service == "dependencies"

    # Test pattern matching for module not found
    normalized_pattern = {
        "error_message": "Module 'sentry_sdk' not found",
        "affected_module": "dependencies",
        "category": "",
    }

    service = route_service_for_classification(FailureCategory.CONFIG, normalized_pattern)
    assert service == "dependencies"

    # Verify category map contains our entries
    assert "DEPENDENCY_MISSING" in CATEGORY_SERVICE_MAP
    assert CATEGORY_SERVICE_MAP["DEPENDENCY_MISSING"] == "dependencies"


@pytest.mark.asyncio
async def test_orchestrator_routes_neo4j_issue():
    """Test that orchestrator correctly routes Neo4j issues."""
    from src.graph.orchestrate_healers import route_service_for_classification, CATEGORY_SERVICE_MAP
    from src.graph.root_cause_classifier import FailureCategory

    # Test direct category mapping
    normalized_category = {
        "error_message": "Neo4j unreachable at bolt://localhost:7687",
        "affected_module": "src.core.graphiti_client",
        "category": "LOCAL_NEO4J_START_FAIL",
    }

    service = route_service_for_classification(FailureCategory.INFRASTRUCTURE, normalized_category)
    assert service == "neo4j_health"

    # Test pattern matching for Neo4j connection issues
    normalized_pattern = {
        "error_message": "neo4j connection unreachable",
        "affected_module": "src.core.graphiti_client",
        "category": "",
    }

    service = route_service_for_classification(FailureCategory.INFRASTRUCTURE, normalized_pattern)
    assert service == "neo4j_health"

    # Verify category map updated
    assert "LOCAL_NEO4J_START_FAIL" in CATEGORY_SERVICE_MAP
    assert CATEGORY_SERVICE_MAP["LOCAL_NEO4J_START_FAIL"] == "neo4j_health"
    assert "NEO4J_CONNECTION_FAIL" in CATEGORY_SERVICE_MAP
    assert CATEGORY_SERVICE_MAP["NEO4J_CONNECTION_FAIL"] == "neo4j_health"


@pytest.mark.asyncio
async def test_health_monitor_triggers_neo4j_remediation():
    """Test that health monitor triggers Neo4j remediation on detection."""
    # Import after mocking to avoid early loading
    import sys
    from pathlib import Path

    # Add scripts dir to path
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts" / "daemons"
    sys.path.insert(0, str(scripts_dir))

    # Now import
    from health_monitor import handle_health_issues

    state = {
        "neo4j": {
            "status": "down",
            "uri": "bolt://localhost:7687",
        },
        "dependencies": {
            "status": "ok",
            "missing": [],
        },
        "sentry": {
            "status": "healthy",
        },
    }

    with patch("subprocess.Popen") as mock_popen:
        await handle_health_issues(state)

        # Verify orchestrator was spawned for Neo4j
        assert mock_popen.called
        call_args = mock_popen.call_args[0][0]
        assert "orchestrate_healers.py" in str(call_args)

        # Verify issue JSON contains Neo4j details
        issue_json_arg = call_args[call_args.index("--issue-json") + 1]
        issue = json.loads(issue_json_arg)
        assert issue["category"] == "LOCAL_NEO4J_START_FAIL"
        assert "Neo4j unreachable" in issue["error_message"]


@pytest.mark.asyncio
async def test_health_monitor_triggers_dependency_remediation():
    """Test that health monitor triggers dependency remediation on detection."""
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parents[2] / "scripts" / "daemons"
    sys.path.insert(0, str(scripts_dir))

    from health_monitor import handle_health_issues

    state = {
        "neo4j": {
            "status": "up",
            "uri": "bolt://localhost:7687",
        },
        "dependencies": {
            "status": "missing",
            "missing": ["sentry_sdk", "graphiti_core"],
        },
        "sentry": {
            "status": "healthy",
        },
    }

    with patch("subprocess.Popen") as mock_popen:
        await handle_health_issues(state)

        # Should spawn 2 remediation processes (one per missing dep)
        assert mock_popen.call_count == 2

        # Verify both spawned orchestrator
        for call_obj in mock_popen.call_args_list:
            call_args = call_obj[0][0]
            assert "orchestrate_healers.py" in str(call_args)

            # Verify issue contains dependency details
            issue_json_arg = call_args[call_args.index("--issue-json") + 1]
            issue = json.loads(issue_json_arg)
            assert issue["category"] == "CONFIG"
            assert "not found" in issue["error_message"]
            assert issue["affected_module"] == "dependencies"


@pytest.mark.asyncio
async def test_no_duplicate_triggers():
    """Test that health monitor doesn't trigger duplicate remediations."""
    import sys
    from pathlib import Path
    import tempfile

    scripts_dir = Path(__file__).resolve().parents[2] / "scripts" / "daemons"
    sys.path.insert(0, str(scripts_dir))

    from health_monitor import handle_health_issues, HEALTH_CACHE_PATH

    # Create a temporary cache showing Neo4j was already down
    prev_cache = {
        "neo4j": {"status": "down", "uri": "bolt://localhost:7687"},
        "dependencies": {"status": "ok", "missing": []},
        "sentry": {"status": "healthy"},
    }

    # Same state (no change)
    current_state = {
        "neo4j": {"status": "down", "uri": "bolt://localhost:7687"},
        "dependencies": {"status": "ok", "missing": []},
        "sentry": {"status": "healthy"},
    }

    # Write previous cache
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(prev_cache, f)
        temp_cache_path = Path(f.name)

    try:
        with patch("health_monitor.HEALTH_CACHE_PATH", temp_cache_path):
            with patch("subprocess.Popen") as mock_popen:
                await handle_health_issues(current_state)

                # Should NOT spawn any processes (no state change)
                assert not mock_popen.called
    finally:
        temp_cache_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_outcome_logging():
    """Test that remediation outcomes are logged to JSONL."""
    from src.graph.orchestrate_healers import record_remediation_outcome, OUTCOME_LOG_PATH
    import tempfile

    # Use temporary file for test
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
        temp_log_path = Path(f.name)

    try:
        with patch("src.graph.orchestrate_healers.OUTCOME_LOG_PATH", temp_log_path):
            record_remediation_outcome(
                issue_id="test-123",
                category="CONFIG",
                confidence=0.95,
                status="remediated",
                service="dependencies",
                evidence={"pattern": "missing_module"},
            )

            # Verify log entry
            with open(temp_log_path, "r") as f:
                line = f.readline()
                entry = json.loads(line)

                assert entry["issue_id"] == "test-123"
                assert entry["category"] == "CONFIG"
                assert entry["status"] == "remediated"
                assert entry["service"] == "dependencies"
    finally:
        temp_log_path.unlink(missing_ok=True)
