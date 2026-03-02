# PreToolUse Hook System (Phase 15)

## What the PreToolUse Hook Does Now

The PreToolUse hook runs **before every Bash command** across all AI providers (Claude, Gemini, Codex). It performs a lightning-fast health check by reading a cached state file.

### Old System (Blocking)
- **Execution time**: 2-5 seconds
- **Behavior**: Blocked every Bash command while checking:
  - Neo4j connectivity (2s timeout)
  - Python dependency imports (5s timeout each)
  - Auto-installation of missing packages
- **Problem**: Interrupted conversation flow, made CLI feel sluggish

### New System (Non-Blocking)
- **Execution time**: 0.3-1.5ms (99.97% faster)
- **Behavior**: Reads health cache file, never blocks:
  - Instant check of cached health state
  - Logs warnings if issues detected
  - Always exits 0 (success) - never interrupts conversation
  - Falls back gracefully if cache missing/stale

## Architecture

```
┌─────────────────────────────────────┐
│ Background Daemon                   │
│ (runs continuously every 2 minutes) │
│                                     │
│ - Checks Sentry for issues          │
│ - Probes Neo4j connectivity         │
│ - Verifies Python dependencies      │
│ - Triggers auto-heal if needed      │
│ - Writes atomic cache file          │
└─────────────────────────────────────┘
          ↓ writes (every 2 min)
┌─────────────────────────────────────┐
│ .graph/health-cache.json            │
│ {                                   │
│   "sentry": {"status": "healthy"},  │
│   "neo4j": {"status": "up"},        │
│   "dependencies": {"status": "ok"}  │
│ }                                   │
└─────────────────────────────────────┘
          ↑ reads (0.3-1.5ms)
┌─────────────────────────────────────┐
│ PreToolUse Hook                     │
│ (runs before every Bash command)    │
│                                     │
│ - Reads cache file instantly        │
│ - Logs warnings if issues exist     │
│ - NEVER blocks (always exits 0)     │
└─────────────────────────────────────┘
```

## What It Checks

### 1. Sentry Issues (if configured)
- Polls Sentry API for unresolved errors
- If issues found: Spawns auto-heal orchestrator in background
- If not configured: Silently skips (status: "not_configured")
- If API fails: Logs warning, continues (status: "unreachable")

### 2. Neo4j Connectivity
- Probes Neo4j with 2s timeout
- If reachable: Status "up", mode "neo4j"
- If unreachable: Triggers local snapshot fallback, mode "local_snapshot"

### 3. Python Dependencies
- Checks if `neo4j` and `graphiti-core` importable
- If missing: Spawns background `pip install`
- If timeout: Logs warning, continues

## Configuration Per AI Provider

### Claude Code
**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/start-health-daemon.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "filter": {"tool": "Bash"},
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/governance/health_gate.py",
            "blockOnFailure": false
          }
        ]
      }
    ]
  }
}
```

**What happens:**
1. SessionStart: Auto-starts health daemon if not running
2. PreToolUse: Reads health cache on every Bash command (never blocks)

### Gemini Code
**Files**: `.gemini/settings.json` + `.gemini/preToolUseHook.sh`

**settings.json**:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .gemini/hooks/start-health-daemon.py"
          }
        ]
      }
    ]
  }
}
```

**preToolUseHook.sh**:
```bash
# Phase 15 health gate: fast cache-based checks (1-2ms vs 2-5s blocking)
python scripts/governance/health_gate.py || true
python scripts/hooks/antigravity_notify.py --provider gemini ...
```

**What happens:**
1. SessionStart: Auto-starts health daemon
2. PreToolUse: Runs health_gate.py before other hooks

### Codex
**Files**: `.codex/settings.json` + `.codex/preToolUseHook.sh`

