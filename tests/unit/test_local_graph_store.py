"""
Unit tests for local graph snapshot fallback query engine.
"""

from pathlib import Path

from src.graph.local_graph_store import query_template, get_snapshot


def test_local_snapshot_builds_and_contains_core_files():
    snapshot = get_snapshot(force_refresh=True)
    assert "src/graph/query_interface.py" in snapshot.files


def test_local_query_imports_and_imported_by():
    imports = query_template("imports", {"file_path": "src/graph/query_interface.py"})
    assert any(row.get("path") == "src/graph/query_templates.py" for row in imports)

    imported_by = query_template("imported_by", {"file_path": "src/graph/query_interface.py"})
    assert isinstance(imported_by, list)


def test_local_query_function_templates():
    functions = query_template("functions_in_file", {"file_path": "src/graph/query_interface.py"})
    names = {row.get("full_name") for row in functions}
    assert "src.graph.query_interface.query_graph" in names

    callers = query_template("function_callers", {"function_name": "src.graph.query_interface.query_graph"})
    callees = query_template("function_callees", {"function_name": "src.graph.query_interface.query_graph"})
    assert isinstance(callers, list)
    assert isinstance(callees, list)


def test_local_snapshot_writes_disk_cache(monkeypatch):
    cache_path = Path("temp/test-local-snapshot-cache.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        cache_path.unlink()
    monkeypatch.setenv("LOCAL_GRAPH_SNAPSHOT_CACHE_PATH", str(cache_path))
    snapshot = get_snapshot(force_refresh=True)
    assert snapshot.files
    assert cache_path.exists()
    cache_path.unlink(missing_ok=True)
