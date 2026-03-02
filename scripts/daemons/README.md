# Daemons

Background services for continuous system monitoring.

## Health Monitor Daemon

Replaces blocking PreToolUse hooks with lightweight cache-based monitoring.

**Start daemon** (auto-starts on session):
```bash
# Unix
bash scripts/daemons/start_health_monitor.sh

# Windows
python scripts/daemons/health_monitor.py --daemon
```

**Stop daemon**:
```bash
bash scripts/daemons/stop_health_monitor.sh
```

**Check status**:
```bash
bash scripts/daemons/status_health_monitor.sh
```

**What it monitors**:
- Sentry issues (every 2 minutes)
- Neo4j connectivity
- Python dependencies (neo4j, graphiti-core)

**What it does**:
- Writes health cache to `.graph/health-cache.json`
- Triggers auto-heal when Sentry issues detected
- Falls back to local snapshot if Neo4j unreachable
- Auto-installs missing dependencies

**Performance**: ~1.5ms hook execution (vs 2-5s blocking)

See: `docs/health-daemon-system.md` for full documentation.
