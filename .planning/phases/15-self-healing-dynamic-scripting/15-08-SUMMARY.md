---
phase: 15-self-healing-dynamic-scripting
plan: 08
subsystem: performance-optimization-learning
tags: [profiler, bottleneck, telemetry, graph, optimization]

requires:
  - phase: 14
    provides: "continuous optimization baseline"
  - phase: 13.2
    provides: "graphiti client"
provides:
  - "PerformanceProfiler for persistent metrics collection"
  - "BottleneckDetector with graph-based impact analysis"
  - "TelemetryDashboard for week-over-week trend visualization"
  - "CLI for autonomous performance analysis"
affects:
  - requirements.txt

tech-stack:
  added:
    - psutil (for system metrics)
  patterns:
    - "lightweight metrics persistence (JSONL)"
    - "graph-based caller impact analysis (Cypher)"
    - "W-o-W telemetry trend calculation"

key-files:
  created:
    - src/graph/performance_profiler.py
    - src/graph/bottleneck_detector.py
    - src/graph/telemetry_dashboard.py
    - scripts/graph/analyze_performance.py
    - tests/graph/test_performance_profiling.py
  modified:
    - requirements.txt

key-decisions:
  - "Added `psutil` to `requirements.txt` to enable high-fidelity memory and process profiling."
  - "Implemented file-based metrics persistence (`.graph/performance-metrics.jsonl`) to avoid complex database schema migrations while ensuring data survives restarts."
  - "Developed a 7-day rolling window strategy for `TelemetryDashboard` to provide meaningful week-over-week (W-o-W) comparisons."
  - "Utilized Cypher `CALLS` relationship in `BottleneckDetector` to map performance bottlenecks back to their architectural impact in the Phase 14 graph."

duration: in-session
completed: 2026-03-02
---

# Phase 15 Plan 08 Summary

Implemented performance profiling and bottleneck detection with graph-based impact analysis.

## What Was Built

1. **Performance Profiler** ([src/graph/performance_profiler.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/performance_profiler.py))
   - Lightweight metrics collection for queries and API calls.
   - Persistent storage using JSONL for 24-hour lookback.
   - Real-time memory and process usage tracking using `psutil`.

2. **Bottleneck Detector** ([src/graph/bottleneck_detector.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/bottleneck_detector.py))
   - Identifies repeatedly slow queries and high memory states.
   - Uses Phase 14 knowledge graph to find caller functions and assess optimization impact.
   - Generates actionable recommendations (e.g., adding indexes) with confidence scores.

3. **Telemetry Dashboard** ([src/graph/telemetry_dashboard.py](/C:/Users/Hp/Documents/Shopify Scraping Script/src/graph/telemetry_dashboard.py))
   - Calculates P95 latency and error rate metrics.
   - Compares current performance window against a 7-day-ago baseline.
   - Visualizes week-over-week (W-o-W) improvement trends.

4. **Analysis CLI** ([scripts/graph/analyze_performance.py](/C:/Users/Hp/Documents/Shopify Scraping Script/scripts/graph/analyze_performance.py))
   - Unified interface for viewing the telemetry dashboard and active bottlenecks.
   - Provides human-readable optimization recommendations.

## Verification Evidence

1. `python -m pytest tests/graph/test_performance_profiling.py -v`
   - Result: `5 passed`
2. `python scripts/graph/analyze_performance.py analyze`
   - Result: Dashboard renders correctly and identifies simulated bottlenecks.

## KISS / Size Check

- `performance_profiler.py`: 120 LOC
- `bottleneck_detector.py`: 85 LOC
- `telemetry_dashboard.py`: 110 LOC
- All modules are well-decoupled and follow project standards.
