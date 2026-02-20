# Phase 14: Codebase Knowledge Graph & Continual Learning - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a self-learning codebase knowledge graph that makes all project context immediately visible to LLMs and developers, eliminating massive token consumption and enabling intelligent code optimization suggestions.

**What this phase delivers:**
- Every file, module, class, and function as a node in Neo4j graph
- Dual indexing: explicit relationships (imports, calls) + semantic similarity (vectors)
- Planning docs as central hubs (the "why" behind every piece of code)
- Automatic graph updates via git hooks + daemon + manual triggers
- Query interface for LLMs to find context without reading everything
- Similarity detection for duplicate code and refactoring opportunities

**What this phase does NOT include:**
- Autonomous refactoring execution (Phase 15)
- Runtime performance optimization (Phase 15)
- Self-healing capabilities (Phase 15)

</domain>

<decisions>
## Implementation Decisions

### 1. Phase Scope Redefined

**Decision:** Phase 14 = Codebase Knowledge Graph (foundational), Phase 15 = Self-Healing + Runtime Optimization (action)

**Rationale:**
- Knowledge graph must come first (foundation for all future work)
- Phase 15 needs Phase 14's graph to make intelligent optimization decisions
- Separation of concerns: Phase 14 = intelligence (what could be better?), Phase 15 = action (make it better)

**Phase 15 context:** See `.planning/phases/15-self-healing-dynamic-scripting/15-CONTEXT.md` for integration details

---

### 2. Progressive Verification MVP (PRE-PHASE 14 BASELINE)

**Status:** ✅ IMPLEMENTED (2026-02-20) - Fully operational before Phase 14 begins

**What exists NOW (file-based MVP):**

Phase 14 begins with a **working progressive verification system** that must be upgraded from file-based to graph-based pattern detection.

**MVP Components Created:**

1. **Checkpoint Scripts** (`.claude/checkpoints/`)
   - `checkpoint_1_discussion.sh` - Validates discussion completeness
   - `checkpoint_2_research.sh` - Validates research depth
   - `checkpoint_3_plan.sh` - Validates plan structure
   - `checkpoint_4_execution.sh` - **CRITICAL** Validates tests + captures metrics
   - `checkpoint_4_post_hook.sh` - **NEW** Auto-trigger after pytest (detects phase/plan from git)

2. **Auto-Improvement Engine** (`.claude/auto-improver/`)
   - `on_execution_complete.py` - Main orchestrator (triggered on test completion)
   - `pattern_detector_file_based.py` - File-based pattern detection (5-10s latency)
   - Threshold: ≥3 similar failures = pattern detected
   - Confidence scoring: ≥60% = auto-apply, <60% = escalate

3. **Verifier Agent** (`.claude/agents/change-verifier.md`)
   - Validates improvements before auto-applying
   - Checks: syntax valid, no conflicts, coherent fix, confidence threshold

4. **Skills** (`.claude/skills/verify-phase/`)
   - `verify.sh` - Runs all 4 checkpoints in sequence
   - Available as `/verify-phase <phase>` command

5. **Hooks** (`.claude/hooks/` + `.claude/settings.json`)
   - **SessionStart:** `check-pending-improvements.py` - Shows escalated improvements
   - **PostToolUse:** `checkpoint_4_post_hook.sh` - **NEW** Auto-runs after pytest commands
   - **PreToolUse:** Risk gate on git commits (existing)

6. **Data Storage** (file-based, Phase 14 will move to graph)
   - `.claude/metrics/<phase>/<plan>.json` - Test results + timing + root cause
   - `.claude/learnings.md` - First occurrences logged for pattern tracking
   - `.claude/escalations/pending-improvements.json` - Low-confidence proposals
   - `/tmp/auto-improver.log` - Execution history (optional)

**How MVP Works Today:**

```
Developer runs tests
    ↓
PostToolUse hook triggers checkpoint_4_post_hook.sh (NEW - automatic!)
    ↓
Checkpoint detects phase/plan from git branch/commit/STATE.md
    ↓
Runs checkpoint_4_execution.sh
    ↓
Captures metrics: test_result, duration, root_cause, suggested_fix
    ↓
If FAIL → triggers on_execution_complete.py
    ↓
pattern_detector_file_based.py scans ALL metrics files (5-10s)
    ↓
Finds similar failures (same root_cause)
    ↓
If ≥3 similar → generates improvement proposal
    ↓
Verifier validates proposal → confidence score
    ↓
If ≥60% → auto-apply to .claude/agents/*.md
If <60% → escalate to pending-improvements.json
    ↓
Next session → SessionStart hook shows pending improvements
```

