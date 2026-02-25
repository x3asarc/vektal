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
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_PATH = REPO_ROOT / "requirements.txt"

CHECK = "[OK]"
FAIL = "[FAIL]"
INFO = "[INFO]"


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

    return True


def main() -> int:
    return 0 if ensure_runtime() else 1


if __name__ == "__main__":
    raise SystemExit(main())

