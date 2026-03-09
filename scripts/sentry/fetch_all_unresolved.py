"""Fetch all unresolved issues from all Sentry projects."""
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

def fetch_all_projects() -> list[dict]:
    """Fetch all projects in the organization."""
    url = f"{BASE_URL}/organizations/x3-solutions/projects/"

    try:
        with httpx.Client() as client:
            response = client.get(url, headers=HEADERS, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return []

def fetch_unresolved_issues(project_slug: str) -> list[dict]:
    """Fetch unresolved issues for a specific project."""
    url = f"{BASE_URL}/projects/x3-solutions/{project_slug}/issues/"

    try:
        with httpx.Client() as client:
            response = client.get(
                url,
                headers=HEADERS,
                params={"query": "is:unresolved", "statsPeriod": "14d"},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching issues for {project_slug}: {e}")
        return []

if __name__ == "__main__":
    print("Fetching all projects...")
    projects = fetch_all_projects()

    if not projects:
        print("No projects found or error occurred")
        sys.exit(1)

    print(f"Found {len(projects)} projects\n")

    all_issues = []
    for project in projects:
        project_name = project.get("name", "Unknown")
        project_slug = project.get("slug", "")

        print(f"Checking {project_name} ({project_slug})...")
        issues = fetch_unresolved_issues(project_slug)

        if issues:
            print(f"  → {len(issues)} unresolved issues")
            for issue in issues:
                all_issues.append({
                    "project": project_name,
                    "project_slug": project_slug,
                    "issue_id": issue.get("id"),
                    "title": issue.get("title", ""),
                    "culprit": issue.get("culprit", ""),
                    "count": issue.get("count", 0),
                    "level": issue.get("level", ""),
                    "lastSeen": issue.get("lastSeen", ""),
                })
        else:
            print(f"  → 0 unresolved issues")

    print(f"\n{'='*80}")
    print(f"TOTAL UNRESOLVED: {len(all_issues)} issues")
    print(f"{'='*80}\n")

    if all_issues:
        print("Issue ID | Project | Title | Count | Last Seen")
        print("-" * 120)
        for issue in all_issues:
            issue_id = issue["issue_id"]
            project = issue["project"][:20]
            title = issue["title"][:50]
            count = issue["count"]
            last_seen = issue["lastSeen"][:19]
            print(f"{issue_id} | {project:<20} | {title:<50} | {count:>5} | {last_seen}")

        # Write to file for reference
        output_file = PROJECT_ROOT / ".tasks" / "UNRESOLVED_ISSUES.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_issues, f, indent=2)

        print(f"\nFull details written to: {output_file}")
