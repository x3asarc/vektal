# Tool Calling 2.0 Integration Plan
## How Anthropic's 2026 Agent Patterns Map to Synthex + Neo4j + Graphiti

**Source:** YouTube — "Anthropic killed Tool calling" (AI Jason, 2026-02)
**Status:** Architecture reference — integration mapped across Phase 13.2, 14, and 15
**Branch:** `claude/agentic-rag-knowledge-graph-7gW6p`

---

## The Core Insight and Why It Matters Here

The video identifies five shifts in how agents should interact with tools:

| Old Pattern | New Pattern | Synthex Impact |
|---|---|---|
| JSON tool output → model extracts params → next JSON call | Code execution handles the loop | Tier 3 delegation becomes programmatic, not round-trip |
| Load all tool schemas upfront | Tool Search: fetch schema on demand | Assistant tool registry already in DB — add search layer |
| Full HTML/JSON floods context window | Filter/extract before it enters context | Vendor scraper and graph ingestion both benefit |
| Bare tool descriptions | `input_examples` field in schema | Graph stores examples alongside tool entity nodes |
| Always-loaded MCP tools | `deferred_loading: true` | Tier 1/2/3 tool projection already tier-scoped — extend to lazy |

This document maps each concept to a specific location in the codebase and assigns
it to the right phase. Nothing here contradicts the Phase 13.2 plan already written.
Everything here either supplements 13.2, feeds into 14, or feeds into 15.

---

## Concept 1 — Programmatic Tool Calling (Code Execution Loop)

### What the video says
Instead of: `Model → calls tool A → reads JSON output → calls tool B with extracted params`
Do: `Model → writes Python code that calls A, processes output, calls B in a loop → single round trip`

The Anthropic parameter is `code_execution_2026_01_20`. Token reduction: 30–50%.

### Where this lives in Synthex

**The problem already exists.** Look at Tier 3 delegation in `src/assistant/runtime_tier3.py`.
The current fan-out pattern is:
```
Tier 3 → delegates subtask 1 → waits → reads result → delegates subtask 2 → waits → reads result
```
Each delegation round-trip costs context. For the enrichment batch use case (8 vendors × N SKUs),
this is compounded.

**The Graphiti connection:** Episode ingestion in `src/tasks/graphiti_sync.py` (Phase 13.2-02)
is already fire-and-forget `.delay()`. But the _enrichment pipeline itself_ still runs
subtask-by-subtask. Once the graph is live, Phase 14 optimization agents will query it.
Those agents are the ones that benefit most from programmatic execution.

### Integration points

**Phase 13.2 — Apply NOW (small, safe):**

File: `src/tasks/graphiti_sync.py` (being created in 13.2-02)

When ingesting a batch of FAILURE_JOURNEY.md entries, do NOT call `ingest_episode.delay()`
per entry. Instead, use a Celery `group()` chord — one dispatch for the whole batch:

```python
# INSTEAD OF (old pattern — N individual Celery dispatches):
for entry in entries:
    ingest_episode.delay(entry)

# DO THIS (programmatic group — single dispatch, Celery handles fan-out):
from celery import group
ingest_group = group(ingest_episode.s(entry) for entry in entries)
result = ingest_group.delay()
```

This is the local equivalent of "programmatic tool calling" for Celery: the orchestrator
writes the execution plan, Celery executes it, instead of the model being the glue.

**Phase 14 — Full implementation:**

When Phase 14 optimization agents run, they should generate a `CeleryExecutionPlan` object
(a list of Celery task signatures) rather than issuing individual task dispatches.

New file: `src/assistant/execution_planner.py` (~150 LOC)
```python
class CeleryExecutionPlan:
    """Programmatic task graph — replaces per-task delegation round trips."""
    def add_task(self, task_sig: Signature, depends_on: list[str] | None = None) -> str
    def to_chord(self) -> Chord         # parallel tasks with callback
    def to_chain(self) -> Chain         # sequential tasks
    def to_group(self) -> Group         # pure parallel
    def estimate_cost(self) -> dict     # {"tasks": int, "estimated_tokens_saved": int}
```

The graph oracle (`graph_oracle_adapter.py`) would query Neo4j for the optimal execution
plan shape based on prior enrichment outcome episodes — "vendor X ran faster with chord,
vendor Y needed chain due to rate limits."

**Phase 15 — Self-healing use:**

