"""
Backend Resolver for Graph Backends (Phase 14.3).
Handles the three-tier fallback: Aura -> Local Neo4j -> Snapshot.
"""

import os
import json
import logging
import asyncio
import time
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Ensure resolver/probes can read local .env when invoked from standalone CLIs.
load_dotenv()

class BACKEND_ENUM(str, Enum):
    AURA = "aura"
    LOCAL_NEO4J = "local_neo4j"
    SNAPSHOT = "local_snapshot"

@dataclass
class BackendStatus:
    backend: BACKEND_ENUM
    checked_at: str  # ISO string
    reason: str
    freshness_hours: float = 0.0
    is_degraded: bool = False
    probe_latency_ms: float = 0.0

# Module-level failure cache (60s TTL)
_failure_cache: Dict[str, float] = {}
FAILURE_CACHE_TTL = 60

MANIFEST_PATH = ".graph/runtime-backend.json"
SYNC_METADATA_PATH = ".graph/last-sync.json"

_MODE_TO_BACKEND = {
    "aura": BACKEND_ENUM.AURA,
    "neo4j": BACKEND_ENUM.LOCAL_NEO4J,
    "local_neo4j": BACKEND_ENUM.LOCAL_NEO4J,
    "local_snapshot": BACKEND_ENUM.SNAPSHOT,
    "snapshot": BACKEND_ENUM.SNAPSHOT,
}

_BACKEND_TO_MODE = {
    BACKEND_ENUM.AURA: "aura",
    BACKEND_ENUM.LOCAL_NEO4J: "neo4j",
    BACKEND_ENUM.SNAPSHOT: "local_snapshot",
}


def _normalize_backend(raw_backend: Any) -> Optional[BACKEND_ENUM]:
    token = str(raw_backend or "").strip().lower()
    if not token:
        return None

    mapped = _MODE_TO_BACKEND.get(token)
    if mapped:
        return mapped

    try:
        return BACKEND_ENUM(token)
    except Exception:
        return None


def runtime_backend_mode() -> str:
    """Return legacy-compatible runtime mode token based on manifest state."""
    status = read_runtime_manifest()
    if not status:
        return ""
    return _BACKEND_TO_MODE.get(status.backend, "")

def _is_failed_cached(key: str) -> bool:
    if key in _failure_cache:
        if time.time() - _failure_cache[key] < FAILURE_CACHE_TTL:
            return True
        else:
            del _failure_cache[key]
    return False

def _mark_failed(key: str):
    _failure_cache[key] = time.time()

async def probe_aura_http() -> Optional[float]:
    """Probes Aura via Query API v2. Returns latency in ms or None if failed."""
    if _is_failed_cached("aura"):
        return None
    
    from src.graph.infra_probe import probe_aura
    
    start = time.perf_counter()
    try:
        ok = await probe_aura()
        latency = (time.perf_counter() - start) * 1000
        if ok:
            return latency
    except Exception as e:
        logger.warning(f"Aura probe error: {e}")
    
    _mark_failed("aura")
    return None

async def probe_bolt() -> Optional[float]:
    """Probes local Neo4j via Bolt port. Returns latency in ms or None if failed."""
    if _is_failed_cached("local_neo4j"):
        return None
    
    from src.graph.infra_probe import probe_local_neo4j
    
    start = time.perf_counter()
    try:
        ok = await probe_local_neo4j()
        latency = (time.perf_counter() - start) * 1000
        if ok:
            return latency
    except Exception as e:
        logger.warning(f"Local Neo4j probe error: {e}")
    
    _mark_failed("local_neo4j")
    return None

async def attempt_docker_start() -> bool:
    """Attempts to start Neo4j container if local probe fails."""
    if _is_failed_cached("docker_start"):
        return False

    from src.graph.remediation_registry import registry
    tool = registry.get_tool("docker")
    if not tool:
        logger.warning("[Resolver] Docker remediator not found in registry.")
        return False

    logger.info("[Resolver] Local Neo4j down. Attempting Docker auto-start...")
    try:
        # 5s budget for start command
        result = await tool.diagnose_and_fix({"service": "neo4j"})
        if result.success:
            return True
        else:
            logger.error("[Resolver] Docker auto-start failed: %s", result.message)
            _mark_failed("docker_start")
            return False
    except Exception as e:
        logger.error("[Resolver] Docker auto-start crashed: %s", e)
        _mark_failed("docker_start")
        return False

def write_runtime_manifest(status: BackendStatus):
    """Writes status to .graph/runtime-backend.json."""
    os.makedirs(".graph", exist_ok=True)
    try:
        payload = asdict(status)
        payload["backend"] = status.backend.value
        # Compatibility schema consumed by older readers/scripts.
        payload["mode"] = _BACKEND_TO_MODE.get(status.backend, status.backend.value)
        payload["detail"] = status.reason
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write runtime manifest: {e}")

