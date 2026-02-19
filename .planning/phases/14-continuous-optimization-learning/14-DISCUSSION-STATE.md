# Phase 14 Discussion State - In Progress

**Date:** 2026-02-19
**Status:** Partial - continue in next session if needed

---

## Decisions Made So Far

### 1. Phase Scope Redefined ✅

**Decision:** Phase 14 is **Codebase Knowledge Graph & Continual Learning**, NOT runtime optimization.

**Rationale:**
- Knowledge graph is foundational infrastructure (must come first)
- Runtime optimization (old Phase 14 content) moved to Phase 15
- Phase 15 = Self-Healing + Runtime Optimization (combined)

**Phase 15 context already created:** `.planning/phases/15-self-healing-dynamic-scripting/15-CONTEXT.md`

---

### 2. Trigger Mechanism: Hybrid 4-Layer ✅

**Decision:** Multiple triggers that cross-validate each other

**Layers:**
1. **Git pre-commit hook** (PRIMARY) - catches 95% of changes, reliable, blocks commit if sync fails
2. **LLM instructions in .md files** (ENRICHMENT) - captures intent/context for AI-generated code
3. **Periodic scan daemon** (FALLBACK) - hourly/daily full scan, catches missed changes, repairs inconsistencies
4. **Manual trigger command** (DEBUG) - `/sync-graph` for testing, recovery, force rebuild

**Implementation sequence (8 plans across 4 waves):**

**Wave 1: Foundation**
- Plan 14-01: Extend Neo4j schema (File, Module, Class, Function, PlanningDoc nodes)
- Plan 14-02: Vector embedding pipeline (embed all files, store embeddings)

**Wave 2: Initial Population**
- Plan 14-03: Full codebase scanner + manual sync command (Layer 4)
- Plan 14-04: Planning docs as central nodes

**Wave 3: Automatic Updates**
- Plan 14-05: Git pre-commit hook integration (Layer 1)
- Plan 14-06: Periodic consistency daemon (Layer 3)

**Wave 4: AI Enrichment**
- Plan 14-07: LLM instruction framework for intent capture (Layer 2)
- Plan 14-08: Query interface for LLMs (natural language → Cypher + vector search)

---

### 3. Graph Scope: Track Everything ✅

**Decision:** Index all project artifacts with semantic similarity detection

**What gets tracked:**
- ✅ Source code (`src/`) - all Python modules, classes, functions
- ✅ Tests (`tests/`) - track what they test, coverage relationships
- ✅ Planning docs (`.planning/`) - phases, plans, requirements (CENTRAL NODES)
- ✅ Documentation (`docs/`) - architecture docs, guides, references

**Relationships captured:**
- Explicit: imports, calls, references, inheritance, tests
- Semantic: vector similarity (find related code without explicit links)

---

### 4. Similarity Handling: Three-Tier Strategy ✅

**Decision:** Different actions based on similarity level

| Similarity | What It Means | Action | Pattern |
|------------|---------------|--------|---------|
| **95-100%** | True duplicates (copy-paste) | Delete duplicate | DRY principle |
| **80-95%** | Shared core + variants | Extract + parameterize | Single function with parameters |
| **60-80%** | Shared pattern, different implementation | Extract utilities + interface | Template Method or Strategy pattern |
| **40-60%** | Related domain | Share low-level utilities only | Utilities library |
| **<40%** | Coincidental similarity | Keep separate | No action |

**Key insight from user:**
> "84% similar doesn't mean merge blindly - it means 84% shared logic + 16% variant behavior. Extract the 84% into shared function, parameterize the 16% differences."

**Example:**
```python
# Two files 84% similar → ONE unified function with parameters

# BEFORE: Duplication
def parse_colors_shopify(text):
    colors = extract_keywords(text)  # 84% shared
    return normalize_to_english(colors)  # 16% different

def parse_colors_vendor(text):
    colors = extract_keywords(text)  # 84% shared (duplicate!)
    return normalize_to_german(colors)  # 16% different

# AFTER: Extract + parameterize
def parse_colors(text, language='english'):
    colors = extract_keywords(text)  # 84% extracted ONCE
    if language == 'german':
        return normalize_to_german(colors)
    return normalize_to_english(colors)
```

---

### 5. Refactoring Autonomy: Governed Auto-Apply ✅

**Decision:** Auto-apply refactoring IF it passes objective verification gates

**For 60-80% similar files:**
- Graph identifies similarity clusters
- AI analyzes: shared logic vs variant logic
- AI generates refactoring plan (extract utilities, create base class, etc.)
- **6-Gate Verification Pipeline:**
  1. Metric thresholds (similarity ≥0.90, impact radius ≤15, coverage ≥0.80)
  2. LLM generates refactoring plan
  3. Sandbox execution
  4. All tests pass (100%)
  5. Contract tests pass (no breaking changes)
  6. Governance gate (GREEN - no security issues)
- **If all pass** → auto-apply, update graph linkage, notify user
- **If any fail** → escalate with detailed report

**For merge suggestions:**
- Phase 14: Detects opportunity, flags candidates, calculates metrics
- Phase 15: Generates refactoring, verifies, applies (autonomous with gates)

---

### 6. File Organization Philosophy ✅

**Decision:** More files + less code > fewer files + more code

**Key insight from user:**
> "More files that are cleaner, smaller, and documented = faster codebase"

