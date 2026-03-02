"""Session primer: compact YAML/JSON context for autonomous remediation prompts."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

import yaml

from src.core.memory_loader import MemoryLoader, get_memory_loader


class RemedyLike(Protocol):
    fingerprint: str
    description: str | None
    confidence: Any
    application_count: int


@dataclass
class PrimerStats:
    load_ms: float
    source: str
    estimated_tokens: int
    raw_chars: int
    compressed_chars: int


class SessionPrimer:
    """Loads and compresses session context for LLM consumption."""

    def __init__(self, memory_loader: MemoryLoader | None = None) -> None:
        self.memory_loader = memory_loader or get_memory_loader()
        self._cache: dict[str, tuple[float, str, PrimerStats]] = {}
        self._ttl_seconds = 120
        self.last_stats = PrimerStats(
            load_ms=0.0,
            source="cold",
            estimated_tokens=0,
            raw_chars=0,
            compressed_chars=0,
        )

    def load_session_context(self, failure_context: str | None = None) -> str:
        """
        Load compressed session context as YAML string.

        Target: <1200 tokens for default context packet.
        """
        key = f"ctx:{(failure_context or '').strip().lower()}"
        now = time.time()
        cached = self._cache.get(key)
        if cached and (now - cached[0]) < self._ttl_seconds:
            cached_stats = cached[2]
            self.last_stats = PrimerStats(
                load_ms=0.0,
                source="cache",
                estimated_tokens=cached_stats.estimated_tokens,
                raw_chars=cached_stats.raw_chars,
                compressed_chars=cached_stats.compressed_chars,
            )
            return cached[1]

        start = time.time()

        commits = self.memory_loader.load_recent_commits(limit=5)
        phase_context = self.memory_loader.load_current_phase()
        roadmap = self.memory_loader.load_roadmap_summary()

        remedies: list[RemedyLike] = []
        if failure_context:
            remedies = self.memory_loader.load_relevant_remedies(
                failure_context=failure_context,
                limit=5,
            )

        compressed_data = {
            "session": phase_context,
            "recent_commits": self._compress_commits(commits),
            "roadmap_context": self._compress_roadmap(roadmap),
            "relevant_remedies": self._compress_remedies(remedies),
        }
        yaml_context = self._compress_to_yaml(compressed_data)

        raw_chars = len(str(commits)) + len(str(phase_context)) + len(str(roadmap)) + len(str(remedies))
        compressed_chars = len(yaml_context)
        estimated_tokens = max(1, compressed_chars // 4)
        load_ms = round((time.time() - start) * 1000.0, 2)

        stats = PrimerStats(
            load_ms=load_ms,
            source="cold",
            estimated_tokens=estimated_tokens,
            raw_chars=raw_chars,
            compressed_chars=compressed_chars,
        )
        self.last_stats = stats
        self._cache[key] = (time.time(), yaml_context, stats)
        return yaml_context

    def load_session_packet(self, failure_context: str | None = None) -> dict[str, Any]:
        """Return parsed packet + stats for programmatic users."""
        yaml_str = self.load_session_context(failure_context=failure_context)
        packet = yaml.safe_load(yaml_str) or {}
        return {
            "yaml": yaml_str,
            "data": packet,
            "stats": {
                "load_ms": self.last_stats.load_ms,
                "source": self.last_stats.source,
                "estimated_tokens": self.last_stats.estimated_tokens,
                "raw_chars": self.last_stats.raw_chars,
                "compressed_chars": self.last_stats.compressed_chars,
            },
        }

    def _compress_commits(self, commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compress commit data: hash, message, files, impact."""
        output: list[dict[str, Any]] = []
        for commit in commits[:5]:
            files = [self._basename(path) for path in (commit.get("changed_files") or [])[:3]]
            output.append(
                {
                    "hash": str(commit.get("sha", ""))[:7],
                    "msg": self._truncate(str(commit.get("message", "")), 60),
                    "files": files,
                    "impact": self._infer_impact_area(commit.get("changed_files") or []),
                }
            )
        return output

    def _compress_roadmap(self, roadmap: dict[str, Any]) -> dict[str, Any]:
        return {
            "milestone": roadmap.get("current_milestone"),
            "current_phase": roadmap.get("current_phase"),
            "goal": self._truncate(str(roadmap.get("goal", "")), 80),
            "completed": (roadmap.get("phases_complete") or [])[:20],
            "next": roadmap.get("next_phase"),
        }

    def _compress_remedies(self, remedies: list[RemedyLike]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for remedy in remedies[:5]:
            confidence = 0.0
            try:
                confidence = float(remedy.confidence or 0.0)
            except Exception:
                confidence = 0.0
            output.append(
                {
                    "fp": self._truncate(str(remedy.fingerprint or ""), 80),
                    "fix": self._truncate(str(remedy.description or ""), 50),
                    "conf": round(confidence, 2),
                    "apps": int(remedy.application_count or 0),
                }
            )
        return output

    def _compress_to_yaml(self, data: dict[str, Any]) -> str:
        return yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            width=80,
            allow_unicode=False,
        )

    def _truncate(self, text: str, max_len: int) -> str:
        return text[:max_len] + "..." if len(text) > max_len else text

    def _basename(self, path: str) -> str:
        normalized = str(path).replace("\\", "/")
        return normalized.split("/")[-1] if normalized else normalized

    def _infer_impact_area(self, files: list[str]) -> str:
        normalized = [str(path).lower() for path in files]
        if any("graph" in path for path in normalized):
            return "graph"
        if any("/api/" in path or path.startswith("api/") for path in normalized):
            return "api"
        if any("model" in path for path in normalized):
            return "database"
        if any("governance" in path for path in normalized):
            return "governance"
        return "core"


def build_session_context(failure_context: str | None = None) -> str:
    """Convenience helper used by scripts and hooks."""
    return SessionPrimer().load_session_context(failure_context=failure_context)
