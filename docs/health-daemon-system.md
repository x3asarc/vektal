# Health Daemon System (Phase 15)

## Overview

The Health Daemon System replaces blocking PreToolUse hooks with a lightweight daemon + cache architecture:

- **Background Daemon** (`scripts/daemons/health_monitor.py`) - Continuously monitors Sentry, Neo4j, and dependencies
- **Health Cache** (`.graph/health-cache.json`) - Atomic cache written every 2 minutes
- **Lightweight Hook** (`scripts/governance/health_gate.py`) - Fast (<5ms) cache read, never blocks

**Performance improvement**: 2-5 seconds → ~1.5ms average (99.9% reduction)

## Architecture

```
┌──────────────────────────────────────────────┐
│ Background Daemon (continuous)               │
│ scripts/daemons/health_monitor.py            │
│                                              │
│ Every 2 minutes:                             │
│  1. Check Sentry issues (API call)          │
│  2. Probe Neo4j health (connection test)    │
│  3. Verify critical dependencies            │
│  4. Write .graph/health-cache.json          │
│                                              │
│ On detection:                                │
│  - Sentry issues → trigger auto-heal        │
│  - Neo4j down → attempt restart/fallback    │
│  - Missing deps → auto-install              │
└──────────────────────────────────────────────┘
                    ↓ writes
┌──────────────────────────────────────────────┐
│ Health Cache (.graph/health-cache.json)      │
│ {                                            │
│   "sentry": {"issues": 2, "last_check": ts}, │
│   "neo4j": {"status": "up", "uri": "..."},  │
│   "deps": {"missing": []},                   │
│   "updated_at": "2026-03-02T..."             │
│ }                                            │
└──────────────────────────────────────────────┘
                    ↑ reads (1ms)
┌──────────────────────────────────────────────┐
│ PreToolUse Hook (instant)                    │
│ scripts/governance/health_gate.py            │
│                                              │
│ 1. Read health-cache.json                   │
│ 2. If cache stale (>5min) → warn, continue  │
│ 3. If critical issues → log warning         │
│ 4. Exit 0 (never blocks)                    │
└──────────────────────────────────────────────┘
```

## Components

### 1. Health Monitor Daemon

**File**: `scripts/daemons/health_monitor.py`

**Features**:
- Continuous monitoring loop (default: 120s interval)
- Checks Sentry API for unresolved issues (limit 5)
- Probes Neo4j connectivity with 2s timeout
- Verifies Python dependencies (`neo4j`, `graphiti-core`)
- Atomic cache writes (write to `.tmp`, rename for atomicity)
- Graceful shutdown on SIGINT/SIGTERM
- PID file tracking at `.graph/health-monitor.pid`
- Self-health reporting at `.graph/health-monitor-health.json`

**Auto-heal integration**:
- Spawns `orchestrate_healers.py` when Sentry issues detected
- Tracks `auto_heal_running` flag to prevent duplicates
- Logs events to `.graph/auto-heal-log.jsonl`

**Cache schema**:
```json
{
  "sentry": {
    "status": "healthy|issues|unreachable",
    "issue_count": 0,
    "last_check": "2026-03-02T12:34:56Z",
    "auto_heal_running": false
  },
  "neo4j": {
    "status": "up|down|fallback",
    "uri": "neo4j+s://...",
    "last_check": "2026-03-02T12:34:56Z",
    "mode": "neo4j|local_snapshot"
  },
  "dependencies": {
    "status": "ok|missing|installing",
    "missing": [],
    "last_check": "2026-03-02T12:34:56Z"
  },
  "daemon": {
    "pid": 12345,
    "started_at": "2026-03-02T12:30:00Z",
    "updated_at": "2026-03-02T12:34:56Z",
    "check_interval_seconds": 120
  }
}
```

### 2. Lightweight Health Gate Hook

**File**: `scripts/governance/health_gate.py`

**Features**:
- Fast cache read (<5ms target, ~1.5ms average)
- Staleness detection (warns if cache >5min old)
- Never blocks (always exits 0)
- Logs warnings to `.graph/health-gate.log`
- Graceful fallback on missing/corrupt cache

**Logic**:
1. Read `health-cache.json`
2. If cache missing/corrupt → warn, continue
3. If cache stale (>5min) → warn, continue
4. Log detected issues (informational only)
5. Always return 0 (success)

### 3. Daemon Lifecycle Scripts

**Start**: `scripts/daemons/start_health_monitor.sh`
- Checks if already running via PID file
- Starts daemon in background with `nohup`
- Waits for PID file creation (max 5s)
- Works on Unix systems

**Stop**: `scripts/daemons/stop_health_monitor.sh`
- Reads PID from file
- Sends SIGTERM for graceful shutdown
- Waits up to 10s for cleanup
- Force kill if necessary

**Status**: `scripts/daemons/status_health_monitor.sh`
- Checks if daemon running
- Displays cache age and status
- Shows last check times for each system

### 4. SessionStart Auto-Start

**File**: `.claude/hooks/start-health-daemon.py`

**Features**:
- Checks if daemon already running
- Starts daemon if needed (Windows-compatible)
- Waits for first cache write (max 5s)
- Never blocks session start

