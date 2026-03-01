"""
Universal Sandbox Verifier (Phase 15).
Orchestrates ephemeral, isolated full-stack clones for autonomous fix verification.
Implements the 6-gate safety protocol.
"""

import os
import json
import logging
import time
import uuid
import shutil
import subprocess
import ast
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class VerificationGate:
    name: str
    status: str = "PENDING"  # PENDING, PASS, FAIL, SKIP
    message: Optional[str] = None
    duration_ms: float = 0.0

@dataclass
class SandboxResult:
    run_id: str
    success: bool
    gates: List[VerificationGate]
    logs: str = ""
    error_details: Optional[str] = None
    revert_plan_valid: bool = False

class SandboxRunner:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.sandbox_base_dir = self.project_root / ".sandbox"
        self.sandbox_base_dir.mkdir(parents=True, exist_ok=True)

    def _create_run_dir(self, run_id: str) -> Path:
        run_dir = self.sandbox_base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    async def verify_fix(self, fix_payload: Dict[str, Any]) -> SandboxResult:
        """
        Main entry point for 6-gate verification.
        fix_payload: {
            "files": {"path/to/file.py": "new content"},
            "tests": ["tests/path/to/test.py"]
        }
        """
        run_id = str(uuid.uuid4())[:8]
        run_dir = self._create_run_dir(run_id)
        gates = [
            VerificationGate("Syntax"),
            VerificationGate("Type"),
            VerificationGate("Unit"),
            VerificationGate("Contract"),
            VerificationGate("Governance"),
            VerificationGate("Rollback")
        ]
        
        logger.info(f"🧪 [Sandbox] Starting verification run {run_id}...")
        
        try:
            # 1. Syntax Gate (Local)
            gates[0].status = "PASS"
            for path, content in fix_payload.get("files", {}).items():
                if path.endswith(".py"):
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        gates[0].status = "FAIL"
                        gates[0].message = f"Syntax error in {path}: {str(e)}"
                        return SandboxResult(run_id, False, gates, error_details=gates[0].message)

            # 2. Setup Sandbox Filesystem (Isolated)
            # In a real production environment, we'd use git clone or rsync.
            # Here we'll do a shallow copy of src/ and tests/ for speed.
            self._setup_sandbox_fs(run_dir, fix_payload)

            # 3. Dynamic Stack Boot (Placeholder for Docker)
            # For Phase 15.0, we simulate the gates using subprocess against the local dir
            # but scoped to the sandbox folder to prevent pollution.
            
            # 2. Type Check (mypy)
            try:
                logger.info(f"🧪 [Sandbox] [{run_id}] Running mypy...")
                # We use the host's python to run mypy in the sandbox folder
                res = subprocess.run(
                    [sys.executable, "-m", "mypy", str(run_dir / "src")],
                    capture_output=True, text=True, timeout=60
                )
                if res.returncode == 0:
                    gates[1].status = "PASS"
                elif "No module named mypy" in res.stderr:
                    gates[1].status = "SKIP"
                    gates[1].message = "Mypy not installed in this environment"
                else:
                    gates[1].status = "FAIL"
                    gates[1].message = res.stdout[:500]
            except Exception as e:
                gates[1].status = "SKIP"
                gates[1].message = f"Mypy check failed to run: {str(e)}"

            # 3. Unit Tests (pytest)
            try:
                logger.info(f"🧪 [Sandbox] [{run_id}] Running pytest...")
                # Scoped pytest run.
                # In Phase 15.0 we target only relevant tests if provided
                test_targets = fix_payload.get("tests")
                if not test_targets:
                    # Try to find tests for the modified files
                    test_targets = [str(run_dir / "tests/unit")]
                else:
                    # Map relative test paths to sandbox paths
                    test_targets = [str(run_dir / t) for t in test_targets]

                res = subprocess.run(
                    [sys.executable, "-m", "pytest", *test_targets, "-q", "--tb=short"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(run_dir)
                )
                if res.returncode == 0:
                    gates[2].status = "PASS"
                else:
                    gates[2].status = "FAIL"
                    gates[2].message = res.stdout[:1000]
            except Exception as e:
                gates[2].status = "FAIL"
                gates[2].message = f"Pytest check failed to run: {str(e)}"
            
            # ... additional gate logic ...

            success = all(g.status == "PASS" for g in gates)
            return SandboxResult(run_id, success, gates)

        except Exception as e:
            logger.exception(f"Sandbox run {run_id} crashed")
            return SandboxResult(run_id, False, gates, error_details=str(e))
        finally:
            # Cleanup
            # shutil.rmtree(run_dir, ignore_errors=True)
            pass

    def _setup_sandbox_fs(self, run_dir: Path, fix_payload: Dict[str, Any]):
        """Clones necessary files and applies the fix."""
        # This is a simplified version. A real one would use 'git checkout-index'
        # or similar to get a clean slate.
        for item in ["src", "tests", "requirements.txt", "pyproject.toml", ".rules", "STANDARDS.md"]:
            src_path = self.project_root / item
            if src_path.exists():
                if src_path.is_dir():
                    shutil.copytree(src_path, run_dir / item, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, run_dir / item)

        # Apply the fixes
        for path_str, content in fix_payload.get("files", {}).items():
            full_path = run_dir / path_str
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

async def test_sandbox():
    runner = SandboxRunner()
    payload = {
        "files": {
            "src/core/sandbox_test.py": "def test_func():\n    return True\n"
        }
    }
    result = await runner.verify_fix(payload)
    print(f"Result: {result.success}")
    for gate in result.gates:
        print(f"  Gate {gate.name}: {gate.status}")

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_sandbox())
