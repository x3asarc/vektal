# Health Detection → Remediation Routing Plan

## Current Architecture (What Exists)

### 1. Detection Layer ✅
**File**: `scripts/daemons/health_monitor.py`
- Monitors Sentry, Neo4j, dependencies every 2 minutes
- Writes health cache to `.graph/health-cache.json`
- **Current auto-heal trigger**: Spawns `orchestrate_healers.py` with `--issue-json` when Sentry issues detected

**File**: `scripts/governance/health_gate.py`
- Fast PreToolUse hook reads cache (<5ms)
- Logs warnings, never blocks

### 2. Orchestration Layer ✅
**File**: `src/graph/orchestrate_healers.py`
- **Entry point**: `async def orchestrate_remediation(sentry_issue: dict) -> dict`
- **Steps**:
  1. **Normalize** Sentry payload → stable schema
  2. **Classify** using `RootCauseClassifier` (3-tier: pattern/graph/LLM)
  3. **Route** to service based on classification
  4. **Execute** remediation via `NanoFixerLoop`
  5. **Record** outcome to `.graph/remediation-outcomes.jsonl`

**Service routing map**:
```python
CATEGORY_SERVICE_MAP = {
    "AURA_UNREACHABLE": "aura",
    "LOCAL_NEO4J_START_FAIL": "docker",
    "SNAPSHOT_CORRUPT": "local_snapshot",
    "SYNC_TIMEOUT": "graph_sync",
}
```

### 3. Classification Layer ✅
**File**: `src/graph/root_cause_classifier.py`
- **3-tier classification**:
  1. **Pattern matching** (90%+ confidence) - deterministic rules
  2. **Graph analysis** (80%+ confidence) - queries knowledge graph for similar failures
  3. **LLM fallback** - for novel failures
- Returns: `(category, confidence, evidence)` where category ∈ {infrastructure, code, config, unknown}

### 4. Remediation Registry ✅
**File**: `src/graph/remediation_registry.py`
- Auto-discovers remediators from `src/graph/remediators/`
- Singleton registry pattern
- Dynamic loading of all `UniversalRemediator` subclasses

### 5. Universal Fixer Loop ✅
**File**: `src/graph/universal_fixer.py`
- **NanoFixerLoop**: Probe → Validate → Act → Verify
- Contract:
  - `UniversalRemediator` base class (abstract)
  - Required methods: `validate_environment()`, `diagnose_and_fix()`
  - Returns: `RemediationResult(success, message, actions_taken)`
- Logs outcomes to `LEARNINGS.md`

### 6. Existing Remediators ✅
**Directory**: `src/graph/remediators/`
- ✅ `aura_remediator.py` - Resume Neo4j Aura instances
- ✅ `bash_agent.py` - Execute safe Bash commands for infra fixes
- ✅ `code_remediator.py` - Code fixes (LLM-generated patches)
- ✅ `docker_remediator.py` - Docker container restarts, health checks
- ✅ `git_staleness_guard.py` - Detect and warn on stale branches
- ✅ `llm_remediator.py` - Generic LLM-based remediation
- ✅ `optimizer_remediator.py` - Performance optimization (pools, timeouts)
- ✅ `redis_remediator.py` - Redis connection fixes, cache clears
- ✅ `snapshot_remediator.py` - Local graph snapshot repair
- ✅ `sync_remediator.py` - Graph sync timeout fixes

---

## Current Flow (Sentry Only)

```
health_monitor.py (checks Sentry API)
    ↓ (when issues found)
Spawns: orchestrate_healers.py --issue-json '{...}'
    ↓
orchestrate_remediation(issue)
    ↓
1. Normalize payload
2. RootCauseClassifier.classify()
    ↓
3. route_service_for_classification()
    ↓
4. NanoFixerLoop.fix_service(service, params)
    ↓
5. registry.get_tool(service)
    ↓
6. remediator.validate_environment()
7. remediator.diagnose_and_fix(params)
    ↓
8. Record outcome → .graph/remediation-outcomes.jsonl
9. Log to LEARNINGS.md
```

---

## THE GAP: Missing Routing for Non-Sentry Issues

### ❌ Neo4j Down Detection
**Current**: `health_monitor.py` detects `neo4j.status == "down"`
**Missing**: No auto-heal trigger! Just sets mode to "local_snapshot"
**Needed**: Spawn Docker remediator to restart Neo4j container

### ❌ Dependency Missing Detection
**Current**: `health_monitor.py` detects missing deps, spawns `pip install`
**Missing**: No verification of success, no fallback
**Needed**: Proper remediation flow with verification

### ❌ Proactive Health Issues
**Current**: Health gate logs warnings but takes no action
**Missing**: Integration with remediation system
**Needed**: Route warnings to appropriate remediators

---

## Solution: Complete Health → Remediation Routing

