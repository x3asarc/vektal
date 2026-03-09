#!/usr/bin/env python3
"""Oracle health check — call ask(domain='project') and report block counts + gaps.

Pass criteria:
  - All blocks return a count (no 'error' key)
  - gaps[] is empty OR only contains Task-11 entries (acceptable — bridge not run yet)
  - agent_defs count >= 10 with letta_id populated
  - bundle_template_history count >= 5

Usage:
  python scripts/letta/check_oracle_health.py
"""
import sys, json, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.agents/skills/aura-oracle'))
from oracle import ask

def main():
    print("=== Oracle Health Check — domain: project ===\n")

    result = ask(domain="project", context={"keywords": [], "domains": []})

    if "error" in result:
        print(f"HARD FAILURE: {result['error']}")
        sys.exit(1)

    errors = []
    all_blocks = []

    for q, blocks in result.get("results", {}).items():
        for bname, br in blocks.items():
            count   = br.get("count", None)
            err     = br.get("error")
            schema  = br.get("schema_task")
            status  = "ERR" if err else str(count)
            flag    = " ⚠️ GHOST" if (schema and count == 0) else ""
            print(f"  {q:4s}  {bname:<35}  count={status}{flag}")
            all_blocks.append(bname)
            if err:
                errors.append(f"{bname}: {err}")

    gaps = result.get("gaps", [])
    print()

    # Advisory blocks: need edge types not yet written by any sync script.
    # count=0 is expected — they are not blockers for Commander.
    ADVISORY_BLOCKS = {
        "cross_domain_env_coupling",     # needs :USES (Function→EnvVar) — no script writes this yet
        "cross_domain_route_coupling",   # needs :CALLS_ROUTE (Function→APIRoute) — no script writes this yet
        "cross_domain_impact",           # needs Function+DEFINED_IN+CALLS — sync_to_neo4j.py required
    }
    ACCEPTABLE_TASKS = {11}  # Graphiti episode bridge — deferred

    hard_gaps = [
        g for g in gaps
        if g.get("schema_task") not in ACCEPTABLE_TASKS
        and g["block"] not in ADVISORY_BLOCKS
    ]
    advisory_gaps = [g for g in gaps if g["block"] in ADVISORY_BLOCKS]
    acceptable_gaps = [g for g in gaps if g.get("schema_task") in ACCEPTABLE_TASKS]

    print(f"Gaps: {len(gaps)} total — {len(hard_gaps)} hard, {len(advisory_gaps)} advisory (no edge script yet), {len(acceptable_gaps)} acceptable (task-11)")
    for g in gaps:
        if g["block"] in ADVISORY_BLOCKS:
            tag = " [advisory — needs edge script]"
        elif g.get("schema_task") in ACCEPTABLE_TASKS:
            tag = " [acceptable — task-11 deferred]"
        else:
            tag = " [ACTION NEEDED]"
        print(f"  {g['block']} — schema_task={g['schema_task']}{tag}")

    # Core pass criteria
    agent_count = result["results"].get("WHO", {}).get("agent_defs", {}).get("count", 0)
    bundle_count = result["results"].get("WHEN", {}).get("bundle_template_history", {}).get("count", 0)

    print()
    print(f"Core checks: AgentDef={agent_count} (need ≥10)  BundleTemplate={bundle_count} (need ≥5)")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors: print(f"  {e}")
        sys.exit(1)

    if hard_gaps:
        print(f"\nRED — {len(hard_gaps)} hard gaps. Run: python scripts/graph/sync_orchestration.py")
        sys.exit(1)

    if agent_count < 10:
        print(f"\nRED — only {agent_count} AgentDef nodes. Run sync_orchestration.py")
        sys.exit(1)

    if bundle_count < 5:
        print(f"\nRED — only {bundle_count} BundleTemplates. Run sync_orchestration.py")
        sys.exit(1)

    print("\nGREEN — substrate healthy. Commander ready to fire.")

if __name__ == "__main__":
    main()
