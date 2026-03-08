"""
Forensic Query: AgentDef → SkillDef → Function → SentryIssue + LongTermPattern

Stage 1  — Find AgentDef for Forensic Investigator (fuzzy name match)
Stage 2  — List SkillDef nodes linked via USES_SKILL edge (or text fallback)
Stage 3  — Bridge SkillDef → Python Function via spec_path → File → DEFINES_FUNCTION
Stage 3b — Fallback: SkillDef spec_path → File node → Functions in that file
Stage 4  — SentryIssue check on implementation functions (OCCURRED_IN / REPORTED_IN)
Stage 5  — LongTermPattern for 'scraping-logic-stability': last recorded timestamp
Stage 6  — StartDate comparison: were impl functions updated AFTER last LTP entry?
"""

import os, sys, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()

uri  = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
pwd  = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, pwd))

SEP = "=" * 72

# ── Stage 1: Find the Forensic Investigator AgentDef ─────────────────────────
print(SEP)
print("STAGE 1: FIND AgentDef — 'Forensic Investigator'")
print(SEP)

with driver.session() as s:
    # Exact + fuzzy search
    agents = s.run("""
        MATCH (a:AgentDef)
        WHERE toLower(a.name) CONTAINS 'forensic'
           OR toLower(a.description) CONTAINS 'forensic'
           OR toLower(a.name) CONTAINS 'investigat'
        RETURN a.agent_id    AS id,
               a.name        AS name,
               a.platform    AS platform,
               a.spec_path   AS spec_path,
               a.description AS description,
               a.has_canonical_spec AS has_spec,
               a.canonical_spec_path AS canonical
        ORDER BY a.has_canonical_spec DESC
    """).data()

if not agents:
    print("  [RED] No AgentDef found matching 'forensic' or 'investigat'.")
    print("  Dumping all AgentDef names for triage:")
    with driver.session() as s:
        all_agents = s.run("MATCH (a:AgentDef) RETURN a.name, a.platform ORDER BY a.name").data()
    for r in all_agents:
        print(f"    {r['a.platform']:12s}  {r['a.name']}")
    driver.close()
    raise SystemExit("HALT: No forensic AgentDef found — cannot continue.")

print(f"  Found {len(agents)} match(es):")
for a in agents:
    print(f"\n  AgentDef: {a['name']}")
    print(f"    id:          {a['id']}")
    print(f"    platform:    {a['platform']}")
    print(f"    spec_path:   {a['spec_path']}")
    print(f"    canonical:   {a['canonical'] or 'none'}")
    print(f"    description: {a['description'][:120] if a['description'] else '(empty)'}")

primary_agent = agents[0]
agent_id = primary_agent["id"]
agent_name = primary_agent["name"]
spec_path = primary_agent.get("canonical") or primary_agent["spec_path"]

# ── Stage 2: SkillDef nodes linked via USES_SKILL ────────────────────────────
print()
print(SEP)
print("STAGE 2: SkillDef LINKED VIA USES_SKILL")
print(SEP)

with driver.session() as s:
    uses_skill = s.run("""
        MATCH (a:AgentDef {agent_id: $aid})-[:USES_SKILL]->(sk:SkillDef)
        RETURN sk.skill_id AS id, sk.name AS name, sk.platform AS platform,
               sk.skill_type AS type, sk.spec_path AS spec_path, sk.description AS description
    """, aid=agent_id).data()

if uses_skill:
    print(f"  USES_SKILL edges found: {len(uses_skill)}")
    for sk in uses_skill:
        print(f"    {sk['name']}  ({sk['platform']}/{sk['type']})  {sk['spec_path']}")
