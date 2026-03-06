Phase 17.5 Dashboard UI (Wave 17.5)
Date: 2026-03-05
Status: Planning

Objective
- Implement the dashboard command-center UI aligned to the ASCII UX spec, embed chat dock, and add product-data visualizations.

Outputs
- Dashboard updated to render API-backed data; ASCII UX alignment per 17-UX-SPEC
- Embedded Chat Dock integrated into the dashboard home
- Visualizations: Field coverage matrix, completeness distribution, activity timeline
- Desktop/mobile variants requested in the ASCII spec

Plan
- Update frontend components to reflect new blocks and data sources
- Wire in API endpoints for completeness metrics and activity
- Ensure design tokens and theme persist across themes; maintain accessibility
- Update tests and create small documentation notes

Acceptance Criteria
- Dashboard renders with real data and functional chat integration
- Visualizations render without layout disruptions

Risks
- UI regression due to complex layout changes; mitigate with contract-driven UI tests
- Accessibility and dark-theme consistency

References
- 17-UX-SPEC.md
- 17-GRAPH-LINKS.md

UX Alignment
- Desktop Wireframe 4.2 (ASCII) from 17-UX-SPEC.md is the UX target; integrated into this planning wave.
