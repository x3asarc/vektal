"""Test TaskExecution node writes to Aura."""
import os
import sys
import uuid
import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

load_dotenv()

from scripts.graph.write_task_execution import write_task_execution


@pytest.fixture
def neo4j_session():
    """Provide Neo4j session for tests."""
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        pytest.skip("Neo4j credentials not configured")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    session = driver.session()
    yield session
    session.close()
    driver.close()


def test_write_task_execution_basic(neo4j_session):
    """Test basic TaskExecution node write."""
    task_id = str(uuid.uuid4())

    result = write_task_execution(
        task_id=task_id,
        task_type="engineering",
        lead_invoked="engineering-lead",
        quality_gate_passed=True,
        loop_count=2,
        skills_used=["test-skill-1", "test-skill-2"],
        model_used="anthropic/claude-sonnet-4-5",
        status="completed",
        difficulty_tier="MICRO",
    )

    assert result["success"] is True
    assert result["task_execution_id"] is not None
    assert result["error"] is None

    # Verify node exists in Aura
    node = neo4j_session.run(
        "MATCH (te:TaskExecution {task_id: $task_id}) RETURN te",
        task_id=task_id
    ).single()

    assert node is not None
    assert node["te"]["task_type"] == "engineering"
    assert node["te"]["lead_invoked"] == "engineering-lead"
    assert node["te"]["quality_gate_passed"] is True
    assert node["te"]["loop_count"] == 2
    assert node["te"]["status"] == "completed"


def test_write_task_execution_circuit_breaker(neo4j_session):
    """Test TaskExecution write with circuit_breaker status."""
    task_id = str(uuid.uuid4())

    result = write_task_execution(
        task_id=task_id,
        task_type="forensic",
        lead_invoked="forensic-lead",
        quality_gate_passed=False,
        loop_count=5,
        skills_used=["systematic-debugging"],
        model_used="anthropic/claude-opus-4",
        status="circuit_breaker",
        escalation_triggered=True,
        escalation_reason="Loop budget exhausted",
        difficulty_tier="STANDARD",
    )

    assert result["success"] is True

    # Verify node
    node = neo4j_session.run(
        "MATCH (te:TaskExecution {task_id: $task_id}) RETURN te",
        task_id=task_id
    ).single()

    assert node["te"]["status"] == "circuit_breaker"
    assert node["te"]["quality_gate_passed"] is False
    assert node["te"]["escalation_triggered"] is True
    assert node["te"]["escalation_reason"] == "Loop budget exhausted"


def test_skill_def_trigger_count_increment(neo4j_session):
    """Test that SkillDef.trigger_count increments."""
    # Create a test SkillDef if it doesn't exist
    test_skill = f"test-skill-{uuid.uuid4().hex[:8]}"
    neo4j_session.run("""
        MERGE (sk:SkillDef {name: $name})
        SET sk.skill_id = $skill_id,
            sk.trigger_count = 0
    """, name=test_skill, skill_id=f"test-{test_skill}")

    # Get initial count
    initial = neo4j_session.run(
        "MATCH (sk:SkillDef {name: $name}) RETURN sk.trigger_count as count",
        name=test_skill
    ).single()["count"]

    # Write TaskExecution using this skill
    task_id = str(uuid.uuid4())
    result = write_task_execution(
        task_id=task_id,
        task_type="engineering",
        lead_invoked="engineering-lead",
        quality_gate_passed=True,
        loop_count=1,
        skills_used=[test_skill],
        model_used="openrouter/auto",
    )

    assert result["success"] is True
    assert result["skills_updated"] >= 1  # At least our test skill

    # Verify count incremented
    final = neo4j_session.run(
        "MATCH (sk:SkillDef {name: $name}) RETURN sk.trigger_count as count",
        name=test_skill
    ).single()["count"]

    assert final == initial + 1

    # Cleanup
    neo4j_session.run("MATCH (sk:SkillDef {name: $name}) DETACH DELETE sk", name=test_skill)
    neo4j_session.run("MATCH (te:TaskExecution {task_id: $task_id}) DETACH DELETE te", task_id=task_id)


def test_query_recent_task_executions(neo4j_session):
    """Test querying recent TaskExecutions."""
    result = neo4j_session.run("""
        MATCH (te:TaskExecution)
        RETURN te.task_id, te.task_type, te.lead_invoked, te.created_at
        ORDER BY te.created_at DESC
        LIMIT 5
    """).data()

    assert isinstance(result, list)
    # Should have at least the test nodes we created
    assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