else:
    print("  [GAP] No USES_SKILL edges exist for this agent.")
    print("  USES_SKILL edge creation was not implemented in sync_orchestration.py (schema stub).")
    print("  Falling back: text-matching skill names from agent spec content.")
    print()

    # Read spec file to find mentioned skills
    from pathlib import Path
    PROJECT = Path(__file__).resolve().parents[2]
    spec_file = PROJECT / spec_path if spec_path else None
    mentioned_skills = []
    if spec_file and spec_file.exists():
        spec_text = spec_file.read_text(encoding="utf-8", errors="replace").lower()
        with driver.session() as s:
            all_skills = s.run("MATCH (sk:SkillDef) RETURN sk.skill_id AS id, sk.name AS name, sk.spec_path AS sp, sk.description AS desc").data()
        for sk in all_skills:
            if sk["name"].lower() in spec_text or (sk["desc"] or "").lower()[:60] in spec_text:
                mentioned_skills.append(sk)
                print(f"  [TEXT-MATCH] {sk['name']} mentioned in spec")

    if not mentioned_skills:
        print("  No skills text-matched. Dumping all SkillDef nodes:")
        with driver.session() as s:
            all_skills = s.run("MATCH (sk:SkillDef) RETURN sk.skill_id AS id, sk.name AS name, sk.platform AS platform, sk.spec_path AS sp, sk.description AS desc").data()
        for sk in all_skills:
            print(f"    [{sk['platform']}] {sk['name']}  →  {sk['sp']}")
        print()
        print("  Using ALL SkillDef nodes as candidates (forensic agent may use any skill).")
        mentioned_skills = all_skills

    uses_skill = mentioned_skills

# ── Stage 3: Bridge SkillDef → Python Function via spec_path ─────────────────
print()
print(SEP)
print("STAGE 3: SkillDef -> Implementation Functions")
print(SEP)

from pathlib import Path
PROJECT = Path(__file__).resolve().parents[2]

skill_functions = {}   # skill_name → list of function dicts

with driver.session() as s:
    for sk in uses_skill:
        skill_name = sk["name"]
        sp = sk.get("spec_path") or sk.get("sp") or ""
        print(f"\n  Skill: {skill_name}  ({sp})")

        # Try direct graph link first: SkillDef → Function via IMPLEMENTS
        direct = s.run("""
            MATCH (sk:SkillDef {skill_id: $sid})-[:IMPLEMENTS]->(f:Function)
            WHERE f.EndDate IS NULL
            RETURN f.function_signature AS sig, f.file_path AS fp, f.StartDate AS sd
        """, sid=sk.get("id") or sk.get("skill_id") or "").data()

        if direct:
            print(f"    [DIRECT LINK] {len(direct)} Function(s) via IMPLEMENTS edge")
            skill_functions[skill_name] = direct
            for f in direct:
                print(f"      {f['sig']}  (StartDate: {str(f['sd'])[:20] if f['sd'] else 'N/A'})")
            continue

        # Fallback 1: find File node matching spec_path, then get Functions in that file
        # Normalize skill spec_path to find associated Python files
        skill_dir = str(Path(sp).parent).replace("\\", "/") if sp else ""
        skill_file_stem = Path(sp).stem if sp else ""

        # Look for Python files in the same directory or with related names
        file_matches = s.run("""
            MATCH (f:File)
            WHERE f.EndDate IS NULL
              AND (f.path CONTAINS $stem
                   OR f.path CONTAINS $dir)
              AND f.path ENDS WITH '.py'
            RETURN f.path AS path LIMIT 5
        """, stem=skill_file_stem, dir=skill_dir if skill_dir != "." else "NOMATCH").data()

        impl_functions = []
        for fm in file_matches:
            fpath = fm["path"]
            fns = s.run("""
                MATCH (fn:Function {file_path: $fp})
                WHERE fn.EndDate IS NULL
                RETURN fn.function_signature AS sig,
                       fn.file_path AS fp,
                       fn.StartDate AS sd,
                       fn.name AS name
                ORDER BY fn.name
                LIMIT 10
            """, fp=fpath).data()
            impl_functions.extend(fns)
            if fns:
                print(f"    [FILE MATCH] {fpath} → {len(fns)} function(s)")
                for fn in fns[:3]:
                    print(f"      {fn['sig']}  (StartDate: {str(fn['sd'])[:20] if fn['sd'] else 'N/A'})")
                if len(fns) > 3:
                    print(f"      ... and {len(fns)-3} more")

        if not impl_functions:
            # Fallback 2: name-based heuristic — look for functions mentioning skill name
            name_parts = skill_name.replace("-", "_").replace(" ", "_").lower().split("_")
            search_term = name_parts[0] if name_parts else skill_name
            heuristic = s.run("""
                MATCH (fn:Function)
                WHERE fn.EndDate IS NULL
                  AND (toLower(fn.name) CONTAINS $term
                       OR toLower(fn.file_path) CONTAINS $term)
                RETURN fn.function_signature AS sig, fn.file_path AS fp, fn.StartDate AS sd
                LIMIT 5
            """, term=search_term).data()
            impl_functions.extend(heuristic)
            if heuristic:
                print(f"    [NAME HEURISTIC '{search_term}'] {len(heuristic)} function(s)")
                for fn in heuristic:
                    print(f"      {fn['sig']}")
            else:
                print(f"    [NO MATCH] No implementation functions found for {skill_name}")

        skill_functions[skill_name] = impl_functions

