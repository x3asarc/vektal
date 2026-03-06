"""
Infrastructure Probes and Remediation (Phase 14.3).
Lightweight TCP/HTTP heartbeats to detect 'PAUSED' vs 'UNREACHABLE' states,
with integrated autonomous remediation via the Registry.
"""

import os
import asyncio
import logging
import socket
import httpx
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from src.graph.remediation_registry import registry
from src.graph.universal_fixer import NanoFixerLoop, RemediationResult

logger = logging.getLogger(__name__)

# Ensure probe commands resolve credentials from local .env in standalone runs.
load_dotenv()

async def probe_aura() -> bool:
    """
    Probes Neo4j Aura Cloud health using Query API v2 (HTTP).
    Researched to be faster than Bolt for 'PAUSED' detection.
    """
    hostname = os.getenv("NEO4J_AURA_HOSTNAME")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not all([hostname, user, password]):
        logger.warning("[Probe] Aura credentials missing. Skipping Aura probe.")
        return False

    url = f"https://{hostname}/db/neo4j/query/v2"
    auth = (user, password)
    payload = {"statement": "RETURN 1", "parameters": {}}
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            resp = await client.post(url, auth=auth, json=payload)
            # Aura Query API can return 200/202 depending on processing mode.
            if resp.is_success:
                logger.info("[Probe] Aura Cloud Query API v2 OK.")
                return True
            else:
                logger.warning("[Probe] Aura Cloud Query API v2 failed with status %s.", resp.status_code)
                return False
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("[Probe] Aura Cloud unreachable/timed out: %s", e)
            return False

async def probe_local_neo4j() -> bool:
    """
    Probes local Neo4j health using Bolt port (TCP).
    """
    host = os.getenv("NEO4J_LOCAL_HOST", "localhost")
    port = int(os.getenv("NEO4J_LOCAL_PORT", 7687))

    try:
        # Using a low-level TCP probe for speed
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=2.0
        )
        writer.close()
        await writer.wait_closed()
        logger.info("[Probe] Local Neo4j Bolt port OK.")
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, socket.error) as e:
        logger.warning("[Probe] Local Neo4j unreachable: %s", e)
        return False

async def active_remediation_loop(services: Optional[List[str]] = None):
    """
    The 'NullClaw' active loop: Probe all services and trigger registry remediation on failure.
    """
    services = services or ["aura", "docker", "redis", "graph_sync", "local_snapshot"]
    fixer = NanoFixerLoop(registry)
    
    logger.info("[InfraProbe] Starting active remediation loop for: %s", ", ".join(services))
    
    # Simple mapping of probe functions
    probes = {
        "aura": probe_aura,
        "docker": probe_local_neo4j, # In this context, docker remediator is for local neo4j
        "local_snapshot": lambda: os.path.exists(".graph/local-snapshot.json") # Simplified
    }

    for service in services:
        probe_func = probes.get(service)
        if probe_func:
            is_healthy = False
            if asyncio.iscoroutinefunction(probe_func):
                is_healthy = await probe_func()
            else:
                is_healthy = probe_func()
            
            if not is_healthy:
                logger.warning("[InfraProbe] Service '%s' failed probe. Triggering fix...", service)
                # registry.get_tool() is called inside NanoFixerLoop.fix_service
                result = await fixer.fix_service(service)
                if result.success:
                    logger.info("[InfraProbe] Remediation successful for %s: %s", service, result.message)
                else:
                    logger.error("[InfraProbe] Remediation failed for %s: %s", service, result.message)
            else:
                logger.info("[InfraProbe] Service '%s' is healthy.", service)
