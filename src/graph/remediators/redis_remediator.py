"""
Redis Remediator Tool.
Autonomous diagnosis and repair for Redis connectivity.
"""

import os
import socket
import subprocess
import time
import shutil
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from src.graph.universal_fixer import UniversalRemediator, RemediationResult

class RedisRemediator(UniversalRemediator):
    @property
    def service_name(self) -> str:
        return "redis"

    @property
    def description(self) -> str:
        return "Fixes Redis connectivity issues and starts container via Compose."

    async def validate_environment(self) -> bool:
        """Check if docker is available for potential fix."""
        return shutil.which("docker") is not None

    def _check_port(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except:
            return False

    async def diagnose_and_fix(self, params: Optional[Dict[str, Any]] = None) -> RemediationResult:
        actions = []
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379

        # 1. Diagnostic Probe
        if self._check_port(host, port):
            return RemediationResult(True, "Redis is already healthy", ["Ping check"])

        actions.append(f"Detected failure on {host}:{port}")

        # 2. Host Mismatch Fix (Docker vs Local)
        if host == "redis":
            actions.append("Detected 'redis' host outside container context. Attempting localhost switch...")
            if self._check_port("localhost", port):
                os.environ["REDIS_URL"] = redis_url.replace("redis://redis:", "redis://localhost:")
                return RemediationResult(True, "Fixed host mismatch (switched to localhost)", actions)

        # 3. Docker Compose Fix
        actions.append("Attempting docker compose start...")
        try:
            subprocess.run(["docker", "compose", "up", "-d", "redis"], capture_output=True, check=False)
            time.sleep(2) # Warm up
            if self._check_port("localhost", port) or self._check_port(host, port):
                return RemediationResult(True, "Started Redis via Docker", actions)
        except Exception as e:
            actions.append(f"Docker fix failed: {str(e)}")

        return RemediationResult(False, "All remediation paths exhausted", actions)
