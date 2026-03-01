# Phase 15 Research: Self-Healing & Runtime Optimization (Comprehensive)

**Date:** 2026-03-01
**Status:** `Enhanced - Comprehensive Deep Research`
**Evidence:**
- Context7: `/docker/docs`, `/getsentry/sentry-python`
- Perplexity: Deep-pass on GNN blast radius + Sandbox hardening
- Web Research: 2026 industry best practices (Docker security, LLM self-healing, Sentry integration, Neo4j vs PostgreSQL, prompt compression, approval workflows, connection pooling, blast radius analysis, adaptive learning)

---

## 1. Executive Summary

Phase 15 transitions the platform from reactive monitoring to **autonomous remediation**. The system will ingest Sentry failures, classify them using the Phase 14 Codebase Knowledge Graph, generate fixes, verify them in a hardened multi-gate sandbox, and promote successful patterns to reusable "Remedy Templates."

**Key Innovation:** Progressive autonomy rollout (Read-Only → Infrastructure → Code) with hybrid learning (deterministic templates + LLM fallback) and 3-tier memory architecture (Redis + In-Prompt + Neo4j) ensures safety while building confidence.

**Sources:**
- [Designing Self-Healing Systems for LLM Platforms](https://latitude.so/blog/designing-self-healing-systems-for-llm-platforms)
- [LLM-Driven Code Refactoring 2026](https://www.analyticsinsight.net/artificial-intelligence/how-llms-are-changing-the-way-developers-refactor-code)

---

## 2. Sandbox Architecture & Security (Defense-in-Depth)

### A. Container Escape Prevention

**Threat Model:** LLM-generated code is untrusted. Standard Docker namespaces share the host kernel, making kernel exploits (namespaces, cgroups, eBPF, overlayfs) potential escape vectors.

**Defense Layers:**

1. **Seccomp Profiles** - Restrict system calls
   - Default Docker seccomp profile blocks ~44 of 300+ syscalls
   - Custom profile for Phase 15: Block additional dangerous syscalls (mount, pivot_root, unshare, clone with CLONE_NEWUSER)
   - Allowlist approach: Deny by default, permit only necessary calls
   - Reference: [Docker Seccomp Documentation](https://docs.docker.com/engine/security/seccomp/)

2. **AppArmor/SELinux** - Mandatory Access Control (MAC)
   - AppArmor profile restricts file access, network access, and capabilities
   - Confine container to read-only filesystem except `/tmp` and sandbox workspace
   - Reference: [Docker Security Best Practices 2026](https://thelinuxcode.com/docker-security-best-practices-2026-hardening-the-host-images-and-runtime-without-slowing-teams-down/)

3. **No New Privileges** - Prevent privilege escalation
   - `--security-opt no-new-privileges:true` blocks setuid binaries
   - Prevents container processes from gaining additional privileges

4. **Capability Dropping** - Remove dangerous Linux capabilities
   - Drop ALL capabilities by default
   - Only add back essential ones (CAP_NET_BIND_SERVICE if needed for tests)

5. **Rootless Execution** - Run as non-root user
   - Container runs as `USER 1000:1000` (non-privileged)
   - Prevents many privilege escalation attacks

6. **Read-Only Root Filesystem** - Immutable container
   - `--read-only=true` prevents writes to container filesystem
   - Only `/tmp` (tmpfs) and sandbox workspace are writable

**Key Insight from Research:**
> "Defense-in-depth combining runtime monitoring, Seccomp profiles, AppArmor or SELinux, capability dropping, rootless execution, read-only filesystems, and network segmentation significantly reduces container escape likelihood and impact."
>
> Source: [Container Escape Vulnerabilities 2026](https://blaxel.ai/blog/container-escape)

### B. Resource Constraints

```python
container = client.containers.run(
    image="backend-sandbox:latest",
    command="python -m pytest",
    mem_limit="512m",           # Hard memory limit
    mem_reservation="256m",     # Soft limit (allows burst)
    cpu_quota=50000,            # 50% of one core (100000 = 100%)
    cpu_period=100000,          # Default period
    pids_limit=100,             # Max processes/threads
    network_mode="none",        # No network access
    read_only=True,             # Immutable root filesystem
    tmpfs={'/tmp': 'size=100m,mode=1777'},  # Ephemeral temp storage
    volumes={
        sandbox_path: {'bind': '/app', 'mode': 'rw'}
    },
    security_opt=[
        'no-new-privileges:true',
        'apparmor=docker-default',
        'seccomp=/path/to/phase15-seccomp.json'
    ],
    cap_drop=['ALL'],           # Drop all capabilities
    cap_add=[],                 # Add back only if needed
    user='1000:1000'            # Non-root user
)
```

**Timeout Protection:**
- Container execution timeout: 300s (5 minutes) for full 6-gate verification
- Individual gate timeouts: Syntax (5s), Type (30s), Unit (120s), Contract (30s), Governance (30s), Rollback (30s)
- Exceeded timeouts trigger automatic container kill and RED verdict

### C. The 6-Gate Verification Protocol

Every remediation must pass **all six gates in sequence**:

1. **Syntax Gate** (Host-side, <5s)
   - `ast.parse()` validation
   - No sandbox needed - pure static analysis
   - Catches basic Python syntax errors before sandbox spin-up

2. **Type Gate** (Sandbox, <30s)
   - `mypy --strict --config-file=mypy.ini`
   - Type hint compliance
   - Ensures type safety of generated code

3. **Unit Gate** (Sandbox, <120s)
   - `pytest -x --tb=short -q tests/unit/`
   - Run tests for modified modules + high-risk dependents (from Phase 14 graph)
   - Stop on first failure for fast feedback

4. **Contract Gate** (Sandbox, <30s)
   - API schema validation via Pydantic models
   - Ensure no breaking changes to REST endpoints
   - Validate OpenAPI schema compatibility

5. **Governance Gate** (Sandbox, <30s)
   - `python scripts/governance/risk_tier_gate.py --changed-files <files>`
   - Check against STANDARDS.md compliance
   - Block on Critical/High severity issues
   - Validate no secrets, proper structure, license compliance

6. **Rollback Gate** (Host-side, <30s)
   - Git diff analysis - verify changes are reversible
   - Database migration dry-run (if schema changes detected)
   - Document rollback procedure in sandbox metadata

**Outcome Classification:**
- **GREEN**: All 6 gates pass → Eligible for production promotion (if confidence ≥0.9)
- **YELLOW**: Minor warnings → Human review required (approval queue)
- **RED**: Any gate fails → Block, escalate, log to FAILURE_JOURNEY.md

---

## 3. LLM Selection & Adaptive Routing

### A. Model Selection Strategy (Answer to Architecture Open Question #1)

**Recommendation: Adaptive routing based on task complexity**

**Routing Logic:**
```
1. Template match exists + confidence ≥0.95 → SKIP LLM (deterministic template)
2. Infrastructure-only remediation → Gemini Flash 1.5 (fast, cheap)
3. Code change ≤3 files + pattern match ≥0.8 → Gemini Flash 1.5
4. Code change 4-5 files OR novel failure → Claude Sonnet 3.5
5. Multi-file refactoring OR complex root cause → Claude Opus 4.5
```

**Cost-Performance Trade-offs:**

| Model | Cost/1M tokens | Speed | Best For |
|-------|----------------|-------|----------|
| Gemini Flash 1.5 | $0.03 | 2-5s | Infrastructure fixes, simple code changes |
| Claude Sonnet 3.5 | $3.00 | 10-20s | Most code changes, moderate complexity |
| Claude Opus 4.5 | $15.00 | 30-60s | Complex refactoring, novel failures |

**Research Finding:**
> "LLMs code refactoring models in 2026 have 'agentic' nature - can execute autonomous tasks across multiple files while preserving semantic meaning. Earlier 2024 models required line-by-line guidance."
>
> Source: [Why Developers Are Relying on LLMs to Refactor Code](https://www.analyticsinsight.net/artificial-intelligence/how-llms-are-changing-the-way-developers-refactor-code)

**Template-First Philosophy:**
- 95% of infrastructure issues should hit templates within 2 weeks of deployment
- 70-80% of code issues should hit templates within 3 months
- LLM invocations should decline over time as template library grows

### B. Confidence Scoring

Remediation confidence based on:
1. **Template match score** (0.0-1.0): Cosine similarity of failure fingerprint to known templates
2. **Graph evidence** (0.0-1.0): How well Phase 14 graph explains the root cause
3. **Test coverage** (0.0-1.0): Percentage of affected code covered by tests
4. **Historical success** (0.0-1.0): Similar fixes that passed 6-gate and worked in production

**Composite Confidence:**
```python
confidence = (
    0.35 * template_match_score +
    0.25 * graph_evidence_score +
    0.20 * test_coverage_score +
    0.20 * historical_success_score
)
```

**Threshold-Based Routing:**
- `confidence ≥ 0.9` → Auto-apply to production (Phase 15.2 only)
- `confidence 0.7-0.89` → Create approval queue entry (human review)
- `confidence < 0.7` → Block autonomous apply, escalate to developer

---

## 4. Session Context Compression (Answer to Architecture Open Question #2)

### A. Compression Techniques

**Problem:** Raw session context (git commits + phase + roadmap + remedies) can consume 10,000+ tokens. Phase 15 needs this context loaded for every fix generation.

**Solution: Multi-stage compression achieving 5-20x reduction**

**Compression Pipeline:**

1. **Git Commits** (Target: 50-100 tokens per commit)
   ```yaml
   # BEFORE (verbose): 500 tokens
   commit a1b2c3d4
   Author: Developer <dev@example.com>
   Date: 2026-03-01 14:30:00

   feat(graph): add backend resolver with three-tier fallback

   - Implemented backend_resolver.py with Aura/local/snapshot fallback
   - Added runtime manifest for backend status tracking
   - Integrated with MCP server for graph availability queries

   Files changed:
   - src/graph/backend_resolver.py (new, 245 lines)
   - src/graph/mcp_server.py (modified, +32 lines)
   - tests/graph/test_backend_resolver.py (new, 178 lines)

   # AFTER (compressed): 100 tokens
   commits:
     - hash: a1b2c3d
       msg: "feat(graph): backend resolver 3-tier fallback"
       files: [backend_resolver.py, mcp_server.py]
       impact: graph_availability
   ```

2. **Roadmap Context** (Target: 100-150 tokens)
   ```yaml
   # BEFORE (verbose): 800 tokens
   # Full roadmap with all phases, requirements, success criteria...

   # AFTER (compressed): 120 tokens
   roadmap:
     milestone: M3_Self_Healing
     current_phase: 15
     goal: "Autonomous remediation + performance optimization"
     completed: [1-14.3]
     next: 16_Admin_Visibility
   ```

3. **Remedy Templates** (Target: 80-120 tokens per template)
   ```yaml
   # BEFORE (verbose): 600 tokens per template with full AST, examples, metadata

   # AFTER (compressed): 100 tokens
   templates:
     - fp: "enrichment.py:TimeoutError"
       fix: "timeout 30→60s"
       conf: 0.92
       apps: 5
     - fp: "database.py:ConnectionError"
       fix: "pool_size +2"
       conf: 0.88
       apps: 3
   ```

**Total Compression:**
- Raw: ~12,000 tokens
- Compressed: ~1,200 tokens
- **Reduction: 10x** (90% token savings)

**Research Finding:**
> "Three core techniques — summarization, keyphrase extraction, and semantic chunking — can achieve 5–20x compression while maintaining or improving accuracy, translating to 70–94% cost savings in production AI systems."
>
> Source: [Prompt Compression for LLM Optimization](https://machinelearningmastery.com/prompt-compression-for-llm-generation-optimization-and-cost-reduction/)

### B. Advanced Compression Tools

**LLMLingua** - Microsoft's prompt compression framework:
- Up to 20x compression with minimal performance loss
- Coarse-to-fine strategy: Document → Paragraph → Sentence → Token
- Budget controller maintains semantic integrity
- Reference: [LLMLingua GitHub](https://github.com/microsoft/LLMLingua)

**Phase 15 Decision:** Use manual YAML compression for session context (simpler, predictable) and reserve LLMLingua for dynamic failure context compression (variable length, unpredictable content).

---

## 5. Template Storage: Neo4j vs PostgreSQL (Answer to Architecture Open Question #4)

### A. Comparative Analysis

| Feature | Neo4j | PostgreSQL |
|---------|-------|------------|
| **Pattern Matching** | Native Cypher patterns, 1 line vs multiple JOINs | Requires complex SQL JOINs for graph-like queries |
| **Traversal Performance** | O(1) relationship traversal | O(n log n) for JOIN-heavy queries |
| **Template Similarity** | Vector search + graph proximity | Vector extension (pgvector) + SQL |
| **Query Complexity** | Simple for relationships | Complex for deep relationships |
| **Write Performance** | Fast for graph writes | Faster for bulk inserts |
| **Existing Infrastructure** | Already used in Phase 14 | Already used for app data |
| **Operational Overhead** | Separate database | Same database as app |

**Research Finding:**
> "Neo4j's pattern-matching syntax expresses in one line what would require multiple joins in SQL, enabling navigation of complex networks, calculation of shortest paths, and deep traversals intuitively. Many large companies like Walmart and eBay use Neo4j for recommendation engines."
>
> Sources:
> - [Neo4j vs PostgreSQL](https://dev.to/pawnsapprentice/postgresql-vs-neo4j-choosing-the-right-database-for-your-project-1o59)
> - [Exploring Graph Database Capabilities](https://medium.com/self-study-notes/exploring-graph-database-capabilities-neo4j-vs-postgresql-105c9e85bb5d)

### B. Decision: Hybrid Approach

**Template Storage:** Neo4j (primary) + PostgreSQL (cache)

**Rationale:**
1. **Neo4j for Template Relationships**
   - Templates form a graph: Similar failures cluster, remedies inherit from base patterns
   - Pattern matching: "Find templates where failure signature is similar AND affected modules overlap"
   - Cypher query: `MATCH (t:RemedyTemplate)-[:SIMILAR_TO]->(t2) WHERE t.fingerprint =~ $pattern RETURN t, t2`

2. **PostgreSQL for Operational Data**
   - Sandbox run metadata (status, confidence, logs)
   - Approval queue (pending approvals, user actions)
   - Metrics and time-series data (template application counts, success rates)

3. **Synchronization Pattern**
   - Neo4j is source of truth for templates
   - PostgreSQL caches frequently-used templates (last 30 days, >3 applications)
   - Sync every 5 minutes or on template promotion

**Template Query Performance:**
- Neo4j direct query: 20-50ms (graph traversal)
- PostgreSQL cache hit: 2-5ms (indexed lookup)
- Cache miss → Neo4j fallback → Update cache

**Example Queries:**

```cypher
// Neo4j: Find similar remedies (relationship-based)
MATCH (f:Failure {type: $failure_type})-[:RESOLVED_BY]->(t:RemedyTemplate)
MATCH (t)-[:SIMILAR_TO*1..2]->(similar:RemedyTemplate)
WHERE similar.confidence > 0.8
RETURN similar
ORDER BY similar.applications DESC
LIMIT 5
```

```sql
-- PostgreSQL: Fast cache lookup (index-based)
SELECT template_id, fingerprint, remedy_payload, confidence
FROM remedy_template_cache
WHERE fingerprint_hash = md5($fingerprint)
  AND confidence >= 0.8
  AND last_applied_at > NOW() - INTERVAL '30 days'
ORDER BY application_count DESC
LIMIT 5;
```

---

## 6. Approval Queue System Design

### A. PostgreSQL Schema

```sql
CREATE TABLE pending_approvals (
    id SERIAL PRIMARY KEY,
    approval_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,  -- 'code_change', 'config_change', 'optimization'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    diff TEXT,  -- Git diff output
    confidence NUMERIC(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    sandbox_run_id INTEGER REFERENCES sandbox_runs(id),
    blast_radius_files INTEGER NOT NULL DEFAULT 0,
    blast_radius_loc INTEGER NOT NULL DEFAULT 0,

    -- Workflow state
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'expired'
    priority VARCHAR(10) NOT NULL DEFAULT 'normal',  -- 'low', 'normal', 'high', 'critical'

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,  -- Auto-reject after expiration
    resolved_at TIMESTAMP,
    resolved_by_user_id INTEGER REFERENCES users(id),
    resolution_note TEXT,

    -- Metadata
    metadata JSONB,  -- Flexible storage for additional context

    -- Indexes
    INDEX idx_pending_approvals_status (status) WHERE status = 'pending',
    INDEX idx_pending_approvals_expires (expires_at) WHERE status = 'pending',
    INDEX idx_pending_approvals_priority (priority, created_at)
);

CREATE TABLE approval_audit_log (
    id SERIAL PRIMARY KEY,
    approval_id UUID NOT NULL REFERENCES pending_approvals(approval_id),
    action VARCHAR(50) NOT NULL,  -- 'created', 'approved', 'rejected', 'expired', 'viewed'
    actor_user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    context JSONB  -- Additional context (IP, user agent, etc.)
);
```

### B. Approval Workflow

**Routing Logic:**

```python
def route_remediation(remediation: Remediation, sandbox_result: SandboxResult) -> ApprovalDecision:
    """Route remediation to auto-apply or approval queue."""

    # Hard blocks (always reject)
    if sandbox_result.verdict == "RED":
        return ApprovalDecision(action="reject", reason="sandbox_failed")

    if sandbox_result.blast_radius_files > 5 or sandbox_result.blast_radius_loc > 500:
        return ApprovalDecision(action="approve_required", reason="blast_radius_exceeded")

    # Confidence-based routing
    if remediation.confidence >= 0.9 and sandbox_result.verdict == "GREEN":
        return ApprovalDecision(action="auto_apply", reason="high_confidence")

    if remediation.confidence >= 0.7:
        return ApprovalDecision(
            action="approve_required",
            reason="medium_confidence",
            priority="normal",
            expires_in_hours=72
        )

    # Low confidence - block
    return ApprovalDecision(action="reject", reason="low_confidence")
```

**Expiration Handling:**

```python
# Cron job runs every hour
def expire_stale_approvals():
    """Auto-reject approvals that exceeded expiration time."""
    expired = db.query(PendingApproval).filter(
        PendingApproval.status == "pending",
        PendingApproval.expires_at < datetime.now()
    ).all()

    for approval in expired:
        approval.status = "expired"
        approval.resolved_at = datetime.now()
        approval.resolution_note = "Auto-expired due to timeout"

        # Log audit trail
        AuditLog.create(
            approval_id=approval.approval_id,
            action="expired",
            timestamp=datetime.now()
        )

    db.commit()
```

**Research Finding:**
> "Approval systems can reduce cycle times by up to 75% while ensuring consistent application of business rules and maintaining complete audit trails. Automation improves workflows by routing requests to appropriate approvers based on content and rules, automatically checking for completeness, sending reminders for pending items, and escalating delays."
>
> Source: [Approval Workflow Process](https://kissflow.com/workflow/approval-process/)

### C. User Experience

**CLI Integration:**

```bash
# List pending approvals
$ python -m scripts.approvals list
┌─────────────────────────────────────────────────────────────┐
│ PENDING APPROVALS (3)                                       │
└─────────────────────────────────────────────────────────────┘

[1] Fix enrichment timeout (confidence: 0.85)
    Files: 2 | LOC: 45 | Age: 2h
    → /approve 1  or  /reject 1

[2] Increase connection pool size (confidence: 0.78)
    Files: 1 | LOC: 8 | Age: 5h
    → /approve 2  or  /reject 2

[3] Refactor import resolver (confidence: 0.72)
    Files: 4 | LOC: 320 | Age: 1d | EXPIRES: 2d
    → /approve 3  or  /reject 3

# Approve with note
$ python -m scripts.approvals approve 1 --note "Verified in staging"

# View diff before approving
$ python -m scripts.approvals diff 3
```

**Chat Integration:**

```
User: /approvals