#!/usr/bin/env python3
"""
Performance Benchmark for Health Gate Hook.

Measures hook execution time to validate <5ms target.
Run with: python tests/daemons/benchmark_health_gate.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.governance import health_gate


def create_realistic_cache(tmp_path: Path) -> Path:
    """Create a realistic health cache for benchmarking."""
    cache = {
        "daemon": {
            "pid": 12345,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "check_interval_seconds": 120,
        },
        "sentry": {
            "status": "issues",
            "issue_count": 3,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "auto_heal_running": True,
        },
        "neo4j": {
            "status": "up",
            "uri": "neo4j+s://12345678.databases.neo4j.io",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "mode": "neo4j",
        },
        "dependencies": {
            "status": "ok",
            "missing": [],
            "last_check": datetime.now(timezone.utc).isoformat(),
        },
    }

    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return cache_file


def benchmark_hook_execution(iterations: int = 100) -> dict:
    """Run benchmark with specified iterations."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache_file = create_realistic_cache(tmp_path)
        log_file = tmp_path / "log.txt"

        times = []
        for _ in range(iterations):
            start = time.perf_counter()

            with mock.patch.object(health_gate, "HEALTH_CACHE_PATH", cache_file):
                with mock.patch.object(health_gate, "LOG_PATH", log_file):
                    result = health_gate.main()

            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

            assert result == 0, "Hook should never block"

        return {
            "iterations": iterations,
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": sum(times) / len(times),
            "median_ms": sorted(times)[len(times) // 2],
            "p95_ms": sorted(times)[int(len(times) * 0.95)],
            "p99_ms": sorted(times)[int(len(times) * 0.99)],
        }


def main() -> int:
    """Main benchmark entry point."""
    print("=" * 60)
    print("Health Gate Hook Performance Benchmark")
    print("=" * 60)
    print()

    # Warmup run
    print("Running warmup (10 iterations)...")
    benchmark_hook_execution(10)
    print("Warmup complete.")
    print()

    # Main benchmark
    print("Running benchmark (100 iterations)...")
    results = benchmark_hook_execution(100)

    print()
    print("Results:")
    print("-" * 60)
    print(f"Iterations:    {results['iterations']}")
    print(f"Min:           {results['min_ms']:.3f}ms")
    print(f"Max:           {results['max_ms']:.3f}ms")
    print(f"Average:       {results['avg_ms']:.3f}ms")
    print(f"Median:        {results['median_ms']:.3f}ms")
    print(f"95th %ile:     {results['p95_ms']:.3f}ms")
    print(f"99th %ile:     {results['p99_ms']:.3f}ms")
    print("-" * 60)
    print()

    # Evaluate against targets
    target_avg = 5.0  # 5ms average target
    target_p99 = 25.0  # 25ms p99 target (Windows I/O can spike)

    if results["avg_ms"] < target_avg:
        print(f"[PASS] Average {results['avg_ms']:.3f}ms < {target_avg}ms target")
    else:
        print(f"[FAIL] Average {results['avg_ms']:.3f}ms > {target_avg}ms target")
        return 1

    if results["p99_ms"] < target_p99:
        print(f"[PASS] P99 {results['p99_ms']:.3f}ms < {target_p99}ms target")
    else:
        print(f"[FAIL] P99 {results['p99_ms']:.3f}ms > {target_p99}ms target")
        return 1

    print()
    print("All performance targets met!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
