"""
Shared bootstrap command for all agents to resolve and cache graph backend status.
Phase 14.3.
"""

import asyncio
import logging
import sys
import os

# Add project root to sys.path to ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.graph.backend_resolver import resolve_backend, BACKEND_ENUM

async def bootstrap_graph():
    """
    Bootstraps the graph backend by resolving the active connection cascade.
    Always exits 0 to ensure fail-open semantics for caller agents.
    """
    # Quiet logging for bootstrap unless DEBUG is set
    log_level = logging.INFO if os.getenv("DEBUG") else logging.WARNING
    logging.basicConfig(level=log_level, format="%(message)s")
    
    try:
        status = await resolve_backend(force=True)
        
        status_tag = "[OK]" if not status.is_degraded else "[WARN]"
        print(f"{status_tag} [GraphBootstrap] Active Backend: {status.backend.value.upper()}")
        print(f"    Reason: {status.reason}")
        
        if status.probe_latency_ms > 0:
            print(f"    Latency: {status.probe_latency_ms:.2f}ms")
            
        if status.is_degraded:
            if status.freshness_hours > 0:
                print(f"    Staleness: {status.freshness_hours:.2f}h")
            else:
                print("    WARNING: Running in degraded mode with no staleness data.")
                
    except Exception as e:
        print(f"[ERROR] [GraphBootstrap] CRITICAL: Unexpected error during resolution: {e}")
        # We still exit 0 because agents should proceed with degraded/no graph rather than crashing
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(bootstrap_graph())
    sys.exit(exit_code)
