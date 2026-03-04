# Priority 2 Context (GSD)

Date: 2026-03-03
Scope: Priority 2 - Deploy to Dokploy for E2E Testing
Canonical references:
- .planning/NEXT_TASKS.md
- docs/NEXT_PHASE_PLAN.md
- .planning/ROADMAP.md
- .planning/STATE.md

## Problem Statement
Priority 2 is currently `PARTIAL`: local readiness exists, but Dokploy deployment validation and evidence closure are missing.

## Current Verified State
- Local stabilization complete: `python -m pytest tests/ -x --tb=short -q` => 903 passed, 2 skipped.
- Playwright framework exists:
  - frontend/playwright.config.ts
  - frontend/tests/e2e/chat.e2e.ts
  - frontend/tests/e2e/enrichment.e2e.ts
  - frontend/tests/e2e/job-progress.e2e.ts
- Historical/local browser artifacts exist in reports/meta and test-results.

## Gap To Close
Not yet demonstrated in a Dokploy environment:
- Full stack deployment verification (frontend/backend/redis/postgres/neo4j/celery).
- Production-like smoke checks with real deployment URLs.
- E2E user workflow evidence from deployed environment.
- Sentry event IDs and remediation-routing proof from deployed runtime.
- Required governance evidence package under reports/future-production-refinement/priority-2-dokploy-e2e/.

## Objective
Close Priority 2 to `GREEN` by executing Dokploy deployment verification end-to-end with auditable evidence and governance-compliant reports.

## In Scope
- Dokploy preflight readiness checks.
- Service deployment mapping and rollout sequence.
- Smoke + E2E + incident/remediation validation.
- Evidence artifact generation and gate documentation.

## Out of Scope
- New feature development.
- Large refactors.
- Priority 3 memory-system implementation.

## Constraints
- Use binary gate outcomes (`GREEN`/`RED`).
- Follow governance artifact rules and report contract.
- Keep the plan auditable and KISS-oriented.
- Prefer existing stack definitions from docker-compose.yml and .env.example.

## Acceptance Criteria
Priority 2 is `GREEN` only when all are true:
1. Core services are deployed and healthy in Dokploy.
2. End-to-end user flow succeeds (chat -> dry-run -> approval -> apply in test store).
3. Sentry receives runtime issue data from deployed services.
4. At least one remediation route is observed and logged.
5. Required reports exist and are complete in reports/future-production-refinement/priority-2-dokploy-e2e/.

## Evidence Targets
- reports/future-production-refinement/priority-2-dokploy-e2e/self-check.md
- reports/future-production-refinement/priority-2-dokploy-e2e/review.md
- reports/future-production-refinement/priority-2-dokploy-e2e/structure-audit.md
- reports/future-production-refinement/priority-2-dokploy-e2e/integrity-audit.md
- Supporting run artifacts (smoke, e2e, incident) referenced from the above.

## Open Questions To Resolve During Execution
- Final Dokploy ingress topology (nginx in-app vs platform ingress only).
- Exact deployed URLs used for smoke and E2E.
- Safe incident simulation method in deployed environment.

## Discussion Evidence
- questions_answered: 4
- areas_discussed:
  - Priority ordering and scope control
  - Priority 2 re-verification baseline
  - GSD workflow requirement
  - Required artifact chain (context -> plan -> alignment -> research -> verification)

### Explicit User Answers Captured
1. Q: Should Dokploy deployment happen before local remediation work?
   A: No. Local fixes come first; Dokploy comes after that baseline.
2. Q: While memory work is active, what should be progressed from NEXT_TASKS?
   A: Proceed with only item 1 initially, then continue with Priority 2 re-verification/planning.
3. Q: Should Priority 2 status be re-verified rather than assumed complete?
   A: Yes. Re-verify what has actually been done.
4. Q: Which workflow and output sequence should be used now?
   A: Use GSD, persist context in context.md, create plan, verify plan-context alignment, run research (Context7 + Playwright + Firecrawl + Perplexity), then verify research.
