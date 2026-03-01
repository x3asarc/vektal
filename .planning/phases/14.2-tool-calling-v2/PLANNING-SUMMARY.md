# Phase 14.2: Tool Calling 2.0 Integration - Planning Summary

**Planning Date**: 2026-02-26
**Status**: PLANNING COMPLETE, READY FOR EXECUTION
**Total Plans**: 7 tasks (6 core + 1 optional)
**Estimated Duration**: 5-7 hours total
**Token Savings Target**: 35-50% reduction

---

## Planning Artifacts Created

### Research
- ✅ **14.2-RESEARCH.md** - Comprehensive research synthesis
  - Anthropic Tool Calling 2.0 patterns
  - MCP protocol architecture
  - Neo4j batch operations & optimization
  - Token economics analysis

### Task Plans
- ✅ **14.2-01-PLAN.md** - Input Examples (Wave 1, 30-45min, ZERO RISK)
- ✅ **14.2-02-PLAN.md** - Tool Nodes + search_tools (Wave 2, 60-90min, LOW RISK)
- ✅ **14.2-03-PLAN.md** - Deferred Loading (Wave 2, 45-60min, LOW RISK)
- ✅ **14.2-04-PLAN.md** - Batch Tools (Wave 3, 60-75min, MEDIUM RISK)
- ✅ **14.2-05-PLAN.md** - Compact Output (Wave 3, 45-60min, LOW RISK)
- ✅ **14.2-06-PLAN.md** - Batch Emission (Wave 4, 45-60min, MEDIUM RISK)
- ✅ **14.2-07-PLAN.md** - External Research Tools (Wave 4, 60-90min, LOW RISK, OPTIONAL)

---

## Execution Roadmap

### Wave 1: Zero Risk, High ROI (Can ship immediately)
**Duration**: 30-45 minutes
**Risk**: NONE

**Tasks**:
- 14.2-01: Add `input_examples` to all tool schemas
  - 3 MCP tools + 6 assistant tools
  - Accuracy improvement: 72% → 90%
  - Pure metadata change, no behavior changes

**Deliverables**:
- Updated `src/graph/mcp_server.py` (+30 LOC)
- Migration for `assistant_tool_registry.metadata_json` (+60 LOC)
- Unit tests (+40 LOC)

**Can ship independently**: YES ✅

---

### Wave 2: Infrastructure Foundation
**Duration**: 105-150 minutes (1.75-2.5 hours)
**Risk**: LOW

**Tasks**:
- 14.2-02: Tool nodes in Neo4j + `search_tools` MCP tool
  - Graph-searchable tool registry
  - Semantic tool discovery
  - Foundation for deferred loading

- 14.2-03: Deferred loading + `schema_json` column
  - Alembic migration for persistent schemas
  - Config-driven conditional loading
  - Only `search_tools` loaded initially

**Deliverables**:
- Neo4j schema extension: `ToolNode`, `REQUIRES_INTEGRATION`, `ALLOWED_IN` edges
- New MCP tool: `search_tools`
- PostgreSQL schema: `schema_json` column
- Config: `.claude/settings.local.json` mcp_server section
- Unit tests for both tasks

**Dependencies**: 14.2-03 requires 14.2-02 (tool nodes must exist)

**Can ship independently**: 14.2-02 YES, 14.2-03 NO (needs 14.2-02)

---

### Wave 3: Batch Operations & Optimization
**Duration**: 105-135 minutes (1.75-2.25 hours)
**Risk**: MEDIUM

**Tasks**:
- 14.2-04: `batch_query` + `batch_dependencies` MCP tools
  - Programmatic multi-query execution
  - Token savings: 30-50% on multi-entity flows
  - Latency reduction: 10s → 0.8s (12.5× faster)

- 14.2-05: `compact_output` mode + edge-type scoring
  - Compact serialization: 50 → 30 tokens/node
  - Edge-type multipliers: IMPLEMENTS=1.3, REFERENCES=0.7
  - Temporal decay: 6-month-old nodes score 0.6× base

**Deliverables**:
- 2 new MCP tools with batch capabilities
- Context window optimization (2.7× more nodes in budget)
- Enhanced graph scoring (structural + temporal signals)
- Token reduction tests (measure ≥30% savings)

**Dependencies**: 14.2-04 depends on 14.2-01 (needs input examples for correctness)

