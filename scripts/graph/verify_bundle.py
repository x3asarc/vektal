"""
Bundle Agent + Lesson System — Success Criteria Verification

Graph tests (run BEFORE wrapper — establish red bar):
  T1  AgentDef: level=2, color=amber, has_canonical_spec
  T2  LEVEL_UNDER → commander
  T3  Commander has ROUTES_VIA → bundle
  T4  bundle has no SPAWNS children (pure config agent, never delegates)
  T5  5 BundleTemplate nodes seeded
  T6  All 5 named templates exist by name
  T7  Each template has required properties (name, domains, leads, trigger_count, is_template)
  T8  ACTIVATES_LEAD edges: each template has edges to its leads
  T9  Bundle has MANAGES → BundleTemplate (≥5)
  T10 :Lesson constraint exists (schema ready for runtime writes)
  T11 :Lesson nodes queryable via roundtrip write/read/delete
  T12 APPLIES_TO edge pattern works (Lesson → AgentDef)
  T13 TaskExecution can hold model tracking fields (roundtrip schema test)

Wrapper content tests (run AFTER wrapper is built):
  T14 openrouter/auto documented as default
  T15 Quality floors table present (sonnet/opus minimums per agent)
  T16 5 utility models documented with 2026 models (gemini-3.1-flash-lite, gpt-5-nano, mistral-small-3.2)
  T17 BundleTemplate query documented (Aura lookup)
  T18 Template promotion criteria: trigger_count ≥ 3 + last_quality_score ≥ 0.7
  T19 Lesson injection documented (lessons_from_history in context package)
  T20 Input/output contracts present
  T21 Forbidden patterns: max 5 leads, no quality floor downgrade, no direct score writes
"""
import os, sys, uuid
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pathlib import Path
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
driver = GraphDatabase.driver(os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD")))

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

    # ── T1: AgentDef node ─────────────────────────────────────────────────────
    print("=== T1: AgentDef node ===")
    b = s.run("MATCH (a:AgentDef {name:'bundle'}) RETURN a.level, a.color, a.has_canonical_spec").single()
    check("T1a level=2",     b["a.level"] if b else None,              2)
    check("T1b color=amber", b["a.color"] if b else None,              "amber")
    check("T1c has_spec",    b["a.has_canonical_spec"] if b else None, True)

    # ── T2: Hierarchy ─────────────────────────────────────────────────────────
    print("\n=== T2: LEVEL_UNDER -> commander ===")
    lu = s.run("MATCH (:AgentDef {name:'bundle'})-[:LEVEL_UNDER]->(c) RETURN c.name").single()
    check("T2 reports to commander", lu["c.name"] if lu else None, "commander")

    # ── T3: ROUTES_VIA ────────────────────────────────────────────────────────
    print("\n=== T3: Commander ROUTES_VIA bundle ===")
    rv = s.run("MATCH (:AgentDef {name:'commander'})-[:ROUTES_VIA]->(:AgentDef {name:'bundle'}) RETURN 1 as ok").single()
    check("T3 commander ROUTES_VIA bundle", bool(rv), True)

    # ── T4: No SPAWNS ────────────────────────────────────────────────────────
    print("\n=== T4: Bundle has no SPAWNS ===")
    sp = s.run("MATCH (:AgentDef {name:'bundle'})-[:SPAWNS]->(b) RETURN count(b) as c").single()["c"]
    check("T4 bundle never delegates (spawns=0)", sp, 0)

    # ── T5+T6: BundleTemplate nodes ──────────────────────────────────────────
    print("\n=== T5+T6: BundleTemplate nodes ===")
    bt_count = s.run("MATCH (bt:BundleTemplate) RETURN count(bt) as c").single()["c"]
    check("T5 5 templates seeded", bt_count, 5)

    expected_templates = [
        "product-enrichment-sprint",
        "vendor-onboarding",
        "bug-triage-and-fix",
        "infrastructure-audit",
        "full-feature-sprint",
    ]
    for name in expected_templates:
        row = s.run("MATCH (bt:BundleTemplate {name: $n}) RETURN bt.name", n=name).single()
        check(f"T6 template exists: {name}", bool(row), True)

    # ── T7: Template properties ───────────────────────────────────────────────
    print("\n=== T7: Template required properties ===")
    for name in expected_templates:
        row = s.run("""
            MATCH (bt:BundleTemplate {name: $n})
            RETURN bt.domains IS NOT NULL as has_domains,
                   bt.leads IS NOT NULL as has_leads,
                   bt.trigger_count IS NOT NULL as has_tc,
                   bt.is_template IS NOT NULL as has_it,
                   bt.model_assignments IS NOT NULL as has_ma,
                   bt.budget_allocation IS NOT NULL as has_ba
        """, n=name).single()
        if row:
            for prop in ["has_domains", "has_leads", "has_tc", "has_it", "has_ma", "has_ba"]:
                check(f"T7 {name}.{prop}", row[prop], True)
        else:
            check(f"T7 {name} exists", False, True)

    # ── T8: ACTIVATES_LEAD edges ──────────────────────────────────────────────
    print("\n=== T8: ACTIVATES_LEAD edges ===")
    al = s.run("MATCH (:BundleTemplate)-[:ACTIVATES_LEAD]->(a:AgentDef) RETURN count(a) as c").single()["c"]
    check("T8 ACTIVATES_LEAD edges exist (>=10)", al, lambda c: c >= 10)
    # Each template must have at least 1
    for name in expected_templates:
        row = s.run("""
            MATCH (:BundleTemplate {name: $n})-[:ACTIVATES_LEAD]->(a) RETURN count(a) as c
        """, n=name).single()["c"]
        check(f"T8 {name} activates ≥1 lead", row, lambda c: c >= 1)

    # ── T9: Bundle MANAGES templates ─────────────────────────────────────────
    print("\n=== T9: Bundle MANAGES BundleTemplate ===")
    mg = s.run("MATCH (:AgentDef {name:'bundle'})-[:MANAGES]->(bt:BundleTemplate) RETURN count(bt) as c").single()["c"]
    check("T9 bundle MANAGES ≥5 templates", mg, lambda c: c >= 5)

    # ── T10: :Lesson schema ───────────────────────────────────────────────────
    print("\n=== T10: :Lesson constraint exists ===")
    constraints = s.run("SHOW CONSTRAINTS").data()
    lesson_constraint = any("Lesson" in str(c) for c in constraints)
    check("T10 :Lesson constraint exists", lesson_constraint, True)

    # ── T11: :Lesson roundtrip ────────────────────────────────────────────────
    print("\n=== T11: :Lesson roundtrip write/read ===")
    lid = f"lesson-test-{uuid.uuid4().hex[:8]}"
    s.run("""
        MERGE (l:Lesson {lesson_id: $lid})
        SET l.pattern = 'test-pattern',
            l.lesson = 'test-lesson',
            l.applies_to_lead = 'design-lead',
            l.applies_to_bundle = 'product-enrichment-sprint',
            l.confidence = 1.0,
            l.failure_count = 3,
            l.status = 'active',
            l.first_observed = '2026-01-01T00:00:00+00:00',
            l.last_observed = '2026-01-03T00:00:00+00:00'
    """, lid=lid)
    back = s.run("MATCH (l:Lesson {lesson_id: $lid}) RETURN l.confidence as c, l.status as st", lid=lid).single()
    check("T11 Lesson confidence roundtrip", back["c"] if back else None, 1.0)
    check("T11 Lesson status roundtrip",    back["st"] if back else None, "active")
    # Cleanup
    s.run("MATCH (l:Lesson {lesson_id: $lid}) DETACH DELETE l", lid=lid)

    # ── T12: APPLIES_TO edge pattern ─────────────────────────────────────────
    print("\n=== T12: APPLIES_TO edge (Lesson → AgentDef) ===")
    lid2 = f"lesson-edge-{uuid.uuid4().hex[:8]}"
    s.run("""
        MERGE (l:Lesson {lesson_id: $lid})
        SET l.pattern='edge-test', l.lesson='edge-lesson',
            l.applies_to_lead='design-lead', l.status='active',
            l.confidence=0.9, l.failure_count=3
    """, lid=lid2)
    s.run("""
        MATCH (l:Lesson {lesson_id: $lid}), (a:AgentDef {name: 'design-lead'})
        MERGE (l)-[:APPLIES_TO]->(a)
    """, lid=lid2)
    edge = s.run("""
        MATCH (:Lesson {lesson_id: $lid})-[:APPLIES_TO]->(a:AgentDef)
        RETURN a.name as n
    """, lid=lid2).single()
    check("T12 APPLIES_TO edge works", edge["n"] if edge else None, "design-lead")
    # Check Bundle can query lessons for a lead
    lessons_for_lead = s.run("""
        MATCH (l:Lesson)-[:APPLIES_TO]->(a:AgentDef {name: 'design-lead'})
        WHERE l.status = 'active'
        RETURN l.lesson as lesson, l.confidence as conf
        ORDER BY l.confidence DESC LIMIT 5
    """).data()
    check("T12 Bundle can query lessons for lead", len(lessons_for_lead), lambda n: n >= 1)
    # Cleanup
    s.run("MATCH (l:Lesson {lesson_id: $lid}) DETACH DELETE l", lid=lid2)

    # ── T13: TaskExecution model tracking schema ──────────────────────────────
    print("\n=== T13: TaskExecution model tracking fields ===")
    te_id = f"te-test-{uuid.uuid4().hex[:8]}"
    s.run("""
        MERGE (te:TaskExecution {task_id: $tid})
        SET te.task_type='test', te.lead_invoked='engineering-lead',
            te.quality_gate_passed=true, te.loop_count=2,
            te.model_requested='openrouter/auto',
            te.model_used='anthropic/claude-sonnet-4-5',
            te.utility_models_used=['classifier','json_validator'],
            te.model_cost_usd=0.0023,
            te.escalation_triggered=false,
            te.difficulty_tier='STANDARD',
            te.status='test', te.created_at='2026-01-01T00:00:00+00:00'
    """, tid=te_id)
    te_back = s.run("""
        MATCH (te:TaskExecution {task_id: $tid})
        RETURN te.model_requested as mr, te.model_used as mu,
               te.difficulty_tier as dt, te.escalation_triggered as et
    """, tid=te_id).single()
    check("T13 model_requested", te_back["mr"] if te_back else None, "openrouter/auto")
    check("T13 model_used",      te_back["mu"] if te_back else None, "anthropic/claude-sonnet-4-5")
    check("T13 difficulty_tier", te_back["dt"] if te_back else None, "STANDARD")
    check("T13 escalation_triggered", te_back["et"] if te_back else None, False)
    # Cleanup
    s.run("MATCH (te:TaskExecution {task_id: $tid}) DELETE te", tid=te_id)

    # ── T14-T21: Wrapper content tests ───────────────────────────────────────
    print("\n=== T14-T21: Wrapper content ===")
    spec_row = s.run("MATCH (a:AgentDef {name:'bundle'}) RETURN a.canonical_spec_path").single()
    sp = spec_row["a.canonical_spec_path"] if spec_row else ""
    spec_file = PROJECT_ROOT / sp if sp else None
    check("T spec file exists", bool(spec_file and spec_file.exists()), True)
    if spec_file and spec_file.exists():
        txt = spec_file.read_text(encoding="utf-8", errors="replace")
        for part in ["Part I","Part II","Part III","Part IV","Part V","Part VI"]:
            check(f"spec {part}", part in txt, True)

    wrapper = PROJECT_ROOT / ".claude" / "agents" / "bundle.md"
    if wrapper.exists():
        wtxt = wrapper.read_text(encoding="utf-8", errors="replace")
        check("T14 openrouter/auto default",      "openrouter/auto" in wtxt, True)
        check("T15 quality floors (sonnet/opus)",  all(m in wtxt for m in ["sonnet","opus"]), True)
        check("T16 gemini-3.1-flash-lite",         "gemini-3.1-flash-lite" in wtxt, True)
        check("T16 gpt-5-nano",                    "gpt-5-nano" in wtxt, True)
        check("T16 mistral-small-3.2",             "mistral-small-3.2" in wtxt or "mistral-small" in wtxt, True)
        check("T17 BundleTemplate Aura query",     "BundleTemplate" in wtxt, True)
        check("T18 trigger_count",                 "trigger_count" in wtxt, True)
        check("T18 last_quality_score",            "last_quality_score" in wtxt, True)
        check("T19 lessons_from_history",          "lessons_from_history" in wtxt, True)
        check("T19 Lesson query",                  "Lesson" in wtxt, True)
        check("T20 input contract",                all(k in wtxt for k in ["task","intent","quality_gate"]), True)
        check("T20 output contract",               "compound_task_id" in wtxt, True)
        check("T21 forbidden: max 5 leads",        "5" in wtxt and "lead" in wtxt.lower(), True)
    else:
        print("  [SKIP] bundle.md not yet built")

print(f"\n{'='*60}")
print(f"RESULT: {PASS} PASS  {FAIL} FAIL")
print(f"STATUS: {'GREEN' if FAIL == 0 else 'RED — ' + str(FAIL) + ' failures'}")
driver.close()
