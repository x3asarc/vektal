# Agent SDK Enhancement Map
**Shopify Multi-Supplier Platform**

> Agent SDK is the **conversational orchestration layer** on top of v1.0. It doesn't replace backend infrastructure — it intelligently sequences and personalizes it.

---

## Executive Summary

Your v1.0 system is **complete** with 17 phases delivered:
- ✅ Scraping engine (Phase 2.1)
- ✅ Product enrichment (Phase 2.2)
- ✅ Tier system (Phase 12)
- ✅ Self-healing runtime (Phase 15)
- ✅ Knowledge graph (Neo4j/Aura)
- ✅ Memory system (Letta + append-only events)

**Agent SDK enhancement** adds:
- **Conversational orchestration** → wrap backend flows in natural language
- **Pattern learning** → detect user behavior, optimize subsequent requests
- **Multi-agent routing** → domain-specific agents per function
- **Live context** → graph-aware decision making with memory-priming

**No replacement.** You call existing APIs via Agent SDK; the agents orchestrate them intelligently.

---

## Layer 0: Existing Infrastructure (v1.0)

### Backend APIs (Callable via Agent SDK)

| Capability | Endpoint | Tier | Used by |
|---|---|---|---|
| **Ingest** | `POST /api/v1/ingest` | T2/T3 | Shopify sync task (`src/tasks/ingest.py`) |
| **Scrape** | `POST /api/v1/scrape` | T3 | Scraper task (`src/tasks/scrape_jobs.py`) |
| **Enrich** | `POST /api/v1/enrichment` | T2/T3 | Enrichment pipeline (`src/tasks/enrichment.py`) |
| **Resolve** | `POST /api/v1/resolve` | T2/T3 | Resolution engine (`src/resolution/`) |
| **Apply** | `POST /api/v1/apply` | T2/T3 | Apply engine with governance gates |
| **Search** | `GET /api/v1/products/search` | T1/T2/T3 | Product discovery |
| **Chat** | `POST /api/v1/chat/message` | T1/T2/T3 | Streaming assistant responses |

### Background Jobs (Orchestrated by Agent SDK)

| Task | Queue | Function | Entry |
|---|---|---|---|
| **Ingest job** | `assistant.t1` | Fetch + validate Shopify data | `src/tasks/ingest.py:ingest_job()` |
| **Scrape job** | `assistant.t3` | Multi-vendor product discovery | `src/tasks/scrape_jobs.py:scrape_task()` |
| **Enrichment job** | `assistant.t2` | AI-powered product descriptions | `src/tasks/enrichment.py:enrich_task()` |
| **Rollback job** | `assistant.t2` | Forensic snapshot recovery | `src/tasks/resolution_apply.py` |
| **Chat bulk job** | `assistant.t3` | Bulk SKU orchestration (1000+ items) | `src/tasks/chat_bulk.py` |

### Knowledge Graph (Neo4j/Aura)

**What's in it:**
- 2,098 Function nodes (every backend function)
- 667 Class nodes (ORM models, services)
- 602 File nodes (codebase structure)
- 469 PlanningDoc nodes (phases, tasks)
- CALLS graph (what imports/calls what)
- Episodic layer (empty — Agent SDK writes here)

**Available to agents:**
- `query_graph("imports", {"file_path": "src/core/enrichments.py"})` → see dependencies
- `query_graph("impact_radius", {"file_path": "src/tasks/ingest.py"})` → what breaks if this changes
- `query_graph("similar_files", ...)` → find related code patterns
- `query_graph("function_callees", {"function_name": "enrich_product"})` → trace execution

### Memory System (3-tier)

| Tier | Storage | Lifetime | Access | Example |
|---|---|---|---|---|
| **Working** | Letta agent memory | Session (agent lifetime) | In-agent variable | User's current goal |
| **Short-term** | STATE.md + events log | 7 days | Graph query + events | "User asked about HS codes 3x this week" |
| **Long-term** | Aura (:LongTermPattern) | ∞ | Persistent nodes | "This vendor always ships Tue/Thu" |

