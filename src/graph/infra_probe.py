"""
Infrastructure probing and active remediation for Phase 14.3.
Provides lightweight heartbeats and triggers autonomous fixes.
"""

import socket
import logging
import os
import time
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from src.graph.universal_fixer import NanoFixerLoop, RemediationResult
from src.graph.remediation_registry import registry

logger = logging.getLogger(__name__)

# Auto-discover tools from the heap
registry.auto_discover()
fixer_loop = NanoFixerLoop(registry)

class InfraStatus:
    def __init__(self, service: str, reachable: bool, latency_ms: float = 0.0, error: Optional[str] = None):
        self.service = service
        self.reachable = reachable
        self.latency_ms = latency_ms
        self.error = error

def probe_tcp(host: str, port: int, timeout: float = 1.0) -> InfraStatus:
    """Lightweight TCP port probe."""
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.time() - start) * 1000
            return InfraStatus(f"{host}:{port}", True, latency)
    except Exception as e:
        return InfraStatus(f"{host}:{port}", False, error=str(e))

def probe_neo4j_lightweight() -> InfraStatus:
    """Probe Neo4j (Aura or Local) without driver overhead."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    parsed = urlparse(uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 7687
    return probe_tcp(host, port)

def probe_redis_lightweight() -> InfraStatus:
    """Probe Redis without celery/kombu overhead."""
    uri = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    parsed = urlparse(uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    return probe_tcp(host, port)

async def active_remediation_loop(service: str, params: Optional[Dict[str, Any]] = None) -> bool:
    """
    Unified entry point for NullClaw-style remediation.
    Pilot of Phase 15 Self-Healing loop.
    """
    result = await fixer_loop.fix_service(service, params)
    
    if result.success:
        logger.info(f"✅ Remediation for {service} succeeded: {result.message}")
        return True
    
    # Recursive logic: If a service fails, check if its common dependency (Docker) needs fixing
    if service in ["redis", "neo4j"] and not result.success:
        logger.warning(f"⚠️ {service} fix failed. Attempting recursive fix for Docker...")
        docker_result = await fixer_loop.fix_service("docker", {"service": service})
        if docker_result.success:
            # Re-attempt original service fix after dependency is resolved
            final_result = await fixer_loop.fix_service(service, params)
            return final_result.success
            
    return result.success
