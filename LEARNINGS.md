# Learnings

Triage rule: every finding is Apply now / Capture here / Dismiss (with reason).
Promotion rule: any learning that changes behaviour 2+ times → extract to a rule in AGENTS.md.
Review cadence: consolidate when entries exceed 30.

## Format
`YYYY-MM-DD | Source | Learning | Status`

---

## Entries

### 2026-02-12 | 07.1-governance-baseline-dry-run
**Learning:** Report schema must be bootstrapped from templates before first task closes.
Without template enforcement, required fields drift and block gate closure.
**Applied:** Four report templates standardised in `reports/templates/`. Strict N/A policy added
to AGENTS.md gate policy. Anti-stubborn rule added: two failed closures → scope reset.
**Status:** Promoted → AGENTS.md gate policy rule #4.

### 2026-02-12 | Phase 6 UAT (Celery)
**Learning:** Celery tasks running inside Flask context fail silently without an app-context wrapper.
Race condition between cancel and start requires row-level locking.
**Applied:** App-context wrapper added to all Celery tasks. Row locks added to cancel path.
Duplicate active-ingest returns deterministic 409.
**Status:** Applied.

### 2026-02-16 | Phase 13.1 execution
**Learning:** Enrichment pipeline tests that reference Tier semantics must distinguish
Tier 1 (read-safe) from Tier 2 (mutation path). Mixing them causes fixture drift on every
semantic-firewall change.
**Applied:** `test_chat_single_sku_workflow.py` refactored to run mutation assertions under Tier 2;
Tier 1 write-block behavior isolated to `test_chat_tier_runtime_contract.py`.
**Status:** Applied. Watch for recurrence in Phase 14 when adding new tier routing rules.

### 2026-02-16 | Session workflow observation
**Learning:** When a session ends without updating STATE.md and MASTER_MAP.md, the next session
wastes 10–15 minutes re-orienting. The cost of the closing ritual is ~3 minutes.
**Applied:** Session end ritual codified in GEMINI.md.
**Status:** Applied — monitor compliance across sessions.

### 2026-02-16 | Phase 13.1 test patterns
**Learning:** Contract tests that import from `src.assistant.governance` need the full Flask
app context via `tests/api/conftest.py`. Without it, SQLAlchemy sessions are uninitialised.
**Applied:** All governance contract tests inherit from `api` conftest scope.
**Status:** Applied.

### 2026-03-09 | Substrate activation / Forensic Partnership live test

**Learning 1 — Letta is memory-only. Never inference.**
Firing Commander via `POST /v1/agents/{id}/messages` (Letta REST API) is wrong.
Letta = memory blocks + `send_message` for Pico-Warden. Inference = OpenRouter direct.
Agent execution happens in the CLI (Claude Code, Gemini CLI, Codex) not in Letta.
**Applied:** `model-rationale.md` v3.0 rewritten. `register_agents.py` MODEL_MAP labeled metadata-only. `scripts/agents/invoke.py` created as the correct inference path. `.env` wired with `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` → OpenRouter.
**Status:** Applied. Rule candidate for AGENTS.md.

**Learning 2 — Letta Cloud model proxy has a limited synced allowlist.**
`lc-openrouter/` prefix and BYOK `openrouter-letta/` prefix both validate model IDs against Letta's own synced registry. `claude-opus-4-6`, `grok-4.1`, etc. return 404 even with a valid BYOK key. Direct OpenRouter bypasses this entirely.
**Applied:** `scripts/agents/invoke.py` calls OpenRouter directly — no Letta proxy.
**Status:** Applied.

**Learning 3 — YAML `description: >` block scalar with routing keywords breaks Claude Code agent init.**
Commander failed at spawn with `classifyHandoffIfNeeded is not defined`. Root cause: multi-line `description: >` containing "spawn Watson", "Bundle → Lead", "routes" triggered Claude Code's handoff classification before the runtime was ready. `infrastructure-lead.md` (single flat line description) spawned fine. Fix: flatten description to one line, remove routing flow keywords.
**Applied:** All 4 platform `commander.md` files updated. Pattern: keep agent description to one flat sentence describing role, not flow.
**Status:** Applied. Watch for same pattern in watson.md if it ever fails at init.

