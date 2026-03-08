# Analyst Review: Gemini Deep Research — Runtime Digital Twin
**Date:** 2026-03-08
**Analyst:** Lead Forensic Investigator (agent-745c61ec)
**Source doc:** `docs/graph/research-input.md`
**Project:** Vektal — Shopify Multi-Supplier Platform (Phase 17+)

---

## Overall Verdict

The structural half is excellent and immediately buildable.
The operational half describes the wrong infrastructure for this project.

The document is a high-quality generic blueprint that needs a specific
compatibility pass before implementation. The core mistake: it proposes
building an operational telemetry layer that already exists in a different
form (Graphiti), and it assumes a database engine (FalkorDB) that is not
what this project runs on (Neo4j Aura).

---

## What to Take Directly — Phase 1 is Solid

### Three-Layer Schema Decomposition
Structural / Operational / Environmental is the right architecture.
Clean separation, each layer implementable independently.

### Decorator Extraction Table
Concrete and directly implementable against the existing `sync_to_neo4j.py`:

| Decorator | AST target | Graph output |
|---|---|---|
| `@app.route` | `decorator_list[i].args` | `url_template` property on Function |
| `@app.route` | `keywords['methods']` | `allowed_methods` property |
| `@app.task` | `keywords['queue']` | `ROUTES_TO` → `:Queue` node |
| `@app.task` | `keywords['priority']` | `task_priority` property |

This is a PR against `sync_to_neo4j.py`, not a research project.

### Risk Tier Taxonomy
Maps directly onto this project's `.env` structure:

| Tier | Definition | Examples in this project |
|---|---|---|
| 1 — Vital | Full outage or security breach | `NEO4J_PASSWORD`, `AURA_CLIENT_SECRET`, `SHOPIFY_API_KEY` |
| 2 — Operational | Specific pipeline failure | `CELERY_BROKER_URL`, `REDIS_URI`, `GRAPH_ORACLE_ENABLED` |
| 3 — Functional | Degraded performance | `SCRAPE_TIMEOUT`, `RETRY_COUNT`, `LOG_LEVEL` |
| 4 — Contextual | Logging / metadata only | `ENVIRONMENT_NAME`, `DEPLOYMENT_ID` |

### Bi-Temporal Versioning
The most sophisticated contribution — and one not previously flagged.
Instead of `DETACH DELETE` on every re-sync, set `EndDate` on stale nodes
and add a `:Deleted` label. This enables time-travel queries:

> "What did the call graph look like before the last deploy?"

The `CALL {} IN TRANSACTIONS` batching (10k rows) to avoid Java heap errors
on Aura is also correct and important to implement.

### Queries Implementable Now (no OTEL required)
- **Q3** — Orphaned EnvVars (static graph only)
- **Q4** — Sentry grounding (Sentry already integrated via `sentry_issue_puller.py`)
- **Q5** — God Function detection by in-degree
- **Q10** — Idempotent task retry logic (needs `is_idempotent` property on Function nodes)

---

## What to Discard or Correct

### FalkorDB References — Ignore Entirely
The document repeatedly uses FalkorDB's sparse adjacency matrix mathematics
as the performance rationale. This project runs on **Neo4j Aura**. FalkorDB
is a Redis-based graph engine (RedisGraph lineage) with a completely different
storage model. The `GRAPH.QUERY` syntax and matrix traversal claims do not
apply. The AST extraction *patterns* transfer fine — the engine-specific
implementation details do not. Treat every FalkorDB mention as
"Neo4j Cypher equivalent."

### Query 6 — Wrong Queue Names
References `within_5_seconds` and `within_5_hours` — generic Shopify scraping
queue names. This project uses: `assistant.t1`, `assistant.t2`, `assistant.t3`,
`scrape`, `ingest`. Rewrite accordingly.

### Query 3 — Syntax Bug
The Cypher clause `AND e.risk_tier IN` is missing its list value.
Broken as written — will fail on execution.

### Queries 1, 2, 7, 8, 9 — Deferred (OTEL Prerequisite)
All five require `:Span` nodes populated via OpenTelemetry instrumentation.
This project does not currently have OTEL instrumentation. These queries are
architecturally correct but will return zero results until Phase 2 (OTEL) is
implemented. Do not prioritise these in the immediate roadmap.

---

## The Critical Gap: Graphiti IS the Operational Layer

This is the most significant miss in the document.

The document proposes adding an "Operational Layer" of `:Span`, `:Trace`,
`:Issue`, `:Metric` nodes via OTEL instrumentation — to bridge static code
to runtime behaviour.

**This layer already exists. It is Graphiti.**

Right now, live temporal episodes are being written to Aura:
- `CODE_INTENT` — LLM-generated code rationale
- `FAILURE_PATTERN` — runtime error signatures from `FAILURE_JOURNEY.md`
- `BUG_ROOT_CAUSE_IDENTIFIED` — diagnosed failure root causes
- `ORACLE_DECISION` — T2/T3 governance decisions
- `QUERY_REASONING_TRACE` — every graph query issued by the Analyst
- `ENRICHMENT_OUTCOME` — product enrichment results
- `CONVENTION_ESTABLISHED` — architectural conventions

