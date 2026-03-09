"""Fetch Sentry issue details for investigation."""
import os
import sys
import json
import httpx
from pathlib import Path

# Fix Windows encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Load token from .env
env_file = PROJECT_ROOT / ".env"
SENTRY_TOKEN = None
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("SENTRY_AUTH_TOKEN="):
                SENTRY_TOKEN = line.split("=", 1)[1].strip()
                break

if not SENTRY_TOKEN:
    print("ERROR: SENTRY_AUTH_TOKEN not found in .env")
    sys.exit(1)

BASE_URL = "https://sentry.io/api/0"
HEADERS = {
    "Authorization": f"Bearer {SENTRY_TOKEN}",
    "Content-Type": "application/json",
}

def fetch_issue(issue_id: int, project_slug: str = "synthex-workers") -> dict:
    """Fetch detailed information about a Sentry issue."""
    # Try project-scoped endpoint first
    url = f"{BASE_URL}/projects/x3-solutions/{project_slug}/issues/"

    try:
        with httpx.Client() as client:
            response = client.get(
                url,
                headers=HEADERS,
                params={"query": f"id:{issue_id}"},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            if data:
                return data[0]
            return {}
    except Exception as e:
        print(f"Error fetching issue {issue_id}: {e}")
        return {}

def fetch_latest_event(issue_id: int, project_slug: str = "synthex-workers") -> dict:
    """Fetch the latest event for an issue."""
    url = f"{BASE_URL}/projects/x3-solutions/{project_slug}/issues/{issue_id}/events/latest/"

    try:
        with httpx.Client() as client:
            response = client.get(url, headers=HEADERS, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching latest event for {issue_id}: {e}")
        return {}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_issue.py <issue_id> [<issue_id2> ...]")
        sys.exit(1)

    for issue_id_str in sys.argv[1:]:
        issue_id = int(issue_id_str)
        print(f"\n{'='*80}")
        print(f"Issue #{issue_id}")
        print(f"{'='*80}")

        # Fetch issue metadata
        issue = fetch_issue(issue_id)
        if issue:
            print(f"\nTitle: {issue.get('title', 'N/A')}")
            print(f"Type: {issue.get('type', 'N/A')}")
            print(f"Status: {issue.get('status', 'N/A')}")
            print(f"Level: {issue.get('level', 'N/A')}")
            print(f"Count: {issue.get('count', 'N/A')} events")
            print(f"First seen: {issue.get('firstSeen', 'N/A')}")
            print(f"Last seen: {issue.get('lastSeen', 'N/A')}")

            culprit = issue.get('culprit', 'N/A')
            print(f"Culprit: {culprit}")

            metadata = issue.get('metadata', {})
            if metadata:
                print(f"\nMetadata:")
                print(f"  Type: {metadata.get('type', 'N/A')}")
                print(f"  Value: {metadata.get('value', 'N/A')}")
                print(f"  Filename: {metadata.get('filename', 'N/A')}")

        # Fetch latest event for stack trace
        event = fetch_latest_event(issue_id)
        if event:
            print(f"\n--- Latest Event ---")
            entries = event.get('entries', [])
            for entry in entries:
                if entry.get('type') == 'exception':
                    values = entry.get('data', {}).get('values', [])
                    for exc_value in values:
                        print(f"\nException: {exc_value.get('type', 'N/A')}")
                        print(f"Value: {exc_value.get('value', 'N/A')}")

                        stacktrace = exc_value.get('stacktrace', {})
                        frames = stacktrace.get('frames', [])
                        if frames:
                            print(f"\nStack trace:")
                            for frame in frames[-10:]:  # Last 10 frames
                                filename = frame.get('filename', 'N/A')
                                function = frame.get('function', 'N/A')
                                lineno = frame.get('lineno', 'N/A')
                                context = frame.get('context', [])
                                print(f"  {filename}:{lineno} in {function}")
                                if context:
                                    for line in context[-3:]:  # Last 3 lines of context
                                        print(f"    {line[1]}")