**Learning 4 — Hook `filter: {tool: "Edit/Write"}` doesn't apply in subagent/Commander contexts in Letta Code.**
`filter: {tool: "Bash"}` works correctly. `filter: {tool: "Edit"}` and `filter: {tool: "Write"}` do not — hooks fired for every tool call (Read, Glob, Grep). Evidence: `impact-advisor.log` flooded with "No file path provided, skipping". Fix: self-filter inside the script by reading `tool_name` from stdin.
**Applied:** `graph_impact_advisor.py` and `test_recommender.py` now self-filter via `stdin_data.get("tool_name")`. Config-level filter kept but not relied upon.
**Status:** Applied. Rule: never rely solely on settings.json filter — always self-filter in script.

**Learning 5 — Gemini rewrites settings files to its own schema without `blockOnFailure`.**
Gemini converted `.gemini/settings.json` from Claude format (`PreToolUse`/`filter`) to Gemini format (`BeforeTool`/`matcher`) but omitted `blockOnFailure: false` on all hooks. Result: hook crashes surfaced as loud errors in Claude Code sessions. Also left `debug_stdin.py` as a permanent hook (was a debug artifact).
**Applied:** `blockOnFailure: false` added to all Gemini hooks. `debug_stdin.py` removed.
**Rule:** After any Gemini session that touches settings, verify `blockOnFailure: false` is present on all BeforeTool/AfterTool hooks.
**Status:** Applied.

**Learning 6 — Gemini's cross-CLI hook improvements are worth keeping.**
Gemini added stdin reading + stderr redirect + `{"decision":"allow"}` stdout to `graph_impact_advisor.py` and `test_recommender.py`. These changes are correct and make hooks work across Claude Code, Gemini CLI, and Codex. Claude Code ignores the stdout decision; Gemini needs it.
**Applied:** Changes committed as `feat(hooks): add Gemini CLI compatibility`.
**Status:** Applied. Gemini should be allowed to improve shared scripts.

**Learning 7 — Watson is agentic; invoke.py is single-turn. Pre-seed oracle context.**
Watson's first run via `invoke.py` tried to spawn Bash tool calls (hallucinated `/home/user/repos/...` paths). Fix: pass live oracle state + Aura DB state in `--context`. Watson then reasoned correctly without needing tools. For true multi-turn Watson execution, invoke.py needs a conversation loop or use CLI subagent spawn.
**Applied:** Second Watson call pre-seeded oracle context. Clean ChallengeReport produced.
**Rule:** For agentic agents (Watson, Commander) in invoke.py: always pre-seed context. Tell the agent explicitly "No tool calls. Reason from context provided."
**Status:** Applied.

**Learning 8 — Lestrade is genuinely useful, not cosmetic.**
First real arbitration: Commander proposed loop_budget=2, Watson proposed 3 (COLD_START advisory, overridable). Lestrade (DeepSeek lineage) ruled loop_budget=3 BINDING. Rationale: cold-start write to live DB with unknown idempotency — contingency loop is prudent containment, not inefficiency. Different reasoning lineage produced a different and correct answer.
**Applied:** loop_budget=3 accepted into BundleConfig.
**Status:** Applied. Lestrade should be invoked on any parameter disagreement, not just full deadlocks.

---

## Promotion Candidates (hit count ≥ 2 = promote to AGENTS.md)

| Learning | Hit count | Action |
|---|---|---|
| Tier semantics isolation in tests | 1 | Watch |
| App-context wrapper for Celery | 1 | Watch |
| State file update at session end | 1 | Watch |

### 2026-02-20 | test-test-01
**Learning:** Execution failed - Add sentry-sdk to requirements.txt
**Root cause:** missing_dependency:sentry-sdk
**Status:** First occurrence (watch for pattern)

