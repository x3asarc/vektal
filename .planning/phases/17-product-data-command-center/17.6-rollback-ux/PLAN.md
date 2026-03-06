Phase 17.6 Rollback UX (Wave 17.6)
Date: 2026-03-05
Status: Planning

Objective
- Integrate rollback UX into the dashboard timeline and actions; enable users to revert to prior product states via governed rollback.

Outputs
- Dashboard timeline entries with rollback actions
- Dry-run -> Approve -> Apply rollback workflow
- Diffed changes and rollback diffs to aid decision making

Plan
- Map rollback workflows into governance: dry-run, approval, apply
- Extend UI to show rollback options in timeline and diffs
- Validate rollback paths against snapshot/event chain integrity
- Add tests and user-facing help text

Acceptance Criteria
- Rollback path is accessible and safe; changes revert to prior snapshot/state
- Rollback workflow respects governance constraints and auditing

Risks
- Data integrity risk if rollback partial; ensure atomicity and validation
- Conflicts when multiple rollbacks are issued; design queueing and conflict resolution

References
- 17-UX-SPEC.md
- 17-GRAPH-LINKS.md

UX Alignment
- Desktop Wireframe 4.2 (ASCII) from 17-UX-SPEC.md is the UX target; integrated into this planning wave.
