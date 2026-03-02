---
status: complete
phase: 15-self-healing-dynamic-scripting
source: [15-01-SUMMARY.md, 15-02-SUMMARY.md, 15-03-SUMMARY.md, 15-04-SUMMARY.md, 15-05-SUMMARY.md, 15-06-SUMMARY.md, 15-07-SUMMARY.md, 15-08-SUMMARY.md, 15-09-SUMMARY.md, 15-10-SUMMARY.md, 15-11a-SUMMARY.md, 15-11b-SUMMARY.md]
started: 2026-03-02T12:00:00Z
updated: 2026-03-02T22:55:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Sandbox 6-gate verification executes all gates
expected: Running sandbox verification should execute all six gates (syntax, type, unit, contract, governance, rollback) and return verdicts (GREEN/YELLOW/RED) for each gate. The sandbox should use Docker with hardened security (network=none, read-only filesystem, dropped capabilities).
result: pass

### 2. SandboxRun persistence stores verification results
expected: After a sandbox run completes, the results should be persisted in the `sandbox_runs` database table with verdict, gate results, blast radius, logs, and rollback notes. The persistence should fail-open when database context is unavailable.
result: pass

### 3. Session context loading retrieves recent context
expected: Running the session context loader (CLI or programmatically) should retrieve: 5 recent commits, current phase/plan info, roadmap summary, and optionally remedies. The output should be compact YAML with token estimates and should cache repeated reads.
result: pass

### 4. Memory loader uses graph-first with local fallback
expected: Memory loader should query Neo4j graph first for commits/remedies, but fall back to local git log and markdown parsing when graph is unavailable. All queries should work safely even without graph connectivity.
result: pass

### 5. Root cause classifier categorizes failures correctly
expected: The classifier should analyze errors and categorize them as infrastructure, code, config, or unknown. It should use patterns first, then graph analysis, then LLM fallback. Common errors (ConnectionError, ImportError, TimeoutError) should be correctly categorized.
result: pass

### 6. Remediation orchestrator routes issues to correct remediator
expected: When an issue is classified, the orchestrator should route it to the appropriate remediator (redis, bash_agent, llm_code_remediator, etc.) based on the category. Results should be logged to `.graph/remediation-outcomes.jsonl`.
result: pass

### 7. Fix generator uses templates before LLM
expected: Fix generation should first check for matching templates (based on module:error_type fingerprint) before calling LLM. Template matches should return immediately with high confidence. Novel failures should trigger LLM generation with session context.
result: pass

### 8. LLM remediator enforces sandbox gates for auto-apply
expected: LLM-generated fixes should go through sandbox verification. Only fixes with GREEN verdict AND confidence >= 0.9 should be marked as auto_apply_ready. Fixes with GREEN + confidence >= 0.7 should require approval. RED verdict or low confidence should be blocked.
result: pass

### 9. Template extraction promotes successful fixes
expected: After a fix is applied successfully 2+ times (tracked via SandboxRun in Neo4j), it should be automatically promoted to the template library. The template should be stored in both Neo4j (truth) and PostgreSQL (cache) for fast retrieval.
result: pass

### 10. Template sync CLI updates PostgreSQL cache from graph
expected: Running `python scripts/graph/promote_to_template.py sync-cache` should synchronize all templates from Neo4j to the PostgreSQL remedy_template_cache table using upsert logic.
result: pass

### 11. Sentry integration normalizes and routes issues
expected: When a Sentry issue payload is received, it should be normalized (extracting error_type and error_message from metadata), classified, and routed to the appropriate remediator. The flow should work for infrastructure failures (Redis ConnectionError) and code failures (ImportError).
result: pass

### 12. Bash agent executes only allowlisted infrastructure commands
expected: The bash agent should only execute allowed commands (docker restart redis, docker restart backend, redis-cli FLUSHDB). Any non-allowlisted command or destructive flag should be blocked. The agent should respect the kill-switch for infrastructure auto-apply.
result: pass

### 13. Kill-switch blocks autonomous infrastructure actions
expected: When the infrastructure_auto_apply kill-switch is set (via CLI or programmatically), the bash agent should refuse to execute any remediation commands and return a blocked status.
result: pass

### 14. Performance profiler persists metrics to JSONL
expected: The performance profiler should collect query/API latency and memory metrics and persist them to `.graph/performance-metrics.jsonl`. Metrics should survive restarts and be queryable for 24-hour lookback.
result: pass

