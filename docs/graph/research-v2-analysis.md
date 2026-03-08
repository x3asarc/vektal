# Analyst Review: Gemini Research v2 — Vektal Knowledge Graph Implementation Spec
**Date:** 2026-03-08
**Analyst:** Lead Forensic Investigator (agent-745c61ec)
**Source doc:** `docs/graph/research-input-v2.md`
**Previous analysis:** `docs/graph/gemini-deep-research-analysis.md`
**Status:** BASIS FOR PLANNING AND IMPLEMENTATION

---

## Critical Architectural Distinction — Read This First

Before any implementation work begins, this distinction must be hardwired into
every decision made about the Knowledge Graph.

### There Are Two Separate Knowledge Graphs

**Graph 1 — The Developer KG (what we are building now)**

Purpose: Domain mastery of the codebase itself.
> "What exists in our software, what affects what, what breaks if we change X,
> what phase introduced it, what governs it, what is connected to what."

Consumers: Developers, the Forensic Investigator agent, CI/CD pipelines.
Node subjects: Code — `Function`, `Class`, `Module`, `APIRoute`, `EnvVar`, `Table`.
Questions answered: Structural, architectural, dependency, blast-radius.

**Graph 2 — The Operational/User-Facing KG (does not exist yet)**

Purpose: Domain mastery of what the platform does for vendors at runtime.
> "What enrichment ran, what oracle decided, what supplier failed,
> what store is affected, what vendor experienced what outcome."

Consumers: Self-healing systems, operators, eventually end-users.
Node subjects: Business events — `EnrichmentOutcome`, `VendorCatalogChange`,
`OracleDecision`, `StoreHealth`.
Questions answered: Operational, business-domain, per-tenant, runtime.

**These two graphs share the same Neo4j Aura instance but are architecturally
separate. Do not mix their schemas. Do not bridge them until Graph 2 is
explicitly designed as its own project.**

---

### Graphiti Episode Classification

Graphiti is already writing episodes to Aura. They split cleanly across
the two graph boundaries:

| Episode Type | Belongs To | Reason |
|---|---|---|
| `CODE_INTENT` | Developer KG | About why code was written |
| `BUG_ROOT_CAUSE_IDENTIFIED` | Developer KG | About code defects |
| `CONVENTION_ESTABLISHED` | Developer KG | About coding decisions |
| `GRAPH_DISCREPANCY` | Developer KG | About the graph itself |
| `QUERY_REASONING_TRACE` | Developer KG | Tool-level trace |
| `ENRICHMENT_OUTCOME` | User-facing KG | Vendor product data quality |
| `ORACLE_DECISION` | User-facing KG | Platform decisions for a store |
| `VENDOR_CATALOG_CHANGE` | User-facing KG | Supplier inventory events |
| `USER_APPROVAL` | User-facing KG | User-triggered approval actions |
| `FAILURE_PATTERN` | Ambiguous | Runtime errors about code but |
| | | triggered by platform operations |

**The bridge from Graphiti to the Developer KG connects ONLY:**
- `CODE_INTENT` → `(:Function)` or `(:Module)`
- `BUG_ROOT_CAUSE_IDENTIFIED` → `(:Function)`
- `CONVENTION_ESTABLISHED` → `(:Module)`

`ENRICHMENT_OUTCOME`, `ORACLE_DECISION`, `VENDOR_CATALOG_CHANGE`,
`USER_APPROVAL` — these episodes exist in Aura but are untouched until
Graph 2 is designed. They are not part of this implementation.

---

## What v2 Got Right — Validated and Implementable

### 1. Graphiti-Static Bridge Design

The `:REFERS_TO` relationship is the correct bridge pattern:

```cypher
(:Episode {type: 'CODE_INTENT'})-[:REFERS_TO]->(:Function {function_signature: $sig})
(:Episode {type: 'BUG_ROOT_CAUSE_IDENTIFIED'})-[:REFERS_TO]->(:Function)
(:Episode {type: 'CONVENTION_ESTABLISHED'})-[:REFERS_TO]->(:Module)
```

