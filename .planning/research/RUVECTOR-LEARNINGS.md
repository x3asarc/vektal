# Research: ruvnet/ruvector — Integration Learnings
**Date**: 2026-02-24
**Source**: https://github.com/ruvnet/ruvector (v2.0.4, MIT)
**Scope**: RAG / Graphiti / Neo4j / MCP / agent workflow applicability
**Status**: Research only — no implementation committed

---

## What RuVector Is

A Rust-native unified engine combining HNSW vector search, dynamic minimum-cut coherence
scoring, graph intelligence, and self-learning memory into one binary. It targets AI agent
systems and real-time analytics. Key performance claims: p50 < 0.8ms on 1M vectors, 4–32×
memory compression vs Python equivalents, SIMD (AVX2/NEON) accelerated distance ops.

Written in Rust with 86+ crates. Ships Node.js (NAPI-RS) and WASM bindings. Has its own MCP
server, Claude Code integration hooks, and a custom vector format (RVF).

---

## Crate Map (Learnable Patterns, Grouped by Relevance)

```
Vector Core
  ruvector-core          HNSW + redb on-disk storage + SIMD metrics
  ruvector-coherence     Anytime-valid coherence scoring (statistical gating)
  ruvector-filter        Post-search metadata filtering layer

Graph Layer
  ruvector-graph         Property graph engine (Neo4j-compatible CLI)
  ruvector-gnn           Graph Neural Network operations over embeddings
  ruvector-dag           DAG for dependency/task ordering
  ruvector-delta-graph   Incremental graph updates (delta-only sync)

Attention / Retrieval
  ruvector-attention     Multi-head attention over retrieved node sets
  ruvector-mincut        Dynamic minimum cut for coherence partitioning
  ruvector-attn-mincut   Fused attention + min-cut scoring
  ruvector-sparse-inference  Sparse activation inference (token-efficient)

Time / State
  ruvector-temporal-tensor   Time-decay embeddings, temporal similarity
  ruvector-delta-core        Incremental state tracking (delta operations)
  ruvector-snapshot          Point-in-time graph snapshots

MCP / Agent Gates
  mcp-gate               Standalone MCP server wrapping the Cognitum gate
  cognitum-gate-kernel   Statistical confidence gate kernel
  cognitum-gate-tilezero Tile-zero initialisation for multi-agent gating

Distributed
  ruvector-raft          Raft consensus for distributed vector DB
  ruvector-replication   Replication state machine
  ruvector-cluster       Cluster membership + ring routing

Format / Storage
  rvlite                 Embedded edge DB (no server required)
  rvf-*                  RVF wire format: quant + crypto + manifest + runtime
  ruvector-postgres      PostgreSQL backend for vector storage

LLM / Inference
  ruvllm                 LLM integration layer
  ruvector-router-core   Model/backend routing (capability-based dispatch)
  ruvector-nervous-system  Distributed "nervous system" coordination mesh
  ruvector-cognitive-container  Encapsulated reasoning unit
```

---

## Learning 1: Anytime-Valid Coherence Gate (mcp-gate / cognitum-gate-kernel)

### What It Is
A separate MCP server (`crates/mcp-gate/`) that wraps every agent mutation with a
statistical confidence test from the cognitum-gate-kernel. The key property is "anytime-valid"
— the gate can be checked at any point during an operation and the false-positive rate remains
bounded (uses sequential hypothesis testing / martingale methods, not fixed p-values).

This is fundamentally different from threshold-based gating (e.g., "confidence > 0.7").
Anytime-valid means: check early → cheap stop if already safe; check late → higher power.
The gate adapts to how much evidence has accumulated.

### Why It Matters Here
Our current mutation gates are threshold-based:
- `kill_switch.py` — boolean enabled/disabled
- `field_policy.py` — hardcoded confidence thresholds per field type
- `convention_checker.py` — cosine ≥ 0.7 to flag a violation

All three are fixed-alpha tests. They will either over-reject (block valid mutations) or
under-reject (miss edge cases) because the threshold doesn't adapt to evidence volume.

The `cognitum-gate-tilezero` pattern initialises a "tile" of prior knowledge at session start
(our session lifecycle hook already does this for Convention nodes) and then the gate updates
that prior continuously as more context arrives — exactly how a Bayesian filter works.

