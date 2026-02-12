# Engineering Standards v1

## Severity taxonomy
1. `Critical`: exploitable security flaw, data corruption/loss, or core system outage.
2. `High`: major logic correctness issue or reliability issue with production impact.
3. `Medium`: maintainability/performance/correctness risk with bounded impact.
4. `Low`: polish, minor clarity issues, non-blocking improvements.

## Blocking matrix
1. Always block on `Critical`.
2. Always block on `High`.
3. Block on `Medium` when category is `Security` or `Dependency`.
4. `Low` never blocks but must be tracked.

## Two-pass review protocol
1. Pass 1 (`Blind Audit`): review output artifacts/code without reading task `PLAN.md` or `FAILURE_JOURNEY.md`.
2. Publish pass-1 findings with timestamp in `review.md`.
3. Pass 2 (`Context Fit`): then read `PLAN.md` and validate requirement fit.
4. Publish pass-2 findings and final gate recommendation.
5. Evidence order required:
   - `pass_1_timestamp`
   - `plan_context_opened_at`
   - `pass_2_timestamp`
6. Rule: `pass_1_timestamp` must be earlier than `plan_context_opened_at`.

## Review checklist
1. Logic correctness against stated requirements.
2. Security posture and dependency safety.
3. Deterministic test/tracing evidence.
4. Maintainability and complexity.
5. KISS compliance (`150-400` target, warning `>500`, exception `>800`).
6. Structure and naming compliance with `ops/STRUCTURE_SPEC.md`.

## Evidence format
Use one line per finding:
`[Severity] [Category] [File/Path] [Issue] [Evidence] [Required Fix]`

## Preventive rules loop
1. ContextCurator publishes journey synthesis every three phases.
2. Reviewer updates this file with accepted preventive rules.
3. Rejected rules must include explicit rationale in synthesis report.

