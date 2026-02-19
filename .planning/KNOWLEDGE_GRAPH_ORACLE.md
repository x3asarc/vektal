# Knowledge Graph Oracle Integration Guide

## Overview

The Knowledge Graph Oracle framework provides temporal knowledge storage and graph-backed evidence retrieval for governance decisions across Phases 13.2, 14, and 15.

**Purpose:**
- Enable Oracle decisions to incorporate historical evidence
- Support temporal trend detection for optimization loops (Phase 14)
- Provide graph-aware remediation planning (Phase 15)
- Maintain fail-open safety to prevent graph unavailability from blocking mutation flows

**Relationship to Phase 13/13.1 Governance:**
- Extends verification oracle with graph-backed evidence retrieval
- Complements field policy and kill-switch governance with historical context
- Preserves all existing governance contracts and safety guarantees

**Phase 14/15 Consumption:**
Phase 14 (Continuous Optimization) and Phase 15 (Self-Healing) MUST query graph evidence before proposing changes and emit episodes after outcomes.

---

## API Reference

### Graph Evidence Query

```python
from src.assistant.governance import query_graph_evidence, OracleDecision

# Returns unified OracleDecision contract (same as enrichment oracles)
signal: OracleDecision = query_graph_evidence(
    action_type='enrichment',      # 'optimization', 'remediation', 'enrichment'
    target_module='src.tasks.enrichment',
    store_id='store_123',
    timeout=2.0  # seconds (default)
)

# OracleDecision contract (unified across all adapters):
# - decision: 'pass', 'fail', 'review', 'hold'
# - confidence: float [0.0, 1.0]
# - reason_codes: tuple[str, ...]
# - evidence_refs: tuple[str, ...]
# - requires_user_action: bool
# - source: str ('graph', 'enrichment', 'graph_unavailable')

if signal.decision == 'fail':
    # Critical failures detected - escalate to user
    print(f"Blocked: {signal.reason_codes}")
elif signal.decision == 'review':
    # Prior failures exist - suggest review
    print(f"Review recommended: {signal.evidence_refs}")
else:
    # No failures found - proceed
    pass
```

**Note:** `OracleSignal` is a deprecated alias for `OracleDecision`. Use `OracleDecision` for new code.

### Memory Retrieval with Graph Evidence

```python
from src.assistant.memory_retrieval import retrieve_relevant_memories, MemoryResult

memories: List[MemoryResult] = retrieve_relevant_memories(
    query="product enrichment quality issues",
    store_id="store_123",
    limit=10,
    include_graph=True,        # Include graph-backed memories
    retrieval_mode='blend'     # 'vector', 'lexical', 'blend'
)

for memory in memories:
    print(f"{memory.source}: {memory.content} (score: {memory.relevance_score})")
    # source: 'facts', 'graph', 'lexical', 'vector'
```

### Episode Emission (via Celery)

```python
from src.tasks.graphiti_sync import emit_episode
from src.core.synthex_entities import EpisodeType, create_episode_payload

# Emit oracle decision episode
payload = create_episode_payload(
    episode_type=EpisodeType.ORACLE_DECISION,
    store_id="store_123",
    correlation_id="run_abc123",
    decision="pass",
    confidence=0.95,
    reason_codes=["no_conflicts"],
    evidence_refs=[],
    source_adapter="enrichment_oracle"
)

# Fire-and-forget emission (non-blocking)
emit_episode.delay(payload)
```

---

## Episode Types

### 1. oracle_decision

**When to emit:** After Oracle makes a pass/fail/review/defer decision

**Required fields:**
- `episode_type`: "oracle_decision"
- `store_id`: Store ID
- `correlation_id`: Action or batch correlation ID
- `decision`: "pass", "fail", "review", "defer"
- `confidence`: float [0.0, 1.0]
- `reason_codes`: List[str] (machine-readable codes)
- `evidence_refs`: List[str] (references to supporting evidence)
- `source_adapter`: str (e.g., "enrichment_oracle", "field_policy")

**Example:**
```python
{
    "episode_type": "oracle_decision",
    "store_id": "store_123",
    "correlation_id": "action_456",
    "created_at": "2026-02-19T12:00:00Z",
    "decision": "review",
    "confidence": 0.6,
    "reason_codes": ["prior_failures_detected"],
    "evidence_refs": ["failure_789", "failure_790"],
    "source_adapter": "graph_oracle"
}
```

