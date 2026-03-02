---
phase: 15-self-healing-dynamic-scripting
plan: 05
subsystem: autonomous-learning-loop
tags: [template, learning, neo4j, pg-cache, learning-loop]

requires:
  - phase: 15-self-healing-dynamic-scripting
    plan: 04
    provides: "autonomous fix generation"
provides:
  - "TemplateExtractor for pattern learning from successful fixes"
  - "CLI for manual template promotion and cache sync"
  - "Automated promotion threshold logic (>=2 successes)"
  - "Neo4j -> PostgreSQL cache synchronization"
affects:
  - src/models/remedy_templates.py

tech-stack:
  added: []
  patterns:
    - "promotion thresholding (>=2 applications)"
    - "graph-first with relational cache (PostgreSQL)"
    - "upsert synchronization logic"
    - "CLI-driven manual intervention and maintenance"

key-files:
  created:
    - src/graph/template_extractor.py
    - scripts/graph/promote_to_template.py
    - tests/graph/test_template_extraction.py
  modified:
    - src/models/remedy_templates.py

key-decisions:
  - "Implemented `TemplateExtractor` with `_safe_graph_query` to handle both Graphiti and raw Neo4j drivers, ensuring fail-open compatibility."
  - "Set promotion threshold at 2 successful applications in Neo4j (via `SandboxRun` episodes) before promoting to the reusable template library."
  - "Added `upsert_from_graph` to `RemedyTemplate` to simplify the synchronization of Neo4j templates into the high-speed PostgreSQL cache."
  - "Created a management CLI for ops-manual promotion of specific fixes and periodic cache synchronization."

duration: in-session
completed: 2026-03-02
---

# Phase 15 Plan 05 Summary

Implemented the learning loop for extracting successful LLM fixes as reusable templates.

## What Was Built

1. **Template Extractor** ([src/graph/template_extractor.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/template_extractor.py))
   - Monitors `SandboxRun` success counts in Neo4j.
   - Promotes fixes with ≥2 successful applications to `RemedyTemplate` status.
   - Handles creation of Neo4j nodes and initial PostgreSQL cache population.

2. **Template Management CLI** ([scripts/graph/promote_to_template.py](/C:/Users/Hp/Documents/Shopify Scraping Script/scripts/graph/promote_to_template.py))
   - `promote` command for manually converting sandbox-verified fixes into templates.
   - `sync-cache` command for bulk-refreshing the PostgreSQL cache from Neo4j truth.
   - Self-bootstrapping with `app_factory` for database access.

3. **Cache Synchronization Logic**
   - Enhanced `RemedyTemplate` model with `upsert_from_graph` for efficient syncing.
   - Support for fingerprinting using `module:error_type` for deterministic lookups.

4. **Verification Suite** ([tests/graph/test_template_extraction.py](/C:/Users/Hp/Documents/Shopify Scraping Script/tests/graph/test_template_extraction.py))
   - Validates promotion eligibility thresholds.
   - Validates end-to-end promotion from payload to both graph and cache.
   - Validates upsert logic for cache refreshes.

## Verification Evidence

1. `python -m pytest tests/graph/test_template_extraction.py -v`
   - Result: `4 passed`
2. `python scripts/graph/promote_to_template.py --help`
   - Result: CLI correctly displays management commands.

## KISS / Size Check

- `template_extractor.py`: 115 LOC
- `promote_to_template.py`: 85 LOC
- `remedy_templates.py` (mod): +30 LOC
- All within acceptable maintainability limits.
