# journey-synthesis-14-16

Owner: ContextCurator
Cadence: end of every three phases

## Phase range covered
`14-16`

## Repeated failure patterns
1. Graph capability existed but was not enforced as first-hop retrieval across all runtime paths.
2. Context docs and summaries drifted unless regeneration was tied to lifecycle hooks and SHA/freshness checks.
3. Memory behavior was difficult to audit before canonical append-only event envelopes and deterministic materializers.
4. Cross-terminal visibility assumptions failed without explicit session-key evidence and timing metrics.

## Promoted preventive rules
1. Enforce a single graph-first context broker with reason-coded fallback telemetry on every retrieval call.
2. Keep append-only events canonical and treat all working/short/long memory artifacts as replayed views.
3. Gate context health with binary `GREEN|RED` metrics (freshness, graph attempts, token budget, hook latency, cross-terminal visibility).
4. Require phase-close verification harness output before updating lifecycle files (`ROADMAP.md`, `STATE.md`).

## Proposed STANDARDS.md updates
1. Add a Context OS section defining mandatory broker telemetry fields and acceptance thresholds.
2. Add a phase-close requirement that onboarding docs (`AGENT_START_HERE`, `FOLDER_SUMMARIES`, `CONTEXT_LINK_MAP`) must be fresh within 24h or regenerated in-session.
3. Add a governance note that cross-terminal memory claims require timestamped multi-session evidence.

## Accepted vs rejected changes
1. Accepted: strict ascending replan contract for Phase 16 (`16-N -> 16-(N+1)` placeholder hard rewrite) | rationale: prevented drift between plan assumptions and actual upstream outputs.
2. Accepted: context gate/report/runbook split (`context_os_gate.py`, `context_os_report.py`, operations runbook) | rationale: gives both machine and operator evidence paths.
3. Rejected: qualitative closure without binary harness evidence | rationale: violates governance baseline and made readiness non-auditable.
