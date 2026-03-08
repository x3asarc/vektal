---
name: page-content-evolution
description: Audits existing website pages to decide what actions, controls, and content blocks should exist, using Playwright and Firecrawl evidence plus structured page-state analysis. Use when the user asks what buttons/options/settings are missing, requests page-by-page functionality recommendations, or says a page feels too basic and needs product-grade interaction design without random feature bloat. Make sure to use this skill whenever the request is about page functionality, information architecture, or action-model improvements on current screens.
---

# Page Content Evolution

Convert "basic pages" into scoped, testable product surfaces.

## Outcome

This skill produces:
1. A full page inventory.
2. Evidence captures (Playwright + Firecrawl) per page.
3. Structured page-state output in JSON.
4. Recommendations for missing buttons/options/content blocks.
5. Scope verification so recommendations are realistic for the project.

## Required output files

Create or update these files:
- `.planning/page-audit/<run-id>/page_inventory.json`
- `.planning/page-audit/<run-id>/structured_page_state.json`
- `.planning/page-audit/<run-id>/recommendations.json`
- `.planning/page-audit/<run-id>/verification_report.md`

Schema reference: [`references/structured-output-schema.json`](references/structured-output-schema.json)

## Required final response format

Return a concise report in this structure:

```markdown
# Page Content Evolution Report

## Scope Context
- Product goal:
- In-scope constraints:
- Out-of-scope boundaries:

## Pages Audited
1. /...
2. /...

## Highest Impact Gaps
1. ...
2. ...
3. ...

## Recommended Buttons and Options
- Page: /settings
  - Add:
  - Why:
  - Validation status: in_scope | phase_later | reject

## Verification Summary
- Technical feasibility:
- Scope compliance:
- Risks:

## Next Build Order
1. ...
2. ...
3. ...
```

## Workflow

### Step 1: Read scope and constraints

Read:
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `STANDARDS.md`
- `docs/MASTER_MAP.md` (if present)

Extract:
- current phase and priority
- target users
- must-have workflows
- explicit non-goals

Do not recommend features that violate current phase scope unless labeled `phase_later`.

### Step 2: Build page inventory

Build inventory from both:
1. Code routes (for example `frontend/src/app/**/page.tsx`)
2. Runtime URLs (base URL + known app navigation paths)

Store in `page_inventory.json`.

Minimum inventory fields:
- `page_id`
- `route`
- `source` (`code`, `runtime`, or `both`)
- `is_settings_page`
- `requires_auth`

### Step 3: Capture evidence for each page (mandatory)

Use both capture methods:

1. Playwright screenshots (desktop and mobile)
2. Firecrawl scrape with screenshot+markdown

Use the helper script:
- `pwsh .codex/skills/page-content-evolution/scripts/capture_pages.ps1 -BaseUrl <url> -RoutesFile <json-path> -RunId <run-id>`

If helper script cannot run, execute equivalent commands manually. Do not skip either evidence source.

### Step 4: Extract structured page state

Using captured evidence, produce `structured_page_state.json` with:
- existing buttons/actions
- existing filters/options/toggles
- missing actions by user goal
- friction points (dead ends, empty states, unclear CTAs)
- information hierarchy quality

Follow exact schema in `references/structured-output-schema.json`.

### Step 5: Generate recommendations

For each page, recommend:
- missing primary CTA
- missing secondary actions
- missing user options/settings controls
- missing status feedback and empty/error/loading states

Each recommendation must include:
- user value
- implementation complexity (`low|medium|high`)
- dependency requirements
- scope decision (`in_scope|phase_later|reject`)

### Step 6: Verify recommendation quality

Apply verification checks from [`references/verification-rubric.md`](references/verification-rubric.md):
- scope alignment
- technical feasibility with current stack
- consistency with existing IA/navigation
- measurable user outcome

If a recommendation fails two or more checks, mark it `reject`.

### Step 7: Produce build order

Generate a prioritized sequence:
1. High impact + low complexity + in-scope
2. High impact + medium complexity + in-scope
3. Phase-later ideas

## Tooling rules

- Playwright and Firecrawl evidence capture is mandatory for this skill.
- Do not rely only on source code inspection.
- Prefer deterministic checks over aesthetic opinions.
- Keep recommendations grounded in current project phase.

## Supporting files

- Schema: `references/structured-output-schema.json`
- Verification rules: `references/verification-rubric.md`
- Capture helper: `scripts/capture_pages.ps1`
