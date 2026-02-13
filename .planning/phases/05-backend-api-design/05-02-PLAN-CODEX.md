---
phase: 05-backend-api-design
plan: 02
type: execute
wave: 2
depends_on: ["05-01"]
files_modified:
  - src/api/rate_limit.py
  - src/api/v1/realtime/routes.py
  - src/api/v1/jobs/routes.py
  - src/api/v1/pipeline/routes.py
  - src/api/v1/status/routes.py
  - src/app.py
  - tests/integration/test_api_rate_limit_and_sse.py
  - .planning/ROADMAP.md
autonomous: true

must_haves:
  truths:
    - "Tier-specific API rate limits are enforced for authenticated users"
    - "Rate-limit responses include clear retry/limit metadata"
    - "Frontend can subscribe to job progress via SSE endpoint"
    - "Polling fallback endpoint remains available for clients without SSE"
    - "Legacy `/api/*` paths continue to work during migration to v1"
  artifacts:
    - path: "src/api/rate_limit.py"
      provides: "Tier-based rate limiting policy and enforcement"
      exports: ["apply_rate_limit", "get_tier_limits"]
    - path: "src/api/v1/realtime/routes.py"
      provides: "SSE job progress stream endpoint"
    - path: "tests/integration/test_api_rate_limit_and_sse.py"
      provides: "Integration tests for rate limit and realtime contracts"
    - path: "src/app.py"
      provides: "Realtime and rate-limiter registration"
  key_links:
    - from: "src/api/v1/jobs/routes.py"
      to: "src/api/rate_limit.py"
      via: "request guard"
      pattern: "apply_rate_limit|get_tier_limits"
    - from: "src/api/v1/realtime/routes.py"
      to: "src/api/v1/jobs/routes.py"
      via: "job status source"
      pattern: "jobs|status"
---

<objective>
Implement production-ready API delivery behavior for Phase 5: tier rate limiting and real-time progress endpoints.

Purpose: Protect backend resources, expose predictable real-time updates to frontend clients, and complete the API runtime contract required before Phase 6/7.
Output: Tier-aware rate limiter, SSE endpoint with polling fallback, migration-safe endpoint compatibility, and integration tests.
</objective>

<execution_context>
@codexclaude/get-shit-done/workflows/execute-plan.md
@codexclaude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-backend-api-design/05-CONTEXT.md
@.planning/phases/05-backend-api-design/05-RESEARCH-CODEX.md
@.planning/phases/05-backend-api-design/05-01-PLAN-CODEX.md
@src/models/user.py
@src/app.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add tier-aware API rate limiting</name>
  <files>src/api/rate_limit.py, src/api/v1/jobs/routes.py, src/api/v1/pipeline/routes.py, src/api/v1/status/routes.py, src/app.py</files>
  <action>
Implement rate limiting that uses authenticated user's tier (`tier_1`, `tier_2`, `tier_3`) and Redis-backed counters.

Requirements:
- Define per-tier limits (Starter/Professional/Enterprise aligned to Phase 4 pricing tiers).
- Enforce limits on mutation-heavy and compute-heavy endpoints first (`/jobs`, `/pipeline/*`, realtime subscribe endpoint).
- Return `429` with structured payload plus retry metadata (`Retry-After`, limit, remaining).
- Exempt health and documentation endpoints from strict limits.

Keep implementation modular so limits can be tuned without route rewrites.
  </action>
  <verify>Trigger repeated requests in tests and confirm expected `429` behavior by tier.</verify>
  <done>Tier-based limits are enforced and observable with consistent response metadata.</done>
</task>

<task type="auto">
  <name>Task 2: Implement SSE job progress endpoint with polling fallback</name>
  <files>src/api/v1/realtime/routes.py, src/api/v1/jobs/routes.py, src/app.py</files>
  <action>
Add real-time progress endpoint using SSE for one-way streaming and keep polling fallback endpoint for broad compatibility.

Required behaviors:
- SSE endpoint under `/api/v1/realtime/jobs/<job_id>/stream` returns `text/event-stream`.
- Stream emits structured events for status/progress/error/complete.
- Keep or add polling endpoint under `/api/v1/jobs/<job_id>/status` for fallback.
- Auth is required for both endpoints and tenant ownership is enforced.

Do not add WebSocket full-duplex behavior in this phase; Phase 9 can expand transport if needed.
  </action>
  <verify>Open SSE stream in integration test client, update job status, and confirm ordered events.</verify>
  <done>Realtime stream works with authenticated sessions and polling fallback remains available.</done>
</task>

<task type="auto">
  <name>Task 3: Add integration tests and update roadmap status</name>
  <files>tests/integration/test_api_rate_limit_and_sse.py, .planning/ROADMAP.md</files>
  <action>
Create integration tests covering rate limit policy and realtime API contracts.

Test coverage must include:
- Tier-specific thresholds and response metadata.
- SSE connection setup, event payload shape, and completion behavior.
- Polling fallback correctness.
- Backward compatibility for key legacy `/api/*` routes during migration.

After tests pass, update Phase 5 plan list/status in roadmap to reflect implemented plan structure and execution readiness.
  </action>
  <verify>Run `pytest tests/integration/test_api_rate_limit_and_sse.py -q` and confirm green.</verify>
  <done>Contracts are test-protected and planning docs reflect current phase execution state.</done>
</task>

</tasks>

<verification>
- [ ] Tier rate limiting returns 429 with retry metadata on threshold breach
- [ ] SSE endpoint streams structured progress events for authenticated user-owned jobs
- [ ] Polling fallback endpoint returns current status consistently
- [ ] Legacy `/api/*` compatibility preserved for migration period
- [ ] `pytest tests/integration/test_api_rate_limit_and_sse.py -q` passes
</verification>

<success_criteria>
- API-04 implemented with tier-aware rate limiting
- API-08 implemented via SSE plus polling fallback
- Phase 5 runtime contract is stable enough for Phase 6 (jobs) and Phase 7 (frontend)
- Existing consumers continue working during migration window
</success_criteria>

<output>
After completion, create `.planning/phases/05-backend-api-design/05-02-SUMMARY.md`
</output>
