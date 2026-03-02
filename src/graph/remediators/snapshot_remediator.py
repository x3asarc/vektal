"""
Snapshot Remediator Tool (Phase 14.3).
Autonomous repair and rebuild for local graph snapshots.
"""

import os
import json
import logging
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from src.graph.universal_fixer import UniversalRemediator, RemediationResult
from src.graph.local_graph_store import get_snapshot

logger = logging.getLogger(__name__)

class SnapshotRemediator(UniversalRemediator):
    """
    Remediator for corrupted or missing local graph snapshots.
    Ensures .graph/local-snapshot.json is valid and matches git HEAD.
    """

    @property
    def service_name(self) -> str:
        return "local_snapshot"

    @property
    def description(self) -> str:
        return "Rebuilds or repairs local graph snapshots from git HEAD."

    def _get_current_head(self) -> str:
        try:
            return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        except Exception as e:
            logger.error(f"Failed to get git HEAD: {e}")
            return "unknown"

    async def validate_environment(self) -> bool:
        """Ensure git is available and .graph directory exists."""
        os.makedirs(".graph/snapshots", exist_ok=True)
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
            return True
        except:
            return False

    async def diagnose_and_fix(self, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        actions = []
        snapshot_path = Path(".graph/local-snapshot.json")
        current_head = self._get_current_head()

        # 1. Diagnose: Check if snapshot exists and is valid JSON
        if not snapshot_path.exists():
            actions.append("Snapshot missing. Triggering rebuild...")
        else:
            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check for required fields (NullClaw structure check)
                required = ["built_at", "files", "imports_out"]
                missing = [f for f in required if f not in data]
                if missing:
                    actions.append(f"Snapshot corrupted (missing fields: {', '.join(missing)})")
                else:
                    # Check staleness vs git HEAD
                    stored_head = data.get("git_head")
                    if stored_head != current_head:
                        actions.append(f"Snapshot stale (Stored: {stored_head}, HEAD: {current_head})")
                    else:
                        return RemediationResult(True, "Snapshot is healthy and up-to-date", ["Integrity Check"])

            except json.JSONDecodeError:
                actions.append("Snapshot file contains invalid JSON (corrupted).")
            except Exception as e:
                actions.append(f"Error reading snapshot: {str(e)}")

        # 2. Fix: Rebuild snapshot
        actions.append("Executing local_graph_store.get_snapshot(force_refresh=True)...")
        try:
            # Rebuild
            snapshot = get_snapshot(force_refresh=True)
            
            # Update the snapshot file with git HEAD metadata
            # Note: local_graph_store.py doesn't currently store git_head, 
            # so we inject it here for future checks.
            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["git_head"] = current_head
                with open(snapshot_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                actions.append(f"Injected git_head {current_head} into manifest.")
            except Exception as e:
                logger.warning(f"Failed to inject git_head: {e}")

            return RemediationResult(True, "Snapshot rebuilt successfully", actions)
        except Exception as e:
            return RemediationResult(False, f"Snapshot rebuild failed: {str(e)}", actions)
