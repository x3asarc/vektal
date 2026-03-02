# MASTER_MAP

Last batch update: 2026-03-02
Owner: ContextCurator

## TOC
1. Project Map (depth 3)
2. Module Index
3. Data and Logic Flow
4. Active Plans
5. Governance Links
6. Journey Synthesis Links
7. GitHub Tracked File Manifest (Complete)

## Project Map (Depth 3)
```text
.
|-- .planning/
|-- docs/
|-- reports/
|-- src/
|-- tests/
|-- frontend/
|-- scripts/
|-- ops/
`-- (full tracked filesystem tree listed below)
```

## Module Index
1. Full repository tracking snapshot: `1739` git-tracked paths (from `git ls-files`).
2. Top-level tracked path counts:
- `.claude`: `165`
- `.codex`: `5`
- `.env.example`: `1`
- `.gemini`: `5`
- `.gitattributes`: `1`
- `.github`: `6`
- `.gitignore`: `1`
- `.obsidian`: `5`
- `.planning`: `398`
- `.pre-commit-config.yaml`: `1`
- `.rules`: `1`
- `.verb.md`: `1`
- `AGENTS.md`: `1`
- `ARCHITECTURE.md`: `1`
- `CLAUDE.md`: `1`
- `Dockerfile.backend`: `1`
- `FAILURE_JOURNEY.md`: `1`
- `GEMINI.md`: `1`
- `HARNESS_GAPS.md`: `1`
- `LEARNINGS.md`: `1`
- `README.md`: `1`
- `STANDARDS.md`: `1`
- `Vektal`: `6`
- `archive`: `151`
- `claudesplan.md`: `1`
- `config`: `4`
- `demo_framework.py`: `1`
- `docker-compose.secrets.yml`: `1`
- `docker-compose.yml`: `1`
- `docs`: `49`
- `frontend`: `130`
- `gunicorn_config.py`: `1`
- `migrations`: `22`
- `nginx`: `1`
- `npm-badge-png.md`: `1`
- `ops`: `8`
- `playwright.config.ts`: `1`
- `pyproject.toml`: `1`
- `reports`: `197`
- `requirements.txt`: `1`
- `risk-policy.json`: `1`
- `scripts`: `54`
- `secrets`: `1`
- `seo`: `11`
- `solutionsos`: `3`
- `src`: `329`
- `tests`: `147`
- `utils`: `12`
- `web`: `4`

## Data and Logic Flow
1. Canonical lifecycle state is maintained in `.planning/ROADMAP.md` and `.planning/STATE.md`.
2. Governance evidence for executed tasks is stored under `reports/<phase>/<task>/`.
3. Product/runtime code is implemented in `src/`, `frontend/`, `scripts/`, and validated by `tests/`.
4. This map is generated from git-tracked paths and therefore reflects what can appear on GitHub.

## Active Plans
1. Current status: v1.0 phases through Phase 15 are complete (`GREEN`) per roadmap/state.
2. No active execution phase is open; next work is in future phases.
3. Latest closure artifacts remain under:
- `.planning/phases/14.3-graph-availability-sync/`
- `.planning/phases/15-self-healing-dynamic-scripting/`
- `reports/14.3/` and `reports/15/`

## Governance Links
1. Policy source: `solutionsos/compound-engineering-os-policy.md`
2. Governance baseline: `AGENTS.md`
3. Standards: `STANDARDS.md`
4. Structure spec: `ops/STRUCTURE_SPEC.md`
5. Canonical roadmap: `.planning/ROADMAP.md`
6. Canonical state: `.planning/STATE.md`
7. Canonical role definitions: `ops/governance/roles/README.md`

## Journey Synthesis Links
1. Template: `reports/meta/journey-synthesis-template.md`
2. Latest synthesis: `reports/meta/journey-synthesis-13-15.md`
3. Next required synthesis: end of the next 3-phase window.

## GitHub Tracked File Manifest (Complete)
Tracked path count: `1739`

```text
.
|-- .claude/
|   |-- agents/
|   |   |-- change-verifier.md
|   |   |-- code-generator.md
|   |   |-- gsd-codebase-mapper.md
|   |   |-- gsd-debugger.md
|   |   |-- gsd-executor.md
|   |   |-- gsd-integration-checker.md
|   |   |-- gsd-phase-research-deep.md
|   |   |-- gsd-phase-researcher.md
|   |   |-- gsd-plan-checker.md
|   |   |-- gsd-planner.md
|   |   |-- gsd-project-researcher.md
|   |   |-- gsd-research-synthesizer.md
|   |   |-- gsd-roadmapper.md
|   |   `-- gsd-verifier.md
|   |-- auto-improver/
|   |   |-- on_execution_complete.py
|   |   |-- pattern_detector_file_based.py
|   |   |-- pattern_detector_graph.py
|   |   `-- README.md
|   |-- checkpoints/
|   |   |-- checkpoint_1_discussion.sh
|   |   |-- checkpoint_2_research.sh
|   |   |-- checkpoint_3_plan.sh
|   |   |-- checkpoint_4_execution.sh
|   |   `-- checkpoint_4_post_hook.sh
|   |-- commands/
|   |   `-- gsd/
|   |       |-- add-phase.md
|   |       |-- add-todo.md
|   |       |-- audit-milestone.md
|   |       |-- check-todos.md
|   |       |-- complete-milestone.md
|   |       |-- compound-execute.md
|   |       |-- debug.md
|   |       |-- discuss-phase.md
|   |       |-- execute-phase.md
|   |       |-- help.md
|   |       |-- insert-phase.md
|   |       |-- join-discord.md
|   |       |-- list-phase-assumptions.md
|   |       |-- map-codebase.md
|   |       |-- new-milestone.md
|   |       |-- new-project.md
|   |       |-- new-project.md.bak
|   |       |-- pause-work.md
|   |       |-- plan-milestone-gaps.md
|   |       |-- plan-phase.md
|   |       |-- progress.md
|   |       |-- quick.md
|   |       |-- reapply-patches.md
|   |       |-- remove-phase.md
|   |       |-- research-phase.md
|   |       |-- resume-work.md
|   |       |-- set-profile.md
|   |       |-- settings.md
|   |       |-- update.md
|   |       `-- verify-work.md
|   |-- escalations/
|   |   `-- pending-improvements.json
|   |-- get-shit-done/
|   |   |-- bin/
|   |   |   |-- gsd-tools.js
|   |   |   `-- gsd-tools.test.js
|   |   |-- references/
|   |   |   |-- checkpoints.md
|   |   |   |-- continuation-format.md
|   |   |   |-- decimal-phase-calculation.md
|   |   |   |-- git-integration.md
|   |   |   |-- git-planning-commit.md
|   |   |   |-- model-profile-resolution.md
|   |   |   |-- model-profiles.md
|   |   |   |-- phase-argument-parsing.md
|   |   |   |-- planning-config.md
|   |   |   |-- questioning.md
|   |   |   |-- tdd.md
|   |   |   |-- ui-brand.md
|   |   |   `-- verification-patterns.md
|   |   |-- templates/
|   |   |   |-- codebase/
|   |   |   |   |-- architecture.md
|   |   |   |   |-- concerns.md
|   |   |   |   |-- conventions.md
|   |   |   |   |-- integrations.md
|   |   |   |   |-- stack.md
|   |   |   |   |-- structure.md
|   |   |   |   `-- testing.md
|   |   |   |-- research-project/
|   |   |   |   |-- ARCHITECTURE.md
|   |   |   |   |-- FEATURES.md
|   |   |   |   |-- PITFALLS.md
|   |   |   |   |-- STACK.md
|   |   |   |   `-- SUMMARY.md
|   |   |   |-- config.json
|   |   |   |-- context.md
|   |   |   |-- continue-here.md
|   |   |   |-- debug-subagent-prompt.md
|   |   |   |-- DEBUG.md
|   |   |   |-- discovery.md
|   |   |   |-- milestone-archive.md
|   |   |   |-- milestone.md
|   |   |   |-- phase-prompt.md
|   |   |   |-- planner-subagent-prompt.md
|   |   |   |-- project.md
|   |   |   |-- requirements.md
|   |   |   |-- research.md
|   |   |   |-- roadmap.md
|   |   |   |-- state.md
|   |   |   |-- summary-complex.md
|   |   |   |-- summary-minimal.md
|   |   |   |-- summary-standard.md
|   |   |   |-- summary.md
|   |   |   |-- UAT.md
|   |   |   |-- user-setup.md
|   |   |   `-- verification-report.md
|   |   |-- workflows/
|   |   |   |-- add-phase.md
|   |   |   |-- add-todo.md
|   |   |   |-- audit-milestone.md
|   |   |   |-- check-todos.md
|   |   |   |-- complete-milestone.md
|   |   |   |-- compound-execute.md
|   |   |   |-- diagnose-issues.md
|   |   |   |-- discovery-phase.md
|   |   |   |-- discuss-phase.md
|   |   |   |-- execute-phase.md
|   |   |   |-- execute-plan.md
|   |   |   |-- help.md
|   |   |   |-- insert-phase.md
|   |   |   |-- list-phase-assumptions.md
|   |   |   |-- map-codebase.md
|   |   |   |-- new-milestone.md
|   |   |   |-- new-project.md
|   |   |   |-- pause-work.md
|   |   |   |-- plan-milestone-gaps.md
|   |   |   |-- plan-phase.md
|   |   |   |-- progress.md
|   |   |   |-- quick.md
|   |   |   |-- remove-phase.md
|   |   |   |-- research-phase.md
|   |   |   |-- resume-project.md
|   |   |   |-- set-profile.md
|   |   |   |-- settings.md
|   |   |   |-- transition.md
|   |   |   |-- update.md
|   |   |   |-- verify-phase.md
|   |   |   `-- verify-work.md
|   |   `-- VERSION
|   |-- hooks/
|   |   |-- check-pending-improvements.py
|   |   |-- gsd-check-update.js
|   |   |-- gsd-statusline.js
|   |   `-- start-health-daemon.py
|   |-- metrics/
|   |   |-- 13.2/
|   |   |   `-- 13.2-01.json
|   |   `-- test/
|   |       |-- test-01.json
|   |       |-- test-02.json
|   |       |-- test-03.json
|   |       `-- test-04.json
|   |-- plugins/
|   |   `-- ralph-wiggum/
|   |       |-- .claude-plugin/
|   |       |   `-- plugin.json
|   |       |-- commands/
|   |       |   |-- cancel-ralph.md
|   |       |   |-- quality-loop.md
|   |       |   `-- ralph-loop.md
|   |       |-- hooks/
|   |       |   |-- hooks.json
|   |       |   `-- stop-hook.sh
|   |       |-- scripts/
|   |       |   `-- setup-ralph-loop.sh
|   |       `-- README.md
|   |-- skills/
|   |   |-- verify-phase/
|   |   |   |-- SKILL.md
|   |   |   `-- verify.sh
|   |   |-- quality-loop.yaml
|   |   `-- seo-update.yaml
|   |-- AUTOMATIC_VERIFICATION_ENABLED.md
|   |-- gsd-file-manifest.json
|   |-- HOOKS_GUIDE.md
|   |-- learnings.md
|   |-- MVP_IMPLEMENTATION_COMPLETE.md
|   |-- PROGRESSIVE_VERIFICATION_QUICKSTART.md
|   |-- SESSION_PRIMER_TEMPLATE.md
|   |-- settings.json
|   `-- settings.local.json
|-- .codex/
|   |-- hooks/
|   |   `-- start-health-daemon.py
|   |-- learnings.md
|   |-- preToolUseHook.sh
|   |-- SESSION_PRIMER_TEMPLATE.md
|   `-- settings.json
|-- .gemini/
|   |-- hooks/
|   |   `-- start-health-daemon.py
|   |-- learnings.md
|   |-- preToolUseHook.sh
|   |-- SESSION_PRIMER_TEMPLATE.md
|   `-- settings.json
|-- .github/
|   `-- workflows/
|       |-- auto-remediate.yml
|       |-- ci-backend.yml
|       |-- phase13-deploy-guard.yml
|       |-- resolve-bot-threads.yml
|       |-- review-agent-rerun.yml
|       `-- risk-policy-gate.yml
|-- .obsidian/
|   |-- app.json
|   |-- appearance.json
|   |-- core-plugins.json
|   |-- graph.json
|   `-- workspace.json
|-- .planning/
|   |-- archive/
|   |   `-- README.md
|   |-- debug/
|   |   |-- chat-unfilled-template-and-ingest-broken.md
|   |   |-- live-authenticated-playwright-pass.md
|   |   |-- url-frontdoor-restoration-vektal.md
|   |   `-- vektal-domain-cutover-not-reachable.md
|   |-- enhancements/
|   |   `-- GSD_PROGRESSIVE_VERIFICATION.md
|   |-- phases/
|   |   |-- 01-codebase-cleanup-analysis/
|   |   |   |-- 01-01-PLAN.md
|   |   |   |-- 01-01-SUMMARY.md
|   |   |   |-- 01-02-PLAN.md
|   |   |   |-- 01-02-SUMMARY.md
|   |   |   |-- 01-03-PLAN.md
|   |   |   |-- 01-03-SUMMARY.md
|   |   |   |-- 01-RESEARCH.md
|   |   |   `-- 01-VERIFICATION.md
|   |   |-- 01.1-root-documentation-organization/
|   |   |   |-- 01.1-01-PLAN.md
|   |   |   |-- 01.1-01-SUMMARY.md
|   |   |   |-- 01.1-02-PLAN.md
|   |   |   |-- 01.1-02-SUMMARY.md
|   |   |   |-- 01.1-03-PLAN.md
|   |   |   |-- 01.1-03-SUMMARY.md
|   |   |   |-- 01.1-VERIFICATION.md
|   |   |   `-- VERIFICATION_SUMMARY.txt
|   |   |-- 02-docker-infrastructure-foundation/
|   |   |   |-- 02-01-PLAN.md
|   |   |   |-- 02-01-SUMMARY.md
|   |   |   |-- 02-02-PLAN.md
|   |   |   |-- 02-02-SUMMARY.md
|   |   |   |-- 02-03-PLAN.md
|   |   |   |-- 02-03-SUMMARY.md
|   |   |   |-- 02-04-PLAN.md
|   |   |   |-- 02-04-SUMMARY.md
|   |   |   |-- 02-CONTEXT.md
|   |   |   |-- 02-RESEARCH.md
|   |   |   |-- 02-UAT.md
|   |   |   `-- 02-VERIFICATION.md
|   |   |-- 02.1-universal-vendor-scraping-engine/
|   |   |   |-- 02.1-01-PLAN.md
|   |   |   |-- 02.1-01-SUMMARY.md
|   |   |   |-- 02.1-02-PLAN.md
|   |   |   |-- 02.1-02-SUMMARY.md
|   |   |   |-- 02.1-03-PLAN.md
|   |   |   |-- 02.1-03-SUMMARY.md
|   |   |   |-- 02.1-04-PLAN.md
|   |   |   |-- 02.1-04-SUMMARY.md
|   |   |   |-- 02.1-05-PLAN.md
|   |   |   |-- 02.1-05-SUMMARY.md
|   |   |   |-- 02.1-06-PLAN.md
|   |   |   |-- 02.1-06-SUMMARY.md
|   |   |   |-- 02.1-07-PLAN.md
|   |   |   |-- 02.1-07-SUMMARY.md
|   |   |   |-- 02.1-08-PLAN.md
|   |   |   |-- 02.1-08-SUMMARY.md
|   |   |   |-- 02.1-09-PLAN.md
|   |   |   |-- 02.1-09-SUMMARY.md
|   |   |   |-- 02.1-10-PLAN.md
|   |   |   |-- 02.1-10-SUMMARY.md
|   |   |   |-- 02.1-11-PLAN.md
|   |   |   |-- 02.1-11-SUMMARY.md
|   |   |   |-- 02.1-CONTEXT.md
|   |   |   |-- 02.1-RESEARCH.md
|   |   |   |-- 02.1-VERIFICATION-backup.md
|   |   |   |-- 02.1-VERIFICATION-old.md
|   |   |   |-- 02.1-VERIFICATION.md
|   |   |   `-- README.md
|   |   |-- 02.2-product-enrichment-pipeline/
|   |   |   |-- 02.2-01-PLAN.md
|   |   |   |-- 02.2-01-SUMMARY.md
|   |   |   |-- 02.2-02-PLAN.md
|   |   |   |-- 02.2-02-SUMMARY.md
|   |   |   |-- 02.2-03-PLAN.md
|   |   |   |-- 02.2-03-SUMMARY.md
|   |   |   |-- 02.2-04-PLAN.md
|   |   |   |-- 02.2-04-SUMMARY.md
|   |   |   |-- 02.2-05-PLAN.md
|   |   |   |-- 02.2-05-SUMMARY.md
|   |   |   |-- 02.2-06-PLAN.md
|   |   |   |-- 02.2-06-SUMMARY.md
|   |   |   |-- 02.2-CONTEXT.md
|   |   |   |-- 02.2-RESEARCH.md
|   |   |   |-- 02.2-VERIFICATION.md
|   |   |   `-- ENHANCEMENTS.md
|   |   |-- 03-database-migration-sqlite-to-postgresql/
|   |   |   |-- 03-01-PLAN.md
|   |   |   |-- 03-01-SUMMARY.md
|   |   |   |-- 03-02-PLAN.md
|   |   |   |-- 03-02-SUMMARY.md
|   |   |   |-- 03-03-PLAN.md
|   |   |   |-- 03-03-SUMMARY.md
|   |   |   |-- 03-04-PLAN.md
|   |   |   |-- 03-04-SUMMARY.md
|   |   |   |-- 03-05-PLAN.md
|   |   |   |-- 03-05-SUMMARY.md
|   |   |   |-- 03-CONTEXT.md
|   |   |   |-- 03-RESEARCH.md
|   |   |   |-- 03-VERIFICATION.md
|   |   |   |-- PHASE3_VERIFICATION.md
|   |   |   |-- PHASE3_VERIFICATION_COMPLETE.md
|   |   |   `-- PHASE3_VERIFICATION_STATUS.md
|   |   |-- 04-authentication-user-management/
|   |   |   |-- 04-01-PLAN.md
|   |   |   |-- 04-01-SUMMARY.md
|   |   |   |-- 04-02-PLAN.md
|   |   |   |-- 04-02-SUMMARY.md
|   |   |   |-- 04-03-PLAN.md
|   |   |   |-- 04-03-SUMMARY.md
|   |   |   |-- 04-03-USER-SETUP.md
|   |   |   |-- 04-04-PLAN.md
|   |   |   |-- 04-04-SUMMARY.md
|   |   |   |-- 04-04-USER-SETUP.md
|   |   |   |-- 04-05-IMPLEMENTATION-NOTES.md
|   |   |   |-- 04-05-PLAN.md
|   |   |   |-- 04-05-SUMMARY.md
|   |   |   |-- 04-05-USER-SETUP.md
|   |   |   |-- 04-06-PLAN.md
|   |   |   |-- 04-06-SUMMARY.md
|   |   |   |-- 04-CONTEXT.md
|   |   |   |-- 04-PRICING-ANALYSIS.md
|   |   |   |-- 04-RESEARCH.md
|   |   |   |-- 04-UAT.md
|   |   |   `-- STRIPE_WEBHOOK_INTEGRATION_STATUS.md
|   |   |-- 05-backend-api-design/
|   |   |   |-- 05-01-PLAN-CODEX.md
|   |   |   |-- 05-01-PLAN.md
|   |   |   |-- 05-01-SUMMARY.md
|   |   |   |-- 05-02-PLAN-CODEX.md
|   |   |   |-- 05-02-PLAN.md
|   |   |   |-- 05-02-SUMMARY.md
|   |   |   |-- 05-03-PLAN.md
|   |   |   |-- 05-03-SUMMARY.md
|   |   |   |-- 05-04-01-PLAN.md
|   |   |   |-- 05-04-01-SUMMARY.md
|   |   |   |-- 05-04-PLAN.md
|   |   |   |-- 05-04-SUMMARY.md
|   |   |   |-- 05-05-PLAN.md
|   |   |   |-- 05-05-SUMMARY.md
|   |   |   |-- 05-CONTEXT.md
|   |   |   |-- 05-RESEARCH-CODEX.md
|   |   |   |-- 05-RESEARCH.md
|   |   |   `-- 05-SUMMARY.md
|   |   |-- 06-job-processing-infrastructure-celery/
|   |   |   |-- 06-01-PLAN.md
|   |   |   |-- 06-01-SUMMARY.md
|   |   |   |-- 06-02-PLAN.md
|   |   |   |-- 06-02-SUMMARY.md
|   |   |   |-- 06-03-PLAN.md
|   |   |   |-- 06-03-SUMMARY.md
|   |   |   |-- 06-04-PLAN.md
|   |   |   |-- 06-04-SUMMARY.md
|   |   |   |-- 06-05-PLAN.md
|   |   |   |-- 06-05-SUMMARY.md
|   |   |   |-- 06-06-PLAN.md
|   |   |   |-- 06-06-SUMMARY.md
|   |   |   |-- 06-CONTEXT.md
|   |   |   |-- 06-POST-UAT-WORKTREE-INVENTORY.md
|   |   |   |-- 06-RESEARCH.md
|   |   |   |-- 06-SUMMARY.md
|   |   |   |-- 06-UAT.md
|   |   |   `-- 06-VERIFICATION.md
|   |   |-- 07-frontend-framework-setup/
|   |   |   |-- 07.1-governance-baseline/
|   |   |   |   `-- PLAN.md
|   |   |   |-- 07.2-governance-operational-defaults/
|   |   |   |   `-- PLAN.md
|   |   |   |-- 07-01-currentstate.md
|   |   |   |-- 07-01-PLAN.md
|   |   |   |-- 07-01-SUMMARY.md
|   |   |   |-- 07-02-PLAN.md
|   |   |   |-- 07-02-SUMMARY.md
|   |   |   |-- 07-03-PLAN.md
|   |   |   |-- 07-03-SUMMARY.md
|   |   |   |-- 07-CONTEXT.md
|   |   |   |-- 07-DISCOVERY.md
|   |   |   |-- 07-MODULE-BOUNDARY-MAP.md
|   |   |   |-- 07-PLANNING-COVERAGE.md
|   |   |   |-- 07-RESEARCH.md
|   |   |   `-- 07-UAT.md
|   |   |-- 08-product-resolution-engine/
|   |   |   |-- 08-01-PLAN.md
|   |   |   |-- 08-01-SUMMARY.md
|   |   |   |-- 08-02-PLAN.md
|   |   |   |-- 08-02-SUMMARY.md
|   |   |   |-- 08-03-PLAN.md
|   |   |   |-- 08-03-SUMMARY.md
|   |   |   |-- 08-04-PLAN.md
|   |   |   |-- 08-04-SUMMARY.md
|   |   |   |-- 08-CONTEXT.md
|   |   |   |-- 08-PLANNING-COVERAGE.md
|   |   |   |-- 08-RESEARCH.md
|   |   |   |-- 08-UAT.md
|   |   |   `-- 08-VERIFICATION.md
|   |   |-- 09-real-time-progress-tracking/
|   |   |   |-- 09-01-PLAN.md
|   |   |   |-- 09-01-SUMMARY.md
|   |   |   |-- 09-02-PLAN.md
|   |   |   |-- 09-02-SUMMARY.md
|   |   |   |-- 09-CONTEXT.md
|   |   |   |-- 09-PLANNING-COVERAGE.md
|   |   |   |-- 09-RESEARCH.md
|   |   |   `-- 09-VERIFICATION.md
|   |   |-- 10-conversational-ai-interface/
|   |   |   |-- 10-01-PLAN.md
|   |   |   |-- 10-01-SUMMARY.md
|   |   |   |-- 10-02-PLAN.md
|   |   |   |-- 10-02-SUMMARY.md
|   |   |   |-- 10-03-PLAN.md
|   |   |   |-- 10-03-SUMMARY.md
|   |   |   |-- 10-04-PLAN.md
|   |   |   |-- 10-04-SUMMARY.md
|   |   |   |-- 10-CONTEXT.md
|   |   |   |-- 10-PLANNING-COVERAGE.md
|   |   |   |-- 10-RESEARCH.md
|   |   |   `-- 10-VERIFICATION.md
|   |   |-- 11-product-search-discovery/
|   |   |   |-- 11-01-PLAN.md
|   |   |   |-- 11-01-SUMMARY.md
|   |   |   |-- 11-02-PLAN.md
|   |   |   |-- 11-02-SUMMARY.md
|   |   |   |-- 11-03-PLAN.md
|   |   |   |-- 11-03-SUMMARY.md
|   |   |   |-- 11-CONTEXT.md
|   |   |   |-- 11-PLANNING-COVERAGE.md
|   |   |   |-- 11-RESEARCH.md
|   |   |   |-- 11-VERIFICATION.md
|   |   |   `-- GOV_REL_GLOSSARY.md
|   |   |-- 12-tier-system-architecture/
|   |   |   |-- 12-01-PLAN.md
|   |   |   |-- 12-01-SUMMARY.md
|   |   |   |-- 12-02-PLAN.md
|   |   |   |-- 12-02-SUMMARY.md
|   |   |   |-- 12-03-PLAN.md
|   |   |   |-- 12-03-SUMMARY.md
|   |   |   |-- 12-CONTEXT.md
|   |   |   |-- 12-PLANNING-COVERAGE.md
|   |   |   |-- 12-PRE-CONTEXT-SCOPE.md
|   |   |   |-- 12-RESEARCH.md
|   |   |   `-- 12-VERIFICATION.md
|   |   |-- 13-integration-hardening-deployment/
|   |   |   |-- 13-01-PLAN.md
|   |   |   |-- 13-01-SUMMARY.md
|   |   |   |-- 13-02-PLAN.md
|   |   |   |-- 13-02-SUMMARY.md
|   |   |   |-- 13-03-PLAN.md
|   |   |   |-- 13-03-SUMMARY.md
|   |   |   |-- 13-04-PLAN.md
|   |   |   |-- 13-04-SUMMARY.md
|   |   |   |-- 13-CONTEXT.md
|   |   |   |-- 13-PLANNING-COVERAGE.md
|   |   |   |-- 13-PRE-CONTEXT-SCOPE.md
|   |   |   |-- 13-RESEARCH-core.md
|   |   |   |-- 13-RESEARCH-deep.md
|   |   |   |-- 13-RESEARCH.md
|   |   |   `-- 13-VERIFICATION.md
|   |   |-- 13.1-product-data-enrichment-protocol-v2-integration/
|   |   |   |-- 13.1-01-PLAN.md
|   |   |   |-- 13.1-01-SUMMARY.md
|   |   |   |-- 13.1-02-PLAN.md
|   |   |   |-- 13.1-02-SUMMARY.md
|   |   |   |-- 13.1-03-PLAN.md
|   |   |   |-- 13.1-03-SUMMARY.md
|   |   |   |-- 13.1-04-PLAN.md
|   |   |   |-- 13.1-04-SUMMARY.md
|   |   |   |-- 13.1-CONTEXT.md
|   |   |   |-- 13.1-PLANNING-COVERAGE.md
|   |   |   |-- 13.1-PRE-CONTEXT-SCOPE.md
|   |   |   |-- 13.1-RESEARCH-core.md
|   |   |   |-- 13.1-RESEARCH-deep.md
|   |   |   |-- 13.1-RESEARCH.md
|   |   |   `-- 13.1-VERIFICATION.md
|   |   |-- 13.2-oracle-framework-reuse/
|   |   |   |-- 13.2-01-PLAN.md
|   |   |   |-- 13.2-01-SUMMARY.md
|   |   |   |-- 13.2-02-PLAN.md
|   |   |   |-- 13.2-02-SUMMARY.md
|   |   |   |-- 13.2-03-PLAN.md
|   |   |   |-- 13.2-03-SUMMARY.md
|   |   |   |-- 13.2-04-PLAN.md
|   |   |   |-- 13.2-04-SUMMARY.md
|   |   |   |-- 13.2-05-PLAN.md
|   |   |   |-- 13.2-05-SUMMARY.md
|   |   |   |-- 13.2-06-PLAN.md
|   |   |   |-- 13.2-06-SUMMARY.md
|   |   |   |-- 13.2-07-PLAN.md
|   |   |   |-- 13.2-07-SUMMARY.md
|   |   |   |-- 13.2-PLANNING-COVERAGE.md
|   |   |   |-- 13.2-PRE-CONTEXT-SCOPE.md
|   |   |   |-- 13.2-VERIFICATION.md
|   |   |   `-- 13.2-VERIFICATION.md.backup
|   |   |-- 14-continuous-optimization-learning/
|   |   |   |-- 14-01-PLAN.md
|   |   |   |-- 14-01-SUMMARY.md
|   |   |   |-- 14-02-PLAN.md
|   |   |   |-- 14-02-SUMMARY.md
|   |   |   |-- 14-03-PLAN.md
|   |   |   |-- 14-03-SUMMARY.md
|   |   |   |-- 14-04-PLAN.md
|   |   |   |-- 14-04-SUMMARY.md
|   |   |   |-- 14-05-PLAN.md
|   |   |   |-- 14-05-SUMMARY.md
|   |   |   |-- 14-06-PLAN.md
|   |   |   |-- 14-06-SUMMARY.md
|   |   |   |-- 14-07-PLAN.md
|   |   |   |-- 14-07-SUMMARY.md
|   |   |   |-- 14-08-PLAN.md
|   |   |   |-- 14-08-SUMMARY.md
|   |   |   |-- 14-CONTEXT.md
|   |   |   |-- 14-DISCUSSION-STATE.md
|   |   |   |-- 14-STATE-AFTER.md
|   |   |   `-- README.md
|   |   |-- 14.1-rag-enhancement/
|   |   |   |-- 14.1-01-PLAN.md
|   |   |   |-- 14.1-01-SUMMARY.md
|   |   |   |-- 14.1-02-PLAN.md
|   |   |   |-- 14.1-02-SUMMARY.md
|   |   |   |-- 14.1-03-PLAN.md
|   |   |   |-- 14.1-03-SUMMARY.md
|   |   |   |-- 14.1-04-PLAN.md
|   |   |   |-- 14.1-04-SUMMARY.md
|   |   |   |-- 14.1-05-PLAN.md
|   |   |   |-- 14.1-05-SUMMARY.md
|   |   |   |-- 14.1-06-PLAN.md
|   |   |   |-- 14.1-06-SUMMARY.md
|   |   |   |-- 14.1-CROSS-REFERENCE.md
|   |   |   |-- 14.1-EXECUTION-VALIDATION.md
|   |   |   |-- 14.1-PLAN-VALIDATION.md
|   |   |   |-- 14.1-PLAN.md
|   |   |   |-- 14.1-RESEARCH.md
|   |   |   `-- 14.1-SUMMARY.md
|   |   |-- 14.2-tool-calling-v2/
|   |   |   |-- 14.2-01-PLAN.md
|   |   |   |-- 14.2-01-SUMMARY.md
|   |   |   |-- 14.2-02-PLAN.md
|   |   |   |-- 14.2-02-SUMMARY.md
|   |   |   |-- 14.2-03-PLAN.md
|   |   |   |-- 14.2-03-SUMMARY.md
|   |   |   |-- 14.2-04-PLAN.md
|   |   |   |-- 14.2-04-SUMMARY.md
|   |   |   |-- 14.2-05-PLAN.md
|   |   |   |-- 14.2-05-SUMMARY.md
|   |   |   |-- 14.2-06-PLAN.md
|   |   |   |-- 14.2-06-SUMMARY.md
|   |   |   |-- 14.2-07-PLAN.md
|   |   |   |-- 14.2-07-SUMMARY.md
|   |   |   |-- 14.2-PLAN.md
|   |   |   |-- 14.2-RESEARCH.md
|   |   |   |-- PLANNING-SUMMARY.md
|   |   |   `-- README.md
|   |   |-- 14.3-graph-availability-sync/
|   |   |   |-- 14.3-01-PLAN.md
|   |   |   |-- 14.3-01-SUMMARY.md
|   |   |   |-- 14.3-02-PLAN.md
|   |   |   |-- 14.3-02-SUMMARY.md
|   |   |   |-- 14.3-03-PLAN.md
|   |   |   |-- 14.3-03-SUMMARY.md
|   |   |   |-- 14.3-04-PLAN.md
|   |   |   |-- 14.3-04-SUMMARY.md
|   |   |   |-- 14.3-05-PLAN.md
|   |   |   |-- 14.3-05-SUMMARY.md
|   |   |   |-- 14.3-06-PLAN.md
|   |   |   |-- 14.3-06-SUMMARY.md
|   |   |   |-- 14.3-07-PLAN.md
|   |   |   |-- 14.3-07-SUMMARY.md
|   |   |   |-- 14.3-CONTEXT.md
|   |   |   |-- 14.3-RESEARCH.md
|   |   |   |-- 14.3-VERIFICATION-GATE.md
|   |   |   `-- README.md
|   |   `-- 15-self-healing-dynamic-scripting/
|   |       |-- 15-01-03-VERIFICATION-GATE.md
|   |       |-- 15-01-PLAN.md
|   |       |-- 15-01-SUMMARY.md
|   |       |-- 15-02-PLAN.md
|   |       |-- 15-02-SUMMARY.md
|   |       |-- 15-03-PLAN.md
|   |       |-- 15-03-SUMMARY.md
|   |       |-- 15-04-08-VERIFICATION-GATE.md
|   |       |-- 15-04-PLAN.md
|   |       |-- 15-04-SUMMARY.md
|   |       |-- 15-05-PLAN.md
|   |       |-- 15-05-SUMMARY.md
|   |       |-- 15-06-PLAN.md
|   |       |-- 15-06-SUMMARY.md
|   |       |-- 15-07-PLAN.md
|   |       |-- 15-07-SUMMARY.md
|   |       |-- 15-08-PLAN.md
|   |       |-- 15-08-SUMMARY.md
|   |       |-- 15-09-PLAN.md
|   |       |-- 15-09-SUMMARY.md
|   |       |-- 15-10-PLAN.md
|   |       |-- 15-10-SUMMARY.md
|   |       |-- 15-11a-PLAN.md
|   |       |-- 15-11a-SUMMARY.md
|   |       |-- 15-11b-PLAN.md
|   |       |-- 15-11b-SUMMARY.md
|   |       |-- 15-ARCHITECTURE-LOCKED.md
|   |       |-- 15-CONTEXT.md
|   |       |-- 15-PLAN.md
|   |       |-- 15-PRE-CONTEXT-SCOPE.md
|   |       |-- 15-RESEARCH.md
|   |       |-- 15-UAT.md
|   |       |-- changes.md
|   |       |-- health-daemon-implementation-summary.md
|   |       |-- RESEARCH-COMPLETION.md
|   |       `-- research.md
|   |-- quick/
|   |   `-- 1-os-self-actualization/
|   |       |-- 1-PLAN.md
|   |       `-- 1-SUMMARY.md
|   |-- research/
|   |   |-- ARCHITECTURE.md
|   |   |-- FEATURES.md
|   |   |-- PITFALLS.md
|   |   |-- RUVECTOR-LEARNINGS.md
|   |   |-- STACK.md
|   |   `-- SUMMARY.md
|   |-- AGENTS.override.md
|   |-- config.json
|   |-- DIRTY_WORKTREE_REPORT.md
|   |-- INCIDENT_LOG.md
|   |-- KNOWLEDGE_GRAPH_ORACLE.md
|   |-- MILESTONES.md
|   |-- PROJECT.md
|   |-- REQUIREMENTS.md
|   |-- ROADMAP.md
|   |-- STATE.md
|   `-- TOOL_CALLING_2_INTEGRATION.md
|-- archive/
|   |-- 2026-directories/
|   |   |-- cli-old-argparse/
|   |   |   |-- bulk/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- push_images_only.py
|   |   |   |   `-- push_metadata_only.py
|   |   |   |-- pentart/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- pentart_manager.py
|   |   |   |-- products/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- check_product.py
|   |   |   |   |-- find_and_update_by_barcode.py
|   |   |   |   |-- find_and_update_sku.py
|   |   |   |   |-- quick_update_product.py
|   |   |   |   |-- update_barcode_product.py
|   |   |   |   |-- update_pentart_barcode.py
|   |   |   |   |-- update_pentart_product.py
|   |   |   |   |-- update_sku.py
|   |   |   |   |-- update_sku_rest.py
|   |   |   |   `-- update_via_rest.py
|   |   |   |-- search/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- get_barcode.py
|   |   |   |   |-- scrape_pentacolor_images.py
|   |   |   |   |-- scrape_pentart_sku.py
|   |   |   |   `-- search_barcode.py
|   |   |   |-- vision/
|   |   |   |   `-- generate_vision_alt_text.py
|   |   |   |-- __init__.py
|   |   |   |-- main.py
|   |   |   `-- temu_exporter.py
|   |   |-- orchestrator-quality-experiment/
|   |   |   |-- __init__.py
|   |   |   |-- product_quality_agent.py
|   |   |   |-- quality_loop_ralph.py
|   |   |   `-- trigger_quality_check.py
|   |   |-- scripts-utility-operations/
|   |   |   |-- add_metadata_columns.py
|   |   |   |-- amend_handles.py
|   |   |   |-- analyze_timing.py
|   |   |   |-- audit_v3.py
|   |   |   |-- auto_organize.py
|   |   |   |-- bulk_update_pentart_shopify.py
|   |   |   |-- clean_push_proof.py
|   |   |   |-- cleanup_shopify_tags.py
|   |   |   |-- cleanup_workspace.py
|   |   |   |-- debug_ddg.py
|   |   |   |-- debug_ean.py
|   |   |   |-- dedupe_not_found.py
|   |   |   |-- export_farbe_metafields.py
|   |   |   |-- export_paperdesigns.py
|   |   |   |-- export_shared_clusters.py
|   |   |   |-- extract_missing_proofs.py
|   |   |   |-- find_correct_eans.py
|   |   |   |-- find_dupes.py
|   |   |   |-- fix_itd_pricing.py
|   |   |   |-- import_pentart_catalog.py
|   |   |   |-- itd_debug.py
|   |   |   |-- list_collections.py
|   |   |   |-- list_vendors.py
|   |   |   |-- not_found_finder_v4_optimized.py
|   |   |   |-- prep_all_itd_prices.py
|   |   |   |-- prep_custom_scrape.py
|   |   |   |-- prep_data_for_push.py
|   |   |   |-- rebuild_push_proof.py
|   |   |   |-- remove_dupes_push_proof.py
|   |   |   |-- review_shared_alt.py
|   |   |   |-- seo_plan_v1.py
|   |   |   |-- sync_to_proof.py
|   |   |   |-- system_organizer.py
|   |   |   |-- test_app.py
|   |   |   |-- test_dynamic_scraper.py
|   |   |   |-- update_metadata.py
|   |   |   |-- variant_image_sync.py
|   |   |   |-- verify_push_proof_final.py
|   |   |   `-- verify_shopify_updates.py
|   |   |-- test_data-original/
|   |   |   |-- README.md
|   |   |   |-- sample_existing_products.csv
|   |   |   |-- sample_mixed_products.csv
|   |   |   `-- sample_new_products.csv
|   |   `-- vision_ai-old-structure/
|   |       |-- __init__.py
|   |       |-- cache.py
|   |       |-- client.py
|   |       |-- generator.py
|   |       |-- prompts.py
|   |       |-- stats.py
|   |       `-- test.py
|   |-- 2026-scripts/
|   |   |-- analysis/
|   |   |   |-- analyze_deleted_images.py
|   |   |   |-- analyze_reispapier_vendors.py
|   |   |   |-- find_missing_products.py
|   |   |   |-- find_products_by_sku.py
|   |   |   |-- find_remaining_products.py
|   |   |   |-- list_all_products.py
|   |   |   |-- search_broad.py
|   |   |   `-- search_by_title.py
|   |   |-- apply/
|   |   |   |-- apply_all_galaxy_flakes_sop.py
|   |   |   |-- apply_saturn_green.py
|   |   |   `-- apply_saturn_green_with_filename.py
|   |   |-- debug/
|   |   |   |-- debug_aistcraft.js
|   |   |   |-- debug_itd.js
|   |   |   |-- debug_pentart.js
|   |   |   `-- debug_single_vendor.js
|   |   |-- dry-run/
|   |   |   |-- dry_run_pluto_yellow.py
|   |   |   |-- dry_run_restore_all_images.py
|   |   |   |-- dry_run_restore_shared_images.py
|   |   |   `-- dry_run_saturn_green.py
|   |   |-- fix/
|   |   |   |-- auto_fix_images.py
|   |   |   |-- fix_and_add_images.py
|   |   |   |-- fix_pentart_products.py
|   |   |   `-- fix_pentart_rest.py
|   |   |-- misc/
|   |   |   |-- add_pentart_products.py
|   |   |   |-- catalog_paperdesigns.py
|   |   |   |-- complete_pentart_products.py
|   |   |   |-- download_galaxy_flakes_images.py
|   |   |   |-- generate_square_versions.py
|   |   |   |-- get_test_skus.py
|   |   |   |-- infer_paperdesigns_urls.py
|   |   |   |-- inspect_pentacolor.py
|   |   |   |-- preview_galaxy_flakes_updates.py
|   |   |   |-- process_products_by_id.py
|   |   |   |-- quick_image_test.py
|   |   |   |-- recreate_pentart_products.py
|   |   |   |-- replace_juno_rose_primary.py
|   |   |   |-- replace_primary_image_safe.py
|   |   |   |-- restore_shared_images_to_all_products.py
|   |   |   |-- scrape_missing_products.js
|   |   |   |-- set_inventory_final.py
|   |   |   |-- set_inventory_levels.py
|   |   |   |-- universal_vendor_scraper.js
|   |   |   |-- universal_vendor_scraper_v2.js
|   |   |   |-- update_saturn_green_final.py
|   |   |   |-- update_three_products.py
|   |   |   |-- upload_scraped_images.py
|   |   |   |-- verify_image_types_with_vision.py
|   |   |   `-- verify_uploaded_images.py
|   |   |-- scrape/
|   |   |   |-- scrape_and_upload_images.py
|   |   |   |-- scrape_missing.js
|   |   |   |-- scrape_paperdesigns_missing.py
|   |   |   |-- scrape_single_paperdesign.py
|   |   |   |-- scrape_three_images.py
|   |   |   `-- scrape_views_0009_direct.py
|   |   |-- test-scripts/
|   |   |   |-- test_pentart_scraper.py
|   |   |   |-- test_product_creation.py
|   |   |   `-- test_universal_scraper.js
|   |   |-- tool-output/
|   |   |   |-- deadcode_output.txt
|   |   |   |-- safety_audit.sql
|   |   |   `-- vulture_output.txt
|   |   |-- DEAD_CODE_REPORT.md
|   |   `-- MANIFEST.md
|   `-- v4_progress/
|       |-- test_results_v4_dryrun_progress_20260126_181321.csv
|       |-- test_results_v4_dryrun_progress_20260126_181400.csv
|       |-- test_results_v4_dryrun_progress_20260126_181438.csv
|       |-- test_results_v4_dryrun_progress_20260126_181532.csv
|       |-- test_results_v4_dryrun_progress_20260126_181617.csv
|       |-- test_results_v4_dryrun_progress_20260126_181703.csv
|       |-- test_results_v4_dryrun_progress_20260126_181742.csv
|       |-- test_results_v4_dryrun_progress_20260126_181814.csv
|       |-- test_results_v4_dryrun_progress_20260126_181847.csv
|       `-- test_results_v4_dryrun_progress_20260126_181923.csv
|-- config/
|   |-- vendors/
|   |   `-- _template.yaml
|   |-- image_processing_rules.yaml
|   |-- product_quality_rules.yaml
|   `-- vendor_configs.yaml
|-- docs/
|   |-- guides/
|   |   |-- CRITICAL_SAFEGUARDS.md
|   |   |-- DOCKER_QUICKSTART.md
|   |   |-- DOCKER_SECRETS.md
|   |   |-- ORCHESTRATOR_INTEGRATION_EXAMPLE.md
|   |   |-- ORCHESTRATOR_QUICK_START.md
|   |   |-- PRODUCT_CREATION_GUIDE.md
|   |   |-- QUICK_START.md
|   |   |-- SEO_QUICK_START.md
|   |   `-- SEO_SKILL_GUIDE.md
|   |-- implementation/
|   |   |-- IMPLEMENTATION_SUMMARY.md
|   |   |-- PENTART_IMPLEMENTATION.md
|   |   `-- PRODUCT_QUALITY_ORCHESTRATOR.md
|   |-- legacy/
|   |   |-- IMPLEMENTATION_SUMMARY.md
|   |   |-- PENTART_PRODUCTS_SUMMARY.md
|   |   |-- phase1-CONTEXT.md
|   |   |-- phase1-PLAN.md
|   |   `-- SolutionContextProfile.md
|   |-- ops/
|   |   `-- graph-availability-runbook.md
|   |-- phase-reports/
|   |   |-- FINAL_SUMMARY_PHASE_2.md
|   |   |-- PHASE_2_COMPLETE.md
|   |   `-- TASK_1_VENDOR_CONFIG_SUMMARY.md
|   |-- reference/
|   |   |-- FRAMEWORK_QUICK_REFERENCE.md
|   |   |-- hybrid_naming_example.md
|   |   |-- README_VISION_AI.md
|   |   `-- VERIFICATION_CHECKLIST.md
|   |-- requirements/
|   |   `-- PRODUCT_REQUIREMENTS_DOCUMENT.md
|   |-- setup/
|   |   |-- README_APP.md
|   |   `-- SETUP.md
|   |-- tasks/
|   |   |-- orchestrator_setup_tasks.md
|   |   |-- SVSE_SESSION_SUMMARY.md
|   |   `-- tag_cleanup_context.md
|   |-- CRITICAL_BUG_FIX.md
|   |-- DIRECTORY_STRUCTURE.md
|   |-- galaxy_flakes_image_plan_summary.md
|   |-- health-daemon-system.md
|   |-- IMAGE_FINDING_SYSTEM.md
|   |-- IMAGE_PROCESSING_FRAMEWORK.md
|   |-- IMAGE_VERIFICATION_SYSTEM.md
|   |-- INDEX.md
|   |-- investigation-notes.md
|   |-- MASTER_MAP.md
|   |-- NEXT_PHASE_PLAN.md
|   |-- PAYLOAD_SCHEMA.md
|   |-- pretooluse-hook-system.md
|   |-- PROJECT_SUMMARY.md
|   |-- QA_CHECKLIST.md
|   |-- RALPH_WIGGUM_INTEGRATION.md
|   |-- README.md
|   `-- SCRAPER_STRATEGY.md
|-- frontend/
|   |-- .design/
|   |   `-- design-context.md
|   |-- src/
|   |   |-- app/
|   |   |   |-- (app)/
|   |   |   |   |-- chat/
|   |   |   |   |   |-- page.test.tsx
|   |   |   |   |   `-- page.tsx
|   |   |   |   |-- dashboard/
|   |   |   |   |   `-- page.tsx
|   |   |   |   |-- enrichment/
|   |   |   |   |   `-- page.tsx
|   |   |   |   |-- jobs/
|   |   |   |   |   |-- [id]/
|   |   |   |   |   |   |-- page.test.tsx
|   |   |   |   |   |   `-- page.tsx
|   |   |   |   |   `-- page.tsx
|   |   |   |   |-- onboarding/
|   |   |   |   |   `-- page.tsx
|   |   |   |   |-- search/
|   |   |   |   |   |-- page.test.tsx
|   |   |   |   |   `-- page.tsx
|   |   |   |   |-- settings/
|   |   |   |   |   `-- page.tsx
|   |   |   |   `-- layout.tsx
|   |   |   |-- (auth)/
|   |   |   |   `-- auth/
|   |   |   |       |-- login/
|   |   |   |       |   `-- page.tsx
|   |   |   |       `-- verify/
|   |   |   |           `-- page.tsx
|   |   |   |-- approvals/
|   |   |   |   `-- page.tsx
|   |   |   |-- dashboard.contract.test.ts
|   |   |   |-- globals.css
|   |   |   |-- layout.tsx
|   |   |   |-- page.tsx
|   |   |   |-- routing.contract.test.ts
|   |   |   `-- routing.guard.integration.test.ts
|   |   |-- features/
|   |   |   |-- approvals/
|   |   |   |   |-- components/
|   |   |   |   |   |-- ApprovalQueue.css
|   |   |   |   |   |-- ApprovalQueue.test.tsx
|   |   |   |   |   `-- ApprovalQueue.tsx
|   |   |   |   `-- pages/
|   |   |   |       `-- ApprovalsPage.tsx
|   |   |   |-- chat/
|   |   |   |   |-- api/
|   |   |   |   |   `-- chat-api.ts
|   |   |   |   |-- components/
|   |   |   |   |   |-- ActionCard.test.tsx
|   |   |   |   |   |-- ActionCard.tsx
|   |   |   |   |   |-- BulkRunPanel.tsx
|   |   |   |   |   |-- ChatWorkspace.test.tsx
|   |   |   |   |   |-- ChatWorkspace.tsx
|   |   |   |   |   |-- DelegationTracePanel.tsx
|   |   |   |   |   `-- MessageBlockRenderer.tsx
|   |   |   |   `-- hooks/
|   |   |   |       |-- useChatSession.ts
|   |   |   |       |-- useChatStream.test.ts
|   |   |   |       `-- useChatStream.ts
|   |   |   |-- enrichment/
|   |   |   |   |-- api/
|   |   |   |   |   `-- enrichment-api.ts
|   |   |   |   `-- components/
|   |   |   |       |-- EnrichmentConflictPanel.tsx
|   |   |   |       |-- EnrichmentReviewTable.test.tsx
|   |   |   |       |-- EnrichmentReviewTable.tsx
|   |   |   |       |-- EnrichmentRunConfigurator.tsx
|   |   |   |       |-- EnrichmentWorkspace.test.tsx
|   |   |   |       `-- EnrichmentWorkspace.tsx
|   |   |   |-- jobs/
|   |   |   |   |-- components/
|   |   |   |   |   |-- GlobalJobTracker.tsx
|   |   |   |   |   |-- JobsWorkspace.tsx
|   |   |   |   |   |-- JobTerminalNotifications.test.ts
|   |   |   |   |   `-- JobTerminalNotifications.tsx
|   |   |   |   |-- hooks/
|   |   |   |   |   |-- useJobDetailObserver.test.ts
|   |   |   |   |   |-- useJobDetailObserver.ts
|   |   |   |   |   |-- useJobListStateFromUrl.test.ts
|   |   |   |   |   |-- useJobListStateFromUrl.ts
|   |   |   |   |   |-- useJobRehydrate.test.ts
|   |   |   |   |   `-- useJobRehydrate.ts
|   |   |   |   `-- observer/
|   |   |   |       |-- job-observer.ts
|   |   |   |       |-- transport-ladder.test.ts
|   |   |   |       `-- transport-ladder.ts
|   |   |   |-- onboarding/
|   |   |   |   |-- api/
|   |   |   |   |   |-- onboarding-mutations.test.ts
|   |   |   |   |   `-- onboarding-mutations.ts
|   |   |   |   |-- components/
|   |   |   |   |   |-- OnboardingWizard.test.tsx
|   |   |   |   |   `-- OnboardingWizard.tsx
|   |   |   |   `-- state/
|   |   |   |       |-- onboarding-machine.test.ts
|   |   |   |       `-- onboarding-machine.ts
|   |   |   |-- resolution/
|   |   |   |   |-- api/
|   |   |   |   |   `-- resolution-api.ts
|   |   |   |   |-- components/
|   |   |   |   |   |-- ActivityPanels.tsx
|   |   |   |   |   |-- CollaborationBadge.tsx
|   |   |   |   |   |-- DryRunReview.tsx
|   |   |   |   |   |-- FieldChangeRow.tsx
|   |   |   |   |   |-- ProductChangeCard.tsx
|   |   |   |   |   `-- TechnicalDetailsToggle.tsx
|   |   |   |   `-- state/
|   |   |   |       `-- review-store.ts
|   |   |   |-- search/
|   |   |   |   |-- api/
|   |   |   |   |   `-- search-api.ts
|   |   |   |   |-- components/
|   |   |   |   |   |-- ApprovalBlockCard.tsx
|   |   |   |   |   |-- BulkActionBuilder.test.tsx
|   |   |   |   |   |-- BulkActionBuilder.tsx
|   |   |   |   |   |-- ProductDetailPanel.tsx
|   |   |   |   |   |-- ProductDiffPanel.tsx
|   |   |   |   |   |-- SearchResultGrid.tsx
|   |   |   |   |   `-- SearchWorkspace.tsx
|   |   |   |   `-- hooks/
|   |   |   |       |-- useBulkStaging.ts
|   |   |   |       `-- useSearchWorkspace.ts
|   |   |   |-- settings/
|   |   |   |   `-- components/
|   |   |   |       |-- RuleSuggestionsInbox.tsx
|   |   |   |       `-- StrategyQuiz.tsx
|   |   |   |-- index.ts
|   |   |   |-- manifest.contract.test.ts
|   |   |   `-- manifest.ts
|   |   |-- lib/
|   |   |   |-- api/
|   |   |   |   |-- client.ts
|   |   |   |   |-- problem-details.test.ts
|   |   |   |   `-- problem-details.ts
|   |   |   |-- auth/
|   |   |   |   |-- guards.test.ts
|   |   |   |   |-- guards.ts
|   |   |   |   `-- session-flags.ts
|   |   |   `-- query/
|   |   |       |-- keys.test.ts
|   |   |       `-- keys.ts
|   |   |-- shared/
|   |   |   |-- contracts/
|   |   |   |   |-- chat.ts
|   |   |   |   |-- index.ts
|   |   |   |   `-- resolution.ts
|   |   |   `-- errors/
|   |   |       `-- error-presenter.ts
|   |   |-- shell/
|   |   |   |-- components/
|   |   |   |   |-- AppShell.tsx
|   |   |   |   |-- ChatSurface.tsx
|   |   |   |   |-- GlobalPendingIndicator.tsx
|   |   |   |   |-- NotificationStack.tsx
|   |   |   |   `-- Sidebar.tsx
|   |   |   |-- state/
|   |   |   |   `-- pending-store.ts
|   |   |   |-- providers.tsx
|   |   |   `-- responsive-layout.test.ts
|   |   `-- state/
|   |       |-- drafts-store.test.ts
|   |       |-- drafts-store.ts
|   |       |-- ui-prefs-store.test.ts
|   |       `-- ui-prefs-store.ts
|   |-- tests/
|   |   `-- frontend/
|   |       |-- resolution/
|   |       |   `-- review.contract.test.tsx
|   |       `-- settings/
|   |           `-- strategy-quiz.contract.test.tsx
|   |-- .codex_tmp.chat-diag.spec.ts
|   |-- .codex_tmp.enrichment-diag.spec.ts
|   |-- .codex_tmp.enrichment-submit-trace.spec.ts
|   |-- .codex_tmp.live-debug.spec.ts
|   |-- .codex_tmp.oauth-status.spec.ts
|   |-- .codex_tmp.playwright.chat.config.ts
|   |-- .codex_tmp.playwright.enrichment.config.ts
|   |-- .codex_tmp.playwright.live.config.ts
|   |-- .codex_tmp.playwright.oauth.config.ts
|   |-- eslint.config.mjs
|   |-- next-env.d.ts
|   |-- next.config.ts
|   |-- package-lock.json
|   |-- package.json
|   |-- README.md
|   |-- tsconfig.json
|   |-- vitest.config.ts
|   `-- vitest.setup.ts
|-- migrations/
|   |-- versions/
|   |   |-- 3c9b2f7d5a1e_add_auth_fields_and_oauth_attempts.py
|   |   |-- 4d8f6b9c2e1a_add_user_api_version_fields.py
|   |   |-- a7b8c9d0e1f2_phase11_product_history_and_staging.py
|   |   |-- a9f3c7d5e1b2_phase13_runtime_policy_and_idempotency.py
|   |   |-- b2f4c6d8e0a1_phase13_governance_recovery.py
|   |   |-- b7d5c4a9e8f1_phase6_ingest_chunks_audit_checkpoints.py
|   |   |-- c1d9e8f7a6b5_phase8_resolution_foundation.py
|   |   |-- c4d5e6f7a8b9_phase13_deploy_observability.py
|   |   |-- d4e5f6a7b8c9_phase12_tier_routing_and_profiles.py
|   |   |-- e5f6a7b8c9d0_phase13_instrumentation_foundation.py
|   |   |-- e6eec7532bd6_initial_schema_users_stores_vendors_.py
|   |   |-- f0a1b2c3d4e5_phase10_chat_foundation.py
|   |   |-- f1a2b3c4d5e6_phase11_snapshot_lifecycle.py
|   |   |-- f2b3c4d5e6f7_phase13_1_enrichment_capability_policy.py
|   |   |-- g14_2_01_tool_input_examples.py
|   |   |-- g14_2_03_schema_json.py
|   |   |-- p15_01_sandbox_runs.py
|   |   `-- p15_02_remedy_template_cache.py
|   |-- alembic.ini
|   |-- env.py
|   |-- README
|   `-- script.py.mako
|-- nginx/
|   `-- nginx.conf
|-- ops/
|   |-- governance/
|   |   `-- roles/
|   |       |-- builder.md
|   |       |-- context-curator.md
|   |       |-- integrity-warden.md
|   |       |-- phase-manager.md
|   |       |-- README.md
|   |       |-- reviewer.md
|   |       `-- structure-guardian.md
|   `-- STRUCTURE_SPEC.md
|-- reports/
|   |-- 07/
|   |   |-- 07.1-governance-baseline-dry-run/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 07.2-governance-operational-defaults/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 11/
|   |   |-- 11-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 11-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 11-03/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 12/
|   |   |-- 12-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 12-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 12-03/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 13/
|   |   |-- 13-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 13-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 13-03/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 13-04/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 13.1/
|   |   |-- 13.1-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 13.1-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 13.1-03/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 13.1-04/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 13.2/
|   |   |-- 13.2-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 13.2-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 13.2-03/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 13.2-04/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 13.2-05/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 14.2/
|   |   |-- 14.2-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.2-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.2-03/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.2-04/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.2-05/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.2-06/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 14.2-07/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 14.3/
|   |   |-- 14.3-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.3-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.3-03/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.3-04/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.3-05/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 14.3-06/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 14.3-07/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- 15/
|   |   |-- 15-01/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-02/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-03/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-04/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-05/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-06/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-07/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-08/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-09/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-10/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   |-- 15-11a/
|   |   |   |-- integrity-audit.md
|   |   |   |-- review.md
|   |   |   |-- self-check.md
|   |   |   `-- structure-audit.md
|   |   `-- 15-11b/
|   |       |-- integrity-audit.md
|   |       |-- review.md
|   |       |-- self-check.md
|   |       `-- structure-audit.md
|   |-- meta/
|   |   |-- governance-baseline-implementation-report-2026-02-12.md
|   |   |-- governance-validation-runbook-2026-02-12.md
|   |   |-- journey-synthesis-13-15.md
|   |   `-- journey-synthesis-template.md
|   |-- templates/
|   |   |-- integrity-audit.template.md
|   |   |-- review.template.md
|   |   |-- self-check.template.md
|   |   `-- structure-audit.template.md
|   `-- AGENTS.override.md
|-- scripts/
|   |-- checkpoints/
|   |   `-- log_approval.py
|   |-- daemons/
|   |   |-- health_monitor.py
|   |   |-- README.md
|   |   |-- start_health_monitor.sh
|   |   |-- status_health_monitor.sh
|   |   `-- stop_health_monitor.sh
|   |-- governance/
|   |   |-- check_harness_slas.py
|   |   |-- ensure_neo4j_runtime.py
|   |   |-- graph_availability_gate.py
|   |   |-- graph_gate.py
|   |   |-- health_gate.py
|   |   |-- phase13_1_enrichment_gate.py
|   |   |-- phase13_canary_gate.py
|   |   |-- README.md
|   |   |-- risk_tier_gate.py
|   |   |-- risk_tier_gate_enforce.py
|   |   |-- sandbox_seccomp.json
|   |   |-- sha_gate.py
|   |   `-- validate_governance.py
|   |-- graph/
|   |   |-- analyze_performance.py
|   |   |-- apply_optimizations.py
|   |   |-- auto_apply_infrastructure.py
|   |   |-- bootstrap_graph_backend.py
|   |   |-- graph_status.py
|   |   |-- init_codebase_schema.py
|   |   |-- init_tool_search_index.py
|   |   |-- load_session_context.py
|   |   |-- orchestrate_healers.py
|   |   |-- pretool_gate.py
|   |   |-- promote_to_template.py
|   |   |-- run_consistency_check.py
|   |   |-- seed_memory_nodes.py
|   |   |-- sentry_auto_heal.py
|   |   |-- start_mcp_server.sh
|   |   |-- sync_codebase.py
|   |   |-- sync_to_neo4j.py
|   |   `-- validate_remedy_efficacy.py
|   |-- harness/
|   |   `-- ui/
|   |       |-- evidence_index.py
|   |       `-- run_e2e.sh
|   |-- hooks/
|   |   |-- antigravity_notify.py
|   |   |-- antigravity_watchdog.py
|   |   `-- pre-commit-graph-sync.py
|   |-- infra/
|   |   `-- redis_health_fixer.py
|   |-- observability/
|   |   |-- ensure_sentry_worker.py
|   |   |-- sentry_issue_puller.py
|   |   `-- test_sentry_flow.py
|   |-- backup_db.sh
|   |-- debug_driver_params.py
|   |-- debug_neo4j_drivers.py
|   |-- import_pentart.py
|   |-- migrate_metrics_to_graph.py
|   |-- restore_db.sh
|   |-- test_sandbox.py
|   `-- verify_phase_14_2_comprehensive.py
|-- secrets/
|   `-- .gitkeep
|-- seo/
|   |-- __init__.py
|   |-- CHANGELOG.md
|   |-- generate_seo_quick.py
|   |-- IMPLEMENTATION.md
|   |-- QUICKSTART.md
|   |-- README.md
|   |-- run_seo_generator.bat
|   |-- run_seo_generator.sh
|   |-- seo_generator.py
|   |-- seo_prompts.py
|   `-- seo_validator.py
|-- solutionsos/
|   |-- compound-engineering-os-policy.md
|   |-- gsd-plan-execution.md
|   `-- os-self-actualization.md
|-- src/
|   |-- api/
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- errors.py
|   |   |   |-- pagination.py
|   |   |   |-- rate_limit.py
|   |   |   |-- sse.py
|   |   |   `-- versioning.py
|   |   |-- jobs/
|   |   |   |-- __init__.py
|   |   |   |-- events.py
|   |   |   `-- schemas.py
|   |   |-- v1/
|   |   |   |-- chat/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- approvals.py
|   |   |   |   |-- bulk.py
|   |   |   |   |-- orchestrator.py
|   |   |   |   |-- routes.py
|   |   |   |   `-- schemas.py
|   |   |   |-- jobs/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- routes.py
|   |   |   |   `-- schemas.py
|   |   |   |-- ops/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- routes.py
|   |   |   |-- products/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- routes.py
|   |   |   |   |-- schemas.py
|   |   |   |   |-- search_query.py
|   |   |   |   `-- staging.py
|   |   |   |-- resolution/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- routes.py
|   |   |   |   `-- schemas.py
|   |   |   |-- vendors/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- routes.py
|   |   |   |   `-- schemas.py
|   |   |   |-- versioning/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- routes.py
|   |   |   |   `-- schemas.py
|   |   |   |-- __init__.py
|   |   |   `-- approvals.py
|   |   |-- __init__.py
|   |   `-- app.py
|   |-- assistant/
|   |   |-- deployment/
|   |   |   |-- __init__.py
|   |   |   |-- canary_guard.py
|   |   |   |-- observability.py
|   |   |   |-- provider_router.py
|   |   |   `-- redaction.py
|   |   |-- governance/
|   |   |   |-- __init__.py
|   |   |   |-- field_policy.py
|   |   |   |-- graph_oracle_adapter.py
|   |   |   |-- kill_switch.py
|   |   |   |-- mutation_guard.py
|   |   |   `-- verification_oracle.py
|   |   |-- instrumentation/
|   |   |   |-- __init__.py
|   |   |   |-- export.py
|   |   |   `-- signals.py
|   |   |-- reliability/
|   |   |   |-- __init__.py
|   |   |   |-- breakers.py
|   |   |   |-- idempotency.py
|   |   |   |-- policy_store.py
|   |   |   `-- retry_matrix.py
|   |   |-- __init__.py
|   |   |-- delegation.py
|   |   |-- memory_retrieval.py
|   |   |-- policy_resolver.py
|   |   |-- runtime_tier1.py
|   |   |-- runtime_tier2.py
|   |   |-- runtime_tier3.py
|   |   |-- session_primer.py
|   |   `-- tool_projection.py
|   |-- auth/
|   |   |-- __init__.py
|   |   |-- decorators.py
|   |   |-- email_sender.py
|   |   |-- email_verification.py
|   |   |-- login.py
|   |   `-- oauth.py
|   |-- billing/
|   |   |-- __init__.py
|   |   |-- checkout.py
|   |   |-- routes.py
|   |   |-- stripe_client.py
|   |   |-- subscription.py
|   |   `-- webhooks.py
|   |-- cli/
|   |   |-- commands/
|   |   |   |-- __init__.py
|   |   |   |-- products.py
|   |   |   `-- search.py
|   |   |-- __init__.py
|   |   |-- approvals.py
|   |   `-- main.py
|   |-- config/
|   |   |-- __init__.py
|   |   |-- email_config.py
|   |   |-- logging_config.py
|   |   |-- sentry_config.py
|   |   `-- session_config.py
|   |-- core/
|   |   |-- chat/
|   |   |   |-- handlers/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- generic.py
|   |   |   |   |-- product.py
|   |   |   |   `-- vendor.py
|   |   |   |-- __init__.py
|   |   |   `-- router.py
|   |   |-- config/
|   |   |   |-- __init__.py
|   |   |   |-- generator.py
|   |   |   |-- loader.py
|   |   |   |-- store_profile_schema.py
|   |   |   |-- vendor_schema.py
|   |   |   `-- verifier.py
|   |   |-- discovery/
|   |   |   |-- __init__.py
|   |   |   |-- ai_inference.py
|   |   |   |-- catalog_extractor.py
|   |   |   |-- firecrawl_client.py
|   |   |   |-- gsd_populator.py
|   |   |   |-- local_classifier.py
|   |   |   |-- local_patterns.py
|   |   |   |-- niche_validator.py
|   |   |   |-- pipeline.py
|   |   |   |-- site_recon.py
|   |   |   |-- sku_validator.py
|   |   |   |-- store_analyzer.py
|   |   |   `-- web_search.py
|   |   |-- enrichment/
|   |   |   |-- embeddings/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- generator.py
|   |   |   |-- extractors/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- attributes.py
|   |   |   |-- families/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- grouper.py
|   |   |   |-- generators/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- descriptions.py
|   |   |   |   `-- seo.py
|   |   |   |-- oracles/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- content_oracle.py
|   |   |   |   |-- policy_oracle.py
|   |   |   |   `-- visual_oracle.py
|   |   |   |-- quality/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- scorer.py
|   |   |   |-- templating/
|   |   |   |   |-- __init__.py
|   |   |   |   `-- engine.py
|   |   |   |-- __init__.py
|   |   |   |-- benchmarks.py
|   |   |   |-- capability_audit.py
|   |   |   |-- color_learning.py
|   |   |   |-- config.py
|   |   |   |-- contracts.py
|   |   |   |-- eligibility.py
|   |   |   |-- evaluation.py
|   |   |   |-- idempotency.py
|   |   |   |-- INTEGRATION.md
|   |   |   |-- oracle_contract.py
|   |   |   |-- pipeline.py
|   |   |   |-- profiles.py
|   |   |   |-- provenance.py
|   |   |   |-- README.md
|   |   |   |-- retries.py
|   |   |   |-- retrieval_payload.py
|   |   |   |-- vendor_integration.py
|   |   |   `-- write_plan.py
|   |   |-- scraping/
|   |   |   |-- strategies/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- base.py
|   |   |   |   |-- playwright_strategy.py
|   |   |   |   `-- requests_strategy.py
|   |   |   |-- __init__.py
|   |   |   |-- adaptive.py
|   |   |   |-- engine.py
|   |   |   `-- metrics.py
|   |   |-- __init__.py
|   |   |-- codebase_entities.py
|   |   |-- codebase_schema.py
|   |   |-- diff_engine.py
|   |   |-- embeddings.py
|   |   |-- encryption.py
|   |   |-- graphiti_client.py
|   |   |-- hs_code_resolver.py
|   |   |-- hybrid_image_naming.py
|   |   |-- image_framework.py
|   |   |-- image_scraper.py
|   |   |-- image_verifier.py
|   |   |-- llm_client.py
|   |   |-- memory_loader.py
|   |   |-- paths.py
|   |   |-- pipeline.py
|   |   |-- product_analyzer.py
|   |   |-- quality_assessor.py
|   |   |-- scrape_engine.py
|   |   |-- secrets.py
|   |   |-- sentry_client.py
|   |   |-- seo_engine.py
|   |   |-- shopify_apply.py
|   |   |-- shopify_resolver.py
|   |   |-- summary_generator.py
|   |   |-- synthex_entities.py
|   |   |-- vendor_config.py
|   |   |-- vision_cache.py
|   |   |-- vision_client.py
|   |   |-- vision_engine.py
|   |   `-- vision_prompts.py
|   |-- graph/
|   |   |-- remediators/
|   |   |   |-- aura_remediator.py
|   |   |   |-- bash_agent.py
|   |   |   |-- code_remediator.py
|   |   |   |-- docker_remediator.py
|   |   |   |-- git_staleness_guard.py
|   |   |   |-- llm_remediator.py
|   |   |   |-- optimizer_remediator.py
|   |   |   |-- redis_remediator.py
|   |   |   |-- snapshot_remediator.py
|   |   |   `-- sync_remediator.py
|   |   |-- ab_test_validator.py
|   |   |-- backend_resolver.py
|   |   |-- batch_handlers.py
|   |   |-- bottleneck_detector.py
|   |   |-- codebase_scanner.py
|   |   |-- commit_parser.py
|   |   |-- consistency_daemon.py
|   |   |-- convention_checker.py
|   |   |-- file_parser.py
|   |   |-- fix_generator.py
|   |   |-- incremental_sync.py
|   |   |-- infra_probe.py
|   |   |-- intent_capture.py
|   |   |-- local_graph_store.py
|   |   |-- mcp_response_metadata.py
|   |   |-- mcp_server.py
|   |   |-- orchestrate_healers.py
|   |   |-- performance_profiler.py
|   |   |-- planning_linker.py
|   |   |-- query_interface.py
|   |   |-- query_templates.py
|   |   |-- refactor_guard.py
|   |   |-- remediation_registry.py
|   |   |-- research_tools.py
|   |   |-- root_cause_classifier.py
|   |   |-- runtime_optimizer.py
|   |   |-- sandbox_docker.py
|   |   |-- sandbox_gates.py
|   |   |-- sandbox_persistence.py
|   |   |-- sandbox_types.py
|   |   |-- sandbox_verifier.py
|   |   |-- sandbox_workspace.py
|   |   |-- search_expand_bridge.py
|   |   |-- semantic_cache.py
|   |   |-- sentry_feedback_loop.py
|   |   |-- sentry_ingestor.py
|   |   |-- similarity_detector.py
|   |   |-- sync_status.py
|   |   |-- telemetry_dashboard.py
|   |   |-- template_extractor.py
|   |   `-- universal_fixer.py
|   |-- integrations/
|   |   `-- perplexity_client.py
|   |-- jobs/
|   |   |-- __init__.py
|   |   |-- cancellation.py
|   |   |-- checkpoints.py
|   |   |-- dispatcher.py
|   |   |-- finalizer.py
|   |   |-- graphiti_ingestor.py
|   |   |-- metrics.py
|   |   |-- orchestrator.py
|   |   |-- progress.py
|   |   `-- queueing.py
|   |-- models/
|   |   |-- __init__.py
|   |   |-- assistant_delegation_event.py
|   |   |-- assistant_deployment_policy.py
|   |   |-- assistant_execution_ledger.py
|   |   |-- assistant_field_policy.py
|   |   |-- assistant_kill_switch.py
|   |   |-- assistant_memory_embedding.py
|   |   |-- assistant_memory_fact.py
|   |   |-- assistant_preference_signal.py
|   |   |-- assistant_profile.py
|   |   |-- assistant_provider_route_event.py
|   |   |-- assistant_route_event.py
|   |   |-- assistant_runtime_policy.py
|   |   |-- assistant_tenant_tool_policy.py
|   |   |-- assistant_tool_registry.py
|   |   |-- assistant_verification_event.py
|   |   |-- assistant_verification_signal.py
|   |   |-- audit_checkpoint.py
|   |   |-- chat_action.py
|   |   |-- chat_message.py
|   |   |-- chat_session.py
|   |   |-- ingest_chunk.py
|   |   |-- job.py
|   |   |-- oauth_attempt.py
|   |   |-- pending_approvals.py
|   |   |-- product.py
|   |   |-- product_change_event.py
|   |   |-- product_enrichment_item.py
|   |   |-- product_enrichment_run.py
|   |   |-- recovery_log.py
|   |   |-- remedy_templates.py
|   |   |-- resolution_batch.py
|   |   |-- resolution_rule.py
|   |   |-- resolution_snapshot.py
|   |   |-- sandbox_runs.py
|   |   |-- shopify.py
|   |   |-- user.py
|   |   |-- vendor.py
|   |   `-- vendor_field_mapping.py
|   |-- resolution/
|   |   |-- adapters/
|   |   |   |-- __init__.py
|   |   |   |-- shopify_adapter.py
|   |   |   |-- supplier_adapter.py
|   |   |   `-- web_adapter.py
|   |   |-- __init__.py
|   |   |-- apply_engine.py
|   |   |-- audit_export.py
|   |   |-- contracts.py
|   |   |-- dry_run_compiler.py
|   |   |-- lineage.py
|   |   |-- locks.py
|   |   |-- media_ingest.py
|   |   |-- normalize.py
|   |   |-- policy.py
|   |   |-- preflight.py
|   |   |-- progress_contract.py
|   |   |-- scoring.py
|   |   |-- shopify_graphql.py
|   |   |-- snapshot_lifecycle.py
|   |   |-- structural.py
|   |   `-- throttle.py
|   |-- tasks/
|   |   |-- __init__.py
|   |   |-- assistant_runtime.py
|   |   |-- audits.py
|   |   |-- chat_bulk.py
|   |   |-- control.py
|   |   |-- enrichment.py
|   |   |-- graphiti_sync.py
|   |   |-- ingest.py
|   |   |-- resolution_apply.py
|   |   `-- scrape_jobs.py
|   |-- utils/
|   |   `-- sku_ean_validator.py
|   |-- __init__.py
|   |-- ai_bot_server.py
|   |-- app.py
|   |-- app_factory.py
|   |-- bot_server.py
|   |-- celery_app.py
|   `-- database.py
|-- tests/
|   |-- api/
|   |   |-- __init__.py
|   |   |-- conftest.py
|   |   |-- test_apply_progress_contract.py
|   |   |-- test_approvals_api.py
|   |   |-- test_assistant_profile_contract.py
|   |   |-- test_audit_export_contract.py
|   |   |-- test_chat_bulk_workflow.py
|   |   |-- test_chat_contract.py
|   |   |-- test_chat_delegation_contract.py
|   |   |-- test_chat_memory_retrieval_contract.py
|   |   |-- test_chat_routing_contract.py
|   |   |-- test_chat_single_sku_workflow.py
|   |   |-- test_chat_stream.py
|   |   |-- test_chat_tier_runtime_contract.py
|   |   |-- test_core.py
|   |   |-- test_endpoints.py
|   |   |-- test_enrichment_audit_export_contract.py
|   |   |-- test_enrichment_capability_audit_contract.py
|   |   |-- test_enrichment_dry_run_contract.py
|   |   |-- test_enrichment_field_policy_contract.py
|   |   |-- test_fallback_stage_telemetry_contract.py
|   |   |-- test_field_policy_threshold_contract.py
|   |   |-- test_graph_oracle_adapter_contract.py
|   |   |-- test_idempotency_terminal_states_contract.py
|   |   |-- test_instrumentation_export_contract.py
|   |   |-- test_jobs_progress_contract.py
|   |   |-- test_jobs_retry.py
|   |   |-- test_jobs_stream_status_contract.py
|   |   |-- test_kill_switch_contract.py
|   |   |-- test_observability_correlation_contract.py
|   |   |-- test_oracle_signal_join_contract.py
|   |   |-- test_preference_signal_contract.py
|   |   |-- test_products_bulk_staging_contract.py
|   |   |-- test_products_history_diff_contract.py
|   |   |-- test_products_search_contract.py
|   |   |-- test_provider_fallback_contract.py
|   |   |-- test_recovery_logs.py
|   |   |-- test_redaction_retention_contract.py
|   |   |-- test_reliability_policy_contract.py
|   |   |-- test_resolution_dry_run.py
|   |   |-- test_resolution_rules.py
|   |   |-- test_snapshot_chain_contract.py
|   |   |-- test_tenant_rls_readiness_contract.py
|   |   |-- test_tool_projection_contract.py
|   |   |-- test_verification_oracle_contract.py
|   |   `-- test_versioning.py
|   |-- assistant/
|   |   `-- test_session_primer.py
|   |-- cli/
|   |   |-- __init__.py
|   |   `-- test_commands.py
|   |-- core/
|   |   |-- test_graphiti_client_contract.py
|   |   `-- test_synthex_entities.py
|   |-- daemons/
|   |   |-- benchmark_health_gate.py
|   |   `-- test_health_monitor.py
|   |-- e2e/
|   |   |-- chat.e2e.ts
|   |   |-- enrichment.e2e.ts
|   |   `-- job-progress.e2e.ts
|   |-- graph/
|   |   |-- test_bash_agent.py
|   |   |-- test_batch_tools.py
|   |   |-- test_compact_output.py
|   |   |-- test_deferred_loading.py
|   |   |-- test_fix_generation.py
|   |   |-- test_mcp_tool_examples.py
|   |   |-- test_performance_profiling.py
|   |   |-- test_root_cause_classifier.py
|   |   |-- test_runtime_optimizer.py
|   |   |-- test_sandbox_verifier.py
|   |   |-- test_sentry_feedback.py
|   |   |-- test_sentry_integration.py
|   |   |-- test_template_extraction.py
|   |   `-- test_tool_search.py
|   |-- integration/
|   |   |-- __init__.py
|   |   |-- test_enrichment_color_finish_accuracy.py
|   |   |-- test_enrichment_pipeline.py
|   |   |-- test_enrichment_retrieval_readiness.py
|   |   |-- test_enrichment_semantic_uplift_smoke.py
|   |   |-- test_gemini_verify.py
|   |   |-- test_graph_resilience.py
|   |   |-- test_image_improvements.py
|   |   |-- test_pentart_search.py
|   |   |-- test_planning_linker.py
|   |   `-- test_vendor_yaml_integration.py
|   |-- integrations/
|   |   `-- test_research_fallback.py
|   |-- jobs/
|   |   |-- __init__.py
|   |   |-- test_assistant_tier_queue_routing.py
|   |   |-- test_canary_rollback_contract.py
|   |   |-- test_cancellation.py
|   |   |-- test_chat_bulk_chunking.py
|   |   |-- test_chat_bulk_fairness.py
|   |   |-- test_deferred_verification_flow.py
|   |   |-- test_dispatcher.py
|   |   |-- test_enrichment_batch_queue_contract.py
|   |   |-- test_finalizer.py
|   |   |-- test_ingest_chunk_flow.py
|   |   |-- test_non_blocking_api_flow.py
|   |   |-- test_observability_metrics.py
|   |   |-- test_phase6_requirements.py
|   |   |-- test_priority_under_load.py
|   |   |-- test_progress_payload.py
|   |   |-- test_queue_routing.py
|   |   |-- test_restart_persistence.py
|   |   |-- test_retention_cleanup.py
|   |   |-- test_scraper_service_routing.py
|   |   |-- test_tier3_queue_ttl_deadletter_contract.py
|   |   `-- test_tier_queue_qos_contract.py
|   |-- resolution/
|   |   |-- test_apply_engine.py
|   |   |-- test_media_ingest.py
|   |   |-- test_policy.py
|   |   |-- test_preflight.py
|   |   |-- test_resolution_pipeline.py
|   |   `-- test_snapshot_lifecycle.py
|   |-- tasks/
|   |   |-- test_batch_emission.py
|   |   `-- test_graphiti_sync_contract.py
|   |-- unit/
|   |   |-- __init__.py
|   |   |-- test_adaptive_scraping.py
|   |   |-- test_ai_descriptions.py
|   |   |-- test_ai_inference.py
|   |   |-- test_antigravity_notify.py
|   |   |-- test_antigravity_watchdog.py
|   |   |-- test_attribute_extraction.py
|   |   |-- test_chat_router.py
|   |   |-- test_color_learning.py
|   |   |-- test_config_generator.py
|   |   |-- test_convention_checker.py
|   |   |-- test_embeddings.py
|   |   |-- test_enrichment_eligibility_matrix.py
|   |   |-- test_enrichment_oracle_contract.py
|   |   |-- test_enrichment_profile_contract.py
|   |   |-- test_enrichment_retry_idempotency.py
|   |   |-- test_firecrawl.py
|   |   |-- test_image_framework.py
|   |   |-- test_local_graph_store.py
|   |   |-- test_local_patterns.py
|   |   |-- test_mcp_server_contract.py
|   |   |-- test_product_families.py
|   |   |-- test_query_interface.py
|   |   |-- test_query_templates.py
|   |   |-- test_refactor_guard.py
|   |   |-- test_scraping_engine.py
|   |   |-- test_search_expand_bridge.py
|   |   |-- test_semantic_cache.py
|   |   |-- test_site_recon.py
|   |   |-- test_store_analyzer.py
|   |   |-- test_vendor_schema.py
|   |   |-- test_wave_sync.py
|   |   `-- test_web_search.py
|   |-- __init__.py
|   `-- conftest.py
|-- utils/
|   |-- __init__.py
|   |-- add_product_image.py
|   |-- approve_seo_csv.py
|   |-- assign_collections.py
|   |-- categorize_product.py
|   |-- create_shopify_redirect.py
|   |-- display_seo_comparison.py
|   |-- enrich_product_logistics.py
|   |-- find_product_image.py
|   |-- fix_product_handles.py
|   |-- generate_product_tags.py
|   `-- pentart_db.py
|-- Vektal/
|   |-- .obsidian/
|   |   |-- app.json
|   |   |-- appearance.json
|   |   |-- core-plugins.json
|   |   |-- graph.json
|   |   `-- workspace.json
|   `-- Welcome.md
|-- web/
|   |-- app.js
|   |-- auth_required.html
|   |-- index.html
|   `-- job_detail.html
|-- .env.example
|-- .gitattributes
|-- .gitignore
|-- .pre-commit-config.yaml
|-- .rules
|-- .verb.md
|-- AGENTS.md
|-- ARCHITECTURE.md
|-- CLAUDE.md
|-- claudesplan.md
|-- demo_framework.py
|-- docker-compose.secrets.yml
|-- docker-compose.yml
|-- Dockerfile.backend
|-- FAILURE_JOURNEY.md
|-- GEMINI.md
|-- gunicorn_config.py
|-- HARNESS_GAPS.md
|-- LEARNINGS.md
|-- npm-badge-png.md
|-- playwright.config.ts
|-- pyproject.toml
|-- README.md
|-- requirements.txt
|-- risk-policy.json
`-- STANDARDS.md
```
