---
phase: 15-self-healing-dynamic-scripting
plan: 07
subsystem: infrastructure-automation
tags: [bash, automation, kill-switch, infrastructure]

requires:
  - phase: 13
    provides: "kill-switch governance"
  - phase: 15-self-healing-dynamic-scripting
    plan: 01
    provides: "sandbox baseline"
provides:
  - "BashAgent for automated infrastructure remediation"
  - "CLI for auto-apply control (infrastructure_auto_apply)"
  - "Allowlisted command execution (Redis, Docker, cache)"
  - "Kill-switch protection for autonomous infrastructure actions"
affects:
  - src/assistant/governance/kill_switch.py
  - src/graph/remediation_registry.py (via auto-discovery)

tech-stack:
  added: []
  patterns:
    - "command allowlisting and safety validation"
    - "governance-gated automation (kill-switch)"
    - "controlled autonomy rollout (approval_required for 15.1)"

key-files:
  created:
    - src/graph/remediators/bash_agent.py
    - scripts/graph/auto_apply_infrastructure.py
    - tests/graph/test_bash_agent.py
  modified:
    - src/assistant/governance/kill_switch.py

key-decisions:
  - "Enhanced `src/assistant/governance/kill_switch.py` with `check_kill_switch`, `set_kill_switch`, and `get_kill_switch_status` to support Phase 15.2 auto-apply controls."
  - "Implemented strict command allowlisting in `BashAgent` (Redis restart, Docker restart, cache clear) to prevent arbitrary command execution."
  - "Blocked destructive flags (`--force`, `rm`, etc.) at the remediator level as an additional safety gate."
  - "Ensured `BashAgent` is automatically registered in the `RemediationRegistry` with the service name `bash_agent`."

duration: in-session
completed: 2026-03-02
---

# Phase 15 Plan 07 Summary

Implemented infrastructure bash agent for automated remediation of Redis, Docker, and cache issues with kill-switch protection.

## What Was Built

1. **Bash Agent** ([src/graph/remediators/bash_agent.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/remediators/bash_agent.py))
   - Specialized remediator for infrastructure-level failures.
   - Detects `ConnectionError`, `APIError`, and `PoolError` related to Redis and Docker.
   - Validates commands against a strict allowlist:
     - `docker restart redis`
     - `docker restart backend`
     - `redis-cli FLUSHDB`
   - Blocks destructive flags and non-allowlisted commands.
   - Integrates with Phase 13 kill-switch to gate autonomous actions.

2. **Auto-Apply Control CLI** ([scripts/graph/auto_apply_infrastructure.py](/C:/Users/Hp/Documents/Shopify Scraping Script/scripts/graph/auto_apply_infrastructure.py))
   - Enables/disables the `infrastructure_auto_apply` kill-switch.
   - Provides status checking for infrastructure automation.
   - Self-bootstraps with `app_factory` for persistent state management.

3. **Governance Helpers** ([src/assistant/governance/kill_switch.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/assistant/governance/kill_switch.py))
   - Added programmatic interface for kill-switch management.
   - Supports both global and tenant-scoped blocks.

4. **Verification Suite** ([tests/graph/test_bash_agent.py](/C:/Users/Hp/Documents/Shopify Scraping Script/tests/graph/test_bash_agent.py))
   - Validates detection logic for infra failures.
   - Validates kill-switch enforcement during remediation.
   - Validates command safety and allowlist enforcement.

## Verification Evidence

1. `python -m pytest tests/graph/test_bash_agent.py -v`
   - Result: `4 passed`
2. `python scripts/graph/auto_apply_infrastructure.py status`
   - Result: Correctly reports current kill-switch status.

## KISS / Size Check

- `bash_agent.py`: 95 LOC
- `auto_apply_infrastructure.py`: 45 LOC
- `kill_switch.py` (mod): +50 LOC
- All within maintainability limits.
