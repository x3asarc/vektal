# Phase 14.2: Tool Calling 2.0 Integration

**Status**: PLANNED
**Depends on**: Phase 14.1 (RAG Enhancement - complete 2026-02-23)
**Branch**: `claude/tool-calling-rag-integration-1TpRu`
**Created**: 2026-02-24
**Tagged**: `[developer-facing]` `[token-optimization]` `[knowledge-graph]`

---

## 📚 What This Phase Does

Upgrades **how Claude calls tools** in the RAG/knowledge graph workflow. Integrates Anthropic's "Tool Calling 2.0" patterns (2026-02 release) to reduce token consumption by 30–50%, increase tool accuracy from ~72% to ~90%, and make the tool registry itself graph-searchable.

**This is the bridge between Phase 14.1's knowledge graph foundation and Phase 15's self-healing agents.**

---

## 🎯 Core Goal

Transform the MCP tool interface from description-only schemas to a **self-describing, batch-capable, context-aware** system that:
1. **Learns from usage** - tool effectiveness tracked in the graph
2. **Loads on demand** - deferred loading prevents schema bloat
3. **Batches intelligently** - programmatic execution collapses multi-round-trip flows
4. **Filters aggressively** - compact output mode keeps token budgets honest

---

## Why This Matters (The Token Economics)

Phase 14.1 built:
- MCP server with 3 tools (`query_graph`, `get_dependencies`, `retrieve_intent`)
- Semantic cache (0.92 cosine threshold, 3600s TTL)
- Search-then-Expand bridge (max 5 nodes, depth 2, 8192 token budget)
- Convention guardrails + session lifecycle hooks

**The problem**: Those tools are called 10–50 times per Tier 3 enrichment cycle. Each call:
- Loads full tool schemas (9 tools × ~80 tokens = 720 tokens/call overhead)
- Transfers verbose graph results (raw Cypher output, 50 tokens/node avg)
- Requires separate round-trips for related queries (20 products = 20 `retrieve_intent` calls)

**The cost at production scale**: Bastelschachtel.at processes 4,000 SKUs × 8 vendors × daily updates.
Current token burn: ~150M tokens/month (estimated from Tier 3 logs).
Post-14.2 target: ~75–100M tokens/month (**35–50% reduction**).

---

## Source Material Integration

This phase synthesizes three research streams:

### 1. Anthropic Tool Calling 2.0 Patterns
**Source**: AI Jason — "Anthropic killed Tool Calling" (2026-02 YouTube)

Five core concepts:
- **Programmatic execution**: Code-generated task graphs, not per-call orchestration
- **Context filtering**: Compact output modes, filter before entering LLM context
- **Tool search**: Dynamic schema discovery via graph queries
- **Input examples**: 72% → 90% accuracy on nested/conditional params
- **Deferred loading**: Hide schemas until needed, expose only `search_tools` initially

**Mapped to codebase**: See `.planning/TOOL_CALLING_2_INTEGRATION.md` for complete 85-LOC Phase 13.2 supplement + Phase 14 implementation targets.

### 2. RuVector Research Learnings
**Source**: https://github.com/ruvnet/ruvector (v2.0.4, MIT, 86 Rust crates)

15 integration opportunities identified (see `.planning/research/RUVECTOR-LEARNINGS.md`):

**Priority P1 (This Phase)**:
- **Min-Cut Coherence Filter** - partition retrieved nodes by graph connectivity, not just cosine
- **Edge-Type Score Multiplier** - `IMPLEMENTS` edges score higher than `REFERENCES`
- **Temporal Decay** - stale nodes score lower, even if semantically similar
- **Embedding SHA Manifest** - integrity verification for stored embeddings

**Priority P2 (Phase 15)**:
- **Delta Operations** - git-style versioning for knowledge graph changes
- **GNN Retrieval Frequency Loop** - edge weights adapt based on usage patterns
- **Causal Recall** - rerank by utility (past outcome quality), not just similarity
- **MCP SSE Transport** - HTTP Server-Sent Events for Celery worker access

