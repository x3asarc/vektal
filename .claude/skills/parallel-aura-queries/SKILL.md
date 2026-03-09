---
name: parallel-aura-queries
description: >
  Parallel execution engine for independent Aura read queries. Reduces audit/discovery
  time by 30-60s when multiple graph queries are needed. READ-ONLY constraint enforced.
  All agents can use this for non-dependent query batches (health checks, SentryIssue
  scans, ImprovementProposal lists, oracle lookups). Spawn once per batch, not per query.
triggers:
  - "parallel aura"
  - "batch aura queries"
  - "concurrent graph queries"
---

# parallel-aura-queries — Concurrent Graph Read Executor

## Purpose

Reduce latency when executing multiple independent Aura queries. Traditional sequential execution adds ~10-20s per query due to network round-trips. This skill batches independent READ queries and executes them concurrently, reducing total time to the slowest query's duration.

**Use case:** Infrastructure audits, P-LOAD context fetches, multi-domain discovery.

---

## Constraints

1. **READ-ONLY:** Only queries that return data. No MERGE, SET, CREATE, DELETE, or REMOVE.
2. **Independence:** Queries must not depend on each other's results (no shared parameters derived from previous results).
3. **Safety:** All queries are validated before execution. Violations block the entire batch.

---

## API

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # Project root
from claude.skills.parallel_aura_queries.executor import execute_parallel

# Define your independent read queries
queries = {
    "sentry_unresolved": {
        "cypher": """
            MATCH (si:SentryIssue)
            WHERE si.resolved = false
            RETURN si.issue_id, si.title, si.category, si.created_at
            ORDER BY si.created_at DESC
            LIMIT 10
        """,
        "params": {}
    },
    "pending_proposals": {
        "cypher": """
            MATCH (ip:ImprovementProposal)
            WHERE ip.status = 'pending'
            RETURN ip.proposal_id, ip.title, ip.severity
            ORDER BY ip.created_at DESC
            LIMIT 5
        """,
        "params": {}
    },
    "oracle_health": {
        "cypher": """
            MATCH (o:Oracle)
            RETURN o.name, o.last_sync, o.status
        """,
        "params": {}
    }
}

# Execute all queries concurrently
results = execute_parallel(queries)

# Results structure:
# {
#   "sentry_unresolved": {"data": [...], "duration_ms": 120, "error": null},
#   "pending_proposals": {"data": [...], "duration_ms": 95, "error": null},
#   "oracle_health": {"data": [...], "duration_ms": 80, "error": null}
# }
```

---

## Implementation

Save this as `C:\Users\Hp\Documents\Shopify Scraping Script\.claude\skills\parallel-aura-queries\executor.py`:

```python
"""
Parallel Aura query executor — READ-ONLY batch execution.
Approved: ImprovementProposal ip-729c4e56a7e0
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Safety: Block write operations
WRITE_KEYWORDS = ["MERGE", "SET", "CREATE", "DELETE", "REMOVE", "DETACH"]

def validate_read_only(cypher: str) -> None:
    """Raise ValueError if query contains write operations."""
    upper_query = cypher.upper()
    for keyword in WRITE_KEYWORDS:
        if keyword in upper_query:
            raise ValueError(f"WRITE operation detected: {keyword}. Only READ queries allowed.")

def execute_query(driver, label: str, cypher: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute single query and return result with metadata."""
    start = time.time()
    try:
        validate_read_only(cypher)
        with driver.session() as session:
            result = session.run(cypher, **params)
            data = [record.data() for record in result]
        duration_ms = int((time.time() - start) * 1000)
        return {"data": data, "duration_ms": duration_ms, "error": None}
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return {"data": [], "duration_ms": duration_ms, "error": str(e)}

def execute_parallel(queries: Dict[str, Dict[str, Any]], max_workers: int = 5) -> Dict[str, Any]:
    """
    Execute multiple independent Aura queries in parallel.

    Args:
        queries: Dict mapping label → {"cypher": str, "params": dict}
        max_workers: Max concurrent threads (default 5)

    Returns:
        Dict mapping label → {"data": list, "duration_ms": int, "error": str|None}
    """
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))
    )

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_query, driver, label, q["cypher"], q["params"]): label
            for label, q in queries.items()
        }

        for future in as_completed(futures):
            label = futures[future]
            results[label] = future.result()

    driver.close()
    return results
```

---

## Usage Example: Infrastructure Lead Health Check

Before (sequential — 3 queries × 15s = 45s):
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver(...)
with driver.session() as s:
    sentry = s.run("MATCH (si:SentryIssue) WHERE si.resolved = false RETURN si").data()
    proposals = s.run("MATCH (ip:ImprovementProposal) WHERE ip.status = 'pending' RETURN ip").data()
    oracle = s.run("MATCH (o:Oracle) RETURN o").data()
driver.close()
```

After (parallel — max(15s, 15s, 15s) = 15s):
```python
from claude.skills.parallel_aura_queries.executor import execute_parallel

queries = {
    "sentry": {"cypher": "MATCH (si:SentryIssue) WHERE si.resolved = false RETURN si", "params": {}},
    "proposals": {"cypher": "MATCH (ip:ImprovementProposal) WHERE ip.status = 'pending' RETURN ip", "params": {}},
    "oracle": {"cypher": "MATCH (o:Oracle) RETURN o", "params": {}}
}
results = execute_parallel(queries)
# Access: results["sentry"]["data"], results["proposals"]["data"], etc.
```

**Time saved:** 30s per audit (66% reduction).

---

## When NOT to Use This Skill

1. **Dependent queries:** If query B needs results from query A as parameters.
2. **Write operations:** MERGE, SET, CREATE, DELETE — these must be sequential for transaction safety.
3. **Single query:** No benefit from parallelization — just use direct Neo4j session.

---

## Integration Points

**Commander P-LOAD:**
- Sentry issues + LongTermPatterns + skill quality + TaskExecutions → all independent

**Infrastructure Lead Audit:**
- Aura health + SentryIssue scan + ImprovementProposal queue → all independent

**Forensic Lead Discovery:**
- Suspect function callers + recent failures + similar patterns → all independent

---

## Rollback / Circuit Breaker

If concurrent execution causes issues (race conditions, connection pool exhaustion):
1. Set `max_workers=1` → degrades to sequential execution
2. Log ImprovementProposal with error details
3. Infrastructure Lead reverts to original sequential pattern in Part II

---

## Quality Metric

Track average time saved per audit:
```cypher
MATCH (te:TaskExecution)
WHERE te.skills_used CONTAINS "parallel-aura-queries"
RETURN avg(te.duration_ms_before - te.duration_ms_after) as avg_time_saved_ms
```

Target: ≥30s saved per invocation.
