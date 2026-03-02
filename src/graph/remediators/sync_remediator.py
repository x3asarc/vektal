"""
Sync Remediator Tool (Phase 14.3).
Diagnoses and resolves codebase-to-graph sync pipeline failures.
"""

import os
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List
from src.graph.universal_fixer import UniversalRemediator, RemediationResult
from src.core.graphiti_client import get_graphiti_client
from src.graph.incremental_sync import sync_changed_files, get_staged_files

logger = logging.getLogger(__name__)

class SyncRemediator(UniversalRemediator):
    """
    Remediator for knowledge graph sync pipeline failures.
    Handles connection retries, timeout diagnosis, and manual sync triggers.
    """

    @property
    def service_name(self) -> str:
        return "graph_sync"

    @property
    def description(self) -> str:
        return "Diagnoses and repairs codebase-to-graph sync pipeline failures."

    async def validate_environment(self) -> bool:
        """Check if graph is enabled in config."""
        return os.getenv("GRAPH_ORACLE_ENABLED", "true").lower() == "true"

    async def diagnose_and_fix(self, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        actions = []
        
        # 1. Diagnose: Connection Check
        client = get_graphiti_client()
        if not client:
            actions.append("Graphiti client unavailable (Connection Failure).")
            return RemediationResult(False, "Could not connect to Neo4j/Graphiti", actions)

        # 2. Check for staged files that might have failed to sync
        staged_files = get_staged_files()
        if not staged_files:
            actions.append("No staged files detected for incremental sync.")
            # If no staged files, maybe we want to sync the last commit? 
            # For now, we follow the 'staged' logic of incremental_sync.
            return RemediationResult(True, "Sync pipeline is clear (no staged changes)", actions)

        actions.append(f"Detected {len(staged_files)} staged files pending sync.")

        # 3. Fix: Retry sync with exponential backoff logic
        max_retries = (params or {}).get("max_retries", 3)
        commit_msg = (params or {}).get("commit_message", "Manual remediation sync")
        
        for attempt in range(1, max_retries + 1):
            actions.append(f"Sync attempt {attempt}/{max_retries}...")
            try:
                # Triggers incremental_sync.py logic
                result = sync_changed_files(staged_files, commit_msg)
                
                if not result.errors:
                    msg = f"Successfully synced {result.files_processed} files."
                    actions.append(msg)
                    return RemediationResult(True, msg, actions)
                else:
                    error_msg = "; ".join(result.errors[:3])
                    actions.append(f"Attempt {attempt} failed: {error_msg}")
                    
                    if attempt < max_retries:
                        delay = 2 ** attempt # 2, 4, 8s backoff
                        actions.append(f"Backing off for {delay}s...")
                        await asyncio.sleep(delay)
            except Exception as e:
                actions.append(f"Attempt {attempt} crashed: {str(e)}")

        return RemediationResult(False, "Sync remediation failed after maximum retries", actions)
