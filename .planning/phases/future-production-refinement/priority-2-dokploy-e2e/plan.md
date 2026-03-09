# Priority 2 Plan (GSD)

Date: 2026-03-04
Input context: .planning/phases/future-production-refinement/priority-2-dokploy-e2e/context.md

## Plan Intent
Execute Dokploy deployment verification end-to-end and close Priority 2 with governance-complete evidence.

## Gate Model
- `GREEN`: all gates pass and evidence is complete.
- `RED`: any gate fails or required evidence missing.

## Wave 0 - Evidence + Workspace Initialization
Goal: Establish auditable evidence structure before execution.

Tasks:
1. Ensure evidence directory exists:
   - reports/future-production-refinement/priority-2-dokploy-e2e/
2. Create required governance reports:
   - self-check.md
   - review.md
   - structure-audit.md
   - integrity-audit.md
3. Create operational evidence notes:
   - run-log.md
   - smoke-results.md
   - e2e-results.md
   - incident-simulation.md

Exit criteria:
- All files created and linked in run-log.md.

## Wave 1 - Dokploy Preflight Readiness
Goal: Confirm deployment prerequisites are complete.

Tasks:
1. Validate Dokploy project/env target is available.
2. Record ingress topology decision in run-log.md:
   - `platform-ingress-only` (default)
   - `app-nginx-plus-platform` (only if app-level proxy behavior is required)
   - Include short justification and impacted services.
3. Validate required environment variables against .env.example:
   - SHOPIFY_API_KEY, SHOPIFY_API_SECRET
   - DB_PASSWORD
   - NEO4J_PASSWORD
   - SENTRY_DSN, SENTRY_WORKERS_DSN, NEXT_PUBLIC_SENTRY_DSN
   - SENTRY_AUTH_TOKEN, SENTRY_ORG_SLUG, SENTRY_PROJECT_SLUG
4. Confirm non-production Shopify test store for write flow.
5. Confirm migration strategy (`flask db upgrade` on backend startup).

Exit criteria:
- Preflight checklist completed in run-log.md with no unknown blockers.

## Wave 2 - Deployment Rollout
Goal: Deploy stack in safe dependency order.

Order:
1. postgres, redis, neo4j
2. backend
3. celery_worker, celery_scraper, celery_assistant
4. frontend
5. optional: flower / nginx (based on ingress design)

Tasks:
- Record deployed service IDs/names and URLs.
- Capture health state snapshots.

Exit criteria:
- All core services report healthy.

## Wave 3 - Smoke Verification
Goal: Validate core availability and connectivity.

Checks:
1. Backend health endpoint returns success.
2. Chat sessions endpoint responds.
3. Frontend route renders and can reach backend.
4. Dokploy service health checks are green for frontend/backend/workers.
5. Rollback/update policy is configured and recorded:
   - Healthcheck JSON
   - Update config JSON with rollback action

Evidence:
- smoke-results.md with URL, status code, timestamp, result.
- run-log.md includes captured healthcheck/update-config JSON used for deployment safety.

Exit criteria:
- All smoke checks pass.

## Wave 4 - E2E User Flow Validation
Goal: Validate product user workflow in deployed environment.

Flow:
1. Run existing Playwright deployed baseline first:
   - `PLAYWRIGHT_BASE_URL=<frontend_url> npm --prefix frontend run test:e2e`
2. Open app and authenticate.
3. Run one chat operation producing dry-run.
4. Validate approval queue appears for reviewable actions.
5. Apply one approved action against test store.
6. If baseline suite does not cover the full approval/apply chain, add one targeted E2E scenario for:
   - `chat -> dry-run -> approval queue -> apply`

Evidence:
- e2e-results.md with scenario steps, pass/fail, screenshots/links.
- Include Playwright run summary and artifact references (HTML report/trace/screenshots).

Exit criteria:
- End-to-end flow passes without manual DB patching.

## Wave 5 - Incident + Remediation Validation
Goal: Verify production observability and self-heal path.

Flow:
1. Trigger one reversible Celery incident task with no data side effects (intentional exception).
2. Confirm Sentry event captured from worker runtime (record event IDs).
3. Confirm classification/remediation route executed for the captured event.
4. Confirm remediation outcome log entry and recovery state.
5. Remove/disable the test incident trigger after verification.

Evidence:
- incident-simulation.md with Sentry event IDs, route evidence, outcome status.
- Include precheck note that Sentry SDK init occurs on worker startup (not task-late init).

Exit criteria:
- At least one full issue -> classification -> remediation trace captured.

## Wave 6 - Governance Closure
Goal: Close Priority 2 with required reports and binary outcome.

Tasks:
1. Fill self-check.md with completed checks and evidence refs.
2. Fill structure-audit.md and integrity-audit.md.
3. Fill review.md with two-pass timestamps:
   - pass_1_timestamp
   - pass_2_timestamp
   - plan_context_opened_at
4. Set final gate status GREEN or RED in self-check.md and .planning/NEXT_TASKS.md.

Exit criteria:
- Exactly four required reports exist and are complete.
- Gate decision is explicit and justified.

## Risks + Mitigation
1. DNS/ingress mismatch:
   - Mitigation: verify resolved host, cert, and backend reachability before E2E.
2. Missing env vars:
   - Mitigation: preflight env diff against .env.example.
3. Remediation test too destructive:
   - Mitigation: use safe, reversible incident injection and test store only.
4. Ingress misconfiguration introduces duplicate proxies:
   - Mitigation: default to platform ingress only unless app-level nginx is justified in Wave 1 decision log.

## Rollback Plan
- If any wave fails hard, mark `RED`, stop forward execution, document blocker in run-log.md, and restore previous stable deployment config.

## Command Skeleton (To Execute During Run)
1. Dokploy deploy commands: TBD per Dokploy target/environment.
2. Smoke probes:
   - curl <frontend_url>
   - curl <backend_url>/health
   - curl <backend_url>/api/v1/chat/sessions
3. Frontend E2E (deployed URL):
   - PLAYWRIGHT_BASE_URL=<frontend_url> npm --prefix frontend run test:e2e

## Deliverables
- Context: .planning/phases/future-production-refinement/priority-2-dokploy-e2e/context.md
- Plan: .planning/phases/future-production-refinement/priority-2-dokploy-e2e/plan.md
- Evidence bundle: reports/future-production-refinement/priority-2-dokploy-e2e/
</frontend_url></frontend_url>