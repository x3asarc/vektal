"""
Local graph snapshot fallback for Neo4j-unavailable environments.

Builds a lightweight in-memory graph from the repository filesystem and
serves template-compatible query results for critical graph operations.
"""

from __future__ import annotations

import ast
import os
import re
import time
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.graph.file_parser import parse_python_file


def _normalize(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _module_name_from_path(path: str) -> str:
    normalized = _normalize(path)
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


def _phase_number(path: str) -> Optional[str]:
    match = re.search(r"/phases/([0-9]+(?:\.[0-9]+)?)", _normalize(path))
    return match.group(1) if match else None


def _resolve_module_to_file(module_name: str) -> Optional[str]:
    dotted = (module_name or "").strip(".")
    if not dotted:
        return None

    src_relative = dotted[4:] if dotted.startswith("src.") else dotted
    tests_relative = dotted[6:] if dotted.startswith("tests.") else dotted
    scripts_relative = dotted[8:] if dotted.startswith("scripts.") else dotted
    options = [
        Path("src") / f"{src_relative.replace('.', '/')}.py",
        Path("src") / src_relative.replace(".", "/") / "__init__.py",
        Path("tests") / f"{tests_relative.replace('.', '/')}.py",
        Path("scripts") / f"{scripts_relative.replace('.', '/')}.py",
    ]
    for option in options:
        if option.exists():
            return _normalize(str(option))
    return None


def _extract_alias_map(tree: ast.AST) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Import):
            for alias in node.names:
                key = alias.asname or alias.name.split(".")[0]
                alias_map[key] = alias.name
        elif isinstance(node, ast.ImportFrom):
            base_module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                key = alias.asname or alias.name
                alias_map[key] = f"{base_module}.{alias.name}".strip(".")
    return alias_map


