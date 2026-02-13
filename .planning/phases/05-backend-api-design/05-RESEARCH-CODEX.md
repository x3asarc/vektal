# Phase 5: Backend API Design - Research (CODEX)

**Researched:** 2026-02-09
**Domain:** Flask API contracts, validation, docs, and real-time progress delivery
**Confidence:** HIGH (project fit), MEDIUM (library implementation details)

## Summary

Phase 5 should formalize the existing mixed API surface into a contract-first versioned API under `/api/v1/*` while keeping compatibility for existing `/api/*` routes during migration.

Recommended approach:
- Keep Flask + Blueprints (already production-proven in this repo).
- Add dedicated API package under `src/api/` for versioning, validation, docs, and error handling.
- Use Pydantic request/response schemas as single source of truth.
- Standardize failures with hybrid format:
  - Problem Details-style envelope for generic errors
  - field-level validation details for 422 payload errors
- Keep session-based auth from Phase 4 (no JWT migration in this phase).
- Implement SSE for one-way real-time updates now; keep polling fallback.
- Add tier-aware rate limiting with Redis-backed counters.

## Current-State Findings

- Existing API endpoints are split across:
  - app-level routes in `src/app.py` (`/api/jobs`, `/api/pipeline/*`, `/api/status`)
  - auth/billing blueprints under `src/auth/*` and `src/billing/*`
- Auth and session infrastructure already exists (Flask-Login + Redis session).
- No unified `/api/v1` namespace yet.
- No OpenAPI endpoint currently exposed.
- Pydantic is already in use under `src/core/config/*` and `src/core/discovery/*`.

## Decisions for Phase 5

1. Versioning
- Primary namespace: `/api/v1`
- Backward compatibility for existing `/api/*` routes retained in this phase.
- Add `users.api_version` for future per-user migration strategy (v1 -> v2).

2. Validation
- All JSON payloads validated with Pydantic schemas in `src/api/schemas/`.
- Validation failures return consistent 422 payload with field-level messages.

3. Error standardization
- Generic API errors include: `type`, `title`, `status`, `detail`, `instance`.
- Validation errors include `errors` map for frontend form binding.

4. Real-time
- Use SSE endpoint for job progress stream in Phase 5.
- Keep polling endpoint (`/api/v1/jobs/<id>/status`) as fallback.

5. Documentation
- OpenAPI JSON at `/api/openapi.json`.
- Interactive docs at `/api/docs`.
- Docs open in local development; auth-protected in production.

6. Security and CORS
- Restrictive CORS allowlist via environment config.
- Keep session cookie auth and existing auth decorators.

## Risks and Mitigations

- Risk: Breaking current consumers of `/api/*` routes.
  - Mitigation: Keep compatibility shims until frontend API client migration completes.
- Risk: Rate limiting blocks legitimate bursts.
  - Mitigation: Tier defaults + clear retry headers + exempt health/docs routes.
- Risk: SSE unsupported by some clients.
  - Mitigation: Keep polling fallback for all progress workflows.

## Deliverables

- `05-01-PLAN-CODEX.md`: API foundation (versioning, schemas, error contracts, docs, CORS, migration field).
- `05-02-PLAN-CODEX.md`: endpoint migration, tier rate limiting, SSE + polling, contract tests.

## Metadata

- Inputs analyzed: `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/phases/05-backend-api-design/05-CONTEXT.md`, `src/app.py`, `src/auth/*`, `src/billing/*`.
- Validity: until Phase 5 execution starts or architecture changes significantly.
