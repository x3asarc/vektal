# Priority 3 Context (GSD)

Date: 2026-03-04
Scope: Priority 3 - Native LLM Capability Context for Chat UX
Canonical references:
- .planning/NEXT_TASKS.md
- .planning/ROADMAP.md
- .planning/STATE.md
- docs/MASTER_MAP.md

## Problem Statement
The chat experience is operational but still feels command-router-first in fallback situations. When user intent is unclear, responses can become repetitive, overly operational, or disconnected from user expectations of a native assistant experience.

## Current Verified State
- Frontdoor login/dashboard access has been restored in production.
- OpenRouter credentials were rotated and reset in runtime environment.
- Unknown-intent fallback behavior was improved in backend chat routing.
- Capability-aware prompt context work has started in chat backend runtime.

## Gap To Close
We still need a governed, low-cost, production-grade conversational fallback that:
- responds naturally like a modern assistant,
- remains grounded in actual platform capabilities and constraints,
- does not break action safety gates (Shopify mutate actions, approvals, auth),
- handles provider/rate-limit failures gracefully.

## Objective
Define and execute a lightweight native-LLM fallback layer for chat that preserves operational safety while improving conversational quality and onboarding guidance.

## In Scope
- Capability packet contract for chat prompts (runtime/tool/infra constraints).
- Unknown-intent fallback behavior and anti-repetition guardrails.
- OpenRouter model policy with cost-aware default and safe fallback model.
- User-facing "getting started" guidance without command-only tone.
- Verification loop across API tests and frontend E2E chat behavior.

## Out of Scope
- New product-resolution features.
- Full agent architecture redesign.
- Memory-system redesign (already covered by prior completed phases).

## Constraints
- Keep existing tier/action safety boundaries intact.
- Preserve governance gate model (`GREEN`/`RED`) and report requirements.
- Keep implementation KISS and auditable.
- Prioritize low-cost inference path by default.

## Acceptance Criteria
Priority 3 is `GREEN` only when all are true:
1. Unknown/non-operational chat messages get natural, non-repetitive assistant responses.
2. Fallback responses are grounded in a capability packet (what system can/cannot do now).
3. OpenRouter low-cost model policy is explicit and configurable per environment.
4. Rate-limit/provider failures degrade gracefully with user-safe messaging.
5. Regression tests cover fallback behavior, capability context, and no duplicated assistant messages.
6. Required governance reports exist in `reports/future-production-refinement/priority-3-native-llm-capability-context/`.

## Evidence Targets
- reports/future-production-refinement/priority-3-native-llm-capability-context/self-check.md
- reports/future-production-refinement/priority-3-native-llm-capability-context/review.md
- reports/future-production-refinement/priority-3-native-llm-capability-context/structure-audit.md
- reports/future-production-refinement/priority-3-native-llm-capability-context/integrity-audit.md

## Open Questions To Resolve During Execution
- Which exact low-cost OpenRouter default model should be pinned for production fallback?
- What response-style contract best balances friendliness with operational precision?
- Should capability context include real-time service health snapshot or static role summaries only?
- What token/cost ceiling should trigger terse-mode responses automatically?

## Discussion Evidence
- questions_answered: 6
- areas_discussed:
  - Native assistant UX expectation vs command-router tone
  - Lightweight LLM fallback preference
  - Cost sensitivity and OpenRouter low-cost model preference
  - Capability grounding from infra/runtime context (nginx, celery, backend, redis)
  - Production error behavior (409/rate-limit/confusing prompts)
  - Keep this as planned next phase context under future production refinement

### Explicit User Answers Captured
1. Q: Should fallback feel native like ChatGPT/Gemini instead of command-only prompts?
   A: Yes.
2. Q: Should a lightweight LLM fallback be the primary unknown-intent behavior?
   A: Yes.
3. Q: Is lower cost a priority for provider/model selection?
   A: Yes, prefer cheaper OpenRouter option.
4. Q: Should the assistant be aware of platform capabilities/constraints at runtime?
   A: Yes, include context such as nginx/celery and related runtime roles.
5. Q: Should we persist this as the next planned phase in `.planning`?
   A: Yes.
6. Q: Should this be treated as context-first planning before further heavy patching?
   A: Yes.
