Phase 17.4 Dashboard Metrics API (Wave 17.4)
Date: 2026-03-05
Status: Planning

Objective
- Expose the dashboard metrics surface for completeness metrics and activity; implement API endpoints for summaries, field-level coverage, distributions, activity timeline, and clarifier pending state.

Outputs
- API endpoints under /api/v1/dashboard/* or /api/v1/products/metrics/*
- Data models for: completeness/summary, completeness/by-field, completeness/distribution, activity/recent, clarifications/pending
- Tests and docs stubs for the new endpoints

Plan
- Draft route definitions and schemas in the API layer
- Wire endpoints to the product data results and equity with 17-UX-SPEC
- Add tests for contract/integration coverage
- Prepare basic UI bindings in frontend to consume these endpoints

Acceptance Criteria
- Endpoints return consistent shapes and sample payloads
- Clarifier pending endpoint surfaces unresolved prompts
- UI components can render the new data surfaces

Risks
- Data drift due to asynchronous updates; include deterministic recompute workflow
- Performance impact for large catalogs; optimize with caching and pagination

References
- 17-UX-SPEC.md
- 17-GRAPH-LINKS.md

UX Alignment
- Desktop Wireframe 4.2 (ASCII) from 17-UX-SPEC.md is the UX target; integrated into this planning wave.