`function_signature` as the shared key between the two layers is correct.
Format: `{module_path}.{class_name}.{function_name}` or
`{module_path}.{function_name}` for module-level functions.

**Pre-condition:** Before the bridge can be wired, episode emission sites
across the codebase must be updated to consistently include
`function_signature` in every relevant payload. Currently only
`FAILURE_PATTERN` episodes reliably include `module_path`.
This is a required pre-condition that must be completed before Step 6
in the implementation sequence below.

### 2. Bi-Temporal Versioning (SCD Type 2)

Replace the current `DETACH DELETE` full re-sync with versioned nodes.
Every static code node gets `StartDate` and `EndDate` properties.

**Current state:** Active node
```
StartDate: <deploy_timestamp>
EndDate: null  (or 9999-12-31 as sentinel)
```

**On code change:** Close old version, create new
```cypher
// Close old version
MATCH (f:Function {function_signature: $sig})
WHERE f.EndDate IS NULL
SET f.EndDate = $now

// Insert new version
CREATE (f_new:Function {
  function_signature: $sig,
  StartDate: $now,
  EndDate: null,
  checksum: $new_hash
  // ... all other properties
})
```

**On deletion:** Mark as deleted, never remove
```cypher
MATCH (f:Function {function_signature: $sig})
WHERE f.EndDate IS NULL
SET f.EndDate = $now
SET f:Deleted
```

**Always filter current-state queries:**
```cypher
MATCH (f:Function) WHERE f.EndDate IS NULL ...
```

Use `CALL { ... } IN TRANSACTIONS OF 10000 ROWS` for all batch
update/delete operations to avoid Aura heap errors.

### 3. AST Decorator Extraction

Correct and Vektal-specific queue names confirmed:

| Decorator | AST Target | Graph Output |
|---|---|---|
| `@app.route` | `args[0]` (ast.Constant) | `:APIRoute.url_template` |
| `@app.route` | `keywords['methods']` (ast.List) | `:APIRoute.http_methods` |
| `@app.task` | `keywords['queue']` (ast.Constant) | `:CeleryTask.queue` |
| `@app.task` | `keywords['priority']` (ast.Constant) | `:CeleryTask.priority` |

Valid queue values: `assistant.t1`, `assistant.t2`, `assistant.t3`,
`scrape`, `ingest`. Reject any other value as a misconfiguration flag.

Relationships:
```cypher
(:APIRoute)-[:TRIGGERS]->(:Function)
(:Function)-[:ROUTES_TO]->(:CeleryTask)-[:QUEUED_ON]->(:Queue)
```

### 4. Environment Variable Mapping

```cypher
(:Function)-[:DEPENDS_ON_CONFIG]->(:EnvVar {name: 'GRAPH_ORACLE_ENABLED', risk_tier: 2})
```

Risk tier taxonomy for this project:

| Tier | Definition | Project examples |
|---|---|---|
| 1 — Vital | Full outage or breach | `NEO4J_PASSWORD`, `AURA_CLIENT_SECRET` |
| 2 — Operational | Pipeline failure | `CELERY_BROKER_URL`, `GRAPH_ORACLE_ENABLED` |
| 3 — Functional | Degraded performance | `SCRAPE_TIMEOUT`, `RETRY_COUNT` |
| 4 — Contextual | Logging / metadata | `ENVIRONMENT_NAME`, `DEPLOYMENT_ID` |

**SECURITY CONSTRAINT:** `:EnvVar` nodes store the variable **name only**.
Never store the actual credential value in the graph. The query layer
resolves values at runtime from the environment.

### 5. Sentry-to-Graph Grounding

`sentry_issue_puller.py` already collects Sentry issues. Extend it to
write `:SentryIssue` nodes and wire them to static `:Function` nodes.

