# Phase 15: Self-Healing & Runtime Optimization - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning (after Phase 14 completes)

## Phase Boundary

Build governed autonomous remediation and runtime optimization capabilities that leverage the Phase 14 Codebase Knowledge Graph to make intelligent decisions about healing failures and optimizing hot paths.

**What this phase delivers:**
- Self-healing workflows that detect and remediate failures autonomously
- Runtime optimization agents that improve performance/cost over time
- Sandbox execution with verification gates for safe autonomous changes
- Predictive intelligence for prefetching and resource allocation
- Integration with Phase 14's knowledge graph for impact analysis

**What this phase does NOT include:**
- Codebase knowledge graph infrastructure (Phase 14)
- Initial graph population (Phase 14)
- Graph schema design (Phase 14)

---

## Integration with Phase 14 (Codebase Knowledge Graph)

### How Phase 15 Consumes Phase 14

**Query "what's related to this failure?"**
```python
# Self-healing agent encounters failure in src/tasks/enrichment.py
from src.assistant.governance import query_graph_evidence

# Query knowledge graph for related modules
related = graph.query("""
    MATCH (failed:File {path: 'src/tasks/enrichment.py'})
    MATCH (failed)-[:IMPORTS|IMPORTED_BY*1..2]-(related:File)
    RETURN related.path, related.last_modified
""")

# Also query vector similarity for semantically related code
similar = graph.vector_search(
    embedding=get_file_embedding('src/tasks/enrichment.py'),
    limit=5,
    threshold=0.8
)

# Combine explicit and semantic relationships
impact_radius = set(related) | set(similar)
```

**Query "what's the impact radius of this optimization?"**
```python
# Before optimizing cache TTL in src/core/cache.py
impact = graph.query("""
    MATCH (target:File {path: 'src/core/cache.py'})
    MATCH (dependent:File)-[:IMPORTS*1..3]->(target)
    RETURN dependent.path, count(dependent) as import_depth
    ORDER BY import_depth
""")

# Check if any planning docs reference this module
planning_refs = graph.query("""
    MATCH (target:File {path: 'src/core/cache.py'})
    MATCH (plan:PlanningDoc)-[:REFERENCES]->(target)
    RETURN plan.path, plan.phase_number
""")

# If many dependents or planning doc references exist, be conservative
if len(impact) > 10 or planning_refs:
    confidence_penalty = 0.3
    requires_user_approval = True
```

**Query "what failed here before?"**
```python
# Check Phase 13.2 runtime graph + Phase 14 codebase graph
from src.assistant.governance import GraphOracleAdapter

oracle = GraphOracleAdapter(timeout_seconds=5.0)

# Runtime failures from Phase 13.2 graph
runtime_failures = oracle.query_failure_history(
    module_path='src.tasks.enrichment',
    store_id=store_id,
    lookback_days=90
)

# Structural changes from Phase 14 graph
structural_changes = graph.query("""
    MATCH (f:File {path: 'src/tasks/enrichment.py'})
    MATCH (f)-[:MODIFIED_IN]->(commit:Commit)
    WHERE commit.timestamp > datetime() - duration({days: 90})
    RETURN commit.hash, commit.message, commit.timestamp
    ORDER BY commit.timestamp DESC
""")

# Correlate: did failures spike after structural changes?
for change in structural_changes:
    failures_after = [f for f in runtime_failures
                      if f.timestamp > change.timestamp]
    if len(failures_after) > 5:
        warn(f"Change {change.hash} preceded {len(failures_after)} failures")
```

### Critical Dependencies on Phase 14

Phase 15 CANNOT function without Phase 14 providing:
1. **File/Module/Class/Function nodes** - understand code structure
2. **Import relationships** - trace dependencies
3. **Planning doc linkage** - understand "why" code exists
4. **Vector embeddings** - find semantically similar code
5. **Commit history in graph** - correlate changes with failures
6. **Automatic graph updates** - knowledge stays current

---

<domain>
## Implementation Decisions

### Self-Healing Scope

**What self-heals autonomously (no approval):**
- Transient failures: retry with backoff, switch providers
- Known patterns: apply documented fixes from FAILURE_JOURNEY.md
- Configuration drift: restore to canonical state
- Resource exhaustion: scale up/down within safe bounds
- Cache invalidation: clear stale caches when vendor sites change

**What requires human approval:**
- Code changes (even small ones)
- Database schema modifications
- API contract changes
- Policy adjustments
- Dependency updates

**What NEVER self-heals (always escalate):**
- Security vulnerabilities
- Data corruption
- Multi-tenant isolation breaches
- Financial/billing discrepancies
- Legal/compliance issues

### Runtime Optimization Boundaries

**Auto-apply optimizations (confidence ≥0.8):**
- Cache TTL adjustments (within safe ranges: 1m - 24h)
- Connection pool sizing (within limits: 5-50)
- Batch size tuning (within limits: 10-1000)
- Prefetch strategies (read-only operations)
- Image quality/resolution (within acceptable degradation)