Remediation plans are already Celery tasks. Phase 15 self-healing agents generate a
`CeleryExecutionPlan` for each remediation, query the graph for prior failure patterns
on target modules, and skip tasks that have `failure_warning` edges with `severity=critical`.

---

## Concept 2 — Context Window Optimization via Code-First Filtering

### What the video says
The `web_fetch_tool_2026_02_09` parameter adds a filtering layer: raw HTML enters a code
execution sandbox, relevant content is extracted, only the clean result enters the context.
Token savings: ~24% for web-heavy agents.

### Where this lives in Synthex

**The vendor scraper is the direct equivalent.** The `celery_scraper` worker fetches
raw vendor catalog HTML/JSON. Today, large raw payloads can leak into the assistant context
if the enrichment pipeline isn't careful.

There are two distinct surfaces:

#### Surface A — Vendor Scraper Preprocessing (immediate)

File: `src/jobs/` vendor adapters (scraper output path)

The scraper already produces structured `VendorCatalogItem` records. The risk is when
the raw vendor page content gets stored in any intermediate buffer that the assistant
can later retrieve. The fix is a preprocessing gate:

```python
# In src/jobs/graphiti_ingestor.py (being created in 13.2-02)
# Add a content_filter step BEFORE building any episode:

def _filter_vendor_payload(raw: dict) -> dict:
    """
    Keep only fields the graph needs. Never let raw HTML/full JSON into an episode.
    Episode bodies must be ≤2KB. This is the equivalent of web_fetch_tool filtering.
    """
    ALLOWED_KEYS = {"sku", "vendor_code", "sku_count_delta", "price_change_pct", "store_id", "job_id"}
    return {k: v for k, v in raw.items() if k in ALLOWED_KEYS}
```

Add to `build_vendor_episode()`: always pass raw through `_filter_vendor_payload()` first.
Target: episode body ≤2KB. Any larger is a sign raw data leaked through.

**Apply in Phase 13.2-02.** This is a 5-line addition to `graphiti_ingestor.py`.

#### Surface B — Assistant Context Window Guard (Phase 14)

The Tier 1/2/3 assistant runtimes build context from memory facts + retrieved episodes.
Phase 14 should add a `ContextWindowGuard` that:
1. Caps total context budget (tokens) before any LLM call
2. Prioritizes high-relevance episodes over low-relevance raw data
3. Strips fields from episodes that exceed the per-field byte limit

New file: `src/assistant/context_window_guard.py` (~120 LOC)
```python
class ContextWindowGuard:
    """Equivalent of web_fetch_tool_2026_02_09 for the assistant context."""
    def filter_episodes(self, episodes: list[dict], *, budget_tokens: int) -> list[dict]
    def filter_memory_facts(self, facts: list, *, budget_tokens: int) -> list
    def estimate_tokens(self, obj: dict | str) -> int   # tiktoken or char/4 heuristic
    def build_context_payload(self, episodes, facts, *, budget_tokens: int) -> dict
```

The `query_graph_evidence()` in `graph_oracle_adapter.py` already has a 2s timeout.
Phase 14 will additionally cap what fraction of the context budget graph evidence can consume.

---

## Concept 3 — Tool Search (Dynamic Schema Retrieval)

### What the video says
Instead of loading 50+ tool schemas at the start of every prompt (token-heavy), add a
"Tool Search" tool. The model calls it with a description of what it needs, gets back
only the relevant tool schema.

With `deferred_loading: true` in MCP config, all other tools are invisible until searched.

### Where this lives in Synthex

**This maps exactly to the existing `assistant_tool_registry` table.**

Phase 12 built the tool registry (`src/assistant/tool_registry.py`). It has tool names,
descriptions, tier-scope, and policy metadata already in PostgreSQL. But it loads the
full tier-scoped tool list into every prompt context.

The "Tool Search" concept says: put the tool registry in Neo4j as entity nodes, let the
assistant query the graph for the tool it needs by description similarity.

#### Phase 13.2 — Foundation (already planned, confirm the hook)

When `src/core/synthex_entities.py` defines entity types (13.2-01), ensure `ToolEntity`
is included:

```python
class ToolEntity(EntityNode):
    """A registered assistant tool with its schema and examples."""
    tool_name: str
    tier_scope: str               # "t1" | "t2" | "t3" | "all"
    input_schema_json: str        # JSON string of parameter schema
    input_examples_json: str      # JSON string of input_examples array
    call_count: int = 0
    last_used_at: str | None = None
```