### 15. Bottleneck detector identifies slow queries with graph impact
expected: The bottleneck detector should identify repeatedly slow queries/functions and use the Phase 14 knowledge graph to find caller functions. It should generate actionable recommendations (e.g., add index) with confidence scores.
result: pass

### 16. Telemetry dashboard shows week-over-week trends
expected: The telemetry dashboard should calculate P95 latency and error rates for the current period and compare against 7-day-ago baseline. The dashboard should display week-over-week (W-o-W) improvement metrics.
result: pass

### 17. Runtime optimizer tunes parameters based on metrics
expected: The runtime optimizer should auto-tune SQLAlchemy connection pools, cache TTL, and batch sizes based on current system metrics (queue depth, memory pressure, API latency). Tuning proposals should be generated with specific parameter changes.
result: pass

### 18. Optimizer remediator validates tuning via sandbox
expected: Parameter tuning proposals from the runtime optimizer should go through sandbox verification before being applied. The optimizer remediator should generate config diffs and verify they pass all gates.
result: pass

### 19. A/B test validator ensures statistical significance
expected: The A/B test validator should require minimum 30 samples per group and p < 0.05 significance before declaring an optimization successful. Statistical validation should use T-test from scipy.
result: pass

### 20. Sentry feedback loop validates fix efficacy
expected: The feedback loop should monitor Sentry issues after remediation is applied. A fix is considered validated only if: the Sentry issue is resolved AND no new activity occurred after the remediation timestamp. Validated fixes should be eligible for template promotion.
result: pass

### 21. Sentry client queries issue lifecycle
expected: The Sentry client should query the Sentry API to retrieve issue status and activity timeline. It should support both live API mode (with SENTRY_AUTH_TOKEN) and fail-open/mock mode for testing.
result: pass

### 22. Remedy efficacy CLI reports validation status
expected: Running `python scripts/graph/validate_remedy_efficacy.py --hours 24` should report counts of validated fixes (issue resolved + no recurrence), failed fixes (recurring activity), and pending fixes (not yet resolved).
result: pass

### 23. Approval queue persists pending fixes to database
expected: Medium-confidence fixes (0.7 <= confidence < 0.9) should be stored in the `pending_approvals` database table with full context: fix diff, confidence score, sandbox results, priority level. Each approval should have a unique approval_id (UUID) and 72-hour TTL.
result: pass

### 24. Approval API allows listing pending fixes
expected: `GET /api/v1/approvals/` should return a list of pending approvals with filtering by status (pending/approved/rejected). Each item should include approval_id, module, error_type, confidence, priority, and created_at.
result: pass

### 25. Approval API allows viewing fix details
expected: `GET /api/v1/approvals/<id>` should return full fix details including: the proposed code changes (git diff), sandbox verification results, confidence score, and session context that was used to generate the fix.
result: pass

### 26. Approval API allows approving fixes
expected: `POST /api/v1/approvals/<id>/approve` should mark the fix as approved and trigger its application. The approval should record resolved_by (user ID) and resolution timestamp.
result: pass

### 27. Approval API allows rejecting fixes
expected: `POST /api/v1/approvals/<id>/reject` with a resolution_note should mark the fix as rejected and prevent its application. The rejection reason should be stored for learning.
result: pass

### 28. Approval queue frontend supports load/approve/reject flows
expected: `ApprovalQueue` should load from `/api/v1/approvals/`, approve/reject via API endpoints, and remove resolved items from the queue while showing empty-state correctly.
result: pass

## Summary

total: 28
passed: 28
issues: 0
pending: 0
skipped: 0

## Gaps

[none - all tests passed]

## Test Suite Results

All Phase 15 automated tests passed successfully:

- `test_sandbox_verifier.py`: 8 passed
- `test_session_primer.py`: 6 passed
- `test_root_cause_classifier.py`: 7 passed
- `test_fix_generation.py`: 6 passed
- `test_template_extraction.py`: 5 passed
- `test_sentry_integration.py`: 6 passed
- `test_bash_agent.py`: 5 passed
- `test_performance_profiling.py`: 7 passed
- `test_runtime_optimizer.py`: 5 passed
- `test_sentry_feedback.py`: 3 passed
- `test_approvals_api.py`: 4 passed
- `ApprovalQueue.test.tsx`: 4 passed

**Total: 66 automated tests passed, 0 failed**

Phase 15 Self-Healing & Runtime Optimization is fully implemented and operational.
