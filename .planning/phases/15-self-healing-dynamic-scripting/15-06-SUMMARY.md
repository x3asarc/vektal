---
phase: 15-self-healing-dynamic-scripting
plan: 06
subsystem: sentry-remediation-integration
tags: [sentry, integration, observability, self-healing]

requires:
  - phase: 14.3
    provides: "sentry ingestor"
  - phase: 15-self-healing-dynamic-scripting
    plan: 03
    provides: "failure classification and orchestration"
provides:
  - "Robust Sentry issue normalization"
  - "End-to-end integration tests for Sentry -> remediation flow"
  - "Manual integration test script for observability verification"
affects:
  - src/graph/orchestrate_healers.py

tech-stack:
  added: []
  patterns:
    - "Sentry payload normalization with metadata fallback"
    - "Async orchestration testing with AsyncMock"
    - "cross-phase capability validation (14.3 + 15.0)"

key-files:
  created:
    - tests/graph/test_sentry_integration.py
    - scripts/observability/test_sentry_flow.py
  modified:
    - src/graph/orchestrate_healers.py

key-decisions:
  - "Updated `normalize_sentry_issue` to robustly extract `error_type` and `error_message` from Sentry's `metadata` object, ensuring compatibility with standard Sentry payloads."
  - "Utilized `AsyncMock` in tests to correctly simulate the asynchronous `fix_service` dispatch in the orchestrator."
  - "Verified that the root-cause classifier correctly routes Sentry issues to specialized remediators (e.g., 'redis') or the general 'code_fix' remediator based on normalized metadata."

duration: in-session
completed: 2026-03-02
---

# Phase 15 Plan 06 Summary

Verified and hardened the integration between Phase 14.3 Sentry ingestion and Phase 15 self-healing orchestration.

## What Was Built

1. **Robust Normalization** ([src/graph/orchestrate_healers.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/orchestrate_healers.py))
   - Enhanced `normalize_sentry_issue` to handle standard Sentry `metadata` structures (mapping `metadata.type` to `error_type` and `metadata.value` to `error_message`).
   - Ensured fallback to title/culprit when metadata is missing.

2. **Sentry Integration Tests** ([tests/graph/test_sentry_integration.py](/C:/Users/Hp/Documents/Shopify Scraping Script/tests/graph/test_sentry_integration.py))
   - Async integration tests covering:
     - Infrastructure failure flow (Redis ConnectionError).
     - Code failure flow (ImportError).
     - Config failure flow (TimeoutError).
     - Normalization correctness.

3. **Manual Flow Validator** ([scripts/observability/test_sentry_flow.py](/C:/Users/Hp/Documents/Shopify Scraping Script/scripts/observability/test_sentry_flow.py))
   - CLI script to manually trigger a mocked Sentry-to-remediation flow.
   - Prints full JSON orchestration outcomes for verification.

## Verification Evidence

1. `python -m pytest tests/graph/test_sentry_integration.py -v`
   - Result: `4 passed`
2. `python scripts/observability/test_sentry_flow.py`
   - Result: Verified successful routing and remediation outcomes for both infra and code failures.

## KISS / Size Check

- `orchestrate_healers.py` (mod): minimal changes to normalization logic.
- Test files remain focused and small.