def _attribute_to_symbol(node: ast.AST) -> Optional[str]:
    parts: List[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


def _extract_called_symbol(call_node: ast.Call, alias_map: Dict[str, str]) -> Optional[str]:
    func_node = call_node.func
    if isinstance(func_node, ast.Name):
        symbol = func_node.id
        return alias_map.get(symbol, symbol)

    if isinstance(func_node, ast.Attribute):
        symbol = _attribute_to_symbol(func_node)
        if not symbol:
            return None
        parts = symbol.split(".")
        if parts and parts[0] in alias_map:
            base = alias_map[parts[0]]
            tail = ".".join(parts[1:])
            return f"{base}.{tail}" if tail else base
        return symbol

    return None


def _resolve_callee_full_name(
    symbol: Optional[str],
    src_file: str,
    by_file_and_name: Dict[Tuple[str, str], str],
    by_name: Dict[str, List[str]],
    by_full_name: Set[str],
) -> Optional[str]:
    if not symbol:
        return None

    symbol = symbol.strip(".")
    if symbol in by_full_name:
        return symbol

    parts = symbol.split(".")
    simple_name = parts[-1]
    local_match = by_file_and_name.get((src_file, simple_name))
    if local_match:
        return local_match

    if len(parts) >= 2:
        module_path = _normalize(".".join(parts[:-1]).replace(".", "/"))
        for candidate in (f"{module_path}.py", f"{module_path}/__init__.py"):
            for file_path, name in by_file_and_name:
                if name == simple_name and (file_path == candidate or file_path.endswith(f"/{candidate}")):
                    return by_file_and_name[(file_path, name)]

    candidates = by_name.get(simple_name, [])
    if len(candidates) == 1:
        return candidates[0]
    return None


@dataclass
class LocalGraphSnapshot:
    built_at: float
    files: Set[str]
    imports_out: Dict[str, Set[str]]
    imports_in: Dict[str, Set[str]]
    functions_by_file: Dict[str, List[str]]
    function_file: Dict[str, str]
    function_callers: Dict[str, Set[str]]
    function_callees: Dict[str, Set[str]]
    planning_docs_by_phase: Dict[str, List[str]]
    file_to_planning: Dict[str, Set[str]]


_SNAPSHOT: Optional[LocalGraphSnapshot] = None


def _snapshot_ttl_seconds() -> float:
    return float(os.environ.get("LOCAL_GRAPH_SNAPSHOT_TTL_SECONDS", "300"))


def _snapshot_disk_ttl_seconds() -> float:
    return float(os.environ.get("LOCAL_GRAPH_SNAPSHOT_DISK_TTL_SECONDS", "900"))


def _snapshot_cache_path() -> Path:
    return Path(os.environ.get("LOCAL_GRAPH_SNAPSHOT_CACHE_PATH", ".graph/local-snapshot.json"))


def _candidate_python_files() -> List[str]:
    roots = [Path("src"), Path("tests"), Path("scripts")]
    files: List[str] = []
    for root in roots:
        if not root.exists():
            continue
        for candidate in root.rglob("*.py"):
            files.append(_normalize(str(candidate)))
    return files


def _build_snapshot() -> LocalGraphSnapshot:
    files = set(_candidate_python_files())
    imports_out: Dict[str, Set[str]] = defaultdict(set)
    imports_in: Dict[str, Set[str]] = defaultdict(set)
    functions_by_file: Dict[str, List[str]] = defaultdict(list)
    function_file: Dict[str, str] = {}
    by_file_and_name: Dict[Tuple[str, str], str] = {}
    by_name: Dict[str, List[str]] = defaultdict(list)
    by_full_name: Set[str] = set()
    function_callers: Dict[str, Set[str]] = defaultdict(set)
    function_callees: Dict[str, Set[str]] = defaultdict(set)
    planning_docs_by_phase: Dict[str, List[str]] = defaultdict(list)
    file_to_planning: Dict[str, Set[str]] = defaultdict(set)

    for path in files:
        parsed = parse_python_file(path)
        for imp in parsed.imports:
            module = imp.from_module or imp.name
            resolved = _resolve_module_to_file(module)
            if resolved:
                imports_out[path].add(resolved)
                imports_in[resolved].add(path)

        module_name = _module_name_from_path(path)
        for fn in parsed.functions:
            full_name = f"{module_name}.{fn.name}"
            functions_by_file[path].append(full_name)
            function_file[full_name] = path
            by_file_and_name[(path, fn.name)] = full_name
            by_name[fn.name].append(full_name)
            by_full_name.add(full_name)

    for path in files:
        if not Path(path).exists():
            continue
        try:
            content = Path(path).read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            continue

        alias_map = _extract_alias_map(tree)
        top_level_functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for fn_node in top_level_functions:
            caller_full_name = by_file_and_name.get((path, fn_node.name))
            if not caller_full_name:
                continue
            for node in ast.walk(fn_node):
                if not isinstance(node, ast.Call):
                    continue
                symbol = _extract_called_symbol(node, alias_map)
                callee_full_name = _resolve_callee_full_name(
                    symbol=symbol,
                    src_file=path,
                    by_file_and_name=by_file_and_name,
                    by_name=by_name,
                    by_full_name=by_full_name,
                )
                if not callee_full_name or callee_full_name == caller_full_name:
                    continue
                function_callees[caller_full_name].add(callee_full_name)
                function_callers[callee_full_name].add(caller_full_name)

    planning_docs = [p for p in Path(".planning").rglob("*.md")] if Path(".planning").exists() else []
    for doc_path in planning_docs:
        normalized_doc = _normalize(str(doc_path))
        phase = _phase_number(normalized_doc)
        if phase:
            planning_docs_by_phase[phase].append(normalized_doc)

        try:
            content = doc_path.read_text(encoding="utf-8")
        except Exception:
            content = ""
        for file_path in files:
            if file_path in content:
                file_to_planning[file_path].add(normalized_doc)

    return LocalGraphSnapshot(
        built_at=time.time(),
        files=files,
        imports_out=imports_out,
        imports_in=imports_in,
        functions_by_file=functions_by_file,
        function_file=function_file,
        function_callers=function_callers,
        function_callees=function_callees,
        planning_docs_by_phase=planning_docs_by_phase,
        file_to_planning=file_to_planning,
    )


def _snapshot_to_dict(snapshot: LocalGraphSnapshot) -> Dict[str, object]:
    return {
        "built_at": snapshot.built_at,
        "files": sorted(snapshot.files),
        "imports_out": {k: sorted(v) for k, v in snapshot.imports_out.items()},
        "imports_in": {k: sorted(v) for k, v in snapshot.imports_in.items()},
        "functions_by_file": snapshot.functions_by_file,
        "function_file": snapshot.function_file,
        "function_callers": {k: sorted(v) for k, v in snapshot.function_callers.items()},
        "function_callees": {k: sorted(v) for k, v in snapshot.function_callees.items()},
        "planning_docs_by_phase": snapshot.planning_docs_by_phase,
        "file_to_planning": {k: sorted(v) for k, v in snapshot.file_to_planning.items()},
    }


def _snapshot_from_dict(payload: Dict[str, object]) -> Optional[LocalGraphSnapshot]:
    try:
        built_at = float(payload.get("built_at", 0))
        files = set(payload.get("files", []))
        imports_out = {k: set(v) for k, v in dict(payload.get("imports_out", {})).items()}
        imports_in = {k: set(v) for k, v in dict(payload.get("imports_in", {})).items()}
        functions_by_file = {
            k: list(v) for k, v in dict(payload.get("functions_by_file", {})).items()
        }
        function_file = {k: str(v) for k, v in dict(payload.get("function_file", {})).items()}
        function_callers = {
            k: set(v) for k, v in dict(payload.get("function_callers", {})).items()
        }
        function_callees = {
            k: set(v) for k, v in dict(payload.get("function_callees", {})).items()
        }
        planning_docs_by_phase = {
            k: list(v) for k, v in dict(payload.get("planning_docs_by_phase", {})).items()
        }
        file_to_planning = {
            k: set(v) for k, v in dict(payload.get("file_to_planning", {})).items()
        }
        return LocalGraphSnapshot(
            built_at=built_at,
            files=files,
            imports_out=imports_out,
            imports_in=imports_in,
            functions_by_file=functions_by_file,
            function_file=function_file,
            function_callers=function_callers,
            function_callees=function_callees,
            planning_docs_by_phase=planning_docs_by_phase,
            file_to_planning=file_to_planning,
        )
    except Exception:
        return None


def _load_snapshot_from_disk() -> Optional[LocalGraphSnapshot]:
    cache_path = _snapshot_cache_path()
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    snapshot = _snapshot_from_dict(payload if isinstance(payload, dict) else {})
    if snapshot is None:
        return None

    if (time.time() - snapshot.built_at) > _snapshot_disk_ttl_seconds():
        return None
    return snapshot


def _write_snapshot_to_disk(snapshot: LocalGraphSnapshot) -> None:
    cache_path = _snapshot_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(_snapshot_to_dict(snapshot), indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_snapshot(force_refresh: bool = False) -> LocalGraphSnapshot:
    global _SNAPSHOT
    if force_refresh or _SNAPSHOT is None:
        if not force_refresh:
            disk_snapshot = _load_snapshot_from_disk()
            if disk_snapshot is not None:
                _SNAPSHOT = disk_snapshot
                return _SNAPSHOT
        _SNAPSHOT = _build_snapshot()
        _write_snapshot_to_disk(_SNAPSHOT)
        return _SNAPSHOT

    if (time.time() - _SNAPSHOT.built_at) > _snapshot_ttl_seconds():
        _SNAPSHOT = _build_snapshot()
        _write_snapshot_to_disk(_SNAPSHOT)
    return _SNAPSHOT


def _impact_radius(snapshot: LocalGraphSnapshot, file_path: str, max_depth: int = 3) -> List[Dict[str, object]]:
    target = _normalize(file_path)
    frontier = {target}
    seen = {target}
    rows: List[Dict[str, object]] = []
    for depth in range(1, max_depth + 1):
        next_frontier: Set[str] = set()
        for item in frontier:
            for importer in snapshot.imports_in.get(item, set()):
                if importer in seen:
                    continue
                seen.add(importer)
                next_frontier.add(importer)
                rows.append({"path": importer, "depth": depth})
        frontier = next_frontier
        if not frontier:
            break
    return rows


def query_template(template_name: str, params: Dict[str, object]) -> List[Dict[str, object]]:
    snapshot = get_snapshot()
    file_path = _normalize(str(params.get("file_path", "")))

    if template_name == "imports":
        return [{"path": p, "purpose": ""} for p in sorted(snapshot.imports_out.get(file_path, set()))]

    if template_name == "imported_by":
        return [{"path": p, "purpose": ""} for p in sorted(snapshot.imports_in.get(file_path, set()))]

    if template_name == "impact_radius":
        return _impact_radius(snapshot, file_path=file_path, max_depth=3)

    if template_name == "functions_in_file":
        return [{"full_name": f, "file_path": file_path} for f in snapshot.functions_by_file.get(file_path, [])]

    if template_name == "function_callers":
        function_name = str(params.get("function_name", ""))
        return [
            {"full_name": caller, "file_path": snapshot.function_file.get(caller, "")}
            for caller in sorted(snapshot.function_callers.get(function_name, set()))
        ]

    if template_name == "function_callees":
        function_name = str(params.get("function_name", ""))
        return [
            {"full_name": callee, "file_path": snapshot.function_file.get(callee, "")}
            for callee in sorted(snapshot.function_callees.get(function_name, set()))
        ]

    if template_name == "planning_context":
        links = snapshot.file_to_planning.get(file_path, set())
        rows: List[Dict[str, object]] = []
        for doc in sorted(links):
            rows.append({"path": doc, "phase": _phase_number(doc), "goal": ""})
        return rows

    if template_name == "phase_code":
        phase = str(params.get("phase", ""))
        docs = set(snapshot.planning_docs_by_phase.get(phase, []))
        rows: List[Dict[str, object]] = []
        for code_path, linked_docs in snapshot.file_to_planning.items():
            if docs.intersection(linked_docs):
                rows.append({"path": code_path, "purpose": ""})
        return rows

    if template_name == "similar_files":
        if not file_path:
            return []
        target_tokens = set(file_path.replace(".", "/").split("/"))
        scored: List[Tuple[float, str]] = []
        for candidate in snapshot.files:
            if candidate == file_path:
                continue
            tokens = set(candidate.replace(".", "/").split("/"))
            intersection = len(target_tokens.intersection(tokens))
            union = max(1, len(target_tokens.union(tokens)))
            score = intersection / union
            if score > 0:
                scored.append((score, candidate))
        scored.sort(reverse=True)
        limit = int(params.get("limit", 5) or 5)
        threshold = float(params.get("threshold", 0.6) or 0.6)
        return [
            {"path": path, "purpose": "", "score": score}
            for score, path in scored[:limit]
            if score >= threshold
        ]

    return []