### Mathematical Foundation (Prime Radiant)
The ruvector "Prime Radiant" coherence gate measures this using the **Sheaf Laplacian**:

```
E(S) = Σ wₑ · ‖ρᵤ(xᵤ) - ρᵥ(xᵥ)‖²
```

Where `ρ` is a restriction map that projects node features into edge space, and `E(S)` is
total contradiction energy. Zero energy = fully consistent. Rising energy = contradictions
accumulating.

This maps to a **Compute Ladder** (4 lanes by energy threshold):

| Energy | Lane | Latency | Action |
|---|---|---|---|
| < 0.1 | Reflex | < 1ms | Immediate approval |
| 0.1–0.4 | Retrieval | ~10ms | Fetch more evidence |
| 0.4–0.7 | Heavy | ~100ms | Deep analysis |
| > 0.7 | Human | async | Escalate to HITL |

The key distinction from our current approach: **"how many contradictions exist in the
retrieved evidence?"** vs **"how confident is the model?"** — a model can be confidently wrong.

### Applicable Pattern
```
Current:  field_policy.py: confidence > THRESHOLD → allow
Future:   CoherenceGate.energy(retrieved_nodes) → lane → allow/defer/block/escalate
          energy() is the Sheaf Laplacian over the retrieved Neo4j subgraph
```

Concrete integration target: `src/assistant/governance/field_policy.py` — replace static
thresholds with energy-based routing seeded by Convention + Decision nodes from Neo4j.
The prior is the graph; the energy measures internal consistency of the retrieved context.

---

## Learning 2: Min-Cut Coherence for Retrieval Partitioning

### What It Is
`ruvector-mincut` computes a dynamic minimum graph cut over the retrieved node set. The cut
partitions results into "coherent" vs "peripheral" nodes — nodes that are densely connected to
the query cluster (keep) vs weakly connected (drop or defer). The `ruvector-attn-mincut` crate
fuses this with multi-head attention so the cut adapts to the query embedding.

The practical effect: instead of a flat top-k list from HNSW, you get a topologically
meaningful cluster. Nodes on the wrong side of the min-cut are excluded even if they score
well on cosine similarity alone.

### Why It Matters Here
Our `search_expand_bridge.py` currently uses:
1. Top-5 initial nodes by cosine similarity
2. Breadth-first expansion to depth 2 following typed edges
3. Token budget as the stop condition

Step 2 can produce an incoherent expansion — a node at depth-2 that is only weakly connected
to the query cluster but happens to be within 2 hops gets included. With 4 allowed edge types
(IMPORTS, CALLS, IMPLEMENTS, EXPLAINS) the expansion fan-out is unconstrained in breadth.

Min-cut would add a coherence filter _after_ expansion:
- Build a subgraph of all expanded nodes + their inter-connections
- Compute min-cut separating query-anchor from the rest
- Retain only nodes on the same side as the query-anchor

### Applicable Pattern
```python
# Pseudocode for search_expand_bridge.py enhancement
def filter_by_mincut(anchor_nodes, expanded_nodes, relationships):
    G = build_subgraph(anchor_nodes + expanded_nodes, relationships)
    cut_nodes = compute_mincut_partition(G, sources=anchor_node_ids)
    return [n for n in expanded_nodes if n["id"] in cut_nodes]
```

This is doable in Python with NetworkX (already a likely transitive dep via Graphiti) without
porting anything from Rust. The coherence gain: fewer "accidental" nodes consuming the token
budget, higher signal density in the returned context.

---

## Learning 3: Delta Operations (ruvector-delta-*)

### What It Is
The `ruvector-delta-*` crate family tracks every graph/vector change as a typed delta:
- `delta-core` — delta record schema (operation, entity_id, before, after, timestamp)
- `delta-index` — queryable index of recent deltas by entity, time range, operation type
- `delta-graph` — graph structure changes (node add/remove, edge type change)
- `delta-consensus` — distributed agreement on which deltas to apply (Raft-backed)

The CLI exposes `delta-behavior` examples showing how to replay, squash, or branch deltas —
essentially git-style versioning for the knowledge graph.

### Why It Matters Here
Our `incremental_sync.py` runs a full diff between filesystem state and Neo4j on each git
hook trigger. This works but has a correctness risk: if two hooks fire in quick succession
(e.g., git rebase touching 30 files), the sync can miss intermediate states.

