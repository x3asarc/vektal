"""
Sync Status Tracking for Codebase Knowledge Graph (Phase 14.3).
Tracks last sync time, mode, and source for reliability monitoring.
"""

import os
import json
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

STATUS_PATH = ".graph/sync-status.json"

@dataclass
class SyncStatus:
    last_sync_at: str  # ISO string
    sync_mode: str     # "auto" or "manual"
    last_source: str   # "git_hook", "cli", "daemon"
    success: bool = True
    error: Optional[str] = None
    files_processed: int = 0
    entities_updated: int = 0

def get_sync_status() -> Optional[SyncStatus]:
    """Reads sync status from .graph/sync-status.json."""
    if not os.path.exists(STATUS_PATH):
        return None
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return SyncStatus(**data)
    except Exception as e:
        logger.error(f"Failed to read sync status: {e}")
        return None

def update_sync_status(
    sync_mode: str, 
    last_source: str, 
    success: bool = True, 
    error: Optional[str] = None,
    files_processed: int = 0,
    entities_updated: int = 0
):
    """Updates sync status in .graph/sync-status.json."""
    os.makedirs(".graph", exist_ok=True)
    status = SyncStatus(
        last_sync_at=datetime.now().isoformat(),
        sync_mode=sync_mode,
        last_source=last_source,
        success=success,
        error=error,
        files_processed=files_processed,
        entities_updated=entities_updated
    )
    try:
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(status), f, indent=2)
        
        # Also update last-sync.json for backend_resolver freshness calculation
        with open(".graph/last-sync.json", "w", encoding="utf-8") as f:
            json.dump({"timestamp": status.last_sync_at}, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to update sync status: {e}")
