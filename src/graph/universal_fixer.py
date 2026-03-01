"""
Universal Infrastructure Fixer (NullClaw-inspired).
Provides a dynamic, layered remediation loop with strict contracts.
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class RemediationResult:
    """Explicit completion signal (NullClaw pattern)."""
    success: bool
    message: str
    actions_taken: List[str] = field(default_factory=list)
    output: Optional[str] = None
    error_details: Optional[str] = None

class UniversalRemediator(ABC):
    """Abstract base with strict metadata and validation (NullClaw vtable pattern)."""
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """The identifier for the service this tool fixes."""
        pass

    @property
    def description(self) -> str:
        """Metadata for the agent to understand tool purpose."""
        return f"Remediator for {self.service_name}"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for tool arguments (NullClaw pattern)."""
        return {}

    @abstractmethod
    async def validate_environment(self) -> bool:
        """Pre-execution check: is this fix even possible? (NullClaw pattern)."""
        pass

    @abstractmethod
    async def diagnose_and_fix(self, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        """The 'Act' phase of the loop."""
        pass

class NanoFixerLoop:
    """The 'NullClaw' loop: Probe -> Validate -> Act -> Verify."""
    def __init__(self, registry):
        self.registry = registry

    async def fix_service(self, service_name: str, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        tool = self.registry.get_tool(service_name)
        if not tool:
            return RemediationResult(False, f"No tool found for {service_name}", [])

        logger.info(f"🧬 [NanoFixer] Attempting fix for {service_name}...")
        
        # 1. Layered Validation (NullClaw pattern)
        if not await tool.validate_environment():
            return RemediationResult(False, f"Environment validation failed for {service_name}", ["Pre-check"])

        # 2. Act
        try:
            result = await tool.diagnose_and_fix(params)
            
            # 3. Log Learning
            self._log_to_master(service_name, result)
            return result
        except Exception as e:
            logger.error(f"NanoFixer loop error: {e}")
            return RemediationResult(False, f"Loop crashed: {str(e)}", ["Execution"])

    def _log_to_master(self, service: str, result: RemediationResult):
        outcome = "SUCCESS" if result.success else "FAILED"
        entry = f"\n### {time.strftime('%Y-%m-%d')} | NanoFixer: {service}\n"
        entry += f"**Outcome:** {outcome}\n"
        entry += f"**Actions:** {', '.join(result.actions_taken)}\n"
        entry += f"**Message:** {result.message}\n"
        if result.error_details:
            entry += f"**Error:** {result.error_details}\n"
        
        # Write to our master learnings source of truth
        with open("LEARNINGS.md", "a", encoding="utf-8") as f:
            f.write(entry)
