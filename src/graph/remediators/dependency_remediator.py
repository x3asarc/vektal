"""
Dependency installation and verification remediator.
Handles missing Python dependencies with automatic installation and import verification.
"""

from __future__ import annotations
import subprocess
import sys
import re
import logging
from typing import Dict, Any, Optional
from src.graph.universal_fixer import UniversalRemediator, RemediationResult

logger = logging.getLogger(__name__)


class DependencyRemediator(UniversalRemediator):
    """Install and verify missing Python dependencies."""

    # Map import names to PyPI package names
    PACKAGE_MAP = {
        "graphiti_core": "graphiti-core",
        "neo4j": "neo4j",
        "sentry_sdk": "sentry-sdk",  # Added for sentry-sdk support
        "flask_openapi3": "flask-openapi3",
        "flask_login": "flask-login",
        "flask_cors": "flask-cors",
        "celery": "celery",
        "redis": "redis",
        "psycopg": "psycopg[binary]",
        "sentence_transformers": "sentence-transformers",
        "requests_mock": "requests-mock",
        "typer": "typer",
    }

    @property
    def service_name(self) -> str:
        return "dependencies"

    @property
    def description(self) -> str:
        return "Install and verify Python dependencies with automatic package mapping"

    async def validate_environment(self) -> bool:
        """Check if pip is available."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning("pip validation failed: %s", e)
            return False

    async def diagnose_and_fix(
        self, params: Optional[Dict[str, Any]] = None
    ) -> RemediationResult:
        """Install missing dependency and verify import."""
        error_message = params.get("error_message", "") if params else ""
        affected_module = params.get("affected_module", "") if params else ""

        # Extract module name from error message or affected_module
        module_name = self._extract_module_name(error_message, affected_module)
        if not module_name:
            return RemediationResult(
                False,
                "Could not extract module name from error",
                ["module_extraction_failed"],
                error_details=f"Error: {error_message}, Module: {affected_module}",
            )

        # Map to package name
        package_name = self.PACKAGE_MAP.get(module_name, module_name)

        logger.info("Installing dependency: %s (package: %s)", module_name, package_name)

        # Install package
        actions = [f"pip_install_{package_name}"]
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return RemediationResult(
                    False,
                    f"Failed to install {package_name}",
                    actions + ["install_failed"],
                    error_details=result.stderr,
                )

            actions.append("install_success")
            logger.info("Successfully installed %s", package_name)

        except subprocess.TimeoutExpired:
            return RemediationResult(
                False,
                f"Installation timeout for {package_name}",
                actions + ["install_timeout"],
            )
        except Exception as e:
            return RemediationResult(
                False,
                f"Installation exception: {str(e)}",
                actions + ["install_exception"],
                error_details=str(e),
            )

        # Verify import
        actions.append(f"verify_import_{module_name}")
        try:
            verify = subprocess.run(
                [sys.executable, "-c", f"import {module_name}"],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if verify.returncode != 0:
                return RemediationResult(
                    False,
                    f"Installed {package_name} but import still fails",
                    actions + ["import_verification_failed"],
                    error_details=verify.stderr,
                )

            actions.append("import_verification_success")
            logger.info("Successfully verified import of %s", module_name)

            return RemediationResult(
                True,
                f"Successfully installed and verified {package_name}",
                actions,
                output=f"Module {module_name} is now available",
            )

        except Exception as e:
            return RemediationResult(
                False,
                f"Import verification exception: {str(e)}",
                actions + ["verification_exception"],
                error_details=str(e),
            )

    def _extract_module_name(
        self, error_message: str, affected_module: str
    ) -> Optional[str]:
        """Extract module name from error message or affected_module."""
        # Try error message first
        if error_message:
            # Pattern: "Module 'xxx' not found" or "No module named 'xxx'"
            match = re.search(
                r"(?:Module|module named)\s+['\"]([^'\"]+)['\"]", error_message
            )
            if match:
                return match.group(1)

            # Pattern: "ModuleNotFoundError: xxx" or "ImportError: xxx"
            match = re.search(r"(?:ModuleNotFoundError|ImportError):\s*(\w+)", error_message)
            if match:
                return match.group(1)

        # Fallback to affected_module
        if affected_module and affected_module != "dependencies":
            # Extract base module name (e.g., "src.core.graphiti_client" -> "graphiti_client")
            # But also check if it's a known package
            parts = affected_module.split(".")
            for part in reversed(parts):
                if part in self.PACKAGE_MAP:
                    return part

        return None
