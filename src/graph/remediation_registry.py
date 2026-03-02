"""
Remediation Registry (NullClaw-inspired).
A centralized 'heap' of tools that the Universal Fixer can pull from.
"""

import logging
import os
import importlib.util
from typing import Dict, Any, List, Type, Optional
from src.graph.universal_fixer import UniversalRemediator

logger = logging.getLogger(__name__)

class RemediationRegistry:
    def __init__(self):
        self._tools: Dict[str, UniversalRemediator] = {}
        self.tool_dir = "src/graph/remediators"

    def register(self, tool: UniversalRemediator):
        """Manually register a tool instance."""
        self._tools[tool.service_name] = tool
        logger.info(f"🛠️ Registered tool: {tool.service_name}")

    def get_tool(self, service_name: str) -> Optional[UniversalRemediator]:
        """Fetch a tool from the heap."""
        return self._tools.get(service_name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def auto_discover(self):
        """
        Dynamically load all remediator classes from the remediators directory.
        This is the 'Dynamic Heap' logic.
        """
        if not os.path.exists(self.tool_dir):
            os.makedirs(self.tool_dir, exist_ok=True)
            return

        for filename in os.listdir(self.tool_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"src.graph.remediators.{filename[:-3]}"
                
                try:
                    # Dynamic Import
                    module = importlib.import_module(module_name)
                    
                    # Look for classes that implement UniversalRemediator
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, UniversalRemediator) and 
                            attr is not UniversalRemediator):
                            instance = attr()
                            self.register(instance)
                except Exception as e:
                    logger.error(f"Failed to load remediator module {module_name}: {e}")

# Singleton registry
registry = RemediationRegistry()
registry.auto_discover()