The delta pattern would:
1. Convert each git hook event to a typed delta record (file_modified, function_added, etc.)
2. Append to a delta log (append-only, never re-compute)
3. Sync applies the log serially — idempotent, replayable, auditable

Secondary benefit: delta log is queryable for "what changed in the last 24 hours" — feeds
directly into `retrieve_intent` queries about recent codebase evolution.

### Applicable Pattern
The delta schema maps cleanly to our Graphiti episode structure:
```python
# Current: emit_episode(text=diff_summary, metadata={...})
# Enhanced: emit_delta_episode(operation="file_modified", entity="src/graph/mcp_server.py",
#                              before_sha="abc", after_sha="def", timestamp=now)
# Index: Episode nodes tagged with delta_type relationship for fast range queries
```

No new Neo4j schema needed — a new `delta_type` property on existing Episode nodes + a
`DELTA_OF` edge from Episode to the affected File/Function node covers it.

---

## Learning 4: REFRAG Pipeline — Compress-Sense-Expand (examples/refrag-pipeline)

### What It Is
Based on arXiv:2509.01092. REFRAG is a **tensor bypass** RAG architecture, not re-chunking.
Architecture: **COMPRESS → SENSE → EXPAND**

```
Index time:  text → embedding (768-dim) → store as tensor
Query time:  query → SENSE policy net (~2-15µs) → decision: send tensor OR text
  COMPRESS:  pre-stored 768-dim tensor, sent directly to LLM's hidden state
  EXPAND:    project tensor to LLM native dim (768→4096 for LLaMA-3, 1536→8192 for GPT-4)
```

The key insight: instead of text chunks that the LLM must tokenize (~5-20ms) and transfer
(~10-50ms), REFRAG pre-computes representation tensors at ingest and sends them directly to
the LLM's context. A lightweight policy network decides which path per chunk:

| Policy | Latency | Description |
|---|---|---|
| ThresholdPolicy | ~2µs | Cosine similarity threshold |
| LinearPolicy | ~5µs | Single-layer classifier |
| MLPPolicy | ~15µs | Two-layer neural network |

Reported latency reduction: ~30x vs text transfer path. Compression modes: None (1×),
Float16 (2×), Int8 (4×), Binary (32×). Zero-copy via `rkyv` for direct memory access.

### Why It Matters Here
Our semantic cache works on full query results. The cache entry is the complete bridge output
for a given embedding. Two queries with cosine ≥ 0.92 will return the _same_ cache entry.

But query A ("who calls semantic_cache.py") and query B ("what does semantic_cache.py export")
might score ≥ 0.92 embedding similarity while needing fundamentally different fragments. The
current cache conflates them.

The **immediately applicable** pattern (no LLM hidden state access needed) is the two-level
cache from the SENSE/COMPRESS split:
- **L1 (current)**: full result cache, 0.92 threshold — fast path for near-identical queries
- **L2 (new)**: fragment candidate cache — for L1 misses, retrieve candidate nodes from cache
  and re-rank/re-assemble rather than re-running the full graph traversal

The tensor bypass is a future Phase 15+ concern when we control the embedding→LLM pipeline;
the cache architecture is applicable now.

---

## Learning 5: MCP Dual Transport (stdio + SSE)

### What It Is
The `ruvector-mcp` binary supports two transports from a single `--transport` flag:
- `stdio` — default, used by Claude Code locally
- `sse` — HTTP Server-Sent Events, used for remote/browser access on any port

The same `McpHandler` struct handles both; only the transport wrapper changes. This matters for
multi-agent or remote orchestration scenarios where Claude Code instances on different machines
need to share the same knowledge graph MCP server.

### Why It Matters Here
Our `mcp_server.py` is stdio-only. This is fine for local Claude Code usage but becomes a
bottleneck if Phase 15's self-healing agents run as distributed Celery workers (which they will
— Tier 3 spawns sub-agents via Celery tasks). Celery workers can't share a stdio pipe.

An SSE transport for our MCP server would allow:
- `celery_worker` container to query the graph via HTTP
- `celery_scraper` container to emit episodes to the graph directly
- Multiple Claude Code windows (multi-user) to share graph state without a separate Neo4j
  connection per client

The FastAPI SSE pattern is already in the codebase (job stream endpoint uses SSE). Adding
`--transport sse` to `mcp_server.py` is a low-effort structural upgrade before Phase 15.

