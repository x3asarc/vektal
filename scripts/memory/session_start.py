#!/usr/bin/env python3
"""SessionStart memory bootstrap."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.context.build_agent_primer import build_agent_primer  # noqa: E402
from scripts.context.build_context_link_map import build_context_link_map  # noqa: E402
from scripts.context.build_folder_summaries import build_folder_summaries  # noqa: E402
from src.memory.event_log import append_event  # noqa: E402
from src.memory.event_schema import EventType, create_event  # noqa: E402
from src.memory.memory_manager import (  # noqa: E402
    LongTermMemory,
    ShortTermMemory,
    WorkingMemory,
    ensure_memory_layout,
)
from scripts.memory.sync_agents_memory import sync_agents_memory_section  # noqa: E402


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip() or "unknown"
    except Exception:
        pass
    return "unknown"


def _needs_refresh(path: Path, *, max_age_hours: int = 24, current_sha: str | None = None) -> bool:
    if not path.exists():
        return True
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if datetime.now(timezone.utc) - modified > timedelta(hours=max_age_hours):
        return True
    if current_sha and path.name == "AGENT_START_HERE.md":
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"Source commit:\s*`([^`]+)`", text)
        if not match or match.group(1).strip() != current_sha:
            return True
    return False


def _refresh_context_docs(current_sha: str) -> list[str]:
    refreshed: list[str] = []
    primer_path = REPO_ROOT / "docs" / "AGENT_START_HERE.md"
    folder_path = REPO_ROOT / "docs" / "FOLDER_SUMMARIES.md"
    link_map_path = REPO_ROOT / "docs" / "CONTEXT_LINK_MAP.md"

    primer_stale = _needs_refresh(primer_path, current_sha=current_sha)
    summaries_stale = _needs_refresh(folder_path)
    link_map_stale = _needs_refresh(link_map_path)

    if primer_stale:
        build_agent_primer(repo_root=REPO_ROOT, git_sha=current_sha, write=True)
        refreshed.append(primer_path.as_posix())
    if summaries_stale:
        build_folder_summaries(repo_root=REPO_ROOT, write=True)
        refreshed.append(folder_path.as_posix())
    if link_map_stale or primer_stale or summaries_stale:
        build_context_link_map(repo_root=REPO_ROOT, write=True)
        refreshed.append(link_map_path.as_posix())
    return refreshed


def main() -> int:
    try:
        ensure_memory_layout()
        removed = WorkingMemory.cleanup_expired(max_age_hours=24)
        latest = WorkingMemory.load_latest(max_age_hours=24)
        short_term = ShortTermMemory()
        day_summary = short_term.summarize_day()
        LongTermMemory().record_event("session_start", source="session-start-hook")
        current_sha = _git_sha()
        refreshed_docs = _refresh_context_docs(current_sha)
        append_event(
            create_event(
                event_type=EventType.SESSION_START,
                provider="codex",
                session_id=(latest or {}).get("session_id") or "session-codex-bootstrap",
                source="scripts/memory/session_start.py",
                scope={"phase": "16"},
                payload={
                    "expired_removed": removed,
                    "short_term_event_count": day_summary.get("count", 0),
                    "docs_refreshed": refreshed_docs,
                    "current_sha": current_sha,
                },
                provenance={"hook": "session_start"},
            ),
            fail_open=True,
        )
        _, sync_message = sync_agents_memory_section()

        print("[Memory] SessionStart bootstrap complete")
        if latest:
            task = (latest.get("context") or {}).get("current_task") or "N/A"
            print(f"[Memory] Restored working memory task: {task}")
        else:
            print("[Memory] No fresh working memory found")
        print(f"[Memory] Today's short-term events: {day_summary.get('count', 0)}")
        print(f"[Memory] Expired working sessions removed: {removed}")
        print(f"[Memory] Context docs refreshed: {len(refreshed_docs)}")
        print(f"[Memory] {sync_message}")
        return 0
    except Exception as exc:  # pragma: no cover - defensive best-effort hook
        print(f"[Memory] WARNING: SessionStart bootstrap failed: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
