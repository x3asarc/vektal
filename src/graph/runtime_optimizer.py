from typing import Dict, Any, Optional
from src.graph.performance_profiler import PerformanceProfiler
import logging

logger = logging.getLogger(__name__)

class RuntimeOptimizer:
    """Auto-tunes runtime parameters based on metrics."""

    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler

    def optimize_connection_pool(self) -> Dict[str, Any]:
        """Adjust connection pool size based on metrics."""
        # Get current pool metrics
        metrics = {
            'requests_waiting': self._get_pool_queue_size(),
            'avg_wait_time_ms': self._get_avg_wait_time(),
            'idle_connections': self._get_idle_connections(),
            'max_overflow_hits': self._get_overflow_hits()
        }

        current_size = self._get_current_pool_size()
        new_size = current_size

        # Decision logic (15-ARCHITECTURE-LOCKED.md Section 10)
        if metrics['requests_waiting'] > 10:
            new_size = min(current_size + 2, 20)  # Max 20
            reason = 'high_queue_depth'
        elif metrics['idle_connections'] > 3:
            # For simplicity in 15.1, we only decrease if idle connections are consistently high
            # In a real system, we'd check historical metrics from the profiler
            new_size = max(current_size - 1, 3)  # Min 3
            reason = 'excessive_idle'
        else:
            return {'changed': False, 'current_size': current_size}

        if new_size == current_size:
            return {'changed': False, 'current_size': current_size}

        return {
            'changed': True,
            'parameter': 'pool_size',
            'old_value': current_size,
            'new_value': new_size,
            'reason': reason,
            'metrics': metrics,
            'config_change': {
                'file': 'src/api/app.py', # Connection pool usually configured in app factory or config
                'parameter': 'SQLALCHEMY_ENGINE_OPTIONS',
                'sub_parameter': 'pool_size',
                'old_value': current_size,
                'new_value': new_size
            }
        }

    def optimize_cache_ttl(self) -> Dict[str, Any]:
        """Adjust cache TTL based on hit rate and memory."""
        mem = self.profiler.get_memory_usage()

        if mem['percent'] > 80:
            return {
                'changed': True,
                'parameter': 'cache_ttl',
                'old_value': 3600,
                'new_value': 1800,  # Reduce from 1h to 30min
                'reason': 'high_memory_usage'
            }

        return {'changed': False}

    def optimize_batch_size(self) -> Dict[str, Any]:
        """Adjust batch sizes based on throughput."""
        # Analyze API call patterns from profiler
        api_calls = self.profiler.metrics.get('api_calls', [])
        if not api_calls:
            return {'changed': False}

        avg_duration = sum(c['duration_ms'] for c in api_calls) / len(api_calls)

        # If API calls are slow, reduce batch size
        if avg_duration > 5000:  # 5s average
            return {
                'changed': True,
                'parameter': 'batch_size',
                'old_value': 50,
                'new_value': 25,
                'reason': 'slow_api_calls'
            }

        return {'changed': False}

    def _get_pool_queue_size(self) -> int:
        try:
            from src.models import db
            if hasattr(db.engine.pool, 'size'):
                return max(0, db.engine.pool.size() - db.engine.pool.checkedin())
        except Exception:
            pass
        return 0

    def _get_avg_wait_time(self) -> float:
        return 0.0  # Placeholder for 15.1

    def _get_idle_connections(self) -> int:
        try:
            from src.models import db
            if hasattr(db.engine.pool, 'checkedin'):
                return db.engine.pool.checkedin()
        except Exception:
            pass
        return 0

    def _get_overflow_hits(self) -> int:
        return 0  # Placeholder for 15.1

    def _get_current_pool_size(self) -> int:
        try:
            from src.models import db
            if hasattr(db.engine.pool, 'size'):
                return db.engine.pool.size()
        except Exception:
            pass
        return 5  # Default SQLAlchemy pool size

    def _idle_for_duration(self, hours: int) -> bool:
        return False  # Placeholder for 15.1
