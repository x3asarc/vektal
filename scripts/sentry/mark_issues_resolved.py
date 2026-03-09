"""Mark fixed Sentry issues as resolved."""
import os
import sys
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

# Issues fixed by engineering-lead agent
FIXED_ISSUES = [
    100523035,  # Site reconnaissance async context manager
    100522706,  # EpisodeType validation
    100521805,  # JSON parsing in MCP server
    # Redis/Celery resilience fixes (commit 81d9f8c) - 750 events
    101522185,  # Connection to Redis lost (713 events)
    101522288,  # Retry limit exceeded (35 events)
    101975024,  # Socket constants TypeError - workers (2 events)
    101975461,  # Socket constants TypeError - flask (1 event)
    # JSON parsing robustness (commit 4f627cc) - 4 events
    101964370,  # API classification Extra data - flask (1 event)
    101960125,  # API classification Extra data - workers (3 events)
    # OpenRouter error handling (commit 65ea28f) - 2 events
    101961468,  # OpenRouter 404 Not Found (1 event)
    100522712,  # OpenRouter 401 Unauthorized (1 event)
]

BASE_URL = "https://sentry.io/api/0"
HEADERS = {
    "Authorization": f"Bearer {SENTRY_TOKEN}",
    "Content-Type": "application/json",
}

def mark_resolved(issue_id: int) -> bool:
    """Mark a Sentry issue as resolved using bulk update endpoint."""
    # Use organization bulk update endpoint which works better
    org = "x3-solutions"
    url = f"{BASE_URL}/organizations/{org}/issues/"

    try:
        with httpx.Client() as client:
            # Bulk update endpoint with query parameter
            response = client.put(
                url,
                headers=HEADERS,
                params={"id": issue_id},  # Query param to target specific issue
                json={"status": "resolved"},
                timeout=10.0
            )
            if response.status_code == 200:
                print(f"✓ Resolved issue {issue_id}")
                return True
            else:
                print(f"✗ Failed to resolve {issue_id}: {response.status_code} {response.text}")
                return False
    except Exception as e:
        print(f"✗ Error resolving {issue_id}: {e}")
        return False

if __name__ == "__main__":
    print(f"Marking {len(FIXED_ISSUES)} issues as resolved...")
    success_count = 0
    for issue_id in FIXED_ISSUES:
        if mark_resolved(issue_id):
            success_count += 1

    print(f"\n{success_count}/{len(FIXED_ISSUES)} issues marked as resolved")
    sys.exit(0 if success_count == len(FIXED_ISSUES) else 1)
