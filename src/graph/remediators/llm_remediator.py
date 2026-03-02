from src.graph.remediators.code_remediator import CodeRemediator
from src.graph.fix_generator import FixGenerator
from src.graph.sandbox_verifier import SandboxRunner
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class LLMRemediator(CodeRemediator):
    """Remediator for code failures using LLM-generated fixes."""

    def __init__(self):
        super().__init__()
        self.fix_generator = FixGenerator()
        self.sandbox = SandboxRunner()

    @property
    def service_name(self) -> str:
        return "llm_code_remediator"

    def detect(self, parameters: Dict) -> bool:
        """Detect if this remediator can handle the failure."""
        # Handle code failures (from classifier)
        return parameters.get('error_type') in [
            'SyntaxError', 'ImportError', 'ModuleNotFoundError', 
            'AttributeError', 'TypeError', 'NameError', 'KeyError'
        ]

    def remediate(self, parameters: Dict) -> Dict:
        """Generate and verify fix using sandbox."""
        # Step 1: Generate fix
        fix, confidence = self.fix_generator.generate_fix(
            error_type=parameters['error_type'],
            error_message=parameters['error_message'],
            affected_module=parameters['affected_module'],
            traceback=parameters.get('traceback', ''),
            classification_evidence=parameters.get('classification_evidence', {})
        )

        if fix.get('type') == 'failed':
            return {'success': False, 'error': fix.get('error')}

        # Step 2: Verify in sandbox
        try:
            sandbox_result = self.sandbox.run_verification(
                changed_files=fix.get('changed_files', {}),
                changed_tests=[]
            )
        except Exception as e:
            logger.error(f"Sandbox verification failed: {e}")
            return {
                'success': False, 
                'error': f"Sandbox failure: {str(e)}",
                'fix': fix
            }

        # Step 3: Route based on sandbox verdict and confidence
        verdict = sandbox_result.get('verdict', 'RED')
        run_id = sandbox_result.get('run_id')

        if verdict == 'GREEN' and confidence >= 0.9:
            # Phase 15.2: Auto-apply (future)
            return {
                'success': True,
                'action': 'auto_apply_ready',  # Not yet auto-applied in Phase 15.0
                'fix': fix,
                'sandbox_run_id': run_id,
                'confidence': confidence,
                'sandbox_result': sandbox_result
            }
        elif verdict == 'GREEN' and confidence >= 0.7:
            # Create approval queue entry
            return {
                'success': True,
                'action': 'approval_required',
                'fix': fix,
                'sandbox_run_id': run_id,
                'confidence': confidence,
                'sandbox_result': sandbox_result
            }
        else:
            # Block - sandbox failed or low confidence
            return {
                'success': False,
                'action': 'blocked',
                'reason': f"Sandbox verdict: {verdict}, confidence: {confidence}",
                'sandbox_run_id': run_id,
                'sandbox_result': sandbox_result,
                'fix': fix
            }

    def describe(self) -> str:
        return "LLM-powered code remediator with sandbox verification"
