# Phase 9 Planning Coverage

**Phase:** 09-real-time-progress-tracking  
**Generated:** 2026-02-13  
**Source inputs:** `09-CONTEXT.md`, `09-RESEARCH.md`

## Requirement Trace

| Requirement | Covered In | Notes |
|---|---|---|
| PROGRESS-01 (SSE or WebSocket) | `09-01` Task 1+2, `09-02` Task 1 | SSE-first with deterministic fallback ladder retained |
| PROGRESS-02 (Progress bar) | `09-02` Task 2 | Job detail progress bar + percent |
| PROGRESS-03 (Step display) | `09-01` Task 1+2, `09-02` Task 2 | Canonical step fields and labels |
| PROGRESS-04 (Visual transitions) | `09-02` Task 2 | Lifecycle tone/state rendering |
| PROGRESS-05 (ETA) | `09-01` Task 1+2, `09-02` Task 2 | Conservative ETA contract + UI fallback |
| PROGRESS-06 (Errors + retry) | `09-01` Task 3, `09-02` Task 2 | Backend retry guardrails + UI retry CTA rules |
| PROGRESS-07 (Success/failure notifications) | `09-02` Task 3 | Rich terminal notifications + actionable links |

## Plan Waves

1. **Wave 1 (`09-01`)**: backend contract hardening, lifecycle broadcasts, retry API.
2. **Wave 2 (`09-02`)**: frontend observer/detail/notifications/onboarding integration.

## Verification Contract (Mandatory)

- Backend (`09-01`):
  - `tests/api/test_jobs_progress_contract.py`
  - `tests/api/test_jobs_stream_status_contract.py`
  - `tests/api/test_jobs_retry.py`
  - `tests/jobs/test_progress_payload.py`
- Frontend (`09-02`):
  - `frontend/src/features/jobs/observer/transport-ladder.test.ts`
  - `frontend/src/features/jobs/hooks/useJobDetailObserver.test.ts`
  - `frontend/src/app/(app)/jobs/[id]/page.test.tsx`
  - `frontend/src/features/jobs/components/JobTerminalNotifications.test.ts`
  - `frontend/src/features/onboarding/components/OnboardingWizard.test.tsx`
  - `frontend` typecheck

## Explicit Out-of-Scope (from context/research)

- Multi-job timeline analytics.
- ML-based predictive ETA tuning.
- Full collaborative live editing semantics.