### Phase 1: Extend health_monitor.py Auto-Heal Triggers

**File**: `scripts/daemons/health_monitor.py`

**Add**: Trigger orchestration for all detected issues, not just Sentry

```python
async def handle_health_issues(state: Dict[str, Any]) -> None:
    """Route detected health issues to remediation orchestrator."""

    # 1. Sentry issues (already implemented)
    if state["sentry"]["status"] == "issues":
        await _trigger_sentry_remediation(state["sentry"])

    # 2. NEW: Neo4j down
    if state["neo4j"]["status"] == "down":
        await _trigger_neo4j_remediation(state["neo4j"])

    # 3. NEW: Missing dependencies
    if state["dependencies"]["status"] == "missing":
        await _trigger_dependency_remediation(state["dependencies"])

    # 4. NEW: Snapshot fallback active (degraded mode)
    if state["neo4j"]["mode"] == "local_snapshot":
        await _trigger_snapshot_health_check(state["neo4j"])


async def _trigger_neo4j_remediation(neo4j_state: dict) -> None:
    """Trigger Docker remediator to fix Neo4j."""
    synthetic_issue = {
        "id": f"neo4j-down-{int(time.time())}",
        "category": "LOCAL_NEO4J_START_FAIL",
        "error_type": "ConnectionRefusedError",
        "error_message": f"Neo4j unreachable at {neo4j_state['uri']}",
        "affected_module": "src/core/graphiti_client",
        "traceback": "",
    }

    # Spawn orchestrator in background
    subprocess.Popen([
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "graph" / "orchestrate_healers.py"),
        "--issue-json",
        json.dumps(synthetic_issue),
    ])

    _log_auto_heal_event("neo4j_down",
                         issue_id=synthetic_issue["id"],
                         detail=neo4j_state["uri"])


async def _trigger_dependency_remediation(deps_state: dict) -> None:
    """Verify and remediate missing dependencies."""
    for missing_dep in deps_state["missing"]:
        synthetic_issue = {
            "id": f"dep-missing-{missing_dep}-{int(time.time())}",
            "category": "CONFIG",
            "error_type": "ModuleNotFoundError",
            "error_message": f"Module '{missing_dep}' not found",
            "affected_module": "dependencies",
            "traceback": "",
        }

        subprocess.Popen([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "graph" / "orchestrate_healers.py"),
            "--issue-json",
            json.dumps(synthetic_issue),
        ])
```

### Phase 2: Create Dependency Remediator

**File**: `src/graph/remediators/dependency_remediator.py` (NEW)

```python
"""Dependency installation and verification remediator."""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from src.graph.universal_fixer import UniversalRemediator, RemediationResult

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class DependencyRemediator(UniversalRemediator):
    @property
    def service_name(self) -> str:
        return "dependencies"

    @property
    def description(self) -> str:
        return "Install and verify Python dependencies"

    async def validate_environment(self) -> bool:
        """Check if pip is available."""
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True
        )
        return result.returncode == 0

    async def diagnose_and_fix(self, params: dict | None = None) -> RemediationResult:
        """Install missing dependency and verify."""
        error_message = params.get("error_message", "") if params else ""

        # Extract module name from error
        import re
        match = re.search(r"Module '([^']+)' not found", error_message)
        if not match:
            return RemediationResult(
                False,
                "Could not extract module name from error",
                []
            )

        module_name = match.group(1)

        # Map module names to package names
        package_map = {
            "graphiti_core": "graphiti-core",
            "neo4j": "neo4j",
        }
        package_name = package_map.get(module_name, module_name)

        # Install
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return RemediationResult(
                False,
                f"Failed to install {package_name}",
                ["pip_install_failed"],
                error_details=result.stderr
            )

        # Verify import
        verify = subprocess.run(
            [sys.executable, "-c", f"import {module_name}"],
            capture_output=True,
            timeout=15
        )

        if verify.returncode != 0:
            return RemediationResult(
                False,
                f"Installed {package_name} but import still fails",
                ["pip_install_success", "import_verification_failed"]
            )

        return RemediationResult(
            True,
            f"Successfully installed and verified {package_name}",
            ["pip_install", "import_verification"]
        )
```

### Phase 3: Create Neo4j Health Remediator

**File**: `src/graph/remediators/neo4j_health_remediator.py` (NEW)

