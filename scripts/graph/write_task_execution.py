#!/usr/bin/env python3
"""Write TaskExecution node to Aura after Lead completion.

Called by Commander in Flow 1 Phase 6 Step 6.1.
See: docs/agent-system/specs/commander.md Part VIII - CMD-WRITE-TASK-EXECUTION
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def write_task_execution(
    task_id: str,
    task_type: str,
    lead_invoked: str,
    quality_gate_passed: bool,
    loop_count: int,
    skills_used: list[str],
    model_used: str,
    status: str = "completed",
    model_requested: str = None,
    utility_models_used: dict = None,
    escalation_triggered: bool = False,
    escalation_reason: str = None,
    difficulty_tier: str = None,
) -> dict:
    """Write TaskExecution node to Aura and update SkillDef.trigger_count.

    Args:
        task_id: UUID for this task execution
        task_type: One of: engineering, design, forensic, infrastructure, compound
        lead_invoked: Name of the Lead agent (e.g., "engineering-lead")
        quality_gate_passed: Boolean - did the task pass its quality gate?
        loop_count: How many loops the Lead took
        skills_used: List of skill names used during execution
        model_used: Actual model ID used (e.g., "anthropic/claude-sonnet-4-5")
        status: One of: completed, circuit_breaker
        model_requested: Model requested in context package (default: openrouter/auto)
        utility_models_used: Dict of utility models used (e.g., {"classifier": "google/gemini-3.1-flash-lite"})
        escalation_triggered: Was model escalation triggered?
        escalation_reason: Why was escalation triggered?
        difficulty_tier: NANO, MICRO, STANDARD, COMPOUND, RESEARCH

    Returns:
        dict with keys: success (bool), task_execution_id (str), skills_updated (int), error (str|None)
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_uri or not neo4j_password:
        return {
            "success": False,
            "error": "NEO4J_URI or NEO4J_PASSWORD not set in .env",
            "task_execution_id": None,
            "skills_updated": 0,
        }

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    try:
        with driver.session() as session:
            # Write TaskExecution node
            result = session.run("""
                MERGE (te:TaskExecution {task_id: $task_id})
                SET te.task_type = $task_type,
                    te.lead_invoked = $lead_invoked,
                    te.quality_gate_passed = $quality_gate_passed,
                    te.loop_count = $loop_count,
                    te.skills_used = $skills_used,
                    te.model_used = $model_used,
                    te.model_requested = $model_requested,
                    te.utility_models_used = $utility_models_used,
                    te.escalation_triggered = $escalation_triggered,
                    te.escalation_reason = $escalation_reason,
                    te.difficulty_tier = $difficulty_tier,
                    te.created_at = $created_at,
                    te.status = $status
                RETURN elementId(te) AS id
            """,
            task_id=task_id,
            task_type=task_type,
            lead_invoked=lead_invoked,
            quality_gate_passed=quality_gate_passed,
            loop_count=loop_count,
            skills_used=skills_used,
            model_used=model_used,
            model_requested=model_requested or "openrouter/auto",
            utility_models_used=json.dumps(utility_models_used) if utility_models_used else None,
            escalation_triggered=escalation_triggered,
            escalation_reason=escalation_reason,
            difficulty_tier=difficulty_tier,
            created_at=datetime.now(timezone.utc).isoformat(),
            status=status)

            te_id = result.single()["id"]

            # Update SkillDef.trigger_count for each skill used
            skills_result = session.run("""
                MATCH (sk:SkillDef) WHERE sk.name IN $skills_used
                SET sk.trigger_count = coalesce(sk.trigger_count, 0) + 1
                RETURN count(sk) AS updated
            """, skills_used=skills_used)

            skills_updated = skills_result.single()["updated"]

            return {
                "success": True,
                "task_execution_id": te_id,
                "skills_updated": skills_updated,
                "error": None,
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "task_execution_id": None,
            "skills_updated": 0,
        }
    finally:
        driver.close()


def main():
    """CLI interface for testing TaskExecution writes."""
    import argparse

    parser = argparse.ArgumentParser(description="Write TaskExecution node to Aura")
    parser.add_argument("--task-id", help="Task ID (generates UUID if not provided)")
    parser.add_argument("--task-type", required=True,
                       choices=["engineering", "design", "forensic", "infrastructure", "compound"],
                       help="Type of task")
    parser.add_argument("--lead", required=True, help="Lead agent name (e.g., engineering-lead)")
    parser.add_argument("--passed", action="store_true", help="Quality gate passed")
    parser.add_argument("--loop-count", type=int, default=1, help="Number of loops")
    parser.add_argument("--skills", nargs="+", default=[], help="Skills used (space-separated)")
    parser.add_argument("--model", default="openrouter/auto", help="Model used")
    parser.add_argument("--status", default="completed", choices=["completed", "circuit_breaker"],
                       help="Execution status")
    parser.add_argument("--difficulty", help="Difficulty tier (NANO, MICRO, STANDARD, etc.)")

    args = parser.parse_args()

    task_id = args.task_id or str(uuid.uuid4())

    result = write_task_execution(
        task_id=task_id,
        task_type=args.task_type,
        lead_invoked=args.lead,
        quality_gate_passed=args.passed,
        loop_count=args.loop_count,
        skills_used=args.skills,
        model_used=args.model,
        status=args.status,
        difficulty_tier=args.difficulty,
    )

    print(json.dumps(result, indent=2))

    if result["success"]:
        print(f"\n[OK] TaskExecution written: {task_id}")
        print(f"     Skills updated: {result['skills_updated']}")
        sys.exit(0)
    else:
        print(f"\n[ERROR] {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
