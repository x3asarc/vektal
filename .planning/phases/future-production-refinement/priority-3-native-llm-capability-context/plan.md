# Priority 3 Plan (GSD)

Date: 2026-03-04
Input context: .planning/phases/future-production-refinement/priority-3-native-llm-capability-context/context.md

## Plan Intent
Deliver a production-safe native conversational fallback that stays grounded in system capabilities and uses a low-cost provider path by default.

## Gate Model
- `GREEN`: all acceptance criteria and evidence artifacts complete.
- `RED`: any missing safety/test/report requirement.

## Wave 0 - Evidence Initialization
Goal: Prepare governance and execution evidence paths.

Tasks:
1. Create `reports/future-production-refinement/priority-3-native-llm-capability-context/`.
2. Create required reports:
   - `self-check.md`
   - `review.md`
   - `structure-audit.md`
   - `integrity-audit.md`
3. Create run evidence notes:
   - `run-log.md`
   - `chat-fallback-tests.md`
   - `provider-cost-notes.md`

Exit criteria:
- All report placeholders exist.

## Wave 1 - Capability Packet Contract
Goal: Finalize and enforce capability-context schema for fallback prompts.

Tasks:
1. Define canonical capability packet fields for runtime/tool/infra context.
2. Enforce serialization and max-size guards.
3. Add backend tests for packet completeness and stable formatting.

Exit criteria:
- Capability packet contract is test-covered and stable.

## Wave 2 - Native Fallback Behavior
Goal: Improve user-facing fallback quality for non-operational chat intents.

Tasks:
1. Add anti-repetition response guardrails.
2. Add conversational "getting started" guidance for uncertain intents.
3. Ensure action-safety constraints remain explicit when needed.

Exit criteria:
- Unknown intent no longer returns repetitive or command-only phrasing.

## Wave 3 - Low-Cost Model Policy
Goal: Pin low-cost default with deterministic fallback behavior.

Tasks:
1. Define default OpenRouter model and fallback model in env/config.
2. Add timeout/retry/rate-limit handling policy for fallback path.
3. Add tests for degraded-mode user messages on provider failure.

Exit criteria:
- Cost-aware policy is explicit, configurable, and test-covered.

## Wave 4 - Frontend Verification Loop
Goal: Verify real UX outcome in deployed frontend.

Tasks:
1. Run authenticated Playwright chat checks for unknown-intent prompts.
2. Use Firecrawl snapshot/crawl evidence to confirm visible behavior.
3. Confirm no duplicate assistant messages and clear first-step guidance.

Exit criteria:
- Deployed UI reflects expected native fallback behavior.

## Wave 5 - Governance Closure
Goal: Close Priority 3 with binary outcome and complete evidence.

Tasks:
1. Complete all four required reports.
2. Record gate decision (`GREEN`/`RED`) with evidence links.
3. Sync `.planning/STATE.md` and `.planning/NEXT_TASKS.md`.

Exit criteria:
- Reports complete and gate decision explicit.
