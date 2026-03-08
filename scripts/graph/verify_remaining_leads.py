"""
Validator + Design Lead + Project Lead + Forensic Lead wrapper — Verification
Tests per agent:
  - AgentDef: level, color, has_canonical_spec
  - LEVEL_UNDER correct parent
  - SPAWNS correct children
  - USES_SKILL correct skills
  - Reachable from Commander
  - Spec 6-part structure
  - Wrapper content gates (if built)
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

TOTAL_PASS, TOTAL_FAIL = 0, 0

def check(label, result, expect):
    global TOTAL_PASS, TOTAL_FAIL
    ok = result == expect if not callable(expect) else expect(result)
    sym = "PASS" if ok else "FAIL"
    if ok: TOTAL_PASS += 1
    else:  TOTAL_FAIL += 1
    exp_str = repr(expect) if not callable(expect) else "<fn>"
    print(f"  [{sym}] {label}  got={result!r}  expect={exp_str}")

def wrapper_check(name, keys_required):
    w = PROJECT_ROOT / ".claude" / "agents" / f"{name}.md"
    if not w.exists():
        print(f"  [SKIP] {name}.md not yet built")
        return
    txt = w.read_text(encoding="utf-8", errors="replace")
    for key, desc in keys_required:
        check(f"wrapper {name}: {desc}", key(txt) if callable(key) else key in txt, True)

with driver.session() as s:

    # ── VALIDATOR ──────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("VALIDATOR")
    print("="*60)
    v = s.run("MATCH (a:AgentDef {name:'validator'}) RETURN a.level, a.color, a.has_canonical_spec").single()
    check("level=2",    v["a.level"] if v else None,              2)
    check("color=green",v["a.color"] if v else None,              "green")
    check("has_spec",   v["a.has_canonical_spec"] if v else None, True)

    lu = s.run("MATCH (:AgentDef {name:'validator'})-[:LEVEL_UNDER]->(p) RETURN p.name").single()
    check("reports to infrastructure-lead", lu["p.name"] if lu else None, "infrastructure-lead")

    no_spawn = s.run("MATCH (:AgentDef {name:'validator'})-[:SPAWNS]->(b) RETURN count(b) as c").single()["c"]
    check("no spawns (pure verdicts)", no_spawn, 0)

    reach_il = s.run("MATCH (:AgentDef {name:'infrastructure-lead'})-[:SPAWNS]->(:AgentDef {name:'validator'}) RETURN 1 as ok").single()
    check("IL->validator 1 hop", bool(reach_il), True)

    reach_cmd = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS*2]->(:AgentDef {name:'validator'}) RETURN 1 as ok LIMIT 1").single()
    check("CMD->IL->validator 2 hops", bool(reach_cmd), True)

    spec_row = s.run("MATCH (a:AgentDef {name:'validator'}) RETURN a.canonical_spec_path").single()
    sp = spec_row["a.canonical_spec_path"] if spec_row else ""
    spec_file = PROJECT_ROOT / sp if sp else None
    check("spec file exists", bool(spec_file and spec_file.exists()), True)
    if spec_file and spec_file.exists():
        txt = spec_file.read_text(encoding="utf-8", errors="replace")
        for part in ["Part I","Part II","Part III","Part IV","Part V","Part VI"]:
            check(f"spec {part}", part in txt, True)

    wrapper_check("validator", [
        ("APPROVED", "APPROVED verdict"),
        ("REJECTED", "REJECTED verdict"),
        ("blast radius", "blast radius check"),
        ("ImprovementProposal", "ImprovementProposal"),
        ("quality_gate_passed", "output contract"),
    ])

    # ── DESIGN LEAD ────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("DESIGN LEAD")
    print("="*60)
    dl = s.run("MATCH (a:AgentDef {name:'design-lead'}) RETURN a.level, a.color, a.has_canonical_spec").single()
    check("level=2",     dl["a.level"] if dl else None,              2)
    check("color=purple",dl["a.color"] if dl else None,              "purple")
    check("has_spec",    dl["a.has_canonical_spec"] if dl else None, True)

    lu = s.run("MATCH (:AgentDef {name:'design-lead'})-[:LEVEL_UNDER]->(p) RETURN p.name").single()
    check("reports to commander", lu["p.name"] if lu else None, "commander")

    spawned = s.run("MATCH (:AgentDef {name:'design-lead'})-[:SPAWNS]->(b) RETURN b.name").data()
    spawn_names = [r["b.name"] for r in spawned]
    check("SPAWNS design-architect", "design-architect" in spawn_names, True)

    skills_dl = s.run("MATCH (:AgentDef {name:'design-lead'})-[:USES_SKILL]->(sk) RETURN sk.name").data()
    sk_dl = [r["sk.name"] for r in skills_dl]
    for sk in ["frontend-design-skill","dev-browser","oiloil-ui-ux-guide","visual-ooda-loop","webapp-testing"]:
        check(f"USES_SKILL {sk}", sk in sk_dl, True)

    reach_dl = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef {name:'design-lead'}) RETURN 1 as ok").single()
    check("CMD->DL 1 hop", bool(reach_dl), True)

    spec_row = s.run("MATCH (a:AgentDef {name:'design-lead'}) RETURN a.canonical_spec_path").single()
    sp = spec_row["a.canonical_spec_path"] if spec_row else ""
    spec_file = PROJECT_ROOT / sp if sp else None
    check("spec file exists", bool(spec_file and spec_file.exists()), True)
    if spec_file and spec_file.exists():
        txt = spec_file.read_text(encoding="utf-8", errors="replace")
        for part in ["Part I","Part II","Part III","Part IV","Part V","Part VI"]:
            check(f"spec {part}", part in txt, True)

    wrapper_check("design-lead", [
        ("taste-to-token", "taste-to-token in pipeline"),
        ("visual-ooda-loop", "visual loop"),
        ("dev-browser", "dev-browser"),
        ("oiloil-ui-ux-guide", "UX gate"),
        ("ralph", "ralph-wiggum pattern"),
        ("quality_gate_passed", "output contract"),
    ])

    # ── PROJECT LEAD ───────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PROJECT LEAD")
    print("="*60)
    pl = s.run("MATCH (a:AgentDef {name:'project-lead'}) RETURN a.level, a.color, a.has_canonical_spec").single()
    check("level=2",    pl["a.level"] if pl else None,              2)
    check("color=teal", pl["a.color"] if pl else None,              "teal")
    check("has_spec",   pl["a.has_canonical_spec"] if pl else None, True)

    lu = s.run("MATCH (:AgentDef {name:'project-lead'})-[:LEVEL_UNDER]->(p) RETURN p.name").single()
    check("reports to commander", lu["p.name"] if lu else None, "commander")

    # project-lead SPAWNS leads dynamically (SPAWNS_ONLY — no LEVEL_UNDER from PL)
    pl_spawns = s.run("MATCH (:AgentDef {name:'project-lead'})-[:SPAWNS]->(b) RETURN b.name").data()
    pl_spawn_names = [r["b.name"] for r in pl_spawns]
    for lead in ["engineering-lead","design-lead","forensic-lead","infrastructure-lead"]:
        check(f"PL SPAWNS {lead} (dynamic)", lead in pl_spawn_names, True)

    # those leads should NOT have LEVEL_UNDER pointing to project-lead
    el_lu = s.run("MATCH (:AgentDef {name:'engineering-lead'})-[:LEVEL_UNDER]->(p) RETURN p.name").single()
    check("EL LEVEL_UNDER is commander (not PL)", el_lu["p.name"] if el_lu else None, "commander")

    reach_pl = s.run("MATCH (:AgentDef {name:'commander'})-[:SPAWNS]->(:AgentDef {name:'project-lead'}) RETURN 1 as ok").single()
    check("CMD->PL 1 hop", bool(reach_pl), True)

    spec_row = s.run("MATCH (a:AgentDef {name:'project-lead'}) RETURN a.canonical_spec_path").single()
    sp = spec_row["a.canonical_spec_path"] if spec_row else ""
    spec_file = PROJECT_ROOT / sp if sp else None
    check("spec file exists", bool(spec_file and spec_file.exists()), True)
    if spec_file and spec_file.exists():
        txt = spec_file.read_text(encoding="utf-8", errors="replace")
        for part in ["Part I","Part II","Part III","Part IV","Part V","Part VI"]:
            check(f"spec {part}", part in txt, True)

    wrapper_check("project-lead", [
        ("decompos", "decomposition logic"),
        ("sequential", "sequential vs parallel"),
        ("parallel", "parallel execution"),
        ("compound_task_id", "compound task_id"),
        ("quality_gate_passed", "output contract"),
    ])

    # ── FORENSIC LEAD (wrapper only — Letta agent IS the capability) ───────────
    print("\n" + "="*60)
    print("FORENSIC LEAD WRAPPER")
    print("="*60)
    fl = s.run("MATCH (a:AgentDef {name:'forensic-lead'}) RETURN a.level, a.color, a.has_canonical_spec, a.platform").single()
    check("level=2",  fl["a.level"] if fl else None,              2)
    check("color=red",fl["a.color"] if fl else None,              "red")
    check("has_spec", fl["a.has_canonical_spec"] if fl else None, True)
    check("platform=letta", fl["a.platform"] if fl else None,     "letta")

    fl_skills = s.run("MATCH (:AgentDef {name:'forensic-lead'})-[:USES_SKILL]->(sk) RETURN sk.name").data()
    fl_sk = [r["sk.name"] for r in fl_skills]
    for sk in ["systematic-debugging","root-cause-tracing","tri-agent-bug-audit","pico-warden"]:
        check(f"USES_SKILL {sk}", sk in fl_sk, True)

    wrapper_check("forensic-lead", [
        ("agent-745c61ec", "Letta agent ID in wrapper"),
        ("send_message", "Letta messaging"),
        ("systematic-debugging", "intake skill"),
        ("root-cause-tracing", "trace skill"),
        ("tri-agent-bug-audit", "adversarial skill"),
        ("quality_gate_passed", "output contract"),
        ("STALE DATA", "STALE DATA WARNING"),
    ])

print(f"\n{'='*60}")
print(f"TOTAL: {TOTAL_PASS} PASS  {TOTAL_FAIL} FAIL")
print(f"STATUS: {'GREEN' if TOTAL_FAIL == 0 else 'RED - ' + str(TOTAL_FAIL) + ' failures'}")
driver.close()