This is a 10-line addition to `synthex_entities.py`. The tool entity ingestion happens
as a one-time setup episode when the Graphiti client initializes.

#### Phase 13.2 — Tool Search function in graph_oracle_adapter.py

Add to `src/assistant/governance/graph_oracle_adapter.py` (13.2-03):

```python
def search_tools_by_intent(
    intent: str,
    *,
    tier: str,
    limit: int = 5,
    timeout_seconds: float = 2.0,
) -> list[dict]:
    """
    Replaces loading full tool schemas.
    Searches Neo4j for tools matching the intent description.
    Returns list of {tool_name, input_schema_json, input_examples_json}.
    Fails open: returns [] if graph unavailable.
    Used by runtime_tier1/2/3.py before each LLM call.
    """
```

#### Phase 14 — Full deferred loading pattern

Modify `src/assistant/runtime_tier1.py`, `runtime_tier2.py`, `runtime_tier3.py`:

```python
# BEFORE (loads all tier-scoped tools regardless of task):
tools = tool_registry.get_tools_for_tier(tier=self.tier)

# AFTER (deferred loading — only fetch when needed):
# Step 1: Give the model only the "search_tools" tool
# Step 2: Model calls search_tools(intent="I need to update product description")
# Step 3: Load only the returned tool schemas
# Step 4: Model calls the actual tool
```

Token savings for Tier 3 (which has the most tools): estimated 40–60% per request.

---

## Concept 4 — Input Examples in Tool Schemas

### What the video says
Adding `input_examples` to tool definitions improves accuracy from 72% to 90%.
Especially valuable for: date formats, nested parameters, conditional fields.

### Where this lives in Synthex

**Critical for the enrichment apply path.** The `POST .../enrichment/runs/{run_id}/apply`
tool has conditional behavior: different fields are valid depending on `strategy_used`.
Without examples, the model frequently misformats `quality_score_before`/`after` deltas.

#### Apply in Phase 13.2-01 (when ToolEntity is defined)

When the Graphiti client runs `graphiti.build_indices_and_constraints()` on startup,
also seed the tool entities with `input_examples`. Pull from the existing OpenAPI schemas
in `src/api/v1/`.

Add to `src/core/graphiti_client.py`:

```python
async def _seed_tool_entities(self) -> None:
    """One-time: ingest tool registry into Neo4j with input_examples."""
    from src.assistant.tool_registry import get_all_tools
    tools = get_all_tools()
    for tool in tools:
        episode = {
            "name": f"tool_definition_{tool.name}",
            "episode_type": EpisodeType.json,
            "content": json.dumps({
                "tool_name": tool.name,
                "description": tool.description,
                "tier_scope": tool.tier_scope,
                "input_schema": tool.input_schema,
                "input_examples": tool.input_examples or [],  # key addition
            }),
            "source": EpisodeType.json,
        }
        await self._graphiti.add_episode(**episode)
```

**Where to add `input_examples` to existing tool definitions:**

File: `src/assistant/tool_registry.py` (read first, add `input_examples` field to tool dataclass)

Priority tools to add examples to (highest accuracy gain):
1. `apply_enrichment_run` — examples for `strategy_used` + `store_id` combination
2. `update_product_fields` — examples for `body_html` vs `tags` vs `variants` format
3. `verify_execution` — examples for `correlation_id` format (UUID with specific prefix)
4. `bulk_stage_products` — examples for the action-block grammar (`action`, `sku`, `fields`)

Target: 3 examples per tool, each covering a different conditional case.

---

## Concept 5 — Deferred Tool Loading (MCP Config Pattern)

### What the video says
`deferred_loading: true` in MCP config keeps all tools hidden until the model searches.
The model only sees the "Tool Search" tool initially.

### Where this lives in Synthex

Synthex doesn't use MCP yet, but the **tier-scoped tool projection already implements
the spirit of this pattern.** Tier 1 sees read-only tools. Tier 2 sees mutation tools.
Tier 3 sees delegation tools. The tool list is already filtered.

The gap is that even within a tier, all tools are loaded at once.

#### Phase 13.2 — Add `deferred` flag to tool registry

File: `src/assistant/tool_registry.py` (read first)

Add `deferred: bool = False` to the tool dataclass. Mark expensive/rarely-used tools
as `deferred=True`. The runtime loads non-deferred tools upfront, deferred tools only
after `search_tools_by_intent()` returns them.

