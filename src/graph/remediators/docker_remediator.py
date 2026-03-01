"""
Docker Remediator Tool.
Autonomous repair for Docker-based infrastructure.
"""

import subprocess
import shutil
from typing import Dict, Any, Optional
from src.graph.universal_fixer import UniversalRemediator, RemediationResult

class DockerRemediator(UniversalRemediator):
    @property
    def service_name(self) -> str:
        return "docker"

    @property
    def description(self) -> str:
        return "Fixes Docker connectivity and starts containers via Compose."

    async def validate_environment(self) -> bool:
        """Check if Docker CLI is available (NullClaw pre-check)."""
        return shutil.which("docker") is not None

    async def diagnose_and_fix(self, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        actions = []
        target_service = (params or {}).get("service", "redis") # Default to redis if not specified
        
        # 1. Diagnose: Check if daemon is responsive
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                return RemediationResult(
                    False, 
                    "Docker daemon is not responsive", 
                    ["Daemon check"], 
                    error_details=res.stderr
                )
        except Exception as e:
            return RemediationResult(False, f"Docker probe failed: {str(e)}", ["Probe"])

        # 2. Fix: Attempt to start service
        actions.append(f"Attempting to start {target_service} via docker compose...")
        try:
            cmd = ["docker", "compose", "up", "-d", target_service]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if res.returncode == 0:
                return RemediationResult(True, f"Started {target_service} successfully", actions, output=res.stdout)
            else:
                return RemediationResult(
                    False, 
                    f"Failed to start {target_service}", 
                    actions, 
                    error_details=res.stderr
                )
        except Exception as e:
            return RemediationResult(False, f"Compose command failed: {str(e)}", actions)
