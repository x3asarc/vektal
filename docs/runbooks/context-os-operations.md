# Context OS Operations Runbook

## Purpose

Operate and recover Phase 16 Context OS with binary gate evidence from:

- `python scripts/governance/context_os_gate.py --window-hours 24`
- `python scripts/governance/context_os_report.py --format markdown`

## GREEN/RED Contract

- `GREEN`: all gate metrics pass in the selected time window.
- `RED`: one or more gate metrics fail and include reason codes with remediation.

## Standard Recovery Sequence

1. Run `python scripts/governance/context_os_report.py --format markdown`.
2. Read failed `reason_code` values.
3. Apply the matching remediation section below.
4. Re-run gate command until status is `GREEN`.

## Degraded Graph Mode

When `graph_attempt_rate` fails or graph backends are unavailable:

1. Check runtime backend state:
   - `python scripts/governance/ensure_neo4j_runtime.py`
2. Probe context path:
   - `python scripts/context/context_query_probe.py --query "what triggers what for pre_tool hook"`
3. Confirm fallback is reason-coded:
   - expect `fallback_reason` in telemetry (`graph_empty`, `graph_error`, `docs_used`, or `baseline_used`).
4. If graph remains unavailable, keep service live with fallback and open a runtime issue with gate output attached.

## Stale Doc Recovery

When `context_freshness` fails (`DOC_MISSING` or `DOC_STALE`):

1. Run session/doc refresh commands:
   - `python scripts/memory/session_start.py`
   - `python scripts/context/build_agent_primer.py`
   - `python scripts/context/build_folder_summaries.py`
   - `python scripts/context/build_context_link_map.py`
2. Confirm docs exist and are fresh:
   - `docs/AGENT_START_HERE.md`
   - `docs/FOLDER_SUMMARIES.md`
   - `docs/CONTEXT_LINK_MAP.md`
3. Re-run gate.

## Hook Latency Spike Triage

When `hook_latency` fails (`HOOK_LATENCY_P95_HIGH` or `HOOK_BLOCKING_INCIDENT`):

1. Inspect recent pre-tool telemetry in `.memory/events/*.jsonl`.
2. Confirm every `pre_tool` event contains `payload.broker_telemetry.latency_ms`.
3. Remove expensive work from hot path in `scripts/memory/pre_tool_update.py`.
4. Keep hook fail-open behavior (never block command flow).
5. Re-run:
   - `python scripts/governance/context_os_gate.py --window-hours 24 --json`

## Fallback-Rate Spike Triage

Fallbacks are expected during graph issues, but sustained spikes indicate drift.

1. Inspect fallback signals from event telemetry:
   - `payload.broker_telemetry.fallback_used`
   - `payload.broker_telemetry.fallback_reason`
2. If most events are `fallback_used=true` with `graph_error`, prioritize backend runtime fix.
3. If most are `docs_used` or `baseline_used`, improve graph coverage and query routing.
4. Validate improvement with:
   - `python scripts/governance/context_os_report.py --format json`

## Cross-Terminal Visibility Checks

When `cross_terminal_visibility` fails:

1. Ensure at least two terminals are writing pre-tool events with distinct session keys.
2. Trigger activity in both terminals within 5 seconds.
3. Verify events in `.memory/events/YYYY-MM-DD.jsonl` show alternating `session_id` timestamps.
4. Re-run gate and confirm metric returns `PASS`.
