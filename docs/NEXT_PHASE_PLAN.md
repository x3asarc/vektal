# Next Phase Plan (Post-v1.0)

Last updated: 2026-03-03

## 1) Canonical Context
- Lifecycle source of truth: `.planning/ROADMAP.md`
- Runtime/project state: `.planning/STATE.md`
- Active priority queue: `.planning/NEXT_TASKS.md`
- Governance baseline: `AGENTS.md`, `STANDARDS.md`

Current state is `v1.0 COMPLETE`. The next execution focus is:
1. Future Phase: Production Refinement & Integration Cleanup
2. Future Phase: User Data Knowledge Graph & Semantic Search

## 2) Priority Queue Snapshot
1. Priority 1: Health -> remediation routing (`COMPLETE`, 2026-03-03)
2. Priority 2: Deploy to Dokploy for end-to-end testing (`ACTIVE`)
3. Priority 3: Implement memory system with hooks (`QUEUED`)

This document completes Priority 2 planning so execution can start without ambiguity.

## 3) Priority 2 Objective
Deploy the full platform to Dokploy and verify real user workflows across frontend, backend, queue, graph, observability, and remediation loops.

Gate outcome is binary:
- `GREEN`: all exit criteria in Section 9 are satisfied with evidence.
- `RED`: any required criterion or evidence artifact is missing.

## 4) Priority 2 Scope
In scope now:
- Dokploy deployment for frontend, backend, Redis, PostgreSQL, Neo4j, and Celery workers.
- Runtime smoke checks for web/API/queue/graph availability.
- E2E validation from user perspective (chat flow, approvals, monitoring, auto-heal loop).
- Sentry + Graphiti + health monitor + remediator integration checks.

Out of scope for Priority 2:
- New feature development.
- Schema redesign or large refactors.
- Priority 3 memory-system implementation.

## 5) Prerequisites (Must Be True Before Deploy)
- Dokploy project and environment are created.
- Production-like secrets are available in Dokploy:
  - `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`
  - `DB_PASSWORD`
  - `NEO4J_PASSWORD`
  - `SENTRY_DSN`, `SENTRY_WORKERS_DSN`, `NEXT_PUBLIC_SENTRY_DSN`
  - `SENTRY_AUTH_TOKEN`, `SENTRY_ORG_SLUG`, `SENTRY_PROJECT_SLUG`
- Environment variables align with `.env.example`.
- A non-production Shopify test store is used for E2E write paths.
- Migration path is defined (`python -m flask db upgrade` at startup is acceptable for this phase).

## 6) Deployment Mapping (Compose -> Dokploy)
| Compose Service | Dokploy Target | Notes |
|---|---|---|
| `frontend` | Web app service | Public route, points to backend API URL |
| `backend` | Web app service | Runs Flask/Gunicorn + migrations |
| `celery_worker` | Worker service | Queues: control + interactive + assistant |
| `celery_scraper` | Worker service | Queues: batch |
| `celery_assistant` | Worker service | Queues: assistant |
| `db` | Managed/Postgres service | Persistent volume required |
| `redis` | Managed/Redis service | Broker + cache |
| `neo4j` | Managed Neo4j service | Port + auth + persistence required |
| `flower` | Optional internal dashboard | Keep internal/private by default |
| `nginx` | Optional | Can be skipped if Dokploy ingress handles routing |

## 7) Execution Sequence
1. Prepare Dokploy services and environment groups.
2. Deploy data layer first: PostgreSQL, Redis, Neo4j.
3. Deploy backend and confirm health endpoint returns success.
4. Deploy Celery workers and verify queue consumption starts.
5. Deploy frontend and confirm app shell loads and can call backend.
6. Run smoke checks:
   - `GET /health` on backend
   - chat session endpoint health probe (`/api/v1/chat/sessions`)
   - frontend route load
7. Run controlled E2E user workflow:
   - open chat
   - execute one dry-run workflow
   - verify approval queue UI path
   - apply one approved action in test store
8. Run failure-path validation:
   - trigger one Sentry-captured runtime error
   - verify classifier + routing path
   - verify remediator attempt and logged outcome

