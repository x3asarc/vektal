from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)

class ABTestValidator:
    """A/B test validator for optimization validation."""

    def __init__(self):
        self.active_tests = {}

    def create_test(self, optimization_id: str, parameter: str, baseline_value: Any, treatment_value: Any) -> str:
        """Create new A/B test for optimization."""
        test_id = f"ab_{optimization_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.active_tests[test_id] = {
            'optimization_id': optimization_id,
            'parameter': parameter,
            'baseline_value': baseline_value,
            'treatment_value': treatment_value,
            'start_time': datetime.now(),
            'end_time': None,
            'control_metrics': [],
            'treatment_metrics': [],
            'status': 'running'
        }
        
        logger.info(f"Created A/B test {test_id} for {parameter} ({baseline_value} vs {treatment_value})")
        return test_id

    def record_metric(self, test_id: str, group: str, metric_name: str, value: float):
        """Record metric for control or treatment group."""
        if test_id not in self.active_tests:
            return

        test = self.active_tests[test_id]
        metric = {
            'name': metric_name,
            'value': float(value),
            'timestamp': datetime.now()
        }

        if group == 'control':
            test['control_metrics'].append(metric)
        elif group == 'treatment':
            test['treatment_metrics'].append(metric)

    def analyze_test(self, test_id: str, metric_name: str = 'latency_ms') -> Dict[str, Any]:
        """Analyze A/B test results with statistical significance."""
        if test_id not in self.active_tests:
            return {'error': 'test_not_found'}

        test = self.active_tests[test_id]

        # Extract metric values
        control_values = [m['value'] for m in test['control_metrics'] if m['name'] == metric_name]
        treatment_values = [m['value'] for m in test['treatment_metrics'] if m['name'] == metric_name]

        # Minimum sample size: 30 (Success Criterion 8)
        if len(control_values) < 30 or len(treatment_values) < 30:
            return {
                'status': 'insufficient_data',
                'control_n': len(control_values),
                'treatment_n': len(treatment_values),
                'required_n': 30
            }

        # T-test for statistical significance (p < 0.05)
        t_stat, p_value = stats.ttest_ind(control_values, treatment_values)

        control_mean = np.mean(control_values)
        treatment_mean = np.mean(treatment_values)
        
        # For latency/errors: lower is better
        improvement = ((control_mean - treatment_mean) / control_mean) * 100 if control_mean != 0 else 0

        # Declare winner if p < 0.05
        significant = bool(p_value < 0.05)

        winner = None
        if significant:
            if treatment_mean < control_mean:
                winner = 'treatment'
            else:
                winner = 'control'

        return {
            'status': 'complete',
            'statistically_significant': significant,
            'p_value': float(p_value),
            'control_mean': float(control_mean),
            'treatment_mean': float(treatment_mean),
            'improvement_percent': float(improvement),
            'winner': winner,
            'recommendation': 'apply_treatment' if winner == 'treatment' else 'revert_to_baseline'
        }

    def finalize_test(self, test_id: str) -> Dict[str, Any]:
        """Finalize test and return verdict."""
        analysis = self.analyze_test(test_id)

        if test_id in self.active_tests:
            if analysis['status'] == 'complete':
                self.active_tests[test_id]['status'] = 'complete'
                self.active_tests[test_id]['end_time'] = datetime.now()
            self.active_tests[test_id]['analysis'] = analysis

        return analysis
