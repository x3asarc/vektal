#!/usr/bin/env python3
"""
Cross-agent notification helper for manual-action checkpoints.

Designed to be called from Claude/Codex/Gemini hook entrypoints and watchdogs.
Never blocks caller execution; exits 0 even on failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from scripts.hooks.antigravity_windows_notify import send_windows_notification
except ModuleNotFoundError:
    # Allow execution as `python scripts/hooks/antigravity_notify.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.hooks.antigravity_windows_notify import send_windows_notification

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = REPO_ROOT / ".graph/antigravity-notify-state.json"
LOG_PATH = REPO_ROOT / ".graph/antigravity-notifications.log"

TRIGGER_PATTERNS: dict[str, list[str]] = {
    "manual_verify": [
        r"\bmanual verify\b",
        r"\bmanual verification\b",
        r"\bcheckpoint:human-verify\b",
        r"\bverification required\b",
        r"\bcheckpoint reached\b",
        r"\byour action\b",
    ],
    "approval": [
        r"\bawaiting[_\-\s]?approval\b",
        r"\bpending[_\-\s]?approval\b",
        r"\bapproval required\b",
        r"\bpermission[_\-\s]?request\b",
        r"\brequest[_\-\s]?approval\b",
        r"\bpermission[_\-\s]?prompt\b",
        r"\bexec[_\-\s]?command[_\-\s]?approval\b",
        r"\bapply[_\-\s]?patch[_\-\s]?approval\b",
    ],
    "accept_edits": [
        r"\baccept edits?\b",
        r"\breview edits?\b",
        r"\bedits? pending\b",
        r"\bapply edits?\b",
    ],
}

RESOLUTION_PATTERNS: list[str] = [
    r"\bcommand approved\b",
    r"\bapproval granted\b",
    r"\bapproval received\b",
    r"\buser approved\b",
    r"\buser accepted\b",
    r"\bresolved\b",
    r"\bcontinuing\b",
]


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    return ""


def _load_stdin_text() -> str:
    try:
        if sys.stdin and not sys.stdin.closed:
            return sys.stdin.read() or ""
    except Exception:
        return ""
    return ""


def _normalize_payload(raw: str, argv_payload: str) -> str:
    raw = (raw or "").strip()
    argv_payload = (argv_payload or "").strip()
    if not raw:
        return argv_payload
    try:
        parsed = json.loads(raw)
        flattened = _flatten_text(parsed).strip()
        return " ".join(p for p in [flattened, argv_payload] if p)
    except Exception:
        return " ".join(p for p in [raw, argv_payload] if p)


def _base_state() -> dict[str, Any]:
    return {"dedupe": {}, "heartbeat": {}, "alerts": {}, "window_hints": {}}


def _normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return _base_state()
    if "dedupe" in raw and "heartbeat" in raw and "alerts" in raw:
        return {
            "dedupe": raw.get("dedupe", {}),
            "heartbeat": raw.get("heartbeat", {}),
            "alerts": raw.get("alerts", {}),
            "window_hints": raw.get("window_hints", {}),
        }
    # Backward compatibility: old state stored only dedupe keys.
    if all(isinstance(v, (int, float)) for v in raw.values()):
        return {"dedupe": raw, "heartbeat": {}, "alerts": {}, "window_hints": {}}
    return _base_state()


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _base_state()
    try:
        parsed = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _base_state()
    return _normalize_state(parsed)


def _save_state(state: dict[str, Any]) -> bool:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2)
    # State updates can happen concurrently from hooks/watchdog; retry briefly
    # on transient lock races instead of crashing caller workflows.
    for attempt in range(4):
        temp = STATE_PATH.with_name(f"{STATE_PATH.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        try:
            temp.write_text(payload, encoding="utf-8")
            temp.replace(STATE_PATH)
            return True
        except (PermissionError, FileNotFoundError, OSError):
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            if attempt == 3:
                return False
            time.sleep(0.05 * (attempt + 1))
    return False


def classify_trigger(text: str) -> str | None:
    normalized = (text or "").lower()
    if not normalized:
        return None
    # Codex escalation prompts surface as tool-call metadata and/or approval UI.
    if (
        "require_escalated" in normalized
        or "would you like to run the following command" in normalized
        or "item/commandexecution/requestapproval" in normalized
        or "event::execapprovalrequest" in normalized
    ):
        return "approval"
    for trigger, patterns in TRIGGER_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return trigger
    return None


def looks_like_resolution(text: str) -> bool:
    normalized = (text or "").lower()
    return any(re.search(pattern, normalized) for pattern in RESOLUTION_PATTERNS)


def _default_message(provider: str, trigger: str, window_hint: str = "") -> str:
    provider_label = provider.upper()
    hint_suffix = f" [{window_hint}]" if window_hint else ""
    if trigger == "manual_verify":
        return f"{provider_label}: Manual verification checkpoint detected. Return to the {provider_label} terminal{hint_suffix}."
    if trigger == "approval":
        return f"{provider_label}: Approval is required. Return to the {provider_label} terminal{hint_suffix} to proceed."
    return f"{provider_label}: Edit acceptance is required. Return to the {provider_label} terminal{hint_suffix}."


def _env_is_true(name: str, default: str = "0") -> bool:
    value = str(os.getenv(name, default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _default_auto_focus(trigger: str) -> bool:
    if trigger != "approval":
        return False
    return _env_is_true("ANTIGRAVITY_AUTO_FOCUS_APPROVAL", "0")


def _send_windows_notification(
    title: str,
    message: str,
    provider: str = "",
    window_hint: str = "",
    auto_focus: bool = False,
) -> bool:
    return send_windows_notification(
        title=title,
        message=message,
        provider=provider,
        window_hint=window_hint,
        auto_focus=auto_focus,
    )


def _send_macos_notification(title: str, message: str) -> bool:
    title_escaped = title.replace('"', '\\"')
    message_escaped = message.replace('"', '\\"')
    cmd = f'display notification "{message_escaped}" with title "{title_escaped}"'
    completed = subprocess.run(
        ["osascript", "-e", cmd],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _send_linux_notification(title: str, message: str) -> bool:
    completed = subprocess.run(
        ["notify-send", title[:120], message[:240]],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def send_system_notification(
    title: str,
    message: str,
    provider: str = "",
    window_hint: str = "",
    auto_focus: bool = False,
) -> bool:
    system_name = platform.system().lower()
    try:
        if "windows" in system_name:
            return _send_windows_notification(
                title,
                message,
                provider=provider,
                window_hint=window_hint,
                auto_focus=auto_focus,
            )
        if "darwin" in system_name:
            return _send_macos_notification(title, message)
        return _send_linux_notification(title, message)
    except Exception:
        return False


def should_send(dedupe_key: str, cooldown_seconds: int, force: bool) -> bool:
    if force:
        return True
    state = _load_state()
    last_sent = float(state["dedupe"].get(dedupe_key, 0.0))
    now = time.time()
    if now - last_sent < cooldown_seconds:
        return False
    state["dedupe"][dedupe_key] = now
    return bool(_save_state(state))


def _log_event(provider: str, trigger: str, sent: bool, message: str, source: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "ts": int(time.time()),
            "provider": provider,
            "trigger": trigger,
            "sent": sent,
            "source": source,
            "message": message,
        }
    )
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def record_heartbeat(provider: str, window_hint: str = "") -> None:
    state = _load_state()
    state["heartbeat"][provider] = time.time()
    if window_hint:
        state["window_hints"][provider] = window_hint
    # Treat a fresh heartbeat as "user is back"; clear stale unresolved alerts
    # so reminders do not keep firing after focus is regained.
    for alert in state.get("alerts", {}).values():
        if alert.get("provider") == provider and not alert.get("resolved_at"):
            alert["resolved_at"] = time.time()
            alert["resolution_reason"] = "heartbeat"
    _save_state(state)


def get_last_heartbeat(provider: str) -> float:
    state = _load_state()
    return float(state["heartbeat"].get(provider, 0.0))


def get_window_hint(provider: str) -> str:
    state = _load_state()
    return str(state.get("window_hints", {}).get(provider, "") or "")


def record_alert(provider: str, trigger: str, message: str, source: str, window_hint: str = "") -> str:
    state = _load_state()
    now = time.time()

    # Coalesce duplicate unresolved alerts in a short window.
    for alert_id, alert in state["alerts"].items():
        if (
            alert.get("provider") == provider
            and alert.get("trigger") == trigger
            and alert.get("message") == message
            and not alert.get("resolved_at")
            and now - float(alert.get("created_at", 0.0)) < 300
        ):
            if window_hint and not alert.get("window_hint"):
                alert["window_hint"] = window_hint
                _save_state(state)
            return alert_id

    alert_id = uuid.uuid4().hex
    state["alerts"][alert_id] = {
        "provider": provider,
        "trigger": trigger,
        "message": message,
        "source": source,
        "window_hint": window_hint,
        "created_at": now,
        "last_reminder_at": 0.0,
        "resolved_at": None,
    }
    _save_state(state)
    return alert_id


def resolve_alerts(provider: str, reason: str = "resolved") -> int:
    state = _load_state()
    now = time.time()
    count = 0
    for alert in state["alerts"].values():
        if alert.get("provider") == provider and not alert.get("resolved_at"):
            alert["resolved_at"] = now
            alert["resolution_reason"] = reason
            count += 1
    if count:
        _save_state(state)
    return count


def get_active_alerts(provider: str | None = None) -> list[dict[str, Any]]:
    state = _load_state()
    alerts = []
    for alert_id, alert in state["alerts"].items():
        if alert.get("resolved_at"):
            continue
        if provider and alert.get("provider") != provider:
            continue
        row = dict(alert)
        row["id"] = alert_id
        alerts.append(row)
    alerts.sort(key=lambda row: float(row.get("created_at", 0.0)))
    return alerts


def mark_alert_reminded(alert_id: str, reminder_ts: float | None = None) -> None:
    state = _load_state()
    if alert_id not in state["alerts"]:
        return
    state["alerts"][alert_id]["last_reminder_at"] = reminder_ts or time.time()
    _save_state(state)


def emit_notification(
    *,
    provider: str,
    trigger: str,
    message: str,
    source: str,
    force: bool,
    cooldown_seconds: int,
    dry_run: bool,
    title: str | None = None,
    window_hint: str = "",
    auto_focus: bool | None = None,
) -> bool:
    provider_label = provider.upper()
    if trigger == "approval":
        default_title = f"Antigravity: {provider_label} Approval Needed"
    elif trigger == "manual_verify":
        default_title = f"Antigravity: {provider_label} Verify Needed"
    elif trigger == "accept_edits":
        default_title = f"Antigravity: {provider_label} Accept Edits"
    else:
        default_title = f"Antigravity: {provider_label} Action Needed"
    title_value = title or default_title
    dedupe_basis = f"{provider}:{source}:{trigger}:{message}"
    dedupe_key = hashlib.sha256(dedupe_basis.encode("utf-8")).hexdigest()

    if not should_send(dedupe_key, cooldown_seconds, force):
        return False

    effective_hint = window_hint or get_window_hint(provider)
    effective_auto_focus = _default_auto_focus(trigger) if auto_focus is None else auto_focus
    sent = False
    if not dry_run:
        sent = send_system_notification(
            title=title_value,
            message=message,
            provider=provider,
            window_hint=effective_hint,
            auto_focus=effective_auto_focus,
        )
    _log_event(provider, trigger, sent, message, source)
    return sent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["claude", "codex", "gemini"], default="codex")
    parser.add_argument("--source", default="hook")
    parser.add_argument("--title", default="")
    parser.add_argument("--message", default="")
    parser.add_argument("--payload", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--cooldown-seconds", type=int, default=45)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--heartbeat", action="store_true")
    parser.add_argument("--resolve", action="store_true")
    parser.add_argument("--list-active", action="store_true")
    parser.add_argument("--no-register-alert", action="store_true")
    parser.add_argument("--window-hint", default="")
    parser.add_argument("--auto-focus", action="store_true")
    parser.add_argument("extra", nargs="*")
    args = parser.parse_args()

    if args.heartbeat:
        record_heartbeat(args.provider, window_hint=args.window_hint)
        return 0

    if args.resolve:
        resolve_alerts(args.provider, reason="manual")
        return 0

    if args.list_active:
        print(json.dumps(get_active_alerts(args.provider), indent=2))
        return 0

    stdin_payload = _load_stdin_text()
    argv_payload = " ".join([args.payload] + args.extra).strip()
    normalized_payload = _normalize_payload(stdin_payload, argv_payload)

    if looks_like_resolution(normalized_payload):
        resolve_alerts(args.provider, reason="pattern")

    trigger = classify_trigger(normalized_payload)
    if not trigger and not args.force:
        return 0

    message = args.message or _default_message(
        args.provider,
        trigger or "manual_verify",
        window_hint=args.window_hint or get_window_hint(args.provider),
    )
    if trigger and not args.no_register_alert:
        record_alert(
            args.provider,
            trigger,
            message,
            source=args.source,
            window_hint=args.window_hint or get_window_hint(args.provider),
        )

    emit_notification(
        provider=args.provider,
        trigger=trigger or "forced",
        message=message,
        source=args.source,
        force=args.force,
        cooldown_seconds=args.cooldown_seconds,
        dry_run=args.dry_run,
        title=args.title or None,
        window_hint=args.window_hint,
        auto_focus=True if args.auto_focus else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
