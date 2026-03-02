import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from src.graph.performance_profiler import PerformanceProfiler
from src.graph.bottleneck_detector import BottleneckDetector
from src.graph.telemetry_dashboard import TelemetryDashboard

@pytest.fixture
def profiler():
    return PerformanceProfiler(persistence_enabled=False)

def test_profiler_collection(profiler):
    profiler.record_query_time("SELECT 1", 500)
    profiler.record_api_call("/api/v1/chat", 200, 200)
    
    assert len(profiler.metrics['queries']) == 1
    assert len(profiler.metrics['api_calls']) == 1
    assert profiler.metrics['queries'][0]['duration_ms'] == 500

def test_bottleneck_detection(profiler):
    # Record 5 slow queries of same name
    for _ in range(5):
        profiler.record_query_time("SLOW_QUERY", 1500)
        
    bottlenecks = profiler.analyze_bottlenecks()
    assert len(bottlenecks) == 1
    assert bottlenecks[0]['type'] == 'slow_query'
    assert bottlenecks[0]['query'] == 'SLOW_QUERY'

def test_recommendation_generation():
    mock_graph = MagicMock()
    mock_graph.execute_query.side_effect = [
        [],
        [{"caller_name": "worker_task"}],
    ]
    
    detector = BottleneckDetector(graph_client=mock_graph)
    bottleneck = {'type': 'slow_query', 'query': 'SLOW_QUERY'}
    
    recs = detector.generate_recommendations(bottleneck)
    assert len(recs) == 1
    assert recs[0]['action'] == 'add_index'
    assert recs[0]['impact']['caller_count'] == 1
    # Verify fallback query path is using CallsEdge pattern.
    assert "CallsEdge" in mock_graph.execute_query.call_args_list[1].args[0]

def test_telemetry_dashboard(profiler):
    # Setup some historical data (within the 7-day window ending 7 days ago)
    # Baseline window for TelemetryDashboard: [now - 14d, now - 7d]
    past = datetime.now() - timedelta(days=10)
    profiler.metrics['api_calls'].append({'endpoint': '/a', 'duration_ms': 1000, 'status_code': 200, 'timestamp': past})
    
    # Setup current data (within the 7-day window ending now)
    # Current window: [now - 7d, now]
    current = datetime.now() - timedelta(days=2)
    profiler.metrics['api_calls'].append({'endpoint': '/b', 'duration_ms': 500, 'status_code': 200, 'timestamp': current})
    
    dashboard = TelemetryDashboard(profiler)
    wow = dashboard.calculate_wow_improvement()
    
    # 1000ms -> 500ms = 50% improvement
    assert wow['improvements']['p95_latency_ms'] == 50.0
    assert wow['trend'] == 'improving'

def test_memory_usage(profiler):
    mem = profiler.get_memory_usage()
    assert 'rss_mb' in mem
    assert 'percent' in mem
    assert mem['percent'] >= 0


def test_background_profiler_loop_once(profiler):
    snapshots = profiler.run_background_profiler(interval_seconds=1, once=True)
    assert snapshots == 1
    assert len(profiler.metrics['system']) == 1


def test_excessive_api_calls_detection(profiler):
    now = datetime.now()
    for _ in range(300):
        profiler.metrics['api_calls'].append(
            {'endpoint': '/api/v1/chat', 'duration_ms': 50, 'status_code': 200, 'timestamp': now}
        )
    bottlenecks = profiler.analyze_bottlenecks()
    assert any(b['type'] == 'excessive_api_calls' for b in bottlenecks)
