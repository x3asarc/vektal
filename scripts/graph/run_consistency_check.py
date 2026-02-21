#!/usr/bin/env python3
"""
CLI for codebase knowledge graph consistency check and repair.

Detects divergence between filesystem and graph nodes (missing/stale/modified files)
and provides automated repair options.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import sys
import os
import argparse
from typing import List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.graph.consistency_daemon import check_consistency, repair_divergence

def main():
    parser = argparse.ArgumentParser(description="Knowledge graph consistency checker")
    parser.add_argument("--repair", action="store_true", help="Repair detected divergences")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate repair without changes")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Actually apply repair changes")
    parser.add_argument("--verbose", action="store_true", help="Detailed output of inconsistencies")
    
    args = parser.parse_args()
    
    print("[consistency] Checking graph/filesystem consistency...")
    report = check_consistency()
    
    print(f"[consistency] Filesystem: {report.files_in_filesystem} files")
    print(f"[consistency] Graph:      {report.files_in_graph} files")
    print(f"[consistency] Missing from graph: {len(report.missing_from_graph)} files")
    print(f"[consistency] Stale in graph:      {len(report.stale_in_graph)} files")
    print(f"[consistency] Hash mismatches:     {len(report.hash_mismatches)} files")
    
    if report.is_consistent:
        print("\n✅ Knowledge graph is consistent with filesystem.")
        sys.exit(0)
        
    print("\n[consistency] Inconsistencies found:")
    
    if args.verbose or (len(report.missing_from_graph) + len(report.stale_in_graph) + len(report.hash_mismatches)) < 10:
        for path in report.missing_from_graph:
            print(f"  - {path} (missing from graph)")
        for path in report.stale_in_graph:
            print(f"  - {path} (stale in graph)")
        for path in report.hash_mismatches:
            print(f"  - {path} (hash mismatch)")
    else:
        print(f"  - ({len(report.missing_from_graph)} missing, {len(report.stale_in_graph)} stale, {len(report.hash_mismatches)} mismatches)")
        print("  - Use --verbose to see full list")

    if args.repair:
        print(f"\n[consistency] Repairing divergence (dry_run={args.dry_run})...")
        result = repair_divergence(report, dry_run=args.dry_run)
        
        print(f"[consistency] Added:   {result.files_added}")
        print(f"[consistency] Removed: {result.files_removed}")
        print(f"[consistency] Updated: {result.files_updated}")
        
        if args.dry_run:
            print("[consistency] Dry-run complete. Run with --no-dry-run to apply changes.")
        else:
            print("[consistency] ✨ Knowledge graph repaired successfully.")
    else:
        print("\n[consistency] Run with --repair to fix these issues.")

if __name__ == "__main__":
    main()
