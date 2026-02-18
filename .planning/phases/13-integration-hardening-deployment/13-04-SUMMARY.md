---
phase: 13-integration-hardening-deployment
plan: 04
subsystem: instrumentation-foundation
tags: [instrumentation, preference-signals, verification-signals, export, dpo-ready, rlvr-ready]
requires:
  - phase: 13-integration-hardening-deployment
    provides: "13-01..13-03 runtime, governance, and deploy observability contracts"
provides:
  - "Durable preference and verification signal persistence schemas"
  - "Tier-aware runtime signal emission on approval/apply paths"
  - "Scoped instrumentation export with deterministic join-integrity reporting"
key-files:
  created:
    - src/models/assistant_preference_signal.py
    - src/models/assistant_verification_signal.py
    - migrations/versions/e5f6a7b8c9d0_phase13_instrumentation_foundation.py
    - src/assistant/instrumentation/__init__.py
    - src/assistant/instrumentation/signals.py
    - src/assistant/instrumentation/export.py
    - tests/api/test_preference_signal_contract.py
    - tests/api/test_oracle_signal_join_contract.py
    - tests/api/test_instrumentation_export_contract.py
  modified:
    - src/models/__init__.py
    - src/api/v1/chat/approvals.py
    - src/api/v1/chat/routes.py
    - src/api/v1/ops/routes.py
completed: 2026-02-16
---

# Phase 13-04 Summary

Implemented Phase 13 wave-4 instrumentation foundation for preference/verification telemetry capture and export, with explicit no-autonomy guardrails.

## Delivered

- Added instrumentation persistence contracts:
  - `assistant_preference_signals` for approval/edit/thumb-style human signals.
  - `assistant_verification_signals` for binary oracle outcomes with status/timing metadata.
- Added instrumentation services:
  - runtime context extraction (`tier`, `correlation_id`, `reasoning_trace_tokens`, `cost_usd`),
  - mandatory correlation-link enforcement for Tier 2/3 paths,
  - preference and verification signal capture helpers,
  - scoped export with deterministic join-integrity stats.
- Wired emission hooks:
  - non-bulk product approval emits preference signals,
  - non-bulk product apply emits verification signals linked to oracle event lineage,
  - bulk approval/apply paths now carry correlation-aware runtime metadata and emit instrumentation signals.
- Added ops export API:
  - `POST /api/v1/ops/instrumentation/export`
  - supports tenant scope + tier/correlation/action/time-window filters.
- Enforced phase boundary:
  - export payload marks `autonomy_enabled: false`,
  - no training/execution-autonomy loop introduced in Phase 13.

## Verification

- `python -m pytest -q tests/api/test_preference_signal_contract.py tests/api/test_oracle_signal_join_contract.py tests/api/test_instrumentation_export_contract.py` -> `6 passed`

Result: `GREEN` for Phase `13-04` required instrumentation contract suites.

## Binary Gates

- `INTEGRATE-06`: `GREEN`
- `INTEGRATE-08`: `GREEN`

## Notes

- Join integrity is reported explicitly (`missing_verification_links`, `missing_preference_links`) to support downstream DPO/RLVR dataset quality checks without enabling autonomous adaptation in this phase.
- Tier-2/3 instrumentation now hard-fails when correlation linkage is missing, preventing orphaned telemetry in governed execution paths.
