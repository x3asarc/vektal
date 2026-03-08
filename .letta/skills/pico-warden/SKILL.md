---
---
# Pico-Warden: Bootstrap Recovery Loop

**Agent ID:** `agent-24c66e02-7099-4027-9d66-24e319a17251`
**Model:** `anthropic/claude-haiku-4-5`
**Analyst (to escalate to):** `agent-745c61ec-da1a-4e13-b142-ff28a1fe7b09`

---

## OODA Loop — Every Heartbeat is a Clean Slate

### OBSERVE
```python
# Step 1: Read manifest (fast, no network)
manifest = read(".graph/runtime-backend.json")
# freshness check: if checked_at > 60s ago → re-probe

# Step 2: Probe Bolt port (DO NOT trust Docker health status)
import socket
s = socket.socket()
s.settimeout(3)
result = s.connect_ex(('localhost', 7687))  # 0 = open, nonzero = closed
s.close()
# NOTE: Docker reports 'unhealthy' because curl is missing from image
# If port 7687 responds → Neo4j IS running regardless of Docker status
```

### ORIENT — Failure Classification
| Symptom | Classification |
|---|---|
| Port 7687 open, Aura HTTP 200 | HEALTHY — no action |
| Port 7687 open, Aura HTTP fails | AURA_DOWN — credential check |
| Port 7687 closed, container running | NEO4J_PROCESS_CRASH — restart |
| Port 7687 closed, container stopped | DOCKER_DOWN — start container |
| All probes fail | SYSTEMIC — escalate after 3 attempts |

### DECIDE / ACT

#### Level 1: Aura Cloud Recovery
```bash
# Check credentials
grep -E "^AURA_" .env

# Probe Aura HTTP
python -c "
from src.graph.infra_probe import probe_aura
import asyncio
print(asyncio.run(probe_aura()))
"

# If credentials rotated: patch_env_credential
# ONLY keys: NEO4J_*, AURA_*, GRAPHITI_*
# ALWAYS backup first:
cp .env .env.bak
```

#### Level 2: Local Neo4j Recovery
```bash
# Check container state
docker ps --filter name=shopifyscrapingscript-neo4j-1 --format "{{.Status}}"

# Restart if stopped/unhealthy
docker restart shopifyscrapingscript-neo4j-1

# Wait and re-probe
python -c "import time; time.sleep(10)"
# Then re-probe port 7687
```

#### Level 3: Snapshot Regeneration
```bash
# Only if L1 + L2 both fail
# Does NOT require Neo4j to be running
cd "C:\Users\Hp\Documents\Shopify Scraping Script"
python scripts/graph/sync_codebase.py --no-embeddings
# Creates: data/codebase_graph.json
```

---

## Handshake Protocol (MANDATORY after every action)

### Write runtime-backend.json
```python
import json
from datetime import datetime

manifest = {
    "backend": "aura",          # or local_neo4j, snapshot
    "is_degraded": False,
    "last_healed_at": datetime.now().isoformat(),
    "checked_at": datetime.now().isoformat(),
    "reason": "Recovered via Level 1: Aura probe success",
    "probe_latency_ms": 0.0
}

with open(".graph/runtime-backend.json", "w") as f:
    json.dump(manifest, f, indent=2)
```

### Append to memory events
```python
import json
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
event = {
    "type": "warden_recovery",
    "backend_restored": "aura",
    "level_used": 1,
    "timestamp": datetime.now().isoformat(),
    "source": "pico-warden"
}

with open(f".memory/events/{today}.jsonl", "a") as f:
    f.write(json.dumps(event) + "\n")
```

---

## Halt State — Escalation to Analyst

```python
# Trigger: 3 consecutive failed repair attempts
# Action: send_message to agent-745c61ec-da1a-4e13-b142-ff28a1fe7b09

message = {
    "tag": "SYSTEMIC_FAILURE",
    "from": "pico-warden",
    "agent_id": "agent-24c66e02-7099-4027-9d66-24e319a17251",
    "attempts": 3,
    "last_error": "<describe failure>",
    "backends_tried": ["aura", "local_neo4j", "snapshot"],
    "timestamp": datetime.now().isoformat(),
    "action_required": "Manual investigation required. All automated recovery paths exhausted."
}
```

---

## Guardrails Checklist
- [ ] Only modifying .env keys starting with `NEO4J_`, `AURA_`, `GRAPHITI_`?
- [ ] Created `.env.bak` before any .env edit?
- [ ] NOT touching anything in `/src/`?
- [ ] NOT restarting any container other than `shopifyscrapingscript-neo4j-1`?
- [ ] Attempt counter < 3?
- [ ] Wrote handshake to `.graph/runtime-backend.json`?
- [ ] Appended event to `.memory/events/{date}.jsonl`?
