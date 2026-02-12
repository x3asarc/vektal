# Compound Engineering OS Blueprint (Authoritative, Planning Only)

## Scope and Status
- This document is planning/spec only. No implementation actions are defined here.
- This operating model applies to every task in every phase.
- Current execution happens to be in Phase 7, but all rules are global.

## Locked Decisions
1. Workflow mode: local-only now, GitHub-ready structure.
2. Merge policy: block on `Critical` and `High`; also block on `Medium` for `Security` and `Dependency` findings only.
3. `MASTER_MAP.md` cadence: update at phase-close and daily batch.
4. Phase model: `7/14` roadmap with decimal atomic tasks (`7.1`, `7.2`, and so on).
5. KISS policy: target `150-400 LOC`; warning at `>500`; architecture note plus manual approval at `>800`.
6. Any file reaching `>=800 LOC` must be decomposed into at least two smaller modules in the following phase.
7. `ROADMAP.md` is the canonical source of truth for phase lifecycle state.

## 1) Blueprint Narrative
1. Governing model: one control plane (`AGENTS.md` plus phase/state artifacts), six specialist roles, hard gates.
2. Builder executes scoped atomic task and publishes self-check.
3. Reviewer audits output only and issues findings by severity.
4. Builder remediates until no blocking findings remain.
5. StructureGuardian runs placement, naming, and spec audit and can propose auto-moves through PR.
6. IntegrityWarden verifies dependencies, imports, and secrets and blocks unknown package risk.
7. ContextCurator updates master context on cadence.
8. PhaseManager validates all gates and is sole authority to mark complete.
9. Gate outcomes are binary: `GREEN` or `RED`.
10. Emergency bypass exists only for PhaseManager with mandatory rationale and rollback plan logged.

## 2) Gate System (Authoritative)
| Gate | Owner | Blocking Rule | Evidence Artifact |
|---|---|---|---|
| Build + Self-Check | Builder | Block if required checks are missing | `reports/<phase>/<task>/self-check.md` |
| Code Review | Reviewer | Block on `Critical/High`; block on `Medium` when `Security/Dependency` | `reports/<phase>/<task>/review.md` |
| Structure Audit | StructureGuardian | Block on any placement, naming, or spec violation | `reports/<phase>/<task>/structure-audit.md` |
| Integrity Audit | IntegrityWarden | Block on unknown package, unresolved vulnerability policy, or secret leak | `reports/<phase>/<task>/integrity-audit.md` |
| Context Sync | ContextCurator | Block phase-close if map or index is stale | `docs/MASTER_MAP.md` plus update log |
| Phase Closure | PhaseManager | Block unless all above are `GREEN` | `ROADMAP.md` plus `STATE.md` |

## 3) Ready-to-Create File Specs
Use exactly these files, owners, and sections.

### 3.1 `AGENTS.md`
Owner: PhaseManager
Sections:
1. Mission and non-negotiables.
2. Role authority boundaries.
3. Gate policy and severity blocking rules.
4. Emergency bypass protocol.
5. KISS limits (`150-400`, `>500`, `>800`).
6. Artifact contract and required reports.

### 3.2 `AGENTS.override.md` (optional per folder)
Owner: folder steward
Sections:
1. Local stricter constraints only.
2. Allowed tooling and commands for subtree.
3. Extra tests or compliance for subtree.

### 3.3 `ROADMAP.md`
Owner: PhaseManager
Sections:
1. 14-phase roadmap table.
2. Current phase pointer.
3. Entry and exit criteria per phase.
4. Gate status board (`GREEN/RED`) per phase.

### 3.4 `STATE.md`
Owner: PhaseManager
Sections:
1. Current phase and atomic task (`<phase>.<n>`).
2. Last completed gate.
3. Current blocker.
4. Next action in one sentence.
5. StructureGuardian audit trail (what moved, why, and when).

### 3.5 `STANDARDS.md`
Owner: Reviewer
Sections:
1. Severity taxonomy (`Critical/High/Medium/Low`).
2. Blocking matrix.
3. Review checklist (logic, security, tests, maintainability, KISS).
4. Evidence format for findings.
5. Preventive rules derived from `FAILURE_JOURNEY.md` three-phase synthesis.

### 3.6 `ops/STRUCTURE_SPEC.md`
Owner: StructureGuardian
Sections:
1. Canonical folder map.
2. Naming rules (`kebab-case`).
3. File placement rules.
4. Auto-move policy (PR plus audit trail).

### 3.7 `docs/MASTER_MAP.md`
Owner: ContextCurator
Sections:
1. TOC.
2. Project tree (depth 3).
3. Module index.
4. Data and logic flow summary.
5. Active plans and latest completed plans.
6. Links to role rules and standards.
7. Last batch update timestamp.
8. Link to the latest three-phase Journey synthesis output.

