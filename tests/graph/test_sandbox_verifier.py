from __future__ import annotations

import json
from pathlib import Path

import asyncio
import shutil
import uuid

from src.graph.sandbox_verifier import SandboxRunner
from src.graph.sandbox_docker import DockerSandboxRuntime


class DummyContainer:
    id = "dummy-container-id"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _mk_local_tmp() -> Path:
    base = Path(".sandbox_test_tmp")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _attach_runtime(monkeypatch, runner: SandboxRunner, responses: dict[str, dict]) -> None:
    def _start(_run_dir: Path):
        return object(), DummyContainer()

    def _stop(_container: DummyContainer) -> str:
        return "container_stopped"

    def _run_command(*, container, command: str, timeout_seconds: int):  # noqa: ARG001
        if "mypy" in command:
            return responses.get("type", {"exit_code": 0, "output": "", "timed_out": False})
        if "--tb=short" in command:
            return responses.get("unit", {"exit_code": 0, "output": "", "timed_out": False})
        if "test_*_contract.py" in command:
            return responses.get("contract", {"exit_code": 0, "output": "", "timed_out": False})
        if "risk_tier_gate.py" in command:
            return responses.get("governance", {"exit_code": 0, "output": '{"tier":"low"}', "timed_out": False})
        return {"exit_code": 0, "output": "", "timed_out": False}

    monkeypatch.setattr(runner.runtime, "start", _start)
    monkeypatch.setattr(runner.runtime, "stop", _stop)
    monkeypatch.setattr(runner.runtime, "run_command", _run_command)


def test_syntax_gate_blocks_immediately(monkeypatch) -> None:
    tmp_path = _mk_local_tmp()
    runner = SandboxRunner(project_root=str(tmp_path), cleanup_run_dir=True)

    def _start(_run_dir: Path):  # pragma: no cover - should not be called
        raise AssertionError("docker start should not be called on syntax failure")

    monkeypatch.setattr(runner.runtime, "start", _start)
    try:
        result = runner.run_verification(
            changed_files={"src/core/example.py": "def broken("},
            changed_tests=[],
        )
        assert result["verdict"] == "RED"
        assert result["gate_results"]["syntax"]["status"] == "RED"
        assert result["gate_results"]["type"]["status"] == "SKIP"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_governance_standard_returns_yellow(monkeypatch) -> None:
    tmp_path = _mk_local_tmp()
    _write(tmp_path / "tests/unit/test_example.py", "def test_ok():\n    assert True\n")
    runner = SandboxRunner(project_root=str(tmp_path), cleanup_run_dir=True)
    _attach_runtime(
        monkeypatch,
        runner,
        {
            "governance": {
                "exit_code": 0,
                "output": json.dumps({"tier": "standard"}),
                "timed_out": False,
            }
        },
    )
    try:
        result = runner.run_verification(
            changed_files={"src/core/example.py": "def ok() -> None:\n    pass\n"},
            changed_tests=["tests/unit/test_example.py"],
        )
        assert result["gate_results"]["governance"]["status"] == "YELLOW"
        assert result["verdict"] == "YELLOW"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_governance_high_returns_red(monkeypatch) -> None:
    tmp_path = _mk_local_tmp()
    _write(tmp_path / "tests/unit/test_example.py", "def test_ok():\n    assert True\n")
    runner = SandboxRunner(project_root=str(tmp_path), cleanup_run_dir=True)
    _attach_runtime(
        monkeypatch,
        runner,
        {
            "governance": {
                "exit_code": 0,
                "output": json.dumps({"tier": "high"}),
                "timed_out": False,
            }
        },
    )
    try:
        result = runner.run_verification(
            changed_files={"src/core/example.py": "def ok() -> None:\n    pass\n"},
            changed_tests=["tests/unit/test_example.py"],
        )
        assert result["gate_results"]["governance"]["status"] == "RED"
        assert result["verdict"] == "RED"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_unit_missing_target_returns_yellow(monkeypatch) -> None:
    tmp_path = _mk_local_tmp()
    runner = SandboxRunner(project_root=str(tmp_path), cleanup_run_dir=True)
    _attach_runtime(monkeypatch, runner, {})
    try:
        result = runner.run_verification(
            changed_files={"src/core/example.py": "def ok() -> None:\n    pass\n"},
            changed_tests=["tests/unit/test_missing.py"],
        )
        assert result["gate_results"]["unit"]["status"] == "YELLOW"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_rollback_warns_when_models_change_without_migration(monkeypatch) -> None:
    tmp_path = _mk_local_tmp()
    _write(tmp_path / "tests/unit/test_model.py", "def test_ok():\n    assert True\n")
    runner = SandboxRunner(project_root=str(tmp_path), cleanup_run_dir=True)
    _attach_runtime(monkeypatch, runner, {})
    try:
        result = runner.run_verification(
            changed_files={"src/models/new_model.py": "class X:\n    pass\n"},
            changed_tests=["tests/unit/test_model.py"],
        )
        assert result["gate_results"]["rollback"]["status"] == "YELLOW"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_rollback_detects_irreversible_migration(monkeypatch) -> None:
    tmp_path = _mk_local_tmp()
    _write(tmp_path / "tests/unit/test_model.py", "def test_ok():\n    assert True\n")
    runner = SandboxRunner(project_root=str(tmp_path), cleanup_run_dir=True)
    _attach_runtime(monkeypatch, runner, {})
    try:
        result = runner.run_verification(
            changed_files={
                "src/models/new_model.py": "class X:\n    pass\n",
                "migrations/versions/abc.py": "op.execute('DROP TABLE users')\n",
            },
            changed_tests=["tests/unit/test_model.py"],
        )
        assert result["gate_results"]["rollback"]["status"] == "RED"
        assert result["verdict"] == "RED"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_verify_fix_async_compatibility(monkeypatch) -> None:
    tmp_path = _mk_local_tmp()
    _write(tmp_path / "tests/unit/test_example.py", "def test_ok():\n    assert True\n")
    runner = SandboxRunner(project_root=str(tmp_path), cleanup_run_dir=True)
    _attach_runtime(monkeypatch, runner, {})
    try:
        verification = asyncio.run(
            runner.verify_fix(
                {
                    "files": {"src/core/example.py": "def ok() -> None:\n    pass\n"},
                    "tests": ["tests/unit/test_example.py"],
                }
            )
        )
        assert verification.success is True
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_container_hardening_kwargs_include_security_controls() -> None:
    tmp_path = _mk_local_tmp()
    seccomp = tmp_path / "sandbox_seccomp.json"
    seccomp.write_text('{"defaultAction":"SCMP_ACT_ERRNO","syscalls":[]}', encoding="utf-8")
    runtime = DockerSandboxRuntime(image="backend:latest", seccomp_profile_path=seccomp)
    try:
        kwargs = runtime.build_run_kwargs(tmp_path)
        assert kwargs["network_mode"] == "none"
        assert kwargs["read_only"] is True
        assert kwargs["cap_drop"] == ["ALL"]
        assert kwargs["user"] == "1000:1000"
        assert "no-new-privileges:true" in kwargs["security_opt"]
        assert any(item.startswith("seccomp=") for item in kwargs["security_opt"])
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
