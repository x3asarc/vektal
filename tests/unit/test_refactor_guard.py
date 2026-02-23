"""
Unit tests for CALLS-based refactor safety guard.
"""

from unittest.mock import patch

from src.graph.refactor_guard import verify_refactor_safety


def _template_side_effect(template_name, params):
    if template_name == "functions_in_file":
        return [{"full_name": "pkg.mod.fn_a", "file_path": "src/pkg/mod.py"}]

    if template_name == "function_callers":
        function_name = params["function_name"]
        if function_name == "pkg.mod.fn_a":
            return [{"full_name": "caller.one", "file_path": "src/a.py"}]

    if template_name == "function_callees":
        function_name = params["function_name"]
        if function_name == "pkg.mod.fn_a":
            return [{"full_name": "callee.one", "file_path": "src/b.py"}]

    return []


def test_refactor_guard_low_risk():
    with patch("src.graph.refactor_guard.execute_template", side_effect=_template_side_effect):
        report = verify_refactor_safety("src/pkg/mod.py")
        assert report.risk_level == "low"
        assert report.safe is True
        assert report.callers_count == 1
        assert "src/a.py" in report.downstream_files
        assert "src/b.py" in report.downstream_files


def test_refactor_guard_medium_risk():
    def side_effect(template_name, params):
        if template_name == "functions_in_file":
            return [{"full_name": "pkg.mod.fn_a", "file_path": "src/pkg/mod.py"}]
        if template_name == "function_callers":
            return [{"full_name": f"caller.{i}", "file_path": f"src/caller_{i}.py"} for i in range(3)]
        if template_name == "function_callees":
            return []
        return []

    with patch("src.graph.refactor_guard.execute_template", side_effect=side_effect):
        report = verify_refactor_safety("src/pkg/mod.py")
        assert report.risk_level == "medium"
        assert report.safe is True
        assert report.callers_count == 3


def test_refactor_guard_high_risk():
    def side_effect(template_name, params):
        if template_name == "functions_in_file":
            return [{"full_name": "pkg.mod.fn_a", "file_path": "src/pkg/mod.py"}]
        if template_name == "function_callers":
            return [{"full_name": f"caller.{i}", "file_path": f"src/caller_{i}.py"} for i in range(12)]
        if template_name == "function_callees":
            return []
        return []

    with patch("src.graph.refactor_guard.execute_template", side_effect=side_effect):
        report = verify_refactor_safety("src/pkg/mod.py")
        assert report.risk_level == "high"
        assert report.safe is False
        assert report.callers_count == 12


def test_refactor_guard_empty_graph_behavior():
    with patch("src.graph.refactor_guard.execute_template", return_value=[]):
        report = verify_refactor_safety("src/empty.py")
        assert report.risk_level == "low"
        assert report.safe is True
        assert report.callers_count == 0
        assert report.downstream_files == []