Mapping logic: `abs_path` from Sentry stack frame → normalized
`module_path` in static graph, `lineno` within function's line range.

Temporal filter — link issue to the function version active at error time:
```cypher
MATCH (f:Function {function_signature: $sig})
WHERE f.StartDate <= $issue_timestamp < f.EndDate
  OR (f.StartDate <= $issue_timestamp AND f.EndDate IS NULL)
```

Relationships:
```cypher
(:SentryIssue)-[:OCCURRED_IN]->(:Function)
(:SentryIssue)-[:REPORTED_IN]->(:Module)
```

### 6. SQLAlchemy → Graph Mapping

| SQL Source | Graph Node/Relationship | Notes |
|---|---|---|
| Entity table | `:Table {name, schema_version}` | One node per table |
| Foreign key | `-[:REFERENCES]->` | Direction = business semantics |
| Junction table | Relationship property | `access_level` on edge, not a node |
| `session.query(X)` in AST | `(:Function)-[:ACCESSES]->(:Table)` | AST visitor on ORM calls |

---

## Issues to Correct Before Implementation

### Issue 1 — `store_id` on Static Function Nodes (INCORRECT)

The v2 document adds `store_id` to `:Function` nodes. This is wrong.

Functions are **shared code**. `emit_episode()` serves all 8 vendors.
It does not belong to any single store. Adding `store_id` to static
nodes implies per-tenant code variants which is not how this codebase works.

**Correct model:**
- Static nodes (`Function`, `Class`, `Module`, `APIRoute`, `EnvVar`, `Table`):
  No `store_id`. These are global, shared across all tenants.
- Dynamic nodes (`Episode`, `SentryIssue`): Carry `store_id`.
  Multi-tenancy is enforced at the episode/issue traversal layer.

The `(:Store)-[:CONTEXT_FOR]->(:Function)` relationship from the v2
diagram is removed. Replace with:
```cypher
(:Store)-[:CONTEXT_FOR]->(:Episode)
(:Store)-[:CONTEXT_FOR]->(:SentryIssue)
```

### Issue 2 — Query 1 References `backup.value` (SECURITY RISK)

Query 1 returns `backup.value AS fallback_config`. The `EnvVar` node
stores the variable name only, not its value. Fix:

```cypher
// WRONG
RETURN f.function_signature, backup.value AS fallback_config

// CORRECT
RETURN f.function_signature, backup.name AS fallback_env_var_name
// Caller resolves the actual value from os.getenv() at runtime
```

### Issue 3 — Query 5 Exact Timestamp Match (FRAGILE)

```cypher
// WRONG — exact equality will fail in practice
WHERE f_old.EndDate = f_fail.StartDate

// CORRECT — overlap check
WHERE f_old.EndDate <= f_fail.StartDate
  AND f_old.StartDate < f_fail.StartDate
```

### Issue 4 — Bridge Pre-Condition Not in v2

The bridge `(:Episode)-[:REFERS_TO]->(:Function)` requires that episode
payloads contain `function_signature`. This is not currently the case for
most episode types. This must be implemented before the bridge sync step.

Files to update: every call site of `emit_episode.delay()` for
`CODE_INTENT`, `BUG_ROOT_CAUSE_IDENTIFIED`, `CONVENTION_ESTABLISHED`
episodes — add `function_signature` to their payload dict.

---

## Corrected Unified LPG Schema

### Node Types

