#!/usr/bin/env python3
"""
Windows notification transport for antigravity hooks.

Isolated to keep the main antigravity_notify module under governance LOC limits
and to encapsulate PowerShell-specific behavior.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


def _env_is_true(name: str, default: str = "0") -> bool:
    value = str(os.getenv(name, default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _escape_ps_single_quoted(value: str) -> str:
    return value.replace("'", "''")


def send_windows_notification(
    title: str,
    message: str,
    provider: str = "",
    window_hint: str = "",
    auto_focus: bool = False,
) -> bool:
    title_ps = _escape_ps_single_quoted(title[:120])
    message_ps = _escape_ps_single_quoted(message[:240])
    provider_ps = _escape_ps_single_quoted((provider or "").lower())
    window_hint_ps = _escape_ps_single_quoted((window_hint or "").strip())
    auto_focus_ps = "$true" if auto_focus else "$false"
    allow_spawn_fallback_ps = "$true" if _env_is_true("ANTIGRAVITY_ALLOW_SPAWN_FALLBACK", "0") else "$false"
    script = (
        "$ErrorActionPreference='Stop';"
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$provider='"
        + provider_ps
        + "';"
        "$windowHint='"
        + window_hint_ps
        + "';"
        "$autoFocus="
        + auto_focus_ps
        + ";"
        "$allowSpawnFallback="
        + allow_spawn_fallback_ps
        + ";"
        "$openAction={"
        "$activated=$false;"
        "try{"
        "$wsh=New-Object -ComObject WScript.Shell;"
        "$titleHints=@();"
        "$processHints=@();"
        "if($windowHint){ $titleHints += $windowHint };"
        "if($windowHint){ if($wsh.AppActivate($windowHint)){ $activated=$true } };"
        "if($provider -eq 'codex'){"
        "if($env:ANTIGRAVITY_CODEX_WINDOW_TITLES){ $titleHints += ($env:ANTIGRAVITY_CODEX_WINDOW_TITLES -split ',') };"
        "if($env:ANTIGRAVITY_CODEX_PROCESS_NAMES){ $processHints += ($env:ANTIGRAVITY_CODEX_PROCESS_NAMES -split ',') };"
        "$titleHints += @('Codex','Antigravity');"
        "$processHints += @('WindowsTerminal','Code','pwsh','powershell');"
        "} elseif($provider -eq 'claude'){"
        "if($env:ANTIGRAVITY_CLAUDE_WINDOW_TITLES){ $titleHints += ($env:ANTIGRAVITY_CLAUDE_WINDOW_TITLES -split ',') };"
        "if($env:ANTIGRAVITY_CLAUDE_PROCESS_NAMES){ $processHints += ($env:ANTIGRAVITY_CLAUDE_PROCESS_NAMES -split ',') };"
        "$titleHints += @('Claude','Antigravity');"
        "$processHints += @('WindowsTerminal','Code','pwsh','powershell');"
        "} elseif($provider -eq 'gemini'){"
        "if($env:ANTIGRAVITY_GEMINI_WINDOW_TITLES){ $titleHints += ($env:ANTIGRAVITY_GEMINI_WINDOW_TITLES -split ',') };"
        "if($env:ANTIGRAVITY_GEMINI_PROCESS_NAMES){ $processHints += ($env:ANTIGRAVITY_GEMINI_PROCESS_NAMES -split ',') };"
        "$titleHints += @('Gemini','Antigravity');"
        "$processHints += @('WindowsTerminal','Code','pwsh','powershell');"
        "};"
        "if($env:ANTIGRAVITY_WINDOW_TITLES){ $titleHints += ($env:ANTIGRAVITY_WINDOW_TITLES -split ',') };"
        "if($env:ANTIGRAVITY_PROCESS_NAMES){ $processHints += ($env:ANTIGRAVITY_PROCESS_NAMES -split ',') };"
        "$titleHints += @('Antigravity');"
        "$procs=Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle };"
        "foreach($hint in ($titleHints | Where-Object { $_ -and $_.Trim() -ne '' } | Select-Object -Unique)){"
        "$match=$procs | Where-Object { $_.MainWindowTitle -like ('*' + $hint + '*') } | Select-Object -First 1;"
        "if($match){"
        "if($wsh.AppActivate($match.Id)){ $activated=$true; break }"
        "}"
        "}"
        "if(-not $activated){"
        "foreach($pname in ($processHints | Where-Object { $_ -and $_.Trim() -ne '' } | Select-Object -Unique)){"
        "$pmatch=Get-Process -Name $pname -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1;"
        "if($pmatch){ if($wsh.AppActivate($pmatch.Id)){ $activated=$true; break } }"
        "}"
        "}"
        "} catch {};"
        "if(-not $activated -and $allowSpawnFallback){"
        "$targets=@($env:ANTIGRAVITY_URL,'antigravity://',$env:ANTIGRAVITY_EXE) | Where-Object { $_ -and $_.Trim() -ne '' };"
        "foreach($target in $targets){"
        "try{ Start-Process -FilePath $target | Out-Null; break } catch {}"
        "};"
        "}"
        "};"
        "if($autoFocus){ try{ & $openAction | Out-Null } catch {} };"
        "$n=New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon=[System.Drawing.SystemIcons]::Information;"
        "$n.BalloonTipTitle='"
        + title_ps
        + "';"
        "$n.BalloonTipText='"
        + message_ps
        + "';"
        "$n.add_BalloonTipClicked($openAction);"
        "$n.Visible=$true;"
        "$n.ShowBalloonTip(5000);"
        "$end=(Get-Date).AddMilliseconds(6000);"
        "while((Get-Date) -lt $end){ [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 100 };"
        "$n.Dispose();"
    )
    popen_kwargs: dict[str, Any] = {}
    if os.name == "nt":
        no_window_flag = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if no_window_flag:
            popen_kwargs["creationflags"] = no_window_flag
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        popen_kwargs["startupinfo"] = startup
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=False,
        capture_output=True,
        text=True,
        **popen_kwargs,
    )
    return completed.returncode == 0
