from datetime import datetime, timedelta
from typing import Dict, List, Any
from src.graph.performance_profiler import PerformanceProfiler

class TelemetryDashboard:
    """Week-over-week telemetry tracking for optimization validation."""

    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler

    def get_baseline_metrics(self) -> Dict[str, Any]:
        """Get baseline metrics from 7 days ago (simulated or historical)."""
        baseline_date = datetime.now() - timedelta(days=7)
        # We calculate P95 and error rate for the 7-day period ending 7 days ago
        return {
            'p95_latency_ms': self._get_p95_latency(baseline_date),
            'error_rate': self._get_error_rate(baseline_date),
            'cost_usd': self._get_cost_usd(baseline_date),
            'timestamp': baseline_date
        }

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current week metrics."""
        return {
            'p95_latency_ms': self._get_p95_latency(datetime.now()),
            'error_rate': self._get_error_rate(datetime.now()),
            'cost_usd': self._get_cost_usd(datetime.now()),
            'timestamp': datetime.now()
        }

    def calculate_wow_improvement(self) -> Dict[str, Any]:
        """Calculate week-over-week improvement percentage."""
        baseline = self.get_baseline_metrics()
        current = self.get_current_metrics()

        improvements = {}
        for metric in ['p95_latency_ms', 'error_rate', 'cost_usd']:
            baseline_val = baseline[metric]
            current_val = current[metric]

            if baseline_val == 0:
                improvements[metric] = 0.0
            else:
                # For latency/cost/errors: lower is better, so improvement is reduction
                improvement = ((baseline_val - current_val) / baseline_val) * 100
                improvements[metric] = round(improvement, 2)

        return {
            'baseline': baseline,
            'current': current,
            'improvements': improvements,
            'trend': 'improving' if all(v >= 0 for v in improvements.values()) else 'mixed'
        }

    def _get_p95_latency(self, date: datetime) -> float:
        """Calculate P95 latency for a 7-day window ending at date."""
        start = date - timedelta(days=7)
        end = date
        api_calls = [
            c for c in self.profiler.metrics.get('api_calls', [])
            if start <= c['timestamp'] <= end
        ]

        if not api_calls:
            # Fallback to queries if no API calls
            api_calls = [
                c for c in self.profiler.metrics.get('queries', [])
                if start <= c['timestamp'] <= end
            ]

        if not api_calls:
            return 0.0

        durations = sorted([c['duration_ms'] for c in api_calls])
        p95_index = int(len(durations) * 0.95)
        return durations[p95_index] if p95_index < len(durations) else durations[-1]

    def _get_error_rate(self, date: datetime) -> float:
        """Calculate error rate for a 7-day window ending at date."""
        start = date - timedelta(days=7)
        end = date
        api_calls = [
            c for c in self.profiler.metrics.get('api_calls', [])
            if start <= c['timestamp'] <= end
        ]

        if not api_calls:
            return 0.0

        error_calls = [c for c in api_calls if c['status_code'] >= 400]
        return (len(error_calls) / len(api_calls)) * 100

    def _get_cost_usd(self, date: datetime) -> float:
        """Estimate cost for date (Placeholder)."""
        return 0.0

    def render_dashboard(self) -> str:
        """Render dashboard as string."""
        wow = self.calculate_wow_improvement()

        dashboard = f"""
TELEMETRY DASHBOARD - Week-over-Week Trends
{'=' * 50}

BASELINE (Historical window):
  P95 Latency: {wow['baseline']['p95_latency_ms']:.0f}ms
  Error Rate:  {wow['baseline']['error_rate']:.2f}%
  Cost:        ${wow['baseline']['cost_usd']:.2f}

CURRENT (Active window):
  P95 Latency: {wow['current']['p95_latency_ms']:.0f}ms
  Error Rate:  {wow['current']['error_rate']:.2f}%
  Cost:        ${wow['current']['cost_usd']:.2f}

WEEK-OVER-WEEK IMPROVEMENT:
  P95 Latency: {wow['improvements']['p95_latency_ms']:+.2f}%
  Error Rate:  {wow['improvements']['error_rate']:+.2f}%
  Cost:        {wow['improvements']['cost_usd']:+.2f}%

Trend: {wow['trend'].upper()}
"""
        return dashboard
