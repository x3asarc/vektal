#!/usr/bin/env python3
"""
Pre-commit hook for codebase knowledge graph synchronization.

Runs on every commit:
1. Gets list of staged files
2. Parses commit message for phase/plan references
3. Updates graph with changed file entities
4. Creates planning doc linkages

Non-blocking: Warns but allows commit if graph unavailable.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.graph.incremental_sync import get_staged_files, sync_changed_files

def main():
    # Check if graph sync is enabled
    if os.environ.get('GRAPH_SYNC_ENABLED', 'true').lower() != 'true':
        print("[graph-sync] Disabled via environment variable, skipping")
        sys.exit(0)

    # Get staged files
    staged_files = get_staged_files()
    if not staged_files:
        sys.exit(0)

    # Get commit message (passed as first argument in commit-msg stage)
    commit_message = "Incremental update"
    if len(sys.argv) > 1:
        commit_msg_file = sys.argv[1]
        if os.path.exists(commit_msg_file):
            with open(commit_msg_file, 'r', encoding='utf-8') as f:
                commit_message = f.read()

    print(f"[graph-sync] Syncing {len(staged_files)} staged files...")
    
    try:
        result = sync_changed_files(staged_files, commit_message)
        
        if result.graph_available:
            print(f"[graph-sync] Processed {result.files_processed} files in {result.duration_ms:.1f}ms")
            print(f"[graph-sync] Created {result.entities_created} entities, {result.relationships_created} relationships")
            if result.planning_links_created > 0:
                print(f"[graph-sync] Linked to planning documents")
        else:
            print("[graph-sync] Warning: Graph unavailable, entities not persisted")
            
        if result.errors:
            print("[graph-sync] Warnings/Errors occurred during sync:")
            for err in result.errors[:5]:  # Limit output
                print(f"  - {err}")
            if len(result.errors) > 5:
                print(f"  - ... and {len(result.errors)-5} more")

    except Exception as e:
        print(f"[graph-sync] Unexpected error: {e}")
        # Never block the commit
        sys.exit(0)

    # Always exit 0 to allow commit to proceed
    sys.exit(0)

if __name__ == "__main__":
    main()