### 3.8 `FAILURE_JOURNEY.md`
Owner: Builder plus Reviewer
Sections:
1. Date and task.
2. Tried X.
3. Failed Y.
4. Doing Z.
5. Preventive rule added.

### 3.9 `.planning/phases/<phase>/<task>/PLAN.md`
Owner: PhaseManager plus Builder
Sections:
1. Objective.
2. Scope in and scope out.
3. Atomic checklist.
4. Risks.
5. Definition of done.
6. Gate evidence links.

### 3.10 `reports/<phase>/<task>/self-check.md`
Owner: Builder
Format: checklist only with `Pass`, `Fail`, `Action Required`, or explicit `N/A` for non-applicable fields. Empty fields are not allowed.

### 3.11 `reports/<phase>/<task>/review.md`
Owner: Reviewer
Finding format:
`[Severity] [Category] [File/Path] [Issue] [Evidence] [Required Fix]`
Required fields:
1. `pass_1_timestamp` (blind audit publish time).
2. `pass_2_timestamp` (context-fit publish time).
3. `plan_context_opened_at` (first time reviewer opens task `PLAN.md`).
Rule: `pass_1_timestamp` must be earlier than `plan_context_opened_at` by git commit evidence.

### 3.12 `reports/<phase>/<task>/structure-audit.md`
Owner: StructureGuardian
Format: checklist plus moved-file log. Use explicit `N/A` for non-applicable fields. Empty fields are not allowed.

### 3.13 `reports/<phase>/<task>/integrity-audit.md`
Owner: IntegrityWarden
Format: registry verification, dependency risk, license compliance, lockfile and pinning verification, and secrets scan result. Use explicit `N/A` for non-applicable fields. Empty fields are not allowed.

### 3.14 `.rules`
Owner: PhaseManager plus IntegrityWarden
Format policy:
1. One rule per line.
2. No nested logic.
3. Enforce presence of pinned tool versions in `requirements.txt` and/or `package-lock.json`.
4. Enforce successful execution of required pinned linters/scanners.
5. Default deny for unknown package installs and imports.
6. Explicit allowlist for approved commands.

### 3.15 `reports/meta/journey-synthesis-<phase-range>.md`
Owner: ContextCurator
Cadence: once at the end of every three phases.
Sections:
1. Phase range covered.
2. Repeated failure patterns.
3. Promoted preventive rules.
4. Proposed `STANDARDS.md` updates.
5. Accepted versus rejected rule changes with rationale.

## 4) Prompt Pack Per Role (Codex-Native Drafts)
Keep each role prompt under 500 words in final operational files.

### 4.1 PhaseManager Prompt
```text
You are PhaseManager. You own phase lifecycle truth in ROADMAP.md and STATE.md.
Only you can mark a phase complete.
Before authorizing work, verify phase entry criteria.
Before closing work, require GREEN status for review, structure, integrity, and context sync.
Emergency bypass is allowed only with written rationale, rollback plan, and timestamped log.
Use binary gate outcomes only: GREEN/RED.
Enforce KISS: target 150-400 LOC per file; warn >500; require architecture note + manual approval >800.
```

### 4.2 Builder Prompt
```text
You are Builder. You implement only the scoped atomic task from PLAN.md.
Produce self-check evidence and deterministic tests or traces required by standards.
Do not mark phase completion.
After review findings, remediate and reissue self-check.
Log failed attempts and lessons in FAILURE_JOURNEY.md using Tried/Failed/Doing format.
Keep solutions simple and aligned with KISS policy.
```

### 4.3 Reviewer Prompt
```text
You are Reviewer. You do not author production code.
Blind Audit protocol: before publishing your initial review, you are forbidden from reading PLAN.md and FAILURE_JOURNEY.md for the task.
Evidence protocol: verify ordering using git commit timestamps for pass-1 review publication and first PLAN.md context access event.
Audit final outputs only and avoid social bias from implementation narrative.
Use STANDARDS.md severity model.
Block on Critical/High; block on Medium for Security/Dependency only.
Provide findings with clear evidence and required fix.
You may provide patch suggestions, but do not merge or close phase.
```

### 4.4 StructureGuardian Prompt
```text
You are StructureGuardian. You own ops/STRUCTURE_SPEC.md.
Enforce naming and file placement policy with binary pass/fail.
You may propose auto-moves, but all moves must be traceable through report entries.
Reject ambiguous placement and undocumented exceptions.
```