## 8) Integration Validation Matrix (Priority 2)
| Capability | Validation | Pass Condition |
|---|---|---|
| Sentry ingestion | Trigger known error in deployed env | Error visible in configured Sentry project |
| Graph context (Graphiti/Neo4j) | Run classification needing graph context | Classification evidence includes graph-related context |
| Health monitor | Confirm cache updates and issue detection | Health cache updates on schedule; issue state flips are recorded |
| Auto-remediation | Trigger Neo4j/dependency style issue | Orchestrator routes to expected remediator and records outcome |
| Frontend approvals (HITL) | Submit approval-required operation | Approval appears in UI and action result is persisted |

## 9) Exit Criteria (`GREEN` / `RED`)
`GREEN` only if all are true:
1. All core services are deployed and healthy in Dokploy.
2. End-to-end user path succeeds (chat -> dry-run -> approval -> apply in test store).
3. Sentry receives runtime issue data from deployed services.
4. At least one remediation route is observed end-to-end with outcome log.
5. Required governance evidence exists under one task folder:
   - `reports/<phase>/<task>/self-check.md`
   - `reports/<phase>/<task>/review.md`
   - `reports/<phase>/<task>/structure-audit.md`
   - `reports/<phase>/<task>/integrity-audit.md`

If any item fails, gate is `RED`.

## 10) Evidence Package For Priority 2
Recommended task folder:
- `reports/future-production-refinement/priority-2-dokploy-e2e/`

Include:
- deployment timestamps and service URLs
- smoke test HTTP results
- E2E run notes with exact scenario IDs
- Sentry event IDs
- remediation outcome log references
- reviewer two-pass timestamps in `review.md`

## 11) Next Step After Priority 2
On `GREEN`, start Priority 3 (`.planning/memory-system-design.md`) without changing Priority 2 evidence.
On `RED`, keep Priority 2 open and re-run only failed checks until all gates pass.

## 12) Re-Verification Snapshot (2026-03-03)
Current gate: `RED` (deployment objective not yet completed).

Evidence-backed status:
- `DONE (readiness)`:
  - Local stack/test stabilization complete (`python -m pytest tests/ -x --tb=short -q` -> 903 passed, 2 skipped).
  - Frontend Playwright E2E harness exists:
    - `frontend/playwright.config.ts`
    - `frontend/tests/e2e/chat.e2e.ts`
    - `frontend/tests/e2e/enrichment.e2e.ts`
    - `frontend/tests/e2e/job-progress.e2e.ts`
  - Historical/local browser evidence exists (for example):
    - `reports/meta/playwright-ui-check-2026-02-16T16-34-21-141Z.json`
    - `reports/meta/playwright-chat-check-2026-02-16T17-45-38-202Z.json`
    - `reports/meta/playwright-chat-api-trace-2026-02-16T17-46-35-143Z.json`
- `NOT DONE (Priority 2 deployment close)`:
  - No Dokploy-specific deployment artifact discovered.
  - No evidence bundle exists at `reports/future-production-refinement/priority-2-dokploy-e2e/`.
  - No verified Dokploy service URL/smoke-check record in reports.
  - No captured Sentry event IDs tied to deployed Dokploy runtime.

---

## Appendix A: Deferred Product-Sync Requirements (Carry Forward)
These requirements are retained from the prior draft and are deferred to future user-facing refinement work.

### A.1 Locked Requirements
- Accept any identifier input (SKU, EAN, handle, title, URL).
- Preserve pipeline flow: resolve -> diff -> scrape -> amend -> push.
- Keep v4 fallback (`scripts/not_found_finder_v4_optimized.py` + `not_found.csv`).
- Image policy:
  - `images == 0`: auto scrape + add image #1
  - `images == 1`: app approval + preview; "apply to batch" unchecked
  - `images >= 2`: app approval + preview; replace image #1 only
- Handle changes require explicit approval.
- Dry-run payload is approved and pushed without re-run.
- Minimize API calls; allow REST fallback when GraphQL misses.

### A.2 UX and Approval Behavior
- App shows current image #1 and candidate side-by-side.
- Batch shorthand remains: current `Lllll`, scraped `Bbbbb` (first image larger).
- "Apply to batch" remains explicit and default-off.
- CLI remains non-visual by default; prompts only when explicitly enabled.

### A.3 SKU/EAN Ambiguity
- If SKU and barcode resolve to different products, surface both to user and trigger vendor-site lookup using existing scripts.
- Cache resolver reads per run.

### A.4 Canonical Artifacts For This Deferred Scope
- Payload spec: `docs/PAYLOAD_SCHEMA.md`
- QA checklist: `docs/QA_CHECKLIST.md`
