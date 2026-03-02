"""Universal Sandbox Verifier orchestration entrypoint."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

from src.graph.sandbox_docker import DockerSandboxRuntime
from src.graph.sandbox_gates import (
    contract_gate,
    governance_gate,
    syntax_gate,
    type_gate,
    unit_gate,
)
from src.graph.sandbox_persistence import persist_sandbox_run
from src.graph.sandbox_types import (
    GATE_ORDER,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_SKIP,
    STATUS_YELLOW,
    GATE_TIMEOUT_SECONDS,
    SandboxResult,
    VerificationGate,
)
from src.graph.sandbox_workspace import cleanup_workspace, create_run_dir, rollback_gate, setup_workspace

logger = logging.getLogger(__name__)


class SandboxRunner:
    """Docker-hardened 6-gate verification orchestrator."""

    def __init__(
        self,
        project_root: Optional[str] = None,
        docker_image: str = "backend:latest",
        total_timeout_seconds: int = 300,
        cleanup_run_dir: bool = False,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.sandbox_base_dir = self.project_root / ".sandbox"
        self.sandbox_base_dir.mkdir(parents=True, exist_ok=True)
        self.total_timeout_seconds = total_timeout_seconds
        self.cleanup_run_dir = cleanup_run_dir
        self.runtime = DockerSandboxRuntime(
            image=docker_image,
            seccomp_profile_path=self.project_root / "scripts/governance/sandbox_seccomp.json",
        )

    async def verify_fix(self, fix_payload: dict[str, Any]) -> SandboxResult:
        result = self.run_verification(
            changed_files=fix_payload.get("files", {}) or {},
            changed_tests=fix_payload.get("tests", []) or [],
            failure_fingerprint=fix_payload.get("failure_fingerprint"),
            remediation_type=fix_payload.get("remediation_type", "code_change"),
            confidence=fix_payload.get("confidence"),
        )
        gates = []
        for gate_name in GATE_ORDER:
            gate = result.get("gate_results", {}).get(gate_name, {})
            gates.append(
                VerificationGate(
                    name=gate_name.capitalize(),
                    status=str(gate.get("status", STATUS_SKIP)),
                    message=gate.get("message"),
                    duration_ms=float(gate.get("duration_ms", 0.0)),
                )
            )
        rollback_status = (
            result.get("gate_results", {}).get("rollback", {}).get("status", STATUS_SKIP)
        )
        return SandboxResult(
            run_id=str(result.get("run_id")),
            success=str(result.get("verdict")) == STATUS_GREEN,
            gates=gates,
            logs=str(result.get("logs", "")),
            error_details=result.get("error_details"),
            revert_plan_valid=rollback_status != STATUS_RED,
        )

    def run_verification(
        self,
        *,
        changed_files: dict[str, str],
        changed_tests: list[str],
        failure_fingerprint: Optional[str] = None,
        remediation_type: str = "code_change",
        confidence: Optional[float] = None,
    ) -> dict[str, Any]:
        run_id, run_dir = create_run_dir(self.sandbox_base_dir)
        changed_files = changed_files or {}
        changed_tests = changed_tests or []
        start = time.monotonic()
        gate_results: dict[str, dict[str, Any]] = {}
        logs: list[str] = []
        error_details: Optional[str] = None
        container = None
        container_id = None

        try:
            gate_results["syntax"] = self._timed(lambda: syntax_gate(changed_files))
            if self._is_red(gate_results["syntax"]):
                self._skip_after(gate_results, "syntax")
                error_details = gate_results["syntax"].get("message")
                return self._finalize(
                    run_id=run_id,
                    run_dir=run_dir,
                    start=start,
                    gate_results=gate_results,
                    logs=logs,
                    error_details=error_details,
                    changed_files=changed_files,
                    failure_fingerprint=failure_fingerprint,
                    remediation_type=remediation_type,
                    container_id=container_id,
                    confidence=confidence,
                )

            setup_workspace(self.project_root, run_dir, changed_files)
            _, container = self.runtime.start(run_dir)
            container_id = getattr(container, "id", None)
            logs.append(f"container_started:{container_id or 'unknown'}")

            gate_results["type"] = self._timed(
                lambda: type_gate(container, self.runtime.run_command)
            )
            if self._is_red(gate_results["type"]):
                self._skip_after(gate_results, "type")
                error_details = gate_results["type"].get("message")
                return self._finalize(
                    run_id=run_id,
                    run_dir=run_dir,
                    start=start,
                    gate_results=gate_results,
                    logs=logs,
                    error_details=error_details,
                    changed_files=changed_files,
                    failure_fingerprint=failure_fingerprint,
                    remediation_type=remediation_type,
                    container_id=container_id,
                    confidence=confidence,
                )

            gate_results["unit"] = self._timed(
                lambda: unit_gate(
                    container,
                    run_dir,
                    changed_files,
                    changed_tests,
                    self.runtime.run_command,
                )
            )
            if self._is_red(gate_results["unit"]):
                self._skip_after(gate_results, "unit")
                error_details = gate_results["unit"].get("message")
                return self._finalize(
                    run_id=run_id,
                    run_dir=run_dir,
                    start=start,
                    gate_results=gate_results,
                    logs=logs,
                    error_details=error_details,
                    changed_files=changed_files,
                    failure_fingerprint=failure_fingerprint,
                    remediation_type=remediation_type,
                    container_id=container_id,
                    confidence=confidence,
                )

            gate_results["contract"] = self._timed(
                lambda: contract_gate(
                    container,
                    run_dir,
                    changed_files,
                    self.runtime.run_command,
                )
            )
            if self._is_red(gate_results["contract"]):
                self._skip_after(gate_results, "contract")
                error_details = gate_results["contract"].get("message")
                return self._finalize(
                    run_id=run_id,
                    run_dir=run_dir,
                    start=start,
                    gate_results=gate_results,
                    logs=logs,
                    error_details=error_details,
                    changed_files=changed_files,
                    failure_fingerprint=failure_fingerprint,
                    remediation_type=remediation_type,
                    container_id=container_id,
                    confidence=confidence,
                )

            gate_results["governance"] = self._timed(
                lambda: governance_gate(container, changed_files, self.runtime.run_command)
            )
            if self._is_red(gate_results["governance"]):
                self._skip_after(gate_results, "governance")
                error_details = gate_results["governance"].get("message")
                return self._finalize(
                    run_id=run_id,
                    run_dir=run_dir,
                    start=start,
                    gate_results=gate_results,
                    logs=logs,
                    error_details=error_details,
                    changed_files=changed_files,
                    failure_fingerprint=failure_fingerprint,
                    remediation_type=remediation_type,
                    container_id=container_id,
                    confidence=confidence,
                )

            gate_results["rollback"] = self._timed(lambda: rollback_gate(changed_files))

        except Exception as exc:  # pragma: no cover
            logger.exception("Sandbox run %s crashed", run_id)
            error_details = f"Sandbox verifier crash: {exc}"
            gate_results.setdefault(
                "syntax", {"status": STATUS_RED, "message": error_details, "duration_ms": 0.0}
            )
            self._skip_after(gate_results, "syntax")
        finally:
            if container is not None:
                logs.append(self.runtime.stop(container))
            cleanup_workspace(run_dir, self.cleanup_run_dir)

        return self._finalize(
            run_id=run_id,
            run_dir=run_dir,
            start=start,
            gate_results=gate_results,
            logs=logs,
            error_details=error_details,
            changed_files=changed_files,
            failure_fingerprint=failure_fingerprint,
            remediation_type=remediation_type,
            container_id=container_id,
            confidence=confidence,
        )

    def _finalize(
        self,
        *,
        run_id: str,
        run_dir: Path,
        start: float,
        gate_results: dict[str, dict[str, Any]],
        logs: list[str],
        error_details: Optional[str],
        changed_files: dict[str, str],
        failure_fingerprint: Optional[str],
        remediation_type: str,
        container_id: Optional[str],
        confidence: Optional[float],
    ) -> dict[str, Any]:
        duration_ms = int((time.monotonic() - start) * 1000)
        verdict = self._verdict(gate_results)
        result = {
            "run_id": run_id,
            "verdict": verdict,
            "success": verdict == STATUS_GREEN,
            "gate_results": gate_results,
            "duration_ms": duration_ms,
            "container_id": container_id,
            "logs": "\n".join(logs),
            "rollback_notes": gate_results.get("rollback", {}).get("message", ""),
            "blast_radius_files": len(changed_files),
            "blast_radius_loc": sum(len(text.splitlines()) for text in changed_files.values()),
            "error_details": error_details,
            "run_dir": str(run_dir),
        }
        persist_sandbox_run(
            result=result,
            changed_files=changed_files,
            failure_fingerprint=failure_fingerprint,
            remediation_type=remediation_type,
            confidence=confidence,
        )
        return result

    def _timed(self, fn: Any) -> dict[str, Any]:
        start = time.monotonic()
        result = fn()
        result["duration_ms"] = round((time.monotonic() - start) * 1000.0, 2)
        return result

    def _is_red(self, gate: dict[str, Any]) -> bool:
        return str(gate.get("status")) == STATUS_RED

    def _skip_after(self, gate_results: dict[str, dict[str, Any]], failed_gate: str) -> None:
        fail_idx = GATE_ORDER.index(failed_gate)
        for gate_name in GATE_ORDER[fail_idx + 1 :]:
            gate_results.setdefault(
                gate_name,
                {
                    "status": STATUS_SKIP,
                    "message": f"Skipped after {failed_gate} gate failure.",
                    "duration_ms": 0.0,
                },
            )

    def _verdict(self, gate_results: dict[str, dict[str, Any]]) -> str:
        statuses = [str(row.get("status")) for row in gate_results.values()]
        if STATUS_RED in statuses:
            return STATUS_RED
        if STATUS_YELLOW in statuses:
            return STATUS_YELLOW
        return STATUS_GREEN


__all__ = [
    "SandboxRunner",
    "SandboxResult",
    "VerificationGate",
    "STATUS_GREEN",
    "STATUS_YELLOW",
    "STATUS_RED",
    "STATUS_SKIP",
    "GATE_TIMEOUT_SECONDS",
]
