from scripts.hooks import antigravity_watchdog


def test_watch_paths_default_disable_codex_and_gemini(monkeypatch) -> None:
    monkeypatch.delenv("ANTIGRAVITY_WATCHDOG_SCAN_CODEX_LOGS", raising=False)
    monkeypatch.delenv("ANTIGRAVITY_WATCHDOG_SCAN_GEMINI_LOGS", raising=False)
    assert antigravity_watchdog._watch_paths_for_provider("codex") == []
    assert antigravity_watchdog._watch_paths_for_provider("gemini") == []


def test_watch_paths_allow_codex_and_gemini_with_env(monkeypatch) -> None:
    monkeypatch.setenv("ANTIGRAVITY_WATCHDOG_SCAN_CODEX_LOGS", "1")
    monkeypatch.setenv("ANTIGRAVITY_WATCHDOG_SCAN_GEMINI_LOGS", "1")
    codex_paths = antigravity_watchdog._watch_paths_for_provider("codex")
    gemini_paths = antigravity_watchdog._watch_paths_for_provider("gemini")
    assert codex_paths and all(".codex" in p for p in codex_paths)
    assert gemini_paths and all(".gemini" in p for p in gemini_paths)


def test_remind_stale_alerts_dedupes_duplicate_signature(monkeypatch) -> None:
    now = 1_700_000_000.0
    alerts = [
        {
            "id": "a1",
            "provider": "claude",
            "trigger": "approval",
            "message": "claude: manual action needed in agent workflow.",
            "last_reminder_at": 0.0,
            "window_hint": "",
        },
        {
            "id": "a2",
            "provider": "claude",
            "trigger": "approval",
            "message": "claude: manual action needed in agent workflow.",
            "last_reminder_at": 0.0,
            "window_hint": "",
        },
        {
            "id": "a3",
            "provider": "claude",
            "trigger": "manual_verify",
            "message": "claude: a different manual action.",
            "last_reminder_at": 0.0,
            "window_hint": "",
        },
    ]

    emitted = []
    reminded = []

    monkeypatch.setattr(antigravity_watchdog.time, "time", lambda: now)
    monkeypatch.setattr(antigravity_watchdog.notify, "get_active_alerts", lambda: alerts)
    monkeypatch.setattr(antigravity_watchdog.notify, "get_last_heartbeat", lambda provider: 0.0)
    monkeypatch.setattr(antigravity_watchdog.notify, "get_window_hint", lambda provider: "")
    monkeypatch.setattr(
        antigravity_watchdog.notify,
        "emit_notification",
        lambda **kwargs: emitted.append(kwargs) or True,
    )
    monkeypatch.setattr(
        antigravity_watchdog.notify,
        "mark_alert_reminded",
        lambda alert_id, reminder_ts=None: reminded.append((alert_id, reminder_ts)),
    )

    antigravity_watchdog._remind_stale_alerts(reminder_seconds=75, heartbeat_grace_seconds=180)

    assert len(emitted) == 2
    assert all(item.get("auto_focus") is False for item in emitted)
    assert {alert_id for alert_id, _ in reminded} == {"a1", "a2", "a3"}
    assert all(reminder_ts == now for _, reminder_ts in reminded)