**settings.json**:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .codex/hooks/start-health-daemon.py"
          }
        ]
      }
    ]
  }
}
```

**preToolUseHook.sh**:
```bash
# Phase 15 health gate: fast cache-based checks (1-2ms vs 2-5s blocking)
python scripts/governance/health_gate.py || true
python scripts/hooks/antigravity_notify.py --provider codex ...
```

**What happens:**
1. SessionStart: Auto-starts health daemon
2. PreToolUse: Runs health_gate.py before other hooks

## Performance Comparison

| Metric | Old System | New System | Improvement |
|--------|-----------|-----------|-------------|
| Avg execution | 2-5 seconds | 1.5ms | 99.97% |
| Min execution | 2 seconds | 0.3ms | 99.98% |
| Max execution | 5+ seconds | 20ms | 99.6% |
| Blocks conversation? | Yes | No | ∞ |
| User perception | Sluggish | Instant | Excellent |

## What Gets Logged

### Health Gate Log (`.graph/health-gate.log`)
```
[2026-03-02T22:40:17+00:00] INFO: Health gate check complete in 0.30ms
[2026-03-02T22:40:18+00:00] WARN: Health cache is stale (>5min) - daemon may have stopped
[2026-03-02T22:40:19+00:00] INFO: 3 Sentry issue(s) detected - auto-heal daemon will handle in background
[2026-03-02T22:40:20+00:00] WARN: Neo4j unreachable - using local snapshot fallback
```

### Daemon Log (`.graph/health-monitor.log`)
```
2026-03-02 23:29:27 [INFO] [HealthMonitor] Running health check cycle...
2026-03-02 23:29:29 [INFO] [HealthMonitor] Neo4j reachable at neo4j+s://...
2026-03-02 23:29:35 [INFO] [HealthMonitor] Health check complete: Sentry=not_configured, Neo4j=up, Deps=ok
```

### Auto-Heal Log (`.graph/auto-heal-log.jsonl`)
```json
{"timestamp": "2026-03-02T23:30:00Z", "event": "triggered", "issue_id": "123", "title": "Neo4j connection timeout"}
{"timestamp": "2026-03-02T23:31:00Z", "event": "completed", "issue_id": "123", "result": "fixed"}
```

## Sentry Configuration (Optional)

If you want Sentry monitoring, add to `.env`:

```bash
# Required for Sentry API access
SENTRY_AUTH_TOKEN=your_auth_token_here
SENTRY_ORG_SLUG=your-org-slug
SENTRY_PROJECT_SLUG=your-project-slug
```

**Without Sentry configured:**
- Status shows "not_configured"
- No errors, continues silently
- System still monitors Neo4j and dependencies

**With Sentry configured:**
- Daemon polls for issues every 2 minutes
- Auto-heal spawns when issues detected
- Issues tracked in auto-heal log

## Daemon Management

### Start daemon manually
```bash
# Unix
bash scripts/daemons/start_health_monitor.sh

# Windows
python scripts/daemons/health_monitor.py --daemon
```

### Stop daemon
```bash
# Unix
bash scripts/daemons/stop_health_monitor.sh

# Windows (find PID and kill)
type .graph\health-monitor.pid
taskkill /PID <pid>
```

### Check status
```bash
bash scripts/daemons/status_health_monitor.sh
```

### View cache
```bash
cat .graph/health-cache.json
```

**Daemon auto-starts** on SessionStart for all AI providers. No manual intervention needed.

## Troubleshooting

### Hook feels slow
1. Run benchmark: `python tests/daemons/benchmark_health_gate.py`
2. Expected: <5ms average
3. If slower: Check disk I/O, cache file size

### Warnings in logs
**"Health cache missing"**
- Normal on first session start
- Daemon creates cache within 5 seconds

**"Health cache is stale"**
- Daemon may have crashed/stopped
- Check: `bash scripts/daemons/status_health_monitor.sh`
- Restart: `bash scripts/daemons/start_health_monitor.sh`

**"Neo4j unreachable"**
- System falls back to local snapshot
- No action needed, continues working

**"Sentry not configured"**
- Sentry env vars not set
- Optional - add to `.env` if desired

### Daemon won't start
1. Check logs: `cat .graph/health-monitor.log`
2. Remove stale PID: `rm .graph/health-monitor.pid`
3. Start manually: `python scripts/daemons/health_monitor.py --daemon`

## Migration from Old System

**Old files** (deprecated, can be removed):
- `scripts/governance/ensure_neo4j_runtime.py` - Old blocking hook
- `scripts/graph/pretool_gate.py` - Old Gemini/Codex gate

**New files** (active):
- `scripts/governance/health_gate.py` - Fast non-blocking hook
- `scripts/daemons/health_monitor.py` - Background daemon

**Breaking changes**: None - system is backward compatible

## Benefits

1. **99.97% faster**: 2-5s → 1.5ms average
2. **Never blocks**: Always returns success, logs warnings only
3. **Proactive monitoring**: Daemon catches issues before they impact you
4. **Auto-healing**: Issues trigger fixes in background
5. **Graceful degradation**: Works even if daemon stops
6. **Multi-provider**: Works identically across Claude, Gemini, Codex
7. **Low resource**: Daemon uses <50MB RAM, checks every 2 minutes

## See Also

- Full architecture: `docs/health-daemon-system.md`
- Quick start: `scripts/daemons/README.md`
- Implementation: `.planning/phases/15-self-healing-dynamic-scripting/health-daemon-implementation-summary.md`
- Tests: `tests/daemons/test_health_monitor.py`
- Benchmark: `tests/daemons/benchmark_health_gate.py`
