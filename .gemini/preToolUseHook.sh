#!/bin/bash
# PreToolUse Hook for Gemini CLI
# Phase 14.3.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

HOOK_INPUT="$(cat || true)"
WINDOW_HINT="gemini-$$"
if [ -w /dev/tty ]; then
  printf '\033]0;%s\007' "Gemini [$WINDOW_HINT]" > /dev/tty || true
elif [ -t 1 ]; then
  printf '\033]0;%s\007' "Gemini [$WINDOW_HINT]" || true
fi

# Phase 15 health gate: fast cache-based checks (1-2ms vs 2-5s blocking)
python scripts/governance/health_gate.py || true
python scripts/hooks/antigravity_watchdog.py --spawn --provider gemini >/dev/null 2>&1 || true
python scripts/hooks/antigravity_notify.py --provider gemini --source heartbeat --heartbeat --window-hint "$WINDOW_HINT" >/dev/null 2>&1 || true

if [ -n "$HOOK_INPUT" ]; then
  printf '%s' "$HOOK_INPUT" | python scripts/hooks/antigravity_notify.py --provider gemini --source pre_tool_use --window-hint "$WINDOW_HINT" "$@" >/dev/null 2>&1 || true
else
  python scripts/hooks/antigravity_notify.py --provider gemini --source pre_tool_use --window-hint "$WINDOW_HINT" "$@" >/dev/null 2>&1 || true
fi
