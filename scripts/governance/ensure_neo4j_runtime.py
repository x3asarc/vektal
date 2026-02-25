#!/usr/bin/env python3
"""
PreToolUse runtime guard for Neo4j/Graphiti dependencies.

Guarantees the project runtime can import Neo4j-related modules before tool use.
If missing, installs pinned packages from requirements.txt into the project venv.
"""

from __future__ import annotations

import re
import subprocess
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_PATH = REPO_ROOT / "requirements.txt"

CHECK = "[OK]"
FAIL = "[FAIL]"
INFO = "[INFO]"
WARN = "[WARN]"
STATE_PATH = REPO_ROOT / ".graph" / "runtime-backend.json"


def _venv_python() -> Optional[Path]:
    if sys.platform == "win32":
        candidate = REPO_ROOT / "venv" / "Scripts" / "python.exe"
    else:
        candidate = REPO_ROOT / "venv" / "bin" / "python"
    return candidate if candidate.exists() else None


def _resolve_package_spec(package_name: str) -> str:
    """
    Resolve exact package spec from requirements.txt, fallback to package name.
    """
    if not REQUIREMENTS_PATH.exists():
        return package_name

    pattern = re.compile(rf"^\s*{re.escape(package_name)}\s*([=<>!~].*)?$", re.IGNORECASE)
    for raw_line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if pattern.match(line):
            return line
    return package_name


def _can_import(python_exe: str, module_name: str) -> bool:
    proc = subprocess.run(
        [python_exe, "-c", f"import {module_name}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _install_package(python_exe: str, package_spec: str) -> bool:
    proc = subprocess.run(
        [python_exe, "-m", "pip", "install", package_spec],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=240,
    )
    if proc.returncode != 0:
        print(f"{FAIL} pip install failed for {package_spec}")
        if proc.stderr:
            print(proc.stderr.strip())
        return False
    return True


def _neo4j_uri_candidates() -> List[str]:
    env = REPO_ROOT / ".env"
    loaded = {}
    if env.exists():
        for raw in env.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            loaded[key.strip()] = value.strip()

    primary = loaded.get("NEO4J_URI") or ""
    fallback_raw = loaded.get("NEO4J_URI_FALLBACKS", "bolt://localhost:7687")
    fallbacks = [item.strip() for item in fallback_raw.split(",") if item.strip()]
    ordered = [uri for uri in [primary, *fallbacks] if uri]
    dedup: List[str] = []
    for uri in ordered:
        if uri not in dedup:
            dedup.append(uri)
    return dedup


def _neo4j_credentials() -> Tuple[str, str]:
    env = REPO_ROOT / ".env"
    user = "neo4j"
    password = ""
    if env.exists():
        for raw in env.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "NEO4J_USER":
                user = value.strip() or user
            elif key.strip() == "NEO4J_PASSWORD":
                password = value.strip()
    return user, password


def _probe_neo4j() -> Optional[str]:
    try:
        from neo4j import GraphDatabase
    except Exception:
        return None

    user, password = _neo4j_credentials()
    if not password:
        return None
    timeout = 0.25
    logging.getLogger("neo4j").setLevel(logging.CRITICAL)
    for uri in _neo4j_uri_candidates():
        try:
            with GraphDatabase.driver(uri, auth=(user, password), connection_timeout=timeout) as driver:
                driver.verify_connectivity()
            return uri
        except Exception:
            continue
    return None


def _warm_local_snapshot(python_exe: str) -> bool:
    proc = subprocess.run(
        [
            python_exe,
            "-c",
            "from src.graph.local_graph_store import get_snapshot; s=get_snapshot(force_refresh=True); print(len(s.files))",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return proc.returncode == 0


def _write_backend_state(mode: str, detail: str) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(
            json.dumps({"mode": mode, "detail": detail}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def ensure_runtime() -> bool:
    venv_python = _venv_python()
    python_exe = str(venv_python) if venv_python else sys.executable

    if not venv_python:
        print(f"{INFO} Project venv python not found; using interpreter: {python_exe}")

    required = [
        ("neo4j", "neo4j"),
        ("graphiti_core", "graphiti-core"),
    ]

    for module_name, package_name in required:
        if _can_import(python_exe, module_name):
            print(f"{CHECK} {module_name} import available")
            continue

        package_spec = _resolve_package_spec(package_name)
        print(f"{INFO} Installing missing dependency: {package_spec}")
        if not _install_package(python_exe, package_spec):
            return False

        if not _can_import(python_exe, module_name):
            print(f"{FAIL} {module_name} still unavailable after install")
            return False
        print(f"{CHECK} {module_name} import restored")

    reachable_uri = _probe_neo4j()
    if reachable_uri:
        print(f"{CHECK} Neo4j reachable at {reachable_uri}")
        _write_backend_state("neo4j", reachable_uri)
        return True

    print(f"{WARN} Neo4j unreachable; warming local graph snapshot fallback")
    if not _warm_local_snapshot(python_exe):
        print(f"{FAIL} Local graph snapshot fallback failed to initialize")
        return False

    print(f"{CHECK} Local graph snapshot fallback ready")
    _write_backend_state("local_snapshot", "neo4j_unreachable")
    return True


def main() -> int:
    return 0 if ensure_runtime() else 1


if __name__ == "__main__":
    raise SystemExit(main())
