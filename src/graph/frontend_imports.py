"""
Frontend import parsing helpers for local graph snapshot fallback.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

_TS_IMPORT_RE = re.compile(
    r"(?:import|export)\s+(?:[^\"']+?\s+from\s+)?[\"']([^\"']+)[\"']|"
    r"import\(\s*[\"']([^\"']+)[\"']\s*\)"
)


def _normalize(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def resolve_frontend_import_to_file(module_name: str, source_path: str) -> Optional[str]:
    module = (module_name or "").strip()
    if not module:
        return None
    if module.startswith("@/"):
        base = Path("frontend/src") / module[2:]
    elif module.startswith("."):
        base = Path(source_path).parent / module
    else:
        return None

    candidates = [
        base,
        Path(f"{base}.ts"),
        Path(f"{base}.tsx"),
        Path(f"{base}.js"),
        Path(f"{base}.jsx"),
        base / "index.ts",
        base / "index.tsx",
        base / "index.js",
        base / "index.jsx",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return _normalize(str(candidate))
    return None


def extract_ts_import_modules(content: str) -> List[str]:
    modules: List[str] = []
    for match in _TS_IMPORT_RE.findall(content):
        value = match[0] or match[1]
        if value:
            modules.append(value)
    return modules