```
STATIC CODE DOMAIN (developer KG — global, no store_id)
  :File             path, language, purpose, embedding, checksum,
                    StartDate, EndDate
  :Module           module_path, package_name, StartDate, EndDate
  :Class            full_name, name, base_classes, StartDate, EndDate
  :Function         full_name, function_signature, name, signature,
                    lineno, is_async, is_method, is_idempotent,
                    StartDate, EndDate
  :PlanningDoc      path, title, doc_type, phase_number
  :APIRoute         url_template, http_methods, blueprint
  :CeleryTask       queue, priority, max_retries, task_name
  :Queue            name, broker
  :EnvVar           name, risk_tier, has_default
  :Table            name, schema_version

GRAPHITI EPISODE DOMAIN (developer-facing subset only)
  :Episode          episode_id, type, content, timestamp,
                    function_signature  ← required for bridge
  (types in scope: CODE_INTENT, BUG_ROOT_CAUSE_IDENTIFIED,
                   CONVENTION_ESTABLISHED, GRAPH_DISCREPANCY,
                   QUERY_REASONING_TRACE)

OBSERVABILITY DOMAIN
  :SentryIssue      issue_id, exception_type, message, timestamp,
                    store_id, resolved
```

### Relationship Types

```
STATIC LAYER
  (File)-[:IMPORTS]->(File)
  (Module)-[:CONTAINS]->(Function)
  (Module)-[:CONTAINS]->(Class)
  (File)-[:DEFINES_FUNCTION]->(Function)
  (File)-[:DEFINES_CLASS]->(Class)
  (Function)-[:CALLS]->(Function)
  (APIRoute)-[:TRIGGERS]->(Function)
  (Function)-[:ROUTES_TO]->(CeleryTask)
  (CeleryTask)-[:QUEUED_ON]->(Queue)
  (Function)-[:DEPENDS_ON_CONFIG]->(EnvVar)
  (Function)-[:ACCESSES]->(Table)
  (Table)-[:REFERENCES]->(Table)
  (File)-[:INTRODUCED_IN]->(PlanningDoc)

BRIDGE LAYER (developer KG ↔ Graphiti)
  (Episode)-[:REFERS_TO]->(Function)
  (Episode)-[:REFERS_TO]->(Module)

OBSERVABILITY LAYER
  (SentryIssue)-[:OCCURRED_IN]->(Function)
  (SentryIssue)-[:REPORTED_IN]->(Module)
```

---

## Corrected Forensic Playbook

All 5 queries from v2, corrected for the issues above.

### Q1 — Fallback Config Discovery (corrected: no `.value`)

```cypher
// A function is failing due to primary proxy. Find the backup EnvVar name.
MATCH (f:Function)-[:DEPENDS_ON_CONFIG]->(primary:EnvVar {name: 'PROX_PRIMARY'})
MATCH (f)-[:DEPENDS_ON_CONFIG]->(backup:EnvVar {name: 'PROX_BACKUP'})
MATCH (e:Episode {type: 'BUG_ROOT_CAUSE_IDENTIFIED'})-[:REFERS_TO]->(f)
WHERE f.EndDate IS NULL
RETURN f.function_signature,
       backup.name AS fallback_env_var,
       e.timestamp
ORDER BY e.timestamp DESC
LIMIT 5
```

### Q2 — Blast Radius of a Table/Schema Change

```cypher
// Which functions and API routes access the 'orders' table?
MATCH (t:Table {name: 'orders'})<-[:ACCESSES]-(f:Function)
WHERE f.EndDate IS NULL
OPTIONAL MATCH (api:APIRoute)-[:TRIGGERS]->(f)
OPTIONAL MATCH (task:CeleryTask {queue: 'assistant.t1'})-[:ROUTES_TO]->(f)
RETURN f.function_signature,
       collect(DISTINCT api.url_template) AS affected_routes,
       collect(DISTINCT task.queue) AS urgent_queues
```

### Q3 — Sentry Issue Correlated with Recent Code Intent

```cypher
// Was there a CODE_INTENT episode recorded for a function before it started failing?
MATCH (si:SentryIssue)-[:OCCURRED_IN]->(f:Function)
MATCH (e:Episode {type: 'CODE_INTENT'})-[:REFERS_TO]->(f)
WHERE e.timestamp < si.timestamp
  AND duration.between(e.timestamp, si.timestamp).days <= 7
RETURN si.issue_id, si.exception_type,
       e.content AS original_intent,
       e.timestamp AS intent_recorded,
       si.timestamp AS issue_raised
ORDER BY si.timestamp DESC
```

