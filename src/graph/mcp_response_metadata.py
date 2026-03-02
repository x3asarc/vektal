"""
MCP Response Metadata Enrichment (Phase 14.3).
Adds backend source and freshness indicators to all tool outputs.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.graph.backend_resolver import read_runtime_manifest

logger = logging.getLogger(__name__)

def enrich_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriches a tool response with graph backend metadata and freshness.
    """
    manifest = read_runtime_manifest()
    
    metadata = {
        "backend_source": "unknown",
        "last_sync_timestamp": None,
        "staleness_hours": 0.0,
        "is_stale": False,
        "is_degraded": True
    }
    
    if manifest:
        metadata["backend_source"] = manifest.backend.value
        metadata["last_sync_timestamp"] = manifest.checked_at
        metadata["staleness_hours"] = manifest.freshness_hours
        metadata["is_stale"] = manifest.freshness_hours > 24.0
        metadata["is_degraded"] = manifest.is_degraded
    
    # Add to response under _metadata key
    response["_metadata"] = metadata
    return response
