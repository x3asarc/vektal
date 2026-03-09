"""Root-cause classification for autonomous remediation routing."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.assistant.session_primer import SessionPrimer
from src.core.memory_loader import MemoryLoader
from src.core.graphiti_client import get_graphiti_client

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
FAILURE_JOURNEY_PATH = REPO_ROOT / "FAILURE_JOURNEY.md"


class FailureCategory:
    INFRASTRUCTURE = "infrastructure"
    CODE = "code"
    CONFIG = "config"
    UNKNOWN = "unknown"

    @classmethod
    def all(cls) -> set[str]:
        return {cls.INFRASTRUCTURE, cls.CODE, cls.CONFIG, cls.UNKNOWN}


class LLMClientLike(Protocol):
    def complete(self, prompt: str, **kwargs: Any) -> str:  # pragma: no cover - protocol
        ...


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    evidence: dict[str, Any]

    def as_tuple(self) -> tuple[str, float, dict[str, Any]]:
        return self.category, self.confidence, self.evidence


class RootCauseClassifier:
    """
    3-tier failure classifier:
    1. Deterministic pattern matching
    2. Graph context analysis
    3. LLM fallback for novel failures
    """

    def __init__(
        self,
        graph_client: Any | None = None,
        session_primer: SessionPrimer | None = None,
        llm_client: LLMClientLike | Any | None = None,
        failure_journey_path: Path = FAILURE_JOURNEY_PATH,
    ) -> None:
        self.graph_client = graph_client if graph_client is not None else get_graphiti_client()
        self.session_primer = session_primer or SessionPrimer(MemoryLoader())
        self.llm_client = llm_client
        self.failure_journey_path = failure_journey_path
        self._journey_cache: tuple[float, str] | None = None

    def classify(
        self,
        error_type: str,
        error_message: str,
        traceback: str,
        affected_module: str,
    ) -> tuple[str, float, dict[str, Any]]:
        started = time.time()

        pattern = self._match_known_patterns(error_type, error_message, affected_module)
        if pattern.confidence >= 0.90:
            pattern.evidence["strategy"] = "pattern"
            pattern.evidence["elapsed_ms"] = round((time.time() - started) * 1000.0, 2)
            return pattern.as_tuple()

        graph = self._analyze_with_graph(
            error_type=error_type,
            error_message=error_message,
            affected_module=affected_module,
        )
        if graph.confidence >= 0.80:
            graph.evidence["strategy"] = "graph"
            graph.evidence["elapsed_ms"] = round((time.time() - started) * 1000.0, 2)
            return graph.as_tuple()

        journey = self._match_failure_journey(error_type, error_message, affected_module)
        if journey.confidence > max(pattern.confidence, graph.confidence):
            pattern = journey

        llm = self._classify_with_llm(
            error_type=error_type,
            error_message=error_message,
            traceback=traceback,
            affected_module=affected_module,
            prior_evidence={
                "pattern": pattern.evidence,
                "graph": graph.evidence,
                "journey": journey.evidence,
            },
        )
        llm.evidence["strategy"] = "llm"
        llm.evidence["elapsed_ms"] = round((time.time() - started) * 1000.0, 2)
        return llm.as_tuple()

    def _match_known_patterns(
        self,
        error_type: str,
        error_message: str,
        affected_module: str,
    ) -> ClassificationResult:
        error_type_l = (error_type or "").lower()
        error_message_l = (error_message or "").lower()
        module_l = (affected_module or "").lower()
        combined = f"{error_type_l} {error_message_l} {module_l}"

        pattern_table: list[tuple[str, tuple[str, ...], tuple[str, ...], float]] = [
            (
                FailureCategory.INFRASTRUCTURE,
                ("connectionerror", "operationalerror", "docker.errors", "socket.gaierror"),
                ("redis", "neo4j", "postgres", "docker", "connection refused", "timeout"),
                0.95,
            ),
            (
                FailureCategory.CODE,
                ("syntaxerror", "importerror", "modulenotfounderror"),
                ("traceback", "cannot import", "unexpected indent", "undefined"),
                0.97,
            ),
            (
                FailureCategory.CODE,
                ("attributeerror", "typeerror", "nameerror", "keyerror"),
                ("object has no attribute", "unsupported operand", "missing required"),
                0.88,
            ),
            (
                FailureCategory.CONFIG,
                ("timeouterror", "valueerror"),
                ("environment variable", "missing env", "pool size", "retry config", "rate limit"),
                0.86,
            ),
        ]

        for category, type_tokens, message_tokens, confidence in pattern_table:
            if any(token in error_type_l for token in type_tokens):
                if not message_tokens or any(token in combined for token in message_tokens):
                    return ClassificationResult(
                        category=category,
                        confidence=confidence,
                        evidence={
                            "pattern_error_type": next((t for t in type_tokens if t in error_type_l), ""),
                            "pattern_message_token": next((t for t in message_tokens if t in combined), ""),
                            "affected_module": affected_module,
                        },
                    )

        if "redis" in combined or "docker" in combined or "neo4j" in combined:
            return ClassificationResult(
                category=FailureCategory.INFRASTRUCTURE,
                confidence=0.84,
                evidence={"pattern_hint": "infra_keyword"},
            )

        return ClassificationResult(
            category=FailureCategory.UNKNOWN,
            confidence=0.0,
            evidence={"reason": "no_pattern_match"},
        )

    def _match_failure_journey(
        self,
        error_type: str,
        error_message: str,
        affected_module: str,
    ) -> ClassificationResult:
        text = self._load_failure_journey_text()
        if not text:
            return ClassificationResult(
                category=FailureCategory.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "failure_journey_unavailable"},
            )

        combined = f"{error_type} {error_message} {affected_module}".lower()
        keyword_map = {
            FailureCategory.INFRASTRUCTURE: ["redis", "docker", "aura", "neo4j", "connection refused"],
            FailureCategory.CODE: ["importerror", "syntax", "traceback", "module", "attributeerror"],
            FailureCategory.CONFIG: ["env", "pool", "timeout", "configuration", "rate limit"],
        }

        best_category = FailureCategory.UNKNOWN
        best_score = 0.0
        best_hit = ""
        lower_text = text.lower()
        for category, keywords in keyword_map.items():
            for keyword in keywords:
                if keyword in combined and keyword in lower_text:
                    score = 0.70 if category == FailureCategory.INFRASTRUCTURE else 0.66
                    if score > best_score:
                        best_category = category
                        best_score = score
                        best_hit = keyword

        if best_category == FailureCategory.UNKNOWN:
            return ClassificationResult(
                category=best_category,
                confidence=0.0,
                evidence={"reason": "no_historical_match"},
            )

        return ClassificationResult(
            category=best_category,
            confidence=best_score,
            evidence={"historical_keyword": best_hit},
        )

    def _analyze_with_graph(
        self,
        error_type: str,
        error_message: str,
        affected_module: str,
    ) -> ClassificationResult:
        if not self.graph_client:
            return ClassificationResult(
                category=FailureCategory.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "graph_unavailable"},
            )

        module_row = self._query_single(
            "MATCH (m:Module {path: $module_path}) "
            "RETURN m.path AS path, m.last_modified AS last_modified",
            {"module_path": affected_module},
        )

        if not module_row:
            if any(token in (affected_module or "").lower() for token in ("redis", "docker", "neo4j", "postgres")):
                return ClassificationResult(
                    category=FailureCategory.INFRASTRUCTURE,
                    confidence=0.76,
                    evidence={"reason": "module_missing_graph_infra_hint"},
                )
            return ClassificationResult(
                category=FailureCategory.UNKNOWN,
                confidence=0.35,
                evidence={"reason": "module_missing_graph"},
            )

        import_neighbors = self._safe_graph_query(
            "MATCH (f:File {path: $module_path})-[:IMPORTS]->(dep:File) "
            "RETURN dep.path AS dependency_path LIMIT 6",
            {"module_path": affected_module},
        )
        if not import_neighbors:
            # Fallback pattern for graph models that persist edge entities explicitly.
            # Required link coverage: MATCH ... ImportsEdge
            import_neighbors = self._safe_graph_query(
                "MATCH (e:ImportsEdge) "
                "WHERE e.source_path = $module_path "
                "RETURN e.target_path AS dependency_path LIMIT 6",
                {"module_path": affected_module},
            )

        calls_neighbors = self._safe_graph_query(
            "MATCH (caller:Function)-[:CALLS]->(callee:Function) "
            "WHERE caller.file_path = $module_path "
            "RETURN caller.full_name AS caller, callee.full_name AS callee LIMIT 6",
            {"module_path": affected_module},
        )
        if not calls_neighbors:
            # Required link coverage: MATCH ... CallsEdge
            calls_neighbors = self._safe_graph_query(
                "MATCH (e:CallsEdge) "
                "WHERE e.source_file = $module_path "
                "RETURN e.source AS caller, e.target AS callee LIMIT 6",
                {"module_path": affected_module},
            )

        recent_commits = self._safe_graph_query(
            "MATCH (m:Module {path: $module_path})<-[:MODIFIED]-(c:Commit) "
            "RETURN c.sha AS sha, c.message AS message, c.timestamp AS timestamp "
            "ORDER BY c.timestamp DESC LIMIT 3",
            {"module_path": affected_module},
        )

        error_type_l = (error_type or "").lower()
        error_message_l = (error_message or "").lower()
        import_problem = "importerror" in error_type_l or "modulenotfounderror" in error_type_l
        infra_problem = any(token in error_message_l for token in ("connection refused", "timeout", "unreachable"))
        config_problem = any(token in error_message_l for token in ("env", "configuration", "pool", "retry"))

        if import_problem and import_neighbors:
            return ClassificationResult(
                category=FailureCategory.CODE,
                confidence=0.86,
                evidence={
                    "reason": "import_graph_neighbors",
                    "dependencies": [row.get("dependency_path") for row in import_neighbors if row.get("dependency_path")],
                },
            )

        if recent_commits and ("attributeerror" in error_type_l or "typeerror" in error_type_l):
            return ClassificationResult(
                category=FailureCategory.CODE,
                confidence=0.82,
                evidence={
                    "reason": "recent_module_changes",
                    "commits": [str(row.get("sha", ""))[:7] for row in recent_commits if row.get("sha")],
                },
            )

        if infra_problem and (calls_neighbors or "redis" in affected_module.lower() or "docker" in affected_module.lower()):
            return ClassificationResult(
                category=FailureCategory.INFRASTRUCTURE,
                confidence=0.81,
                evidence={"reason": "infra_signal_with_graph_context"},
            )

        if config_problem:
            return ClassificationResult(
                category=FailureCategory.CONFIG,
                confidence=0.80,
                evidence={"reason": "config_tokens_in_error_message"},
            )

        return ClassificationResult(
            category=FailureCategory.UNKNOWN,
            confidence=0.30,
            evidence={
                "reason": "graph_inconclusive",
                "import_neighbors": len(import_neighbors),
                "calls_neighbors": len(calls_neighbors),
                "recent_commits": len(recent_commits),
            },
        )

    def _classify_with_llm(
        self,
        error_type: str,
        error_message: str,
        traceback: str,
        affected_module: str,
        prior_evidence: dict[str, Any],
    ) -> ClassificationResult:
        try:
            session_context = self.session_primer.load_session_context(
                failure_context=f"{error_type}: {error_message} in {affected_module}"
            )
        except Exception as exc:
            logger.debug("Session context unavailable for classifier: %s", exc)
            session_context = ""

        prompt = (
            "Classify this runtime failure into exactly one category:\n"
            "- infrastructure: redis/docker/network/database connectivity\n"
            "- code: syntax/import/type/attribute/runtime logic\n"
            "- config: env vars/timeouts/pool sizes/retries\n"
            "- unknown\n\n"
            f"Session Context (compressed YAML):\n{session_context}\n\n"
            f"Failure Type: {error_type}\n"
            f"Failure Message: {error_message}\n"
            f"Affected Module: {affected_module}\n"
            f"Traceback Tail:\n{self._truncate_traceback(traceback, last_n_lines=8)}\n\n"
            f"Prior Evidence: {json.dumps(prior_evidence, default=str)}\n\n"
            "Return JSON only:\n"
            '{"category":"infrastructure|code|config|unknown","confidence":0.0,"reasoning":"short"}'
        )

        try:
            raw_response = self._invoke_llm(prompt)
            parsed = self._parse_llm_json(raw_response)
            category = str(parsed.get("category", FailureCategory.UNKNOWN)).strip().lower()
            confidence = float(parsed.get("confidence", 0.0))
            if category not in FailureCategory.all():
                category = FailureCategory.UNKNOWN
            confidence = max(0.0, min(1.0, confidence))
            return ClassificationResult(
                category=category,
                confidence=confidence,
                evidence={
                    "reasoning": parsed.get("reasoning", ""),
                    "llm_used": True,
                },
            )
        except Exception as exc:
            logger.warning("LLM classification unavailable: %s", exc)
            return ClassificationResult(
                category=FailureCategory.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "llm_unavailable", "error": str(exc)},
            )

    def _invoke_llm(self, prompt: str) -> str:
        if self.llm_client is not None:
            if hasattr(self.llm_client, "complete"):
                return str(
                    self.llm_client.complete(
                        prompt=prompt,
                        model=os.getenv("ROOT_CAUSE_CLASSIFIER_MODEL", "google/gemini-2.0-flash-001"),
                        temperature=0.1,
                        max_tokens=200,
                    )
                )
            if hasattr(self.llm_client, "classify"):
                return str(self.llm_client.classify(prompt))

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing and no injected llm_client")

        import requests

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": os.getenv("ROOT_CAUSE_CLASSIFIER_MODEL", "google/gemini-2.0-flash-001"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 220,
            },
            timeout=4.5,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])

    def _parse_llm_json(self, raw: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling extra text after JSON."""
        text = (raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            # Try standard parsing first (fast path)
            return json.loads(text)
        except json.JSONDecodeError as e:
            # If "Extra data" error, try parsing just the first JSON object
            if "Extra data" in str(e):
                try:
                    decoder = json.JSONDecoder()
                    obj, idx = decoder.raw_decode(text)
                    # Log warning about extra text (for debugging)
                    extra = text[idx:].strip()
                    if extra:
                        print(f"Warning: LLM returned extra text after JSON: {extra[:100]}", file=sys.stderr)
                    return obj
                except (json.JSONDecodeError, ValueError):
                    pass  # Fall through to original error
            # Re-raise original error if we can't recover
            raise

    def _truncate_traceback(self, traceback: str, last_n_lines: int = 8) -> str:
        lines = (traceback or "").splitlines()
        if not lines:
            return ""
        return "\n".join(lines[-max(1, last_n_lines) :])

    def _load_failure_journey_text(self) -> str:
        now = time.time()
        if self._journey_cache and (now - self._journey_cache[0]) < 30.0:
            return self._journey_cache[1]
        try:
            text = self.failure_journey_path.read_text(encoding="utf-8")
            self._journey_cache = (now, text)
            return text
        except Exception:
            return ""

    def _query_single(self, query: str, params: dict[str, Any]) -> dict[str, Any] | None:
        rows = self._safe_graph_query(query, params)
        return rows[0] if rows else None

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
            with driver.session() as session:
                result = session.run(query, params)
                return [dict(row) for row in result]
        except Exception as exc:
            logger.debug("Graph query failed in classifier: %s", exc)
            return []
