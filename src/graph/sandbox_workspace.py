"""Workspace setup and rollback-risk helpers for sandbox verification."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from src.graph.sandbox_types import STATUS_GREEN, STATUS_RED, STATUS_YELLOW


def create_run_dir(base_dir: Path) -> tuple[str, Path]:
    run_id = uuid.uuid4().hex
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_id, run_dir


def setup_workspace(project_root: Path, run_dir: Path, changed_files: dict[str, str]) -> None:
    include_items = [
        "src",
        "tests",
        "scripts/governance",
        "pyproject.toml",
        "mypy.ini",
        "risk-policy.json",
        "STANDARDS.md",
    ]
    for item in include_items:
        src_path = project_root / item
        dst_path = run_dir / item
        if not src_path.exists():
            continue
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)

    for rel_path, content in changed_files.items():
        target = run_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def cleanup_workspace(run_dir: Path, enabled: bool) -> None:
    if enabled:
        shutil.rmtree(run_dir, ignore_errors=True)


def rollback_gate(changed_files: dict[str, str]) -> dict[str, str]:
    if not changed_files:
        return {
            "status": STATUS_GREEN,
            "message": "No changed files to analyze for rollback.",
        }

    notes: list[str] = []
    status = STATUS_GREEN
    changed_paths = list(changed_files.keys())
    total_loc = sum(len(content.splitlines()) for content in changed_files.values())

    if len(changed_paths) > 5 or total_loc > 500:
        status = STATUS_YELLOW
        notes.append("Large blast radius; human approval recommended.")

    touched_models = any(path.startswith("src/models/") for path in changed_paths)
    touched_migrations = any(path.startswith("migrations/") for path in changed_paths)
    if touched_models and not touched_migrations:
        status = STATUS_YELLOW
        notes.append("Model changes detected without migration updates.")

    irreversible_patterns = ("drop table", "truncate table", "delete from")
    for path, content in changed_files.items():
        if path.startswith("migrations/") and any(
            token in content.lower() for token in irreversible_patterns
        ):
            return {
                "status": STATUS_RED,
                "message": f"Irreversible migration pattern detected in {path}.",
            }

    if status == STATUS_GREEN:
        return {
            "status": STATUS_GREEN,
            "message": "Rollback risk is low; changes appear reversible.",
        }
    return {
        "status": status,
        "message": " ".join(notes),
    }