**Agent SDK writes to all three:**
1. Session start → load working memory from Aura
2. Task execution → write TaskExecution nodes + events
3. Pattern detection → write LongTermPattern nodes → influences future prompts

---

## Layer 1: Agent SDK Orchestration Layer

### Domain-Specific Agents

```
User Chat (Discord/Web/SDK)
     ↓
Orchestrator Agent (Router)
     ├─ Onboarding Agent
     │  └─ Calls: ingest, scrape, enrich (Phases 2.1–2.2)
     │
     ├─ Sync Agent
     │  └─ Calls: shopify_sync, ingest (Phase 17)
     │
     ├─ Data Quality Agent
     │  └─ Calls: resolve, search (Phase 8, 11)
     │
     ├─ Compliance Agent
     │  └─ Calls: audit, rollback (Phase 17.6)
     │
     └─ Pattern Learning Agent
        └─ Reads: TaskExecution nodes
        └─ Writes: LongTermPattern nodes
```

### How Each Agent Enhances Existing Flow

#### 1. **Onboarding Agent** (Your example)
**Goal:** Walk user through initial setup conversationally.

**Existing components:**
- Shopify OAuth endpoint (`src/api/v1/auth/shopify`)
- Ingest task (`src/tasks/ingest.py:ingest_job()`)
- Vendor discovery (`src/tasks/scrape_jobs.py`)
- Enrichment pipeline (`src/tasks/enrichment.py`)

**What Agent SDK adds:**
```
User: "I want to add my 50 initial products to Shopify"

Onboarding Agent:
  1. Calls Shopify OAuth endpoint
     → "Connected to 'My Store' (8 products exist)"

  2. Shows visualization
     → "Current Shopify catalog: 8 items"
     → "Ready for enrichment"

  3. Asks: "Which vendors should I search for these products?"

  4. Calls vendor discovery API
     → For each SKU: searches supplier databases (Phase 2.1)

  5. Shows results
     → "Found 45/50 on supplier sites"
     → Confidence levels, missing items

  6. Calls enrichment API
     → AI generates descriptions, extracts attributes
     → Generates HS codes, country of origin

  7. Shows preview before apply
     → User reviews + approves (HITL gate)

  8. Applies changes
     → Updates Shopify via resolve + apply flow (Phase 8)

  9. Writes to memory:
     → TaskExecution node ("onboarding_initial_50_items")
     → LongTermPattern node ("This store: 50% from supplier X, 30% from Y...")
     → Next agent reads this for optimization
```

**Agent SDK value:**
- ✅ Natural language sequencing (no UI clicks)
- ✅ Context awareness (remembers "we're adding initial 50")
- ✅ Error recovery ("vendor not found" → fallback to web search via Firecrawl)
- ✅ Learning (detects patterns → feeds to other agents)

---

#### 2. **Sync Agent**
**Goal:** Keep Shopify catalog in sync with vendor changes.

**Existing components:**
- Webhook listener (`src/tasks/shopify_sync.py`)
- Product Data Command Center metrics (Phase 17)
- Rollback system with snapshots (Phase 17.6)

**What Agent SDK adds:**
```
Scheduled: Daily 9 AM

Sync Agent:
  1. Reads graph query:
     → "How many products changed per vendor?"
     → Via Phase 17.4 metrics API

  2. Groups by vendor
     → Reads LongTermPattern nodes
     → "Vendor A updates Tue/Thu" (learned from history)

  3. Calls sync orchestration
     → Targets vendors with scheduled updates

  4. Shows user summary
     → "Synced 127 products, 3 price changes flagged"
     → "Review these 3 before applying" (high-risk items)

  5. Applies changes with verification
     → Calls governance gates (kill_switch, field_policy)
     → Creates snapshots for rollback

  6. Learns:
     → Detects "Vendor B is failing" → writes as LongTermPattern
     → Next sync will avoid/retry Vendor B intelligently
```

**Agent SDK value:**
- ✅ Scheduled pattern learning
- ✅ Risk-aware decision making (human-in-loop for price changes)
- ✅ Fault tolerance (learns why syncs fail, adapts)

