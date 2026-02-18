# Harness Gaps — Browser Evidence Coverage

> Auto-generated context for `check_harness_slas.py`. Update this file when gaps are closed.
> Last manual review: 2026-02-17

## Coverage Status

| Feature Area | Unit Tests | E2E Tests | Browser Evidence | Gap Priority |
|---|---|---|---|---|
| Chat surface | ✅ ChatWorkspace.test.tsx | ✅ chat.e2e.ts | ✅ chat-shell.png | — |
| Enrichment workspace | ✅ EnrichmentWorkspace.test.tsx | ✅ enrichment.e2e.ts | ✅ enrichment-workspace.png | — |
| Job progress | ✅ jobs/[id]/page.test.tsx | ✅ job-progress.e2e.ts | ✅ jobs-list.png | — |
| Search/product grid | ✅ BulkActionBuilder.test.tsx | ❌ MISSING | ❌ MISSING | HIGH |
| Resolution dry-run review | ❌ MISSING | ❌ MISSING | ❌ MISSING | HIGH |
| Onboarding wizard | ✅ OnboardingWizard.test.tsx | ❌ MISSING | ❌ MISSING | MEDIUM |
| Settings / strategy quiz | ❌ MISSING | ❌ MISSING | ❌ MISSING | MEDIUM |
| Auth login flow | ❌ MISSING | ❌ MISSING | ❌ MISSING | HIGH |
| Approval workflow | ❌ MISSING | ❌ MISSING | ❌ MISSING | CRITICAL |
| SSE job streaming | ❌ MISSING | ❌ MISSING | ❌ MISSING | HIGH |
| Bulk action submission | ✅ BulkActionBuilder.test.tsx | ❌ MISSING | ❌ MISSING | HIGH |

## SLA Targets

```json
{
  "e2e_coverage_floor_pct": 60,
  "browser_evidence_required_for": ["critical", "high"],
  "max_gap_age_days": 14
}
```

## Known Gaps (ordered by priority)

### CRITICAL
1. **Approval workflow E2E** — Tier 2 dry-run → approve path has zero browser evidence.
   Required by assistant tier safety contract. Block deployment of Tier 2 changes until covered.
   Owner: Phase 14 (Continuous Optimization)

### HIGH
2. **Auth login flow E2E** — No E2E test for login → redirect → authenticated state.
   Foundational — affects all other E2E tests when running against real server.
   Owner: Next available sprint

3. **Search page E2E** — SearchWorkspace renders but has no smoke test.
   `tests/e2e/search.e2e.ts` needs creating.

4. **Resolution dry-run E2E** — DryRunReview component has no E2E coverage.
   Critical user path: vendor triggers dry-run → reviews diffs → approves/rejects.

5. **SSE job streaming E2E** — Job detail page has SSE stream (`/<job_id>/stream`).
   Playwright can intercept SSE; test is missing.

6. **Bulk action submission E2E** — BulkActionBuilder unit tested but no E2E.

### MEDIUM
7. **Onboarding wizard E2E** — Multi-step wizard; unit tested but no E2E flow.

8. **Settings/strategy quiz E2E** — RuleSuggestionsInbox and StrategyQuiz not covered.

## Closure Protocol

When closing a gap:
1. Create the E2E test file at `tests/e2e/<feature>.e2e.ts`
2. Confirm screenshot evidence emitted to `test-results/playwright-artifacts/`
3. Update the table above (✅ → row)
4. Run `python scripts/governance/check_harness_slas.py` — must pass
5. Commit the test + updated HARNESS_GAPS.md together

## Gap Age Tracking

| Gap | Opened | Max Age | Status |
|---|---|---|---|
| Approval workflow E2E | 2026-02-17 | 2026-03-03 | OPEN |
| Auth login flow E2E | 2026-02-17 | 2026-03-03 | OPEN |
| Search page E2E | 2026-02-17 | 2026-03-03 | OPEN |
| Resolution dry-run E2E | 2026-02-17 | 2026-03-03 | OPEN |
| SSE job streaming E2E | 2026-02-17 | 2026-03-03 | OPEN |
| Bulk action submission E2E | 2026-02-17 | 2026-03-03 | OPEN |
| Onboarding wizard E2E | 2026-02-17 | 2026-03-17 | OPEN |
| Settings/strategy quiz E2E | 2026-02-17 | 2026-03-17 | OPEN |
