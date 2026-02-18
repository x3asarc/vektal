---
phase: 09-real-time-progress-tracking
plan: 01
subsystem: backend
tags: [progress-contract, sse, polling, retry, lifecycle-broadcast]
requires:
  - phase: 09-real-time-progress-tracking
    provides: "09-CONTEXT.md + 09-RESEARCH.md + regenerated 09-01 plan gates"
provides:
  - "Canonical progress payload contract shared across SSE/polling/list/detail"
  - "Lifecycle transition broadcasts wired through orchestrator/finalizer/cancellation"
  - "Guarded retry endpoint for terminal failed/cancelled jobs"
affects: [phase-09-frontend-progress-ux, phase-10-chat-ops]
tech-stack:
  added: [src/jobs/progress.py, contract tests for progress/retry/stream parity]
  patterns: [single-payload-source, named-sse-event, retry-as-new-job]
key-files:
  created:
    - src/jobs/progress.py
    - tests/jobs/test_progress_payload.py
    - tests/api/test_jobs_retry.py
    - tests/api/test_jobs_progress_contract.py
    - tests/api/test_jobs_stream_status_contract.py
  modified:
    - src/api/jobs/events.py
    - src/api/jobs/schemas.py
    - src/api/v1/jobs/routes.py
    - src/api/v1/jobs/schemas.py
    - src/jobs/orchestrator.py
    - src/jobs/finalizer.py
    - src/jobs/cancellation.py
key-decisions:
  - "Progress field derivation is centralized in a backend helper to eliminate producer drift."
  - "Retry semantics are backend-enforced with terminal-state gating and 409 conflict behavior."
patterns-established:
  - "All progress producers (SSE, polling, list/detail, lifecycle broadcasts) call canonical payload builder."
  - "Named SSE event channel (`job_{id}`) remains stable for frontend observer contracts."
duration: 75min
completed: 2026-02-13
---

# Phase 9: Real-Time Progress Tracking Summary

Phase `09-01` delivered backend contract hardening for live progress, lifecycle broadcasting, and retry guardrails.

## Accomplishments

- Added canonical progress payload helper (`src/jobs/progress.py`) with:
  - counters, percent, step semantics, ETA, retryability, deep links.
- Extended SSE + polling schemas and events to use the canonical payload.
- Enriched v1 jobs list/detail responses with the same progress fields.
- Added retry API endpoint:
  - `POST /api/v1/jobs/{job_id}/retry`
  - supports `failed`, `failed_terminal`, `cancelled`
  - returns `202` with new stream URL and lineage (`retry_of_job_id`).
- Wired lifecycle broadcasts in:
  - ingest orchestrator (queue/chunk transitions),
  - finalizer (terminal convergence),
  - cancellation request path.

## Verification Runs

- Command:
  - `python -m pytest -q tests/jobs/test_progress_payload.py tests/api/test_jobs_progress_contract.py tests/api/test_jobs_stream_status_contract.py tests/api/test_jobs_retry.py tests/jobs/test_finalizer.py tests/jobs/test_cancellation.py tests/jobs/test_non_blocking_api_flow.py tests/api/test_endpoints.py`
- Result:
  - `33 passed`, `0 failed`

## Issues Encountered

- Existing `tests/jobs/test_cancellation.py` failed initially because new progress broadcaster touched sparse fake job doubles missing attributes.
- Fixed by making progress helper resilient to missing optional attributes (`total_items`, `processed_items`, `parameters`, `successful_items`, `failed_items`, `error_message`).

## Outcome Against Plan Gates

- Canonical payload parity across stream/status/list/detail: **met**
- Deterministic lifecycle broadcasts: **met**
- Retry endpoint guarded and deterministic: **met**
- Backward-compatibility and non-blocking API checks: **met**

## Next

- Execute `09-02` frontend plan:
  - named-event observer contract,
  - job detail progress UX (progress/step/ETA/retry),
  - terminal notifications and onboarding live progress linkage.
