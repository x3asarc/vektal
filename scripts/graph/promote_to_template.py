#!/usr/bin/env python
import subprocess
import sys
import time
from pathlib import Path

import click

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.app_factory import create_app
from src.graph.template_extractor import TemplateExtractor

DEFAULT_SYNC_INTERVAL_SECONDS = 300


@click.group()
def cli():
    """Template management CLI."""


@cli.command()
@click.option("--fingerprint", required=True)
@click.option("--sandbox-run-id", required=True)
def promote(fingerprint, sandbox_run_id):
    """Manually promote a GREEN sandbox run to a template."""
    app = create_app()
    with app.app_context():
        from src.models.sandbox_runs import SandboxRun

        run = SandboxRun.query.filter_by(run_id=sandbox_run_id).first()
        verdict = str(getattr(run.verdict, "value", run.verdict)).lower() if run else ""
        if not run or verdict != "green":
            click.echo("ERROR: Run not found or not GREEN")
            return

        changed_files = run.changed_files if isinstance(run.changed_files, dict) else {}
        extractor = TemplateExtractor()
        template_id = extractor.extract_and_promote(
            fix_payload={
                "changed_files": changed_files,
                "description": f"Manual promotion of {sandbox_run_id}",
            },
            confidence=run.confidence or 0.9,
            fingerprint=fingerprint,
        )
        if template_id:
            click.echo(f"Promoted to template: {template_id}")
        else:
            click.echo("FAILED to promote template")


@cli.command("sync-cache")
def sync_cache():
    """Sync Neo4j templates to PostgreSQL cache."""
    app = create_app()
    with app.app_context():
        extractor = TemplateExtractor()
        count = extractor.sync_templates_to_cache(min_application_count=3, recent_days=7)
        click.echo(f"Synced {count} templates to cache")


@cli.command("expire-changed")
@click.option(
    "--changed-file",
    "changed_files",
    multiple=True,
    help="File path(s) to evaluate for template expiry. If omitted, use git diff.",
)
@click.option("--since-ref", default="HEAD~1", show_default=True)
def expire_changed(changed_files, since_ref):
    """Expire templates whose affected file sets overlap changed files."""
    app = create_app()
    with app.app_context():
        extractor = TemplateExtractor()
        paths = list(changed_files) if changed_files else _detect_changed_files_from_git(since_ref)
        expired = extractor.expire_templates_for_changed_files(paths)
        click.echo(f"Expired {expired} templates from {len(paths)} changed files")


@cli.command("sync-daemon")
@click.option("--interval-seconds", default=DEFAULT_SYNC_INTERVAL_SECONDS, show_default=True)
@click.option("--once", is_flag=True, help="Run one cycle then exit.")
@click.option("--since-ref", default="HEAD~1", show_default=True)
def sync_daemon(interval_seconds, once, since_ref):
    """Run periodic cache sync every 5 minutes (or configured interval)."""
    app = create_app()
    interval_seconds = max(30, int(interval_seconds))

    while True:
        with app.app_context():
            extractor = TemplateExtractor()
            synced = extractor.sync_templates_to_cache(min_application_count=3, recent_days=7)
            changed = _detect_changed_files_from_git(since_ref)
            expired = extractor.expire_templates_for_changed_files(changed)
            click.echo(
                f"[sync-cycle] synced={synced} expired={expired} "
                f"changed_files={len(changed)} interval={interval_seconds}s"
            )

        if once:
            return
        time.sleep(interval_seconds)


def _detect_changed_files_from_git(since_ref: str) -> list[str]:
    """Best-effort helper for expiry checks; fail-open to empty file set."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", since_ref, "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


if __name__ == "__main__":
    cli()
