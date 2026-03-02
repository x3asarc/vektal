---
phase: 15-self-healing-dynamic-scripting
plan: 03
subsystem: failure-classification-orchestration
tags: [root-cause, graph, llm, routing, remediation]

requires:
  - phase: 15-self-healing-dynamic-scripting
    plan: 02
    provides: "session context and memory loader"
  - phase: 15-self-healing-dynamic-scripting
    plan: 03
    provides: "15-03-PLAN requirements"
provides:
  - "3-tier RootCauseClassifier (pattern -> graph -> LLM)"
  - "Classification-aware remediation orchestrator"
  - "CLI wrapper bridged to reusable orchestration module"
  - "Classifier/orchestrator unit test coverage"
affects:
  - scripts/graph/orchestrate_healers.py

tech-stack:
  added: []
  patterns:
    - "deterministic-first routing with confidence gates"
    - "graph-assisted inference with fail-open query execution"
    - "LLM fallback with strict JSON parsing + unknown fallback"
    - "outcome journaling for future learning loop phases"

key-files:
  created:
    - src/graph/root_cause_classifier.py
    - src/graph/orchestrate_healers.py
    - tests/graph/test_root_cause_classifier.py
  modified:
    - scripts/graph/orchestrate_healers.py

key-decisions:
  - "Kept legacy `--category/--event_id` behavior but delegated execution to new `src/graph/orchestrate_healers.py` to avoid script-only logic drift."
  - "Implemented graph query fallback forms covering both relationship-style (`:IMPORTS`, `:CALLS`) and edge-entity-style (`ImportsEdge`, `CallsEdge`) schemas."
  - "Used fail-open behavior for graph and LLM unavailability: classifier returns `unknown` instead of crashing orchestration."
  - "Added durable JSONL outcome logging under `.graph/remediation-outcomes.jsonl` for Phase 15 learning-loop consumption."

duration: in-session
completed: 2026-03-02
---

# Phase 15 Plan 03 Summary

Implemented root-cause classification and integrated it into remediation orchestration.

## What Was Built

1. Root cause classifier ([root_cause_classifier.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/root_cause_classifier.py))
   - 3-tier strategy:
     - deterministic patterns
     - graph analysis
     - LLM fallback
   - Supports categories: `infrastructure`, `code`, `config`, `unknown`
   - Includes graph-evidence extraction from imports/calls/recent commits
   - Includes historical matching against `FAILURE_JOURNEY.md`
   - Includes resilient LLM parsing with hard fallback to `unknown`

2. Classification-aware orchestration module ([orchestrate_healers.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/orchestrate_healers.py))
   - Added `normalize_sentry_issue(...)`
   - Added `orchestrate_remediation(...)` async flow:
     - normalize issue
     - classify
     - route to remediator
     - execute via `NanoFixerLoop`
     - persist outcome log entry
   - Added category/service routing strategy with backward compatibility

3. CLI wrapper update ([scripts/graph/orchestrate_healers.py](/C:/Users/Hp/Documents/Shopify Scraping Script/scripts/graph/orchestrate_healers.py))
   - Delegates to `src.graph.orchestrate_healers`
   - Supports legacy mode: `--category`, `--event_id`
   - Supports classification mode: `--issue-json`

4. Tests ([test_root_cause_classifier.py](/C:/Users/Hp/Documents/Shopify Scraping Script/tests/graph/test_root_cause_classifier.py))
   - Pattern-based infra/code classification
   - Graph-based import failure classification
   - LLM fallback and LLM-failure behavior
   - Orchestrator dispatch and manual-required behavior

## Verification Evidence

1. `python -m py_compile src/graph/root_cause_classifier.py src/graph/orchestrate_healers.py scripts/graph/orchestrate_healers.py tests/graph/test_root_cause_classifier.py`
   - Result: passed
2. `python -m pytest tests/graph/test_root_cause_classifier.py -q`
   - Result: `7 passed`
3. Smoke call:
   - `python -c "...orchestrate_remediation(...)"` with novel issue
   - Result: `manual_required` (expected fail-open when no confident route/LLM path unavailable)

## Notes

1. Environment has network restrictions; OpenRouter fallback can fail and is intentionally handled as `unknown` with no crash.
2. Existing warnings unrelated to this task persist (`python-dotenv` parse warnings and pytest cache permission warnings).
