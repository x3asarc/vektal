#!/usr/bin/env python3
"""
Seed memory nodes (Convention + Decision) for Phase 14.1.

Supports dry-run mode and idempotent MERGE writes.
"""

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root for "src" imports when invoked directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.graphiti_client import get_graphiti_client


def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _extract_conventions(root: Path) -> List[Dict[str, str]]:
    conventions: List[Dict[str, str]] = []
    for rel in ["CLAUDE.md", "GEMINI.md", "STANDARDS.md", "AGENTS.md"]:
        lines = _read_lines(root / rel)
        for line in lines:
            text = line.strip()
            if not text.startswith(("- ", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                continue
            lowered = text.lower()
            if "must" not in lowered and "never" not in lowered and "required" not in lowered:
                continue
            rule = text.lstrip("- ").strip()
            if len(rule) < 18:
                continue
            conventions.append(
                {
                    "rule": rule,
                    "scope": "global",
                    "enforcement": "hard" if ("must" in lowered or "never" in lowered) else "soft",
                    "source": rel,
                }
            )

    dedup: Dict[str, Dict[str, str]] = {}
    for row in conventions:
        key = row["rule"].lower()
        dedup[key] = row
    return list(dedup.values())[:50]


def _extract_decisions(root: Path) -> List[Dict[str, str]]:
    decisions: List[Dict[str, str]] = []
    for rel in [".planning/PROJECT.md", ".planning/ROADMAP.md"]:
        lines = _read_lines(root / rel)
        for line in lines:
            text = line.strip()
            if "Decision" not in text and "depends on" not in text.lower():
                continue
            if len(text) < 20:
                continue
            title = text[:120]
            decisions.append(
                {
                    "title": title,
                    "context": f"Extracted from {rel}",
                    "rationale": text,
                    "status": "active",
                    "phase_ref": "14.1",
                    "source": rel,
                }
            )

    dedup: Dict[str, Dict[str, str]] = {}
    for row in decisions:
        key = hashlib.sha1(row["title"].encode("utf-8")).hexdigest()
        dedup[key] = row
    return list(dedup.values())[:50]


async def _merge_seed_data(client, store_id: str, conventions: List[Dict[str, str]], decisions: List[Dict[str, str]]) -> Tuple[int, int]:
    created_conventions = 0
    created_decisions = 0
    async with client.driver.session() as session:
        for row in conventions:
            await session.run(
                """
                MERGE (c:Convention {rule: $rule})
                ON CREATE SET c.scope = $scope, c.enforcement = $enforcement, c.source = $source, c.store_id = $store_id
                """,
                rule=row["rule"],
                scope=row["scope"],
                enforcement=row["enforcement"],
                source=row["source"],
                store_id=store_id,
            )
            created_conventions += 1

        for row in decisions:
            await session.run(
                """
                MERGE (d:Decision {title: $title})
                ON CREATE SET d.context = $context, d.rationale = $rationale, d.status = $status, d.phase_ref = $phase_ref, d.source = $source, d.store_id = $store_id
                """,
                title=row["title"],
                context=row["context"],
                rationale=row["rationale"],
                status=row["status"],
                phase_ref=row["phase_ref"],
                source=row["source"],
                store_id=store_id,
            )
            created_decisions += 1

    return created_conventions, created_decisions


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Convention/Decision memory nodes")
    parser.add_argument("--dry-run", action="store_true", help="Print seed candidates without writing to Neo4j")
    parser.add_argument("--store-id", default="global", help="Store ID for seeded nodes")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    conventions = _extract_conventions(root)
    decisions = _extract_decisions(root)

    print(f"[seed_memory_nodes] conventions={len(conventions)} decisions={len(decisions)}")

    if args.dry_run:
        for row in conventions[:5]:
            print(f"CONVENTION: {row['rule'][:100]}")
        for row in decisions[:5]:
            print(f"DECISION: {row['title'][:100]}")
        return 0

    client = get_graphiti_client()
    if client is None:
        print("[seed_memory_nodes] graph client unavailable; skipping write (fail-open).")
        return 0

    created_conventions, created_decisions = asyncio.run(
        _merge_seed_data(client, args.store_id, conventions, decisions)
    )
    print(
        f"[seed_memory_nodes] wrote conventions={created_conventions} decisions={created_decisions}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
