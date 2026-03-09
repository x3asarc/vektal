---
name: gsd
description: Execute Get Shit Done workflows for this repository using local planning artifacts and installed GSD references.
---

# GSD Skill

Use this skill when the user asks to run any GSD workflow in this repository, including discuss/plan/execute/verify tasks by phase number.

## Workflow roots

Resolve workflow files in this order:
1. `codexclaude/get-shit-done`
2. `.claude/get-shit-done`

## Supported commands

Map user intent to these workflows:
- `help` -> show command overview from `.claude/commands/gsd` (if present)
- `discuss-phase N` -> `workflows/discuss-phase.md`
- `plan-phase N` -> plan workflow and generate/update `.planning` plan files
- `execute-phase N` -> `workflows/execute-phase.md`
- `verify-work N` -> `workflows/verify-work.md`

## Execution rules

- Always read relevant `.planning` files for the target phase before acting.
- Preserve existing `.planning` naming conventions and structure.
- Call out assumptions and blockers explicitly.
- Prefer concrete next commands in responses.

## Post-closure regression gate (strict, integrated)

After implementation and before final phase closure, run a heavier post-closure regression gate as part of the normal verification workflow (not a separate command).

Rules:
1. Gate is phase-scoped to success metrics and contracts; no feature expansion.
2. Gate must include all of:
   - phase unit regression tests,
   - phase integration/e2e regressions (where applicable),
   - at least one runtime smoke path for the phase,
   - compatibility checks for required upstream/downstream contracts.
3. If focused regression coverage is missing, add focused regression tests before closure.
4. Any regression failure forces `gaps_found` and reopens gap-closure flow.
5. Record gate evidence in:
   - phase `*-VERIFICATION.md`,
   - latest phase summary,
   - `.planning/STATE.md`.
6. Enforcement point is inside normal verification flow (`verify_phase_goal` / `verify-work`), not a standalone post-closure command.

## Mandatory sequencing (strict)

For `discuss-phase N`, run this order strictly:
1. Run **Pre-Context Scope Gate** and create/update `N-PRE-CONTEXT-SCOPE.md` first.
2. Scope must stay high-level and project-wide (completed phases, planned/active phases, dependency impact).
3. Present route options A/B/C as explicit, evidence-backed directions:
   - each option must include scope now, defers, hard-fact basis, and tradeoff.
   - generic "keep/amend/alternate" labels without concrete detail are not acceptable.
4. Capture user selection.
5. Only then run detailed context questioning and write/update `N-CONTEXT.md`.

For `plan-phase N`, run this order strictly:
1. Ensure `N-CONTEXT.md` exists (run discuss flow if missing).
2. Trigger **research agent** (`gsd-phase-researcher`) and produce/update `N-RESEARCH.md` unless `--skip-research` or `--gaps`.
3. Generate/update `N-*-PLAN.md`.

For `execute-phase N`, run this order strictly:
1. Load phase plans and run **Plan Verification Gate** (via `gsd-plan-checker`).
2. If plan gate fails, stop execution and route to `/prompts:gsd-plan-phase N` (or `--gaps` flow).
3. Only execute waves after plan gate passes (or explicit emergency bypass is recorded).

Do not skip step 2 when context exists and research is missing/stale.
Do not execute implementation before context + research + plan artifacts are in place.

## Context questioning gate (strict)

When creating or updating `N-CONTEXT.md`, assumptions-only context is forbidden.

Required before writing context:
- at least 1 discussed area
- at least 4 explicit user answers to context questions
- `Discussion Evidence` recorded in context (`questions_answered`, `areas_discussed`)

If the user asks to skip questions, run a compact mandatory 4-question pack, capture answers, then continue.

## Research depth gate

When triggering research:
- Reuse existing internal files first (no duplicate parallel specs).
- Run dual-pass research in parallel:
  - baseline pass via `gsd-phase-researcher`
  - deep exhaustive pass via `gsd-phase-research-deep`
- Synthesize both outputs into one canonical `N-RESEARCH.md` before planning.
- For in-scope libraries/frameworks/APIs, use Context7 first (resolve-library-id + query-docs) before broad web search.
- Capture concrete implementation contracts (payloads, invariants, failure paths).
- Include requirement mapping and explicit unresolved risks.
- RESEARCH.md must include Context7 evidence: library IDs queried + topics, or explicit `Context7 not applicable` reason.
- If synthesized research is shallow/incomplete, iterate deep pass + synthesis once more before planning.


