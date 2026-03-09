#!/usr/bin/env python3
"""Verify T1-T4 oracle/architecture changes."""
import os, re, sys

results = []

def chk(label, ok):
    results.append((label, ok))
    print(("GREEN  " if ok else "RED    ") + label)

oracle = open(".claude/skills/aura-oracle/oracle.py", encoding="utf-8").read()
cmd    = open(".claude/agents/commander.md", encoding="utf-8").read()
spec   = open("docs/agent-system/specs/task-observer.md", encoding="utf-8", errors="replace").read()
v2     = open("docs/agent-system/commander-architecture-v2.md", encoding="utf-8").read()

# T1 ── schema_task guard removed
chk("T1  guard string gone",         "requires graph sprint Task" not in oracle)
chk("T1  schema_task extracted",     "schema_task = block.get" in oracle)
chk("T1  schema_task in ok-return",  '"schema_task": schema_task' in oracle)
chk("T1  schema_task in err-return", '"schema_task": schema_task' in oracle)

# T2 ── new oracle blocks + project profile + commander LOAD
chk("T2  improvement_proposals block",  '"improvement_proposals"' in oracle)
chk("T2  oracle_gaps_recent block",     '"oracle_gaps_recent"' in oracle)
chk("T2  sentry in project profile",    bool(re.search(r'"project".*?sentry_unresolved', oracle, re.DOTALL)))
chk("T2  oracle_gaps in project profile", bool(re.search(r'"project".*?oracle_gaps_recent', oracle, re.DOTALL)))
chk("T2  improvement_props in project",  bool(re.search(r'"project".*?improvement_proposals', oracle, re.DOTALL)))
chk("T2  commander uses aura-oracle",   "ask(domain=" in cmd)
chk("T2  LOAD step uses aura-oracle",   "ask(domain=" in cmd and "GraphDatabase" not in cmd.split("Step 1")[1].split("Step 2")[0])
chk("T2  oracle Layer0 checks in cmd",  "oracle_gaps_recent" in cmd)
for plat in [".letta/agents/commander.md", ".codex/agents/commander.md", ".gemini/agents/commander.md"]:
    chk(f"T2  {plat} synced",          "ask(domain=" in open(plat).read())

# T3 ── gaps in ask() return + task-observer spec
chk("T3  gaps list built in ask()",    "gaps = []" in oracle)
chk("T3  gaps returned by ask()",      '"gaps": gaps' in oracle)
chk("T3  schema_task+count condition", "schema_task" in oracle and 'count", -1) == 0' in oracle)
chk("T3  TO-DETECT-ORACLE-GAPS action", "TO-DETECT-ORACLE-GAPS" in spec)
chk("T3  block->script table",          "sync_routes_tasks.py" in spec)
chk("T3  Appendix A present",           "Appendix A" in spec)
chk("T3  DD-10 false-positive guard",   "DD-10" in spec)

# T4 ── commander-architecture-v2.md
chk("T4  v2 file exists",               os.path.exists("docs/agent-system/commander-architecture-v2.md"))
chk("T4  Forensic Partnership section", "Forensic Partnership" in v2)
chk("T4  P-LOAD Definition",            "P-LOAD Definition" in v2)
chk("T4  Lestrade documented",          "Lestrade" in v2)
chk("T4  Oracle Shortcoming Loop",      "Oracle Shortcoming Loop" in v2)
chk("T4  DD-10 present",                "DD-10" in v2)
chk("T4  DD-11 present",                "DD-11" in v2)
chk("T4  Implemented vs Deferred",      "Implemented vs Deferred" in v2)
chk("T4  9-step cognitive loop",        "BLIND SPAWN" in v2)
chk("T4  v1 archived intact",           os.path.exists("docs/agent-system/commander-architecture.md"))

print()
fails = [l for l, ok in results if not ok]
if fails:
    print(f"RED  — {len(fails)} failures: {fails}")
    sys.exit(1)
else:
    print(f"GREEN — all {len(results)} checks passed")
