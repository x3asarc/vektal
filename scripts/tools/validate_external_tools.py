#!/usr/bin/env python3
"""Validate Firecrawl, Perplexity, and Context7 toolchain health."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib import request as urllib_request
from urllib import error as urllib_error


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = REPO_ROOT / ".tooling" / "external-tools-health.json"


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Firecrawl, Perplexity, and Context7 availability."
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="quick = local install/config checks only, full = includes live network smoke tests",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Path to write JSON report",
    )
    return parser.parse_args()


def load_env_from_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def run_cmd(cmd: list[str], timeout: int = 20) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        timeout=timeout,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def probe_long_running_process(cmd: list[str], env: dict[str, str] | None = None, timeout: int = 5) -> tuple[bool, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    try:
        try:
            proc.wait(timeout=timeout)
            output = ((proc.stdout.read() if proc.stdout else "") + "\n" + (proc.stderr.read() if proc.stderr else "")).strip()
            if proc.returncode == 0:
                return True, output or "process exited cleanly"
            return False, output or f"exit code {proc.returncode}"
        except subprocess.TimeoutExpired:
            proc.terminate()
            return True, "process started and remained alive"
    finally:
        try:
            proc.kill()
        except Exception:
            pass


def check_binary_presence(binary_name: str) -> CheckResult:
    found = shutil.which(binary_name) is not None
    return CheckResult(
        name=f"binary:{binary_name}",
        ok=found,
        details="found" if found else "missing from PATH",
    )


def check_firecrawl_status() -> CheckResult:
    code, out, err = run_cmd(["cmd", "/c", "firecrawl", "--status"], timeout=30)
    details = out or err or "no output"
    ok = code == 0 and ("Authenticated" in details or "authenticated" in details.lower())
    return CheckResult("firecrawl:status", ok, details)


def check_firecrawl_search_smoke() -> CheckResult:
    temp_dir = REPO_ROOT / ".tooling"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = temp_dir / "firecrawl-smoke.json"
    cmd = [
        "cmd",
        "/c",
        "firecrawl",
        "search",
        "site:openai.com responses api",
        "--limit",
        "1",
        "--json",
        "-o",
        str(output_path),
    ]
    code, out, err = run_cmd(cmd, timeout=90)
    details = out or err or "no output"
    ok = code == 0 and output_path.exists() and output_path.stat().st_size > 0
    return CheckResult("firecrawl:search_smoke", ok, details)


def check_perplexity_key() -> CheckResult:
    present = bool(os.environ.get("PERPLEXITY_API_KEY"))
    return CheckResult("perplexity:key", present, "present" if present else "missing")


def check_perplexity_mcp_start() -> CheckResult:
    ok, details = probe_long_running_process(["perplexity-mcp.cmd", "--cwd", "."], timeout=5)
    return CheckResult("perplexity:mcp_start", ok, details)


def check_perplexity_api_smoke() -> CheckResult:
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        return CheckResult("perplexity:api_smoke", False, "PERPLEXITY_API_KEY missing")

    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": "Reply with exactly: PERPLEXITY_OK"}],
        "max_tokens": 20,
        "temperature": 0,
    }
    req = urllib_request.Request(
        url="https://api.perplexity.ai/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        parsed = json.loads(body)
        content = (
            parsed.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        ok = bool(content)
        return CheckResult("perplexity:api_smoke", ok, content[:200] if content else "empty response content")
    except urllib_error.URLError as exc:
        return CheckResult("perplexity:api_smoke", False, f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # pragma: no cover - defensive
        return CheckResult("perplexity:api_smoke", False, f"{type(exc).__name__}: {exc}")


def check_context7_key() -> CheckResult:
    present = bool(os.environ.get("CONTEXT7_API_KEY") or os.environ.get("UPSTASH_CONTEXT7_API_KEY"))
    if present:
        return CheckResult("context7:key", True, "present")
    return CheckResult("context7:key", True, "missing (optional when MCP startup succeeds)")


def check_context7_mcp_start() -> CheckResult:
    env = dict(os.environ)
    cmd = ["cmd", "/c", "npx", "-y", "@upstash/context7-mcp"]
    ok, details = probe_long_running_process(cmd, env=env, timeout=8)
    return CheckResult("context7:mcp_start", ok, details)


def check_context7_config_reference() -> CheckResult:
    settings_files = [
        REPO_ROOT / ".codex" / "settings.json",
        REPO_ROOT / ".gemini" / "settings.json",
        REPO_ROOT / ".claude" / "settings.json",
    ]
    found = []
    for path in settings_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "context7" in text.lower():
            found.append(path.as_posix())
    return CheckResult(
        "context7:config_reference",
        bool(found),
        ", ".join(found) if found else "no context7 MCP reference found in settings files",
    )


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def safe_console_text(text: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def main() -> int:
    args = parse_args()
    load_env_from_dotenv(REPO_ROOT / ".env")

    checks: list[CheckResult] = []
    checks.append(check_binary_presence("firecrawl"))
    checks.append(check_binary_presence("perplexity-mcp.cmd"))
    checks.append(check_binary_presence("npx"))

    checks.append(check_firecrawl_status())
    checks.append(check_perplexity_key())
    checks.append(check_perplexity_mcp_start())
    checks.append(check_context7_key())
    checks.append(check_context7_config_reference())
    checks.append(check_context7_mcp_start())

    if args.mode == "full":
        checks.append(check_firecrawl_search_smoke())
        checks.append(check_perplexity_api_smoke())

    overall_ok = all(check.ok for check in checks)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = {
        "timestamp": timestamp,
        "mode": args.mode,
        "overall_ok": overall_ok,
        "checks": [asdict(item) for item in checks],
    }
    report_path = Path(args.report).resolve()
    write_report(report_path, report)

    print(f"[tools] report={report_path}")
    for item in checks:
        tag = "PASS" if item.ok else "FAIL"
        print(f"[{tag}] {item.name}: {safe_console_text(item.details)}")

    if overall_ok:
        print("[tools] overall=PASS")
        return 0
    print("[tools] overall=FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