### 2. failure_pattern

**When to emit:** From FAILURE_JOURNEY.md sync or runtime error capture

**Required fields:**
- `episode_type`: "failure_pattern"
- `store_id`: Store ID
- `correlation_id`: Optional correlation ID
- `failure_type`: str (e.g., "timeout", "validation", "null_pointer")
- `module_path`: str (Python module path)
- `error_signature`: str (normalized error message or hash)
- `occurrence_count`: int (default 1)

**Example:**
```python
{
    "episode_type": "failure_pattern",
    "store_id": "store_123",
    "created_at": "2026-02-19T12:00:00Z",
    "failure_type": "timeout",
    "module_path": "src.tasks.enrichment",
    "error_signature": "OpenRouter API timeout after 30s",
    "occurrence_count": 1
}
```

### 3. enrichment_outcome

**When to emit:** After enrichment batch completes

**Required fields:**
- `episode_type`: "enrichment_outcome"
- `store_id`: Store ID
- `correlation_id`: Enrichment run ID
- `product_id`: str (product enriched)
- `profile_gear`: str ("conservative", "balanced", "aggressive")
- `fields_modified`: List[str]
- `quality_delta`: float (quality score change)
- `oracle_arbitration_used`: bool

**Example:**
```python
{
    "episode_type": "enrichment_outcome",
    "store_id": "store_123",
    "correlation_id": "run_abc123",
    "created_at": "2026-02-19T12:00:00Z",
    "product_id": "prod_789",
    "profile_gear": "balanced",
    "fields_modified": ["title", "description", "tags"],
    "quality_delta": 0.15,
    "oracle_arbitration_used": true
}
```

### 4. user_approval

**When to emit:** When user approves/rejects action

**Required fields:**
- `episode_type`: "user_approval"
- `store_id`: Store ID
- `correlation_id`: Action or batch correlation ID
- `action_id`: str
- `action_type`: str ("create", "update", "bulk_update")
- `approval_decision`: str ("approved", "rejected", "modified")
- `user_id`: str

**Example:**
```python
{
    "episode_type": "user_approval",
    "store_id": "store_123",
    "correlation_id": "action_456",
    "created_at": "2026-02-19T12:00:00Z",
    "action_id": "action_456",
    "action_type": "bulk_update",
    "approval_decision": "approved",
    "user_id": "user_123"
}
```

### 5. vendor_catalog_change

**When to emit:** After vendor catalog modifications

**Required fields:**
- `episode_type`: "vendor_catalog_change"
- `store_id`: Store ID
- `correlation_id`: Ingestion job ID
- `vendor_id`: str
- `change_type`: str ("add", "update", "remove")
- `items_affected`: int

**Example:**
```python
{
    "episode_type": "vendor_catalog_change",
    "store_id": "store_123",
    "correlation_id": "ingest_xyz",
    "created_at": "2026-02-19T12:00:00Z",
    "vendor_id": "vendor_456",
    "change_type": "update",
    "items_affected": 42
}
```

---

## Phase 14 Integration Guide

**Continuous Optimization & Learning**

### Before Optimization

Query graph evidence to check for prior failures or warnings:

```python
signal = query_graph_evidence(
    action_type='optimization',
    target_module='src.tasks.enrichment',
    store_id=store_id
)

if signal.decision == 'fail':
    # Critical warnings - do not optimize automatically
    escalate_to_user(signal.reason_codes, signal.evidence_refs)
elif signal.decision == 'review':
    # Prior failures - proceed with caution
    log_warning(f"Optimization proceeding despite warnings: {signal.reason_codes}")
```

### After Optimization

Emit enrichment outcome episode:

```python
from src.tasks.graphiti_sync import emit_episode
from src.core.synthex_entities import EpisodeType, create_episode_payload

payload = create_episode_payload(
    episode_type=EpisodeType.ENRICHMENT_OUTCOME,
    store_id=store_id,
    correlation_id=run_id,
    product_id=product_id,
    profile_gear=profile_gear,
    fields_modified=fields_modified,
    quality_delta=quality_after - quality_before,
    oracle_arbitration_used=oracle_was_invoked
)

emit_episode.delay(payload)
```

### Trend Detection

Query historical episodes by time range:

