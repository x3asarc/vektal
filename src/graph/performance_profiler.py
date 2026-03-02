import time
import psutil
import json
import os
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event, Thread

METRICS_FILE = Path(".graph/performance-metrics.jsonl")

class PerformanceProfiler:
    """Collects performance metrics without impacting app performance."""

    def __init__(self, persistence_enabled: bool = True):
        self.metrics = defaultdict(list)
        self.persistence_enabled = persistence_enabled
        if self.persistence_enabled:
            METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._load_recent_metrics()

    def _load_recent_metrics(self):
        """Load metrics from the last 24 hours."""
        if not METRICS_FILE.exists():
            return
            
        threshold = datetime.now() - timedelta(hours=24)
        try:
            with METRICS_FILE.open('r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        ts = datetime.fromisoformat(entry['timestamp'])
                        if ts > threshold:
                            entry['timestamp'] = ts
                            category = entry.get('category', 'unknown')
                            self.metrics[category].append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to load metrics: {e}")

    def _persist_entry(self, entry: Dict):
        """Append entry to metrics file."""
        if not self.persistence_enabled:
            return
            
        # Convert datetime to string for JSON serialization
        persist_copy = entry.copy()
        if isinstance(persist_copy.get('timestamp'), datetime):
            persist_copy['timestamp'] = persist_copy['timestamp'].isoformat()
            
        try:
            with METRICS_FILE.open('a', encoding='utf-8') as f:
                f.write(json.dumps(persist_copy) + '\n')
        except Exception:
            pass

    def record_query_time(self, query_name: str, duration_ms: float):
        """Record database query execution time."""
        entry = {
            'category': 'queries',
            'name': query_name,
            'duration_ms': duration_ms,
            'timestamp': datetime.now()
        }
        self.metrics['queries'].append(entry)
        self._persist_entry(entry)

    def record_api_call(self, endpoint: str, duration_ms: float, status_code: int):
        """Record API call metrics."""
        entry = {
            'category': 'api_calls',
            'endpoint': endpoint,
            'duration_ms': duration_ms,
            'status_code': status_code,
            'timestamp': datetime.now()
        }
        self.metrics['api_calls'].append(entry)
        self._persist_entry(entry)

    def record_system_snapshot(self):
        """Record periodic process-level telemetry for background profiling."""
        mem = self.get_memory_usage()
        entry = {
            'category': 'system',
            'rss_mb': mem['rss_mb'],
            'vms_mb': mem['vms_mb'],
            'memory_percent': mem['percent'],
            'timestamp': datetime.now()
        }
        self.metrics['system'].append(entry)
        self._persist_entry(entry)

    def get_slow_queries(self, threshold_ms: float = 1000) -> List[Dict]:
        """Identify queries exceeding threshold."""
        recent = datetime.now() - timedelta(hours=1)
        return [
            q for q in self.metrics['queries']
            if q['duration_ms'] > threshold_ms and q['timestamp'] > recent
        ]

    def get_memory_usage(self) -> Dict:
        """Get current memory usage."""
        process = psutil.Process()
        mem = process.memory_info()
        return {
            'rss_mb': mem.rss / 1024 / 1024,
            'vms_mb': mem.vms / 1024 / 1024,
            'percent': process.memory_percent()
        }

    def analyze_bottlenecks(self) -> List[Dict]:
        """Analyze metrics to find bottlenecks."""
        bottlenecks = []

        # Slow queries
        slow_queries = self.get_slow_queries(threshold_ms=1000)
        if slow_queries:
            query_counts = defaultdict(list)
            for q in slow_queries:
                query_counts[q['name']].append(q['duration_ms'])

            for query_name, durations in query_counts.items():
                if len(durations) >= 5:  # Repeatedly slow
                    bottlenecks.append({
                        'type': 'slow_query',
                        'query': query_name,
                        'occurrences': len(durations),
                        'avg_duration_ms': sum(durations) / len(durations)
                    })

        # High memory
        mem = self.get_memory_usage()
        if mem['percent'] > 80:
            bottlenecks.append({
                'type': 'high_memory',
                'percent': mem['percent'],
                'rss_mb': mem['rss_mb']
            })

        # Excessive API pressure (short-window burst detection)
        burst_window = datetime.now() - timedelta(minutes=1)
        recent_calls = [
            call for call in self.metrics['api_calls']
            if call['timestamp'] >= burst_window
        ]
        if len(recent_calls) >= 300:
            bottlenecks.append({
                'type': 'excessive_api_calls',
                'calls_last_minute': len(recent_calls)
            })

        return bottlenecks

    def run_background_profiler(
        self,
        interval_seconds: int = 60,
        stop_event: Optional[Event] = None,
        once: bool = False,
    ) -> int:
        """
        Continuous background profiling loop (non-blocking when run in thread).
        Returns the number of snapshots recorded.
        """
        interval_seconds = max(1, int(interval_seconds))
        stop_event = stop_event or Event()
        snapshots = 0

        while True:
            self.record_system_snapshot()
            snapshots += 1
            if once:
                break
            if stop_event.wait(interval_seconds):
                break
        return snapshots

    def start_background_profiler_thread(self, interval_seconds: int = 60) -> tuple[Thread, Event]:
        """
        Start continuous profiling in a daemon thread.
        """
        stop_event = Event()
        thread = Thread(
            target=self.run_background_profiler,
            kwargs={"interval_seconds": interval_seconds, "stop_event": stop_event},
            daemon=True,
            name="performance-profiler",
        )
        thread.start()
        return thread, stop_event
