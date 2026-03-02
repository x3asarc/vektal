import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.graph.runtime_optimizer import RuntimeOptimizer
from src.graph.ab_test_validator import ABTestValidator
from src.graph.remediators.optimizer_remediator import OptimizerRemediator

@pytest.fixture
def mock_profiler():
    mock = MagicMock()
    mock.get_memory_usage.return_value = {'percent': 50}
    mock.metrics = {'api_calls': []}
    return mock

def test_optimizer_pool_tuning(mock_profiler):
    optimizer = RuntimeOptimizer(mock_profiler)
    
    # Mock database pool with high queue
    with patch("src.graph.runtime_optimizer.RuntimeOptimizer._get_pool_queue_size", return_value=15):
        with patch("src.graph.runtime_optimizer.RuntimeOptimizer._get_current_pool_size", return_value=5):
            result = optimizer.optimize_connection_pool()
            assert result['changed'] is True
            assert result['new_value'] == 7
            assert result['reason'] == 'high_queue_depth'

def test_optimizer_cache_ttl(mock_profiler):
    optimizer = RuntimeOptimizer(mock_profiler)
    
    # High memory -> reduce TTL
    mock_profiler.get_memory_usage.return_value = {'percent': 85}
    result = optimizer.optimize_cache_ttl()
    assert result['changed'] is True
    assert result['new_value'] == 1800
    
    # Normal memory -> no change
    mock_profiler.get_memory_usage.return_value = {'percent': 40}
    result = optimizer.optimize_cache_ttl()
    assert result['changed'] is False

def test_ab_test_statistical_significance():
    validator = ABTestValidator()
    test_id = validator.create_test('opt_1', 'pool_size', 5, 10)
    
    # Control group (mean=100)
    np.random.seed(42)
    control = np.random.normal(100, 10, 50)
    for val in control:
        validator.record_metric(test_id, 'control', 'latency_ms', val)
        
    # Treatment group (mean=80)
    treatment = np.random.normal(80, 10, 50)
    for val in treatment:
        validator.record_metric(test_id, 'treatment', 'latency_ms', val)
        
    analysis = validator.finalize_test(test_id)
    assert analysis['status'] == 'complete'
    assert analysis['statistically_significant'] is True
    assert analysis['winner'] == 'treatment'
    assert analysis['p_value'] < 0.05

def test_ab_test_insufficient_data():
    validator = ABTestValidator()
    test_id = validator.create_test('opt_2', 'batch_size', 50, 25)
    
    for _ in range(10): # < 30
        validator.record_metric(test_id, 'control', 'latency_ms', 100)
        validator.record_metric(test_id, 'treatment', 'latency_ms', 95)
        
    analysis = validator.analyze_test(test_id)
    assert analysis['status'] == 'insufficient_data'

@patch("src.graph.remediators.optimizer_remediator.SandboxRunner")
def test_optimizer_remediator(mock_sandbox_cls, mock_profiler):
    mock_sandbox = mock_sandbox_cls.return_value
    mock_sandbox.run_verification.return_value = {'verdict': 'GREEN', 'run_id': 'run_opt'}
    
    # Ensure some optimization is triggered
    mock_profiler.get_memory_usage.return_value = {'percent': 90}
    
    remediator = OptimizerRemediator(profiler=mock_profiler)
    result = remediator.remediate({'trigger': 'manual'})
    
    assert result['success'] is True
    assert result['action'] == 'approval_required'
    assert len(result['optimizations']) > 0
