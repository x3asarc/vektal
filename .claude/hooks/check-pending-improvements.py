#!/usr/bin/env python3
"""
SessionStart Hook: Check for pending auto-improvements
Notifies user of escalated improvements that need review
"""

import json
from pathlib import Path

def main():
    escalation_file = Path(".claude/escalations/pending-improvements.json")

    if not escalation_file.exists():
        print("✅ No pending improvements")
        return 0

    try:
        with open(escalation_file) as f:
            escalations = json.load(f)
    except Exception as e:
        print(f"⚠️  Could not read escalations: {e}")
        return 0

    pending = [e for e in escalations if e.get("status") == "pending"]

    if not pending:
        print("✅ No pending improvements")
        return 0

    print(f"\n⚠️  {len(pending)} pending improvement(s) need review:")
    print(f"   Location: {escalation_file}")
    print()

    # Show summary of each pending improvement
    for i, improvement in enumerate(pending[:3], 1):  # Show first 3
        print(f"   {i}. Phase {improvement.get('phase')}-{improvement.get('plan')}")
        print(f"      Root cause: {improvement.get('root_cause')}")
        print(f"      Proposed: {improvement.get('proposed_fix', 'N/A')[:60]}...")
        print(f"      Confidence: {improvement.get('confidence', 0):.0%}")
        print()

    if len(pending) > 3:
        print(f"   ... and {len(pending) - 3} more")
        print()

    print("   Review file and apply manually if appropriate")
    print()

    return 0

if __name__ == "__main__":
    exit(main())
