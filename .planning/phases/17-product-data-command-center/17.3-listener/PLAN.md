Phase 17.3 Shopify Listener (Wave 17.3)
Date: 2026-03-05
Status: Planning

Objective
- Implement Shopify product change listener: webhook receiver, signature verification, idempotent event ingestion, and reconciliation daemon to backfill missed events.

Outputs
- Webhook receiver endpoints for product changes (products/*)
- Signature verification path and credential lookup
- Idempotency keys per webhook event and store
- Reconciliation poller to catch missed events
- Versioned upsert + snapshot append on product changes

Plan
- Implement webhook route under the product listener modules
- Add signature verification and credential lookup hooks
- Implement idempotent handling keyed by event id + store
- Build reconciliation daemon to run in background and recover missed events
- Extend ingestion path to emit events and optional snapshots without destructive overwrites
- Update tests and docs; reference 17-UX-SPEC.md and 17-GRAPH-LINKS.md

Acceptance Criteria
- Webhook events are processed idempotently with no duplicates
- Reconciliation daemon catches missed events
- Snapshot/event chain remains traceable and consistent

Risks
- Webhook misconfiguration or signature issues; mitigate with validations
- Conflicts with existing ingest flow; handle via separation of concerns

References
- 17-UX-SPEC.md
- 17-GRAPH-LINKS.md

UX Alignment
- Desktop Wireframe 4.2 (ASCII) from 17-UX-SPEC.md is the UX target; integrated into this planning wave.
