# journey-synthesis-13-15

Owner: ContextCurator
Cadence: end of every three phases

## Phase range covered
`13-15`

## Repeated failure patterns
1. Lifecycle trackers and phase READMEs drifted behind implementation artifacts.
2. Governance report bundles were missing for completed tasks, blocking formal closure.
3. Validation coverage was strong in backend slices but lagged in newly added frontend slices.

## Promoted preventive rules
1. Treat completion of each `*-SUMMARY.md` as a mandatory trigger for creating the four governance reports in `reports/<phase>/<task>/`.
2. Run targeted backend and frontend verification before phase-close updates to `.planning/ROADMAP.md` and `.planning/STATE.md`.
3. Update `docs/MASTER_MAP.md` batch date and journey links during every phase-close sweep.

## Proposed STANDARDS.md updates
1. Add a phase-close checklist item requiring both API and UI verification when a task spans backend + frontend.
2. Add a lifecycle sync rule that roadmap checkboxes must be updated in the same change as final summary/report artifacts.

## Accepted vs rejected changes
1. Accepted: split autonomous approval queue into `15-11a` backend + `15-11b` frontend plans | rationale: reduced scope risk and clearer governance evidence boundaries.
2. Accepted: approval queue component tests (`ApprovalQueue.test.tsx`) | rationale: closes uncovered UI behavior paths for approve/reject flows.
3. Rejected: hardcoded local DB credentials in checkpoint scripts | rationale: violates secret-integrity expectations and creates avoidable leakage risk.
