# TaskExecution Node Logging

## Overview

Commander writes `:TaskExecution` nodes to Aura after every completed Lead run. This enables:
- task-observer to compute quality metrics and generate ImprovementProposals
- Watson to calibrate verdict accuracy via PostMortem feedback
- SkillDef quality scores to improve via trigger_count tracking

## Implementation

**Helper Script:** `scripts/graph/write_task_execution.py`

**Called by:** Commander (`.claude/agents/commander.md` Part VIII)

**When:** Flow 1 Phase 6 Step 6.1 — immediately after Lead returns outcome, before PostMortem handshake

## Usage

### From Commander (programmatic)

```python
import subprocess, json, sys

cmd = [
    sys.executable, "scripts/graph/write_task_execution.py",
    "--task-id", task_id,
    "--task-type", "engineering",  # engineering|design|forensic|infrastructure|compound
    "--lead", "engineering-lead",
    "--loop-count", "3",
    "--skills", "gsd-executor", "test-fixing",
    "--model", "anthropic/claude-sonnet-4-5",
    "--status", "completed",  # completed|circuit_breaker
    "--difficulty", "MICRO"  # NANO|MICRO|STANDARD|COMPOUND|RESEARCH
]

if quality_gate_passed:
    cmd.append("--passed")

result = subprocess.run(cmd, capture_output=True, text=True)
outcome = json.loads(result.stdout)
```

### From CLI (testing)

```bash
python scripts/graph/write_task_execution.py \
  --task-type engineering \
  --lead engineering-lead \
  --passed \
  --loop-count 3 \
  --skills gsd-executor test-fixing \
  --model "anthropic/claude-sonnet-4-5" \
  --difficulty MICRO
```

## Node Schema

```cypher
(:TaskExecution {
  task_id: string (UUID),
  task_type: string,
  lead_invoked: string,
  quality_gate_passed: boolean,
  loop_count: integer,
  skills_used: [string],
  model_used: string,
  model_requested: string,
  utility_models_used: string (JSON),
  escalation_triggered: boolean,
  escalation_reason: string,
  difficulty_tier: string,
  created_at: string (ISO timestamp),
  status: string
})
```

## Side Effects

The script also updates `SkillDef.trigger_count` for each skill used:

```cypher
MATCH (sk:SkillDef) WHERE sk.name IN $skills_used
SET sk.trigger_count = coalesce(sk.trigger_count, 0) + 1
```

## Verification

```bash
# Count TaskExecution nodes
python -c "from neo4j import GraphDatabase; import os; from dotenv import load_dotenv; load_dotenv(); driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))); session = driver.session(); result = session.run('MATCH (te:TaskExecution) RETURN count(te) as count'); print(f\"TaskExecution nodes: {result.single()['count']}\"); driver.close()"

# Recent TaskExecutions
python -c "from neo4j import GraphDatabase; import os; from dotenv import load_dotenv; load_dotenv(); driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))); session = driver.session(); result = session.run('MATCH (te:TaskExecution) RETURN te ORDER BY te.created_at DESC LIMIT 5'); import json; [print(json.dumps(dict(r), indent=2)) for r in result]; driver.close()"
```

## Architecture Context

**Spec:** `docs/agent-system/specs/commander.md` — Flow 1 Phase 6, Flow 4 (PostMortem Handshake)

**Platform Wrapper:** `.claude/agents/commander.md` — Part VIII

**Integration:** Commander → TaskExecution write → Watson PostMortem → task-observer

## Success Criteria

- ✅ Commander writes TaskExecution after every Lead completion
- ✅ SkillDef.trigger_count increments for each skill used
- ✅ Can be verified by querying: `MATCH (te:TaskExecution) RETURN te LIMIT 5`
- ✅ task-observer can read TaskExecutions for ImprovementProposal validation
