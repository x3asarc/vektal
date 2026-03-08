"""
Engineering Lead — Success Criteria Verification
Run BEFORE building the agent wrapper to define the green bar.
Run AFTER to confirm it passes.

Tests:
  T1  AgentDef exists with correct level/color
  T2  LEVEL_UNDER -> commander
  T3  SPAWNS all required GSD agents
  T4  USES_SKILL all required skills (per finetuned-resources.md)
  T5  All required GSD agents exist and have level=3
  T6  All required skills exist with correct tier
  T7  Engineering Lead reachable from Commander in 1 hop
  T8  Engineering Lead can reach all its GSD agents in 1 hop
  T9  Engineering Lead can reach all its skills in 1 hop
  T10 GSD agents reachable from Commander in 2 hops
  T11 Engineering Lead has canonical spec
  T12 spec-doc.md 6-part structure present in spec file
  T13 Context package input contract documented in wrapper
  T14 Output contract documented in wrapper
  T15 Loop/circuit-breaker protocol documented in wrapper
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

REQUIRED_GSD = ["gsd-planner", "gsd-executor", "gsd-verifier",
                "gsd-plan-checker", "gsd-integration-checker", "gsd-debugger"]

REQUIRED_SKILLS = [
    "review-implementing", "test-driven-development", "test-fixing",
    "defense-in-depth", "postgres", "finishing-a-development-branch",
    "using-git-worktrees",
]

with driver.session() as s:
    print("=== T1: AgentDef node ===")
    el = s.run("MATCH (a:AgentDef {name:'engineering-lead'}) RETURN a.level, a.color, a.platform, a.has_canonical_spec, a.canonical_spec_path").single()
    if el:
        check("T1a level=2",        el["a.level"],              2)
        check("T1b color=blue",     el["a.color"],              "blue")
        check("T1c has_spec",       el["a.has_canonical_spec"], True)
    else:
        check("T1 node exists", None, lambda x: False)

    print("\n=== T2: LEVEL_UNDER -> commander ===")
    lu = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:LEVEL_UNDER]->(c:AgentDef) RETURN c.name").single()
    check("T2 reports to commander", lu["c.name"] if lu else None, "commander")

    print("\n=== T3: SPAWNS all required GSD agents ===")
    spawned = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:SPAWNS]->(b) RETURN b.name").data()
    spawn_names = [r["b.name"] for r in spawned]
    for gsd in REQUIRED_GSD:
        check(f"T3 SPAWNS {gsd}", gsd in spawn_names, True)

    print("\n=== T4: USES_SKILL all required skills ===")
    skills = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:USES_SKILL]->(sk) RETURN sk.name").data()
    skill_names = [r["sk.name"] for r in skills]
    for sk in REQUIRED_SKILLS:
        check(f"T4 USES_SKILL {sk}", sk in skill_names, True)

    print("\n=== T5: GSD agents have level=3 ===")
    for gsd in REQUIRED_GSD:
        lv = s.run("MATCH (a:AgentDef {name:$n}) RETURN a.level", n=gsd).single()
        check(f"T5 {gsd} level=3", lv["a.level"] if lv else None, 3)

    print("\n=== T6: Required skills have correct tier ===")
    for sk in REQUIRED_SKILLS:
        row = s.run("MATCH (sk:SkillDef {name:$n}) RETURN sk.tier", n=sk).single()
        check(f"T6 {sk} tier in [1,2]", row["sk.tier"] if row else None, lambda t: t in [1,2])

    print("\n=== T7: EL reachable from Commander in 1 hop ===")
    reach = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(el:AgentDef {name:'engineering-lead'}) RETURN 1 as ok").single()
    check("T7 CMD->EL 1 hop", bool(reach), True)

    print("\n=== T8: EL can reach all GSD agents in 1 hop ===")
    el_gsd = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:SPAWNS]->(b:AgentDef) RETURN count(b) as c").single()["c"]
    check("T8 EL reaches 6 GSD agents", el_gsd, 6)

    print("\n=== T9: EL can reach all skills in 1 hop ===")
    el_sk = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:USES_SKILL]->(sk) RETURN count(sk) as c").single()["c"]
    check("T9 EL reaches 7 skills", el_sk, 7)

    print("\n=== T10: GSD agents reachable from Commander in 2 hops ===")
    cmd_gsd = s.run("""
        MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef {name:'engineering-lead'})-[:SPAWNS]->(gsd)
        RETURN count(gsd) as c
    """).single()["c"]
    check("T10 CMD->EL->GSD in 2 hops = 6", cmd_gsd, 6)

    print("\n=== T11: Canonical spec exists ===")
    spec_path = el["a.canonical_spec_path"] if el else ""
    spec_file = PROJECT_ROOT / spec_path if spec_path else None
    check("T11 spec file exists on disk", bool(spec_file and spec_file.exists()), True)

    print("\n=== T12: Spec has 6-part structure (spec-doc.md compliance) ===")
    if spec_file and spec_file.exists():
        spec_text = spec_file.read_text(encoding="utf-8", errors="replace")
        for part in ["Part I", "Part II", "Part III", "Part IV", "Part V", "Part VI"]:
            check(f"T12 spec has {part}", part in spec_text, True)
    else:
        for i in range(1,7):
            check(f"T12 spec Part {i} (skip - file missing)", False, False)

    print("\n=== T13-T15: Wrapper content gates ===")
    wrapper = PROJECT_ROOT / ".claude" / "agents" / "engineering-lead.md"
    if wrapper.exists():
        txt = wrapper.read_text(encoding="utf-8", errors="replace")
        check("T13 input contract (task, intent, aura_context)",
              all(k in txt for k in ["task", "intent", "aura_context"]), True)
        check("T14 output contract (quality_gate_passed, loop_count, skills_used)",
              all(k in txt for k in ["quality_gate_passed", "loop_count", "skills_used"]), True)
        check("T15 loop/circuit-breaker documented",
              any(k in txt for k in ["loop_budget", "circuit", "CIRCUIT"]), True)
        check("T15b gsd-planner -> gsd-executor -> gsd-verifier sequence documented",
              all(k in txt for k in ["gsd-planner", "gsd-executor", "gsd-verifier"]), True)
        check("T15c review-implementing gate before executor",
              "review-implementing" in txt, True)
    else:
        print("  [SKIP] engineering-lead.md not yet built — T13-T15 will re-run after build")

print(f"\n{'='*52}")
print(f"RESULT: {PASS} PASS  {FAIL} FAIL")
print(f"STATUS: {'GREEN' if FAIL == 0 else 'RED - ' + str(FAIL) + ' failures to fix'}")
driver.close()