```python
@dataclass
class AssistantTool:
    name: str
    description: str
    tier_scope: str
    input_schema: dict
    input_examples: list[dict] = field(default_factory=list)
    deferred: bool = False        # NEW — if True, load only when searched
    call_weight_tokens: int = 0   # NEW — estimated token cost of schema
```

Mark these as `deferred=True` immediately:
- `bulk_stage_products` (large schema)
- `run_enrichment_batch` (complex nested params)
- Any tool with `call_weight_tokens > 500`

This is an additive change. Existing behavior unchanged for `deferred=False` tools.

#### Future MCP integration

When Synthex eventually integrates Claude's MCP server, the `deferred` flag maps directly
to `deferred_loading: true` in the server config. The migration path is already designed.

---

## Concept 6 — Optimized Multi-Step Workflows

### What the video says
For tasks like "search all emails for pattern X," design the agent to use a programmatic
loop rather than one tool call per email. This is deterministic and dramatically cheaper.

### Where this lives in Synthex

**The enrichment batch workflow is the exact use case.** Today:
```
Tier 3 → analyze vendor 1 → wait → analyze vendor 2 → wait → ... → analyze vendor 8
```

**Phase 14 target:**
```
Tier 3 → write: "for vendor in vendors: run_enrichment(vendor)" → execute as Chord → done
```

The graph oracle is the key enabler: before generating the execution plan, query the graph
for which vendors have `failure_warning` edges, which have low `quality_uplift` history,
which have high `sku_count_delta` volatility. The plan is graph-informed, not guessed.

#### Phase 14 concrete change

File: `src/assistant/runtime_tier3.py`

Replace the current sequential delegation loop with:
```python
from src.assistant.execution_planner import CeleryExecutionPlan
from src.assistant.governance.graph_oracle_adapter import query_graph_evidence

def _build_enrichment_plan(self, vendors: list[str], store_id: int) -> CeleryExecutionPlan:
    plan = CeleryExecutionPlan()
    for vendor in vendors:
        evidence = query_graph_evidence(
            action_type="enrichment",
            target_module=f"vendor:{vendor}",
            store_id=store_id,
        )
        if evidence["decision"] == "warn":
            plan.add_task(run_enrichment.s(vendor, store_id, mode="conservative"))
        else:
            plan.add_task(run_enrichment.s(vendor, store_id, mode="standard"))
    return plan
```

The result: one graph query per vendor (fast, cached), one Celery plan dispatch,
zero LLM round trips for orchestration.

---

## Implementation Sequencing by Phase

### Phase 13.2 — Apply NOW (low-risk, additive)

| Change | File | Risk | LOC delta |
|---|---|---|---|
| Add `ToolEntity` + `ToolSearchEdge` to entity types | `src/core/synthex_entities.py` | Low | +15 |
| Add `_filter_vendor_payload()` to episode builder | `src/jobs/graphiti_ingestor.py` | Low | +10 |
| Add `search_tools_by_intent()` to oracle adapter | `src/assistant/governance/graph_oracle_adapter.py` | Low | +25 |
| Add `deferred` + `call_weight_tokens` + `input_examples` to tool dataclass | `src/assistant/tool_registry.py` | Low | +10 |
| Add `_seed_tool_entities()` to graphiti client | `src/core/graphiti_client.py` | Low | +20 |
| Use Celery `group()` in `sync_failure_journey` | `src/tasks/graphiti_sync.py` | Low | +5 |

**Total: ~85 LOC additions. Zero breaking changes. All additive.**

### Phase 14 — Build on the foundation

| Change | File | Notes |
|---|---|---|
| `ContextWindowGuard` | `src/assistant/context_window_guard.py` | ~120 LOC new file |
| `CeleryExecutionPlan` | `src/assistant/execution_planner.py` | ~150 LOC new file |
| Deferred loading in runtime | `src/assistant/runtime_tier1/2/3.py` | +20 LOC each |
| Graph-informed execution plan | `src/assistant/runtime_tier3.py` | Replace delegation loop |
| Input examples on all tools | `src/assistant/tool_registry.py` | +3 examples × N tools |

### Phase 15 — Complete the loop

| Change | File | Notes |
|---|---|---|
| `CeleryExecutionPlan` for remediation | `src/tasks/` self-healing tasks | Phase 15 work |
| `context_window_guard` in remediation context | Remediation agent | Phase 15 work |
| Tool search for remediation toolset | Graph query before plan | Phase 15 work |

---

## Interaction with the Phase 13.2 Plan Already Written

