"""6-gate primitives for sandbox verification."""

from __future__ import annotations

import ast
import json
import shlex
from pathlib import Path
from typing import Any, Callable

from src.graph.sandbox_types import (
    GATE_TIMEOUT_SECONDS,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_YELLOW,
)


def syntax_gate(changed_files: dict[str, str]) -> dict[str, str]:
    for path, content in changed_files.items():
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(content)
        except SyntaxError as exc:
            return {"status": STATUS_RED, "message": f"Syntax error in {path}: {exc}"}
    return {"status": STATUS_GREEN, "message": "Syntax validation passed."}


def type_gate(
    container: Any,
    run_command: Callable[..., dict[str, Any]],
) -> dict[str, str]:
    run = run_command(
        container=container,
        command="python -m mypy --strict --config-file=mypy.ini src/",
        timeout_seconds=GATE_TIMEOUT_SECONDS["type"],
    )
    if run["timed_out"]:
        return {"status": STATUS_RED, "message": "Type gate timed out."}
    if run["exit_code"] == 0:
        return {"status": STATUS_GREEN, "message": "Type checks passed."}
    if "warning" in run["output"].lower() and "error:" not in run["output"].lower():
        return {"status": STATUS_YELLOW, "message": "Type gate returned warnings."}
    return {"status": STATUS_RED, "message": "Type gate failed."}


def _determine_unit_targets(
    run_dir: Path,
    changed_files: dict[str, str],
    changed_tests: list[str],
) -> list[str]:
    targets: list[str] = []
    for item in changed_tests:
        normalized = item.replace("\\", "/")
        if normalized not in targets:
            targets.append(normalized)

    for path in changed_files:
        normalized = path.replace("\\", "/")
        if not normalized.startswith("src/") or not normalized.endswith(".py"):
            continue
        rel = normalized[len("src/") : -len(".py")]
        module_path = Path(rel)
        candidates = [
            f"tests/unit/{module_path.as_posix()}.py",
            f"tests/unit/test_{module_path.name}.py",
            f"tests/unit/{module_path.parent.as_posix()}/test_{module_path.name}.py",
        ]
        for candidate in candidates:
            candidate = candidate.replace("//", "/")
            if candidate not in targets:
                targets.append(candidate)

    existing = [target for target in targets if (run_dir / target).exists()]
    if existing:
        return existing
    if (run_dir / "tests/unit").exists():
        return ["tests/unit"]
    return targets


def unit_gate(
    container: Any,
    run_dir: Path,
    changed_files: dict[str, str],
    changed_tests: list[str],
    run_command: Callable[..., dict[str, Any]],
) -> dict[str, str]:
    targets = _determine_unit_targets(run_dir, changed_files, changed_tests)
    if not targets:
        return {
            "status": STATUS_YELLOW,
            "message": "No unit test targets resolved for changed files.",
        }

    warnings: list[str] = []
    for target in targets:
        if not (run_dir / target).exists():
            warnings.append(f"Missing unit test target: {target}")
            continue
        run = run_command(
            container=container,
            command=f"python -m pytest -x --tb=short -q {shlex.quote(target)}",
            timeout_seconds=GATE_TIMEOUT_SECONDS["unit"],
        )
        if run["timed_out"]:
            return {"status": STATUS_RED, "message": f"Unit gate timed out for {target}."}
        if run["exit_code"] != 0:
            return {"status": STATUS_RED, "message": f"Unit tests failed for {target}."}

    if warnings:
        return {"status": STATUS_YELLOW, "message": "; ".join(warnings)}
    return {"status": STATUS_GREEN, "message": f"Unit tests passed for {len(targets)} target(s)."}


def _requires_contract_gate(changed_files: dict[str, str]) -> bool:
    prefixes = ("src/api/", "src/models/", "src/schemas/", "tests/api/")
    return any(path.replace("\\", "/").startswith(prefixes) for path in changed_files)


def contract_gate(
    container: Any,
    run_dir: Path,
    changed_files: dict[str, str],
    run_command: Callable[..., dict[str, Any]],
) -> dict[str, str]:
    if not _requires_contract_gate(changed_files):
        return {
            "status": STATUS_GREEN,
            "message": "Contract gate not required for this change.",
        }

    tests = sorted(
        str(path.relative_to(run_dir)).replace("\\", "/")
        for path in (run_dir / "tests/api").glob("test_*_contract.py")
    )
    if not tests:
        return {"status": STATUS_YELLOW, "message": "No contract tests found under tests/api."}

    run = run_command(
        container=container,
        command=f"python -m pytest -x -q {' '.join(shlex.quote(item) for item in tests)}",
        timeout_seconds=GATE_TIMEOUT_SECONDS["contract"],
    )
    if run["timed_out"]:
        return {"status": STATUS_RED, "message": "Contract gate timed out."}
    if run["exit_code"] != 0:
        return {"status": STATUS_RED, "message": "Contract tests failed."}
    return {"status": STATUS_GREEN, "message": f"Contract tests passed ({len(tests)} file(s))."}


def _extract_json(output: str) -> dict[str, Any] | None:
    first = output.find("{")
    last = output.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None
    try:
        return json.loads(output[first : last + 1])
    except Exception:
        return None


def governance_gate(
    container: Any,
    changed_files: dict[str, str],
    run_command: Callable[..., dict[str, Any]],
) -> dict[str, str]:
    if not changed_files:
        return {
            "status": STATUS_GREEN,
            "message": "No changed files provided to governance gate.",
        }

    run = run_command(
        container=container,
        command=(
            "python scripts/governance/risk_tier_gate.py --changed-files "
            + " ".join(shlex.quote(path) for path in changed_files)
        ),
        timeout_seconds=GATE_TIMEOUT_SECONDS["governance"],
    )
    if run["timed_out"]:
        return {"status": STATUS_RED, "message": "Governance gate timed out."}
    if run["exit_code"] != 0:
        return {"status": STATUS_RED, "message": "Governance gate execution failed."}

    payload = _extract_json(run["output"])
    if payload is None:
        return {"status": STATUS_RED, "message": "Governance output was not valid JSON."}

    tier = str(payload.get("tier", "low")).lower()
    if tier in {"critical", "high"}:
        return {"status": STATUS_RED, "message": f"Governance tier is {tier}; blockers detected."}
    if tier == "standard":
        return {"status": STATUS_YELLOW, "message": "Governance tier is standard; review recommended."}
    return {"status": STATUS_GREEN, "message": f"Governance tier is {tier}."}
