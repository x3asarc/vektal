"""
Create ImprovementProposal for workflow parallelization
"""
import uuid
from datetime import datetime, timezone
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))
)

proposal_id = f"ip-{uuid.uuid4().hex[:12]}"
now = datetime.now(timezone.utc).isoformat()

with driver.session() as session:
    session.run("""
        CREATE (ip:ImprovementProposal {
            proposal_id: $proposal_id,
            title: $title,
            severity: $severity,
            target_component: $target_component,
            description: $description,
            evidence: $evidence,
            expected_impact: $expected_impact,
            implementation_approach: $implementation_approach,
            blast_radius: $blast_radius,
            status: $status,
            created_at: $created_at
        })
        RETURN ip.proposal_id as id
    """,
        proposal_id=proposal_id,
        title="Parallelize workflow orchestration to reduce latency 4x",
        severity="HIGH",
        target_component="commander",
        description="""
Current workflow executes agents sequentially even when tasks are independent:
- Infrastructure audit completes → then task-observer analyzes
- One ImprovementProposal implemented → then next one starts
- Tests run after all implementations complete

Result: 20-minute workflows that should take 5 minutes.

**Root cause:** Commander and Leads spawn one agent at a time, waiting for completion
before spawning the next, even when work is independent.

**Examples from 2026-03-09 session:**
1. Infrastructure audit (5 min) + task-observer analysis (3 min) = 8 min sequential
   → Could be 5 min parallel (observer starts while audit running)
2. 3 ImprovementProposals processed sequentially (9 min total)
   → Could be 3 min parallel (all proposals to Validator at once, approved ones implemented in parallel)
3. TaskExecution implementation (5 min) + test run (2 min) = 7 min sequential
   → Could be 5 min parallel (tests run in background during implementation tail)
        """,
        evidence="Session 2026-03-09: Infrastructure audit workflow took 20 minutes with 6+ sequential agent spawns for work that had minimal dependencies",
        expected_impact="4x latency reduction: 20-minute workflows → 5-minute workflows. No code changes required, instruction-only.",
        implementation_approach="""
**Lightweight fix (instruction-only, no code changes):**

1. **Commander Part IV update** - Add parallelization protocol:
   ```
   ## Parallel Execution Rules
   - Spawn multiple Leads in parallel when tasks are independent
   - Use `run_in_background=True` for read-only analysis while main work continues
   - Example: Infrastructure audit + task-observer can run simultaneously
   - Wait only when dependencies exist (e.g., Validator must complete before implementation)
   ```

2. **Infrastructure Lead optimization** - Update to spawn Validator + batch all proposals:
   ```
   ## ImprovementProposal Processing
   - Fetch ALL pending proposals at once
   - Send batch to Validator (single spawn, evaluates all)
   - Spawn multiple implementation agents in parallel for APPROVED proposals
   ```

3. **Engineering Lead update** - Run tests in background while wrapping up:
   ```
   ## Test Execution
   - Start test run in background when implementation nears completion
   - Continue writing docs/reports while tests run
   - Check test results at the end
   ```

**Implementation time:** 10 minutes (edit 3 agent files)
**Risk:** LOW (instructions only, no behavior change if agents ignore)
**Rollback:** Delete new sections if agents get confused
        """,
        blast_radius="commander, infrastructure-lead, engineering-lead (instruction sections only)",
        status="pending",
        created_at=now
    )
    result = session.execute_read(lambda tx: tx.run(
        "MATCH (ip:ImprovementProposal {proposal_id: $pid}) RETURN ip.proposal_id",
        pid=proposal_id
    ).single())

driver.close()

print(f"ImprovementProposal created: {proposal_id}")
print(f"   Title: Parallelize workflow orchestration to reduce latency 4x")
print(f"   Severity: HIGH")
print(f"   Target: commander, infrastructure-lead, engineering-lead")
print(f"   Approach: Instruction-only (no code changes)")
print(f"   Expected impact: 20 min -> 5 min (4x speedup)")
print(f"   Status: pending (ready for Validator)")
