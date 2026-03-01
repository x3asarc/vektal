# Phase 15 Research Completion & Summary

**Date:** 2026-03-01
**Status:** Research Complete - Ready for Planning

---

## Research Completion Summary

Comprehensive research has been conducted for Phase 15, answering all open questions from `15-ARCHITECTURE-LOCKED.md` and gathering industry best practices from 2026 sources.

### Open Questions Answered

#### 1. LLM Selection (ANSWERED)
**Decision: Adaptive routing based on task complexity**

```
Routing Logic:
1. Template match exists + confidence ≥0.95 → SKIP LLM (deterministic)
2. Infrastructure-only → Gemini Flash 1.5 (fast, cheap)
3. Code change ≤3 files + pattern ≥0.8 → Gemini Flash 1.5
4. Code change 4-5 files OR novel failure → Claude Sonnet 3.5
5. Multi-file refactoring OR complex → Claude Opus 4.5
```

**Cost-Performance Trade-offs:**
- Gemini Flash 1.5: $0.03/1M tokens (2-5s) - Infrastructure fixes, simple code
- Claude Sonnet 3.5: $3.00/1M tokens (10-20s) - Most code changes
- Claude Opus 4.5: $15.00/1M tokens (30-60s) - Complex refactoring

#### 2. Session Context Compression (ANSWERED)
**Decision: Manual YAML compression achieving 10x reduction**

**Compression Pipeline:**
- Git commits: 500 tokens → 100 tokens (5x reduction)
- Roadmap: 800 tokens → 120 tokens (6.7x reduction)
- Templates: 600 tokens → 100 tokens (6x reduction)
- **Total: ~12,000 tokens → ~1,200 tokens (10x reduction)**

**Advanced Tools:** LLMLingua available for dynamic content (up to 20x compression)

#### 3. Sandbox Container Image (ANSWERED)
**Decision: Extend existing backend image with hardened security profile**

**Security Layers:**
1. Seccomp profile (block ~44+ syscalls)
2. AppArmor/SELinux (MAC)
3. No-new-privileges (prevent setuid escalation)
4. Capability dropping (drop ALL, add back only needed)
5. Rootless execution (USER 1000:1000)
6. Read-only root filesystem

**Resource Limits:**
- Memory: 512MB hard limit, 256MB soft
- CPU: 50% of one core
- PIDs: 100 max
- Network: None (isolated)
- Timeout: 300s total, per-gate timeouts

#### 4. Template Storage Schema (ANSWERED)
**Decision: Hybrid Neo4j (primary) + PostgreSQL (cache)**

**Neo4j (Source of Truth):**
- Template relationships and pattern matching
- Similarity graphs and traversals
- Query performance: 20-50ms

**PostgreSQL (Operational Cache):**
- Frequently-used templates (last 30 days, >3 applications)
- Sandbox metadata, approval queue, metrics
- Cache hit performance: 2-5ms

**Sync:** Every 5 minutes or on template promotion

#### 5. Metrics Collection (ANSWERED)
**Decision: Custom metrics in PostgreSQL + Optional Prometheus export**

**PostgreSQL Tables:**
- `remedy_application_log` - Every template application
- `sandbox_run_metrics` - Gate timings, resource usage
- `approval_queue_metrics` - Approval cycle times

**Future Prometheus Integration:**
- Export endpoint for Grafana dashboards
- Time-series for trends (latency, cost, error rates)
- Alerts for pool exhaustion, approval backlogs

---

## Key Research Findings

### 1. Sandbox Security (Defense-in-Depth)

**Critical Insight:**
> "Defense-in-depth combining runtime monitoring, Seccomp profiles, AppArmor or SELinux, capability dropping, rootless execution, read-only filesystems, and network segmentation significantly reduces container escape likelihood and impact."

