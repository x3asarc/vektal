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

    with patch("src.graph.query_templates.get_graphiti_client", return_value=Client()):
        rows = execute_template("imports", {"file_path": "src/a.py"})
        assert rows == [{"path": "src/d.py"}]


def test_execute_template_returns_empty_for_missing_client():
    with patch("src.graph.query_templates.get_graphiti_client", return_value=None):
        rows = execute_template("imports", {"file_path": "src/a.py"})
        assert rows == []

