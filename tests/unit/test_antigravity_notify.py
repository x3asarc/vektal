import pytest

from scripts.hooks import antigravity_notify


def test_classify_trigger_manual_verify() -> None:
    text = "CHECKPOINT REACHED: manual verification required before continuing."
    assert antigravity_notify.classify_trigger(text) == "manual_verify"


def test_classify_trigger_approval() -> None:
    text = "Action is awaiting_approval and requires approval."
    assert antigravity_notify.classify_trigger(text) == "approval"


def test_classify_trigger_codex_escalation_prompt() -> None:
    text = '{"sandbox_permissions":"require_escalated","justification":"Do you want me to proceed?"}'
    assert antigravity_notify.classify_trigger(text) == "approval"


def test_classify_trigger_codex_approval_ui_text() -> None:
    text = "Would you like to run the following command? 1. Yes, proceed (y)"
    assert antigravity_notify.classify_trigger(text) == "approval"


def test_classify_trigger_question_alone_is_not_approval() -> None:
    text = "Do you want me to draft a plan before coding?"
    assert antigravity_notify.classify_trigger(text) is None


def test_classify_trigger_generic_requires_approval_is_not_enough() -> None:
    text = "This document says the command requires approval in some environments."
    assert antigravity_notify.classify_trigger(text) is None


def test_classify_trigger_accept_edits() -> None:
    text = "Please accept edits before apply."
    assert antigravity_notify.classify_trigger(text) == "accept_edits"


def test_should_send_respects_cooldown(monkeypatch) -> None:
    state_file = antigravity_notify.LOG_PATH.parent / "test-antigravity-state.json"
    if state_file.exists():
        state_file.unlink()
    monkeypatch.setattr(antigravity_notify, "STATE_PATH", state_file)

    key = "k"
    assert antigravity_notify.should_send(key, cooldown_seconds=60, force=False) is True
    assert antigravity_notify.should_send(key, cooldown_seconds=60, force=False) is False
    assert antigravity_notify.should_send(key, cooldown_seconds=60, force=True) is True
    if state_file.exists():
        state_file.unlink()


def test_record_and_resolve_alert(monkeypatch) -> None:
    state_file = antigravity_notify.LOG_PATH.parent / "test-antigravity-alert-state.json"
    if state_file.exists():
        state_file.unlink()
    monkeypatch.setattr(antigravity_notify, "STATE_PATH", state_file)

    alert_id = antigravity_notify.record_alert(
        provider="codex",
        trigger="approval",
        message="codex: approval required",
        source="test",
    )
    active = antigravity_notify.get_active_alerts("codex")
    assert any(row["id"] == alert_id for row in active)
    assert antigravity_notify.resolve_alerts("codex", reason="test") == 1
    assert antigravity_notify.get_active_alerts("codex") == []
    if state_file.exists():
        state_file.unlink()


def test_heartbeat_resolves_active_alerts(monkeypatch) -> None:
    state_file = antigravity_notify.LOG_PATH.parent / "test-antigravity-heartbeat-state.json"
    if state_file.exists():
        state_file.unlink()


@pytest.mark.parametrize("provider", ["codex", "claude", "gemini"])
def test_heartbeat_resolves_active_alerts_for_all_providers(monkeypatch, provider: str) -> None:
    state_file = antigravity_notify.LOG_PATH.parent / f"test-antigravity-heartbeat-{provider}.json"
    if state_file.exists():
        state_file.unlink()
    monkeypatch.setattr(antigravity_notify, "STATE_PATH", state_file)

    antigravity_notify.record_alert(
        provider=provider,
        trigger="approval",
        message=f"{provider}: approval required",
        source="test-heartbeat-all",
    )
    assert antigravity_notify.get_active_alerts(provider)
    antigravity_notify.record_heartbeat(provider, window_hint=f"{provider}-hint")
    assert antigravity_notify.get_active_alerts(provider) == []
    assert antigravity_notify.get_window_hint(provider) == f"{provider}-hint"
    if state_file.exists():
        state_file.unlink()
    monkeypatch.setattr(antigravity_notify, "STATE_PATH", state_file)

    antigravity_notify.record_alert(
        provider="codex",
        trigger="approval",
        message="codex: approval required",
        source="test-heartbeat",
    )
    assert antigravity_notify.get_active_alerts("codex")
    antigravity_notify.record_heartbeat("codex")
    assert antigravity_notify.get_active_alerts("codex") == []
    if state_file.exists():
        state_file.unlink()