---

#### 3. **Data Quality Agent**
**Goal:** Answer "What's wrong with my catalog?" conversationally.

**Existing components:**
- Search API (Phase 11)
- Resolution engine (Phase 8)
- Oracle verification framework (Phase 13.2)

**What Agent SDK adds:**
```
User: "Why do some products have no images?"

Data Quality Agent:
  1. Searches graph:
     → "Products where image_url IS NULL"
     → Calls Phase 11 search endpoint

  2. Groups failures by root cause
     → "Vendor didn't scrape images (confidence: 0.85)"
     → "Image URL expired (8 products)"
     → "Enrichment pipeline skipped (no description text)"

  3. Shows user dashboard
     → "12 missing images: 8 supplier-side, 4 pipeline gaps"

  4. Offers fixes
     → "I can re-scrape Vendor A (might take 5 min)"
     → "Or use placeholder + note for human review"

  5. Executes chosen fix
     → Calls scrape task (Phase 2.1)
     → Calls enrichment pipeline (Phase 2.2)

  6. Learns:
     → "Vendor A's image selectors changed"
     → Writes to LongTermPattern for scrape agent
```

**Agent SDK value:**
- ✅ Root cause analysis (combines graph + Oracle + LLM reasoning)
- ✅ Proactive recommendations
- ✅ Conversational HITL (user picks fix, not just reports problem)

---

#### 4. **Compliance Agent**
**Goal:** Audit catalog changes, enforce governance, enable rollback.

**Existing components:**
- Approval queue (Phase 15.11b)
- Audit logs (Oracle framework, Phase 13.2)
- Rollback snapshots (Phase 17.6)

**What Agent SDK adds:**
```
User: "Show me all price changes from last 7 days"

Compliance Agent:
  1. Queries audit trail
     → Calls Phase 17.4 metrics API
     → Filters by price changes

  2. Highlights governance gaps
     → "3 prices changed without approval"
     → "1 change violated field_policy threshold"

  3. Shows forensic snapshot
     → "Product SKU 12345: $50 → $52"
     → "Applied by: vendor_sync_job on 2026-03-09"
     → "Previous value: $48 (changed on 2026-03-05)"

  4. Offers rollback
     → "Revert to $50 (2 days ago)?"
     → Calls Phase 17.6 rollback executor

  5. Logs compliance action
     → Writes audit event
     → TaskExecution node for compliance tracking
```

**Agent SDK value:**
- ✅ Forensic investigation (pulls from audit log + snapshots)
- ✅ Governance enforcement (reads kill_switch + field_policy)
- ✅ Compliance reporting (can generate audit reports)

---

#### 5. **Pattern Learning Agent** (Background)
**Goal:** Learn from all agent executions; personalize future behavior.

**Existing components:**
- TaskExecution nodes (Phase 16, recently added)
- Episodic layer (empty, ready for Agent SDK)
- LongTermPattern nodes (Aura)

**What Agent SDK adds:**
```
Background: Daily 2 AM (or after every 10 tasks)

Pattern Learning Agent:
  1. Reads TaskExecution nodes
     → Past 7 days of agent executions
     → Execution time, success rate, cost

  2. Detects patterns:
     → "This user always filters SKUs by price > $50"
     → "This vendor's scraper fails on Thu (timezone issue?)"
     → "Onboarding takes 15 min avg; this user took 3 min (power user)"

  3. Writes LongTermPattern nodes:
     → user_price_preference: min_50
     → vendor_X_failure_pattern: thursday_pst
     → user_tier_implicit: power_user

  4. Updates agent instructions:
     → Sync Agent reads patterns on next run
     → Sync Agent now skips "price > $50" filter (learned)
     → Onboarding Agent shows advanced mode to power users

  5. For higher tiers:
     → Tier 2: Daily patterns → personalized recommendations
     → Tier 3: Hourly patterns → cost optimization (save $X/week)
     → Suggests workflows: "Your Tue/Thu pattern = 20% cheaper if scheduled"
```

