#!/usr/bin/env python3
"""
Graph Impact Advisor PreToolUse Hook.

Shows blast radius before editing critical infrastructure files.
Only fires for high-risk paths to minimize overhead.

Budget: 500ms max execution time (with 5-minute cache).
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Add project root to Python path for imports
sys.path.insert(0, str(PROJECT_ROOT))

# Set output encoding to UTF-8 for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
CACHE_PATH = PROJECT_ROOT / ".graph" / "impact-cache.json"
LOG_PATH = PROJECT_ROOT / ".graph" / "impact-advisor.log"

# High-risk paths that warrant impact analysis
HIGH_RISK_PREFIXES = [
    "src/core/",
    "src/api/",
    "src/models/",
    "src/graph/",
    "src/assistant/",
]

CACHE_TTL_MINUTES = 5


def _log(message: str) -> None:
    """Append log message to impact-advisor.log."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Silent failure - never block


def _is_high_risk(file_path: str) -> bool:
    """Check if file path is in high-risk category."""
    normalized = file_path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in HIGH_RISK_PREFIXES)


def _read_cache() -> Dict[str, Any]:
    """Read impact cache from disk."""
    if not CACHE_PATH.exists():
        return {}

    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        _log(f"WARN: Failed to parse cache: {exc}")
        return {}


def _write_cache(cache: Dict[str, Any]) -> None:
    """Write impact cache to disk."""
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception as exc:
        _log(f"WARN: Failed to write cache: {exc}")


def _get_cached_impact(file_path: str, cache: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Get cached impact data if still valid."""
    entry = cache.get(file_path)
    if not entry:
        return None

    try:
        cached_at = datetime.fromisoformat(entry["cached_at"].replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - cached_at

        if age < timedelta(minutes=CACHE_TTL_MINUTES):
            return entry["impact"]
    except Exception:
        pass

    return None


def _query_impact_radius(file_path: str) -> List[Dict[str, Any]]:
    """Query graph for files that depend on this file."""
    try:
        from src.graph.query_templates import execute_template

        results = execute_template("impact_radius", {"file_path": file_path}, timeout_ms=1500)
        return results

    except Exception as exc:
        _log(f"WARN: impact_radius query failed for {file_path}: {exc}")
        return []


def _format_warning(file_path: str, impact: List[Dict[str, Any]]) -> str:
    """Format impact warning output."""
    if not impact:
        return ""  # No impact = no warning

    # Group by depth
    by_depth: Dict[int, List[str]] = {}
    for item in impact:
        depth = item.get("depth", 0)
        path = item.get("path", "")
        if path:
            by_depth.setdefault(depth, []).append(path)

    total_count = len(impact)

    lines = []
    lines.append("\n" + "="*60)
    lines.append("⚠️  GRAPH IMPACT ADVISOR")
    lines.append("="*60)
    lines.append(f"\n📍 Editing: {file_path}")
    lines.append(f"🔗 Impact Radius: {total_count} file(s) depend on this")

    # Show direct dependents (depth 1)
    if 1 in by_depth:
        direct = by_depth[1]
        lines.append(f"\n📌 Direct Callers ({len(direct)}):")
        for dep in sorted(direct)[:5]:
            lines.append(f"  • {dep}")
        if len(direct) > 5:
            lines.append(f"  ... and {len(direct) - 5} more")

    # Show indirect dependents (depth 2-3)
    indirect = []
    for depth in [2, 3]:
        indirect.extend(by_depth.get(depth, []))

    if indirect:
        lines.append(f"\n🔀 Indirect Callers ({len(indirect)}):")
        for dep in sorted(indirect)[:3]:
            lines.append(f"  • {dep}")
        if len(indirect) > 3:
            lines.append(f"  ... and {len(indirect) - 3} more")

    # Suggest tests
    module_name = Path(file_path).stem
    lines.append(f"\n💡 Tip: Run tests/integration/test_{module_name}_pipeline.py after changes")
    lines.append("="*60 + "\n")

    return "\n".join(lines)


def main() -> int:
    """Main hook execution - always returns 0 (never blocks)."""
    start_time = time.perf_counter()

    # Read stdin once (cross-CLI: Claude Code, Gemini CLI, Codex all pass context here)
    stdin_data = {}
    if not sys.stdin.isatty():
        try:
            stdin_data = json.load(sys.stdin)
        except Exception:
            pass

    # Self-filter: only run for Edit/Write tool calls.
    # Config-level filter (settings.json) may not work in all CLI/subagent contexts.
    tool_name = stdin_data.get("tool_name", "")
    if tool_name and tool_name not in ("Edit", "Write", "str_replace_based_edit_tool",
                                       "create_file", "replace", "write_file"):
        print(json.dumps({"decision": "allow"}))
        return 0

    # Get file being edited from stdin, environment, or args
    tool_input = stdin_data.get("tool_input", {})
    edited_file = tool_input.get("file_path") or tool_input.get("path") or os.environ.get("CLAUDE_TOOL_FILE_PATH", "")
    if not edited_file and len(sys.argv) > 1:
        edited_file = sys.argv[1]

    if not edited_file:
        _log("WARN: No file path provided, skipping")
        print(json.dumps({"decision": "allow"}))
        return 0

    # Check if this is a high-risk file
    if not _is_high_risk(edited_file):
        _log(f"INFO: Skipping {edited_file} (not high-risk)")
        print(json.dumps({"decision": "allow"}))
        return 0

    try:
        # Check cache first
        cache = _read_cache()
        impact = _get_cached_impact(edited_file, cache)

        if impact is None:
            # Cache miss - query graph
            impact = _query_impact_radius(edited_file)

            # Update cache
            cache[edited_file] = {
                "impact": impact,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            _write_cache(cache)

        # Format and output warning to stderr for Gemini CLI
        if impact:
            warning = _format_warning(edited_file, impact)
            print(warning, file=sys.stderr, flush=True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        _log(f"INFO: Impact check complete in {elapsed_ms:.2f}ms ({len(impact)} dependents)")

    except Exception as exc:
        _log(f"ERROR: Unexpected failure: {exc}")
        # Still return 0 - never block

    # Gemini CLI compatibility: Output allow decision
    print(json.dumps({"decision": "allow"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
