#!/usr/bin/env python3
"""
Graph-based Pattern Detector (Phase 14 upgrade)
Queries Neo4j for similar failures in <100ms
Replaces file-based scanner (5-10s)
"""

import json
import logging
from typing import List, Dict, Any
from src.graph.query_templates import execute_template

logger = logging.getLogger(__name__)


def find_similar_failures(current_failure: dict) -> list:
    """
    Query graph for similar failures.
    100x faster than file-based version.
    
    Args:
        current_failure: Dictionary containing failure metrics.
        
    Returns:
        List of formatted failure patterns.
    """
    root_cause = current_failure.get("root_cause", "unknown")
    root_cause_type = root_cause.split(":")[0]

    # Use template query to find failures with same root cause type
    results = execute_template("similar_failures", {
        "root_cause_type": root_cause_type,
        "limit": 10
    })

    # Format for compatibility with existing orchestrator (on_execution_complete.py)
    # The existing orchestrator expects a list of pattern objects
    patterns = []
    
    if results:
        # Simplified pattern detection for MVP upgrade
        # In a real setup, we'd use similarity algorithms or counts from Cypher
        patterns.append({
            "pattern_detected": True,
            "root_cause": root_cause,
            "occurrences": len(results),
            "confidence": 0.85 if len(results) > 2 else 0.6,
            "proposed_fix": results[0].get("fix") if results else current_failure.get("suggested_fix"),
            "reasoning": f"Found {len(results)} historical occurrences of {root_cause_type} in the knowledge graph."
        })
        
    return patterns


if __name__ == "__main__":
    # If run as script, simulate for CLI testing
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            metrics = json.load(f)
        results = find_similar_failures(metrics)
        if results:
            print(json.dumps(results[0]))
        else:
            print(json.dumps({"pattern_detected": False, "reason": "No similar failures in graph"}))