**Performance (MVP):**
- Checkpoint execution: 3-5s (pytest runtime)
- Pattern detection: **5-10s** (scans all JSON files)
- Auto-improvement: 2-3s (LLM + file write)
- Total: **10-18s** per test failure

**What Phase 14 MUST Upgrade:**

| Component | MVP (File-Based) | Phase 14 Target (Graph-Based) |
|-----------|------------------|-------------------------------|
| **Pattern Detection** | Scan all `.claude/metrics/**/*.json` files (5-10s) | Cypher query on Episode nodes (<100ms) |
| **Failure Storage** | JSON files in `.claude/metrics/` | Neo4j Episode entities (already in 13.2 schema) |
| **Learnings** | `.claude/learnings.md` text file | Knowledge graph nodes + relationships |
| **Similarity Search** | String matching on `root_cause` field | Vector embeddings + semantic similarity |
| **Cross-Phase Patterns** | Manual grep across phases | Graph traversal: `MATCH (e:Episode)-[:SIMILAR_TO]->(other)` |
| **Impact Analysis** | None | `MATCH (e:Episode)-[:AFFECTS]->(f:File)-[:IMPORTED_BY*]->(dep)` |

**Critical Integration Points for Phase 14:**

1. **Episode Emission Already Works** (from Phase 13.2):
   ```python
   # src/assistant/governance/verification_oracle.py
   emit_episode(
       episode_type=EpisodeType.ORACLE_DECISION,
       store_id=...,
       phase="14",
       plan="14-01",
       test_result="FAIL",
       root_cause="missing_dependency:neo4j-driver",
       suggested_fix="Add neo4j to requirements.txt"
   )
   ```
   ✅ Episodes are already being emitted to Neo4j (13.2-02)
   ✅ Emission hooks are fail-open (won't break if graph unavailable)
   ❌ pattern_detector is still file-based (reads JSON, not graph)

2. **File → Graph Migration Path:**
   ```python
   # Phase 14 Plan: Migrate pattern_detector_file_based.py → pattern_detector_graph.py

   # OLD (MVP):
   def find_similar_failures(metrics_file):
       all_metrics = glob(".claude/metrics/**/*.json")  # 5-10s
       similar = [m for m in all_metrics if m.root_cause == current.root_cause]
       return similar

   # NEW (Phase 14):
   def find_similar_failures(episode_id):
       query = """
           MATCH (e:Episode {id: $episode_id})
           MATCH (similar:Episode)
           WHERE similar.root_cause = e.root_cause
           AND similar.test_result = 'FAIL'
           RETURN similar
       """
       return graph.execute(query)  # <100ms
   ```

3. **Hooks Keep Working:**
   - PostToolUse hook (`checkpoint_4_post_hook.sh`) continues to trigger
   - Instead of calling `pattern_detector_file_based.py`, calls `pattern_detector_graph.py`
   - No user-facing changes - same workflow, 100x faster backend

4. **Backward Compatibility:**
   - Phase 14 must import existing `.claude/metrics/**/*.json` files as Episodes
   - One-time migration script: `scripts/migrate_metrics_to_graph.py`
   - After migration, file-based storage deprecated

**Phase 14 Success Criteria Addition:**

9. **Pattern detection <100ms** - Graph queries replace file scans (100x speedup)
10. **Historical metrics in graph** - All `.claude/metrics/` data migrated to Episodes
11. **Auto-improver uses graph** - `pattern_detector_graph.py` replaces file-based version
12. **Hooks unchanged** - PostToolUse/SessionStart continue working (transparent upgrade)

**Documentation References:**
- MVP quickstart: `.claude/PROGRESSIVE_VERIFICATION_QUICKSTART.md`
- MVP completion: `.claude/MVP_IMPLEMENTATION_COMPLETE.md`
- Auto-improver README: `.claude/auto-improver/README.md`
- Full specification: `.planning/enhancements/GSD_PROGRESSIVE_VERIFICATION.md`

---

### 4. Trigger Mechanism: Hybrid 4-Layer

**Decision:** Multiple triggers that cross-validate each other with clear precedence

**Layers:**
1. **Git pre-commit hook** (PRIMARY)
   - Runs on every commit
   - Scans changed files, updates graph relationships
   - Can block commit if graph sync fails (ensures accuracy)
   - Catches 95% of changes reliably

2. **LLM instructions in .md files** (ENRICHMENT)
   - Instructions in `claude.md`, `codex.md`, `gemini.md`
   - LLM logs intent + context when generating code
   - Enriches graph with semantic meaning ("why" not just "what")
   - Only works for AI-generated code

3. **Periodic scan daemon** (FALLBACK)
   - Runs hourly or daily
   - Full codebase scan
   - Finds divergence between graph and reality
   - Catches manual edits outside git, repairs inconsistencies

4. **Manual trigger command** (DEBUG/OVERRIDE)
   - `/sync-graph` or `gsd:sync-graph`
   - Force full rescan on-demand
   - For testing, debugging, recovery after issues

**Cross-validation:**
```python
# Git hook checks graph freshness
if graph.last_sync_time < (now - 1 hour):
    warn("Graph may be stale - run daemon sync first")

# Daemon detects divergence
files_in_codebase = scan_src_directory()
files_in_graph = query_graph("MATCH (f:File) RETURN f.path")
missing = files_in_codebase - files_in_graph
if missing:
    log(f"Found {len(missing)} files not in graph - syncing")
```

**Implementation sequence (8 plans across 4 waves):**

**Wave 1: Foundation**
- Plan 14-01: Extend Neo4j schema for codebase entities
- Plan 14-02: Vector embedding pipeline

**Wave 2: Initial Population**
- Plan 14-03: Full codebase scanner + manual sync command (Layer 4)
- Plan 14-04: Planning docs as central nodes

**Wave 3: Automatic Updates**
- Plan 14-05: Git pre-commit hook integration (Layer 1)
- Plan 14-06: Periodic consistency daemon (Layer 3)

**Wave 4: AI Enrichment**
- Plan 14-07: LLM instruction framework (Layer 2)
- Plan 14-08: Query interface for LLMs

---

### 3. Graph Scope: Track Everything

**Decision:** Index all project artifacts with semantic similarity detection

**What gets tracked:**
- ✅ Source code (`src/`) - all Python modules, classes, functions
- ✅ Tests (`tests/`) - track what they test, coverage relationships
- ✅ Planning docs (`.planning/`) - phases, plans, requirements (**CENTRAL NODES**)
- ✅ Documentation (`docs/`) - architecture docs, guides, references

**Relationships captured:**
- **Explicit:** imports, calls, references, inheritance, tests, planning_doc_references
- **Semantic:** vector similarity (find related code without explicit links)

**Rationale:** Comprehensive graph enables finding anything related to anything else, eliminating need to read entire codebase.

---

### 4. Similarity Handling: Three-Tier Strategy

**Decision:** Different actions based on similarity level with intelligent refactoring

| Similarity | What It Means | Action | Pattern |
|------------|---------------|--------|---------|
| **95-100%** | True duplicates (copy-paste) | Delete duplicate | DRY principle |
| **80-95%** | Shared core + parameterizable variants | Extract + parameterize | Single function with parameters |
| **60-80%** | Shared pattern, different implementation | Extract utilities + interface | Template Method or Strategy pattern |
| **40-60%** | Related domain | Share low-level utilities only | Utilities library |
| **<40%** | Coincidental similarity | Keep separate | No action |

**Key insight:**
> "84% similar doesn't mean merge blindly - it means 84% shared logic + 16% variant behavior. Extract the 84%, parameterize the 16%."

**Example (80-95% case):**
```python
# BEFORE: Two similar files (84% similar)
def parse_colors_shopify(text):
    colors = extract_keywords(text)  # 84% shared
    return normalize_to_english(colors)  # 16% different

def parse_colors_vendor(text):
    colors = extract_keywords(text)  # 84% shared (DUPLICATE!)
    return normalize_to_german(colors)  # 16% different

# AFTER: Extract + parameterize
def parse_colors(text, language='english'):
    """Unified function serving both use cases"""
    colors = extract_keywords(text)  # 84% extracted ONCE
    if language == 'german':
        return normalize_to_german(colors)
    return normalize_to_english(colors)

# Callers updated:
shopify_colors = parse_colors(product.title, language='english')
vendor_colors = parse_colors(catalog.name, language='german')
```

**Example (60-80% case):**
```python
# Two files 65% similar → Extract shared utilities + keep separate strategies

# BEFORE: 200 lines each, 65% duplicated
class PlaywrightScraper:  # 200 lines
    # Duplicate validation, retry, parsing...

class RequestsScraper:  # 200 lines
    # Duplicate validation, retry, parsing...

# AFTER: 3 files, 200 total lines (50% reduction)
# base.py (100 lines) - shared template
class BaseScraper(ABC):
    def scrape(self, url, config):
        self.validate_url(url)  # Shared
        client = self.setup_client()  # Subclass implements
        html = self.retry_with_backoff(lambda: self.fetch(url, client))  # Shared
        return self.parse_html(html, config)  # Shared

# strategies/playwright_scraper.py (50 lines) - Playwright specifics only
class PlaywrightScraper(BaseScraper):
    def setup_client(self): ...
    def fetch(self, url, client): ...

# strategies/requests_scraper.py (50 lines) - Requests specifics only
class RequestsScraper(BaseScraper):
    def setup_client(self): ...
    def fetch(self, url, client): ...
```

---

### 5. Refactoring Autonomy: Governed Auto-Apply

**Decision:** Phase 14 detects and flags, Phase 15 executes with verification gates

**Phase 14 role (detection only):**
- Identifies similarity clusters
- Calculates metrics:
  - Similarity score (0.0-1.0)
  - Impact radius (how many files import these)
  - Test coverage (are they tested?)
  - Complexity score (LOC, cyclomatic complexity)
- **Outputs suggestions** to queue for Phase 15
- **Does NOT modify code** (read-only)

**Phase 15 role (execution with gates):**
- Reads Phase 14's suggestions
- For each suggestion, runs **6-gate verification pipeline**:
  1. **Metric thresholds** (similarity ≥0.90, impact radius ≤15, coverage ≥0.80)
  2. **LLM generates refactoring plan**
  3. **Sandbox execution**
  4. **All tests pass** (100%)
  5. **Contract tests pass** (no breaking changes)
  6. **Governance gate** (GREEN - no security issues)
- **If all pass** → auto-apply, update graph, notify user
- **If any fail** → escalate with detailed report

**Rationale:** Separation of concerns - detection is Phase 14 (intelligence), execution is Phase 15 (action with safety).

---

### 6. File Organization Philosophy

**Decision:** More files + less code > fewer files + more code

**Key insight:**
> "More files that are cleaner, smaller, and documented = faster codebase"

**Why superior:**
- Faster IDE indexing (smaller files to parse)
- Faster git operations (smaller diffs, fewer merge conflicts)
- Faster human comprehension (50 lines in 2 seconds vs 500 lines in 20 seconds)
- Parallel team work (multiple devs editing different files)
- Less memory (Python loads only imported modules)

**Example:**
- Before: 2 files, 400 total lines
- After: 3 files (base + 2 strategies), 200 total lines
- Result: +1 file, -50% code, better organization

**Pattern:** Extract shared logic → new `base.py`, keep specific logic in separate files

**Real-world validation:** This codebase already follows this pattern:
- `src/assistant/runtime_tier1.py`, `runtime_tier2.py`, `runtime_tier3.py` (separate, not one file)
- `src/scraping/strategies/playwright_scraper.py`, `requests_scraper.py` (separate strategies)

---

### 7. Vector Embedding Strategy: Hierarchical Summaries

**Decision:** Embed file summaries + function summaries (NOT full content)

**User's keyboard analogy:**
> "I can see letters, numbers, special characters, Fn keys separately. I don't need to zoom in on each key."

**Translation:**
- **File-level embedding:** docstring + purpose + list of exports
- **Function-level embedding:** signature + docstring (NOT full implementation)
- **Class-level embedding:** docstring + method signatures

**Embedding structure:**
```python
# File summary embedding
file_embedding = embed(
    f"File: {file_path}\n"
    f"Purpose: {file_docstring}\n"
    f"Exports: {', '.join(exported_names)}\n"
    f"Imports: {', '.join(import_names)}"
)

# Function summary embedding (each function separately)
function_embedding = embed(
    f"Function: {module}.{class_name}.{function_name}\n"
    f"Signature: {signature}\n"
    f"Purpose: {function_docstring}\n"
    f"File: {file_path}"
)
```

**Why summaries, not full content:**
- Current scale: small codebase, no users yet
- Summaries capture intent without noise
- Faster queries (smaller embeddings)
- Future-proof: structure scales as codebase grows

**Embedding model:**
- Primary: `sentence-transformers` (local, free, already in use)
- Fallback: OpenAI embeddings (for complex semantic queries if needed)

**Update frequency:**
- On file change (real-time via git hook)
- Batch re-embed nightly (catch any missed changes)

---

### 8. Vector Storage: Neo4j Vector Index

**Decision:** Store embeddings IN Neo4j as node properties, use Neo4j vector index for queries

**Rationale:**
- **Integrated queries:** Combine graph + vector in ONE query
  ```cypher
  // Find files similar to X that import Y
  MATCH (f:File)-[:IMPORTS]->(target {path: 'src/core/cache.py'})
  CALL db.index.vector.queryNodes('file_embeddings', 5, f.embedding)
  YIELD node, score
  RETURN node.path, score
  ```

- **Future Shopify semantic search:** Same vector infrastructure
  ```cypher
  // Find products similar to user query
  CALL db.index.vector.queryNodes('product_embeddings', 10, $query_embedding)
  YIELD node, score
  WHERE node:Product
  RETURN node.title, score
  ```

- **One database:** Simpler deployment, one connection pool, one backup strategy

**Alternative considered:** PostgreSQL pgvector
- **Rejected:** Would split vectors across two systems (code in Neo4j, products in PostgreSQL)
- Trade-off: More complex setup now (Neo4j + vector extension) vs simpler architecture long-term

**User insight:**
> "More complex now, simpler later. PostgreSQL is tables, Neo4j uses Cypher for graph queries. Worth the investment."

---

### 9. Planning Docs Centrality: Both Natural + Auto-Link

**Decision:** Hybrid approach - bootstrap with auto-linking, let natural references accumulate over time

**Auto-linking at commit time:**
```python
# Parse commit message for phase reference
commit_msg = "feat(13.2-03): add graph oracle adapter"

# Extract: Phase 13.2, Plan 03
phase_match = re.search(r'(\d+\.?\d*)-(\d+)', commit_msg)
if phase_match:
    phase = phase_match.group(1)  # "13.2"
    plan = phase_match.group(2)   # "03"

    # Link all changed files to planning doc
    plan_path = f".planning/phases/{phase}-*/13.2-03-PLAN.md"
    for file in changed_files:
        graph.create_edge(file, "IMPLEMENTS", plan_path)
```

**Natural references:**
```python
# Code comments reference phases
# src/core/graphiti_client.py
def get_graphiti_client():
    """
    Graph client singleton with fail-open behavior.

    Related to Phase 13.2-01: Neo4j runtime + graph client
    """
    ...

# Automatically detected and linked when file is scanned
```

**Why hybrid:**
- Auto-linking ensures every commit is traceable to a plan (governance)
- Natural references capture design intent (semantic meaning)
- Planning docs become central hubs organically (most-referenced = most-central)

**Visualization:** Obsidian-style graph viewer showing planning docs as large central nodes with many connections

---

### 10. Query Interface for LLMs: Hybrid (Templates + Custom)

**Decision:** Pre-built query templates for common patterns (95% of use), natural language fallback for novel questions

**Common query templates:**
```python
QUERY_TEMPLATES = {
    "imports": """
        MATCH (f:File {path: $file_path})-[:IMPORTS]->(imported:File)
        RETURN imported.path, imported.purpose
    """,

    "imported_by": """
        MATCH (f:File {path: $file_path})<-[:IMPORTS]-(importer:File)
        RETURN importer.path, importer.purpose
    """,

    "similar_files": """
        MATCH (f:File {path: $file_path})
        CALL db.index.vector.queryNodes('file_embeddings', 5, f.embedding)
        YIELD node, score
        WHERE score > 0.8
        RETURN node.path, node.purpose, score
    """,

    "planning_context": """
        MATCH (f:File {path: $file_path})-[:IMPLEMENTS]->(plan:PlanningDoc)
        RETURN plan.path, plan.phase_number, plan.goal
    """,

    "impact_radius": """
        MATCH (f:File {path: $file_path})<-[:IMPORTS*1..3]-(dependent:File)
        RETURN dependent.path, length(path) as depth
        ORDER BY depth
    """,

    "phase_code": """
        MATCH (plan:PlanningDoc {phase_number: $phase})<-[:IMPLEMENTS]-(f:File)
        RETURN f.path, f.purpose
    """
}
```

**Natural language fallback:**
```python
# For novel questions not in templates
def query_graph_natural_language(question: str):
    # LLM converts question to Cypher
    cypher = llm.generate_cypher(
        question=question,
        schema=graph.get_schema(),
        examples=QUERY_TEMPLATES
    )

    # Execute generated query
    return graph.execute(cypher)

# Example:
# Q: "What files would break if I delete src/core/cache.py?"
# Cypher: MATCH (f:File {path: 'src/core/cache.py'})<-[:IMPORTS]-(dependent) ...
```

**Why hybrid:**
- Templates = fast, reliable, no LLM cost (95% of queries)
- Natural language = flexible for edge cases (5% of queries)
- Best of both worlds: performance + flexibility

**Performance:**
- Template queries: <100ms (direct Cypher)
- Natural language queries: 500ms-2s (LLM translation + execution)
- Timeout: 5s (fail gracefully if exceeded)

---

### Claude's Discretion

**Areas where Claude decides during planning/implementation:**
- Exact Neo4j indexes to create (based on common query patterns)
- Cypher query optimization techniques
- Error handling for graph unavailability
- Daemon scheduling frequency (hourly vs daily)
- LLM prompt engineering for Cypher generation
- Graph visualization UI framework (if building viewer)

</decisions>

<specifics>
## Specific Ideas

### Keyboard Analogy (User's Mental Model)

> "If I'm looking at my keyboard, I can see: letters, numbers, special characters, Fn keys separately. I don't need to zoom into each key."

**Applied to codebase:**
- **Letters** = files (see file names, purposes)
- **Numbers** = classes (see class names, responsibilities)
- **Special chars** = functions (see function signatures, purposes)
- **Fn keys** = planning docs (see phase goals, requirements)
- **Don't zoom in** = don't embed full implementations, just summaries

### More Files = Faster Codebase

**Mental model shift:**
- OLD: "More files = larger codebase = slower"
- NEW: "More files + less code = cleaner organization = faster"

**Real example:**
- Before refactoring: 2 files, 400 lines total
- After refactoring: 3 files, 200 lines total
- Benefit: -50% code, +better organization, +faster comprehension

### Integration with Future Shopify Semantic Search

**User mentioned:** Vector embeddings will be reused for Shopify product search

**Implication:** Neo4j vector infrastructure built in Phase 14 enables:
```cypher
// Phase 14: Find similar code files
CALL db.index.vector.queryNodes('file_embeddings', 5, $query_embedding)
YIELD node WHERE node:File RETURN node

// Future phase: Find similar Shopify products
CALL db.index.vector.queryNodes('product_embeddings', 10, $query_embedding)
YIELD node WHERE node:Product RETURN node
```

Same infrastructure, different node types = architectural consistency.

---

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 14 scope.

Runtime optimization, self-healing, and autonomous refactoring execution are Phase 15 territory (see `15-CONTEXT.md`).

---

</deferred>

---

## Success Criteria (What Must Be TRUE)

1. **Every file is a node** - All `src/`, `tests/`, `.planning/`, `docs/` files indexed in graph
2. **Relationships captured** - Imports, calls, references, tests, planning_doc links tracked
3. **Semantic similarity works** - Vector search finds related files without explicit links
4. **Planning docs are central** - Phases/plans have most connections, easy to query "what code implements Phase X?"
5. **Graph updates automatically** - Git hook + daemon + manual trigger all working, cross-validating
6. **LLMs can query efficiently** - Template queries <100ms, natural language queries <2s
7. **Similarity detection accurate** - Correctly identifies 95-100% (duplicates), 80-95% (parameterizable), 60-80% (shared utilities)
8. **Context visible without token cost** - Query graph instead of reading files, 10x reduction in tokens needed

---

## Phase 14 → Phase 15 Handoff Requirements

When Phase 15 planning begins, verify Phase 14 delivered:

- [ ] **Neo4j schema extended** - File, Module, Class, Function, PlanningDoc nodes exist
- [ ] **Codebase fully indexed** - All src/ files in graph with relationships
- [ ] **Vector embeddings generated** - All files embedded with hierarchical summaries
- [ ] **Planning docs as central nodes** - Auto-linking at commit + natural references working
- [ ] **Automatic update triggers working** - Git hook + daemon + manual all operational
- [ ] **Query interface for LLMs** - Templates + natural language fallback ready
- [ ] **Integration with Phase 13.2** - Can query both runtime and structural graphs
- [ ] **Similarity detection operational** - Can identify refactoring candidates with metrics

If any requirement missing, Phase 15 cannot proceed.

---

*Phase: 14-continuous-optimization-learning*
*Context gathered: 2026-02-19*
*Ready for: Research → Planning → Execution*
