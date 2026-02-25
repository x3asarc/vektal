"""
Unit tests for query template execution paths.
"""

from unittest.mock import patch

import pytest

from src.graph.query_templates import execute_template


class _Record:
    def __init__(self, payload):
        self._payload = payload

    def data(self):
        return self._payload


class _Eager:
    def __init__(self, rows):
        self.records = [_Record(row) for row in rows]


def test_execute_template_sync_driver_path():
    class SyncDriver:
        def execute_query(self, cypher, parameters_=None):
            assert "MATCH" in cypher
            assert parameters_ == {"file_path": "src/a.py"}
            return _Eager([{"path": "src/b.py"}])

    class Client:
        driver = SyncDriver()

    with patch("src.graph.query_templates._runtime_backend_mode", return_value=""):
        with patch("src.graph.query_templates.get_graphiti_client", return_value=Client()):
            rows = execute_template("imports", {"file_path": "src/a.py"})
            assert rows == [{"path": "src/b.py"}]


@pytest.mark.asyncio
async def test_execute_template_async_driver_inside_running_loop():
    class AsyncDriver:
        async def execute_query(self, cypher, parameters_=None):
            assert "MATCH" in cypher
            assert parameters_ == {"file_path": "src/a.py"}
            return _Eager([{"path": "src/c.py"}])

    class Client:
        driver = AsyncDriver()

    with patch("src.graph.query_templates.get_graphiti_client", return_value=Client()):
        rows = execute_template("imports", {"file_path": "src/a.py"})
        assert rows == [{"path": "src/c.py"}]


def test_execute_template_session_fallback_when_execute_query_unavailable():
    class Cursor:
        def __iter__(self):
            return iter([_Record({"path": "src/d.py"})])

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def run(self, cypher, params):
            assert "MATCH" in cypher
            assert params == {"file_path": "src/a.py"}
            return Cursor()

    class Driver:
        def session(self):
            return Session()

    class Client:
        driver = Driver()

    with patch("src.graph.query_templates._runtime_backend_mode", return_value=""):
        with patch("src.graph.query_templates.get_graphiti_client", return_value=Client()):
            rows = execute_template("imports", {"file_path": "src/a.py"})
            assert rows == [{"path": "src/d.py"}]


def test_execute_template_returns_empty_for_missing_client():
    with patch("src.graph.query_templates.get_graphiti_client", return_value=None):
        rows = execute_template("imports", {"file_path": "src/a.py"})
        assert rows == []


def test_execute_template_uses_filesystem_fallback_for_imports(monkeypatch):
    monkeypatch.setenv("GRAPH_TEMPLATE_PREFER_SYNC", "true")
    monkeypatch.setenv("GRAPH_ORACLE_ENABLED", "true")
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:1")
    monkeypatch.setenv("NEO4J_URI_FALLBACKS", "")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "sandbox")
    monkeypatch.setenv("NEO4J_CONNECT_TIMEOUT_SECONDS", "0.1")

    with patch("src.graph.query_templates.get_graphiti_client", return_value=None):
        rows = execute_template("imports", {"file_path": "src/graph/query_interface.py"})
        paths = {item.get("path") for item in rows}
        assert "src/graph/query_templates.py" in paths


def test_execute_template_uses_local_snapshot_for_functions(monkeypatch):
    monkeypatch.setenv("GRAPH_TEMPLATE_PREFER_SYNC", "true")
    monkeypatch.setenv("GRAPH_ORACLE_ENABLED", "true")
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:1")
    monkeypatch.setenv("NEO4J_URI_FALLBACKS", "")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "sandbox")
    monkeypatch.setenv("NEO4J_CONNECT_TIMEOUT_SECONDS", "0.1")

    with patch("src.graph.query_templates.get_graphiti_client", return_value=None):
        functions = execute_template("functions_in_file", {"file_path": "src/graph/query_interface.py"})
        assert any("query_graph" in row.get("full_name", "") for row in functions)

        callers = execute_template("function_callers", {"function_name": "src.graph.query_interface.query_graph"})
        assert isinstance(callers, list)

        callees = execute_template("function_callees", {"function_name": "src.graph.query_interface.query_graph"})
        assert isinstance(callees, list)


def test_execute_template_respects_local_snapshot_runtime_pin(monkeypatch):
    monkeypatch.setenv("GRAPH_TEMPLATE_PREFER_SYNC", "true")
    monkeypatch.setenv("GRAPH_ORACLE_ENABLED", "true")
    monkeypatch.setenv("GRAPH_FORCE_NEO4J_PROBE", "false")
    with patch("src.graph.query_templates._runtime_backend_mode", return_value="local_snapshot"):
        with patch("src.graph.query_templates.get_graphiti_client", return_value=None):
            rows = execute_template("imports", {"file_path": "src/graph/query_interface.py"})
            assert any(row.get("path") == "src/graph/query_templates.py" for row in rows)
