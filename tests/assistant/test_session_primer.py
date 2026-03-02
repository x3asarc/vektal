from __future__ import annotations

from dataclasses import dataclass

import yaml

from src.assistant.session_primer import SessionPrimer


@dataclass
class FakeRemedy:
    fingerprint: str
    description: str
    confidence: float
    application_count: int


class FakeMemoryLoader:
    def __init__(self) -> None:
        self.calls = {"commits": 0, "phase": 0, "roadmap": 0, "remedies": 0}

    def load_recent_commits(self, limit: int = 5):
        self.calls["commits"] += 1
        return [
            {
                "sha": "1234567890abcdef",
                "message": "feat(graph): add runtime fallback and compact snapshot support",
                "timestamp": "2026-03-02T10:00:00Z",
                "changed_files": [
                    "src/graph/backend_resolver.py",
                    "src/graph/mcp_server.py",
                    "tests/graph/test_backend_resolver.py",
                ],
            }
        ][:limit]

    def load_current_phase(self):
        self.calls["phase"] += 1
        return {"current_phase": "15", "current_plan": "15-02"}

    def load_roadmap_summary(self):
        self.calls["roadmap"] += 1
        return {
            "current_milestone": "M3: Self-Healing",
            "current_phase": "15",
            "goal": "Autonomous remediation + performance optimization loops",
            "phases_complete": ["1", "2", "3"],
            "next_phase": "16",
        }

    def load_relevant_remedies(self, failure_context: str, limit: int = 5):
        self.calls["remedies"] += 1
        if not failure_context:
            return []
        return [
            FakeRemedy(
                fingerprint="src/tasks/enrichment.py:TimeoutError",
                description="Increase timeout from 30 to 60 seconds and retry once",
                confidence=0.92,
                application_count=7,
            )
        ][:limit]


def test_session_primer_yaml_structure() -> None:
    primer = SessionPrimer(FakeMemoryLoader())
    text = primer.load_session_context(failure_context="TimeoutError")
    data = yaml.safe_load(text)
    assert "session" in data
    assert "recent_commits" in data
    assert "roadmap_context" in data
    assert "relevant_remedies" in data
    assert data["session"]["current_phase"] == "15"
    assert len(data["recent_commits"]) == 1
    assert len(data["relevant_remedies"]) == 1


def test_session_primer_token_budget_target() -> None:
    primer = SessionPrimer(FakeMemoryLoader())
    text = primer.load_session_context(failure_context="TimeoutError")
    token_estimate = len(text) / 4
    assert token_estimate < 1200


def test_session_primer_cache_prevents_redundant_loader_calls() -> None:
    loader = FakeMemoryLoader()
    primer = SessionPrimer(loader)
    first = primer.load_session_context(failure_context="TimeoutError")
    second = primer.load_session_context(failure_context="TimeoutError")
    assert first == second
    assert loader.calls["commits"] == 1
    assert loader.calls["remedies"] == 1


def test_session_primer_reports_cache_source_on_second_read() -> None:
    primer = SessionPrimer(FakeMemoryLoader())
    first = primer.load_session_packet(failure_context="TimeoutError")
    second = primer.load_session_packet(failure_context="TimeoutError")
    assert first["stats"]["source"] == "cold"
    assert second["stats"]["source"] == "cache"


def test_session_primer_lazy_remedy_loading() -> None:
    loader = FakeMemoryLoader()
    primer = SessionPrimer(loader)
    text = primer.load_session_context(failure_context=None)
    data = yaml.safe_load(text)
    assert data["relevant_remedies"] == []
    assert loader.calls["remedies"] == 0


def test_session_primer_compression_of_commit_fields() -> None:
    primer = SessionPrimer(FakeMemoryLoader())
    data = yaml.safe_load(primer.load_session_context("TimeoutError"))
    commit = data["recent_commits"][0]
    assert commit["hash"] == "1234567"
    assert len(commit["files"]) <= 3
    assert commit["impact"] == "graph"