**Sources:**
- [Docker Seccomp Documentation](https://docs.docker.com/engine/security/seccomp/)
- [Docker Security Best Practices 2026](https://thelinuxcode.com/docker-security-best-practices-2026-hardening-the-host-images-and-runtime-without-slowing-teams-down/)
- [Container Escape Vulnerabilities 2026](https://blaxel.ai/blog/container-escape)

### 2. LLM Self-Healing Systems

**Critical Insight:**
> "LLMs in 2026 have 'agentic' nature - can execute autonomous tasks across multiple files while preserving semantic meaning. Earlier 2024 models required line-by-line guidance. Meta, Google, Amazon pilot agentic workflows with heavy guardrails, custom retrieval, and mandatory review gates."

**Sources:**
- [Designing Self-Healing Systems for LLM Platforms](https://latitude.so/blog/designing-self-healing-systems-for-llm-platforms)
- [LLM-Driven Code Refactoring 2026](https://www.analyticsinsight.net/artificial-intelligence/how-llms-are-changing-the-way-developers-refactor-code)

### 3. Prompt Compression

**Critical Insight:**
> "Three core techniques — summarization, keyphrase extraction, and semantic chunking — can achieve 5–20x compression while maintaining or improving accuracy, translating to 70–94% cost savings in production AI systems."

**Sources:**
- [Prompt Compression for LLM Optimization](https://machinelearningmastery.com/prompt-compression-for-llm-generation-optimization-and-cost-reduction/)
- [LLMLingua GitHub](https://github.com/microsoft/LLMLingua)

### 4. Neo4j vs PostgreSQL for Templates

**Critical Insight:**
> "Neo4j's pattern-matching syntax expresses in one line what would require multiple joins in SQL. Many large companies like Walmart and eBay use Neo4j for recommendation engines. Neo4j excels at traversal-heavy queries, while PostgreSQL offers balance for lightweight scenarios."

**Sources:**
- [Neo4j vs PostgreSQL](https://dev.to/pawnsapprentice/postgresql-vs-neo4j-choosing-the-right-database-for-your-project-1o59)
- [Exploring Graph Database Capabilities](https://medium.com/self-study-notes/exploring-graph-database-capabilities-neo4j-vs-postgresql-105c9e85bb5d)

### 5. Approval Workflows

**Critical Insight:**
> "Approval systems can reduce cycle times by up to 75% while ensuring consistent application of business rules and maintaining complete audit trails. Automation improves workflows by routing requests, checking completeness, sending reminders, and escalating delays."

**Source:**
- [Approval Workflow Process](https://kissflow.com/workflow/approval-process/)

### 6. Connection Pool Auto-Tuning

**Critical Insight:**
> "PgBouncer doesn't have built-in auto-tuning, but external poolers allow dynamic connection scaling according to demand. Key metrics: cl_waiting vs sv_idle, pool utilization, query latency. Alert if waiting > 0 while idle = 0."

**Sources:**
- [PgBouncer Best Practices](https://techcommunity.microsoft.com/blog/adforpostgresql/pgbouncer-best-practices-in-azure-database-for-postgresql-%E2%80%93-part-1/4453323)
- [How to Handle 10K Connections with PgBouncer](https://oneuptime.com/blog/post/2026-01-26-pgbouncer-connection-pooling/view)

### 7. Blast Radius Analysis

**Critical Insight:**
> "Blast radius refers to scope of impact a change can have. Tools map real downstream impact so teams can review and ship with confidence. Service-discovery layers stitch REST endpoints, gRPC, queues, and database migrations into living dependency graph."

**Sources:**
- [Blast Radius: Impact Analysis](https://blast-radius.dev/)
- [Microservices Impact Analysis](https://www.augmentcode.com/tools/microservices-impact-analysis)

### 8. Adaptive Learning Systems

**Critical Insight:**
> "Adaptive systems leverage ML to gather, analyze, and interpret learner data, dynamically adjusting experience. Confidence thresholds enable adaptive online threshold selection robust to distribution shifts with statistical guarantees on false positive/negative rates."

**Sources:**
- [Adaptive Learning Using AI](https://www.mdpi.com/2227-7102/13/12/1216)
- [Online Adaptive Anomaly Thresholding](https://www.amazon.science/publications/online-adaptive-anomaly-thresholding-with-confidence-sequences)

---

## Implementation Status

### Initial Implementation by Gemini (See `changes.md`)

Gemini created initial implementation files during research phase:

1. **`src/graph/sandbox_verifier.py`** (Created)
   - `SandboxRunner` class with 6-gate protocol
   - Uses `ast.parse()` for syntax gate
   - Uses `subprocess` for pytest/mypy in sandbox
   - Automated filesystem setup

2. **`src/graph/remediators/code_remediator.py`** (Created)
   - Base class for code remediators
   - Integrates with `SandboxRunner`
   - Defines parameter schema for files and tests

3. **`scripts/test_sandbox.py`** (Created)
   - Integration test for sandbox verification
   - Tests success and failure detection
   - Basic environment setup

**Status:**
- Sandbox engine: Functional (subprocess-based simulation)
- Integration: Code remediator registered
- Tests: Passing for syntax and unit gates

### Critical Files for Planning

When creating execution plans, reference:

1. **Research:** `.planning/phases/15-self-healing-dynamic-scripting/15-RESEARCH.md`
   - Comprehensive technical research (497 lines)
   - Covers all architecture decisions
   - Industry best practices and sources

2. **Architecture:** `.planning/phases/15-self-healing-dynamic-scripting/15-ARCHITECTURE-LOCKED.md`
   - 11 tasks defined and prioritized
   - 3-phase rollout strategy
   - Success criteria and dependencies

3. **Initial Implementation:** `.planning/phases/15-self-healing-dynamic-scripting/changes.md`
   - Files Gemini created during research
   - Sandbox verifier implementation
   - Code remediator base class
   - Integration tests

4. **This Summary:** `.planning/phases/15-self-healing-dynamic-scripting/RESEARCH-COMPLETION.md`
   - Answers to open questions
   - Research findings summary
   - Implementation status
   - Next steps

---

## Next Steps for Planning

### Plan Creation Checklist

When creating `15-XX-PLAN.md` files, ensure they:

1. **Reference Research**
   - Cite decisions from RESEARCH.md
   - Use recommended tech stack (docker-py, Neo4j hybrid, LLMLingua)
   - Follow security best practices

2. **Build on Initial Implementation**
   - Extend `sandbox_verifier.py` with full 6-gate protocol
   - Add Type, Contract, Governance, Rollback gates
   - Implement docker-py instead of subprocess simulation

3. **Honor Architecture Decisions**
   - Follow 3-phase rollout (Read-Only → Infrastructure → Code)
   - Implement hybrid template storage (Neo4j + PostgreSQL)
   - Use adaptive LLM routing
   - Apply 10x session context compression

4. **Address Integration Points**
   - Phase 14.3 NullClaw architecture (extend remediation_registry.py)
   - Sentry ingestion (use existing sentry_ingestor.py)
   - Neo4j graph (Phase 14 infrastructure)
   - Approval queue (new PostgreSQL tables)

### Suggested Plan Structure

Based on architecture document (11 tasks, reordered by priority):

**Phase 15.0: Foundation (Read-Only Mode)**
- 15-01: Universal Sandbox with 6-gate verification
- 15-02: Session Context & Memory Architecture (lazy-load YAML)
- 15-03: Root-Cause Classifier (LLM + Graph)

**Phase 15.1: Detection & Learning (Still Read-Only)**
- 15-04: Autonomous Fix Generation (Templates + LLM)
- 15-05: Learnings Loop (Template extraction)
- 15-06: Sentry Integration Verification

**Phase 15.2: Controlled Autonomy (Infrastructure Auto-Apply)**
- 15-07: Infrastructure Bash Agent
- 15-08: Performance Profiling & Bottleneck Detection

**Phase 15.3: Full Autonomy (Code Auto-Apply)**
- 15-09: Runtime Optimization Engine
- 15-10: Sentry Feedback Closure
- 15-11: Autonomous Approval Queue

---

## Success Metrics

From architecture document, Phase 15 must achieve:

1. ✅ Sandbox passes all 6 gates before production apply
2. ✅ 95%+ transient infrastructure issues self-heal
3. ✅ Performance optimization proven via metrics (cost -20%, latency -30% per quarter)
4. ✅ Learnings loop: Templates grow from LLM successes (2+ apps → template)
5. ✅ Session context: Git + phase + remedies auto-loaded as compressed YAML
6. ✅ Approval queue: Changes <0.9 confidence require human review
7. ✅ Sentry-driven triage: Issues normalized and routed <5min
8. ✅ Validated remedies: Only proven fixes (via Sentry feedback) promoted to memory

---

## Research Sources Index

**Docker Security:**
- [Docker Seccomp Documentation](https://docs.docker.com/engine/security/seccomp/)
- [Docker Security Best Practices 2026](https://thelinuxcode.com/docker-security-best-practices-2026-hardening-the-host-images-and-runtime-without-slowing-teams-down/)
- [Container Escape Vulnerabilities 2026](https://blaxel.ai/blog/container-escape)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

**LLM Self-Healing:**
- [Designing Self-Healing Systems for LLM Platforms](https://latitude.so/blog/designing-self-healing-systems-for-llm-platforms)
- [LLM-Driven Code Refactoring 2026](https://www.analyticsinsight.net/artificial-intelligence/how-llms-are-changing-the-way-developers-refactor-code)

**Sentry Integration:**
- [Sentry Python SDK GitHub](https://github.com/getsentry/sentry-python)
- [Sentry Python Documentation](https://docs.sentry.io/platforms/python/)
- [Sentry Workflow Triage](https://blog.sentry.io/sentry-workflow-triage/)

**Database Selection:**
- [Neo4j vs PostgreSQL](https://dev.to/pawnsapprentice/postgresql-vs-neo4j-choosing-the-right-database-for-your-project-1o59)
- [Exploring Graph Database Capabilities](https://medium.com/self-study-notes/exploring-graph-database-capabilities-neo4j-vs-postgresql-105c9e85bb5d)
- [Postgres vs Neo4j Fundamentals](https://pgbench.com/comparisons/postgres-vs-neo4j/)

**Prompt Compression:**
- [Prompt Compression for LLM Optimization](https://machinelearningmastery.com/prompt-compression-for-llm-generation-optimization-and-cost-reduction/)
- [LLMLingua GitHub](https://github.com/microsoft/LLMLingua)
- [Token Optimization Guide](https://redis.io/blog/llm-token-optimization-speed-up-apps/)

**Approval Workflows:**
- [Approval Workflow Process](https://kissflow.com/workflow/approval-process/)
- [Understanding Approval Workflows](https://www.wrike.com/workflow-guide/approval-workflow/)

**Connection Pooling:**
- [PgBouncer Best Practices](https://techcommunity.microsoft.com/blog/adforpostgresql/pgbouncer-best-practices-in-azure-database-for-postgresql-%E2%80%93-part-1/4453323)
- [How to Handle 10K Connections with PgBouncer](https://oneuptime.com/blog/post/2026-01-26-pgbouncer-connection-pooling/view)

**Blast Radius Analysis:**
- [Blast Radius: Impact Analysis](https://blast-radius.dev/)
- [Microservices Impact Analysis](https://www.augmentcode.com/tools/microservices-impact-analysis)

**Adaptive Learning:**
- [Adaptive Learning Using AI](https://www.mdpi.com/2227-7102/13/12/1216)
- [Online Adaptive Anomaly Thresholding](https://www.amazon.science/publications/online-adaptive-anomaly-thresholding-with-confidence-sequences)

---

*Research Completed: 2026-03-01*
*Ready for: Phase 15 execution planning*
