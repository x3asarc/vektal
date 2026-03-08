"""Verify Commander node + all edges are correct in Aura."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()

driver = GraphDatabase.driver(os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME","neo4j"), os.getenv("NEO4J_PASSWORD")))

PASS, FAIL = 0, 0

def check(label, result, expect):
    global PASS, FAIL
    ok = result == expect if not callable(expect) else expect(result)
    status = "PASS" if ok else "FAIL"
    if ok: PASS += 1
    else:  FAIL += 1
    exp_str = repr(expect) if not callable(expect) else "<fn>"
    print(f"  [{status}] {label}  got={result!r}  expect={exp_str}")

with driver.session() as s:
    print("=== Commander node ===")
    cmd = s.run("MATCH (a:AgentDef {name:'commander'}) RETURN a.level, a.color, a.platform, a.has_canonical_spec").single()
    check("level=1",           cmd["a.level"],              1)
    check("color=gold",        cmd["a.color"],              "gold")
    check("has_canonical_spec",cmd["a.has_canonical_spec"], True)

    print("\n=== SPAWNS edges (Commander -> Leads) ===")
    spawned = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(b:AgentDef) RETURN b.name ORDER BY b.name").data()
    names   = [r["b.name"] for r in spawned]
    for expected in ["engineering-lead","design-lead","forensic-lead","infrastructure-lead","project-lead","task-observer"]:
        check(f"SPAWNS {expected}", expected in names, True)

    print("\n=== LEVEL_UNDER (Leads report to Commander) ===")
    under = s.run("MATCH (b:AgentDef)-[:LEVEL_UNDER]->(:AgentDef {name:'commander'}) RETURN b.name").data()
    under_names = [r["b.name"] for r in under]
    check("count=6", len(under_names), 6)

    print("\n=== Engineering Lead hierarchy ===")
    el_spawns = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:SPAWNS]->(b) RETURN b.name").data()
    el_names  = [r["b.name"] for r in el_spawns]
    for gsd in ["gsd-planner","gsd-executor","gsd-verifier"]:
        check(f"EL SPAWNS {gsd}", gsd in el_names, True)

    print("\n=== USES_SKILL (Commander) ===")
    cmd_skills = s.run("MATCH (:AgentDef {name:'commander'})-[:USES_SKILL]->(sk) RETURN sk.name, sk.tier").data()
    cmd_skill_names = [r["sk.name"] for r in cmd_skills]
    for sk in ["brainstorming","find-skills","deep-research"]:
        check(f"CMD uses {sk}", sk in cmd_skill_names, True)

    print("\n=== USES_SKILL (Engineering Lead) ===")
    el_skills = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:USES_SKILL]->(sk) RETURN sk.name, sk.tier").data()
    el_skill_names = [r["sk.name"] for r in el_skills]
    for sk in ["review-implementing","test-driven-development","defense-in-depth"]:
        check(f"EL uses {sk}", sk in el_skill_names, True)

    print("\n=== USES_SKILL (Forensic Lead) ===")
    fl_skills = s.run("MATCH (:AgentDef {name:'forensic-lead'})-[:USES_SKILL]->(sk) RETURN sk.name").data()
    fl_skill_names = [r["sk.name"] for r in fl_skills]
    for sk in ["systematic-debugging","root-cause-tracing","tri-agent-bug-audit","pico-warden"]:
        check(f"FL uses {sk}", sk in fl_skill_names, True)

    print("\n=== SkillDef schema richness ===")
    sk_sample = s.run("MATCH (sk:SkillDef) WHERE sk.tier IS NOT NULL RETURN count(sk) as c").single()["c"]
    check("all skills have tier", sk_sample, lambda c: c >= 23)
    ext_stub = s.run("MATCH (sk:SkillDef {name:'dev-browser'}) RETURN sk.tier, sk.source_url, sk.installed_at").single()
    if ext_stub:
        check("dev-browser tier=1",           ext_stub["sk.tier"],         1)
        check("dev-browser installed_at=[]",  ext_stub["sk.installed_at"], [])
    else:
        check("dev-browser exists", False, True)

    print("\n=== HookDef nodes ===")
    hooks = s.run("MATCH (h:HookDef) RETURN h.event, h.script, h.blocking ORDER BY h.event, h.script").data()
    check("8 hooks total", len(hooks), 8)
    blocking = [h for h in hooks if h["h.blocking"]]
    check("1 blocking hook (risk_tier_gate)", len(blocking), 1)
    check("blocking = risk_tier_gate", "risk_tier_gate" in blocking[0]["h.script"], True)

    print("\n=== IMPLEMENTS (pico-warden -> Functions) ===")
    impl = s.run("MATCH (:SkillDef {name:'pico-warden'})-[:IMPLEMENTS]->(f:Function) RETURN count(f) as c").single()["c"]
    check("pico-warden implements 11 functions", impl, 11)

    print("\n=== Stress: full Commander capability surface ===")
    # Commander should be able to reach every lead via one hop, every skill via two hops
    reachable_leads = s.run("""
        MATCH (cmd:AgentDef {name:'commander'})-[:SPAWNS]->(lead:AgentDef)
        RETURN count(DISTINCT lead) as c
    """).single()["c"]
    check("Commander reaches 6 leads in 1 hop", reachable_leads, 6)

    reachable_skills = s.run("""
        MATCH (cmd:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef)-[:USES_SKILL]->(sk:SkillDef)
        RETURN count(DISTINCT sk) as c
    """).single()["c"]
    check("Commander reaches Lead skills in 2 hops", reachable_skills, lambda c: c > 10)

    reachable_fns = s.run("""
        MATCH (cmd:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef)-[:USES_SKILL]->(:SkillDef)-[:IMPLEMENTS]->(f:Function)
        RETURN count(DISTINCT f) as c
    """).single()["c"]
    check("Commander reaches impl functions in 3 hops", reachable_fns, 11)

print(f"\n{'='*50}")
print(f"RESULT: {PASS} PASS  {FAIL} FAIL")
print(f"STATUS: {'GREEN' if FAIL == 0 else 'RED'}")
driver.close()