**Require approval (confidence <0.8 OR high impact):**
- Algorithm changes
- Database index creation/deletion
- API rate limit changes
- Cost reduction tactics with quality trade-offs
- Model/provider switching

**Require A/B testing first:**
- User-facing latency changes
- Quality metric changes
- Resource allocation shifts
- Caching strategy overhauls

### Sandbox Verification Gates

Every autonomous remediation MUST pass:

1. **Syntax check** - code compiles/parses
2. **Type check** - type annotations valid (if applicable)
3. **Unit tests** - existing tests still pass
4. **Contract tests** - API contracts preserved
5. **Governance gate** - no Critical/High security issues
6. **Rollback plan** - documented revert path

Sandbox outcomes:
- **GREEN (all pass)** → Promote to staging
- **YELLOW (minor warnings)** → Human review
- **RED (any failure)** → Block, escalate, log to FAILURE_JOURNEY.md

### Daemon vs Event-Driven

**Daemon-based (scheduled, Celery Beat):**
- Performance profiling (hourly)
- Cost analysis (daily)
- Cache effectiveness review (every 6 hours)
- Consistency checks (daily)
- A/B test result evaluation (when tests complete)

**Event-driven (immediate response):**
- Failure detection → self-healing attempt
- Rate limit hit → backoff + fallback
- Vendor site change detected → scraper update
- Memory/CPU spike → scale up
- Error threshold breach → alert + investigate

**Hybrid (daemon monitors, events trigger):**
- Daemon detects "high failure rate" → triggers investigation
- Investigation finds root cause → emits remediation event
- Remediation runs in sandbox → emits outcome event
- Outcome verified → auto-applies or escalates

---

</domain>

<decisions>
## Key Decisions

### 1. Knowledge Graph Consumption

**Decision:** Phase 15 queries Phase 14's knowledge graph for every remediation and optimization decision

**Rationale:**
- Impact analysis requires understanding dependencies
- Self-healing needs to know "what else might break"
- Optimization needs to know "what calls this hot path"
- Without graph, changes are blind

**Alternative considered:** Maintain separate "impact map" → Rejected (duplicate data, sync issues)

### 2. Autonomous vs Governed

**Decision:** Tiered autonomy based on risk + confidence

**Tiers:**
- **Tier 1 (Auto-apply):** Transient fixes, config restoration, safe cache tuning
- **Tier 2 (Approval required):** Code changes, schema changes, policy changes
- **Tier 3 (A/B test first):** User-facing changes, quality trade-offs

**Rationale:** Balance velocity (auto-fix common issues) with safety (human oversight for high-risk changes)

**Alternative considered:** Always require approval → Rejected (defeats purpose of self-healing)

### 3. Sandbox Verification

**Decision:** All autonomous changes MUST pass 6-gate sandbox verification

**Gates:**
1. Syntax check
2. Type check
3. Unit tests
4. Contract tests
5. Governance gate
6. Rollback plan

**Rationale:** Prevents autonomous changes from breaking production

**Alternative considered:** Skip sandbox for "low-risk" changes → Rejected (risk assessment is itself risky)

### 4. Integration with Phase 13.2 Runtime Graph

**Decision:** Correlate Phase 13.2 runtime episodes with Phase 14 structural changes

**Example:** If `src/tasks/enrichment.py` was modified on 2026-02-15 and failures spiked after, flag for review

**Rationale:** Temporal correlation between code changes and failures reveals causation

**Alternative considered:** Treat runtime and structural graphs separately → Rejected (loses valuable correlation)

### 5. Optimization Telemetry

**Decision:** Week-over-week improvement tracking for 5 key metrics:
1. P95 latency (target: -30% per quarter)
2. Cost per operation (target: -20% per quarter)
3. Cache hit rate (target: >80%)
4. Error rate (target: <1%)
5. User-reported issues (target: -50% per quarter)

**Rationale:** Objective measurement prevents "optimization theater"

**Alternative considered:** No explicit metrics → Rejected (can't prove it's working)

### 6. LLM-Driven Remediation Generation

**Decision:** Use LLM to generate remediation code, but ONLY after:
1. Querying knowledge graph for context
2. Reviewing FAILURE_JOURNEY.md for known patterns
3. Sandbox verification passes
4. Human approval (for code changes)

**Rationale:** LLM creativity + graph context + human safety = effective self-healing

