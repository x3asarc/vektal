#!/usr/bin/env python3
"""Analyze congruence between Plan, Tokens, and Live UI."""

import json
from pathlib import Path
import re
import sys

def analyze_congruence(run_id, plan_path="PLAN.md", token_path="design-tokens-v2.json"):
    report = {
        "run_id": run_id,
        "congruence": "Partial",
        "findings": [],
        "satisfaction": 0
    }

    ooda_root = Path(f".planning/ooda-audit/{run_id}")
    fc_dir = ooda_root / "captures/firecrawl"

    if not fc_dir.exists():
        return {"error": f"Evidence not found in {fc_dir}"}

    # 1. Load Plan
    plan_content = ""
    if Path(plan_path).exists():
        plan_content = Path(plan_path).read_text()

    # 2. Load Tokens
    tokens = {}
    if Path(token_path).exists():
        try:
            tokens = json.loads(Path(token_path).read_text())
        except:
            pass

    # 3. Analyze each capture
    for fc_file in fc_dir.glob("*.json"):
        try:
            data = json.loads(fc_file.read_text())
            markdown = data.get("markdown", "")
            
            # Simple Plan congruence: check for keywords
            if plan_content:
                # Extract probable elements from PLAN (look for <done> or specific nouns)
                promised = re.findall(r"([A-Z][a-z]+ (?:Button|Link|Form|Section))", plan_content)
                for item in set(promised):
                    if item.lower() not in markdown.lower():
                        report["findings"].append(f"Missing promised element: {item}")

            # Simple Token congruence (e.g. check if primary color hex is in markdown if included)
            # This is naive but provides a baseline for OODA loop
            if tokens:
                primary = tokens.get("tokens", {}).get("colors", {}).get("brand", {}).get("primary")
                if primary and primary not in markdown:
                    # Hex colors rarely appear in markdown scrapes, but we note it for human check
                    report["findings"].append(f"Primary token {primary} not detected in raw structural scrape.")

        except:
            continue

    if not report["findings"]:
        report["congruence"] = "Match"
        report["satisfaction"] = 100
    else:
        report["satisfaction"] = max(0, 100 - (len(report["findings"]) * 10))

    return report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_congruence.py <run_id>")
        sys.exit(1)
    
    res = analyze_congruence(sys.argv[1])
    print(json.dumps(res, indent=2))
