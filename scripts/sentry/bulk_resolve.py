"""Bulk resolve issues by ID."""
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

BASE_URL = "https://sentry.io/api/0"
HEADERS = {
    "Authorization": f"Bearer {SENTRY_TOKEN}",
    "Content-Type": "application/json",
}

# Old issues that should be resolved (predating our fixes)
OLD_ISSUES_TO_RESOLVE = [
    101549134,  # Neo4j similar_files - 2d ago
    101549138,  # Neo4j ParameterMissing - 2d ago
    101549129,  # Neo4j search similar entities - 2d ago
    101522296,  # Neo4j imports template - 2d ago
    101522291,  # Neo4j query pending - 2d ago
    100522741,  # Test error - 6d ago
]

def mark_resolved(issue_id: int) -> bool:
    """Mark a Sentry issue as resolved."""
    org = "x3-solutions"
    url = f"{BASE_URL}/organizations/{org}/issues/"

    try:
        with httpx.Client() as client:
            response = client.put(
                url,
                headers=HEADERS,
                params={"id": issue_id},
                json={"status": "resolved"},
                timeout=10.0
            )
            if response.status_code == 200:
                print(f"✓ Resolved issue {issue_id}")
                return True
            else:
                print(f"✗ Failed to resolve {issue_id}: {response.status_code} {response.text[:200]}")
                return False
    except Exception as e:
        print(f"✗ Error resolving {issue_id}: {e}")
        return False

if __name__ == "__main__":
    print(f"Marking {len(OLD_ISSUES_TO_RESOLVE)} old issues as resolved...")
    success_count = 0
    for issue_id in OLD_ISSUES_TO_RESOLVE:
        if mark_resolved(issue_id):
            success_count += 1

    print(f"\n{success_count}/{len(OLD_ISSUES_TO_RESOLVE)} issues marked as resolved")
    sys.exit(0 if success_count == len(OLD_ISSUES_TO_RESOLVE) else 1)