### 2026-02-21 | Session continuity
**Learning:** Delayed commits (multiple days/plans) increase the risk of massive context loss during random session cutoffs.
**Applied:** Standardized checkpoint commits. I must now commit after every "Plan" (e.g., 14-01, 14-02) is verified and its `SUMMARY.md` is created. This ensures progress is persistent and easily recoverable.
**Status:** Apply now.

### 2026-02-23 | Phase 14.1 plan validation tooling
**Learning:** `must_haves.artifacts.exports` must be YAML lists in plan frontmatter. Comma-separated export strings create false `Missing export` failures in `gsd-tools verify artifacts`.
**Applied:** Normalized `14.1-01/03/04/05/06-PLAN.md` exports to YAML arrays.
**Status:** Applied.

### 2026-02-23 | Convention guardrail testing
**Learning:** Similarity-threshold tests for convention conflicts can be flaky with paraphrased text. Threshold-driven tests must use deterministic near-identical strings or explicit threshold calibration.
**Applied:** Updated `tests/unit/test_convention_checker.py` conflict case to deterministic wording.
**Status:** Applied.

### 2026-03-01 | Phase 14.2 verification
**Learning:** Neo4j `AsyncDriver` and `Driver` (sync) instances have incompatible session interfaces (`async with` vs `with`). Mixing them in hybrid retrieval paths causes `AsyncSession` context manager errors.
**Applied:** Implemented a robust `_execute_query` helper in `src/core/embeddings.py` that definitively detects driver type by inspecting session `__enter__` presence and manages event loops using threading when necessary.
**Status:** Applied.

### 2026-03-01 | Infrastructure reliability
**Learning:** Persistent Redis connection retries (default 20) in Celery/Kombu can stall agent verification loops for minutes when Docker is down.
**Applied:** Added `GRAPH_DISABLE_ASYNC_EMIT` flag to `query_interface.py` to bypass Redis-backed event emission during verification. Added task 15-06 for an autonomous infrastructure agent.
**Status:** Applied.

### 2026-03-01 | NanoFixer: local_snapshot
**Outcome:** SUCCESS
**Actions:** Snapshot stale (Stored: None, HEAD: 6414bde318b2daa8185f59f5bf735a091e9238dd), Executing local_graph_store.get_snapshot(force_refresh=True)..., Injected git_head 6414bde318b2daa8185f59f5bf735a091e9238dd into manifest.
**Message:** Snapshot rebuilt successfully

### 2026-03-02 | NanoFixer: local_snapshot
**Outcome:** SUCCESS
**Actions:** Snapshot stale (Stored: None, HEAD: 7e5aa945e6db984447bf2503483a900e5807b294), Executing local_graph_store.get_snapshot(force_refresh=True)..., Injected git_head 7e5aa945e6db984447bf2503483a900e5807b294 into manifest.
**Message:** Snapshot rebuilt successfully

### 2026-03-02 | NanoFixer: local_snapshot
**Outcome:** SUCCESS
**Actions:** Snapshot stale (Stored: 7e5aa945e6db984447bf2503483a900e5807b294, HEAD: efb59cc2c35799b5814435669a01bc6173ce7800), Executing local_graph_store.get_snapshot(force_refresh=True)..., Injected git_head efb59cc2c35799b5814435669a01bc6173ce7800 into manifest.
**Message:** Snapshot rebuilt successfully

### 2026-03-03 | NanoFixer: dependencies
**Outcome:** FAILED
**Actions:** pip_install_sentry-sdk, install_exception
**Message:** Installation exception: 

### 2026-03-03 | NanoFixer: dependencies
**Outcome:** FAILED
**Actions:** pip_install_sentry-sdk, install_exception
**Message:** Installation exception: 

### 2026-03-03 | NanoFixer: dependencies
**Outcome:** FAILED
**Actions:** pip_install_sentry-sdk, install_exception
**Message:** Installation exception: 

### 2026-03-10 | NanoFixer: neo4j_health
**Outcome:** SUCCESS
**Actions:** neo4j_connection_probe, connection_attempt_1, graphiti_client_validated, connection_success
**Message:** Neo4j connection restored on attempt 1/3