```python
"""Neo4j connection health and recovery remediator."""

from __future__ import annotations
import asyncio
from src.graph.universal_fixer import UniversalRemediator, RemediationResult

class Neo4jHealthRemediator(UniversalRemediator):
    @property
    def service_name(self) -> str:
        return "neo4j_health"

    @property
    def description(self) -> str:
        return "Diagnose and fix Neo4j connection issues"

    async def validate_environment(self) -> bool:
        """Check if neo4j module is available."""
        try:
            import neo4j
            return True
        except ImportError:
            return False

    async def diagnose_and_fix(self, params: dict | None = None) -> RemediationResult:
        """Attempt to restore Neo4j connection."""
        from src.core.graphiti_client import get_graphiti_client
        import os

        uri = os.getenv("NEO4J_URI")
        if not uri:
            return RemediationResult(
                False,
                "NEO4J_URI not configured",
                ["config_check"]
            )

        # Try to connect with retries
        for attempt in range(3):
            try:
                client = get_graphiti_client()
                # Simple health check
                from neo4j import GraphDatabase
                user = os.getenv("NEO4J_USER", "neo4j")
                password = os.getenv("NEO4J_PASSWORD", "")

                with GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5) as driver:
                    driver.verify_connectivity()

                return RemediationResult(
                    True,
                    f"Neo4j connection restored (attempt {attempt + 1}/3)",
                    [f"connection_retry_{attempt}"]
                )
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue

                return RemediationResult(
                    False,
                    f"Neo4j still unreachable after 3 attempts: {str(e)}",
                    [f"connection_retry_{i}" for i in range(3)],
                    error_details=str(e)
                )
```

### Phase 4: Enhance Service Routing

**File**: `src/graph/orchestrate_healers.py` (UPDATE)

Add routing for new issue types:

```python
CATEGORY_SERVICE_MAP = {
    "AURA_UNREACHABLE": "aura",
    "LOCAL_NEO4J_START_FAIL": "docker",
    "SNAPSHOT_CORRUPT": "local_snapshot",
    "SYNC_TIMEOUT": "graph_sync",
    # NEW:
    "NEO4J_CONNECTION_FAIL": "neo4j_health",
    "DEPENDENCY_MISSING": "dependencies",
}

def route_service_for_classification(category: str, normalized: dict[str, Any]) -> str | None:
    """Enhanced routing with health monitor issues."""
    message = f"{normalized.get('error_message', '')} {normalized.get('affected_module', '')}".lower()
    event_category = str(normalized.get("category") or "").strip().upper()

    # Direct category mapping (highest priority)
    if event_category in CATEGORY_SERVICE_MAP:
        return CATEGORY_SERVICE_MAP[event_category]

    # Infrastructure issues
    if category == FailureCategory.INFRASTRUCTURE:
        if "neo4j" in message and "unreachable" in message:
            return "neo4j_health"
        if "redis" in message:
            return "redis"
        if "aura" in message:
            return "aura"
        if "snapshot" in message:
            return "local_snapshot"
        if "sync" in message:
            return "graph_sync"
        return "docker"

    # Config issues
    if category == FailureCategory.CONFIG:
        if "module" in message and "not found" in message:
            return "dependencies"
        if "redis" in message:
            return "redis"
        if "graph" in message or "sync" in message:
            return "graph_sync"
        return "docker"

    # Code issues
    if category == FailureCategory.CODE:
        return "code_fix"

    return None
```

### Phase 5: Health Gate Integration (Optional)

**Enhancement**: Make health_gate.py more proactive

**File**: `scripts/governance/health_gate.py` (UPDATE)

```python
def main() -> int:
    """Main hook execution with proactive remediation triggers."""
    cache = _read_cache()

    if cache is None or _is_stale(cache, STALENESS_THRESHOLD_SECONDS):
        _log("WARN: Health cache stale - daemon may need restart")
        # Optional: Trigger daemon restart
        return 0

    # Current: Just log warnings
    # NEW: Could trigger lightweight fixes directly (optional)

    sentry = cache.get("sentry", {})
    if sentry.get("status") == "issues" and not sentry.get("auto_heal_running"):
        _log(f"INFO: {sentry['issue_count']} Sentry issues - triggering auto-heal")
        # Could spawn orchestrator here if daemon missed it

    return 0  # Never block
```

---

## Implementation Roadmap

### Task 1: Create New Remediators
- `src/graph/remediators/dependency_remediator.py`
- `src/graph/remediators/neo4j_health_remediator.py`
- Auto-discovered by registry on startup

### Task 2: Enhance health_monitor.py
- Add `handle_health_issues()` function
- Add `_trigger_neo4j_remediation()`
- Add `_trigger_dependency_remediation()`
- Call from `run_health_check()` after cache write

### Task 3: Update Orchestration Routing
- Extend `CATEGORY_SERVICE_MAP`
- Update `route_service_for_classification()`
- Test with synthetic issues

### Task 4: Testing
- Unit tests for new remediators
- Integration test: health_monitor → orchestrator → remediator
- E2E test: Simulate Neo4j down → auto-recovery

### Task 5: Verification Loop
- Add success verification back to health_monitor
- If remediation succeeds, next health check should show green
- If remediation fails after 3 attempts, escalate to HITL

---

## Expected Outcomes

