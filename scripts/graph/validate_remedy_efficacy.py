#!/usr/bin/env python
import click
import sys
import os
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.graph.sentry_feedback_loop import SentryFeedbackLoop
from src.core.sentry_client import get_sentry_client
from src.app_factory import create_app

@click.command()
@click.option('--hours', default=24, help='Validate last N hours')
def validate(hours):
    """Validate remediation efficacy via Sentry status."""
    app = create_app()
    with app.app_context():
        client = get_sentry_client()
        loop = SentryFeedbackLoop(client)

        results = loop.validate_pending_remediations(hours=hours)

        click.echo(f"Processed {len(results)} remediations:")
        validated = [r for r in results if r['status'] == 'validated']
        failed = [r for r in results if r['status'] == 'failed']
        pending = [r for r in results if r['status'] == 'pending']

        click.echo(f"  ✓ Validated/Promoted: {len(validated)}")
        click.echo(f"  ✗ Validation Failed:  {len(failed)}")
        click.echo(f"  ⏳ Still Pending:     {len(pending)}")

        if failed:
            click.echo("\nFailed remediations:")
            for f in failed:
                click.echo(f"  - {f['sentry_issue_id']} (Run: {f['run_id']})")

if __name__ == '__main__':
    validate()
