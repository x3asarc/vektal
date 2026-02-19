# Phase 14: Codebase Knowledge Graph & Continual Learning

**Status**: Ready for planning (context complete)
**Created**: 2026-02-08
**Redefined**: 2026-02-19

---

## 📚 Evolution History

> **Meta-note:** This README demonstrates what Phase 14 will do - track how things change over time and why. One file, two versions, clear lineage.

### Version 1.0 (2026-02-08): Runtime Optimization Vision

**Original scope:**
- Performance optimization (cache tuning, query optimization)
- Machine learning from user behavior
- Autonomous agents (cost optimizer, query optimizer)
- Predictive intelligence (prefetching, resource allocation)
- A/B testing framework
- Self-healing systems

**Why it changed:**
This vision was **too late** in the dependency chain. To optimize intelligently, the system needs to understand code structure FIRST. You can't optimize what you can't understand.

**Where it went:**
→ **Phase 15: Self-Healing & Runtime Optimization** (see `../15-self-healing-dynamic-scripting/15-CONTEXT.md`)

---

### Version 2.0 (2026-02-19): Codebase Knowledge Graph

**New scope:**
- Every file/class/function as a graph node in Neo4j
- Dual indexing: explicit relationships (imports, calls) + semantic similarity (vectors)
- Planning docs as central hubs (the "why" behind every piece of code)
- Automatic graph updates (git hook + daemon + LLM enrichment)
- Similarity detection for refactoring opportunities
- Query interface for LLMs to find context without massive token consumption

**Why this is foundational:**
- **Phase 15 needs this** - can't optimize without understanding structure
- **Eliminates token waste** - query graph instead of reading entire codebase
- **Enables intelligent decisions** - "what would break if I change X?"
- **Makes context visible** - Obsidian-style experience for code

**Dependency shift:**
```
OLD: Phase 1-13 → Phase 14 (optimization) → Phase 15 (self-healing)
NEW: Phase 1-13 → Phase 14 (knowledge graph) → Phase 15 (optimization + self-healing)
```

**Key insight from discussion:**
> "If we have the graph, optimization becomes intelligent. Without it, optimization is blind guessing."

---

## 🎯 Current Purpose

Build a **self-learning codebase knowledge graph** that makes all project context immediately visible, eliminating massive token consumption and enabling intelligent code optimization.

### What Gets Built

**Infrastructure:**
- Neo4j graph database with codebase entities
- Vector embeddings for semantic similarity
- Automatic update triggers (git hook + daemon)
- Query interface for LLMs

**Node Types:**
- `File` - Python source files, tests, planning docs, documentation
- `Module` - Python modules
- `Class` - Class definitions
- `Function` - Function definitions
- `PlanningDoc` - Phases, plans, requirements (CENTRAL NODES)

**Relationship Types:**
- `IMPORTS` - explicit import statements
- `CALLS` - function calls
- `INHERITS` - class inheritance
- `TESTS` - test coverage
- `IMPLEMENTS` - code implements planning doc
- `SIMILAR_TO` - semantic similarity (vector-based)

---

## 🔑 Key Decisions

### 1. Trigger Mechanism: Hybrid 4-Layer
- **Git pre-commit hook** (primary) - 95% of changes
- **LLM instructions** (enrichment) - captures intent for AI-generated code
- **Periodic daemon** (fallback) - catches missed changes, repairs drift
- **Manual trigger** (debug) - force rescan when needed

### 2. Similarity-Based Refactoring Tiers

| Similarity | Action |
|------------|--------|
| 95-100% | Delete duplicate (DRY violation) |
| 80-95% | Extract shared logic + parameterize differences |
| 60-80% | Extract utilities + interface (Template/Strategy pattern) |
| <60% | Share low-level utilities only |

**Example (84% similar):**
```python
# BEFORE: Two files, 84% duplicated
def parse_colors_shopify(text):
    colors = extract_keywords(text)  # 84% shared
    return normalize_to_english(colors)  # 16% different

def parse_colors_vendor(text):
    colors = extract_keywords(text)  # 84% DUPLICATE
    return normalize_to_german(colors)  # 16% different

# AFTER: One function, parameterized
def parse_colors(text, language='english'):
    colors = extract_keywords(text)  # 84% extracted ONCE
    return normalize_to_german(colors) if language == 'german' else normalize_to_english(colors)
```

### 3. Vector Strategy: Hierarchical Summaries

**User's keyboard analogy:**
> "I can see letters, numbers, special characters, Fn keys separately. I don't need to zoom into each key."

**Applied:**
- Embed file summaries (docstring + exports) - NOT full 500-line content
- Embed function summaries (signature + docstring) - NOT implementations
- Store in Neo4j vector index (integrated with graph)

### 4. Planning Docs as Central Hubs

**Auto-linking at commit:**
```bash
# Commit: "feat(13.2-03): add graph oracle adapter"
# Auto-links: src/assistant/governance/graph_oracle_adapter.py → Phase 13.2 Plan 03
```

**Natural references:**
```python
# Code: src/core/graphiti_client.py
"""
Graph client singleton.
Related to Phase 13.2-01: Neo4j runtime + graph client
"""
# Auto-detected and linked when scanned
```

### 5. More Files + Less Code = Faster

**Philosophy shift:**
- OLD: "More files = larger codebase"
- NEW: "More files + less code = cleaner, faster, better organized"

**Example:**
- Before refactoring: 2 files, 400 lines
- After refactoring: 3 files (base + 2 strategies), 200 lines
- Result: +1 file, -50% code, faster comprehension

---

## 🎨 The Vision in Practice

### Before Phase 14: Token-Heavy Context Gathering