**Why RuVector matters**: 61µs p50 latency at 16,400 QPS on 384-dim HNSW search (vs Neo4j's 5–50ms). We can't match the speed (pure Rust + SIMD), but we **can** adopt the architectural patterns in Python.

### 3. Phase 14.2 Execution Plan
**Source**: `.planning/phases/14.2-tool-calling-v2/14.2-PLAN.md`

6-wave implementation sequence:
```
Wave 1: Input examples on all schemas            [14.2-01] Zero risk, pure enrichment
Wave 2: Tool nodes in Neo4j + search_tools MCP   [14.2-02] Infrastructure
Wave 3: Deferred loading + schema_json column    [14.2-03] Requires 14.2-02
Wave 4: batch_query + batch_dependencies MCP     [14.2-04] Requires examples
Wave 5: compact_output mode in bridge            [14.2-05] Validates token savings
Wave 6: Batch episode emission in sync           [14.2-06] Celery group() pattern
```

---

## Architecture: Before vs After

### Current (Phase 14.1)
```
Claude → query_graph("who calls X") → mcp_server.py → query_interface.py → Neo4j
       → get_dependencies("file.py")  ↑ (separate round trip)
       → retrieve_intent("why 8192?") ↑ (separate round trip)

Tool schemas: Loaded all 9 upfront (720 tokens overhead/call)
Graph results: Full node dumps (50 tokens/node avg)
Multi-entity: Sequential calls (20 products = 20 separate MCP invocations)
```

### After (Phase 14.2)
```
Claude → search_tools("graph query tools") → returns only query_graph schema
       → batch_query(["who calls X", "what imports Y", "why Z"]) → one call, aggregated results
       → compact_output=true → 30 tokens/node (vs 50), 2.7× more nodes in 8192 budget

Tool schemas: Deferred (only search_tools visible initially), fetched on demand
Graph results: Compact mode default, full mode opt-in
Multi-entity: Batched programmatically, single round trip
Edge weights: IMPLEMENTS=1.3, CALLS=1.1, IMPORTS=0.9, REFERENCES=0.7 (graph topology in scores)
Temporal decay: Nodes older than 6 months score 0.6× even if semantically identical
```

---

## The Five Tool Calling 2.0 Concepts → Codebase Mapping

### C1: Programmatic / Code-Execution Tool Calling

**Problem**: `get_dependencies` internally calls `query_graph()` twice. Tier 3 agents resolving 20 products call `retrieve_intent` 20 times sequentially.

**Solution**:
- Add `batch_query(queries: list[str])` MCP tool
- Add `batch_dependencies(file_paths: list[str])` MCP tool
- Use Celery `group()` in `graphiti_sync.py` for episode batches (not per-episode `.delay()`)

**Files**: `src/graph/mcp_server.py`, `src/tasks/graphiti_sync.py`, `src/jobs/graphiti_ingestor.py`
**Token reduction**: 30–50% on multi-entity Tier 3 flows

---

### C2: Context Window Optimization (Compact Output)

**Problem**: Raw Cypher results with full descriptions consume the 8192-token budget inefficiently. A node with a 300-token description field may only contribute 10 tokens of signal.

**Solution**:
- Add `compact_output: bool = False` param to `query_graph_tool`
- When `True`: return `{path, type, summary}` only (strip verbose fields)
- Adjust token estimates: 30 tokens/node (compact) vs 50 tokens/node (full)
- Result: 2.7× more nodes within same 8192 budget

**Files**: `src/graph/mcp_server.py`, `src/graph/search_expand_bridge.py`
**Token reduction**: ~40% on large graph retrievals with compact mode

---

### C3: Deferred Tool Loading + Tool Search

**Problem**: Currently 3 MCP tools + 6 assistant tools = 9 schemas loaded upfront (720 tokens overhead/call). Phase 15 adds 5+ more. At 15 tools, schema overhead becomes 1,200+ tokens/call.

**Solution**:
- Store tool schemas as `Tool` nodes in Neo4j
- Add `search_tools(query: str)` MCP tool - queries graph for matching tool schemas
- Set `deferred_loading: true` in `.claude/settings.local.json`
- Initially expose only `search_tools`; Claude calls it to discover/load other schemas on demand

**Files**: `src/graph/mcp_server.py`, `src/core/synthex_entities.py`, `src/models/assistant_tool_registry.py` + Alembic migration
**Token reduction**: Scales with tool count - at 15 tools saves ~40% prompt tokens/request

---

### C4: Input Examples in Tool Schemas

**Problem**: All current tool schemas are description-only. Research shows 72% → 90% accuracy improvement for complex nested params simply by adding `input_examples`.

**Solution**: Add `input_examples` key to every tool schema.

**Concrete examples**:

`query_graph`:
```json
"input_examples": [
  {"query": "who imports src/core/graphiti_client.py"},
  {"query": "what conventions exist for error handling"},
  {"query": "show decisions made about the token budget"}
]
```

`batch_query` (new):
```json
"input_examples": [
  {"queries": ["who imports graphiti_client.py", "what calls semantic_cache.py"]},
  {"queries": ["conventions for rate limiting", "decisions about Celery queues"]}
]
```

**Files**: `src/graph/mcp_server.py`, `src/assistant/tool_projection.py`
**Accuracy improvement**: 72% → ~90% on nested/conditional params

---

### C5: RuVector Hybrid Search Integration (Edge-Type Scoring)

**Problem**: Current `search_expand_bridge.py` treats all edge types equally during BFS expansion. A node reached via `IMPLEMENTS` (strong structural signal) scores identically to one reached via `REFERENCES` (weak mention).

**Solution**: Edge-type score multipliers from RuVector hybrid search pattern:

```python
EDGE_SCORE_MULTIPLIER = {
    "IMPLEMENTS": 1.3,    # Strong: actual implementation
    "CALLS": 1.1,         # Medium: direct function call
    "IMPORTS": 0.9,       # Medium-weak: dependency
    "REFERENCES": 0.7,    # Weak: documentation mention
    "EXPLAINS": 1.0       # Neutral: planning doc link
}

# node_final_score = base_cosine_score * EDGE_SCORE_MULTIPLIER[edge_type] * anchor_score
```

**Files**: `src/graph/search_expand_bridge.py` (3-line change)
**Signal improvement**: Immediate - topologically strong nodes surface earlier

---

## Implementation Sequence (6 Waves)

```
Wave 1: High ROI, Zero Risk
  [14.2-01] Input examples on all existing tool schemas
            Files: mcp_server.py, tool_projection.py
            Risk: NONE - pure schema enrichment, no interface changes
            Can ship in isolation

Wave 2: Infrastructure
  [14.2-02] Tool nodes in Neo4j + search_tools meta-tool
            Files: synthex_entities.py (ToolNode), query_templates.py (tool_search), mcp_server.py
            Requires: Nothing - additive schema

  [14.2-03] Deferred loading flag + schema_json column + Alembic migration
            Files: assistant_tool_registry.py, migrations/
            Requires: 14.2-02 (tool nodes must exist before deferring)

Wave 3: Batch/Programmatic
  [14.2-04] batch_query + batch_dependencies MCP tools
            Files: mcp_server.py (2 new tools), register in list_tool_contracts()
            Requires: 14.2-01 (examples) for correctness

  [14.2-05] compact_output mode in search_expand_bridge + query_graph_tool
            Files: mcp_server.py (param), search_expand_bridge.py (compact serialization)
            Requires: 14.2-04 to validate token savings

Wave 4: Sync Optimization
  [14.2-06] Batch episode emission in graphiti_sync + graphiti_ingestor
            Files: graphiti_sync.py (Celery group()), graphiti_ingestor.py (chunk loops)
            Requires: Graphiti client batch API check first
```

---

## Success Criteria (Phase Completion Gates)

1. ✅ All 5 MCP tools (3 existing + `batch_query` + `search_tools`) have `input_examples`
2. ✅ `search_tools("resolve product")` returns at least one matching tool schema from Neo4j
3. ✅ `batch_query(queries=["A", "B", "C"])` returns aggregated results in **one** MCP call
4. ✅ Token consumption for a 10-entity Tier 3 resolution flow drops by ≥30% vs baseline
5. ✅ `compact_output=true` on `query_graph_tool` reduces token usage by ≥20% vs full output
6. ✅ `deferred_loading: true` set in `.claude/settings.local.json` with `search_tools` as entry point
7. ✅ `AssistantToolRegistry.schema_json` column exists, migrated, populated for all 6 tools
8. ✅ Edge-type score multipliers active in `search_expand_bridge.py` (IMPLEMENTS=1.3, etc.)
9. ✅ No existing tests broken - all new behaviour covered by unit tests
10. ✅ Four governance reports GREEN: `self-check.md`, `review.md`, `structure-audit.md`, `integrity-audit.md`

---

## Integration Points with Existing Architecture

| Phase 14.1 Artifact | Phase 14.2 Enhancement |
|---|---|
| `mcp_server.py` — 3 tools | +2 tools (`batch_query`, `search_tools`), `input_examples` on all 5 |
| `search_expand_bridge.py` — 8192 token budget | `compact_output` mode: 30 tokens/node vs 50 |
| `semantic_cache.py` — 0.92 threshold | Cache hits for batch queries (same embedding per sub-query) |
| `synthex_entities.py` — entity contracts | New `ToolNode` entity, `REQUIRES_INTEGRATION`/`ALLOWED_IN` edges |
| `query_templates.py` — Cypher templates | New `tool_search` template |
| `convention_checker.py` — guardrails | `search_tools` results respect tier + Convention constraints |
| `AssistantToolRegistry` model | `schema_json` column for deferred loading |
| `tool_projection.py` | Propagate `input_examples` from `metadata_json` |
| `graphiti_sync.py` | Batch episode emission via Celery `group()` |

---

## RuVector Learnings Applied (Prioritised)

From `.planning/research/RUVECTOR-LEARNINGS.md`:

**Integrated in This Phase (P1)**:
- ✅ **Edge-Type Score Multiplier** (Learning 14) - immediate signal boost, 3-line change
- ✅ **Temporal Decay on Embeddings** (Learning 6) - stale nodes score lower
- ✅ **MCP SSE Transport** (Learning 5) - HTTP transport for Celery worker access
- ✅ **Embedding SHA Manifest** (Learning 10) - integrity verification on stored embeddings
- ✅ **Reflexion Memory Outcome Tagging** (Learning 12) - add `success: bool`, `critique: str` to `ReasoningTrace`

**Deferred to Phase 15 (P2)**:
- ⏭️ **Min-Cut Coherence Filter** (Learning 2) - topological clustering of retrieved nodes
- ⏭️ **Delta Operations** (Learning 3) - git-style knowledge graph versioning
- ⏭️ **GNN Retrieval Frequency Loop** (Learning 11) - edge weights adapt from usage patterns
- ⏭️ **Causal Recall Utility Reranking** (Learning 12) - rerank by past outcome quality, not similarity
- ⏭️ **SONA Loop C: Episode → Decision Promotion** (Learning 13) - auto-promote successful patterns weekly

**Not Adopted**:
- ❌ **RVF Binary Format** - Neo4j handles storage, no clear gain
- ❌ **Raft Consensus** - single-node Neo4j, not distributed
- ❌ **FPGA Transformer** - hardware dependency incompatible with Docker stack

---

## Out of Scope (Defer to Phase 15)

- Vendor web scraper HTML filtering (needs vendor adapter audit first)
- Tree-sitter multi-language AST for Tool node generation
- 1536-dim embedding upgrade for tool semantic search
- Production API call changes for `code-execution-2026-01-20` beta header (needs load test)
- Anytime-Valid Coherence Gate + Compute Ladder (RuVector Learning 1 - governance critical path)

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| MCP `deferred_loading` flag not supported in current SDK | Medium | Check SDK version first; flag is opt-in, skip if not available |
| Graphiti client lacks batch episode API | Medium | Check `graphiti_client.py` emit signature; fall back to chunked sequential |
| `schema_json` column migration breaks CI | Low | Standard Alembic migration; existing pattern in codebase |
| `search_tools` Cypher query returns stale schemas | Low | Invalidate Tool nodes on schema change in `incremental_sync.py` |
| Edge-type multipliers bias results incorrectly | Low | A/B test with multipliers off/on, measure retrieval precision@5 |

---

## Governance

**Reports**: `reports/14.2/<task>/`
**Required**: `self-check.md`, `review.md`, `structure-audit.md`, `integrity-audit.md`
**Gate**: GREEN on all before merge. Block on Critical/High. Block on Medium for Security/Dependency.

**KISS Policy**: Target 150–400 LOC per file. Before creating new modules, ask: "Can an existing file absorb this?"

**Constitutional Addendum** (append to `.planning/KNOWLEDGE_GRAPH_ORACLE.md`):

```markdown
## Tool Calling 2.0 Protocol

### Programmatic execution (Phase 14.2+)
- batch_query MUST be used for >2 related graph queries
- Individual tool calls for batchable operations are PROHIBITED post-14.2
- Celery group() pattern REQUIRED for episode batch ingestion

### Context window discipline
- compact_output=true MUST be default for graph queries returning >5 nodes
- Full output mode requires explicit justification in reasoning trace
- Edge-type score multipliers MUST be applied during BFS expansion

### Tool loading discipline
- Tools marked deferred=True MUST NOT appear in initial system prompt
- search_tools() MUST be called when intent requires tool not in base set
- input_examples MUST be present on all tools with conditional/nested parameters
```

---

## Token Economics Summary

| Optimization | Mechanism | Estimated Saving |
|---|---|---|
| Programmatic batch ingestion | Celery `group()` instead of per-item `.delay()` | 40–50% Celery overhead |
| Batch MCP tools | `batch_query(["A","B","C"])` → 1 call vs 3 | 30–50% multi-entity flows |
| Compact output mode | 30 tokens/node vs 50 | 40% reduction in node-heavy results |
| Tool search (deferred loading) | Only load schemas when searched | 30–40% context reduction per Tier 3 call |
| Input examples | Higher accuracy, fewer retry calls | 18% accuracy gain → fewer correction round trips |
| Edge-type score multipliers | Structural signal in ranking | Qualitative: higher precision, lower noise |

**Combined Phase 14.2 target**: **35–50% reduction in tokens per Tier 3 enrichment cycle**.

At Bastelschachtel.at production scale (4,000 SKUs × 8 vendors × daily):
**Baseline**: ~150M tokens/month
**Post-14.2**: ~75–100M tokens/month
**Cost impact**: ~$500–$750/month savings at OpenRouter rates

---

## Relationship to Phase 14.1 and Phase 15

```
Phase 14.1 (RAG Enhancement) ────┐
  Built:                          │
  - MCP server (3 tools)          │
  - Semantic cache                │
  - Search-then-Expand bridge     │
  - Convention guardrails         │
  - Session lifecycle hooks       │
                                  │
                                  ▼
Phase 14.2 (Tool Calling 2.0) ◄──┘
  Optimizes:
  - How tools are called (batch, deferred, examples)
  - How results are returned (compact, filtered)
  - How schemas are discovered (graph-searchable)
  - Token efficiency (35–50% reduction)
                                  │
                                  │
                                  ▼
Phase 15 (Self-Healing) ◄─────────┘
  Consumes:
  - Optimized tool call patterns (programmatic execution)
  - Graph-searchable tool registry (self-healing agents discover capabilities)
  - Batch MCP interface (distributed Celery workers share graph state via SSE)
  - Causal recall (rerank remediation patterns by past success rate)
```

**Key dependency**: Phase 15's self-healing agents will spawn as Celery workers. They need:
1. SSE transport to access MCP server remotely (14.2-05 adds this)
2. Tool search to discover remediation capabilities (14.2-02 adds this)
3. Batch queries to check 20+ modules for failure patterns in one call (14.2-04 adds this)

**Without 14.2, Phase 15 agents would burn 3–5× more tokens and require a separate Neo4j connection per worker.**

---

## Reference Documents

- `.planning/TOOL_CALLING_2_INTEGRATION.md` - Complete mapping of Tool Calling 2.0 patterns to Synthex codebase
- `.planning/research/RUVECTOR-LEARNINGS.md` - 15 learnings from ruvnet/ruvector (v2.0.4, MIT)
- `.planning/phases/14.2-tool-calling-v2/14.2-PLAN.md` - Detailed 6-wave execution plan
- `ops/STRUCTURE_SPEC.md` - File placement rules and KISS policy
- `STANDARDS.md` - Governance severity definitions
- `.planning/KNOWLEDGE_GRAPH_ORACLE.md` - Constitutional oracle rules (append Tool Calling 2.0 protocol)

---

## Summary: What Gets Built

**5 new/enhanced MCP tools**:
- `query_graph` (enhanced: `compact_output`, `input_examples`)
- `get_dependencies` (enhanced: `input_examples`)
- `retrieve_intent` (enhanced: `input_examples`)
- `batch_query` (new: accept `list[str]`, aggregate results)
- `search_tools` (new: graph-searchable tool discovery)

**Neo4j schema additions**:
- `ToolNode` entity type
- `REQUIRES_INTEGRATION`, `ALLOWED_IN` edges
- `schema_json` storage for deferred loading

**PostgreSQL schema additions**:
- `AssistantToolRegistry.schema_json` column (Alembic migration)

**Scoring enhancements**:
- Edge-type multipliers (IMPLEMENTS=1.3, CALLS=1.1, IMPORTS=0.9, REFERENCES=0.7)
- Temporal decay on embeddings (exp(-0.01 × age_days))
- Compact output mode (30 tokens/node vs 50)

**Integration patterns**:
- Celery `group()` for batch episode ingestion
- SSE transport for remote MCP access (Celery workers)
- Deferred loading via `search_tools` entry point

**Result**: A token-efficient, graph-aware, self-describing tool system ready for Phase 15's distributed self-healing agents.

---

**Next step**: `/gsd:plan-phase 14.2` to generate detailed task PLANs for each wave.
