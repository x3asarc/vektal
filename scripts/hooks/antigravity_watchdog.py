#!/usr/bin/env python3
"""
Persistent watchdog for approval/verification stagnation.

Scans live Claude/Codex/Gemini local logs for manual-action checkpoints, then
keeps sending reminders until the user returns (heartbeat observed).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from scripts.hooks import antigravity_notify as notify
except ModuleNotFoundError:
    # Allow execution as `python scripts/hooks/antigravity_watchdog.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.hooks import antigravity_notify as notify

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCHDOG_STATE_PATH = REPO_ROOT / ".graph/antigravity-watchdog-state.json"
WATCHDOG_PID_PATH = REPO_ROOT / ".graph/antigravity-watchdog.pid"
WATCHDOG_LOG_PATH = REPO_ROOT / ".graph/antigravity-watchdog.log"

# Keep polling lightweight; this process should be cheap and always-on.
DEFAULT_POLL_SECONDS = 12
DEFAULT_REMINDER_SECONDS = 75
DEFAULT_HEARTBEAT_GRACE_SECONDS = 180
MAX_READ_BYTES = 256 * 1024
MAX_FILES_PER_PATTERN = 180
RECENT_WINDOW_SECONDS = 14 * 24 * 60 * 60

TRIGGER_HINTS = [
    "checkpoint reached",
    "your action",
    "type \"approved\"",
    "type 'approved'",
    "awaiting_approval",
    "pending approval",
    "manual approval",
    "accept edits",
    "require_escalated",
    "would you like to run the following command",
]


def _log(message: str) -> None:
    WATCHDOG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with WATCHDOG_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{int(time.time())} {message}\n")


def _load_watchdog_state() -> dict[str, Any]:
    if not WATCHDOG_STATE_PATH.exists():
        return {"files": {}}
    try:
        return json.loads(WATCHDOG_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"files": {}}


def _save_watchdog_state(state: dict[str, Any]) -> None:
    WATCHDOG_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = WATCHDOG_STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(WATCHDOG_STATE_PATH)


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _watch_paths_for_provider(provider: str) -> list[str]:
    home = Path.home()
    if provider == "codex":
        # Codex/Gemini approvals are detected directly by pre-tool hooks.
        # Log scanning for these providers creates false positives because
        # history lines often contain approval-like prose in user text.
        if os.getenv("ANTIGRAVITY_WATCHDOG_SCAN_CODEX_LOGS", "0") != "1":
            return []
        return [
            str(home / ".codex" / "sessions" / "**" / "*.jsonl"),
            str(home / ".codex" / "history.jsonl"),
            str(home / ".codex" / "log" / "*.log"),
        ]
    if provider == "claude":
        return [
            str(home / ".claude" / "history.jsonl"),
            str(home / ".claude" / "debug" / "*.txt"),
            str(REPO_ROOT / ".claude" / "checkpoints" / "*.log"),
        ]
    if os.getenv("ANTIGRAVITY_WATCHDOG_SCAN_GEMINI_LOGS", "0") != "1":
        return []
    return [
        str(home / ".gemini" / "antigravity" / "brain" / "**" / "*.md"),
        str(home / ".gemini" / "antigravity" / "brain" / "**" / "*.resolved*"),
        str(home / ".gemini" / "state.json"),
    ]


def _iter_watch_files(providers: list[str]) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = []
    now = time.time()
    for provider in providers:
        for pattern in _watch_paths_for_provider(provider):
            matched: list[Path] = []
            for path in glob.glob(pattern, recursive=True):
                p = Path(path)
                if not p.is_file():
                    continue
                matched.append(p)

            if not matched:
                continue

            # Large recursive histories can be massive; prioritize files with
            # recent writes to keep each poll responsive.
            if len(matched) > MAX_FILES_PER_PATTERN:
                recent: list[Path] = []
                for p in matched:
                    try:
                        if now - p.stat().st_mtime <= RECENT_WINDOW_SECONDS:
                            recent.append(p)
                    except OSError:
                        continue
                target = recent if recent else matched
                ranked: list[tuple[float, Path]] = []
                for candidate in target:
                    try:
                        ranked.append((candidate.stat().st_mtime, candidate))
                    except OSError:
                        continue
                ranked.sort(key=lambda row: row[0], reverse=True)
                matched = [path for _, path in ranked[:MAX_FILES_PER_PATTERN]]

            for p in matched:
                items.append((provider, p))
    return items


def _extract_text_from_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                event_type = str(parsed.get("type") or "")
                payload = parsed.get("payload")
                if event_type == "session_meta":
                    return ""
                if isinstance(payload, dict):
                    payload_type = str(payload.get("type") or "")
                    payload_role = str(payload.get("role") or "")
                    if payload_type == "user_message" or payload_role == "user":
                        return ""
                    if payload_type in {"function_call_output", "function_call"}:
                        return ""
                return notify._flatten_text(payload if payload is not None else parsed)  # type: ignore[attr-defined]
            return notify._flatten_text(parsed)  # type: ignore[attr-defined]
        except Exception:
            return stripped
    return stripped


def _line_has_trigger(text: str) -> tuple[bool, str | None]:
    trigger = notify.classify_trigger(text)
    if trigger:
        return True, trigger
    lowered = text.lower()
    for hint in TRIGGER_HINTS:
        if hint in lowered:
            return True, "manual_verify"
    return False, None


def _scan_file(provider: str, path: Path, state: dict[str, Any]) -> None:
    key = str(path)
    files_state = state.setdefault("files", {})
    cursor = files_state.get(key, {"offset": 0, "size": 0.0})

    try:
        stat = path.stat()
    except OSError:
        return

    size = int(stat.st_size)
    last_offset = int(cursor.get("offset", 0))

    # New file: start at EOF to avoid replaying stale historical content.
    if key not in files_state:
        last_offset = size
    elif size < last_offset:
        # File rotated/truncated.
        last_offset = 0

    read_start = max(0, min(last_offset, size))
    read_len = min(MAX_READ_BYTES, max(0, size - read_start))
    if read_len <= 0:
        files_state[key] = {"offset": size, "size": size}
        return

    try:
        with path.open("rb") as handle:
            handle.seek(read_start)
            chunk = handle.read(read_len)
    except OSError:
        return

    text = chunk.decode("utf-8", errors="ignore")
    for raw_line in text.splitlines():
        line = _extract_text_from_line(raw_line)
        if not line:
            continue
        if notify.looks_like_resolution(line):
            notify.resolve_alerts(provider, reason="pattern")
        has_trigger, trigger = _line_has_trigger(line)
        if not has_trigger:
            continue
        msg = f"{provider}: manual action needed in agent workflow."
        notify.record_alert(provider, trigger or "manual_verify", msg, source=f"watchdog:{path.name}")
        notify.emit_notification(
            provider=provider,
            trigger=trigger or "manual_verify",
            message=msg,
            source="watchdog-detect",
            force=False,
            cooldown_seconds=20,
            dry_run=False,
            title=f"Antigravity: Return To {provider.capitalize()}",
            window_hint=notify.get_window_hint(provider),
            auto_focus=False,
        )

    files_state[key] = {"offset": size, "size": size}


def _remind_stale_alerts(reminder_seconds: int, heartbeat_grace_seconds: int) -> None:
    now = time.time()
    sent_signatures: set[tuple[str, str, str]] = set()
    for alert in notify.get_active_alerts():
        provider = alert.get("provider", "codex")
        last_heartbeat = notify.get_last_heartbeat(provider)
        if now - last_heartbeat <= heartbeat_grace_seconds:
            continue
        last_reminder = float(alert.get("last_reminder_at", 0.0))
        if now - last_reminder < reminder_seconds:
            continue
        message = alert.get("message") or f"{provider}: approval is still pending."
        trigger = str(alert.get("trigger", "manual_verify"))
        signature = (provider, trigger, message)
        if signature in sent_signatures:
            notify.mark_alert_reminded(str(alert.get("id")), reminder_ts=now)
            continue
        sent_signatures.add(signature)
        notify.emit_notification(
            provider=provider,
            trigger=trigger,
            message=message,
            source="watchdog-reminder",
            force=True,
            cooldown_seconds=0,
            dry_run=False,
            title=f"Antigravity: Return To {provider.capitalize()}",
            window_hint=str(alert.get("window_hint") or notify.get_window_hint(provider)),
            auto_focus=False,
        )
        notify.mark_alert_reminded(str(alert.get("id")), reminder_ts=now)


def _spawn_watchdog(providers: list[str], poll_seconds: int, reminder_seconds: int, heartbeat_grace_seconds: int) -> int:
    WATCHDOG_PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    if WATCHDOG_PID_PATH.exists():
        try:
            pid = int(WATCHDOG_PID_PATH.read_text(encoding="utf-8").strip())
        except Exception:
            pid = -1
        if _is_process_running(pid):
            return 0

    python_bin = sys.executable

    cmd = [
        python_bin,
        str(REPO_ROOT / "scripts/hooks/antigravity_watchdog.py"),
        "--run",
        "--poll-seconds",
        str(poll_seconds),
        "--reminder-seconds",
        str(reminder_seconds),
        "--heartbeat-grace-seconds",
        str(heartbeat_grace_seconds),
    ]
    for provider in providers:
        cmd.extend(["--provider", provider])

    log_handle = WATCHDOG_LOG_PATH.open("a", encoding="utf-8")
    kwargs: dict[str, Any] = {
        "stdout": log_handle,
        "stderr": log_handle,
        "stdin": subprocess.DEVNULL,
        "cwd": str(REPO_ROOT),
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        )
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        kwargs["startupinfo"] = startup
    proc = subprocess.Popen(cmd, **kwargs)  # noqa: S603
    WATCHDOG_PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    _log(f"spawn pid={proc.pid} providers={providers} cwd={REPO_ROOT}")
    return 0


def _run_loop(providers: list[str], poll_seconds: int, reminder_seconds: int, heartbeat_grace_seconds: int) -> int:
    WATCHDOG_PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHDOG_PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    _log(f"run_loop started pid={os.getpid()} providers={providers} cwd={Path.cwd()}")

    while True:
        try:
            state = _load_watchdog_state()
            for provider, path in _iter_watch_files(providers):
                _scan_file(provider, path, state)
            _save_watchdog_state(state)
            _remind_stale_alerts(reminder_seconds, heartbeat_grace_seconds)
        except Exception as exc:
            _log(f"loop_error {exc!r}")
        time.sleep(max(5, poll_seconds))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spawn", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--provider", action="append", choices=["claude", "codex", "gemini"])
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--reminder-seconds", type=int, default=DEFAULT_REMINDER_SECONDS)
    parser.add_argument("--heartbeat-grace-seconds", type=int, default=DEFAULT_HEARTBEAT_GRACE_SECONDS)
    args = parser.parse_args()

    providers = args.provider or ["claude", "codex", "gemini"]

    if args.stop:
        if WATCHDOG_PID_PATH.exists():
            try:
                pid = int(WATCHDOG_PID_PATH.read_text(encoding="utf-8").strip())
            except Exception:
                pid = -1
            if _is_process_running(pid):
                try:
                    os.kill(pid, 15)
                except OSError:
                    pass
            try:
                WATCHDOG_PID_PATH.unlink()
            except OSError:
                pass
        return 0

    if args.spawn:
        return _spawn_watchdog(
            providers=providers,
            poll_seconds=args.poll_seconds,
            reminder_seconds=args.reminder_seconds,
            heartbeat_grace_seconds=args.heartbeat_grace_seconds,
        )
    if args.run:
        return _run_loop(
            providers=providers,
            poll_seconds=args.poll_seconds,
            reminder_seconds=args.reminder_seconds,
            heartbeat_grace_seconds=args.heartbeat_grace_seconds,
        )
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