```
LLM: "What files are related to enrichment?"
→ Read src/tasks/enrichment.py (200 lines)
→ Read src/assistant/governance/verification_oracle.py (150 lines)
→ Read src/core/enrichment/ (5 files, 800 lines)
→ Read tests/integration/test_enrichment*.py (400 lines)
→ Total: 1,550 lines read, ~30,000 tokens consumed

Answer: "These 9 files are related to enrichment."
```

### After Phase 14: Graph-Powered Context

```
LLM: "What files are related to enrichment?"
→ Query graph:
   MATCH (f:File)-[:IMPLEMENTS|CALLS|TESTS*1..2]-(enrichment:File)
   WHERE enrichment.path CONTAINS 'enrichment'
   RETURN f.path, f.purpose

Answer: "These 9 files are related to enrichment."
Tokens consumed: ~500 (graph query + results)

Reduction: 98% fewer tokens
```

### Similarity Detection in Action

```
# Phase 14 detects:
similarity_clusters = [
    {
        'files': ['src/utils/color_helper.py', 'src/utils/color_utils.py'],
        'similarity': 0.87,
        'shared_logic': 'extract_color_keywords() - 87%',
        'variant_logic': 'normalize_to_english() vs normalize_to_german() - 13%',
        'recommendation': 'Extract + parameterize',
        'estimated_savings': '150 lines of duplicated code'
    }
]

# Phase 15 executes:
# → Generates refactoring plan
# → Sandbox tests
# → Auto-applies if all gates pass
# → Updates graph linkage
```

---

## 📋 Implementation Plan

**8 plans across 4 waves** (see `14-CONTEXT.md` for details):

### Wave 1: Foundation
- **14-01**: Extend Neo4j schema (File, Module, Class, Function, PlanningDoc nodes)
- **14-02**: Vector embedding pipeline (hierarchical summaries)

### Wave 2: Initial Population
- **14-03**: Full codebase scanner + manual sync command
- **14-04**: Planning docs as central nodes (auto-linking)

### Wave 3: Automatic Updates
- **14-05**: Git pre-commit hook integration
- **14-06**: Periodic consistency daemon

### Wave 4: AI Enrichment
- **14-07**: LLM instruction framework (intent capture)
- **14-08**: Query interface for LLMs (templates + natural language)

---

## 🔗 Integration with Other Phases

### Consumes from Phase 13.2 (Oracle Framework)
- Neo4j infrastructure already set up
- Episode emission patterns established
- Fail-open behavior proven

### Enables Phase 15 (Self-Healing + Optimization)
- Phase 15 queries Phase 14's graph for impact analysis
- Example: "What would break if I optimize this cache?"
  ```cypher
  MATCH (cache:File {path: 'src/core/cache.py'})<-[:IMPORTS*1..3]-(dependent)
  RETURN dependent.path, length(path) as depth
  ```
- Correlation: Structural changes (Phase 14) + runtime failures (Phase 13.2) = root cause detection

---

## 🎯 Success Criteria

When Phase 14 is complete, these must be TRUE:

1. ✅ Every file in codebase is a node in the graph
2. ✅ Relationships captured: imports, calls, references, tests, planning docs
3. ✅ Semantic similarity works (vector search finds related code)
4. ✅ Planning docs are central hubs (most-referenced nodes)
5. ✅ Graph updates automatically (git hook + daemon operational)
6. ✅ LLMs can query efficiently (<100ms templates, <2s natural language)
7. ✅ Similarity detection accurate (correctly identifies refactoring candidates)
8. ✅ Context visible without token cost (10x reduction in tokens needed)

---

## 📖 For Future Reference

### Version 1.0 Content (Runtime Optimization)

**Preserved for historical context** - this vision moved to Phase 15:

<details>
<summary>Click to expand original vision (2026-02-08)</summary>

**Capabilities moved to Phase 15:**
- 🤖 Autonomous agents fix common issues
- 📊 ML learns from user behavior
- ⚡ Hot paths get faster automatically
- 💰 Costs decrease over time
- 🔮 Predicts what user needs next
- 🧪 A/B tests optimizations
- 🔧 Self-healing when things break

**Success metrics (Phase 15):**
```
Week 1 → Week 12:
- Vendor discovery: 2800ms → 150ms (18x faster)
- Success rate: 85% → 92% (+7%)
- Cost per product: $0.15 → $0.06 (60% less)
- Self-healed issues: 0% → 95%
```

**Technologies (Phase 15):**
- ML: Scikit-learn, TensorFlow
- Monitoring: OpenTelemetry, Prometheus, Grafana
- Agents: Celery Beat, custom framework
- Experimentation: A/B testing, feature flags

</details>

---

## 🚀 Next Steps

**Ready to plan:**
```bash
/gsd:plan-phase 14
```

**Or research first:**
```bash
/gsd:research-phase 14
```

**Key questions for planning:**
- Neo4j vector index setup and performance
- Cypher query patterns for common use cases
- Git hook implementation without slowing commits
- Daemon scheduling strategy (hourly vs daily)
- LLM prompt engineering for Cypher generation

---

## 💡 Meta-Lesson

**This README itself demonstrates Phase 14's value:**
- **One file** - but two versions documented
- **Clear evolution** - from V1.0 (optimization) to V2.0 (knowledge graph)
- **Preserved history** - original vision not lost, just moved
- **Explains why** - architectural decision rationale captured

**Imagine this for every file in the codebase:**
```cypher
// Query: "How did src/core/cache.py evolve?"
MATCH (f:File {path: 'src/core/cache.py'})-[:MODIFIED_IN]->(commits:Commit)
RETURN commits.hash, commits.message, commits.timestamp
ORDER BY commits.timestamp DESC
```

**That's Phase 14.** 🎯

---

*Phase: 14-continuous-optimization-learning*
*Version: 2.0*
*Updated: 2026-02-19*
*Next: Planning → Execution*
