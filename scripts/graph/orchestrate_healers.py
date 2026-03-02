"""Autonomous Healer CLI wrapper (delegates to src.graph orchestration module)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.graph.orchestrate_healers import orchestrate_healing, orchestrate_remediation

logger = logging.getLogger(__name__)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default=None, help="Legacy category mode (14.3)")
    parser.add_argument("--event_id", default=None, help="Legacy event id")
    parser.add_argument(
        "--issue-json",
        default=None,
        help="Full normalized issue payload as JSON string for classification-aware orchestration",
    )
    args = parser.parse_args()

    if args.issue_json:
        try:
            issue = json.loads(args.issue_json)
        except json.JSONDecodeError as exc:
            logger.error("Invalid --issue-json payload: %s", exc)
            return 2
        result = await orchestrate_remediation(issue)
        logger.info("[Orchestrator] %s", json.dumps(result, default=str))
        return 0 if result.get("status") == "remediated" else 1

    if args.category:
        ok = await orchestrate_healing(args.category, args.event_id)
        return 0 if ok else 1

    parser.error("Provide either --category or --issue-json")
    return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(main()))
