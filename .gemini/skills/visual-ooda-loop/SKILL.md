---
name: visual-ooda-loop
description: Orchestrates a visual verification loop for frontend changes. Use Playwright and Firecrawl to capture live visual evidence from localhost or public URLs, then analyze for congruence with the implementation plan and design tokens. Make sure to use this skill after frontend changes are pushed and technical deployment gates have passed.
---

# Visual OODA Loop

Provides high-fidelity visual verification by automating the **Observe** and **Orient** phases of the OODA loop.

---

## When to Use

- After pushing frontend changes to verify visual accuracy.
- When the implementation plan (PLAN.md) contains specific UI elements that must be verified.
- When `design-tokens-v2.json` is provided and must be enforced visually.
- After `deployment-validator` passes its technical checks, to ensure visual quality.

---

## Workflow

### 1. Observe (Capture Evidence)
Capture live screenshots and structural markdown from the running application.

**Commands:**
- `pwsh scripts/visual/capture_evidence.ps1 -BaseUrl "http://localhost:3000" -RunId "ooda-01"`
- `firecrawl scrape "http://localhost:3000" --format markdown,screenshot`

### 2. Orient (Analyze Congruence)
Compare the captured state against the source of truth.

**Checks:**
- **Plan Compliance**: Are all elements promised in `PLAN.md` present in the markdown?
- **Design Integrity**: Do colors and typography match `design-tokens-v2.json`?
- **Regression Check**: Compare current screenshots with baseline images in `/images/`.

### 3. Decide (Verdict)
Issue a satisfaction score and identify next actions.

**Output Structure:**
```markdown
# Visual Verification Report

## Evidence
- Screenshot: [path/to/screenshot.png]
- Structural Capture: [path/to/capture.json]

## Congruence Analysis
- Plan vs. Reality: [Match | Partial | Mismatch]
- Token Adherence: [Compliant | Non-compliant]

## Verdict
- Satisfaction: [0-100]
- Status: [SATISFACTORY | REMEDIATION_REQUIRED]
- Recommended Fixes: (if remediation required)
```

---

## Integration

- **Previous Skill**: `deployment-validator` (Technical Gates)
- **Current Skill**: `visual-ooda-loop` (Visual Gates)
- **Next Skill (on FAIL)**: `frontend-design` (Targeted Remediation)
- **Next Skill (on PASS)**: None (Loop Closed)

---

## Support Scripts
- `scripts/visual/capture_evidence.ps1`: Automated screenshot and scrape capture.
- `scripts/visual/analyze_congruence.py`: Objective comparison logic.
