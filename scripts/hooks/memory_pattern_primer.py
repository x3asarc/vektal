#!/usr/bin/env python3
"""
Memory Pattern Primer PreToolUse Hook.

Loads long-term patterns before Task tool spawns to inject accumulated wisdom.
Fires only on Task tool invocations (rare, high-value events).

Budget: 200ms max execution time.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LONG_TERM_INDEX_PATH = PROJECT_ROOT / ".memory" / "long-term" / "index.json"
LOG_PATH = PROJECT_ROOT / ".graph" / "memory-primer.log"


def _log(message: str) -> None:
    """Append log message to memory-primer.log."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Silent failure - never block


def _read_local_index() -> Dict[str, Any]:
    """Read long-term memory index from local file."""
    if not LONG_TERM_INDEX_PATH.exists():
        return {}

    try:
        return json.loads(LONG_TERM_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        _log(f"WARN: Failed to parse long-term index: {exc}")
        return {}


def _query_graph_patterns() -> List[Dict[str, Any]]:
    """Query Neo4j for LongTermPattern nodes."""
    try:
        # Import here to avoid startup cost when hook doesn't fire
        from src.core.graphiti_client import get_graphiti_client

        client = get_graphiti_client()
        cypher = """
            MATCH (lp:LongTermPattern)
            RETURN lp.description as description,
                   lp.domain as domain,
                   lp.task_id as task_id,
                   lp.created_at as created_at
            ORDER BY lp.created_at DESC
            LIMIT 10
        """

        # Run query with timeout
        records = client.query(cypher, {}, timeout_ms=1000)

        patterns = []
        for record in records or []:
            if hasattr(record, "data"):
                patterns.append(record.data())
            elif isinstance(record, dict):
                patterns.append(record)

        return patterns

    except Exception as exc:
        _log(f"WARN: Graph query failed: {exc}")
        return []


def _format_primer(local_index: Dict[str, Any], graph_patterns: List[Dict[str, Any]]) -> str:
    """Format primer output for injection into Task tool."""
    lines = []
    lines.append("\n" + "="*60)
    lines.append("🧠 MEMORY PATTERN PRIMER")
    lines.append("="*60)

    # Event counters from local index
    event_counters = local_index.get("event_counters", {})
    if event_counters:
        lines.append("\n📊 Session Activity:")
        for event_type, count in sorted(event_counters.items()):
            if count > 0:
                lines.append(f"  • {event_type}: {count}")

    # Long-term patterns from graph
    if graph_patterns:
        lines.append("\n📚 Long-Term Patterns:")
        for pattern in graph_patterns[:5]:  # Top 5 most recent
            domain = pattern.get("domain", "general")
            desc = pattern.get("description", "")
            task_id = pattern.get("task_id", "")

            lines.append(f"\n  [{domain.upper()}] {desc}")
            if task_id:
                lines.append(f"    Task: {task_id}")
    else:
        lines.append("\n📚 Long-Term Patterns: (No patterns in graph yet)")

    # Last updated
    last_updated = local_index.get("last_updated", "unknown")
    lines.append(f"\n⏱️  Index last updated: {last_updated}")

    lines.append("="*60 + "\n")

    return "\n".join(lines)


def main() -> int:
    """Main hook execution - always returns 0 (never blocks)."""
    start_time = time.perf_counter()

    try:
        # Read local index
        local_index = _read_local_index()

        # Query graph for patterns
        graph_patterns = _query_graph_patterns()

        # Format and output primer
        primer = _format_primer(local_index, graph_patterns)
        print(primer, flush=True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        _log(f"INFO: Memory primer complete in {elapsed_ms:.2f}ms ({len(graph_patterns)} patterns)")

    except Exception as exc:
        _log(f"ERROR: Unexpected failure: {exc}")
        # Still return 0 - never block

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