**Why this is superior:**
- Faster IDE indexing (smaller files to parse)
- Faster git operations (smaller diffs)
- Faster human comprehension (50 lines in 2s vs 500 lines in 20s)
- Parallel team work (no merge conflicts)
- Less memory (Python loads only imported modules)

**Example:**
- Before: 2 files, 400 total lines
- After: 3 files (base + 2 strategies), 200 total lines
- Result: +1 file, -50% code, better organization

**Pattern:** Extract shared logic → new `base.py`, keep specific logic in separate files

---

## Remaining Questions (NOT YET DISCUSSED)

### 7. Vector Embedding Strategy ⏸️

**Need to decide:**
- What to embed?
  - Option A: Full file content
  - Option B: File summary (docstring + function signatures)
  - Option C: Each function separately
  - Option D: Hierarchical (file + classes + functions)
- Where to store embeddings?
  - Option A: Neo4j vector index (integrated with graph)
  - Option B: Separate vector DB (Qdrant, Pinecone, Weaviate)
  - Option C: PostgreSQL pgvector (already have PostgreSQL)
- When to re-embed?
  - Option A: On every file change (real-time)
  - Option B: Batch daily (off-hours)
  - Option C: On-demand when querying (lazy)
- Which embedding model?
  - Option A: sentence-transformers (local, free, already in use)
  - Option B: OpenAI embeddings (API, cost, higher quality)
  - Option C: Cohere embeddings (API, optimized for code)

**User preference:** ???

---

### 8. Planning Docs Centrality ⏸️

**Context from earlier discussion:**
> "Planning docs, the phases, should be the main references, kind of like the center of the knowledge graph. The center exists as far as how much one file is referenced or linked to."

**Need to decide:**
- How to make phases/plans "central hubs"?
  - Option A: Special node type `PlanningDoc` with higher query weight
  - Option B: Just natural (many edges = central automatically)
  - Option C: Explicit metadata `is_planning_doc=true` + boost in queries
- How to link code to planning docs?
  - Option A: Manual annotations in code (`# Related to Phase 13.2`)
  - Option B: Automatic detection (commit messages reference phase)
  - Option C: Graph query at commit time (what phase is this commit for?)
- How to visualize centrality?
  - Option A: Obsidian-style graph viewer (interactive)
  - Option B: Text-based centrality report (top 20 most-linked files)
  - Option C: Both

**User preference:** ???

---

### 9. Query Interface for LLMs ⏸️

**Need to decide:**
- How do LLMs query the graph?
  - Option A: Natural language → Cypher translation (LLM converts)
  - Option B: Pre-built query templates (common patterns)
  - Option C: Hybrid (templates + custom Cypher)
- How to combine graph + vector search?
  - Option A: Query graph for structure, then vector search for similarity
  - Option B: Vector search first, then expand via graph relationships
  - Option C: Parallel queries, merge results by relevance score
- What queries should be available?
  - "What files import X?"
  - "What files are similar to X?"
  - "What would break if I change X?"
  - "What planning doc explains why X exists?"
  - "Show me all code related to Phase 13.2"
  - Others?

**User preference:** ???

---

### 10. Performance & Scalability ⏸️

**Need to decide:**
- How to keep queries fast as codebase grows?
  - Option A: Neo4j indexes on common query patterns
  - Option B: Query result caching (Redis)
  - Option C: Materialized views for expensive queries
- Query timeout limits?
  - Option A: 2 seconds (same as Phase 13.2 graph oracle)
  - Option B: 5 seconds (more complex queries)
  - Option C: Tiered (simple=2s, complex=10s, background=60s)
- When to rebuild full graph?
  - Option A: Never (incremental updates only)
  - Option B: Weekly (full consistency check + rebuild)
  - Option C: On-demand (manual trigger when drift detected)

**User preference:** ???

---

## Integration with Phase 13.2 (Already Clear)

Phase 14 codebase graph **complements** Phase 13.2 runtime graph:

**Phase 13.2 (Existing):**
- Runtime operational events (oracle_decision, failure_pattern, enrichment_outcome, etc.)
- Temporal knowledge: what happened, when, why

**Phase 14 (New):**
- Codebase structural/semantic knowledge (files, modules, classes, functions)
- Architectural knowledge: what exists, how it relates

**Integration point:**
- Phase 15 queries BOTH graphs to make intelligent decisions
- Example: "File X failed at runtime (13.2) after structural change Y (14) → correlation detected"

---

## Next Steps

### If continuing discussion in SAME session:
1. Answer questions 7-10 above
2. Update 14-CONTEXT.md with all decisions
3. Move to research phase (`/gsd:research-phase 14`) or planning (`/gsd:plan-phase 14`)

### If continuing in NEW session:
1. Read this file (14-DISCUSSION-STATE.md)
2. Read 14-CONTEXT.md (partial - decisions 1-6 captured)
3. Read 15-CONTEXT.md (Phase 15 integration points)
4. Continue with questions 7-10
5. Complete 14-CONTEXT.md
6. Then research/planning

---

## Token Usage Note

At time of saving: ~93,000 / 200,000 tokens used (46%)
Remaining capacity: ~107,000 tokens

Estimated tokens needed to finish discussion: ~20,000
**Conclusion:** Can likely finish in this session, but state saved as precaution.

---

*Saved: 2026-02-19*
*Status: PARTIAL - continue discussion*
