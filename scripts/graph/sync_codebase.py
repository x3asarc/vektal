#!/usr/bin/env python3
"""Manual codebase sync command for knowledge graph."""

import os
import sys
import argparse
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.graph.codebase_scanner import scan_codebase, ScanConfig

def main():
    parser = argparse.ArgumentParser(description="Sync codebase to knowledge graph")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be indexed")
    parser.add_argument('--dir', help="Specific directory to scan")
    parser.add_argument('--no-embeddings', action='store_true', help="Skip embedding generation")
    args = parser.parse_args()

    # Configure scan
    config = ScanConfig(generate_embeddings=not args.no_embeddings)
    if args.dir:
        config.include_dirs = [args.dir]

    root_path = '.'

    print(f"Scanning codebase...")
    print(f"Directories: {', '.join(config.include_dirs)}")
    print(f"Embeddings: {'disabled' if args.no_embeddings else 'enabled'}")
    print()

    # Scan
    result = scan_codebase(root_path, config)

    # Print summary
    print(f"\n=== Scan Complete ({result.scan_duration_seconds:.1f}s) ===")
    print(f"Files: {len(result.files)}")
    print(f"Classes: {len(result.classes)}")
    print(f"Functions: {len(result.functions)}")
    print(f"Planning docs: {len(result.planning_docs)}")

    if result.errors:
        print(f"\nErrors: {len(result.errors)}")
        for error in result.errors[:5]:  # Show first 5
            print(f"  - {error}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more")

    if args.dry_run:
        print("\nDRY RUN: No changes made")
    else:
        # Export to JSON (fallback when graph unavailable)
        output_file = '.graph_scan_export.json'
        export_data = {
            'files': result.files,
            'classes': result.classes,
            'functions': result.functions,
            'planning_docs': result.planning_docs
        }
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"\nExported to {output_file}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