```python
from src.assistant.governance import GraphOracleAdapter

adapter = GraphOracleAdapter(timeout_seconds=5.0)
failures = adapter.query_failure_history(
    module_path='src.tasks.enrichment',
    store_id=store_id,
    lookback_days=90  # 3-month trend analysis
)

if len(failures) > 10:
    print("High failure rate detected - investigate root cause")
```

---

## Phase 15 Integration Guide

**Self-Healing and Autonomous Remediation**

### Before Remediation

Query graph evidence to check for critical warnings:

```python
signal = query_graph_evidence(
    action_type='remediation',
    target_module='src.assistant.governance.field_policy',
    store_id=store_id
)

if signal.decision == 'fail':
    # Critical warnings force escalation
    # DO NOT auto-remediate - requires user intervention
    escalate_critical_remediation(
        module=target_module,
        reason_codes=signal.reason_codes,
        evidence=signal.evidence_refs
    )
    return

if signal.requires_user_action:
    # High-risk remediation - get approval first
    await_user_approval_for_remediation()
```

### After Sandbox Testing

Emit episode with outcome:

```python
payload = create_episode_payload(
    episode_type=EpisodeType.ORACLE_DECISION,
    store_id=store_id,
    correlation_id=remediation_id,
    decision="pass" if sandbox_succeeded else "fail",
    confidence=0.9 if sandbox_succeeded else 0.1,
    reason_codes=["sandbox_verified"] if sandbox_succeeded else ["sandbox_failed"],
    evidence_refs=[f"sandbox_run_{remediation_id}"],
    source_adapter="self_healing_sandbox"
)

emit_episode.delay(payload)
```

### Time-Aware History

Use temporal graph state to inform future remediations:

```python
# Check if this module was remediated recently
recent_remediations = adapter.query_failure_history(
    module_path=target_module,
    store_id=store_id,
    lookback_days=7
)

if recent_remediations:
    # Module was recently remediated - be more conservative
    confidence_penalty = 0.2
    print("Recent remediation detected - applying confidence penalty")
```

---

## Fail-Open Contract

**All graph queries have timeout and fail-open behavior:**

1. **2-second default timeout** - Queries complete within 2s or return fallback
2. **FAIL_OPEN_SIGNAL returned on timeout/error:**
   ```python
   OracleDecision(
       decision='pass',
       confidence=0.5,
       reason_codes=(),
       evidence_refs=(),
       requires_user_action=False,
       source='graph_unavailable'
   )
   ```
3. **Never blocks primary request path** - Graph unavailability logged but not raised
4. **Graph unavailability** - Logged at WARNING level, operations continue

**Testing fail-open behavior:**
```python
# Simulate graph unavailability
import os
os.environ['GRAPH_ORACLE_ENABLED'] = 'false'

signal = query_graph_evidence(
    action_type='enrichment',
    target_module='src.tasks.enrichment',
    store_id='store_123'
)

assert signal.source == 'graph_unavailable'
assert signal.decision == 'pass'
assert signal.confidence == 0.5
```

---

## Cross-Phase Invariants

**Rules that apply across Phases 13.2, 14, and 15:**

### 1. Agents Add Episodes Only

Agents MUST NOT delete or modify graph history.

**Allowed:**
```python
emit_episode.delay(payload)  # Add new episode
```

**Forbidden:**
```python
# DO NOT delete episodes
client.delete_episode(episode_id)  # FORBIDDEN

# DO NOT modify past episodes
client.update_episode(episode_id, new_data)  # FORBIDDEN
```

### 2. Episode ID Provides Idempotency

Episode ingestion MUST be idempotent based on `correlation_id` or `episode_id`.

```python
# Same correlation_id = same episode (deduplicated)
payload1 = create_episode_payload(
    episode_type=EpisodeType.ORACLE_DECISION,
    store_id="store_123",
    correlation_id="action_456",  # Dedup key
    # ...
)

payload2 = create_episode_payload(
    episode_type=EpisodeType.ORACLE_DECISION,
    store_id="store_123",
    correlation_id="action_456",  # Same key = deduplicated
    # ...
)
```

### 3. Non-Blocking Emission

Episode emission MUST be fire-and-forget via Celery:

```python
# Correct: non-blocking
emit_episode.delay(payload)

# Incorrect: blocking
emit_episode(payload)  # DO NOT use synchronous call
```

### 4. Store Isolation

