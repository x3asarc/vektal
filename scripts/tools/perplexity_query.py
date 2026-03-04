#!/usr/bin/env python3
"""Run a Perplexity chat completion query and write raw JSON output."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib import request as urllib_request


def load_env(dotenv_path: Path) -> None:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Perplexity query and save JSON response.")
    parser.add_argument("--prompt", required=True, help="User prompt")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--model", default="sonar-pro", help="Perplexity model")
    parser.add_argument("--max-tokens", type=int, default=700, help="Max completion tokens")
    parser.add_argument("--search-mode", default="web", help="Search mode")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument(
        "--system",
        default="Be concise and implementation-focused. Include safeguards and rollback.",
        help="System instruction",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    load_env(repo_root / ".env")
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise SystemExit("PERPLEXITY_API_KEY missing")

    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": args.prompt},
        ],
        "search_mode": args.search_mode,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }

    req = urllib_request.Request(
        url="https://api.perplexity.ai/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        body = response.read().decode("utf-8", errors="ignore")

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
