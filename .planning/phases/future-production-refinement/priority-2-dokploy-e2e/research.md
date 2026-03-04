# Priority 2 Research (GSD)

Date: 2026-03-04
Context: .planning/phases/future-production-refinement/priority-2-dokploy-e2e/context.md
Plan: .planning/phases/future-production-refinement/priority-2-dokploy-e2e/plan.md

## Research Intent
Answer the Priority 2 context and plan questions with tool-driven evidence, not tool health only.

## Context Questions to Resolve
1. Ingress topology: keep app nginx, or rely on Dokploy ingress only?
2. What concrete pre-E2E smoke checks and URLs must pass before user-flow runs?
3. What is a safe incident simulation that proves Sentry capture and remediation routing without data loss?
4. Are existing Playwright tests sufficient as a deployed-environment baseline for AC2?

## Tool Usage Evidence

### Context7 (primary docs)
- Playwright: `/microsoft/playwright`
  - Focus: deployed E2E config (`baseURL`, retries/workers, trace/report artifacts).
- Firecrawl: `/websites/firecrawl_dev`
  - Focus: crawl/scrape status model, polling/failure fields for evidence capture.
- Perplexity API: `/websites/perplexity_ai_api-reference`
  - Focus: request/response schema (`model`, `messages`, `search_results`, `usage`).
- Sentry Python: `/getsentry/sentry-python`
  - Focus: Celery integration startup timing and verify pattern.

### Playwright (actual project usage)
- Command executed:
  - `cmd /c npx --prefix frontend playwright --version`
  - Result: `1.58.2`
- Command executed:
  - `cmd /c npx --prefix frontend playwright test --config frontend/playwright.config.ts --list`
  - Result: 13 E2E tests in 3 files (`chat`, `enrichment`, `job-progress`).
- Code inspected:
  - `frontend/playwright.config.ts`
  - `frontend/tests/e2e/chat.e2e.ts`
  - `frontend/tests/e2e/enrichment.e2e.ts`
  - `frontend/tests/e2e/job-progress.e2e.ts`

### Firecrawl (live retrieval for current docs)
- Search evidence:
  - `.planning/debug/priority2-firecrawl-dokploy-search.json`
  - `.planning/debug/priority2-firecrawl-sentry-search.json`
- Scrape evidence:
  - `.planning/debug/priority2-firecrawl-dokploy-going-production.json`
  - `.planning/debug/priority2-firecrawl-sentry-celery-doc.json`

### Perplexity (live context synthesis)
- Script added for repeatable queries:
  - `scripts/tools/perplexity_query.py`
- Query outputs:
  - `.planning/debug/priority2-perplexity-dokploy-ingress.json`
  - `.planning/debug/priority2-perplexity-sentry-runbook.json`
  - `.planning/debug/priority2-perplexity-dokploy-incident.json`
  - `.planning/debug/priority2-perplexity-dokploy-ingress-runbook.json`

## Findings Mapped to Context + Plan

### Q1: Ingress topology decision
Decision:
- Default to Dokploy ingress only for frontend/backend if app-level nginx is not needed for custom behavior.
- Keep nginx optional fallback only when app-specific routing/proxy behavior is required.

Evidence:
- Firecrawl scrape of Dokploy "Going Production" emphasizes platform-level domain + port mapping and health/rollback controls.
- Perplexity ingress runbook output aligns with removing duplicate reverse-proxy layers when direct app listener is healthy.

Plan impact:
- Wave 1 preflight must record chosen ingress mode explicitly.
- Wave 2 rollout should not deploy optional nginx unless a documented requirement exists.

### Q2: Pre-E2E smoke contract before Wave 4
Required checks before E2E starts:
1. Frontend domain returns success over HTTPS.
2. Backend `/health` returns success from deployed URL.
3. Backend `/api/v1/chat/sessions` responds (auth status acceptable if route is protected).
4. Dokploy service healthcheck is green for core services.
5. Rollback policy is set to rollback-on-health-failure for app service.
6. Domain routes to correct app port (no stale port mapping).
7. No crash-loop/restart pattern on backend or workers.
8. Test store credentials/keys are present for the apply-step path.

Evidence:
- Firecrawl Dokploy scrape includes production guidance for:
  - health endpoint (example `/health`),
  - health check JSON,
  - update config with rollback `FailureAction: rollback`.

Plan impact:
- Directly strengthens Wave 3 exit criteria and adds auditable preconditions for Wave 4.

### Q3: Safe incident simulation for AC3/AC4
Recommended simulation:
- Use a dedicated reversible Celery task that intentionally raises an exception and has no side effects.
- Trigger once in deployed environment.
- Validate Sentry event, stack trace/task identity, and remediation routing log path.

Evidence:
- Context7 Sentry Python guidance:
  - initialize `sentry_sdk.init()` on worker startup (`celeryd_init`/`worker_init`),
  - verify by triggering intentional `ZeroDivisionError` task.
- Firecrawl Sentry Celery scrape confirms:
  - startup timing requirement for SDK init,
  - explicit verify pattern via intentional error task.
- Perplexity Sentry runbook output provides sequence:
  - prechecks -> reversible task -> validation -> cleanup/rollback.

Plan impact:
- Wave 5 can use a deterministic, low-risk incident path with concrete validation steps.

### Q4: Playwright baseline sufficiency for AC2
Assessment:
- Current suite is a valid deployed-smoke baseline (13 tests, evidence screenshots, trace-on-retry).
- It is not a full business-approval flow validator yet; current tests are mostly shell/smoke navigation and stability checks.

Evidence:
- Listed tests show coverage of chat/enrichment/jobs surface and evidence capture.
- `frontend/playwright.config.ts` already supports deployed URL via `PLAYWRIGHT_BASE_URL`.

Plan impact:
- Wave 4 should run current suite against deployed URL first.
- Then add targeted scenario extension for `chat -> dry-run -> approval -> apply` closure evidence.

## Context/Plan Alignment Matrix
| Context/Plan need | Research output | Status |
|---|---|---|
| Ingress topology decision | Dokploy ingress-only default with documented fallback | GREEN |
| Smoke gate definition | 8 concrete pre-E2E checks + rollback-health contract | GREEN |
| Safe incident simulation | Reversible Celery exception task runbook + Sentry verify steps | GREEN |
| Deployed E2E baseline | Playwright suite validated and enumerated; extension gap identified | GREEN |

## Limitations and Mitigations
1. Perplexity responses on Dokploy-specific incident design were partially sparse.
   - Mitigation: anchored incident runbook in official Sentry Celery docs via Firecrawl + Context7.
2. Firecrawl/Perplexity can require unrestricted network runs in this environment.
   - Mitigation: persistent approval pattern established (`cmd /c firecrawl`, `python scripts/tools/perplexity_query.py`).

## Immediate Actions for Execution Phase
1. Add Wave 1 checklist item: explicit ingress decision (`platform-only` vs `nginx+platform`) with justification.
2. Add Wave 3 checklist item: Dokploy healthcheck + rollback JSON captured in run-log evidence.
3. Add Wave 5 checklist item: run reversible Celery exception task and log Sentry event IDs plus remediation outcome.
4. Add Wave 4 sub-task: extend one Playwright spec for approval/apply path if current suite does not cover it end-to-end.