All queries MUST filter by `store_id` for multi-tenant isolation:

```python
# Always include store_id in queries
signal = query_graph_evidence(
    action_type='enrichment',
    target_module='src.tasks.enrichment',
    store_id=store_id  # Required for tenant isolation
)
```

---

## Environment Configuration

**Required environment variables:**

```bash
# Neo4j connection
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure-password>

# Feature flag
GRAPH_ORACLE_ENABLED=true
```

**Default behavior when disabled:**
- `GRAPH_ORACLE_ENABLED=false` (default)
- All graph queries return `FAIL_OPEN_SIGNAL`
- Episode emission becomes no-op
- No Neo4j connection required

---

## Error Handling

### Import Errors

```python
try:
    from src.assistant.governance import query_graph_evidence, FAIL_OPEN_SIGNAL
except ImportError:
    # Graph oracle not available - use fallback logic
    logger.warning("Graph oracle not available - using default decision")
    from src.core.enrichment.oracle_contract import OracleDecision
    FAIL_OPEN_SIGNAL = OracleDecision(
        decision='pass', confidence=0.5, reason_codes=(), evidence_refs=(),
        requires_user_action=False, source='graph_unavailable'
    )
```

### Query Timeouts

All graph queries have built-in timeout handling:

```python
# Timeout handled automatically
signal = query_graph_evidence(
    action_type='enrichment',
    target_module='src.tasks.enrichment',
    store_id='store_123',
    timeout=2.0  # Times out after 2s, returns FAIL_OPEN_SIGNAL
)
```

### Graph Unavailability

```python
from src.core.graphiti_client import check_graph_availability

if not check_graph_availability(timeout_seconds=2.0):
    logger.warning("Graph database unavailable - using fallback")
    # Continue with fallback logic
```

---

## Performance Considerations

**Query Timeouts:**
- Default: 2 seconds
- Maximum: 5 seconds (for trend analysis)
- Timeout triggers fail-open signal

**Request Path Impact:**
- Graph queries MUST NOT block mutation flows
- Use async bridge pattern for request-path queries
- Emission is always fire-and-forget via Celery

**Caching:**
- Graph client is singleton (one instance per process)
- Query results NOT cached (temporal queries need fresh data)

---

## Troubleshooting

### Graph Oracle Not Available

**Symptom:** All queries return `source='graph_unavailable'`

**Causes:**
1. `GRAPH_ORACLE_ENABLED=false` (default)
2. `graphiti-core` package not installed
3. Neo4j connection failed
4. Missing environment variables

**Solution:**
```bash
# 1. Enable graph oracle
export GRAPH_ORACLE_ENABLED=true

# 2. Install dependencies
pip install graphiti-core==0.26.0 neo4j==5.26.0

# 3. Verify Neo4j connection
curl -sf http://localhost:7474

# 4. Check environment variables
echo $NEO4J_URI $NEO4J_PASSWORD
```

### High Query Latency

**Symptom:** Queries timing out frequently

**Solution:**
1. Check Neo4j server resources (memory, CPU)
2. Verify network connectivity to Neo4j
3. Increase timeout for non-critical queries
4. Review query patterns for optimization

### Episode Not Appearing in Graph

**Symptom:** Emitted episode not visible in Neo4j Browser

**Causes:**
1. Celery worker not processing `graphiti_sync` queue
2. Episode validation failed
3. Neo4j connection issue during ingestion

**Debugging:**
```bash
# Check Celery worker logs
docker compose logs -f celery_worker

# Check Neo4j Browser
# http://localhost:7474
# Query: MATCH (n) WHERE n.episode_type = 'oracle_decision' RETURN n LIMIT 10
```

---

## Migration Path

**For existing deployments:**

1. **Phase 13.2-01:** Deploy Neo4j service, install dependencies
2. **Phase 13.2-02:** Add emission hooks (non-breaking, additive)
3. **Phase 13.2-03:** Enable graph evidence queries (opt-in)
4. **Phase 14:** Optimization loops consume graph evidence
5. **Phase 15:** Self-healing uses graph for remediation planning

**Rollback safety:**
- Set `GRAPH_ORACLE_ENABLED=false` to disable
- All queries fail-open gracefully
- No database schema changes required

---

*Phase 13.2 - Oracle Framework Reuse*
*Last updated: 2026-02-19*
