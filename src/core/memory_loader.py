"""Session memory loader for commits, roadmap context, and remedy templates."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.core.graphiti_client import get_graphiti_client
from src.models.remedy_templates import RemedyTemplate

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = REPO_ROOT / ".planning/STATE.md"
ROADMAP_PATH = REPO_ROOT / ".planning/ROADMAP.md"
CACHE_TTL_SECONDS = 300


class MemoryLoader:
    """Loads session context from graph first, with resilient local fallbacks."""

    def __init__(self) -> None:
        self.graph_client = get_graphiti_client()
        self._cache: dict[str, tuple[float, Any]] = {}

    def _get_cached(self, key: str) -> Any:
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, value = entry
        if (time.time() - ts) > CACHE_TTL_SECONDS:
            self._cache.pop(key, None)
            return None
        return value

    def _set_cached(self, key: str, value: Any) -> Any:
        self._cache[key] = (time.time(), value)
        return value

    def load_recent_commits(self, limit: int = 5) -> list[dict[str, Any]]:
        """Load recent git commits from graph, falling back to local git log."""
        key = f"recent_commits:{int(limit)}"
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        records = self._load_recent_commits_from_graph(limit=limit)
        if not records:
            records = self._fallback_git_log(limit=limit)
        return self._set_cached(key, records)

    def load_current_phase(self) -> dict[str, Any]:
        """Parse phase/plan context from STATE.md."""
        cached = self._get_cached("current_phase")
        if cached is not None:
            return cached

        current_phase = "15"
        current_plan = None
        try:
            content = STATE_PATH.read_text(encoding="utf-8")
            phase_match = re.search(r"Phase\s+(\d+(?:\.\d+)?)", content)
            if phase_match:
                current_phase = phase_match.group(1)
            plan_match = re.search(r"(?:Current\s+Task|Current\s+Plan):\s*([^\n]+)", content)
            if plan_match:
                current_plan = plan_match.group(1).strip()
        except Exception as exc:
            logger.debug("STATE parsing fallback used: %s", exc)

        return self._set_cached(
            "current_phase",
            {
                "current_phase": current_phase,
                "current_plan": current_plan,
            },
        )

    def load_roadmap_summary(self) -> dict[str, Any]:
        """Extract compact roadmap summary for prompt priming."""
        cached = self._get_cached("roadmap_summary")
        if cached is not None:
            return cached

        milestone = "M3: Self-Healing"
        goal = "Autonomous remediation + performance optimization"
        current_phase = self.load_current_phase().get("current_phase", "15")
        next_phase = None
        completed: list[str] = []

        try:
            text = ROADMAP_PATH.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.strip().startswith("- [x] **Phase"):
                    phase_match = re.search(r"Phase\s+([0-9]+(?:\.[0-9]+)?)", line)
                    if phase_match:
                        completed.append(phase_match.group(1))
                if line.strip().startswith("- [ ] **Phase"):
                    phase_match = re.search(r"Phase\s+([0-9]+(?:\.[0-9]+)?)", line)
                    if phase_match:
                        if phase_match.group(1) != str(current_phase):
                            next_phase = phase_match.group(1)
                            break
            goal_match = re.search(
                rf"### Phase\s+{re.escape(str(current_phase))}:[\s\S]*?\*\*Goal\*\*:\s*(.+)",
                text,
            )
            if goal_match:
                goal = goal_match.group(1).strip()
        except Exception as exc:
            logger.debug("Roadmap parsing fallback used: %s", exc)

        return self._set_cached(
            "roadmap_summary",
            {
                "current_milestone": milestone,
                "current_phase": current_phase,
                "goal": goal,
                "phases_complete": completed[:20],
                "next_phase": next_phase,
            },
        )

    def load_relevant_remedies(self, failure_context: str, limit: int = 5) -> list[RemedyTemplate]:
        """
        Load relevant remedies from PostgreSQL cache first; fallback to graph query.
        """
        context = (failure_context or "").strip()
        if not context:
            return []

        key = f"remedies:{context.lower()}:{int(limit)}"
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        try:
            rows = RemedyTemplate.query_relevant(context, limit=limit)
            if rows:
                return self._set_cached(key, rows)
        except Exception as exc:
            logger.debug("Remedy cache lookup skipped (db unavailable): %s", exc)

        records = self._query_remedies_from_graph(context=context, limit=limit)
        templates: list[RemedyTemplate] = []
        for record in records:
            template = RemedyTemplate.from_graph_result(record)
            if not template.template_id:
                continue
            templates.append(template)
            try:
                existing = RemedyTemplate.query.filter_by(template_id=template.template_id).first()
                if existing is None:
                    existing = template
                else:
                    existing.fingerprint = template.fingerprint
                    existing.description = template.description
                    existing.remedy_payload = template.remedy_payload
                    existing.confidence = template.confidence
                    existing.application_count = template.application_count
                    existing.success_count = template.success_count
                    existing.affected_files_json = template.affected_files_json
                    existing.source_commit_sha = template.source_commit_sha
                    existing.last_applied_at = template.last_applied_at
                    existing.expires_at = template.expires_at
                existing.cache_refresh()
            except Exception as exc:
                logger.debug("Remedy cache upsert skipped (db unavailable): %s", exc)

        return self._set_cached(key, templates[: max(1, int(limit))])

    def _load_recent_commits_from_graph(self, limit: int) -> list[dict[str, Any]]:
        query = (
            "MATCH (c:Commit) "
            "RETURN c.sha AS sha, c.message AS message, c.timestamp AS timestamp, "
            "c.changed_files AS changed_files "
            "ORDER BY c.timestamp DESC LIMIT $limit"
        )
        records = self._safe_graph_query(query, {"limit": int(limit)})
        return [self._normalize_commit_record(row) for row in records]

    def _query_remedies_from_graph(self, *, context: str, limit: int) -> list[dict[str, Any]]:
        query = (
            "MATCH (t:RemedyTemplate) "
            "WHERE toLower(t.fingerprint) CONTAINS toLower($context) "
            "OR toLower(t.description) CONTAINS toLower($context) "
            "RETURN t.template_id AS template_id, t.fingerprint AS fingerprint, "
            "t.description AS description, t.remedy_payload AS remedy_payload, "
            "t.confidence AS confidence, t.application_count AS application_count, "
            "t.success_count AS success_count, t.affected_files_json AS affected_files_json, "
            "t.source_commit_sha AS source_commit_sha, t.last_applied_at AS last_applied_at, "
            "t.expires_at AS expires_at "
            "ORDER BY t.application_count DESC, t.confidence DESC LIMIT $limit"
        )
        records = self._safe_graph_query(query, {"context": context, "limit": int(limit)})
        return [dict(row) for row in records]

    def _safe_graph_query(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        client = self.graph_client
        if client is None:
            return []

        try:
            if hasattr(client, "execute_query"):
                rows = client.execute_query(query, params)  # type: ignore[attr-defined]
                return [dict(row) for row in rows] if rows else []
            driver = getattr(client, "driver", None)
            if driver is None:
                return []

            def _run_sync() -> list[dict[str, Any]]:
                with driver.session() as session:
                    result = session.run(query, params)
                    return [dict(record) for record in result]

            return _run_sync()
        except Exception as exc:
            logger.debug("Graph query fallback used: %s", exc)
            return []

    def _fallback_git_log(self, limit: int) -> list[dict[str, Any]]:
        """Fallback to local git log when graph is unavailable."""
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-{int(limit)}",
                    "--pretty=format:%H|%s|%ct",
                    "--name-only",
                ],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                check=False,
            )
            commits: list[dict[str, Any]] = []
            for block in result.stdout.split("\n\n"):
                block = block.strip()
                if not block:
                    continue
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                if not lines:
                    continue
                header = lines[0].split("|", maxsplit=2)
                if len(header) != 3:
                    continue
                sha, message, ts = header
                commits.append(
                    {
                        "sha": sha,
                        "message": message,
                        "timestamp": datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(),
                        "changed_files": lines[1:],
                    }
                )
            return commits
        except Exception as exc:
            logger.debug("git log fallback failed: %s", exc)
            return []

    def _normalize_commit_record(self, row: dict[str, Any]) -> dict[str, Any]:
        ts = row.get("timestamp")
        if isinstance(ts, datetime):
            timestamp = ts.isoformat()
        else:
            timestamp = str(ts) if ts is not None else ""
        changed_files = row.get("changed_files") or []
        if isinstance(changed_files, str):
            try:
                changed_files = json.loads(changed_files)
            except Exception:
                changed_files = [changed_files]
        if not isinstance(changed_files, list):
            changed_files = []
        return {
            "sha": str(row.get("sha") or ""),
            "message": str(row.get("message") or ""),
            "timestamp": timestamp,
            "changed_files": [str(path) for path in changed_files[:20]],
        }


@lru_cache(maxsize=1)
def get_memory_loader() -> MemoryLoader:
    return MemoryLoader()


def load_recent_commits(limit: int = 5) -> list[dict[str, Any]]:
    return get_memory_loader().load_recent_commits(limit=limit)


def load_relevant_remedies(failure_context: str, limit: int = 5) -> list[RemedyTemplate]:
    return get_memory_loader().load_relevant_remedies(
        failure_context=failure_context,
        limit=limit,
    )
