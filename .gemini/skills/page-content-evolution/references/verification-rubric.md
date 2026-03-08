# Verification Rubric

Apply this rubric to every recommendation.

## 1) Scope alignment

Pass when:
- recommendation supports current roadmap phase
- required backend/data dependencies are available or planned now

Fail when:
- it requires major capabilities not in current phase
- it conflicts with explicit non-goals

## 2) Technical feasibility

Pass when:
- current frontend stack can support it without high-risk rewrites
- needed APIs/configuration are realistically available

Fail when:
- it needs unavailable services, unsupported infra, or speculative dependencies

## 3) Information architecture consistency

Pass when:
- it matches existing page hierarchy/navigation model
- it does not introduce duplicated or conflicting actions

Fail when:
- it creates unclear interaction paths or redundant controls

## 4) Measurable user outcome

Pass when:
- success can be measured (conversion, completion rate, reduced drop-off, fewer dead ends)

Fail when:
- value is aesthetic-only with no clear behavioral impact

## Decision rule

- `in_scope`: 4/4 passes
- `phase_later`: 2-3 passes with clear future dependency
- `reject`: 0-1 passes or fails scope alignment plus one additional check

