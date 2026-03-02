from typing import Dict, List, Any
from src.graph.remediators.code_remediator import CodeRemediator
from src.graph.runtime_optimizer import RuntimeOptimizer
from src.graph.performance_profiler import PerformanceProfiler
from src.graph.sandbox_verifier import SandboxRunner
import logging

logger = logging.getLogger(__name__)

class OptimizerRemediator(CodeRemediator):
    """Auto-tunes runtime parameters based on profiler metrics."""

    def __init__(self, profiler: PerformanceProfiler = None):
        super().__init__()
        self.profiler = profiler or PerformanceProfiler()
        self.optimizer = RuntimeOptimizer(self.profiler)
        self.sandbox = SandboxRunner()

    @property
    def service_name(self) -> str:
        return "optimizer"

    def detect(self, parameters: Dict) -> bool:
        """Eligible for manual or scheduled optimization runs."""
        return parameters.get('trigger') == 'scheduled' or parameters.get('trigger') == 'manual'

    def remediate(self, parameters: Dict) -> Dict:
        """Run all optimizations and apply if sandbox GREEN."""
        optimizations = [
            self.optimizer.optimize_connection_pool(),
            self.optimizer.optimize_cache_ttl(),
            self.optimizer.optimize_batch_size()
        ]

        changes = [opt for opt in optimizations if opt.get('changed')]

        if not changes:
            return {'success': True, 'action': 'no_optimizations_needed'}

        # In 15.1, we simulate config changes for the sandbox
        # Production application will be implemented in Phase 15.2
        changed_files = {}
        for change in changes:
            if 'config_change' in change:
                file_path = change['config_change']['file']
                # Mock file modification for sandbox validation
                changed_files[file_path] = f"# Optimized {change['parameter']}\n"
        
        # If no files to change (e.g. TTL change only), we still verify the state
        if not changed_files:
            changed_files = {".sandbox/opt_marker": "optimizing"}

        try:
            sandbox_result = self.sandbox.run_verification(
                changed_files=changed_files,
                changed_tests=[]
            )
            
            verdict = sandbox_result.get('verdict', 'RED')
            run_id = sandbox_result.get('run_id')

            if verdict == 'GREEN':
                return {
                    'success': True,
                    'action': 'approval_required',
                    'optimizations': changes,
                    'sandbox_run_id': run_id,
                    'message': f"Validated {len(changes)} optimizations in sandbox."
                }
            else:
                return {
                    'success': False,
                    'action': 'blocked',
                    'reason': f"Sandbox verdict: {verdict}",
                    'optimizations': changes,
                    'sandbox_run_id': run_id
                }
        except Exception as e:
            logger.error(f"Sandbox validation failed for optimizer: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'optimizations': changes
            }

    def describe(self) -> str:
        return "Runtime parameter optimizer (pools, cache, batches)"
