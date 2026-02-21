#!/usr/bin/env python3
"""
One-time migration script to import historical failure metrics into the graph.

Reads JSON metrics from .claude/metrics/ and emits them as Episode nodes
using the EpisodeType.ORACLE_DECISION (which includes failure data).

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.tasks.graphiti_sync import emit_episode
from src.core.synthex_entities import EpisodeType

logger = logging.getLogger(__name__)

def migrate_metrics():
    metrics_dir = Path(".claude/metrics")
    if not metrics_dir.exists():
        print(f"[migration] Metrics directory not found: {metrics_dir}")
        return

    print("[migration] Scanning for historical metrics...")
    json_files = list(metrics_dir.glob("**/*.json"))
    print(f"[migration] Found {len(json_files)} metrics files")

    success_count = 0
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Skip if already marked as fixed or not a failure
            # (In a real migration, we might want everything, but let's prioritize failures)
            
            # Prepare payload matching EpisodeType fields
            payload = {
                'decision': 'fail' if data.get('test_result') == 'FAIL' else 'pass',
                'confidence': 1.0,
                'reason_codes': [data.get('root_cause', 'unknown')],
                'evidence_refs': [str(file_path)],
                'phase': data.get('phase'),
                'plan': data.get('plan'),
                'test_result': data.get('test_result'),
                'root_cause': data.get('root_cause'),
                'suggested_fix': data.get('suggested_fix'),
                'duration': data.get('duration_seconds', 0),
                'created_at': data.get('timestamp', datetime.utcnow().isoformat())
            }
            
            # Emit to graph
            # Note: Using .delay() for async processing
            emit_episode.delay(
                EpisodeType.ORACLE_DECISION.value,
                "codebase",
                payload,
                correlation_id=f"migration_{file_path.stem}"
            )
            success_count += 1
            
        except Exception as e:
            print(f"[migration] Failed to process {file_path}: {e}")

    print(f"[migration] Successfully queued {success_count} metrics for ingestion")

if __name__ == "__main__":
    migrate_metrics()