**Alternative considered:** Rule-based remediation only → Rejected (can't handle novel failures)

---

</decisions>

<specifics>
## Specific Implementation Patterns

### Performance Profiling (from existing Phase 14 vision)

```python
# Automatic bottleneck identification
bottlenecks = profiler.identify_slowest_operations(
    threshold_ms=500,
    frequency="high"
)

# Query knowledge graph for impact
for bottleneck in bottlenecks:
    module_path = bottleneck['module']

    # Find what depends on this
    impact = graph.query("""
        MATCH (slow:Module {path: $module_path})
        MATCH (caller:Module)-[:CALLS]->(slow)
        RETURN caller.path, count(caller) as call_frequency
        ORDER BY call_frequency DESC
    """, module_path=module_path)

    # High-impact bottleneck = prioritize optimization
    if sum(i['call_frequency'] for i in impact) > 100:
        create_optimization_task(bottleneck, priority='high')
```

### Cost Optimization (from existing Phase 14 vision)

```python
# Vision API cost reduction
cost_optimizer = {
    "current_cost": "$120/month",
    "tactics": [
        {
            "name": "Increase cache TTL 24h -> 7d",
            "savings": "$40/month (33%)",
            "quality_impact": "none",
            "auto_apply": True  # Safe, no quality degradation
        },
        {
            "name": "Reduce image resolution 1200px -> 800px",
            "savings": "$20/month (17%)",
            "quality_impact": "minimal",
            "auto_apply": False  # Requires A/B test
        }
    ]
}

# Query graph for image usage patterns
image_usage = graph.query("""
    MATCH (f:File)-[:CALLS]->(vision:Module {name: 'vision_api'})
    RETURN f.path, count(f) as call_count
    ORDER BY call_count DESC
""")

# Apply safe tactics immediately, schedule A/B tests for risky ones
for tactic in cost_optimizer['tactics']:
    if tactic['auto_apply']:
        apply_optimization(tactic)
        emit_episode(EpisodeType.OPTIMIZATION_APPLIED, tactic)
    else:
        schedule_ab_test(tactic)
```

### Self-Healing Vendor Site Changes (from existing Phase 14 vision)

```python
class VendorSiteMonitor:
    """Detects vendor site changes and auto-fixes"""

    def check_hourly(self):
        for vendor in all_vendors:
            success_rate = get_scraper_success_rate(vendor, hours=24)

            if success_rate < 0.5:  # Dramatic drop
                # Query knowledge graph for vendor-related code
                vendor_code = graph.query("""
                    MATCH (v:Vendor {code: $vendor_code})
                    MATCH (v)-[:HAS_SCRAPER]->(scraper:File)
                    MATCH (scraper)-[:IMPORTS]->(deps:File)
                    RETURN scraper.path, deps.path
                """, vendor_code=vendor.code)

                # Trigger site reconnaissance (from Phase 2.1)
                new_selectors = run_site_reconnaissance(vendor)

                # Generate YAML update
                yaml_update = generate_yaml_update(vendor, new_selectors)

                # Sandbox test
                sandbox_result = test_in_sandbox(yaml_update)

                if sandbox_result == 'GREEN':
                    apply_yaml_update(yaml_update)
                    notify_user(f"{vendor.name} site changed, auto-updated")
                    emit_episode(EpisodeType.SELF_HEALING_SUCCESS, vendor)
                else:
                    escalate_to_user(f"{vendor.name} site changed, manual fix needed")
                    emit_episode(EpisodeType.SELF_HEALING_FAILED, vendor)
```

### Predictive Prefetching (from existing Phase 14 vision)

```python
# User opens "Add Product" page
# ML model predicts next action based on history

from src.assistant.ml import predict_user_action

prediction = predict_user_action(
    user_id=user_id,
    current_page='add_product',
    time_of_day=datetime.now().hour
)

# prediction = {action: 'search_itd', confidence: 0.82}

if prediction['confidence'] > 0.7:
    # Query graph for ITD-related modules
    itd_modules = graph.query("""
        MATCH (v:Vendor {code: 'itd-collection'})
        MATCH (v)-[:HAS_SCRAPER]->(scraper:File)
        MATCH (scraper)-[:IMPORTS]->(cache:Module)
        WHERE cache.name CONTAINS 'cache'
        RETURN cache.path
    """)

    # Prefetch in background
    for module in itd_modules:
        warm_cache(module['path'])
```

---

</specifics>

<deferred>
## Deferred to Future Phases

None - Phase 15 is the final phase in the current roadmap.

However, potential future expansions:
- **Multi-tenant optimization** - per-store optimization strategies
- **Federated learning** - learn from patterns across all tenants (privacy-preserving)
- **Autonomous feature development** - LLM generates and tests new features (far future)

---

</deferred>

---

## Phase 14 → Phase 15 Handoff Checklist

When Phase 15 planning begins, verify Phase 14 delivered:

- [ ] **Neo4j schema extended** - File, Module, Class, Function, PlanningDoc nodes exist
- [ ] **Codebase fully indexed** - All src/ files in graph with relationships
- [ ] **Vector embeddings generated** - All files embedded and searchable
- [ ] **Planning docs as central nodes** - Phases and plans heavily linked
- [ ] **Automatic update triggers working** - Git hook + daemon + manual trigger operational
- [ ] **Query interface for LLMs** - Natural language → Cypher + vector search
- [ ] **Integration with Phase 13.2** - Can query both runtime and structural graphs
- [ ] **Performance baseline established** - Know current latency/cost/error rates

If any checklist item is missing, Phase 15 planning cannot proceed.

---

*Phase: 15-self-healing-dynamic-scripting*
*Context gathered: 2026-02-19*
*Depends on: Phase 14 (Codebase Knowledge Graph) completion*