---

## Learning 6: Temporal Tensors (ruvector-temporal-tensor)

### What It Is
Embeds a time-decay signal directly into the vector representation. Nodes become
"fresher" or "staler" as time passes without being explicitly re-embedded. The decay is
applied at query time by multiplying the stored embedding with a time-decay kernel:

```
effective_embedding = stored_embedding * time_kernel(age, decay_rate)
```

Result: a file last touched 6 months ago scores lower in similarity even if its content is
semantically identical to the query — unless the query is specifically looking for historical
artifacts. The decay_rate is configurable per entity type.

### Why It Matters Here
Convention nodes, Decision nodes, and BugRootCause nodes have different temporal relevance:
- **Convention** nodes: slow decay (rules stay valid for months)
- **Decision** nodes: medium decay (decisions can be superseded; SUPERCEDES edge handles this
  structurally, but temporal decay adds a soft signal before the formal superseding happens)
- **BugRootCause** nodes: fast decay (a bug fix becomes less relevant as the codebase evolves)
- **File** nodes: decay proportional to git inactivity — stale files surface less

Currently our semantic cache uses cosine similarity with no time component. An expired TTL
is a hard cutoff (3600s → evict). Temporal decay is a soft continuous signal.

Minimal integration path: add `last_modified_ts` to node embeddings at query time in
`search_expand_bridge.py` by applying a scalar weight:

```python
def temporal_weight(node: dict, decay_rate: float = 0.01) -> float:
    age_days = (now - node["updated_at"]).days
    return math.exp(-decay_rate * age_days)

# score = cosine_similarity * temporal_weight(node)
```

---

## Learning 7: Sparse Inference (ruvector-sparse-inference)

### What It Is
Applies sparse activation patterns to inference: instead of activating all 384 embedding
dimensions for every retrieval, only activate the dimensions that correlate with the current
query's "activation mask". Claims 3-8× throughput improvement with <2% recall loss at k=10.

Technically: a learned binary mask per query cluster selects which embedding dimensions
participate in distance computation. The mask is retrieved from a small index (fast) then
applied to the full vectors (vectorised, cache-friendly).

### Why It Matters Here
Our 384-dim sentence-transformers embeddings are dense — all dimensions used for every
comparison. At 4,000+ SKUs and 1,000+ code nodes, this is fine. But Phase 15 will add:
- Per-product embeddings for vendor catalog
- Per-customer embeddings for personalisation
- Embedding history (multiple versions per entity)

At 50K+ entities, dense 384-dim search becomes expensive even with Neo4j's vector index.
Sparse inference is worth studying as a pre-filter before the HNSW/ANN step.

In Python, the concept is simpler than the Rust implementation — a dimension selection mask
applied via numpy before running the cosine similarity batch. No dependency on ruvector.

---

## Learning 8: Self-Learning Hooks + Claude Flow V3

### What It Is
The `ruvector` CLI has a `hooks` subcommand with 50+ operations for integrating with Claude
Code. The hooks call home to a `@claude-flow/cli` process that manages:
- 3-tier model routing: WASM booster (< 100 tokens) → Haiku → Sonnet/Opus
- Hierarchical swarm topology with max 15 concurrent agents
- Memory persistence via `@claude-flow/memory` npm package (≥ v3.0.0-alpha.7)

The CLAUDE.md in the ruvector repo configures this as the default Claude Code behaviour for
contributors — every Claude Code session uses the swarm topology automatically.

### Why It Matters Here
Phase 14.1 built session lifecycle hooks (14.1-06) that pull Convention nodes on init. The
ruvector model shows a more sophisticated version: the session hook doesn't just pull data,
it also _routes_ the Claude Code instance to an appropriate tier based on task complexity
detected from the session's initial context.

The 3-tier routing maps directly to our existing Tier 1/2/3 architecture — our tiers govern
mutation safety; their tiers govern model cost. Combining both creates a 2D routing matrix:
```
                Tier 1 (read)    Tier 2 (dry-run)    Tier 3 (agent)
WASM/Haiku       Ideal                OK              Not recommended
Sonnet           OK                  Ideal            OK
Opus             Overkill            OK               Ideal
```

Session init hook could detect task keywords ("refactor", "apply", "spawn") and pre-select
model + mutation tier simultaneously, rather than routing them independently as we do today.

