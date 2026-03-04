#!/usr/bin/env python3
"""Generate docs/FOLDER_SUMMARIES.md with lightweight directory metadata."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_DIRECTORIES = ["src", "scripts", ".planning", "docs", "tests", "ops"]
IGNORED_FILE_NAMES = {"AGENT_START_HERE.md", "FOLDER_SUMMARIES.md", "CONTEXT_LINK_MAP.md"}
PURPOSE_MAP = {
    "src": "Core runtime and application logic",
    "scripts": "Operational and maintenance commands",
    ".planning": "Canonical lifecycle plans and phase artifacts",
    "docs": "Human-readable architecture and onboarding docs",
    "tests": "Automated verification suites",
    "ops": "Governance and structure contracts",
}
OWNER_MAP = {
    "src": "Builder",
    "scripts": "Builder",
    ".planning": "PhaseManager",
    "docs": "ContextCurator",
    "tests": "Reviewer",
    "ops": "StructureGuardian",
}
VOLATILITY_MAP = {
    "src": "High",
    "scripts": "High",
    ".planning": "Medium",
    "docs": "Medium",
    "tests": "High",
    "ops": "Low",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _top_files(directory: Path, *, repo_root: Path, limit: int = 5, scan_cap: int = 300) -> list[str]:
    if not directory.exists():
        return []
    candidates: list[Path] = []
    for index, path in enumerate(sorted(directory.rglob("*"))):
        if index >= scan_cap:
            break
        if path.is_file():
            if "__pycache__" in path.parts:
                continue
            if path.suffix.lower() == ".pyc":
                continue
            if path.name in IGNORED_FILE_NAMES:
                continue
            candidates.append(path)
    picked = sorted(candidates, key=lambda item: item.name.lower())[:limit]
    return [item.relative_to(repo_root).as_posix() for item in picked]


def build_folder_summaries(
    *,
    repo_root: Path = REPO_ROOT,
    output_path: Path | None = None,
    now_iso: str | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Build folder summary markdown and optionally write it to docs/."""

    now_value = now_iso or _utc_now_iso()
    lines = [
        "# FOLDER SUMMARIES",
        "",
        f"Last verified: {now_value}",
        "",
        "| Folder | Purpose | Top Files | Owner Role | Volatility | Last Verified |",
        "|---|---|---|---|---|---|",
    ]

    for folder_name in CORE_DIRECTORIES:
        directory = repo_root / folder_name
        top_files = _top_files(directory, repo_root=repo_root)
        top_display = ", ".join(f"`{item}`" for item in top_files) if top_files else "`N/A`"
        lines.append(
            "| {folder} | {purpose} | {top_files} | {owner} | {volatility} | {verified} |".format(
                folder=f"`{folder_name}/`",
                purpose=PURPOSE_MAP.get(folder_name, "N/A"),
                top_files=top_display,
                owner=OWNER_MAP.get(folder_name, "N/A"),
                volatility=VOLATILITY_MAP.get(folder_name, "N/A"),
                verified=now_value,
            )
        )

    content = "\n".join(lines) + "\n"
    target = output_path or (repo_root / "docs" / "FOLDER_SUMMARIES.md")
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return {"path": str(target), "content": content, "directories": CORE_DIRECTORIES}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate docs/FOLDER_SUMMARIES.md")
    parser.add_argument("--dry-run", action="store_true", help="Render without writing file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_folder_summaries(write=not args.dry_run)
    print(result["content"] if args.dry_run else f"[folder-summaries] wrote {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
