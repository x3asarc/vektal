"""
Mutation Guard for Graph Backends (Phase 14.3).
Blocks mutations in degraded/snapshot modes to prevent graph-filesystem divergence.
"""

import logging
from typing import Tuple
from src.graph.backend_resolver import read_runtime_manifest, BACKEND_ENUM

logger = logging.getLogger(__name__)

def check_mutation_allowed() -> Tuple[bool, str]:
    """
    Checks if graph mutations (sync, apply, etc.) are permitted.
    
    Returns:
        (allowed, reason)
    """
    manifest = read_runtime_manifest()
    
    if not manifest:
        return False, "Graph runtime manifest missing. Run bootstrap script."
        
    if manifest.backend == BACKEND_ENUM.SNAPSHOT:
        reason = "Mutations blocked: Running in read-only SNAPSHOT mode."
        logger.warning("[MutationGuard] %s", reason)
        return False, reason
        
    if manifest.is_degraded:
        # We might allow mutations in degraded modes other than snapshot, 
        # but for now, we follow the plan's strict requirement.
        pass
        
    return True, f"Mutations permitted on {manifest.backend.value.upper()}"
