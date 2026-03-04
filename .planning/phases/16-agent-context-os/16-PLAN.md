# Phase 16: Agent Context OS - Master Plan (Plain Language)

**Status**: COMPLETE (executed 2026-03-03 via `16-01` .. `16-07`)  
**Depends on**: v1.0 complete baseline (Phases 1-15)  
**Tagged**: `[developer-facing]` `[context]` `[memory]` `[graph]` `[governance]`

This document is now the as-built master reference for Phase 16 outputs.

---

## 1) One-Page Summary

This phase creates one always-fresh context system for agents.

What you get:

1. One canonical file for any new agent to start from.
2. Folder summaries so agents stop re-reading the whole repo.
3. Live memory across terminals (working, short-term, long-term).
4. Graph context attempted first, fallback second.
5. Strict lightweight behavior (minimal tokens, low latency, non-blocking hooks).

This is the control plane for context quality and efficiency.

---

## 2) Your Intent (As Implemented in This Plan)

1. Keep context practical, not theoretical.
2. Make Graphiti/Neo4j part of normal context flow, not occasional tooling.
3. Preserve speed and low token use.
4. Keep everything auditable and deterministic.
5. Give new agents instant orientation from one doc.

---

## 3) Current Reality (Why It Feels Inconsistent)

Today, graph capability exists but is not enforced everywhere:

1. Some graph paths are strong (query templates, graph tooling), but chat routing and memory retrieval still have non-graph primary paths.
2. Some graph adapter logic is placeholder/fail-open, so it can return empty even when called.
3. Runtime fallbacks (Aura/local/snapshot) are designed to keep system alive, but this also means graph may not be the active path in many turns.
4. Agent entrypoint doc is not yet the hard single source for every session.

This plan fixes that by enforcing one broker and one onboarding entrypoint.

---

## 4) Graphiti + Neo4j + Aura (Clear Roles)

Use this mental model:

1. **Neo4j**: the graph database engine (where nodes/edges/data live).
2. **Aura**: managed Neo4j deployment (cloud runtime for Neo4j).
3. **Graphiti**: the graph-memory/query library/client layer that writes/reads knowledge episodes and graph structures.

Intent alignment:

1. You want relationship-aware context ("what triggers what", "which script impacts which module", "what fires after X").
2. That is exactly graph territory and should be first-class.
3. Neo4j gives the storage + traversal engine; Graphiti gives application-level memory patterns over it.

This plan makes that relationship explicit and operationally mandatory through a single retrieval broker.

---

## 5) Target System (Simple View)

## 5.1 Single Entrypoint

Create one canonical file:

1. `docs/AGENT_START_HERE.md`

This file always includes:

1. Current phase/task/status.
2. Current blockers/next actions.
3. Top links to plans/runtime/tests.
4. Folder summary pointers.
5. Last refresh timestamp.

## 5.2 Folder Summaries

Create:

1. `docs/FOLDER_SUMMARIES.md`

Each folder row includes:

1. Purpose.
2. Top files.
3. Owner role.
4. Volatility.
5. Last verified.

## 5.3 Memory Layers

1. Working memory: per-session operational context.
2. Short-term memory: daily/task stream.
3. Long-term memory: stable project decisions/patterns.

All three are derived from append-only events.

## 5.4 Graph-First Retrieval

All context retrieval goes through one broker:

1. Attempt graph first.
2. If timeout/unavailable, fallback to local indexes/summaries.
3. Always record provenance (`graph_used`, `fallback_used`, latency).

---

## 6) Lightweight Rules (Hard Constraints)

1. Default assembled context target: `<= 2,500 tokens`.
2. Routine hard cap: `4,000 tokens`.
3. Compaction order:
   - trim low-priority retrieved snippets first;
   - summarize older history second;
   - never drop core governance constraints.
4. PreTool memory write path target: `< 20ms` local path.
5. Hooks are best-effort and never block commands.
6. Prefer stable prompt prefixes and caching-friendly structure.

---

## 7) Always-Live Update Contract

## 7.1 SessionStart

1. Hydrate memory views.
2. Rebuild `AGENT_START_HERE.md` if stale or git SHA changed.

## 7.2 PreTool

1. Append command/intent event.
2. Update session working memory.
3. Surface peer-session signal when relevant.

## 7.3 PostTool

1. Append outcome event (`success/fail`, touched files, timing class).
2. Update short-term counters.

## 7.4 SessionEnd

1. Persist final session summary and next steps.
2. Promote useful learnings to short-term.

## 7.5 TaskComplete / PhaseComplete

1. Promote validated patterns to long-term.
2. Regenerate onboarding docs.

---

## 8) Deliverables (What Must Exist)

1. `docs/AGENT_START_HERE.md`
2. `docs/FOLDER_SUMMARIES.md`
3. `docs/CONTEXT_LINK_MAP.md`
4. `.memory/events/YYYY-MM-DD.jsonl`
5. `.memory/working/*.json`
6. `.memory/short-term/*.jsonl`
7. `.memory/long-term/index.json`
8. `src/assistant/context_broker.py`
9. `scripts/context/build_agent_primer.py`
10. Session-driven refresh path (implemented):
    - `scripts/memory/session_start.py`
    - `scripts/memory/pre_tool_update.py`
11. `scripts/governance/context_os_gate.py`
12. `scripts/governance/context_os_report.py`
13. `scripts/context/verify_phase16.py`

