#!/usr/bin/env python
import click
import sys
import json
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.graph.remediators.optimizer_remediator import OptimizerRemediator
from src.app_factory import create_app

@click.command()
@click.option('--auto-apply', is_flag=True, help='Auto-apply if sandbox GREEN')
@click.option('--trigger', default='manual', help='Trigger type (manual/scheduled)')
def optimize(auto_apply, trigger):
    """Run runtime optimizations."""
    app = create_app()
    with app.app_context():
        remediator = OptimizerRemediator()
        result = remediator.remediate({'trigger': trigger})

        click.echo(f"Optimization Result: {result['action']}")
        
        if result.get('optimizations'):
            click.echo("\nOptimizations Proposed:")
            for opt in result['optimizations']:
                click.echo(f"  - {opt['parameter']}: {opt['old_value']} → {opt['new_value']} ({opt['reason']})")
                
        if result.get('sandbox_run_id'):
            click.echo(f"Sandbox Run ID: {result['sandbox_run_id']}")
            
        if not result['success']:
            click.echo(f"Error: {result.get('error') or result.get('reason')}")

if __name__ == '__main__':
    optimize()
