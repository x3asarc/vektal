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