**Can ship independently**: Both YES (but 14.2-05 benefits from 14.2-04 validation)

---

### Wave 4: Sync Optimization & External Tools
**Duration**: 105-150 minutes (1.75-2.5 hours)
**Risk**: LOW-MEDIUM

**Tasks**:
- 14.2-06: Batch episode emission (Celery groups)
  - Replace sequential `.delay()` with `group()` pattern
  - Chunk episodes (max 50/chunk)
  - Performance: 100 episodes in ~5s (vs 15s)

- 14.2-07: External research tools (Firecrawl + Perplexity) [OPTIONAL]
  - Fallback cascade: Firecrawl → Perplexity → Local graph
  - `research_vendor` tool for Phase 15 agents
  - `search_documentation` tool with AI search
  - Rate limiting: 10 Firecrawl/hour, 20 Perplexity/hour

**Deliverables**:
- Celery group pattern for episode ingestion
- 2 external MCP integrations (Firecrawl, Perplexity)
- Fallback pattern implementation
- Performance tests (40% Celery overhead reduction)

**Dependencies**: 14.2-06 requires Graphiti client batch API check first

**Can ship independently**: Both YES (14.2-07 is optional enhancement)

---

## Token Economics Summary

| Optimization | Mechanism | Token Saving | Latency Impact |
|--------------|-----------|--------------|----------------|
| Input examples | Accuracy 72%→90% | 18% (fewer retries) | Neutral |
| Tool search | Deferred loading | 30-40% prompt tokens | Neutral |
| Batch queries | Multi-entity collapse | 30-50% multi-entity | -88% latency |
| Compact output | Filter before LLM | 40% node-heavy queries | Neutral |
| Edge scoring | Better ranking | Qualitative | Neutral |
| Batch emission | Celery groups | N/A | -67% dispatch |

**Combined target**: 35-50% reduction in tokens/request

**At production scale** (4,000 SKUs × 8 vendors × daily):
- **Baseline**: ~150M tokens/month
- **After 14.2**: ~75-100M tokens/month
- **Cost savings**: $500-750/month at OpenRouter rates

---

## Risk Assessment

### Zero Risk (Can ship any time)
- ✅ 14.2-01: Input examples (pure metadata)
- ✅ 14.2-02: Tool nodes (additive Neo4j schema)
- ✅ 14.2-05: Compact output (opt-in parameter)
- ✅ 14.2-07: External tools (fail-open, optional)

### Low Risk (Standard testing required)
- ⚠️ 14.2-03: Deferred loading (Alembic migration, config flag)

### Medium Risk (Extra validation needed)
- ⚠️ 14.2-04: Batch tools (multi-query orchestration, error handling)
- ⚠️ 14.2-06: Batch emission (Celery groups, chunking logic)

**Mitigation**: All tasks have rollback plans via config flags or git revert

---

## LOC Summary

| Task | LOC | Complexity | Files Modified | Files Created |
|------|-----|------------|----------------|---------------|
| 14.2-01 | ~130 | Low | 2 | 2 |
| 14.2-02 | ~260 | Medium | 3 | 3 |
| 14.2-03 | ~124 | Low | 3 | 2 |
| 14.2-04 | ~330 | High* | 1 | 2 |
| 14.2-05 | ~218 | Medium | 2 | 2 |
| 14.2-06 | ~235 | Medium | 5 | 2 |
| 14.2-07 | ~386 | Medium | 3 | 4 |
| **TOTAL** | **~1,683** | - | 19 | 17 |

*Note: 14.2-04 breaches KISS 400-LOC threshold - consider extracting handlers to `src/graph/batch_handlers.py`

---

## Dependencies Graph

```
14.2-01 (Input examples)
  ↓
14.2-04 (Batch tools) ──┐
                        ├──> Can execute in parallel
14.2-02 (Tool nodes)    │
  ↓                     │
14.2-03 (Deferred)      │
                        ↓
14.2-05 (Compact output)
                        ↓
14.2-06 (Batch emission)
                        ↓
14.2-07 (External tools) [OPTIONAL]
```

**Critical path**: 14.2-01 → 14.2-04 (batch tools need examples)
**Parallel tracks**: 14.2-02/03 can run alongside 14.2-01

---

## Testing Strategy