## Configuration

### Hook Configuration

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

### Environment Variables

- `HEALTH_CHECK_INTERVAL_SECONDS` - Daemon check interval (default: 120)
- `SENTRY_AUTH_TOKEN` - Sentry API authentication
- `SENTRY_ORG_SLUG` - Sentry organization (default: shopify-scraping-script)
- `SENTRY_PROJECT_SLUG` - Sentry project (default: shopify-scraping-script)
- `NEO4J_URI` - Neo4j connection URI
- `NEO4J_USER` - Neo4j username (default: neo4j)
- `NEO4J_PASSWORD` - Neo4j password

## Usage

### Manual Daemon Control

**Start daemon**:
```bash
# Unix
bash scripts/daemons/start_health_monitor.sh

# Windows
python scripts/daemons/health_monitor.py --daemon
```

**Stop daemon**:
```bash
# Unix
bash scripts/daemons/stop_health_monitor.sh

# Windows (find PID and kill)
type .graph\health-monitor.pid
taskkill /PID <pid> /F
```

**Check status**:
```bash
bash scripts/daemons/status_health_monitor.sh
```

**View cache**:
```bash
cat .graph/health-cache.json
```

**View logs**:
```bash
tail -f .graph/health-monitor.log
tail -f .graph/health-gate.log
tail -f .graph/auto-heal-log.jsonl
```

### One-Time Health Check

Run health check once without daemon:
```bash
python scripts/daemons/health_monitor.py
```

### Test Hook Performance

```bash
python tests/daemons/benchmark_health_gate.py
```

## Performance Metrics

**Benchmark results** (100 iterations):
- **Min**: 1.2ms
- **Average**: 1.5ms (99.9% faster than old 2-5s blocking hook)
- **Median**: 1.3ms
- **95th percentile**: 1.8ms
- **99th percentile**: 10.2ms
- **Max**: 20.1ms

**Cache file size**: ~0.5KB (well below 5KB target)

## Testing

**Unit tests**:
```bash
python -m pytest tests/daemons/test_health_monitor.py -v
```

**Performance benchmark**:
```bash
python tests/daemons/benchmark_health_gate.py
```

**Test coverage**:
- Atomic cache writes
- Sentry API mocking (0 issues, 5 issues, API down)
- Neo4j connection tests with timeout
- Dependency checks
- Auto-heal spawn logic
- PID file management
- Graceful shutdown
- Cache staleness detection
- Concurrent cache reads
- Hook execution time (<5ms)

## State Files

All state files are in `.graph/` directory:

- `health-cache.json` - Main health cache (read by hook)
- `health-monitor.pid` - Daemon process ID
- `health-monitor.log` - Daemon logs
- `health-monitor-health.json` - Daemon self-health
- `health-gate.log` - Hook execution logs
- `auto-heal-log.jsonl` - Auto-heal event log

## Troubleshooting

### Daemon won't start
1. Check if already running: `cat .graph/health-monitor.pid`
2. Check logs: `cat .graph/health-monitor.log`
3. Remove stale PID: `rm .graph/health-monitor.pid`
4. Start manually: `python scripts/daemons/health_monitor.py --daemon`

### Cache is stale
1. Check if daemon running: `bash scripts/daemons/status_health_monitor.sh`
2. Restart daemon: `bash scripts/daemons/stop_health_monitor.sh && bash scripts/daemons/start_health_monitor.sh`

### Hook is slow
1. Run benchmark: `python tests/daemons/benchmark_health_gate.py`
2. Check cache file size: `ls -lh .graph/health-cache.json`
3. Check for disk I/O issues

### Auto-heal not triggering
1. Check Sentry configuration in `.env`
2. View auto-heal log: `cat .graph/auto-heal-log.jsonl`
3. Check cache: `cat .graph/health-cache.json | grep auto_heal_running`

## Migration from Old System

**Old system** (`ensure_neo4j_runtime.py`):
- Blocking PreToolUse hook
- 2-5 second execution time
- Synchronous dependency checks
- No background monitoring

**New system**:
- Non-blocking PreToolUse hook
- ~1.5ms execution time
- Continuous background monitoring
- Proactive auto-heal

**Breaking changes**:
- None - system is backward compatible
- Old hook replaced in `.claude/settings.json`
- Daemon auto-starts on SessionStart

## Future Enhancements

1. **Machine learning**: Learn patterns (e.g., "Sentry always spikes at 3pm")
2. **Predictive monitoring**: Detect trends before failures
3. **Remediation templates**: Cache successful fixes for instant replay
4. **Multi-project support**: Multiple Sentry projects in one daemon
5. **Alerting**: Slack/Discord integration for critical issues
6. **Metrics dashboard**: Web UI for health visualization

## References

- Plan: `.planning/phases/15-self-healing-dynamic-scripting/health-daemon-plan.md`
- Tests: `tests/daemons/test_health_monitor.py`
- Benchmark: `tests/daemons/benchmark_health_gate.py`
- Old hook: `scripts/governance/ensure_neo4j_runtime.py` (deprecated)
