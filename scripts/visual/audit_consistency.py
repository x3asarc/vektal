#!/usr/bin/env python3
"""Audit visual consistency between target page and anchor pages."""

import json
from pathlib import Path
import re
import sys

def audit_consistency(run_id):
    audit = {
        "run_id": run_id,
        "status": "PASS",
        "mismatches": [],
        "consistency_score": 100
    }

    ooda_root = Path(f".planning/ooda-audit/{run_id}")
    fc_dir = ooda_root / "captures/firecrawl"

    if not fc_dir.exists():
        return {"error": f"Evidence not found in {fc_dir}"}

    # 1. Load all captures
    captures = {}
    for fc_file in fc_dir.glob("*.json"):
        try:
            data = json.loads(fc_file.read_text())
            captures[fc_file.stem] = data
        except:
            continue

    if len(captures) < 2:
        return {"error": "Not enough pages captured for consistency audit."}

    # 2. Extract DNA from "Anchor" pages
    anchors = ["search", "chat", "enrichment", "dashboard"]
    
    dna = {
        "sidebar_items": set(),
        "background_colors": set(),
        "spacing_patterns": set(),
        "module_containers": set()
    }

    for name, data in captures.items():
        if any(a in name for a in anchors):
            markdown = data.get("markdown", "")
            # DNA: Sidebar / Global Nav
            links = re.findall(r"\[([^\]]+)\]\((/[^\)]+)\)", markdown)
            for text, href in links:
                if len(text) < 25: dna["sidebar_items"].add(f"{text}:{href}")
            
            # DNA: Module/Card Patterns (Heuristic: Look for common headers or list patterns)
            modules = re.findall(r"### ([^\n]+)", markdown)
            for m in modules: dna["module_containers"].add(m.strip())

    # 3. Check target page against anchor DNA
    for name, data in captures.items():
        markdown = data.get("markdown", "")
        
        # 3.1 Sidebar Drift (Weight: High)
        links = re.findall(r"\[([^\]]+)\]\((/[^\)]+)\)", markdown)
        page_links = {f"{text}:{href}" for text, href in links if len(text) < 25}
        if dna["sidebar_items"]:
            overlap = page_links.intersection(dna["sidebar_items"])
            if len(overlap) < len(dna["sidebar_items"]) * 0.8: # Require 80% parity
                audit["mismatches"].append(f"CRITICAL: Page '{name}' sidebar deviates from Anchor Pages.")
                audit["status"] = "FAIL"

        # 3.2 Component DNA / Spacing (Weight: Medium)
        # Look for the presence of the 'CommandCenter' or 'DashboardSummary' module pattern if applicable
        if "dashboard" in name.lower():
             if "Command Center" not in markdown or "Summary" not in markdown:
                 audit["mismatches"].append(f"UI BREAK: Dashboard missing required module wrappers (CommandCenter/Summary).")
                 audit["status"] = "FAIL"

    # 4. Human-in-the-Loop Upgrade Detection
    # If a page has MORE modules or NEW links compared to anchors, flag it as an UPGRADE
    for name, data in captures.items():
        markdown = data.get("markdown", "")
        modules = re.findall(r"### ([^\n]+)", markdown)
        new_modules = [m for m in modules if m.strip() not in dna["module_containers"]]
        if new_modules:
            audit["mismatches"].append(f"UPGRADE DETECTED: Page '{name}' introduced new modules: {', '.join(new_modules)}. Ask user if these should be global.")

    # 4. Score calculation
    if audit["mismatches"]:
        audit["consistency_score"] = max(0, 100 - (len(audit["mismatches"]) * 25))
    
    return audit

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit_consistency.py <run_id>")
        sys.exit(1)
    
    res = audit_consistency(sys.argv[1])
    print(json.dumps(res, indent=2))
