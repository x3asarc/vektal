"""
Operator CLI for Graph Status (Phase 14.3).
Provides a unified view of backend health and sync reliability.
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.graph.backend_resolver import read_runtime_manifest
from src.graph.sync_status import get_sync_status

def main():
    parser = argparse.ArgumentParser(description="Show knowledge graph status")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    backend = read_runtime_manifest()
    sync = get_sync_status()

    status_data = {
        "backend": None,
        "sync": None
    }

    if backend:
        status_data["backend"] = {
            "type": backend.backend.value,
            "checked_at": backend.checked_at,
            "reason": backend.reason,
            "is_degraded": backend.is_degraded,
            "latency_ms": backend.probe_latency_ms
        }

    if sync:
        status_data["sync"] = {
            "last_sync_at": sync.last_sync_at,
            "sync_mode": sync.sync_mode,
            "last_source": sync.last_source,
            "success": sync.success,
            "error": sync.error,
            "files_processed": sync.files_processed,
            "entities_updated": sync.entities_updated
        }

    if args.json:
        print(json.dumps(status_data, indent=2))
        return 0

    # Human-readable output
    print("=== Knowledge Graph Status ===")
    
    if backend:
        tag = "[OK]" if not backend.is_degraded else "[WARN]"
        print(f"\n{tag} [Backend: {backend.backend.value.upper()}]")
        print(f"    Checked: {backend.checked_at}")
        print(f"    Reason:  {backend.reason}")
        if backend.probe_latency_ms > 0:
            print(f"    Latency: {backend.probe_latency_ms:.2f}ms")
    else:
        print("\n[FAIL] [Backend: UNKNOWN]")
        print("    No runtime manifest found. Run bootstrap script.")

    if sync:
        sync_tag = "[OK]" if sync.success else "[FAIL]"
        print(f"\n{sync_tag} [Last Sync: {sync.last_sync_at}]")
        print(f"    Mode:    {sync.sync_mode}")
        print(f"    Source:  {sync.last_source}")
        print(f"    Files:   {sync.files_processed}")
        if sync.entities_updated > 0:
            print(f"    Entities: {sync.entities_updated}")
        if not sync.success:
            print(f"    Error:   {sync.error}")
    else:
        print("\n[WARN] [Last Sync: NEVER]")
        print("    No sync status recorded.")

    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