### Q4 — God Function Detection (high blast radius candidates)

```cypher
// Functions with the most inbound dependencies — single points of failure
MATCH (f:Function)
WHERE f.EndDate IS NULL
WITH f,
     size((f)<-[:CALLS]-()) AS call_in,
     size((f)<-[:TRIGGERS]-(:APIRoute)) AS api_in,
     size((f)-[:DEPENDS_ON_CONFIG]->()) AS config_deps
WHERE (call_in + api_in) > 5
RETURN f.function_signature,
       call_in,
       api_in,
       config_deps,
       (call_in + api_in) AS blast_score
ORDER BY blast_score DESC
LIMIT 20
```

### Q5 — Code Evolution During Instability (corrected timestamp logic)

```cypher
// Find the last stable version of a failing function + its original design intent
MATCH (f_fail:Function {function_signature: $sig})
WHERE f_fail.EndDate IS NULL
MATCH (f_old:Function {function_signature: $sig})
WHERE f_old.EndDate <= f_fail.StartDate
  AND f_old.StartDate < f_fail.StartDate
OPTIONAL MATCH (e:Episode {type: 'CODE_INTENT'})-[:REFERS_TO]->(f_old)
RETURN f_old.StartDate AS version_introduced,
       f_old.EndDate AS version_retired,
       f_old.checksum AS old_checksum,
       e.content AS original_design_intent
ORDER BY f_old.StartDate DESC
LIMIT 1
```

---

## Implementation Sequence

Dependencies respected — no step assumes a capability from a later step.

| Step | What | Touches |
|---|---|---|
| **1** | Run full `sync_to_neo4j.py` — Class, Function, PlanningDoc, CALLS edges | `sync_to_neo4j.py` |
| **2** | Add `:APIRoute` + `:CeleryTask` via decorator AST extraction | Extend scanner |
| **3** | Add `:EnvVar` + `DEPENDS_ON_CONFIG` via `os.getenv` AST visitor | New visitor |
| **4** | Add `:Table` + `ACCESSES` from SQLAlchemy model analysis | New mapper |
| **5** | Replace `DETACH DELETE` with bi-temporal SCD Type 2 versioning | Replace sync core |
| **6** | Update `CODE_INTENT`, `BUG_ROOT_CAUSE_IDENTIFIED`, `CONVENTION_ESTABLISHED` episode emission to include `function_signature` in payload | `src/tasks/graphiti_sync.py` + emit sites |
| **7** | Wire `(Episode)-[:REFERS_TO]->(Function)` bridge in sync | New sync step |
| **8** | Extend `sentry_issue_puller.py` to write `(:SentryIssue)-[:OCCURRED_IN]->(:Function)` | `scripts/observability/` |
| **9** | Add composite indexes for query performance | Schema migration |
| **10** | Validate with the 5 Forensic Playbook queries against live Aura | Verification |

Steps 1–5: Pure static graph. No dependencies on Graphiti or Sentry.
Steps 6–7: Graphiti bridge. Requires Step 5 (versioning) to be complete.
Steps 8: Sentry bridge. Can run in parallel with 6–7.
Steps 9–10: Operational. Requires all prior steps.

---

## What Is Explicitly Out of Scope

The following are deferred to the future user-facing operational KG project:

- `store_id` on static code nodes
- `ENRICHMENT_OUTCOME` episodes in any graph bridge
- `ORACLE_DECISION` episodes (product/vendor decisions)
- `VENDOR_CATALOG_CHANGE` episodes
- `USER_APPROVAL` episodes
- `(:Store)` nodes and `CONTEXT_FOR` relationships
- Per-vendor blast radius (operational KG concern)
- Any query involving vendor performance, supplier health, or SKU data

When the operational KG is designed, it will be a separate graph layer
that may reference the developer KG's static nodes by `function_signature`
but will not modify or extend the developer KG schema.
