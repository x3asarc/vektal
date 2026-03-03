"""
Sentry Issue Puller and Normalizer (Phase 14.3).
Polls Sentry REST API for unresolved errors, normalizes failures, and triggers ingestion.
Supports daemon mode for autonomous operation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.graph.sentry_ingestor import FailureEvent, ingest_failure_event

logger = logging.getLogger(__name__)

GRAPH_DIR = PROJECT_ROOT / ".graph"
CURSOR_PATH = GRAPH_DIR / "sentry-cursor.json"
PID_PATH = GRAPH_DIR / "sentry-worker.pid"
HEALTH_PATH = GRAPH_DIR / "sentry-worker-health.json"


def _ensure_graph_dir() -> None:
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)


def _load_cursor() -> Optional[str]:
    if not CURSOR_PATH.exists():
        return None
    try:
        data = json.loads(CURSOR_PATH.read_text(encoding="utf-8"))
        return data.get("cursor") or data.get("last_seen_id")
    except Exception:
        return None


def _save_cursor(cursor: Optional[str]) -> None:
    _ensure_graph_dir()
    payload = {
        "cursor": cursor,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    CURSOR_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _parse_next_cursor(link_header: str) -> Optional[str]:
    """
    Parse Sentry Link header for next cursor with results=true.
    Example:
    <...&cursor=abc>; rel="previous"; results="false"; cursor="abc",
    <...&cursor=def>; rel="next"; results="true"; cursor="def"
    """
    if not link_header:
        return None

    for part in link_header.split(","):
        if 'rel="next"' not in part:
            continue
        results_match = re.search(r'results="(true|false)"', part)
        if not results_match or results_match.group(1) != "true":
            return None
        cursor_match = re.search(r'cursor="([^"]+)"', part)
        if cursor_match:
            return cursor_match.group(1)
    return None


def _write_health(status: str, events: int = 0, error: Optional[str] = None) -> None:
    _ensure_graph_dir()
    payload = {
        "pid": os.getpid(),
        "status": status,
        "events_processed": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }
    HEALTH_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_pid() -> None:
    _ensure_graph_dir()
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid() -> None:
    try:
        if PID_PATH.exists():
            PID_PATH.unlink()
    except Exception:
        pass


def normalize_issue(issue: Dict[str, Any]) -> FailureEvent:
    """Map Sentry issue data to Phase 14.3 FailureEvent taxonomy."""
    title = issue.get("title", "")
    culprit = issue.get("culprit", "unknown")
    tags = {
        t["key"]: t["value"]
        for t in issue.get("tags", [])
        if isinstance(t, dict) and "key" in t and "value" in t
    }

    category = "UNKNOWN"
    title_lower = title.lower()

    if any(k in title_lower for k in ["serviceunavailable", "neo4jerror", "aura"]):
        category = "AURA_UNREACHABLE"
    elif any(k in title_lower for k in ["docker.errors", "connectionrefused", "neo4j_start"]):
        category = "LOCAL_NEO4J_START_FAIL"
    elif any(k in title_lower for k in ["filenotfound", "jsondecodeerror", "snapshot"]):
        category = "SNAPSHOT_CORRUPT"
    elif any(k in title_lower for k in ["tasktimeout", "celeryerror", "sync"]):
        category = "SYNC_TIMEOUT"

    return FailureEvent(
        event_id=str(issue.get("id", "unknown")),
        title=title,
        category=category,
        culprit=culprit,
        timestamp=issue.get("lastSeen", datetime.now(timezone.utc).isoformat()),
        tags=tags,
        level=issue.get("level", "error"),
    )


def _resolve_sentry_project() -> tuple[str, str]:
    """
    Resolve Sentry org/project locator.

    Priority:
    1) explicit SENTRY_ORG_SLUG + SENTRY_PROJECT_SLUG
    2) numeric org/project parsed from SENTRY_DSN (o<org_id> + /<project_id>)
    3) legacy default slugs
    """
    org_slug = (os.getenv("SENTRY_ORG_SLUG") or "").strip()
    project_slug = (os.getenv("SENTRY_PROJECT_SLUG") or "").strip()
    if org_slug and project_slug:
        return org_slug, project_slug

    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if dsn:
        parsed = urlparse(dsn)
        # Example host: o4510917867929600.ingest.de.sentry.io
        org_match = re.search(r"o(\d+)\.", parsed.netloc or "")
        # Example path: /4510917894930512
        project_id = (parsed.path or "/").strip("/").split("/")[0]
        if org_match and project_id.isdigit():
            return org_match.group(1), project_id

    return "shopify-scraping-script", "shopify-scraping-script"


async def pull_sentry_issues(manual: bool = False) -> List[FailureEvent]:
    """Poll Sentry API for unresolved error issues with cursor pagination."""
    auth_token = os.getenv("SENTRY_AUTH_TOKEN")
    org_slug, project_slug = _resolve_sentry_project()

    if manual:
        logger.info("[SentryPuller] Manual mode enabled; using mock failure data.")
        mock_issues = [
            {
                "id": "mock-1",
                "title": "Neo4jError: ServiceUnavailable (Aura Paused)",
                "culprit": "src/core/graphiti_client.py",
                "lastSeen": datetime.now(timezone.utc).isoformat(),
                "tags": [{"key": "level", "value": "error"}],
            },
            {
                "id": "mock-2",
                "title": "FileNotFoundError: .graph/local-snapshot.json missing",
                "culprit": "src/graph/local_graph_store.py",
                "lastSeen": datetime.now(timezone.utc).isoformat(),
                "tags": [{"key": "level", "value": "error"}],
            },
        ]
        return [normalize_issue(i) for i in mock_issues]

    if not auth_token:
        logger.warning("[SentryPuller] SENTRY_AUTH_TOKEN missing; poll skipped.")
        return []

    base_url = f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/"
    headers = {"Authorization": f"Bearer {auth_token}"}
    base_params = {"query": "is:unresolved level:error", "limit": 25}

    logger.info("[SentryPuller] Polling project %s/%s", org_slug, project_slug)

    cursor = _load_cursor()
    events: List[FailureEvent] = []
    seen_ids: Set[str] = set()

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            params = dict(base_params)
            if cursor:
                params["cursor"] = cursor

            try:
                resp = await client.get(base_url, headers=headers, params=params)
            except Exception as exc:
                logger.error("[SentryPuller] Request error: %s", exc)
                break

            if resp.status_code != 200:
                logger.error(
                    "[SentryPuller] API failed (HTTP %s): %s",
                    resp.status_code,
                    resp.text[:500],
                )
                break

            issues = resp.json()
            for issue in issues:
                event = normalize_issue(issue)
                if event.event_id in seen_ids:
                    continue
                seen_ids.add(event.event_id)
                events.append(event)

            next_cursor = _parse_next_cursor(resp.headers.get("Link", ""))
            if not next_cursor:
                break
            cursor = next_cursor

    # Persist last cursor when available so subsequent runs continue paging.
    if cursor:
        _save_cursor(cursor)

    return events


async def run_ingestion_cycle(manual: bool = False) -> int:
    """Pull and ingest one cycle of Sentry issues. Returns ingested count."""
    events = await pull_sentry_issues(manual=manual)
    logger.info("[SentryPuller] Pulled %s event(s).", len(events))

    ingested = 0
    for event in events:
        logger.info("[SentryPuller] [%s] %s", event.category, event.title)
        if await ingest_failure_event(event):
            ingested += 1
    return ingested


async def run_daemon(interval_seconds: int) -> None:
    """Autonomous polling loop with heartbeat/pid tracking."""
    _write_pid()
    logger.info("[SentryPuller] Daemon started (pid=%s, interval=%ss).", os.getpid(), interval_seconds)
    _write_health("running", events=0)

    try:
        while True:
            try:
                ingested = await run_ingestion_cycle(manual=False)
                _write_health("running", events=ingested)
            except Exception as exc:
                logger.exception("[SentryPuller] Daemon cycle failed: %s", exc)
                _write_health("error", events=0, error=str(exc))

            await asyncio.sleep(interval_seconds)
    finally:
        _remove_pid()
        _write_health("stopped", events=0)


async def _main_async(args: argparse.Namespace) -> int:
    if args.daemon:
        await run_daemon(interval_seconds=args.interval)
        return 0

    ingested = await run_ingestion_cycle(manual=args.manual)
    _write_health("running", events=ingested)
    logger.info("[SentryPuller] Ingested %s event(s).", ingested)
    return 0


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Poll and ingest Sentry issues.")
    parser.add_argument("--manual", action="store_true", help="Use mock issues instead of Sentry API.")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in autonomous daemon mode.")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("SENTRY_PULL_INTERVAL_SECONDS", "120")),
        help="Polling interval in seconds for daemon mode.",
    )
    args = parser.parse_args()

    if args.interval < 30:
        args.interval = 30

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