---

## Learning 9: Cognitive Container (ruvector-cognitive-container)

### What It Is
An encapsulated reasoning unit: a container holding an embedding, a working memory buffer, a
goal state, and a set of allowed operations. Multiple containers can run concurrently and
communicate via the nervous system mesh. Each container is independently paused, snapshotted,
resumed, or discarded.

This is the implementation analogue of what Claude's agent specs call "sub-agents" — but with
explicit state encapsulation and a defined lifecycle (init, run, checkpoint, terminate).

### Why It Matters Here
Our Tier 3 sub-agents (`agent.spawn_sub_agent` tool) currently have no lifecycle contract.
A sub-agent is a Celery task that runs to completion or times out. There is no:
- Checkpoint (save partial progress, resume later)
- Pause (block on HITL approval without burning Celery worker)
- Snapshot (replay sub-agent work for verification)

The cognitive container pattern suggests adding a lightweight state envelope to every Tier 3
task:

```python
@dataclass
class SubAgentEnvelope:
    agent_id: str
    goal: str
    working_memory: list[dict]  # accumulated context
    checkpoint_at: int          # step number of last checkpoint
    allowed_operations: list[str]  # from tool_projection
    status: Literal["running", "paused", "checkpointed", "done"]
```

This envelope would live in Redis (already in the stack) alongside the Celery task state,
giving HITL the ability to inspect, approve, resume, or discard a sub-agent mid-execution.

---

## Learning 10: RVF Wire Format (rvf-* sub-workspace)

### What It Is
A custom binary format for vectors combining: quantization (f32 → int8/int4 configurable),
cryptographic manifest (SHA-256 per chunk), streaming runtime (chunk-at-a-time decode), and
an eBPF kernel hook for zero-copy IO on Linux. It is effectively "Parquet for embeddings" —
columnar, compressed, integrity-verified, streamable.

### Why It Matters Here
Our embeddings are stored in Neo4j's vector index with no integrity verification. The node's
embedding is whatever was last written — there is no mechanism to detect silent corruption
or verify that the stored embedding matches the source content.

The RVF manifest concept is a lightweight borrowable idea: when writing an embedding to Neo4j,
also write a `embedding_sha` property derived from the source content. On retrieval, verify
the SHA before using the embedding in distance computation. Flag mismatches as discrepancies
in `ReasoningTrace` (Phase 14.1-02 already has discrepancy tracking infrastructure).

No need to adopt the full binary format — just the manifest discipline applied to our
existing JSON-over-bolt Neo4j writes.

---

## Learning 11: GNN-Over-HNSW — Continuous In-Flight Learning

### What It Is
RuVector places a Graph Neural Network layer **on top of** the HNSW index rather than treating
the index as a static lookup. The GNN loop:

```
Query → HNSW nearest neighbours → GNN multi-head attention over neighbours
      ↑                                                                    ↓
      └──────────── path weights reinforced ──────────── better ranking ──┘
```

This is **not periodic reindexing** — it is continuous in-flight learning. Frequently-traversed
paths get reinforced; cold paths decay. No retraining, no reconfiguration. At query time the
GNN applies multi-head attention to weight which neighbours matter given graph topology.

Specific numbers: k=10 on 384-dim vectors, single thread: **61µs p50, 16,400 QPS**.
Multi-thread (16 threads): 3,597 QPS at 2.86ms p50.

### Why It Matters Here
Our `search_expand_bridge.py` does static cosine + BFS expansion. The path weights never
update — a Code node that was retrieved 1,000 times is weighted identically to one retrieved
once. We miss the signal that heavy retrieval patterns carry.

The applicable Python equivalent: after each retrieval, emit a Graphiti episode tagging
which nodes were included in the returned context. A background task (Celery beat) can
re-weight edges in Neo4j based on retrieval frequency:

```python
# On successful retrieval emit:
emit_episode(type="retrieval_event", nodes_returned=[n["id"] for n in results],
             query_embedding_hash=embed_hash)

# Nightly Celery beat:
# Increment edge weight for co-retrieved node pairs → influences next BFS traversal
```

This is the "poor man's GNN" that requires no Rust and no model changes — just edge weight
updates in Neo4j driven by empirical retrieval patterns.

---

## Learning 12: AgentDB Six Memory Patterns