### Before (Current)
```
health_monitor detects Neo4j down
    ↓
Writes cache: {neo4j: {status: "down", mode: "local_snapshot"}}
    ↓
Nothing happens - system stays in degraded mode
    ↓
User must manually restart Neo4j
```

### After (Complete Flow)
```
health_monitor detects Neo4j down
    ↓
Triggers neo4j_health remediation
    ↓
Remediator attempts connection with retries
    ↓
If successful: Next health check shows neo4j: "up"
If failed: Creates HITL approval queue item
    ↓
System self-heals without human intervention (90% of cases)
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ DETECTION LAYER (Phase 15 - Completed)                      │
│                                                              │
│ health_monitor.py (daemon, 2min interval)                   │
│  - check_sentry() → Sentry API                             │
│  - check_neo4j() → Connection probe                        │
│  - check_dependencies() → Import tests                     │
│  - write health-cache.json                                 │
│                                                              │
│ health_gate.py (PreToolUse hook, <5ms)                     │
│  - read health-cache.json                                  │
│  - log warnings                                            │
└──────────────────────────────────────────────────────────────┘
                         ↓ NEW: handle_health_issues()
┌──────────────────────────────────────────────────────────────┐
│ ORCHESTRATION LAYER (Phase 15 - Completed)                  │
│                                                              │
│ orchestrate_healers.py                                      │
│  - orchestrate_remediation(issue)                          │
│  - normalize_sentry_issue()                                │
│  - RootCauseClassifier.classify() (3-tier)                 │
│  - route_service_for_classification()                      │
│  - NanoFixerLoop.fix_service()                             │
│  - record_remediation_outcome()                            │
└──────────────────────────────────────────────────────────────┘
                         ↓ registry.get_tool(service)
┌──────────────────────────────────────────────────────────────┐
│ REMEDIATION LAYER (Phase 15 - Completed)                    │
│                                                              │
│ Existing Remediators (10):                                  │
│  ✅ aura_remediator - Resume Aura instances                 │
│  ✅ bash_agent - Execute safe Bash commands                 │
│  ✅ code_remediator - LLM-generated code patches            │
│  ✅ docker_remediator - Container restarts                  │
│  ✅ llm_remediator - Generic LLM fixes                      │
│  ✅ optimizer_remediator - Performance tuning               │
│  ✅ redis_remediator - Redis fixes                          │
│  ✅ snapshot_remediator - Local snapshot repair             │
│  ✅ sync_remediator - Graph sync fixes                      │
│  ✅ git_staleness_guard - Branch staleness warnings         │
│                                                              │
│ NEW Remediators Needed (2):                                 │
│  ❌ dependency_remediator - pip install + verify            │
│  ❌ neo4j_health_remediator - Connection recovery           │
└──────────────────────────────────────────────────────────────┘
                         ↓ RemediationResult
┌──────────────────────────────────────────────────────────────┐
│ VERIFICATION & LEARNING (Phase 15 - Completed)              │
│                                                              │
│  - Write to .graph/remediation-outcomes.jsonl               │
│  - Append to LEARNINGS.md                                   │
│  - Update health cache on next check cycle                  │
│  - HITL approval queue (if confidence < threshold)          │
└──────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

1. ✅ Health monitor detects Neo4j down → spawns remediation → next check shows "up"
2. ✅ Health monitor detects missing dep → spawns remediation → next check shows installed
3. ✅ All remediations logged to `.graph/remediation-outcomes.jsonl`
4. ✅ All remediations append learnings to `LEARNINGS.md`
5. ✅ Failed remediations (after retries) create HITL approval queue items
6. ✅ 90%+ of common issues auto-heal without human intervention
7. ✅ Complete audit trail from detection → remediation → outcome

---

## Files to Create/Modify

### Create:
1. `src/graph/remediators/dependency_remediator.py`
2. `src/graph/remediators/neo4j_health_remediator.py`
3. `tests/graph/test_dependency_remediator.py`
4. `tests/graph/test_neo4j_health_remediator.py`
5. `tests/integration/test_health_to_remediation_flow.py`

### Modify:
1. `scripts/daemons/health_monitor.py` - Add remediation triggers
2. `src/graph/orchestrate_healers.py` - Extend routing map
3. `docs/health-daemon-system.md` - Update with complete flow
4. `docs/pretooluse-hook-system.md` - Document auto-heal triggers

---

## Next Steps

**Ready to implement?** We can proceed in phases:

**Phase 1** (Low-hanging fruit):
- Create `dependency_remediator.py`
- Update `health_monitor.py` to trigger it
- Test with simulated missing dependency

**Phase 2** (Higher impact):
- Create `neo4j_health_remediator.py`
- Update `health_monitor.py` to trigger it
- Test with Neo4j connection failure

**Phase 3** (Polish):
- Update routing logic
- Add comprehensive tests
- Update documentation

Let me know which phase you want to start with!
