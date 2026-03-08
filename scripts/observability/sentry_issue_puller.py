"""
Sentry Issue Puller and Normalizer (Phase 14.3).
Polls Sentry REST API for unresolved errors, normalizes failures, and triggers ingestion.
Supports daemon mode for autonomous operation.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
import logging
import os
import re
import subprocess
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
from src.memory.event_log import append_event
from src.memory.event_schema import EventType, create_event

# ── Task 11b: SentryIssue → Graph bridge helpers ─────────────────────────────
def _cul_to_module(culprit: str) -> tuple[str, str | None]:
    """Parse Sentry culprit into (module_dotted, function_name | None).
    Examples:
      'src/graph/sentry_ingestor.py in ingest_failure_event' → ('src.graph.sentry_ingestor', 'ingest_failure_event')
      'src/core/graphiti_client.py'                          → ('src.core.graphiti_client', None)
    """
    fn_name: str | None = None
    path = culprit.strip()
    if " in " in path:
        path, fn_name = path.rsplit(" in ", 1)
        fn_name = fn_name.strip()
    norm = path.replace("\\", "/").replace(".py", "")
    if norm.startswith("./"):
        norm = norm[2:]
    module = norm.replace("/", ".")
    return module, fn_name


def _write_sentry_issue_to_graph(event: FailureEvent, driver) -> None:
    """Write :SentryIssue node + OCCURRED_IN / REPORTED_IN edges to Aura.

    Runs as best-effort after episode ingest — never blocks the ingest cycle.
    Bi-temporal filter: only links to Function/File nodes with EndDate IS NULL.
    """
    try:
        module_name, fn_name = _cul_to_module(event.culprit)
        fn_sig = f"{module_name}.{fn_name}" if fn_name else None

        with driver.session() as s:
            # Upsert :SentryIssue node
            s.run("""
                MERGE (si:SentryIssue {issue_id: $issue_id})
                SET si.title = $title,
                    si.category = $category,
                    si.culprit = $culprit,
                    si.level = $level,
                    si.timestamp = $ts,
                    si.resolved = false,
                    si.module_path = $module
            """,
            issue_id=event.event_id,
            title=event.title,
            category=event.category,
            culprit=event.culprit,
            level=event.level,
            ts=event.timestamp,
            module=module_name,
            )

            # [:OCCURRED_IN] → specific Function (if culprit has "in <function>")
            if fn_sig:
                s.run("""
                    MATCH (si:SentryIssue {issue_id: $issue_id})
                    MATCH (f:Function {function_signature: $sig})
                    WHERE f.EndDate IS NULL
                    MERGE (si)-[:OCCURRED_IN]->(f)
                """, issue_id=event.event_id, sig=fn_sig)

            # [:REPORTED_IN] → File node (module → file path)
            file_path = module_name.replace(".", "/") + ".py"
            s.run("""
                MATCH (si:SentryIssue {issue_id: $issue_id})
                MATCH (f:File) WHERE f.path ENDS WITH $file_path
                  AND f.EndDate IS NULL
                MERGE (si)-[:REPORTED_IN]->(f)
            """, issue_id=event.event_id, file_path=file_path)

    except Exception as e:
        logger.debug("[SentryPuller] Graph write skipped: %s", e)

logger = logging.getLogger(__name__)

GRAPH_DIR = PROJECT_ROOT / ".graph"
CURSOR_PATH = GRAPH_DIR / "sentry-cursor.json"
PID_PATH = GRAPH_DIR / "sentry-worker.pid"
HEALTH_PATH = GRAPH_DIR / "sentry-worker-health.json"
PULLER_SOURCE = "scripts/observability/sentry_issue_puller.py"
RUN_SESSION_ID = f"sentry-puller-{os.getpid()}"


@dataclass(frozen=True)
class PullResult:
    events: List[FailureEvent]
    cursor_state: Dict[str, Any]
    error: Optional[str] = None


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


def _write_health(
    status: str,
    events: int = 0,
    error: Optional[str] = None,
    cursor_state: Optional[Dict[str, Any]] = None,
) -> None:
    _ensure_graph_dir()
    payload = {
        "pid": os.getpid(),
        "status": status,
        "events_processed": events,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
        "cursor_state": cursor_state or {},
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


def _extract_error_type(issue: Dict[str, Any], title: str) -> str:
    metadata = issue.get("metadata") if isinstance(issue.get("metadata"), dict) else {}
    raw = issue.get("error_type") or metadata.get("type") or issue.get("type")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    head = title.split(":", 1)[0].strip()
    return head or "UnknownError"


def normalize_issue(issue: Dict[str, Any]) -> FailureEvent:
    """Map Sentry issue data to Phase 14.3 FailureEvent taxonomy."""
    title = issue.get("title", "")
    culprit = issue.get("culprit", "unknown")
    issue_id = str(issue.get("id", "unknown"))
    error_type = _extract_error_type(issue, title)
    affected_module = culprit if isinstance(culprit, str) and culprit.strip() else "unknown"
    tags = {
        t["key"]: t["value"]
        for t in issue.get("tags", [])
        if isinstance(t, dict) and "key" in t and "value" in t
    }
    tags["issue_id"] = issue_id
    tags["error_type"] = error_type
    tags["affected_module"] = affected_module

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
        event_id=issue_id,
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


def _emit_issue_pulled_event(event: FailureEvent) -> None:
    try:
        envelope = create_event(
            event_type=EventType.SENTRY_ISSUE_PULLED,
            provider="sentry",
            session_id=RUN_SESSION_ID,
            source=PULLER_SOURCE,
            scope={"phase": "15.1", "issue_id": event.event_id},
            payload={
                "issue_id": event.event_id,
                "level": event.level,
                "error_type": event.tags.get("error_type", "UnknownError"),
                "affected_module": event.tags.get("affected_module", event.culprit),
                "timestamp": event.timestamp,
                "category": event.category,
                "title": event.title,
            },
            provenance={"component": "sentry_issue_puller"},
        )
        result = append_event(envelope, fail_open=True)
        if not result.get("ok", False):
            logger.warning("[SentryPuller] Canonical event write failed: %s", result.get("error", "unknown"))
    except Exception as exc:
        logger.warning("[SentryPuller] Canonical event emission skipped: %s", exc)


def _refresh_materialized_views() -> None:
    script_path = PROJECT_ROOT / "scripts" / "memory" / "materialize_views.py"
    command = [sys.executable, str(script_path), "--mode", "incremental"]
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception as exc:
        logger.warning("[SentryPuller] Memory view refresh failed: %s", exc)
        return
    if completed.returncode != 0:
        logger.warning(
            "[SentryPuller] Memory view refresh returned %s: %s",
            completed.returncode,
            (completed.stderr or completed.stdout or "").strip()[:300],
        )


async def pull_sentry_issues(manual: bool = False) -> PullResult:
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
        normalized = [normalize_issue(i) for i in mock_issues]
        return PullResult(
            events=normalized,
            cursor_state={"mode": "manual", "last_cursor": None, "pages_fetched": 1},
            error=None,
        )

    if not auth_token:
        error = "SENTRY_AUTH_TOKEN missing"
        logger.warning("[SentryPuller] %s; poll skipped.", error)
        return PullResult(
            events=[],
            cursor_state={"mode": "api", "last_cursor": _load_cursor(), "pages_fetched": 0},
            error=error,
        )

    base_url = f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/"
    headers = {"Authorization": f"Bearer {auth_token}"}
    base_params = {"query": "is:unresolved level:error", "limit": 25}

    logger.info("[SentryPuller] Polling project %s/%s", org_slug, project_slug)

    cursor = _load_cursor()
    events: List[FailureEvent] = []
    seen_ids: Set[str] = set()
    pages_fetched = 0
    last_error: Optional[str] = None

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            params = dict(base_params)
            if cursor:
                params["cursor"] = cursor

            try:
                resp = await client.get(base_url, headers=headers, params=params)
            except Exception as exc:
                last_error = f"request_error:{type(exc).__name__}:{str(exc)}"
                logger.error("[SentryPuller] Request error: %s", exc)
                break

            if resp.status_code != 200:
                last_error = f"http_error:{resp.status_code}"
                logger.error(
                    "[SentryPuller] API failed (HTTP %s): %s",
                    resp.status_code,
                    resp.text[:500],
                )
                break

            pages_fetched += 1
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

    return PullResult(
        events=events,
        cursor_state={"mode": "api", "last_cursor": cursor, "pages_fetched": pages_fetched},
        error=last_error,
    )


async def run_ingestion_cycle(manual: bool = False) -> Dict[str, Any]:
    """Pull and ingest one cycle of Sentry issues. Returns ingested count."""
    pull_result = await pull_sentry_issues(manual=manual)
    logger.info("[SentryPuller] Pulled %s event(s).", len(pull_result.events))

    # Task 11b: acquire Neo4j driver once per cycle for SentryIssue graph writes
    _graph_driver = None
    try:
        from neo4j import GraphDatabase
        _neo4j_uri = os.getenv("NEO4J_URI")
        _neo4j_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
        _neo4j_pwd = os.getenv("NEO4J_PASSWORD")
        if _neo4j_uri and _neo4j_pwd:
            _graph_driver = GraphDatabase.driver(_neo4j_uri, auth=(_neo4j_user, _neo4j_pwd))
            # Ensure SentryIssue constraint exists
            with _graph_driver.session() as s:
                s.run("CREATE CONSTRAINT sentry_issue_id_unique IF NOT EXISTS "
                      "FOR (si:SentryIssue) REQUIRE si.issue_id IS UNIQUE")
    except Exception as e:
        logger.debug("[SentryPuller] Graph driver init skipped: %s", e)

    ingested = 0
    for event in pull_result.events:
        _emit_issue_pulled_event(event)
        logger.info("[SentryPuller] [%s] %s", event.category, event.title)
        if await ingest_failure_event(event):
            ingested += 1
        # Task 11b: write SentryIssue node + graph edges
        if _graph_driver:
            _write_sentry_issue_to_graph(event, _graph_driver)

    if _graph_driver:
        try:
            _graph_driver.close()
        except Exception:
            pass

    if pull_result.error is None:
        _refresh_materialized_views()
    return {
        "ingested": ingested,
        "events_processed": len(pull_result.events),
        "cursor_state": pull_result.cursor_state,
        "error": pull_result.error,
    }


async def run_daemon(interval_seconds: int) -> None:
    """Autonomous polling loop with heartbeat/pid tracking."""
    _write_pid()
    logger.info("[SentryPuller] Daemon started (pid=%s, interval=%ss).", os.getpid(), interval_seconds)
    _write_health("running", events=0)

    try:
        while True:
            try:
                cycle = await run_ingestion_cycle(manual=False)
                _write_health(
                    "running",
                    events=int(cycle["events_processed"]),
                    error=cycle.get("error"),
                    cursor_state=cycle.get("cursor_state"),
                )
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

    cycle = await run_ingestion_cycle(manual=args.manual)
    _write_health(
        "running",
        events=int(cycle["events_processed"]),
        error=cycle.get("error"),
        cursor_state=cycle.get("cursor_state"),
    )
    logger.info("[SentryPuller] Ingested %s event(s).", cycle["ingested"])
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