# ── Stage 4: Sentry check on implementation functions ────────────────────────
print()
print(SEP)
print("STAGE 4: SENTRY ISSUES ON IMPLEMENTATION FUNCTIONS")
print(SEP)

all_impl_sigs = list({fn["sig"] for fns in skill_functions.values() for fn in fns})
print(f"  Implementation functions under investigation: {len(all_impl_sigs)}")

with driver.session() as s:
    sentry_hits = s.run("""
        MATCH (si:SentryIssue)-[:OCCURRED_IN|REPORTED_IN]->(target)
        WHERE si.resolved = false
          AND (target.function_signature IN $sigs
               OR ANY(sig IN $sigs WHERE target.path CONTAINS
                      replace(split(sig, '.')[0] + '.' + split(sig, '.')[1], '.', '/')))
        RETURN si.issue_id   AS issue_id,
               si.title      AS title,
               si.category   AS category,
               si.culprit    AS culprit,
               si.timestamp  AS ts,
               type(head([(si)-[r]->(t) | r])) AS link_type
        ORDER BY si.timestamp DESC
    """, sigs=all_impl_sigs).data()

    total_sentry = s.run("MATCH (si:SentryIssue) RETURN count(si) as c").single()["c"]

if sentry_hits:
    print(f"  UNRESOLVED Sentry issues touching impl functions: {len(sentry_hits)}")
    for r in sentry_hits:
        print(f"\n    [{r['category']}] {r['issue_id']}")
        print(f"    Title:   {r['title']}")
        print(f"    Culprit: {r['culprit']}")
        print(f"    Link:    {r['link_type']}")
else:
    print(f"  No unresolved Sentry issues linked to implementation functions.")
    print(f"  (Total SentryIssue nodes in graph: {total_sentry} — all are test/mock data)")

# ── Stage 5: LongTermPattern for 'scraping-logic-stability' ──────────────────
print()
print(SEP)
print("STAGE 5: LongTermPattern — 'scraping-logic-stability'")
print(SEP)

with driver.session() as s:
    # Exact domain
    ltp_exact = s.run("""
        MATCH (lp:LongTermPattern)
        WHERE lp.domain = 'scraping-logic-stability'
           OR lp.task_id CONTAINS 'scraping'
           OR toLower(lp.description) CONTAINS 'scraping'
        RETURN lp.pattern_id AS id, lp.domain AS domain,
               lp.task_id AS task_id, lp.description AS desc,
               lp.StartDate AS recorded_at, lp.source AS source
        ORDER BY lp.StartDate DESC
    """).data()

    # Also dump all domains for situational awareness
    all_domains = s.run("""
        MATCH (lp:LongTermPattern)
        RETURN DISTINCT lp.domain AS domain, count(lp) AS c
        ORDER BY lp.domain
    """).data()