These are the runtime signals the document proposes to instrument from scratch.
The actual work is not OTEL — it is a **bridge relationship** between the
static AST nodes and the existing Graphiti episode nodes.

### The Bridge Relationship (Phase 2)

```cypher
// What already exists in Aura (Graphiti layer)
(:Episode {type: 'FAILURE_PATTERN', module_path: 'src.tasks.graphiti_sync'})

// What needs to be added (the bridge — ~50 lines of code)
(:Function {full_name: 'src.tasks.graphiti_sync.emit_episode'})
  -[:HAS_EPISODE]->
(:Episode {type: 'FAILURE_PATTERN'})

// Query that becomes possible immediately after:
MATCH (f:Function)-[:CALLS*1..3]->(target:Function)
MATCH (target)-[:HAS_EPISODE]->(e:Episode {type: 'FAILURE_PATTERN'})
WHERE e.timestamp > datetime() - duration({days: 30})
RETURN f.full_name, target.full_name, count(e) AS failure_count
ORDER BY failure_count DESC
```

> "Which call paths lead to functions with active failure patterns
> in the last 30 days?"

This query is more valuable for this project than any OTEL span query.
It is achievable now, without new instrumentation — just a join between
two existing graph layers that have never been connected.

### The Sentry Layer Also Already Exists
`scripts/observability/sentry_issue_puller.py` already pulls Sentry issues.
`:Issue` nodes can be populated from that data today without waiting for OTEL.

---

## Multi-Tenancy Gap — Still Absent

The document has no concept of tenancy. This is an 8-vendor platform with
`store_id` isolation on every operation. Every relevant node should carry it:

```cypher
(:Function {name: 'emit_episode'})-[:SERVES_TENANT]->(:Vendor {store_id: 'bastelschachtel'})
```

Without this, blast radius analysis is platform-wide when it should be
per-vendor. A failure in vendor A's enrichment pipeline should not surface
as a risk to vendor B.

The Cypher queries in the Forensic Playbook all assume a single-tenant
architecture. Every query needs a `store_id` filter parameter to be
production-safe.

---

## Revised Implementation Roadmap

| Phase | What | Where | Source |
|---|---|---|---|
| **1a** | Full re-sync: Class, Function, PlanningDoc + DEFINES/CALLS | `sync_to_neo4j.py` | Already built, never fully run |
| **1b** | Decorator extraction: Flask routes + Celery queues → nodes | Extend `sync_to_neo4j.py` | Decorator table above |
| **1c** | EnvVar mapping: `os.getenv()` → `:EnvVar` + Risk Tiers | New AST visitor | Tier taxonomy above |
| **1d** | Bi-temporal versioning: replace `DETACH DELETE` with `EndDate/:Deleted` | Replace sync strategy | Document section 3 |
| **2a** | Graphiti bridge: `(:Function)-[:HAS_EPISODE]->(:Episode)` | New relationship + sync | ~50 lines, high ROI |
| **2b** | Sentry bridge: `:Issue` nodes from `sentry_issue_puller.py` | Extend sync | Already collected |
| **2c** | Multi-tenancy: `store_id` on all operational nodes | Schema + sync | Gap not in document |
| **3** | OTEL instrumentation → `:Span`/`:Trace` nodes | New infra layer | Phase 2 prerequisite |
| **4** | GraphRAG + LLM reasoning loop | Query layer | Phase 3 prerequisite |

The document gives a precise, correct Phase 1.
**Phase 2 is Graphiti bridging, not OTEL.** That is the reorder that matters.

---

## For the Next Research Iteration

Feed Gemini:
1. This analysis document (the compatibility gaps and corrections)
2. The original research prompt output (`research-input.md`)
3. The following project-specific constraints:

**Hard constraints for Gemini to respect:**
- Database: Neo4j Aura (not FalkorDB — discard all FalkorDB-specific syntax)
- Existing telemetry layer: Graphiti temporal KG (episodes already in Aura)
- Existing Sentry integration: `scripts/observability/sentry_issue_puller.py`
- Queue names: `assistant.t1`, `assistant.t2`, `assistant.t3`, `scrape`, `ingest`
- Multi-tenancy: every operational node needs `store_id` (8 vendors, 4000+ SKUs)
- No OTEL yet: Phase 2 = Graphiti bridge, Phase 3 = OTEL
- `sync_to_neo4j.py` is the sync entry point — all schema changes extend it

**The most important question for the next iteration:**
> "How should the static AST layer (File, Class, Function nodes) be joined
> to the existing Graphiti temporal episode layer in the same Neo4j Aura
> instance? What node labels, relationship types, and shared properties
> should create the bridge? Design the Cypher schema and 5 forensic
> queries that traverse both layers."