**Agent SDK value:**
- ✅ Automatic personalization (no manual config needed)
- ✅ Tier-based monetization (Tier 3 pays for learning insights)
- ✅ System feedback loop (learning improves all agents)

---

## Layer 2: How Agent SDK Calls Existing v1.0

### Request Path: Agent → Backend API → Job Queue → Task Execution

```
Agent SDK Call:
   User asks Onboarding Agent: "Add my 50 products"
   ↓
Orchestrator routes to Onboarding Agent
   ↓
Onboarding Agent.execute():
   1. Call backend ingest API
      POST /api/v1/ingest
      {"shopify_store_id": "...", "scope": "all_products"}
      ← Returns ingest_job_id

   2. Poll job status
      GET /api/v1/jobs/{ingest_job_id}
      ← Returns: "ingest_job running, 50 products validated"

   3. Show progress to user
      "Found 50 products in Shopify (8 enriched, 42 pending)"

   4. Trigger scrape for missing data
      POST /api/v1/scrape
      {"skus": ["123", "124", ...], "vendors": ["supplier_a", "supplier_b"]}
      ← Returns scrape_job_id

   5. Poll scrape completion
      GET /api/v1/jobs/{scrape_job_id}
      → 45/50 found on supplier sites

   6. Trigger enrichment
      POST /api/v1/enrichment
      {"product_ids": [5, 7, 12, ...], "strategy": "full"}
      ← Returns enrichment_job_id

   7. Write execution to graph
      POST /api/v1/graph/task-execution
      {
        "agent_name": "OnboardingAgent",
        "skill_name": "product_initialization",
        "outcome": "success",
        "duration_seconds": 145,
        "metadata": {"products_added": 50, "success_rate": 0.9}
      }
      → Increments SkillDef.trigger_count in Aura

   8. Write pattern to graph
      POST /api/v1/graph/long-term-pattern
      {
        "user_id": "user_42",
        "pattern_type": "initialization_batch_size",
        "value": 50,
        "confidence": 0.95
      }
```

### Key: Agent SDK makes **blocking calls to existing APIs**

Your v1.0 already has:
- ✅ Job orchestration (Celery queues)
- ✅ Tier routing (Phase 12 gates)
- ✅ Streaming responses (SSE from Phase 9)
- ✅ HITL approval (Phase 15.11)
- ✅ Governance gates (kill_switch, field_policy)

Agent SDK just wraps these in conversation + memory.

---

## Implementation Priority (What to Build First)

### **Phase A: Foundation (2 weeks)**
**Goal:** Get Agent SDK → Backend integration working

1. **API audit**
   - What endpoints exist?
   - What auth do they need?
   - What can Agent SDK call safely?
   - Document: `docs/AGENT_SDK_API_SURFACE.md`

2. **Authorization model**
   - How does Agent SDK authenticate to your backend?
   - Per-vendor isolation?
   - Rate limits per tier?
   - Document: `docs/AGENT_PERMISSIONS.md`

3. **Domain context**
   - What should agents know about Shopify, vendors, enrichment?
   - What's a "good" price change vs "bad"?
   - What fields are immutable?
   - Document: `docs/AGENT_DOMAIN_CONTEXT.md`

4. **Onboarding Agent (MVP)**
   - Single agent: walk user through initial 50 SKU setup
   - Calls existing ingest → scrape → enrich APIs
   - No memory yet (v0)
   - Test: Agent completes onboarding in 5 conversational turns

**Output:** Chatbot that can start a user's journey

---

### **Phase B: Multi-agent + Memory (4 weeks)**
**Goal:** Add domain-specific agents + pattern learning

1. **Domain agents**
   - Sync Agent
   - Data Quality Agent
   - Compliance Agent

2. **Memory integration**
   - Agents write TaskExecution nodes after each task
   - Pattern Learning Agent runs hourly/daily
   - LongTermPattern nodes influence future agent behavior

