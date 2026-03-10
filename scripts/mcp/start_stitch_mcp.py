#!/usr/bin/env python3
"""Start Stitch MCP proxy with environment loaded from .env."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")

    env = os.environ.copy()
    env.setdefault("STITCH_USE_SYSTEM_GCLOUD", "1")
    env.setdefault("CI", "1")

    if not env.get("STITCH_API_KEY") and not env.get("STITCH_ACCESS_TOKEN"):
        print(
            "Missing Stitch auth: set STITCH_API_KEY or STITCH_ACCESS_TOKEN in .env",
            file=sys.stderr,
        )
        return 1

    cmd = ["npx.cmd", "-y", "@_davideast/stitch-mcp@latest", "proxy"]
    result = subprocess.run(cmd, env=env, cwd=str(root))
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
