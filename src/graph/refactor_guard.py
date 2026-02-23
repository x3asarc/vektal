"""
Refactor safety guard based on downstream dependency/caller impact.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.graph.query_templates import execute_template


@dataclass
class RefactorSafetyReport:
    safe: bool
    downstream_files: List[str] = field(default_factory=list)
    callers_count: int = 0
    risk_level: str = "low"


def _risk_level(callers_count: int) -> str:
    if callers_count <= 2:
        return "low"
    if callers_count <= 10:
        return "medium"
    return "high"


def _functions_in_file(file_path: str) -> List[str]:
    rows = execute_template("functions_in_file", {"file_path": file_path})
    names: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("full_name")
        if isinstance(name, str) and name not in names:
            names.append(name)
    return names


def verify_refactor_safety(file_path: str) -> RefactorSafetyReport:
    """
    Estimate refactor risk for a file by inspecting CALLS topology.
    """
    function_names = _functions_in_file(file_path)
    if not function_names:
        return RefactorSafetyReport(safe=True, downstream_files=[], callers_count=0, risk_level="low")

    unique_callers: Set[str] = set()
    downstream_files: Set[str] = set()

    for function_name in function_names:
        callers = execute_template("function_callers", {"function_name": function_name})
        callees = execute_template("function_callees", {"function_name": function_name})

        for row in callers:
            if not isinstance(row, dict):
                continue
            caller_name = row.get("full_name")
            caller_file = row.get("file_path")
            if isinstance(caller_name, str):
                unique_callers.add(caller_name)
            if isinstance(caller_file, str):
                downstream_files.add(caller_file)

        for row in callees:
            if not isinstance(row, dict):
                continue
            callee_file = row.get("file_path")
            if isinstance(callee_file, str):
                downstream_files.add(callee_file)

    callers_count = len(unique_callers)
    risk = _risk_level(callers_count)
    return RefactorSafetyReport(
        safe=risk != "high",
        downstream_files=sorted(downstream_files),
        callers_count=callers_count,
        risk_level=risk,
    )