---

## 9) Definition of Done (Binary Gate)

`GREEN` only if all are true:

1. New agent can start from one file and orient in <=2 minutes.
2. Folder summaries are present, fresh, and cover required core directories.
3. Graph-first broker is the default retrieval path with threshold metrics met.
4. Memory views are reproducible from append-only events.
5. Live updates run across lifecycle hooks.
6. Context freshness <=24h (or auto-refresh on session start).
7. Governance evidence exists per task (`self-check`, `review`, `structure-audit`, `integrity-audit`).
8. All "Owner Success Metrics" in Section 10.1 pass.

Any missing condition is `RED`.

---

## 10) Metrics (How We Know It Works)

1. New-agent warm-start time.
2. Repeated broad file-read reduction.
3. Graph attempt rate for context retrieval.
4. Fallback rate and reason.
5. Hook write success rate.
6. End-to-end context assembly latency.
7. Average context token size.

---

## 10.1) Owner Success Metrics (Non-Negotiable)

These are the exact intent metrics for this phase:

1. **Single entrypoint adoption**:
   - `AGENT_START_HERE.md` is generated and referenced first in session bootstrap.
   - Pass target: `>=95%` of new sessions start from this doc (by hook telemetry).
2. **Folder summary coverage**:
   - `FOLDER_SUMMARIES.md` covers all top-level production directories used by agents.
   - Pass target: `100%` coverage for `src/`, `scripts/`, `.planning/`, `docs/`, `tests/`, `ops/`.
3. **Graph-first context behavior**:
   - Broker attempts graph retrieval before fallback on context requests.
   - Pass target: `>=95%` graph-attempt rate on context retrieval calls.
4. **Trigger/connection visibility**:
   - Context responses can answer "what triggers what" for script flow with provenance.
   - Pass target: for a fixed test set of trigger questions, `>=90%` return linked evidence path(s).
5. **Live cross-terminal memory**:
   - Activity in terminal A is visible to terminal B without manual file reads.
   - Pass target: visibility within `<=1 command cycle` (or `<=5s` on daemon tick).
6. **Lightweight token control**:
   - Routine context assembly stays within budget.
   - Pass target: median `<=2,500` tokens, p95 `<=4,000` tokens.
7. **Low-latency non-blocking hooks**:
   - Memory hooks never block tool execution.
   - Pass target: write path p95 `<20ms` local path, blocking incidents `=0`.
8. **Freshness SLA**:
   - Context docs and materialized views remain current.
   - Pass target: stale window `<24h`, with auto-refresh at SessionStart.

---

## 11) Risks and Controls

1. Too much event noise:
   - enforce event schema + dedupe + priority tiers.
2. Graph latency/unavailability:
   - strict timeout + fail-open local fallback + telemetry.
3. Summary drift:
   - scheduled reconciliation + freshness gate.
4. Context bloat:
   - hard token budgets + compaction.
5. Multi-terminal contention:
   - append-only events + deterministic materializers.

---

## 12) Execution Sequence (Master Only)

Atomic plans were executed in this order:

1. `16-01-PLAN.md` - Event schema and append-only writer.
2. `16-02-PLAN.md` - Materializers for working/short/long.
3. `16-03-PLAN.md` - Master onboarding doc and folder summary generator.
4. `16-04-PLAN.md` - Graph-first context broker.
5. `16-05-PLAN.md` - Full lifecycle hook integration.
6. `16-06-PLAN.md` - Governance gate and runbook.
7. `16-07-PLAN.md` - Verification and closure.

Ascending execution contract:

1. No parallel execution of 16-01..16-07.
2. After each plan completes, rewrite the next plan using delivered outputs from prior plan summaries.
3. Any unresolved upstream placeholder in next plan is a blocking `RED`.
4. Canonical contract file: `16-EXECUTION-CONTRACT.md`.

---

## 13) Immediate Next Step

Consume Phase 16 contracts in active phases (starting with 15.1) so new runtime features emit canonical memory/context telemetry and remain gateable by `context_os_gate.py`.

---

## 15) Closure Evidence

1. Final summary: `.planning/phases/16-agent-context-os/16-07-SUMMARY.md`
2. Verification harness evidence:
   - `reports/meta/phase16-verification-full-2026-03-03.json`
3. Operational runbook:
   - `docs/runbooks/context-os-operations.md`
4. Journey synthesis:
   - `reports/meta/journey-synthesis-14-16.md`

---

## 14) Research Inputs Used for This Plan

1. LangGraph persistence/store patterns: https://docs.langchain.com/oss/python/langgraph/persistence
2. OpenAI prompt caching: https://platform.openai.com/docs/guides/prompt-caching
3. OpenAI agent sessions: https://openai.github.io/openai-agents-python/sessions/
4. Anthropic prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
5. Semantic Kernel history reducers: https://devblogs.microsoft.com/semantic-kernel/managing-chat-history-for-large-language-models-llms/
6. LlamaIndex memory patterns: https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/memory/
7. AutoGen memory protocol: https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/memory.html
8. MemGPT (virtual memory framing): https://arxiv.org/abs/2310.08560
9. Lost in the Middle (context ordering): https://aclanthology.org/2024.tacl-1.9/
10. Graphiti reference implementation: https://github.com/getzep/graphiti
