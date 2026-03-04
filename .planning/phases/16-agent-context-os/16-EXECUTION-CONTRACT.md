# Phase 16 Ascending Execution Contract

Status: ACTIVE  
Applies to: `16-01-PLAN.md` through `16-07-PLAN.md`

---

## Rule 1: Strict Ascending Order

Execute plans in this exact order only:

1. `16-01-PLAN.md`
2. `16-02-PLAN.md`
3. `16-03-PLAN.md`
4. `16-04-PLAN.md`
5. `16-05-PLAN.md`
6. `16-06-PLAN.md`
7. `16-07-PLAN.md`

No parallel execution across these plans is allowed.

---

## Rule 2: Mandatory Replan Before Each Next Plan

After finishing plan `N`, plan `N+1` must be rewritten before any implementation starts.

Required process:

1. Read prior summary: `.planning/phases/16-agent-context-os/16-NN-SUMMARY.md`
2. Extract delivered assets:
   - actual file paths created
   - exported functions/classes/CLI commands
   - constraints and known limitations
3. Update next plan in-place:
   - fill all `[[UPSTREAM_*]]` placeholders
   - replace any assumed paths/APIs with actual delivered ones
   - adjust tasks and verification commands to use real outputs
4. Save replan evidence:
   - `.planning/phases/16-agent-context-os/16-NN-to-16-(NN+1)-REPLAN.md`
5. Gate:
   - if unresolved placeholders remain, status is `RED` and execution cannot proceed.

---

## Rule 3: Summary Contract Per Plan

Each completed plan must publish:

1. `.planning/phases/16-agent-context-os/16-NN-SUMMARY.md`

Minimum required fields:

1. `Delivered Files`
2. `Exported APIs and Commands`
3. `Config and Environment Changes`
4. `Metrics Collected`
5. `Known Limits`
6. `Handoff to Next Plan`

---

## Rule 4: Binary Gates

Every plan execution must end with one outcome:

1. `GREEN`: all plan criteria met with evidence.
2. `RED`: any required criterion missing or placeholder unresolved.