### 4.5 IntegrityWarden Prompt
```text
You are IntegrityWarden. You are the package firewall.
Verify imports and dependencies against real registries using a known-good registry policy.
Auto-approve packages only when they are older than two years and exceed 1,000,000 weekly downloads on npm or PyPI.
Escalate scrutiny for all other packages, including provenance and slopsquatting risk checks.
Block strong copyleft licenses (for example GPL family). Allow permissive licenses (for example MIT and Apache) by default.
Require lockfiles and pinned dependency versions for any plan that introduces or updates dependencies.
Block unknown or hallucinated packages, unresolved dependency risks, and hardcoded secrets.
Publish integrity-audit evidence for every atomic task that changes dependencies or sensitive flows.
```

### 4.6 ContextCurator Prompt
```text
You are ContextCurator. You own docs/MASTER_MAP.md.
Maintain a scannable TOC-style map with depth-3 tree, module index, active plans, and key links.
Update on daily batch and phase-close.
At the end of every three phases, summarize FAILURE_JOURNEY.md patterns and propose STANDARDS.md preventive-rule updates.
Archive stale artifacts instead of deleting them, preserving auditability.
Reject context updates that add noise without decision value.
```

## 5) KISS Policy (Final Operational Form)
1. Target per-file size: `150-400 LOC`.
2. Warning trigger: `>500 LOC` requires split evaluation.
3. Exception trigger: `>800 LOC` requires architecture note plus manual approval.
4. Required architecture note fields: root cause, impact, risk, and explicit refactoring plan.
5. Mandatory follow-up: any file reaching `>=800 LOC` must be decomposed into at least two smaller modules in the following phase.
6. Complexity policy: complexity growth without functional necessity is a `Medium` maintainability risk.
7. Duplication policy: repeated logic in three or more places requires a consolidation plan.

## 6) Red Team Failure-Mode Matrix
| Failure Mode | Early Signal | Primary Detector | Containment | Prevention |
|---|---|---|---|---|
| Context rot | stale links or phase mismatch | ContextCurator | freeze phase-close | daily batch plus phase-close map updates |
| Review theater | LGTM with weak evidence | PhaseManager | reopen review gate | strict evidence format in `review.md` |
| Sycophancy bias | low challenge rate | Reviewer | force devil's-advocate pass on risky changes | mandatory adversarial review for high or critical risk tasks |
| Slopsquatting | unknown or low-trust package names | IntegrityWarden | block merge immediately | known-good registry thresholds plus provenance checks |
| Drift loop | repeated failed fixes | PhaseManager | backtrack after two failed attempts | anti-drift rule in gate logic |
| Stubborn loop | same fix reattempted | PhaseManager | REFRESH directive plus scope reset | failure journey logging |
| Structure entropy | misplaced files | StructureGuardian | auto-move PR plus block until green | `STRUCTURE_SPEC.md` enforcement |
| Overengineering | size or complexity spikes | Reviewer | mark `Medium` maintainability | KISS thresholds plus architecture note rule |
| Hidden bypasses | unlogged exceptions | PhaseManager | invalidate phase close | bypass log required in `STATE.md` |
| Secret leakage | token or key patterns | IntegrityWarden | block and rotate credentials | secret scan gate |

## 7) System Acceptance Criteria (Global)
1. Every task (`<phase>.<n>`) has a `PLAN.md` and exactly four reports in `reports/<phase>/<task>/`: `self-check.md`, `review.md`, `structure-audit.md`, `integrity-audit.md`.
2. No unresolved blocking findings under the merge policy.
3. `MASTER_MAP.md` updates happen on daily batch and at phase-close.
4. `STATE.md` always reflects current active task and gate status.
5. At least one anti-drift and anti-stubborn handling example is captured in `FAILURE_JOURNEY.md` during rollout.
6. Reports contain no empty required fields; non-applicable fields must use explicit `N/A`.
7. Reviewer initial audit is published before task-context access and proven via git commit timestamp ordering (`review.md` pass 1 before first `PLAN.md` context update commit).
8. `ROADMAP.md` is authoritative for phase status, and phase close requires all gates marked `GREEN`.
9. Strong copyleft dependency licenses are blocked; permissive licenses are allowed by default unless otherwise restricted.
10. Any task introducing dependencies must include lockfile plus pinned versions evidence.
11. At the end of every three phases, ContextCurator publishes Journey synthesis and proposed `STANDARDS.md` updates.

## 8) Pilot Metrics and Readiness Signals
1. Baseline metrics: cycle time, reopen rate, gate failure rate.
2. Noise control metrics: false-positive rate for StructureGuardian and IntegrityWarden findings.
3. Pilot stop rule: any stubborn loop (three or more failed fix attempts) triggers policy tuning before proceeding.
4. Go-live rehearsal: one dry-run task must complete the full four-gate flow before production implementation tasks.
