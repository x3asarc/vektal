"""
task-observer — Success Criteria Verification
Tests:
  T1  AgentDef exists: level=2, color=cyan, has_canonical_spec
  T2  LEVEL_UNDER -> commander
  T3  No SPAWNS children (task-observer doesn't delegate)
  T4  Reachable from Commander in 1 hop
  T5  TaskExecution nodes queryable (may be 0 — schema must exist)
  T6  ImprovementProposal schema: can write + read a test node
  T7  SkillDef.quality_score and trigger_count properties exist on nodes
  T8  Canonical spec exists with 6-part structure
  T9  Wrapper: TaskExecution load query documented
  T10 Wrapper: ImprovementProposal write documented
  T11 Wrapper: SkillDef.quality_score update documented
  T12 Wrapper: significance threshold / pattern detection logic
  T13 Wrapper: input/output contracts present
"""
import os, sys, uuid
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
    to = s.run("MATCH (a:AgentDef {name:'task-observer'}) RETURN a.level, a.color, a.has_canonical_spec").single()
    check("T1a level=2",    to["a.level"] if to else None,              2)
    check("T1b color=cyan", to["a.color"] if to else None,              "cyan")
    check("T1c has_spec",   to["a.has_canonical_spec"] if to else None, True)

    print("\n=== T2: LEVEL_UNDER -> commander ===")
    lu = s.run("MATCH (:AgentDef {name:'task-observer'})-[:LEVEL_UNDER]->(c) RETURN c.name").single()
    check("T2 reports to commander", lu["c.name"] if lu else None, "commander")

    print("\n=== T3: No SPAWNS children ===")
    spawned = s.run("MATCH (:AgentDef {name:'task-observer'})-[:SPAWNS]->(b) RETURN count(b) as c").single()["c"]
    check("T3 no spawns (pure reader/writer)", spawned, 0)

    print("\n=== T4: Reachable from Commander ===")
    reach = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef {name:'task-observer'}) RETURN 1 as ok").single()
    check("T4 CMD->task-observer 1 hop", bool(reach), True)

    print("\n=== T5: TaskExecution schema ===")
    te_count = s.run("MATCH (te:TaskExecution) RETURN count(te) as c").single()["c"]
    check("T5 TaskExecution queryable (may be 0)", te_count, lambda c: c >= 0)
    # Verify schema by writing + reading a test node
    test_id = f"test-{uuid.uuid4().hex[:8]}"
    s.run("""
        MERGE (te:TaskExecution {task_id: $tid})
        SET te.task_type='test', te.lead_invoked='test', te.quality_gate_passed=true,
            te.loop_count=1, te.skills_used=['test'], te.model_used='test',
            te.created_at='2026-01-01T00:00:00+00:00', te.status='test'
    """, tid=test_id)
    back = s.run("MATCH (te:TaskExecution {task_id: $tid}) RETURN te.quality_gate_passed as qgp", tid=test_id).single()
    check("T5 TaskExecution write+read roundtrip", back["qgp"] if back else None, True)
    # Cleanup
    s.run("MATCH (te:TaskExecution {task_id: $tid}) DELETE te", tid=test_id)

    print("\n=== T6: ImprovementProposal schema ===")
    test_ip_id = f"ip-test-{uuid.uuid4().hex[:8]}"
    s.run("""
        MERGE (ip:ImprovementProposal {proposal_id: $pid})
        SET ip.title='Test proposal', ip.target_skill='test-skill',
            ip.status='pending', ip.evidence='test', ip.created_at='2026-01-01T00:00:00+00:00'
    """, pid=test_ip_id)
    ip_back = s.run("MATCH (ip:ImprovementProposal {proposal_id: $pid}) RETURN ip.status as st", pid=test_ip_id).single()
    check("T6 ImprovementProposal write+read", ip_back["st"] if ip_back else None, "pending")
    # Cleanup
    s.run("MATCH (ip:ImprovementProposal {proposal_id: $pid}) DELETE ip", pid=test_ip_id)

    print("\n=== T7: SkillDef quality_score + trigger_count ===")
    sk_with_props = s.run("""
        MATCH (sk:SkillDef)
        WHERE sk.quality_score IS NOT NULL OR sk.trigger_count IS NOT NULL
        RETURN count(sk) as c
    """).single()["c"]
    check("T7 SkillDef has quality_score/trigger_count", sk_with_props, lambda c: c > 0)
    # Verify we can update a score
    s.run("MATCH (sk:SkillDef {name:'pico-warden'}) SET sk.trigger_count = coalesce(sk.trigger_count, 0) + 0")
    tw = s.run("MATCH (sk:SkillDef {name:'pico-warden'}) RETURN sk.trigger_count as tc").single()
    check("T7 pico-warden trigger_count updatable", tw["tc"] if tw else None, lambda t: t is not None)

    print("\n=== T8: Spec 6-part structure ===")
    spec_row = s.run("MATCH (a:AgentDef {name:'task-observer'}) RETURN a.canonical_spec_path").single()
    sp = spec_row["a.canonical_spec_path"] if spec_row else ""
    spec_file = PROJECT_ROOT / sp if sp else None
    check("T8a spec file exists", bool(spec_file and spec_file.exists()), True)
    if spec_file and spec_file.exists():
        txt = spec_file.read_text(encoding="utf-8", errors="replace")
        for part in ["Part I", "Part II", "Part III", "Part IV", "Part V", "Part VI"]:
            check(f"T8 spec {part}", part in txt, True)

    print("\n=== T9-T13: Wrapper content ===")
    wrapper = PROJECT_ROOT / ".claude" / "agents" / "task-observer.md"
    if wrapper.exists():
        txt = wrapper.read_text(encoding="utf-8", errors="replace")
        check("T9  TaskExecution load query",    "TaskExecution" in txt,         True)
        check("T10 ImprovementProposal write",   "ImprovementProposal" in txt,   True)
        check("T11 quality_score update",        "quality_score" in txt,         True)
        check("T12 pattern detection threshold", "threshold" in txt.lower() or "signific" in txt.lower(), True)
        check("T13 input contract",  all(k in txt for k in ["task", "intent", "quality_gate"]), True)
        check("T13 output contract", all(k in txt for k in ["quality_gate_passed", "loop_count"]), True)
    else:
        print("  [SKIP] task-observer.md not yet built")

print(f"\n{'='*54}")
print(f"RESULT: {PASS} PASS  {FAIL} FAIL")
print(f"STATUS: {'GREEN' if FAIL == 0 else 'RED - ' + str(FAIL) + ' failures'}")
driver.close()
