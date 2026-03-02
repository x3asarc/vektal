#!/usr/bin/env python
import json
import sys
from pathlib import Path

import click

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.app_factory import create_app
from src.assistant.governance.kill_switch import get_kill_switch_status, set_kill_switch

FALLBACK_STATUS_PATH = REPO_ROOT / ".graph" / "infrastructure-auto-apply.json"


@click.group()
def cli():
    """Infrastructure auto-apply control."""


@cli.command()
def enable():
    """Enable infrastructure auto-apply (Phase 15.2)."""
    try:
        app = create_app()
        with app.app_context():
            set_kill_switch("infrastructure_auto_apply", enabled=True)
        _write_fallback_status(True, source="db")
        click.echo("Infrastructure auto-apply ENABLED (kill-switch block removed)")
    except Exception as exc:
        _write_fallback_status(True, source=f"fallback:{exc}")
        click.echo("Infrastructure auto-apply ENABLED (fallback mode; DB unavailable)")


@cli.command()
def disable():
    """Disable infrastructure auto-apply."""
    try:
        app = create_app()
        with app.app_context():
            set_kill_switch("infrastructure_auto_apply", enabled=False)
        _write_fallback_status(False, source="db")
        click.echo("Infrastructure auto-apply DISABLED (kill-switch block active)")
    except Exception as exc:
        _write_fallback_status(False, source=f"fallback:{exc}")
        click.echo("Infrastructure auto-apply DISABLED (fallback mode; DB unavailable)")


@cli.command()
def status():
    """Check auto-apply status."""
    try:
        app = create_app()
        with app.app_context():
            enabled = bool(get_kill_switch_status("infrastructure_auto_apply"))
        _write_fallback_status(enabled, source="db")
        click.echo(f"Infrastructure auto-apply: {'ENABLED' if enabled else 'DISABLED'}")
    except Exception:
        enabled = _read_fallback_status()
        click.echo(
            "Infrastructure auto-apply: "
            f"{'ENABLED' if enabled else 'DISABLED'} (fallback status)"
        )


def _write_fallback_status(enabled: bool, source: str) -> None:
    FALLBACK_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"enabled": bool(enabled), "source": source}
    FALLBACK_STATUS_PATH.write_text(json.dumps(payload), encoding="utf-8")


def _read_fallback_status() -> bool:
    if not FALLBACK_STATUS_PATH.exists():
        return False
    try:
        payload = json.loads(FALLBACK_STATUS_PATH.read_text(encoding="utf-8"))
        return bool(payload.get("enabled", False))
    except Exception:
        return False


if __name__ == "__main__":
    cli()
