"""Core working/short-term/long-term memory manager."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import uuid
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEMORY_ROOT = REPO_ROOT / ".memory"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "entry"


@dataclass(frozen=True)
class MemoryPaths:
    root: Path

    @property
    def events(self) -> Path:
        return self.root / "events"

    @property
    def working(self) -> Path:
        return self.root / "working"

    @property
    def short_term(self) -> Path:
        return self.root / "short-term"

    @property
    def long_term(self) -> Path:
        return self.root / "long-term"

    @property
    def long_term_index(self) -> Path:
        return self.long_term / "index.json"


def get_memory_paths(root: Path | None = None) -> MemoryPaths:
    env_root = os.getenv("AI_MEMORY_ROOT")
    resolved = root
    if resolved is None and env_root:
        resolved = Path(env_root).expanduser()
    if resolved is None:
        resolved = DEFAULT_MEMORY_ROOT
    return MemoryPaths(root=resolved.resolve())


def ensure_memory_layout(root: Path | None = None) -> MemoryPaths:
    paths = get_memory_paths(root=root)
    required_dirs = [
        paths.events,
        paths.working,
        paths.short_term,
        paths.long_term / "architecture" / "decisions",
        paths.long_term / "architecture" / "diagrams",
        paths.long_term / "architecture" / "evolution",
        paths.long_term / "patterns" / "success",
        paths.long_term / "patterns" / "anti-patterns",
        paths.long_term / "preferences",
    ]
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    if not paths.long_term_index.exists():
        initial = {
            "version": 1,
            "generated_from": ".planning/memory-system-design.md",
            "last_updated": _utc_now_iso(),
            "event_counters": {},
            "phase_summaries": [],
        }
        paths.long_term_index.write_text(json.dumps(initial, indent=2), encoding="utf-8")
    return paths


class WorkingMemory:
    """Session-scoped memory persisted as JSON files."""

    def __init__(
        self,
        *,
        root: Path | None = None,
        session_id: str | None = None,
        started_at: str | None = None,
    ) -> None:
        self.paths = ensure_memory_layout(root=root)
        self.session_id = session_id or f"session-{uuid.uuid4().hex[:8]}"
        self.started_at = started_at or _utc_now_iso()
        self.context: dict[str, Any] = {}
        self.recent_files: list[dict[str, Any]] = []
        self.recent_commands: list[dict[str, Any]] = []
        self.insights: list[str] = []
        self.next_steps: list[str] = []

    @property
    def file_path(self) -> Path:
        return self.paths.working / f"{self.session_id}.json"

    @classmethod
    def load_for_session(
        cls,
        session_id: str,
        *,
        root: Path | None = None,
    ) -> "WorkingMemory":
        memory = cls(root=root, session_id=session_id)
        file_path = memory.file_path
        if not file_path.exists():
            return memory
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return memory

        memory.started_at = str(payload.get("started_at") or memory.started_at)
        memory.context = dict(payload.get("context") or {})
        memory.recent_files = list(payload.get("recent_files") or [])
        memory.recent_commands = list(payload.get("recent_commands") or [])
        memory.insights = [str(item) for item in (payload.get("insights") or []) if str(item).strip()]
        memory.next_steps = [str(item) for item in (payload.get("next_steps") or []) if str(item).strip()]
        return memory

    def merge_context(self, payload: dict[str, Any] | None) -> None:
        if not payload:
            return
        self.context.update(payload)

    def update_context(self, key: str, value: Any) -> None:
        self.context[str(key)] = value

    def track_file(self, path: str, action: str) -> None:
        self.recent_files.append(
            {
                "path": path,
                "action": action,
                "timestamp": _utc_now_iso(),
            }
        )

    def track_command(
        self,
        command: str,
        *,
        success: bool | None = True,
        exit_code: int | None = None,
        stage: str | None = None,
    ) -> None:
        item: dict[str, Any] = {
            "cmd": command,
            "timestamp": _utc_now_iso(),
        }
        if success is not None:
            item["success"] = bool(success)
        if exit_code is not None:
            item["exit_code"] = int(exit_code)
        if stage:
            item["stage"] = str(stage)
        self.recent_commands.append(item)

    def add_insight(self, value: str) -> None:
        if value.strip():
            self.insights.append(value.strip())

    def add_next_step(self, value: str) -> None:
        if value.strip():
            self.next_steps.append(value.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "updated_at": _utc_now_iso(),
            "context": self.context,
            "recent_files": self.recent_files[-200:],
            "recent_commands": self.recent_commands[-200:],
            "insights": self.insights[-200:],
            "next_steps": self.next_steps[-200:],
        }

    def save(self) -> Path:
        payload = self.to_dict()
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.file_path

    @classmethod
    def load_latest(cls, *, root: Path | None = None, max_age_hours: int = 24) -> dict[str, Any] | None:
        paths = ensure_memory_layout(root=root)
        sessions = sorted(paths.working.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not sessions:
            return None
        latest = sessions[0]
        age = _utc_now() - datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc)
        if age > timedelta(hours=max_age_hours):
            return None
        try:
            return json.loads(latest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    @classmethod
    def cleanup_expired(cls, *, root: Path | None = None, max_age_hours: int = 24) -> int:
        paths = ensure_memory_layout(root=root)
        cutoff = _utc_now() - timedelta(hours=max_age_hours)
        removed = 0
        for item in paths.working.glob("*.json"):
            modified = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                item.unlink(missing_ok=True)
                removed += 1
        return removed


class ShortTermMemory:
    """Task/day scoped append-only memory in JSONL format."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.paths = ensure_memory_layout(root=root)

    def _daily_file(self, day: datetime | None = None) -> Path:
        point = day or _utc_now()
        return self.paths.short_term / f"{point.strftime('%Y-%m-%d')}.jsonl"

    def append_event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = {"timestamp": _utc_now_iso(), "type": event_type}
        if payload:
            entry.update(payload)
        target = self._daily_file()
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
        return entry

    def query(
        self,
        *,
        event_type: str | None = None,
        last_n_days: int = 7,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        cutoff = _utc_now().date() - timedelta(days=max(0, last_n_days))
        rows: list[dict[str, Any]] = []
        files = sorted(self.paths.short_term.glob("*.jsonl"), reverse=True)
        for file in files:
            try:
                file_day = datetime.strptime(file.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if file_day < cutoff:
                continue
            for line in file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event_type and row.get("type") != event_type:
                    continue
                rows.append(row)
                if len(rows) >= limit:
                    return rows
        return rows

    def summarize_day(self, *, day: datetime | None = None) -> dict[str, Any]:
        target = self._daily_file(day=day)
        if not target.exists():
            return {"date": target.stem, "count": 0, "types": {}}
        counts: dict[str, int] = {}
        total = 0
        for line in target.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = str(row.get("type") or "unknown")
            counts[event_type] = counts.get(event_type, 0) + 1
            total += 1
        return {"date": target.stem, "count": total, "types": counts}

    def prune_older_than(self, *, days_to_keep: int = 30) -> int:
        cutoff = _utc_now().date() - timedelta(days=max(0, days_to_keep))
        removed = 0
        for item in self.paths.short_term.glob("*.jsonl"):
            try:
                file_day = datetime.strptime(item.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if file_day < cutoff:
                item.unlink(missing_ok=True)
                removed += 1
        return removed


class LongTermMemory:
    """Project lifetime memory persisted in markdown and JSON index files."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.paths = ensure_memory_layout(root=root)

    def load_index(self) -> dict[str, Any]:
        try:
            return json.loads(self.paths.long_term_index.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            ensure_memory_layout(root=self.paths.root)
            return json.loads(self.paths.long_term_index.read_text(encoding="utf-8"))

    def save_index(self, index_payload: dict[str, Any]) -> None:
        payload = dict(index_payload)
        payload["last_updated"] = _utc_now_iso()
        self.paths.long_term_index.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def record_event(self, event_type: str, *, source: str = "memory-hook") -> dict[str, Any]:
        index = self.load_index()
        counters = index.setdefault("event_counters", {})
        counters[event_type] = int(counters.get(event_type, 0)) + 1
        index["last_event"] = {"type": event_type, "source": source, "timestamp": _utc_now_iso()}
        self.save_index(index)
        return index

    def append_pattern(self, *, title: str, summary: str, anti_pattern: bool = False) -> Path:
        bucket = "anti-patterns" if anti_pattern else "success"
        slug = _slugify(title)
        file_path = self.paths.long_term / "patterns" / bucket / f"{slug}.md"
        content = "\n".join(
            [
                f"# {title}",
                "",
                f"Recorded: {_utc_now_iso()}",
                "",
                summary.strip(),
                "",
            ]
        )
        file_path.write_text(content, encoding="utf-8")
        self.record_event("pattern_recorded", source=f"long-term/{bucket}")
        return file_path

    def write_phase_evolution(self, *, phase_name: str, summary: str, highlights: list[str] | None = None) -> Path:
        slug = _slugify(f"phase-{phase_name}")
        file_path = self.paths.long_term / "architecture" / "evolution" / f"{slug}.md"
        lines = [
            f"# Phase {phase_name} Evolution",
            "",
            f"Updated: {_utc_now_iso()}",
            "",
            "## Summary",
            summary.strip() or "N/A",
            "",
            "## Highlights",
        ]
        for item in highlights or []:
            lines.append(f"- {item}")
        if not highlights:
            lines.append("- N/A")
        lines.append("")
        file_path.write_text("\n".join(lines), encoding="utf-8")

        index = self.load_index()
        phase_summaries = index.setdefault("phase_summaries", [])
        phase_summaries.append(
            {
                "phase": str(phase_name),
                "path": file_path.relative_to(self.paths.root).as_posix(),
                "updated_at": _utc_now_iso(),
            }
        )
        self.save_index(index)
        return file_path