The primary Phase 13.2 plan is `clever-booping-muffin.md` (master blueprint).
This document is a supplement. The additions from this document to Phase 13.2 are:

1. `ToolEntity` added to `synthex_entities.py` (13.2-01) — 15 LOC
2. `_filter_vendor_payload()` added to `graphiti_ingestor.py` (13.2-02) — 10 LOC
3. `search_tools_by_intent()` added to `graph_oracle_adapter.py` (13.2-03) — 25 LOC
4. `deferred`/`input_examples` added to tool registry dataclass (13.2-01 or 13.2-03) — 10 LOC
5. `_seed_tool_entities()` in graphiti client (13.2-01) — 20 LOC
6. Celery `group()` in sync_failure_journey (13.2-02) — 5 LOC

**Total supplement to Phase 13.2: ~85 LOC across existing plans. No new plans needed.**

These are all small, additive, risk-free changes that set up Phase 14 to fully implement
the programmatic execution and deferred loading patterns without a major refactor.

---

## What NOT to Change During Phase 13.2

Per the frontend soft freeze (master plan Step 0b):
- No changes to `src/api/v1/` response schemas
- No changes to `frontend/src/features/`
- No changes to existing tool _behavior_ — only adding metadata fields to the dataclass
- No removing tools from tier-scoped projections

The `deferred` flag is additive metadata only. Tools marked `deferred=True` continue
loading normally until Phase 14 runtime changes activate deferred loading behavior.

---

## Token Cost Estimate (when fully implemented by Phase 14)

| Optimization | Mechanism | Estimated Saving |
|---|---|---|
| Programmatic batch ingestion | Celery `group()` instead of per-item `.delay()` | 40–50% Celery overhead |
| Content filtering in episodes | `_filter_vendor_payload()` | Episodes ≤2KB, no raw HTML leak |
| Tool search (deferred loading) | Only load schemas when searched | 30–40% context reduction per Tier 3 call |
| Input examples | Higher accuracy, fewer retry calls | 18% accuracy gain → fewer correction round trips |
| Context window guard | Cap budget before LLM call | Prevents 1M-token accidental contexts |

Combined Phase 14 target: **35–50% reduction in tokens per Tier 3 enrichment cycle.**
This directly reduces OpenRouter API cost at Bastelschachtel.at scale.

---

## Constitutional Addendum (append to KNOWLEDGE_GRAPH_ORACLE.md)

When Phase 13.2-03 creates `.planning/KNOWLEDGE_GRAPH_ORACLE.md`, append:

```markdown
## Tool Calling 2.0 Protocol

### Programmatic execution (Phase 14+)
- Tier 3 MUST generate a CeleryExecutionPlan before dispatching any multi-vendor task
- Plans MUST be graph-informed: query failure_warnings before adding vendor to plan
- Individual `.delay()` calls for batch operations are PROHIBITED in Phase 14+

### Context window discipline
- Episode bodies MUST be ≤2KB (enforced by _filter_vendor_payload)
- ContextWindowGuard MUST be called before every LLM invocation in Tier 2/3
- Raw HTML, full JSON payloads, unfiltered vendor data MUST NOT enter the context

### Tool loading discipline
- Tools marked deferred=True MUST NOT appear in the initial system prompt
- search_tools_by_intent() MUST be called when the intent requires a tool not in base set
- input_examples MUST be present on all tools with conditional or nested parameters
```

---

## Summary

The five Tool Calling 2.0 concepts from the video are not hypothetical for Synthex —
they solve real problems already present in the codebase:

- **Programmatic execution** → fixes Tier 3 sequential delegation overhead (Phase 14)
- **Context filtering** → prevents raw vendor data from leaking into graph episodes (Phase 13.2 NOW)
- **Tool search** → makes the graph the source of truth for what tools exist (Phase 13.2 + 14)
- **Input examples** → improves enrichment apply accuracy from estimated 70% to 85%+ (Phase 13.2 NOW)
- **Deferred loading** → reduces per-call token cost for Tier 3 by 30–40% (Phase 14)

The graph (Neo4j + Graphiti) is the infrastructure that makes all five patterns possible.
Without the graph, tool search has no store. Without the graph, programmatic plans have no
historical evidence to inform them. The Phase 13.2 work is not just governance infrastructure —
it's the prerequisite for every efficiency gain described in the video.

Build Phase 13.2. Then Phase 14 gets all five patterns for free.
