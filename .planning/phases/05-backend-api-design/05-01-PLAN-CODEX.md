---
phase: 05-backend-api-design
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - src/models/user.py
  - migrations/versions/
  - src/api/__init__.py
  - src/api/errors.py
  - src/api/docs.py
  - src/api/schemas/common.py
  - src/api/v1/__init__.py
  - src/api/v1/status/routes.py
  - src/api/v1/jobs/routes.py
  - src/api/v1/pipeline/routes.py
  - src/app.py
  - tests/integration/test_api_v1_contracts.py
autonomous: true

must_haves:
  truths:
    - "All primary backend endpoints are exposed under /api/v1"
    - "Invalid JSON payloads return standardized field-level validation errors"
    - "API errors return a consistent structured format"
    - "OpenAPI JSON and interactive docs endpoints are available"
    - "Session-based authentication is enforced on protected API endpoints"
  artifacts:
    - path: "src/api/schemas/common.py"
      provides: "Pydantic request/response schemas for API contracts"
      contains: "class"
    - path: "src/api/errors.py"
      provides: "Centralized API error/validation handlers"
      exports: ["register_api_error_handlers"]
    - path: "src/api/docs.py"
      provides: "OpenAPI and docs route registration"
      exports: ["register_api_docs"]
    - path: "src/api/v1/jobs/routes.py"
      provides: "Versioned jobs API routes"
    - path: "src/app.py"
      provides: "API v1 blueprint and docs registration"
  key_links:
    - from: "src/app.py"
      to: "src/api/v1/jobs/routes.py"
      via: "blueprint registration"
      pattern: "register_blueprint"
    - from: "src/api/v1/pipeline/routes.py"
      to: "src/api/schemas/common.py"
      via: "request validation"
      pattern: "BaseModel|model_validate"
    - from: "src/api/errors.py"
      to: "src/api/v1/"
      via: "global exception mapping"
      pattern: "errorhandler|register_api_error_handlers"
---

<objective>
Create the API contract foundation for Phase 5 with versioned routes, validation, standardized errors, and docs.

Purpose: Establish a stable `/api/v1` contract so frontend and workers can integrate predictably without coupling to legacy app-level endpoints.
Output: Versioned API package, schema validation layer, common error contract, docs endpoints, and baseline API contract tests.
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
@src/app.py
@src/auth/decorators.py
@src/models/user.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create API v1 package and blueprint structure</name>
  <files>src/api/__init__.py, src/api/v1/__init__.py, src/api/v1/status/routes.py, src/api/v1/jobs/routes.py, src/api/v1/pipeline/routes.py, src/app.py</files>
  <action>
Create a dedicated `src/api/` package with domain-separated v1 route modules and register it in `src/app.py` under `/api/v1`.

Scope:
- Move or wrap existing `/api/status`, `/api/jobs`, `/api/pipeline/dry-run`, and `/api/pipeline/push` behavior into v1 route modules.
- Keep existing `/api/*` routes as compatibility wrappers in this phase.
- Ensure protected endpoints use Phase 4 auth/session decorators consistently.

Do not introduce business-logic changes in this task; this task is route architecture and contract stability.
  </action>
  <verify>`flask routes` includes `/api/v1/status`, `/api/v1/jobs`, `/api/v1/pipeline/*` and existing `/api/*` routes still resolve.</verify>
  <done>Versioned API routes are registered and coexist with legacy routes.</done>
</task>

<task type="auto">
  <name>Task 2: Implement schema validation and standardized error responses</name>
  <files>requirements.txt, src/api/schemas/common.py, src/api/errors.py, src/api/v1/pipeline/routes.py, src/api/v1/jobs/routes.py, src/app.py</files>
  <action>
Add Pydantic-based request/response schemas for v1 routes and centralized API error handling.

Required behaviors:
- Validate request bodies using Pydantic before business logic execution.
- Map validation failures to 422 with field-level `errors` payload.
- Map generic failures to a consistent Problem Details-style response.
- Ensure auth errors and permission errors remain compatible with current frontend expectations.

Update `requirements.txt` only if required to align Pydantic runtime version with project usage.
  </action>
  <verify>Send invalid payload to `/api/v1/pipeline/dry-run` and confirm structured 422 response with field errors.</verify>
  <done>All v1 JSON endpoints validate payloads and emit standardized error envelopes.</done>
</task>

<task type="auto">
  <name>Task 3: Add API docs endpoints and baseline contract tests</name>
  <files>src/api/docs.py, src/app.py, tests/integration/test_api_v1_contracts.py</files>
  <action>
Expose API docs endpoints and add integration tests that lock the v1 contract.

Required outcomes:
- `/api/openapi.json` returns valid JSON spec structure.
- `/api/docs` serves interactive documentation page.
- In production mode, docs endpoints require authentication; in development they remain open.
- Add integration tests for route availability, validation error shape, and auth gating.
  </action>
  <verify>Run `pytest tests/integration/test_api_v1_contracts.py -q` and confirm passing tests.</verify>
  <done>Docs endpoints exist and contract tests verify v1 baseline behavior.</done>
</task>

</tasks>

<verification>
- [ ] `flask routes` shows `/api/v1` namespace endpoints
- [ ] Validation errors return 422 with field-level details
- [ ] Generic API errors return standardized structured format
- [ ] `/api/openapi.json` and `/api/docs` are reachable under correct auth mode
- [ ] `pytest tests/integration/test_api_v1_contracts.py -q` passes
</verification>

<success_criteria>
- API-01 implemented with versioned `/api/v1` structure
- API-02 baseline implemented with docs endpoints and spec route
- API-03 satisfied using existing session auth on protected endpoints
- API-05 implemented through Pydantic validation for v1 payloads
- API-06 implemented with standardized error responses
- API-07 baseline CORS and route contract preserved for frontend migration
</success_criteria>

<output>
After completion, create `.planning/phases/05-backend-api-design/05-01-SUMMARY.md`
</output>
