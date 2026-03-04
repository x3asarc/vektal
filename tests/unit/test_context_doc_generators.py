from __future__ import annotations

from pathlib import Path
import shutil
import uuid

from scripts.context.build_agent_primer import build_agent_primer
from scripts.context.build_context_link_map import build_context_link_map
from scripts.context.build_folder_summaries import build_folder_summaries


def _new_repo_dir() -> Path:
    base = Path.cwd() / "context_doc_test_runs"
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / f"context-docs-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _seed_repo(root: Path) -> None:
    for rel in ["src", "scripts", ".planning", "docs", "tests", "ops", ".memory/events", ".memory/working"]:
        (root / rel).mkdir(parents=True, exist_ok=True)

    (root / ".planning" / "STATE.md").write_text(
        "\n".join(
            [
                "**Phase:** 16-agent-context-os",
                "**Gate Status:** `GREEN`",
                "**Target Milestone:** Phase 16",
            ]
        ),
        encoding="utf-8",
    )
    (root / ".planning" / "ROADMAP.md").write_text("# roadmap", encoding="utf-8")
    (root / ".planning" / "NEXT_TASKS.md").write_text("- [ ] Generate primer\n- [ ] Build folder summaries\n", encoding="utf-8")
    (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (root / "scripts" / "tool.sh").write_text("echo ok\n", encoding="utf-8")
    (root / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
    (root / "ops" / "STRUCTURE_SPEC.md").write_text("# spec\n", encoding="utf-8")
    (root / ".memory" / "working" / "session-codex-x.json").write_text(
        '{"context":{"current_task":"phase16-test"}}',
        encoding="utf-8",
    )


def test_generators_emit_required_sections_and_coverage():
    run_dir = _new_repo_dir()
    try:
        _seed_repo(run_dir)
        fixed_now = "2026-03-03T20:10:00Z"
        primer = build_agent_primer(repo_root=run_dir, now_iso=fixed_now, git_sha="abc1234")
        folder = build_folder_summaries(repo_root=run_dir, now_iso=fixed_now)
        link_map = build_context_link_map(repo_root=run_dir, now_iso=fixed_now)

        primer_text = Path(primer["path"]).read_text(encoding="utf-8")
        assert "## Current Runtime Snapshot" in primer_text
        assert "## Immediate Blockers / Next Actions" in primer_text
        assert "## Priority Links" in primer_text
        assert "## Memory Snapshot" in primer_text

        folder_text = Path(folder["path"]).read_text(encoding="utf-8")
        for name in ["`src/`", "`scripts/`", "`.planning/`", "`docs/`", "`tests/`", "`ops/`"]:
            assert name in folder_text
        assert "Last verified: 2026-03-03T20:10:00Z" in folder_text

        link_text = Path(link_map["path"]).read_text(encoding="utf-8")
        assert "Last refreshed: 2026-03-03T20:10:00Z" in link_text
        assert "`docs/AGENT_START_HERE.md`" in link_text
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_generators_are_stable_for_same_input():
    run_dir = _new_repo_dir()
    try:
        _seed_repo(run_dir)
        fixed_now = "2026-03-03T20:10:00Z"

        first = build_agent_primer(repo_root=run_dir, now_iso=fixed_now, git_sha="abc1234")
        second = build_agent_primer(repo_root=run_dir, now_iso=fixed_now, git_sha="abc1234")
        assert first["content"] == second["content"]

        first_folder = build_folder_summaries(repo_root=run_dir, now_iso=fixed_now)
        second_folder = build_folder_summaries(repo_root=run_dir, now_iso=fixed_now)
        assert first_folder["content"] == second_folder["content"]

        first_map = build_context_link_map(repo_root=run_dir, now_iso=fixed_now)
        second_map = build_context_link_map(repo_root=run_dir, now_iso=fixed_now)
        assert first_map["content"] == second_map["content"]
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)

