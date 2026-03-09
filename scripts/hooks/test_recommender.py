#!/usr/bin/env python3
"""
Test Recommender PostToolUse Hook.

Suggests relevant tests after Edit/Write operations on source files.
Uses graph queries to determine test impact based on function call chains.

Budget: 300ms max execution time.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Set
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / ".graph" / "test-recommender.log"


def _log(message: str) -> None:
    """Append log message to test-recommender.log."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Silent failure - never block


def _should_recommend(file_path: str) -> bool:
    """Check if file path warrants test recommendations."""
    # Normalize path
    normalized = file_path.replace("\\", "/")

    # Only source files, not test files
    if "/test" in normalized or normalized.endswith("_test.py"):
        return False

    # Only Python/TypeScript source files
    if not any(normalized.endswith(ext) for ext in [".py", ".ts", ".tsx", ".js", ".jsx"]):
        return False

    # Only src/ or frontend/src/ files
    return normalized.startswith("src/") or normalized.startswith("frontend/src/")


def _get_functions_in_file(file_path: str) -> List[str]:
    """Query graph for functions defined in file."""
    try:
        from src.graph.query_templates import execute_template

        results = execute_template("functions_in_file", {"file_path": file_path}, timeout_ms=500)
        return [r.get("name", "") for r in results if r.get("name")]

    except Exception as exc:
        _log(f"WARN: functions_in_file query failed for {file_path}: {exc}")
        return []


def _get_function_callers(function_name: str) -> List[str]:
    """Query graph for files that call this function."""
    try:
        from src.graph.query_templates import execute_template

        results = execute_template("function_callers", {"function_name": function_name}, timeout_ms=500)
        return [r.get("caller_file", "") for r in results if r.get("caller_file")]

    except Exception as exc:
        _log(f"WARN: function_callers query failed for {function_name}: {exc}")
        return []


def _map_to_test_files(source_files: Set[str]) -> List[str]:
    """Map source files to corresponding test files."""
    test_files = set()

    for source_file in source_files:
        # Python test mapping
        if source_file.endswith(".py"):
            # src/core/embeddings.py -> tests/unit/test_embeddings.py
            if source_file.startswith("src/"):
                module_name = Path(source_file).stem
                test_files.add(f"tests/unit/test_{module_name}.py")
                test_files.add(f"tests/integration/test_{module_name}.py")

        # TypeScript/React test mapping
        elif any(source_file.endswith(ext) for ext in [".ts", ".tsx", ".js", ".jsx"]):
            # frontend/src/components/Button.tsx -> frontend/src/components/Button.test.tsx
            test_file = source_file.rsplit(".", 1)[0] + ".test." + source_file.rsplit(".", 1)[1]
            test_files.add(test_file)

    # Filter to files that actually exist
    existing_tests = []
    for test_file in test_files:
        test_path = PROJECT_ROOT / test_file
        if test_path.exists():
            existing_tests.append(test_file)

    return sorted(existing_tests)


def _format_recommendations(edited_file: str, test_files: List[str], affected_files: Set[str]) -> str:
    """Format test recommendations output."""
    if not test_files:
        return ""  # No recommendations = silent

    lines = []
    lines.append("\n" + "="*60)
    lines.append("🧪 TEST RECOMMENDATIONS")
    lines.append("="*60)
    lines.append(f"\nEdited: {edited_file}")

    if affected_files:
        lines.append(f"\n📍 Impact: {len(affected_files)} file(s) depend on this")
        if len(affected_files) <= 5:
            for f in sorted(affected_files):
                lines.append(f"  • {f}")
        else:
            for f in sorted(list(affected_files)[:3]):
                lines.append(f"  • {f}")
            lines.append(f"  ... and {len(affected_files) - 3} more")

    lines.append(f"\n🎯 Suggested Tests:")
    for test_file in test_files:
        lines.append(f"  • {test_file}")

    lines.append("\n💡 Run: python -m pytest " + " ".join(test_files) + " -x")
    lines.append("="*60 + "\n")

    return "\n".join(lines)


def main() -> int:
    """Main hook execution - always returns 0 (never blocks)."""
    start_time = time.perf_counter()

    # Get edited file from environment (set by Claude Code)
    # Fallback: try to get from command line args
    edited_file = os.environ.get("CLAUDE_TOOL_FILE_PATH", "")
    if not edited_file and len(sys.argv) > 1:
        edited_file = sys.argv[1]

    if not edited_file:
        _log("WARN: No file path provided, skipping")
        return 0

    # Check if we should recommend tests for this file
    if not _should_recommend(edited_file):
        _log(f"INFO: Skipping {edited_file} (not a source file)")
        return 0

    try:
        # Get functions in edited file
        functions = _get_functions_in_file(edited_file)
        if not functions:
            _log(f"INFO: No functions found in {edited_file}")
            return 0

        # Get all files that call these functions
        affected_files: Set[str] = set()
        for func in functions:
            callers = _get_function_callers(func)
            affected_files.update(callers)

        # Add the edited file itself
        affected_files.add(edited_file)

        # Map to test files
        test_files = _map_to_test_files(affected_files)

        # Format and output recommendations
        if test_files:
            recommendations = _format_recommendations(edited_file, test_files, affected_files)
            print(recommendations, flush=True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        _log(f"INFO: Test recommendations complete in {elapsed_ms:.2f}ms ({len(test_files)} tests found)")

    except Exception as exc:
        _log(f"ERROR: Unexpected failure: {exc}")
        # Still return 0 - never block

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
