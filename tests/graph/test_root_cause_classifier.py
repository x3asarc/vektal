from __future__ import annotations

import asyncio
from pathlib import Path
import shutil
import uuid

from src.graph.orchestrate_healers import orchestrate_remediation
from src.graph.root_cause_classifier import RootCauseClassifier, FailureCategory
from src.graph.universal_fixer import RemediationResult


class FakePrimer:
    def load_session_context(self, failure_context: str | None = None) -> str:  # noqa: ARG002
        return "session:\n  current_phase: '15'\n"


class GraphImportClient:
    def execute_query(self, query: str, params: dict):  # noqa: ARG002
        if "MATCH (m:Module" in query:
            return [{"path": "src/tasks/enrichment.py", "last_modified": "2026-03-02"}]
        if "[:IMPORTS]" in query or "ImportsEdge" in query:
            return [{"dependency_path": "src/core/missing_dep.py"}]
        if "[:CALLS]" in query or "CallsEdge" in query:
            return []
        if "[:MODIFIED]" in query:
            return []
        return []


class GraphInconclusiveClient:
    def execute_query(self, query: str, params: dict):  # noqa: ARG002
        if "MATCH (m:Module" in query:
            return [{"path": "src/tasks/enrichment.py", "last_modified": "2026-03-02"}]
        return []


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response

    def complete(self, prompt: str, **kwargs):  # noqa: ARG002
        return self.response


def test_pattern_matching_routes_redis_to_infrastructure() -> None:
    classifier = RootCauseClassifier(
        graph_client=None,
        session_primer=FakePrimer(),
        llm_client=None,
    )
    category, confidence, evidence = classifier.classify(
        error_type="ConnectionError",
        error_message="redis connection refused",
        traceback="",
        affected_module="src/core/redis_client.py",
    )
    assert category == FailureCategory.INFRASTRUCTURE
    assert confidence >= 0.9
    assert evidence["strategy"] == "pattern"


def test_pattern_matching_routes_syntax_to_code() -> None:
    classifier = RootCauseClassifier(
        graph_client=None,
        session_primer=FakePrimer(),
        llm_client=None,
    )
    category, confidence, _ = classifier.classify(
        error_type="SyntaxError",
        error_message="unexpected indent",
        traceback="",
        affected_module="src/core/parser.py",
    )
    assert category == FailureCategory.CODE
    assert confidence >= 0.9


def test_graph_analysis_routes_import_failures_to_code() -> None:
    classifier = RootCauseClassifier(
        graph_client=GraphImportClient(),
        session_primer=FakePrimer(),
        llm_client=None,
    )
    category, confidence, evidence = classifier.classify(
        error_type="ModuleNotFoundError",
        error_message="dependency missing",
        traceback="",
        affected_module="src/tasks/enrichment.py",
    )
    assert category == FailureCategory.CODE
    assert confidence >= 0.8
    assert evidence["strategy"] == "graph"
    assert evidence["reason"] == "import_graph_neighbors"


def test_llm_fallback_classifies_novel_failure() -> None:
    classifier = RootCauseClassifier(
        graph_client=GraphInconclusiveClient(),
        session_primer=FakePrimer(),
        llm_client=FakeLLM('{"category":"config","confidence":0.74,"reasoning":"timeout and pool hints"}'),
    )
    category, confidence, evidence = classifier.classify(
        error_type="UnexpectedRuntimeFailure",
        error_message="opaque branch panic during startup",
        traceback="line 1\nline 2\nline 3",
        affected_module="src/worker/runner.py",
    )
    assert category == FailureCategory.CONFIG
    assert 0.7 <= confidence <= 1.0
    assert evidence["strategy"] == "llm"


def test_llm_unavailable_falls_back_to_unknown() -> None:
    classifier = RootCauseClassifier(
        graph_client=GraphInconclusiveClient(),
        session_primer=FakePrimer(),
        llm_client=FakeLLM("not-json"),
    )
    category, confidence, evidence = classifier.classify(
        error_type="UnexpectedRuntimeFailure",
        error_message="something odd happened",
        traceback="",
        affected_module="src/worker/runner.py",
    )
    assert category == FailureCategory.UNKNOWN
    assert confidence == 0.0
    assert evidence["strategy"] == "llm"


class FixedClassifier:
    def __init__(self, category: str, confidence: float = 0.9) -> None:
        self.category = category
        self.confidence = confidence

    def classify(self, error_type: str, error_message: str, traceback: str, affected_module: str):  # noqa: ARG002
        return self.category, self.confidence, {"source": "test"}


class FakeFixer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def fix_service(self, service_name: str, params: dict | None = None) -> RemediationResult:
        self.calls.append((service_name, params or {}))
        return RemediationResult(success=True, message="ok", actions_taken=["test"])


def _local_tmp_dir() -> Path:
    base = Path(".pytest_tmp_work")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"root-cause-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_orchestrator_dispatches_to_expected_remediator(monkeypatch) -> None:
    work = _local_tmp_dir()
    monkeypatch.setattr("src.graph.orchestrate_healers.OUTCOME_LOG_PATH", work / "outcomes.jsonl")
    fixer = FakeFixer()
    try:
        result = asyncio.run(
            orchestrate_remediation(
                {
                    "id": "issue-1",
                    "error_type": "ConnectionError",
                    "error_message": "redis connection refused",
                    "affected_module": "src/core/redis_client.py",
                    "traceback": "",
                },
                classifier=FixedClassifier(FailureCategory.INFRASTRUCTURE),
                fixer=fixer,
            )
        )
        assert result["status"] == "remediated"
        assert fixer.calls
        service, params = fixer.calls[0]
        assert service == "redis"
        assert "classification_evidence" in params
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_orchestrator_returns_manual_required_for_unknown(monkeypatch) -> None:
    work = _local_tmp_dir()
    monkeypatch.setattr("src.graph.orchestrate_healers.OUTCOME_LOG_PATH", work / "outcomes.jsonl")
    try:
        result = asyncio.run(
            orchestrate_remediation(
                {"id": "issue-2", "error_type": "NovelError", "error_message": "weird failure", "traceback": ""},
                classifier=FixedClassifier(FailureCategory.UNKNOWN, confidence=0.2),
            )
        )
        assert result["status"] == "manual_required"
        assert result["category"] == FailureCategory.UNKNOWN
    finally:
        shutil.rmtree(work, ignore_errors=True)