3. **Error recovery**
   - What happens when scrape fails? (fallback to web search)
   - What happens when enrichment times out? (partial results + retry hint)
   - What happens when Shopify API rate-limits? (backoff + reschedule)

**Output:** Multi-agent system with learning loop active

---

### **Phase C: Tier-based Features (2 weeks)**
**Goal:** Monetize via personalization + optimization

1. **Tier 1 (Free):**
   - Conversational chat interface (no learning)
   - Single query per request (no memory)

2. **Tier 2 ($99/mo):**
   - Daily pattern learning
   - Personalized recommendations
   - Cost transparency

3. **Tier 3 ($299/mo):**
   - Hourly pattern learning
   - Predictive scheduling (optimal sync times)
   - Cost optimization suggestions
   - Custom workflow orchestration

**Output:** Tiered SaaS features ready for Stripe billing

---

## File Locations (Reference)

### Backend APIs (Agent SDK will call these)
```
src/api/v1/
  ingest.py           ← Shopify ingestion
  scrape.py           ← Vendor scraping
  enrichment.py       ← Product enrichment
  resolution.py       ← Product resolution
  apply.py            ← Approved changes
  search.py           ← Product discovery
  chat.py             ← Streaming chat
  graph/              ← Knowledge graph endpoints
  approvals.py        ← Approval queue
```

### Background Jobs (Orchestrated by Agent SDK)
```
src/tasks/
  ingest.py           ← Ingest job
  scrape_jobs.py      ← Scrape job
  enrichment.py       ← Enrichment job
  resolution_apply.py ← Apply job
  chat_bulk.py        ← Bulk orchestration
  shopify_sync.py     ← Shopify listener
```

### Knowledge Graph
```
src/graph/
  query_interface.py  ← Agent SDK queries go here
  write_task_execution.py ← Write TaskExecution nodes
```

### Agent System (Soon)
```
.claude/agents/
  commander.md        ← Already exists; spawns Leads
  orchestrator.md     ← New; routes user queries
  onboarding.md       ← New; Phase A agent
  sync.md             ← New; Phase B agent
  data_quality.md     ← New; Phase B agent
  compliance.md       ← New; Phase B agent
  pattern_learning.md ← New; Phase B agent (background)
```

---

## Next Steps

1. **Read your API endpoints**
   ```bash
   cat src/api/v1/*.py | grep "^@"
   ```
   → Understand what's callable

2. **Check auth model**
   ```bash
   grep -r "requires_tier\|requires_auth" src/api/
   ```
   → Understand auth boundaries

3. **Create `docs/AGENT_SDK_API_SURFACE.md`**
   → List all endpoints + params + required auth + tier gates

4. **Create `docs/AGENT_PERMISSIONS.md`**
   → Define who (which agent) can call what

5. **Create `docs/AGENT_DOMAIN_CONTEXT.md`**
   → Encode business rules (Shopify limits, immutable fields, etc.)

6. **Pick Onboarding Agent as first target**
   → Wire it to existing ingest → scrape → enrich flow

---

## FAQ

**Q: Do I have to rewrite my scrape/ingest/enrichment code?**
A: No. Agent SDK calls your existing APIs. The APIs already exist and work.

**Q: How does Agent SDK know about vendor strategies?**
A: From Phase 2.1 YAML configs + graph queries. Agents can query Neo4j for "what scrapers do we have" and "which one succeeded on this vendor before?"

**Q: What if Shopify API rate-limits during a scrape?**
A: Your existing scrape task has retry logic. Agent SDK can poll job status and show user "backing off, will retry in 5 min" conversationally.

**Q: Can Agent SDK write directly to the database?**
A: No. Agent SDK only calls your APIs. Your APIs enforce governance gates (kill_switch, field_policy, etc.). This is safer.

**Q: How does memory survive across user sessions?**
A: LongTermPattern nodes in Aura. When user logs back in, agents query Aura for patterns → load into working memory → use throughout session.

**Q: How much will pattern learning cost?**
A: Graph queries are cheap (stored in Neo4j locally). LLM calls to detect patterns: ~$0.02/day per user. Tier 2/3 pays for this.