### Per-Task Unit Tests
- Each task has dedicated test file
- Coverage target: All new functions + error paths
- Test framework: pytest

### Integration Tests
- Token reduction measurements (14.2-01, 04, 05)
- Performance benchmarks (14.2-04, 06)
- Fallback cascade validation (14.2-07)

### Regression Tests
- Run full test suite after each task
- Ensure no existing tests broken
- Measure baseline metrics before Wave 1

---

## Governance Compliance

### Per-Task Reports (Mandatory)
Each task generates 4 reports in `reports/14.2/<task>/`:
1. `self-check.md` - Builder self-review
2. `review.md` - Two-pass review (blind + context)
3. `structure-audit.md` - StructureGuardian placement check
4. `integrity-audit.md` - IntegrityWarden dependencies/secrets

**Gate**: All 4 must be GREEN before merge

### KISS Policy
- Target: 150-400 LOC/file
- 14.2-04 breaches at ~330 LOC (consider refactor)
- Other tasks compliant

### Rollback Plans
All tasks include:
- Config-based feature flags
- Git revert procedure
- Backward compatibility guarantees

---

## Success Metrics

### Phase-Level Gates (from ROADMAP.md)
1. ✅ All 5 MCP tools have `input_examples`
2. ✅ `search_tools("resolve product")` returns tools from Neo4j
3. ✅ `batch_query(["A", "B", "C"])` works in 1 call
4. ✅ Token consumption drops ≥30% on 10-entity flows
5. ✅ `compact_output=true` reduces tokens ≥20%
6. ✅ `deferred_loading: true` active with `search_tools` entry
7. ✅ `schema_json` column exists and populated
8. ✅ Edge-type multipliers active
9. ✅ No tests broken
10. ✅ All governance reports GREEN

### Production Metrics (Phase 15 validation)
- Tokens/month: Measure baseline → target 35-50% reduction
- Latency P95: Measure multi-entity flows → target 50%+ reduction
- Tool accuracy: Measure correction rate → target <10% (vs ~28% currently)
- Cost: Track OpenRouter spend → target $500-750/month savings

---

## Next Steps

### Immediate (Week 1)
1. Execute Wave 1 (14.2-01) - can ship immediately for quick win
2. Execute Wave 2 in parallel (14.2-02 + 14.2-03)
3. Measure baseline metrics before Wave 3

### Week 2
4. Execute Wave 3 (14.2-04 + 14.2-05)
5. Validate token savings (target ≥30%)
6. Execute Wave 4 (14.2-06 + optional 14.2-07)

### Week 3
7. End-to-end integration testing
8. Production canary deployment (10% traffic)
9. Monitor metrics for 48 hours
10. Full rollout if metrics meet targets

### Phase Closure
11. Create `14.2-VERIFICATION.md` (all gates passed)
12. Create `14.2-SUMMARY.md` (learnings + actual metrics)
13. Update `ROADMAP.md` (mark 14.2 complete)
14. Update `STATE.md` (transition to 14.3 or 15)

---

## Research Sources

All sources documented in `14.2-RESEARCH.md`:
- Anthropic Tool Calling 2.0 documentation
- MCP protocol specifications
- Neo4j Python driver & vector search docs
- Celery canvas primitives
- Context7 library queries (Neo4j, MCP)
- Web searches (Perplexity, tool calling patterns)

---

## Files Ready for Execution

```
.planning/phases/14.2-tool-calling-v2/
├── README.md                      [EXISTING - Phase overview]
├── 14.2-PLAN.md                   [EXISTING - High-level plan]
├── 14.2-RESEARCH.md               [NEW - Research synthesis]
├── 14.2-01-PLAN.md                [NEW - Input examples task]
├── 14.2-02-PLAN.md                [NEW - Tool nodes task]
├── 14.2-03-PLAN.md                [NEW - Deferred loading task]
├── 14.2-04-PLAN.md                [NEW - Batch tools task]
├── 14.2-05-PLAN.md                [NEW - Compact output task]
├── 14.2-06-PLAN.md                [NEW - Batch emission task]
├── 14.2-07-PLAN.md                [NEW - External tools task]
└── PLANNING-SUMMARY.md            [NEW - This file]
```

**Status**: ✅ Planning complete. Ready for execution.

**Recommended start**: 14.2-01 (zero risk, immediate value)

---

**Planning complete. Awaiting execution approval.**
