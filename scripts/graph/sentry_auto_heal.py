#!/usr/bin/env python3
"""
Autonomous Sentry Issue Remediation (Phase 15)

Pulls issues from Sentry and runs them through the self-healing pipeline:
1. Fetch recent issues from Sentry
2. Classify root cause (infrastructure/code/config)
3. Generate fixes (template-first, LLM fallback)
4. Verify in sandbox
5. Auto-apply or queue for approval
"""

import sys
import os
import asyncio
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.sentry_client import SentryClient
from src.graph.orchestrate_healers import orchestrate_remediation


async def main():
    client = SentryClient()

    print("=" * 60)
    print("PHASE 15: AUTONOMOUS SENTRY REMEDIATION")
    print("=" * 60)
    print()

    print("Fetching issues from Sentry dashboard...")
    issues = client.get_recent_issues(limit=5)

    if not issues:
        print("No issues found - your application is healthy!")
        return

    print(f"Found {len(issues)} issue(s):\n")

    for i, issue in enumerate(issues, 1):
        title = issue.get('title', 'Unknown issue')
        status = issue.get('status', 'unknown')
        count = issue.get('count', 0)
        level = issue.get('level', 'error')

        print(f"{i}. {title}")
        print(f"   Status: {status} | Events: {count} | Level: {level}")
        print()

    print("-" * 60)
    print("Starting autonomous remediation pipeline...")
    print("-" * 60)
    print()

    results = []

    for i, issue in enumerate(issues, 1):
        title = issue.get('title', 'Unknown')
        print(f"[{i}/{len(issues)}] Processing: {title}")

        try:
            result = await orchestrate_remediation(issue)
            results.append(result)

            status = result.get('status', 'unknown')
            category = result.get('category', 'unknown')

            print(f"  Category: {category}")

            if status == 'auto_apply_ready':
                confidence = result.get('confidence', 0)
                print(f"  Status: AUTO-FIX READY (confidence: {confidence:.0%})")
            elif status == 'approval_required':
                confidence = result.get('confidence', 0)
                print(f"  Status: APPROVAL REQUIRED (confidence: {confidence:.0%})")
            elif status == 'blocked':
                reason = result.get('reason', 'Unknown')
                print(f"  Status: BLOCKED ({reason})")
            else:
                print(f"  Status: MANUAL INTERVENTION REQUIRED")

            print()

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            print()

    print("=" * 60)
    print("REMEDIATION SUMMARY")
    print("=" * 60)

    auto_apply = sum(1 for r in results if r.get('status') == 'auto_apply_ready')
    approval = sum(1 for r in results if r.get('status') == 'approval_required')
    blocked = sum(1 for r in results if r.get('status') == 'blocked')
    manual = len(results) - auto_apply - approval - blocked

    print(f"Auto-apply ready: {auto_apply}")
    print(f"Approval required: {approval}")
    print(f"Blocked: {blocked}")
    print(f"Manual required: {manual}")
    print()

    if approval > 0:
        print("To review pending approvals:")
        print("  curl http://localhost:5000/api/v1/approvals/")
        print()

    print("Remediation pipeline complete!")


if __name__ == "__main__":
    asyncio.run(main())
