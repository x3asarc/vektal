#!/usr/bin/env python3
"""
File-based Pattern Detector (MVP - before Phase 14)
Scans .claude/metrics/ for similar failures
Upgrade to graph-based in Phase 14 for <100ms performance
"""

import json
import glob
import sys
from pathlib import Path
from collections import defaultdict

def find_similar_failures(current_failure: dict) -> list:
    """
    Scan all metric files for similar failures
    Returns pattern if ≥3 similar failures found

    NOTE: This is slower than graph queries (5-10s vs <100ms)
    but works before Phase 14 knowledge graph is ready
    """

    root_cause = current_failure.get("root_cause", "unknown")

    # Extract root cause type (e.g., "missing_dependency:graphiti-core" → "missing_dependency")
    root_cause_type = root_cause.split(":")[0] if ":" in root_cause else root_cause

    # Scan all metrics files
    metrics_files = glob.glob(".claude/metrics/*/*.json")

    if not metrics_files:
        print("⚠️  No previous metrics found - pattern detection unavailable", file=sys.stderr)
        return []

    similar_failures = defaultdict(lambda: {
        "count": 0,
        "fixes_applied": [],
        "success_rate": 0,
        "recent_occurrences": []
    })

    for metrics_file in metrics_files:
        try:
            with open(metrics_file) as f:
                metrics = json.load(f)

            metrics_root_cause = metrics.get("root_cause", "unknown")

            # Check if similar root cause
            if metrics_root_cause.startswith(root_cause_type):
                key = metrics_root_cause
                similar_failures[key]["count"] += 1
                similar_failures[key]["recent_occurrences"].append({
                    "phase": metrics.get("phase"),
                    "plan": metrics.get("plan"),
                    "timestamp": metrics.get("timestamp")
                })

                # Track fixes if available
                if "fix_applied" in metrics:
                    similar_failures[key]["fixes_applied"].append({
                        "fix": metrics["fix_applied"],
                        "success": metrics.get("fix_success", False)
                    })
        except Exception as e:
            # Skip malformed metrics files
            continue

    # Convert to list and sort by count
    results = []
    for root_cause_key, data in similar_failures.items():
        # Calculate success rate
        successful_fixes = [f for f in data["fixes_applied"] if f["success"]]
        total_fixes = len(data["fixes_applied"])
        success_rate = len(successful_fixes) / total_fixes if total_fixes > 0 else 0

        # Get most successful fix
        best_fix = successful_fixes[0]["fix"] if successful_fixes else None

        results.append({
            "root_cause": root_cause_key,
            "occurrences": data["count"],
            "fix": best_fix,
            "worked": success_rate > 0.5,
            "success_rate": success_rate,
            "recent_occurrences": data["recent_occurrences"][:3]  # Last 3
        })

    # Sort by occurrences
    results.sort(key=lambda x: x["occurrences"], reverse=True)

    return results

def generate_improvement_proposal(current_failure: dict, pattern: list) -> dict:
    """Generate improvement proposal based on historical pattern"""

    if not pattern or pattern[0]["occurrences"] < 3:
        return {
            "pattern_detected": False,
            "reason": f"Only {pattern[0]['occurrences'] if pattern else 0} similar failures found (need ≥3)"
        }

    most_common = pattern[0]

    # Confidence based on occurrences (more = higher confidence)
    confidence = min(0.95, most_common["occurrences"] / 10)

    # Use suggested fix from current failure if no historical fix available
    proposed_fix = most_common["fix"] or current_failure.get("suggested_fix", "Manual investigation required")

    return {
        "pattern_detected": True,
        "occurrences": most_common["occurrences"],
        "root_cause": current_failure["root_cause"],
        "proposed_fix": proposed_fix,
        "confidence": confidence,
        "historical_success_rate": most_common.get("success_rate", 0),
        "reasoning": f"Found {most_common['occurrences']} similar failures in historical metrics. "
                     f"Proposed fix has {confidence:.0%} confidence based on occurrence frequency.",
        "recent_failures": most_common.get("recent_occurrences", [])
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pattern_detector_file_based.py <metrics_file.json>")
        sys.exit(1)

    metrics_file = sys.argv[1]

    try:
        with open(metrics_file) as f:
            current_failure = json.load(f)
    except Exception as e:
        print(f"Error reading metrics file: {e}", file=sys.stderr)
        sys.exit(1)

    # Find similar failures
    pattern = find_similar_failures(current_failure)

    # Generate proposal
    proposal = generate_improvement_proposal(current_failure, pattern)

    # Output as JSON for orchestrator
    print(json.dumps(proposal, indent=2))
