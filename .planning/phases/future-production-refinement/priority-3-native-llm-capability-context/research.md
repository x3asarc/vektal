# Priority 3 Research (GSD)

Date: 2026-03-04
Context: .planning/phases/future-production-refinement/priority-3-native-llm-capability-context/context.md

## Research Intent
Capture execution-time research targets for a low-cost, capability-grounded chat fallback without blocking immediate planning continuity.

## Context7 / Primary Docs Targets
- OpenAI/OpenRouter-compatible chat completion semantics (fallback/message formatting).
- Flask request/response safety patterns for structured fallback errors.
- Playwright chat E2E assertion patterns for conversational UX regressions.

## External Validation Targets
- Firecrawl: deployed frontend crawl/snapshot to verify visible chat fallback behavior.
- Playwright: authenticated chat flow replay to confirm no duplicate responses and natural fallback.
- Perplexity (optional): model cost/latency comparison snapshot for OpenRouter model pinning.

## Contracts To Validate
1. Capability packet contract:
   - required keys,
   - optional keys,
   - serialization limits,
   - prompt placement.
2. Fallback response policy:
   - anti-repetition,
   - user-safe failure copy,
   - capability-grounded response template.
3. Cost policy contract:
   - default model id,
   - fallback model id,
   - timeout/retry policy.

## Research Completion Gate
Research is `GREEN` when:
1. Model choice is justified by cost + response quality evidence.
2. Capability packet fields are finalized with tests.
3. Degraded-mode responses are documented and test-covered.
4. Frontend-visible behavior is verified in deployed UI replay.