ltp_scraping = ltp_exact
last_ltp_date = None

if ltp_scraping:
    print(f"  Found {len(ltp_scraping)} pattern(s) for scraping-logic-stability:")
    for lp in ltp_scraping:
        print(f"\n    [{lp['domain']}] {lp['task_id']}")
        print(f"    Recorded:    {lp['recorded_at']}")
        print(f"    Source:      {lp['source']}")
        print(f"    Description: {lp['desc'][:200] if lp['desc'] else '(empty)'}")
    last_ltp_date = ltp_scraping[0]["recorded_at"]
else:
    print("  [GAP] No LongTermPattern with domain='scraping-logic-stability' found.")
    print()
    print("  All domains currently in graph:")
    for d in all_domains:
        print(f"    {d['domain']:30s}  ({d['c']} entries)")
    print()
    print("  Using most recent LongTermPattern (any domain) as temporal anchor:")
    with driver.session() as s:
        most_recent = s.run("""
            MATCH (lp:LongTermPattern)
            WHERE lp.StartDate IS NOT NULL
            RETURN lp.pattern_id AS id, lp.domain AS domain,
                   lp.task_id AS task_id, lp.StartDate AS recorded_at,
                   lp.description AS desc
            ORDER BY lp.StartDate DESC LIMIT 3
        """).data()
    for lp in most_recent:
        print(f"    [{lp['domain']}] {lp['task_id']}  at {lp['recorded_at']}")
    if most_recent:
        last_ltp_date = most_recent[0]["recorded_at"]

# ── Stage 6: Were impl functions updated AFTER last LTP entry? ───────────────
print()
print(SEP)
print("STAGE 6: FUNCTION DRIFT — Updated AFTER last LongTermPattern recorded")
print(SEP)

if not last_ltp_date:
    print("  [SKIP] No temporal anchor (LTP date) available.")
else:
    print(f"  Temporal anchor: {last_ltp_date}")
    print()

    with driver.session() as s:
        drifted = s.run("""
            MATCH (fn:Function)
            WHERE fn.EndDate IS NULL
              AND fn.function_signature IN $sigs
              AND fn.StartDate > $anchor
            RETURN fn.function_signature AS sig,
                   fn.StartDate          AS updated_at,
                   fn.file_path          AS file,
                   fn.checksum           AS checksum
            ORDER BY fn.StartDate DESC
        """, sigs=all_impl_sigs, anchor=str(last_ltp_date)).data()

        stable = s.run("""
            MATCH (fn:Function)
            WHERE fn.EndDate IS NULL
              AND fn.function_signature IN $sigs
              AND (fn.StartDate IS NULL OR fn.StartDate <= $anchor)
            RETURN fn.function_signature AS sig,
                   fn.StartDate          AS updated_at
            ORDER BY fn.StartDate DESC
        """, sigs=all_impl_sigs, anchor=str(last_ltp_date)).data()

    if drifted:
        print(f"  DRIFTED (updated after LTP anchor): {len(drifted)}")
        for r in drifted:
            print(f"    [DRIFT] {r['sig']}")
            print(f"            updated: {r['updated_at']}  checksum: {r['checksum']}")
    else:
        print(f"  No implementation functions were updated after LTP anchor.")

    print()
    print(f"  STABLE (unchanged since LTP anchor): {len(stable)}")
    for r in stable[:5]:
        print(f"    [OK] {r['sig']}  (StartDate: {r['updated_at']})")
    if len(stable) > 5:
        print(f"    ... and {len(stable)-5} more stable")

print()
print(SEP)
print("END")
print(SEP)

driver.close()
