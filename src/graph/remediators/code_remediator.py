"""
Code Remediator Base (Phase 15).
Specialized remediator for source code and configuration changes.
Integrates with the Universal Sandbox for 6-gate verification.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from src.graph.universal_fixer import UniversalRemediator, RemediationResult
from src.graph.sandbox_verifier import SandboxRunner

logger = logging.getLogger(__name__)

class CodeRemediator(UniversalRemediator):
    """
    Base class for remediators that modify source code.
    Enforces sandbox verification before reporting success.
    """
    
    def __init__(self):
        self.sandbox = SandboxRunner()

    @property
    def service_name(self) -> str:
        return "code_fix"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "object",
                    "description": "Map of file paths to new contents",
                    "additionalProperties": {"type": "string"}
                },
                "tests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of test paths to run"
                }
            },
            "required": ["files"]
        }

    async def validate_environment(self) -> bool:
        """Verify sandbox environment is ready."""
        try:
            return self.sandbox.sandbox_base_dir.exists()
        except Exception:
            return False

    async def diagnose_and_fix(self, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        """
        1. Setup Sandbox
        2. Apply Fix
        3. Run 6-Gate Verification
        4. Apply to Production (if success)
        """
        if not params or "files" not in params:
            return RemediationResult(False, "Missing 'files' parameter", ["Validation"])

        # 1. Sandbox Verification
        logger.info("🧪 [CodeRemediator] Starting sandbox verification...")
        verification = await self.sandbox.verify_fix(params)
        
        actions = [f"Sandbox run {verification.run_id}"]
        for gate in verification.gates:
            actions.append(f"Gate {gate.name}: {gate.status}")

        if not verification.success:
            return RemediationResult(
                False, 
                f"Sandbox verification failed: {verification.error_details or 'Gate failure'}",
                actions
            )

        # 2. Apply to Production
        # In this base class, we just log the intent. 
        # Subclasses or the orchestrator will handle the actual file write.
        logger.info("✅ [CodeRemediator] Sandbox PASSED. Ready to apply to production.")
        
        return RemediationResult(
            True,
            "Code changes verified in sandbox and ready for apply.",
            actions,
            output=json.dumps({"run_id": verification.run_id}, indent=2)
        )
