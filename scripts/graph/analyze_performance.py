#!/usr/bin/env python
import click
import sys
import time
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.graph.performance_profiler import PerformanceProfiler
from src.graph.bottleneck_detector import BottleneckDetector
from src.graph.telemetry_dashboard import TelemetryDashboard

@click.group()
def cli():
    """Performance analysis CLI."""
    pass

@cli.command()
def analyze():
    """Analyze current performance bottlenecks and show dashboard."""
    profiler = PerformanceProfiler()
    detector = BottleneckDetector()
    dashboard = TelemetryDashboard(profiler)

    click.echo(dashboard.render_dashboard())

    bottlenecks = profiler.analyze_bottlenecks()
    click.echo(f"\nFound {len(bottlenecks)} active bottlenecks:")

    for b in bottlenecks:
        recommendations = detector.generate_recommendations(b)
        click.echo(f"\n{b['type'].upper()}:")
        click.echo(f"  Details: {b}")
        click.echo(f"  Recommendations: {len(recommendations)}")
        for rec in recommendations:
            click.echo(f"    - {rec['action']}: {rec['description']} (conf: {rec['confidence']})")


@cli.command()
@click.option("--interval-seconds", default=60, show_default=True)
@click.option("--once", is_flag=True, help="Record one background snapshot and exit.")
def daemon(interval_seconds, once):
    """Run continuous background profiling loop."""
    profiler = PerformanceProfiler()
    if once:
        snapshots = profiler.run_background_profiler(interval_seconds=interval_seconds, once=True)
        click.echo(f"Recorded {snapshots} background snapshot")
        return

    click.echo(f"Starting background profiler (interval={interval_seconds}s). Ctrl+C to stop.")
    try:
        while True:
            snapshots = profiler.run_background_profiler(
                interval_seconds=interval_seconds,
                once=True,
            )
            click.echo(f"Recorded {snapshots} background snapshot")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        click.echo("Background profiler stopped.")


if __name__ == '__main__':
    cli()
