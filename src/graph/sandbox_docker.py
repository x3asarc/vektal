"""Docker runtime wrapper used by sandbox verification."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DockerSandboxRuntime:
    """Thin adapter around docker-py for hardened container execution."""

    def __init__(self, image: str, seccomp_profile_path: Path) -> None:
        self.image = image
        self.seccomp_profile_path = seccomp_profile_path

    def create_client(self) -> Any:
        try:
            import docker  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "docker SDK is not installed. Install package `docker`."
            ) from exc

        try:
            client = docker.from_env()
            client.ping()
        except Exception as exc:
            raise RuntimeError(
                "Docker daemon is not reachable. Start Docker Desktop/daemon."
            ) from exc
        return client

    def build_run_kwargs(self, run_dir: Path) -> dict[str, Any]:
        security_opt = ["no-new-privileges:true"]
        if self.seccomp_profile_path.exists():
            security_opt.append(f"seccomp={self.seccomp_profile_path.resolve()}")
        else:
            logger.warning(
                "Seccomp profile missing at %s; using runtime default.",
                self.seccomp_profile_path,
            )

        return {
            "image": self.image,
            "command": ["sh", "-lc", "sleep 1200"],
            "detach": True,
            "working_dir": "/app",
            "network_mode": "none",
            "mem_limit": "512m",
            "mem_reservation": "256m",
            "cpu_period": 100000,
            "cpu_quota": 50000,
            "pids_limit": 100,
            "read_only": True,
            "user": "1000:1000",
            "tmpfs": {"/tmp": "rw,size=104857600"},
            "volumes": {str(run_dir.resolve()): {"bind": "/app", "mode": "rw"}},
            "security_opt": security_opt,
            "cap_drop": ["ALL"],
            "init": True,
            "auto_remove": False,
        }

    def start(self, run_dir: Path) -> tuple[Any, Any]:
        client = self.create_client()
        container = client.containers.run(**self.build_run_kwargs(run_dir))
        return client, container

    def stop(self, container: Any) -> str:
        try:
            logs = container.logs(tail=100).decode("utf-8", errors="ignore")
        except Exception:
            logs = ""
        try:
            container.remove(force=True)
        except Exception:
            pass
        return f"container_stopped:{getattr(container, 'id', 'unknown')}\n{logs}".strip()

    def run_command(
        self,
        *,
        container: Any,
        command: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def _target() -> None:
            try:
                exit_code, output = container.exec_run(
                    ["sh", "-lc", command],
                    workdir="/app",
                    demux=False,
                )
                if isinstance(output, (bytes, bytearray)):
                    text = output.decode("utf-8", errors="ignore")
                else:
                    text = str(output)
                result["exit_code"] = int(exit_code)
                result["output"] = text[-10000:]
            except Exception as exc:
                result["exit_code"] = 1
                result["output"] = f"Container command error: {exc}"

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)
        if thread.is_alive():
            return {
                "exit_code": 124,
                "output": f"Command timed out after {timeout_seconds}s: {command}",
                "timed_out": True,
            }
        return {
            "exit_code": int(result.get("exit_code", 1)),
            "output": str(result.get("output", "")),
            "timed_out": False,
        }
