Phase 17.2 Ingest Hardening (Wave 17.2)
Date: 2026-03-05
Status: Planning

Objective
- Harden onboarding ingest workflow to reliably create product records and compute initial completeness aggregates; persist ingest watermark for listener handoff; ensure idempotency and observability.

Outputs
- Bootstrap ingest path writes product records and initial completeness aggregates
- Ingest watermark persisted: last_full_ingest_at, last_shopify_cursor
- Observability hooks (metrics/logs) for ingestion progress and health
- Non-destructive changes to existing ingest flow

Plan
- Review onboarding/integration points in: frontend/src/features/onboarding/components/OnboardingWizard.tsx, src/api/v1/jobs/routes.py, src/jobs/orchestrator.py
- Implement ingest mode that computes completeness aggregates as part finalization
- Persist ingest watermark for handoff to the listener (cursor + timestamp)
- Add basic health checks and logging around ingest
- Update tests or add contract stubs for ingest workflow
- Align with 17-UX-SPEC.md and 17-GRAPH-LINKS.md

Acceptance Criteria
- Bootstrap ingest writes product records and completeness aggregates
- Ingest watermark is persisted and readable by listener
- No regressions to existing ingest behavior

Risks
- Watermark schema drift; mitigate with migration guardrails
- Duplicate/omitted ingest events; mitigate with idempotency and reconciliation

References
- 17-UX-SPEC.md
- 17-GRAPH-LINKS.md

UX Alignment
- Desktop Wireframe 4.2 (ASCII) from 17-UX-SPEC.md is the UX target; integrated into this planning wave.