### What It Is
The `agentdb` npm package (built on ruvector) implements six cognitive memory patterns drawn
from published AI agent research:

| Pattern | Source | What It Stores | Key Capability |
|---|---|---|---|
| Reflexion Memory | Shinn et al. 2023 | Full task trajectories (inputs, outputs, rewards, self-critiques) | Learn from past successes/failures without retraining |
| Skill Library | Voyager 2023 | High-reward execution patterns as parameterized, composable skills | Reuse proven strategies across tasks |
| Causal Memory Graph | Novel | Action → outcome causal links as graph edges | Causal reasoning: "if I change X, what happens to Y?" |
| Causal Recall | Novel | Same as vector search, but reranked by **business utility**, not similarity | Returns the *useful* memory, not just the *similar* one |
| Explainable Recall | Novel | Merkle certificate proofs explaining why memories were retrieved | Audit trail, debugging, quality verification |
| Nightly Learner | Novel | K-means++ clustering hourly; EWC++ weekly to prevent forgetting | Background consolidation without blocking request path |

**Backend auto-selection**: RuVector → HNSWLib → better-sqlite3 → sql.js (WASM fallback).

**Causal Recall vs Semantic Recall** is the most important distinction: standard vector
search returns similar items; Causal Recall reranks by utility — what historically produced
good outcomes, weighted by causal impact and performance cost.

### Why It Matters Here
Our `memory_retrieval.py` currently does blended vector + lexical scoring (0.7v + 0.3l).
The result is the most *similar* past memory, not the most *useful* one.

**Reflexion Memory** maps to our `ReasoningTrace` nodes — we capture reasoning steps but do
not tag them with outcome quality or self-critique. Adding `success: bool` + `critique: str`
to ReasoningTrace would let future queries filter to successful trajectories only.

**Skill Library** maps to our `Decision` nodes — reusable approved patterns. Currently
a Decision node is static. If we track which decisions led to successful `EnrichmentOutcome`
episodes (via the existing `YieldedOutcomeEdge`), we can surface "proven patterns" as a
distinct retrieval class.

**Causal Recall** in Python:
```python
# Current: score = 0.7 * cosine + 0.3 * lexical
# Enhanced: causal_score = base_score * utility_weight(node)
# utility_weight = f(past_outcome_quality, retrieval_frequency, recency)
# Retrieved from: Episode nodes with outcome_quality property (phase 14.1-02 already has this)
```

---

## Learning 13: SONA — Three Temporal Learning Loops

### What It Is
SONA (Self-Optimizing Neural Architecture) separates continuous learning into three
non-blocking temporal loops:

| Loop | Frequency | Latency | Mechanism |
|---|---|---|---|
| A: Instant | Per-request | <100µs | MicroLoRA rank 1-2 (<50KB adapters) |
| B: Background | Hourly | ~100ms | K-means++ clustering + BaseLoRA rank 4-16 |
| C: Deep | Weekly | Minutes | EWC++ (prevents catastrophic forgetting) |

The key insight: **no loop blocks the request path**. Loop A applies per-request micro
adaptations with near-zero overhead. Loops B and C run as background consolidation tasks.
EWC++ (Elastic Weight Consolidation) penalises large changes to weights important for
previously-learned tasks — the system remembers old patterns while learning new ones.

**ReasoningBank**: stores successful reasoning trajectories via K-means++ clustering. On
a new query, similar past trajectories influence the current response — this is the Reflexion
paper's insight implemented as a background service.

### Why It Matters Here
Our agent system has no equivalent of the temporal learning loops. Each session starts cold.
The session init hook (14.1-06) loads Convention + Decision nodes but not *outcome patterns*.

Mapping to our Celery architecture:
```
Loop A (per-request):  In-memory LRU weight on node scores within current request
Loop B (hourly):       Celery beat task — re-weight Neo4j edges from episode patterns
Loop C (weekly):       Celery beat task — cluster Episode nodes, promote patterns to Decision nodes
```

The weekly Loop C is particularly powerful: automatically promote high-quality `ReasoningTrace`
episodes (where `oracle_decision = pass` and `outcome_quality >= 0.85`) to `Decision` nodes
— creating a self-improving knowledge graph that grows from successful executions.

---

## Learning 14: Hybrid Search — Dense + Sparse + Graph

### What It Is
RuVector's most capable retrieval mode blends three signal types simultaneously:

