#!/usr/bin/env python3
"""Probe command for context broker graph/fallback telemetry behavior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.assistant.context_broker import assemble_context  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe context broker behavior.")
    parser.add_argument("--query", required=True, help="Query to assemble context for")
    parser.add_argument("--top-k", type=int, default=6)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = assemble_context(query=args.query, top_k=args.top_k)
    print(
        json.dumps(
            {
                "query": bundle.query,
                "query_class": bundle.query_class,
                "telemetry": bundle.telemetry,
                "snippet_count": len(bundle.snippets),
                "provenance": bundle.provenance[:5],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

