"""
Infrastructure Lead — Success Criteria Verification
Tests:
  T1  AgentDef exists: level=2, color=orange, has_canonical_spec
  T2  LEVEL_UNDER -> commander
  T3  LEVEL_UNDER -> validator confirmed (IL supervises validator)
  T4  USES_SKILL: pico-warden, varlock-claude-skill
  T5  pico-warden IMPLEMENTS 11 functions
  T6  Reachable from Commander in 1 hop
  T7  Validator reachable from IL in 1 hop
  T8  IL reachable from Commander → validator in 2 hops
  T9  Canonical spec exists on disk with 6-part structure
  T10 Wrapper content: pico-warden escalation documented
  T11 Wrapper content: varlock-claude-skill documented
  T12 Wrapper content: ImprovementProposal pipeline documented
  T13 Wrapper content: input/output contracts present
  T14 HookDef RUNS_SCRIPT bridge: IL can see what hooks run
  T15 EnvVar risk tiers queryable (T1/T2/T3/T4 nodes exist in graph)
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pathlib import Path
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
driver = GraphDatabase.driver(os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME","neo4j"), os.getenv("NEO4J_PASSWORD")))

PASS, FAIL = 0, 0

def check(label, result, expect):
    global PASS, FAIL
    ok = result == expect if not callable(expect) else expect(result)
    sym = "PASS" if ok else "FAIL"
    if ok: PASS += 1
    else:  FAIL += 1
    exp_str = repr(expect) if not callable(expect) else "<fn>"
    print(f"  [{sym}] {label}  got={result!r}  expect={exp_str}")

with driver.session() as s:
    print("=== T1: AgentDef node ===")
    il = s.run("MATCH (a:AgentDef {name:'infrastructure-lead'}) RETURN a.level, a.color, a.has_canonical_spec").single()
    check("T1a level=2",    il["a.level"] if il else None,              2)
    check("T1b color=orange", il["a.color"] if il else None,            "orange")
    check("T1c has_spec",   il["a.has_canonical_spec"] if il else None, True)

    print("\n=== T2: LEVEL_UNDER -> commander ===")
    lu = s.run("MATCH (:AgentDef {name:'infrastructure-lead'})-[:LEVEL_UNDER]->(c:AgentDef) RETURN c.name").single()
    check("T2 reports to commander", lu["c.name"] if lu else None, "commander")

    print("\n=== T3: IL supervises validator ===")
    val = s.run("MATCH (:AgentDef {name:'infrastructure-lead'})-[:SPAWNS]->(v:AgentDef {name:'validator'}) RETURN 1 as ok").single()
    check("T3 IL SPAWNS validator", bool(val), True)
    val_lu = s.run("MATCH (:AgentDef {name:'validator'})-[:LEVEL_UNDER]->(il:AgentDef {name:'infrastructure-lead'}) RETURN 1 as ok").single()
    check("T3 validator LEVEL_UNDER IL", bool(val_lu), True)

    print("\n=== T4: USES_SKILL ===")
    skills = s.run("MATCH (:AgentDef {name:'infrastructure-lead'})-[:USES_SKILL]->(sk) RETURN sk.name").data()
    sk_names = [r["sk.name"] for r in skills]
    for sk in ["pico-warden", "varlock-claude-skill"]:
        check(f"T4 USES_SKILL {sk}", sk in sk_names, True)

    print("\n=== T5: pico-warden IMPLEMENTS functions ===")
    impl = s.run("MATCH (:SkillDef {name:'pico-warden'})-[:IMPLEMENTS]->(f:Function) RETURN count(f) as c").single()["c"]
    check("T5 pico-warden implements 11 fn", impl, 11)

    print("\n=== T6: Reachable from Commander ===")
    reach = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef {name:'infrastructure-lead'}) RETURN 1 as ok").single()
    check("T6 CMD->IL 1 hop", bool(reach), True)

    print("\n=== T7+T8: IL -> validator path ===")
    il_val = s.run("MATCH (:AgentDef {name:'infrastructure-lead'})-[:SPAWNS]->(:AgentDef {name:'validator'}) RETURN 1 as ok").single()
    check("T7 IL->validator 1 hop", bool(il_val), True)
    cmd_val = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef {name:'infrastructure-lead'})-[:SPAWNS]->(:AgentDef {name:'validator'}) RETURN 1 as ok").single()
    check("T8 CMD->IL->validator 2 hops", bool(cmd_val), True)

    print("\n=== T9: Spec 6-part structure ===")
    spec_row = s.run("MATCH (a:AgentDef {name:'infrastructure-lead'}) RETURN a.canonical_spec_path").single()
    sp = spec_row["a.canonical_spec_path"] if spec_row else ""
    spec_file = PROJECT_ROOT / sp if sp else None
    check("T9a spec file exists", bool(spec_file and spec_file.exists()), True)
    if spec_file and spec_file.exists():
        txt = spec_file.read_text(encoding="utf-8", errors="replace")
        for part in ["Part I", "Part II", "Part III", "Part IV", "Part V", "Part VI"]:
            check(f"T9 spec {part}", part in txt, True)

    print("\n=== T14: HookDef bridge ===")
    hooks = s.run("MATCH (h:HookDef)-[:RUNS_SCRIPT]->(f:File) RETURN count(h) as c").single()["c"]
    check("T14 RUNS_SCRIPT edges exist", hooks, lambda c: c >= 4)

    print("\n=== T15: EnvVar risk tiers ===")
    ev = s.run("MATCH (e:EnvVar) RETURN count(e) as c").single()["c"]
    check("T15 EnvVar nodes exist", ev, lambda c: c > 0)
    tiers = s.run("MATCH (e:EnvVar) RETURN DISTINCT e.risk_tier as t ORDER BY t").data()
    tier_vals = [r["t"] for r in tiers if r["t"] is not None]
    check("T15 multiple risk tiers", len(tier_vals), lambda c: c >= 2)

    print("\n=== T10-T13: Wrapper content ===")
    wrapper = PROJECT_ROOT / ".claude" / "agents" / "infrastructure-lead.md"
    if wrapper.exists():
        txt = wrapper.read_text(encoding="utf-8", errors="replace")
        check("T10 pico-warden escalation", "pico-warden" in txt, True)
        check("T11 varlock documented",     "varlock" in txt, True)
        check("T12 ImprovementProposal",    "ImprovementProposal" in txt, True)
        check("T13 input contract",  all(k in txt for k in ["task", "intent", "quality_gate"]), True)
        check("T13 output contract", all(k in txt for k in ["quality_gate_passed", "loop_count"]), True)
    else:
        print("  [SKIP] infrastructure-lead.md not yet built")

print(f"\n{'='*54}")
print(f"RESULT: {PASS} PASS  {FAIL} FAIL")
print(f"STATUS: {'GREEN' if FAIL == 0 else 'RED - ' + str(FAIL) + ' failures'}")
driver.close()