```
score = hybridAlpha * dense_score + (1-hybridAlpha) * sparse_score
      + graph_traversal_bonus(cypher_hops)
```

- **Dense**: embedding cosine/dot-product — semantic meaning
- **Sparse**: BM25/TF-IDF/SPLADE — keyword precision
- **Graph**: Cypher multi-hop traversal — structural relationships

Default `hybridAlpha = 0.7` (70% semantic, 30% keyword). GNN reranking applied after hybrid
score is computed. The sparse signal handles exact-match queries that dense embeddings score
poorly (e.g., querying for a specific function name that doesn't appear in the training corpus).

### Why It Matters Here
Our `search_expand_bridge.py` already does blended scoring (0.7 vector + 0.3 lexical from
13.2-03). We are effectively at `hybridAlpha = 0.7` on the dense+sparse axis. What we lack:

1. **Structural graph bonus**: BFS expansion adds graph context but doesn't feed back into
   node scores. A node reached via an `IMPLEMENTS` edge from a high-scoring anchor should
   score higher than one reached via a weak `REFERENCES` edge from a low-scoring anchor.

2. **Sparse SPLADE-style index**: our lexical scoring is simple character n-gram overlap.
   True sparse retrieval (BM25 or SPLADE) would handle German compound words and technical
   identifiers much better.

Minimal integration for point 1 — add edge-type weights to BFS scoring in `search_expand_bridge.py`:
```python
EDGE_SCORE_MULTIPLIER = {"IMPLEMENTS": 1.3, "CALLS": 1.1, "IMPORTS": 0.9, "REFERENCES": 0.7}
# node_score *= EDGE_SCORE_MULTIPLIER[edge_type] * anchor_score
```

---

## Learning 15: COW Branching for Versioned Knowledge Graphs

### What It Is
RuVector implements copy-on-write (COW) branching at the vector cluster level, analogous to
git branches for the knowledge graph:

```
1M-vector parent + 100 edits = ~2.5MB child branch (not 512MB full copy)
```

Each "branch" is a sparse patch (DELTA segment) on top of a shared parent. Branch metadata
tracks ownership (COW_MAP) and reference counts (REFCOUNT). Branches can be merged, discarded,
or promoted to become the new parent.

Use case: test "what if we added these 500 new documents?" without committing. Query the branch
independently, measure retrieval quality, then promote or discard.

### Why It Matters Here
Phase 15 (Self-Healing) will need to test alternative knowledge graph states — e.g., "if we
retracted these 20 vendor decisions, does the oracle start blocking different operations?"

Our current Neo4j instance has no branching. Every write is permanent. Testing hypotheticals
requires either:
1. A second Neo4j instance (expensive)
2. Saving + restoring snapshots (slow, ~30s round-trip)

The COW pattern is implementable in Neo4j via a `branch_id` property on nodes + edges:
- Main branch: `branch_id = "main"`
- Test branch: `branch_id = "test-vendor-retraction-2026-02-24"`
- Query: add `WHERE n.branch_id IN ["main", current_branch]` to all Cypher queries
- Merge: copy test branch nodes to main, delete branch nodes

This is a subset of what ruvector does in Rust, but the logical structure is the same. The
existing `incremental_sync.py` snapshot infrastructure (Phase 14) provides the foundation.

---

## Prioritised Integration Opportunities

| Priority | Learning | Where | Effort | Risk |
|---|---|---|---|---|
| **P1** | Anytime-Valid Coherence Gate + Compute Ladder | `field_policy.py` | High | High (governance critical path) |
| **P1** | Min-Cut Coherence Filter | `search_expand_bridge.py` | Medium | Low (additive filter) |
| **P1** | Edge-Type Score Multiplier (Hybrid Search) | `search_expand_bridge.py` | Low | Low (additive weight) |
| **P2** | GNN Retrieval Frequency Edge-Weight Loop | `incremental_sync.py` + Celery beat | Medium | Low (additive episode) |
| **P2** | Causal Recall Utility Reranking | `memory_retrieval.py` | Medium | Low (additive score term) |
| **P2** | Delta Operations for Sync | `incremental_sync.py`, `graphiti_sync.py` | Medium | Medium (schema touch) |
| **P2** | MCP SSE Transport | `mcp_server.py` | Low | Low (no schema change) |
| **P2** | Temporal Decay on Embeddings | `search_expand_bridge.py` | Low | Low (additive scalar weight) |
| **P3** | SONA Loop C: Promote Episodes to Decision Nodes | Celery beat + `codebase_schema.py` | Medium | Medium (schema touch) |
| **P3** | Reflexion Memory: outcome tagging on ReasoningTrace | `reasoning_trace.py` | Low | Low |
| **P3** | Two-Level Fragment Cache (L1/L2) | `semantic_cache.py` | Medium | Low |
| **P3** | Sub-Agent Lifecycle Envelope | `assistant_runtime.py`, Redis | Medium | Medium |
| **P3** | Embedding SHA Manifest | `incremental_sync.py`, `codebase_schema.py` | Low | Low |
| **P4** | COW Branching via branch_id in Neo4j | Neo4j schema + Cypher queries | High | Medium |
| **P4** | 2D Tier × Model Routing | Session hook, `tool_projection.py` | High | High (tier safety) |
| **P4** | Sparse Inference Pre-filter | `query_interface.py` | High | Medium |
| **P5** | REFRAG Tensor Bypass (L2 fragment cache first) | `semantic_cache.py` | High | Low (cache only) |

---

## What NOT to Adopt

- **RVF binary format**: Neo4j vector index already handles storage. Adding a separate
  serialisation format adds complexity with no clear gain in our stack.
- **Raft consensus / ruvector-cluster**: We are single-node Neo4j. Raft is for distributed
  vector DB — not applicable until production scale requires it.
- **ruQu (quantum algorithms)**: Listed as `ruqu-exotic`. Research-grade, not production.
- **FPGA transformer (ruvector-fpga-transformer)**: Hardware dependency, incompatible with
  Docker Compose stack.
- **Nervous system mesh**: Compelling concept but `@claude-flow/memory` is `alpha.7` — not
  stable enough for production governance paths.

---

## Phase Routing for These Learnings

```
Phase 14.2 (Tool Calling 2.0 — in plan):
  → MCP SSE Transport (Learning 5)                   low risk, natural fit
  → Temporal Decay on Embeddings (Learning 6)         pure search_expand_bridge.py addition
  → Edge-Type Score Multiplier (Learning 14)          3-line change, immediate gain
  → Embedding SHA Manifest (Learning 10)              additive to existing sync
  → Reflexion: outcome tagging on ReasoningTrace (12) additive property to existing node

Phase 15 (Self-Healing — next):
  → Delta Operations (Learning 3)                     sync + episode schema
  → Min-Cut Coherence Filter (Learning 2)             bridge enhancement
  → GNN retrieval frequency edge-weight loop (11)     Celery beat + Neo4j writes
  → Causal Recall utility reranking (Learning 12)     memory_retrieval.py score term
  → SONA Loop C: episode → Decision promotion (13)    Celery beat weekly task
  → Two-Level Fragment Cache (Learning 4)             semantic_cache enhancement
  → Sub-Agent Lifecycle Envelope (Learning 9)         Tier 3 safety

Future Phase (Post-15):
  → Anytime-Valid Coherence Gate + Compute Ladder (1) replaces field_policy thresholds
  → COW Branching via branch_id (Learning 15)         Phase 15 hypothesis testing
  → 2D Tier × Model Routing (Learning 8)              architectural, needs full design pass
  → REFRAG Tensor Bypass (Learning 4, P5)             requires embedding→LLM pipeline control
  → Sparse Inference Pre-filter (Learning 7)           only when node count > 50K
```

---

## Key Repo Stats for Context

- 86+ Rust crates (30 primary + 13 RVF sub-crates), MIT licensed
- 569 GitHub stars, 117 forks, active as of 2026-02-23
- Claude Code CLAUDE.md present — the repo itself is a Claude Code managed project
- `@claude-flow/memory ^3.0.0-alpha.7` dependency — experimental
- No Python; pure Rust + WASM + NAPI-RS bindings
- Benchmarks (single thread, 384-dim, k=10): **61µs p50, 16,400 QPS** for HNSW
  (vs Neo4j vector index: typically 5-50ms for similar workloads — ~100–800× slower)
- Production use: agentic systems, not general document RAG
- Research coverage: two-pass (surface + deep). Deep pass sourced directly from ADRs,
  example READMEs, and arxiv reference (arXiv:2509.01092 for REFRAG)