def read_runtime_manifest() -> Optional[BackendStatus]:
    """Reads status from .graph/runtime-backend.json."""
    if not os.path.exists(MANIFEST_PATH):
        return None
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            backend = _normalize_backend(data.get("backend"))
            if backend is None:
                legacy_mode = str(data.get("mode", "")).strip().lower()
                backend = _normalize_backend(legacy_mode)
                if backend is None:
                    logger.warning("Runtime manifest has unknown backend/mode: backend=%s mode=%s", data.get("backend"), legacy_mode)
                    return None
            data["backend"] = backend
            data["reason"] = data.get("reason") or data.get("detail") or "Runtime manifest loaded"
            data["checked_at"] = data.get("checked_at") or datetime.now().isoformat()
            data["is_degraded"] = bool(data.get("is_degraded", backend == BACKEND_ENUM.SNAPSHOT))
            data["freshness_hours"] = float(data.get("freshness_hours", 0.0) or 0.0)
            data["probe_latency_ms"] = float(data.get("probe_latency_ms", 0.0) or 0.0)

            # Ignore unknown keys from mixed manifest versions.
            return BackendStatus(
                backend=data["backend"],
                checked_at=data.get("checked_at", datetime.now().isoformat()),
                reason=data.get("reason", "Runtime manifest loaded"),
                freshness_hours=float(data.get("freshness_hours", 0.0) or 0.0),
                is_degraded=bool(data.get("is_degraded", False)),
                probe_latency_ms=float(data.get("probe_latency_ms", 0.0) or 0.0),
            )
    except Exception as e:
        logger.warning(f"Failed to read runtime manifest: {e}")
        return None

def _calculate_staleness() -> float:
    """Calculates staleness in hours based on last sync metadata."""
    if not os.path.exists(SYNC_METADATA_PATH):
        return 0.0
    try:
        with open(SYNC_METADATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            last_sync = datetime.fromisoformat(data["timestamp"])
            elapsed = (datetime.now() - last_sync).total_seconds()
            return elapsed / 3600.0
    except:
        return 0.0

async def resolve_backend(force: bool = False) -> BackendStatus:
    """
    Resolves active backend with fallback cascade:
    Aura (HTTP) -> Local Neo4j (Bolt) -> Docker Start -> Snapshot.
    """
    if not force:
        cached = read_runtime_manifest()
        if cached:
            try:
                checked_at = datetime.fromisoformat(cached.checked_at)
                if (datetime.now() - checked_at).total_seconds() < 60:
                    return cached
            except Exception:
                pass

    logger.info("[Resolver] Resolving active backend cascade...")
    
    # 1. Aura Probe (HTTP)
    aura_latency = await probe_aura_http()
    if aura_latency is not None:
        status = BackendStatus(
            backend=BACKEND_ENUM.AURA,
            checked_at=datetime.now().isoformat(),
            reason="Aura Cloud available via Query API v2",
            probe_latency_ms=aura_latency
        )
        write_runtime_manifest(status)
        return status

    # 2. Local Neo4j Probe (Bolt)
    local_latency = await probe_bolt()
    if local_latency is not None:
        status = BackendStatus(
            backend=BACKEND_ENUM.LOCAL_NEO4J,
            checked_at=datetime.now().isoformat(),
            reason="Aura down; Local Neo4j available via Bolt",
            probe_latency_ms=local_latency
        )
        write_runtime_manifest(status)
        return status

    # 3. Docker Auto-Start (if local probe fails)
    if await attempt_docker_start():
        # Re-probe after start attempt
        await asyncio.sleep(2.0) # Give container a moment
        # We need to bypass the failure cache for this specific probe after start
        if "local_neo4j" in _failure_cache:
            del _failure_cache["local_neo4j"]
            
        local_latency = await probe_bolt()
        if local_latency is not None:
            status = BackendStatus(
                backend=BACKEND_ENUM.LOCAL_NEO4J,
                checked_at=datetime.now().isoformat(),
                reason="Aura down; Local Neo4j started via Docker",
                probe_latency_ms=local_latency
            )
            write_runtime_manifest(status)
            return status

    # 4. Snapshot Fallback
    snapshot_exists = os.path.exists("data/codebase_graph.json")
    reason = "Aura and Local Neo4j unreachable; "
    if snapshot_exists:
        reason += "Falling back to local snapshot (Read-Only)"
    else:
        reason += "CRITICAL: No local snapshot found"
    
    status = BackendStatus(
        backend=BACKEND_ENUM.SNAPSHOT,
        checked_at=datetime.now().isoformat(),
        reason=reason,
        is_degraded=True,
        freshness_hours=_calculate_staleness()
    )
    write_runtime_manifest(status)
    return status
