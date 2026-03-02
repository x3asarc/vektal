#!/usr/bin/env python3
"""Load compressed session context for prompt injection workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys

# Allow direct script execution without requiring external PYTHONPATH setup.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.assistant.session_primer import SessionPrimer
from src.core.memory_loader import get_memory_loader


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--failure-context", default="")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml")
    parser.add_argument("--include-stats", action="store_true")
    args = parser.parse_args()

    primer = SessionPrimer(get_memory_loader())
    packet = primer.load_session_packet(failure_context=args.failure_context or None)

    if args.format == "json":
        payload = packet["data"]
        if args.include_stats:
            payload = {"context": payload, "stats": packet["stats"]}
        print(json.dumps(payload, indent=2, default=str))
    else:
        if args.include_stats:
            print(packet["yaml"])
            print("---")
            print(
                json.dumps(
                    {"session_primer_stats": packet["stats"]},
                    indent=2,
                    default=str,
                )
            )
        else:
            print(packet["yaml"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
