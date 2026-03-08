"""Orchestration layer indexer — nodes + full edge graph.

Writes to Aura (schema from docs/agent-system/finetuned-resources.md):
  :AgentDef    {level, provider, color, tools, ...}
  :SkillDef    {tier, quality_score, trigger_count, source_url, installed_at, ...}
  :HookDef     {event, script, blocking, provider}
  :LongTermPattern

Edges:
  (:AgentDef)-[:LEVEL_UNDER]->(:AgentDef)   hierarchy (Lead under Commander)
  (:AgentDef)-[:SPAWNS]->(:AgentDef)        task delegation
  (:AgentDef)-[:USES_SKILL]->(:SkillDef)    skill wiring
  (:SkillDef)-[:IMPLEMENTS]->(:Function)    skill -> Python entry points
  (:HookDef)-[:RUNS_SCRIPT]->(:File)        hook -> codebase bridge
"""
import hashlib, json, os, re, sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync, _now_iso
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ── Metadata tables (source: locked specs + finetuned-resources.md) ───────────

AGENT_LEVELS = {          # 1=Commander 2=Lead 3=Specialist
    "commander": 1,
    "engineering-lead": 2, "design-lead": 2, "forensic-lead": 2,
    "infrastructure-lead": 2, "project-lead": 2,
    "task-observer": 2, "validator": 2, "bundle": 2,
}
AGENT_COLORS = {
    "commander": "gold",
    "engineering-lead": "blue", "design-lead": "purple",
    "forensic-lead": "red", "infrastructure-lead": "orange",
    "project-lead": "teal", "task-observer": "cyan", "validator": "green",
    "bundle": "amber",
}
AGENT_PROVIDER = {
    "forensic-lead": "letta",     # delegates to Letta agent-745c61ec
}

# Permanent hierarchy: supervisor → [subordinates]  (LEVEL_UNDER + SPAWNS)
# Permanent = org chart relationship. Subordinate always reports to this supervisor.
HIERARCHY: dict[str, list[str]] = {
    "commander":           ["engineering-lead", "infrastructure-lead", "design-lead",
                            "project-lead", "forensic-lead", "task-observer", "bundle"],
    "infrastructure-lead": ["validator"],
    "engineering-lead":    ["gsd-planner", "gsd-executor", "gsd-verifier",
                            "gsd-plan-checker", "gsd-integration-checker", "gsd-debugger"],
    "design-lead":         ["design-architect"],
}

# Dynamic delegation only: spawner → [delegates]  (SPAWNS only, no LEVEL_UNDER)
# These are task-time delegations, not permanent reporting lines.
SPAWNS_ONLY: dict[str, list[str]] = {
    "project-lead": ["engineering-lead", "design-lead", "forensic-lead", "infrastructure-lead"],
    "commander":    [],  # Commander's dynamic routing handled by HIERARCHY already
}

# Agent → skills it uses  (USES_SKILL)
USES_SKILL: dict[str, list[str]] = {
    "commander":          ["brainstorming", "find-skills", "deep-research"],
    "engineering-lead":   ["review-implementing", "test-driven-development", "test-fixing",
                           "defense-in-depth", "postgres", "finishing-a-development-branch",
                           "using-git-worktrees"],
    "design-lead":        ["frontend-design-skill", "dev-browser", "oiloil-ui-ux-guide",
                           "visual-ooda-loop", "webapp-testing",
                           "taste-to-token-extractor", "design-atoms", "design-molecules",
                           "design-interactions", "frontend-deploy-debugger"],
    "forensic-lead":      ["systematic-debugging", "root-cause-tracing",
                           "tri-agent-bug-audit", "pico-warden"],
    "infrastructure-lead": ["pico-warden", "varlock-claude-skill"],
}

# Skill → Python Function signatures it implements  (IMPLEMENTS)
IMPLEMENTS: dict[str, list[str]] = {
    "pico-warden": [
        "src.graph.infra_probe.probe_aura",
        "src.graph.infra_probe.probe_local_neo4j",
        "src.graph.infra_probe.active_remediation_loop",
        "src.graph.backend_resolver.probe_aura_http",
        "src.graph.backend_resolver.probe_bolt",
        "src.graph.backend_resolver.runtime_backend_mode",
        "src.graph.orchestrate_healers.orchestrate_remediation",
        "src.graph.orchestrate_healers.orchestrate_healing",
        "src.graph.orchestrate_healers.record_remediation_outcome",
        "src.graph.orchestrate_healers.normalize_sentry_issue",
        "src.graph.orchestrate_healers.route_service_for_classification",
    ],
}

# ── Utility model manifest (model-policy.md + 2026 recommendations) ───────────
# DEFAULT for all tasks: openrouter/auto
# Quality floors: sonnet (Validator standard, Engineering CRITICAL, varlock),
#                 opus  (Validator governance, Forensic adversary/referee)
UTILITY_MODELS = {
    "classifier":    "google/gemini-3.1-flash-lite",      # intent detection (2026)
    "difficulty":    "google/gemini-3.1-flash-lite",      # tier classification (2026)
    "tool_selector": "google/gemini-3.1-flash-lite",      # model vs tool decision (2026)
    "json_validator":"mistralai/mistral-small-3.2",        # schema strictness (2026)
    "summarizer":    "openai/gpt-5-nano",                  # STATE.md + episode compression (2026)
}
QUALITY_FLOORS = {
    # (agent, subtask_type) → minimum model
    ("validator",         "standard_review"): "anthropic/claude-sonnet-4-5",
    ("validator",         "governance_auth"): "anthropic/claude-opus-4",
    ("forensic-lead",     "tri_adversary"):   "anthropic/claude-opus-4",
    ("forensic-lead",     "tri_referee"):     "anthropic/claude-opus-4",
    ("commander",         "compound_cot"):    "anthropic/claude-sonnet-4-5",
    ("engineering-lead",  "security_critical"):"anthropic/claude-sonnet-4-5",
    ("infrastructure-lead","varlock"):         "anthropic/claude-sonnet-4-5",
}

# ── BundleTemplate seed data (initial project recipes for Aura) ───────────────
# trigger_count=0 + is_template=False until task-observer graduates them.
# model_assignments: openrouter/auto default; quality floors applied per QUALITY_FLOORS.
BUNDLE_TEMPLATES: list[dict] = [
    {
        "name":        "product-enrichment-sprint",
        "description": "Backend API + frontend UI for product enrichment features. "
                       "Engineering Lead (API, tests) + Design Lead (tokens → atoms → visual gate).",
        "domains":     ["engineering", "design"],
        "leads":       ["engineering-lead", "design-lead"],
        "model_assignments": json.dumps({
            "engineering-lead": "openrouter/auto",
            "design-lead":      "openrouter/auto",
        }),
        "budget_allocation": json.dumps({
            "engineering-lead": 5,
            "design-lead":      4,
        }),
        "skills_override": json.dumps({
            "design-lead": ["oiloil-ui-ux-guide", "taste-to-token-extractor"],
        }),
        "compound_gate": "All tests pass + visual satisfaction ≥ 8/10 + no console errors",
    },
    {
        "name":        "vendor-onboarding",
        "description": "Integrate a new supplier vendor: scraper adapter + API endpoints + deployment validation.",
        "domains":     ["engineering", "infrastructure"],
        "leads":       ["engineering-lead", "infrastructure-lead"],
        "model_assignments": json.dumps({
            "engineering-lead":    "openrouter/auto",
            "infrastructure-lead": "openrouter/auto",
        }),
        "budget_allocation": json.dumps({
            "engineering-lead":    5,
            "infrastructure-lead": 3,
        }),
        "skills_override": json.dumps({
            "engineering-lead": ["postgres", "defense-in-depth"],
        }),
        "compound_gate": "All tests pass + deployment gate GREEN + varlock clean",
    },
    {
        "name":        "bug-triage-and-fix",
        "description": "Sequential: Forensic Lead investigates → confirmed root cause → "
                       "Engineering Lead applies fix. Triggered by SentryIssue or bug report.",
        "domains":     ["forensic", "engineering"],
        "leads":       ["forensic-lead", "engineering-lead"],
        "model_assignments": json.dumps({
            "forensic-lead":   "openrouter/auto",      # tri-adversary/referee get opus floor via quality_floors
            "engineering-lead":"openrouter/auto",
        }),
        "budget_allocation": json.dumps({
            "forensic-lead":    5,
            "engineering-lead": 4,
        }),
        "skills_override": json.dumps({
            "forensic-lead": ["systematic-debugging", "root-cause-tracing", "tri-agent-bug-audit"],
        }),
        "compound_gate": "Root cause CONFIRMED confidence ≥ 0.7 + all tests pass after fix",
    },
    {
        "name":        "infrastructure-audit",
        "description": "Infrastructure health sweep: Aura probe + deployment gate + ImprovementProposal "
                       "queue drain + task-observer pattern cycle. Typically scheduled maintenance.",
        "domains":     ["infrastructure"],
        "leads":       ["infrastructure-lead", "task-observer"],
        "model_assignments": json.dumps({
            "infrastructure-lead": "openrouter/auto",
            "task-observer":       "openrouter/auto",
        }),
        "budget_allocation": json.dumps({
            "infrastructure-lead": 3,
            "task-observer":       1,
        }),
        "skills_override": json.dumps({
            "infrastructure-lead": ["pico-warden", "varlock-claude-skill"],
        }),
        "compound_gate": "Backend GREEN + deployment GREEN + proposals queued + patterns synced",
    },
    {
        "name":        "full-feature-sprint",
        "description": "Full-stack feature: Engineering builds + Design implements UI + "
                       "post-deploy forensic validation (optional if risk is HIGH/CRITICAL).",
        "domains":     ["engineering", "design", "forensic"],
        "leads":       ["engineering-lead", "design-lead", "forensic-lead"],
        "model_assignments": json.dumps({
            "engineering-lead": "openrouter/auto",
            "design-lead":      "openrouter/auto",
            "forensic-lead":    "openrouter/auto",    # adversary/referee get opus floor
        }),
        "budget_allocation": json.dumps({
            "engineering-lead": 6,
            "design-lead":      5,
            "forensic-lead":    3,
        }),
        "skills_override": json.dumps({
            "design-lead":    ["oiloil-ui-ux-guide"],
            "forensic-lead":  ["systematic-debugging", "tri-agent-bug-audit"],
        }),
        "compound_gate": "All tests pass + visual ≥ 8/10 + no regressions + post-deploy probe GREEN",
    },
]

# ── External skills not yet installed — stub nodes with tier/source metadata
EXTERNAL_SKILLS: list[dict] = [
    # Tier 1 — install immediately
    {"name": "dev-browser",        "tier": 1, "platform": "claude", "skill_type": "plugin",
     "source_url": "https://github.com/SawyerHood/dev-browser",
     "description": "Persistent browser state + agentic execution. Replaces fragile Playwright scripts."},
    {"name": "agnix",              "tier": 1, "platform": "claude", "skill_type": "linter",
     "source_url": "",
     "description": "Agent config linter. 156 rules, auto-fix, LSP server. Validates SKILL.md files."},
    {"name": "plugin-authoring",   "tier": 1, "platform": "claude", "skill_type": "guidance",
     "source_url": "",
     "description": "Authoritative guidance for Claude Code plugins with hook schema and plugin.json."},
    {"name": "varlock-claude-skill","tier": 1, "platform": "claude", "skill_type": "security",
     "source_url": "",
     "description": "Secure env var management. Secrets never appear in sessions, terminals, logs."},
    # Tier 2 — evaluate before agent build
    {"name": "systematic-debugging","tier": 2, "platform": "claude", "skill_type": "forensic",
     "source_url": "",
     "description": "Forensic Lead intake: characterise failure before proposing fixes."},
    {"name": "root-cause-tracing", "tier": 2, "platform": "claude", "skill_type": "forensic",
     "source_url": "",
     "description": "Trace errors deep in execution back to original trigger."},
    {"name": "tri-agent-bug-audit","tier": 2, "platform": "claude", "skill_type": "forensic",
     "source_url": "",
     "description": "Adversarial validation: Neutral + Bug Finder + Adversary + Referee pattern."},
    {"name": "review-implementing","tier": 2, "platform": "claude", "skill_type": "engineering",
     "source_url": "",
     "description": "Evaluate implementation plans against specs. Pre-gsd-executor gate."},
    {"name": "test-driven-development","tier": 2, "platform": "claude", "skill_type": "engineering",
     "source_url": "",
     "description": "TDD intake protocol. Augments GSD executor TDD mode."},
    {"name": "test-fixing",        "tier": 2, "platform": "claude", "skill_type": "engineering",
     "source_url": "",
     "description": "Fix failing tests. Invoked by Engineering Lead during loop failures."},
    {"name": "defense-in-depth",   "tier": 2, "platform": "claude", "skill_type": "security",
     "source_url": "",
     "description": "Multi-layered testing + security for CRITICAL/HIGH risk tier changes."},
    {"name": "postgres",           "tier": 2, "platform": "claude", "skill_type": "data",
     "source_url": "",
     "description": "Safe read-only SQL against PostgreSQL. Post-execution data verification."},
    {"name": "webapp-testing",     "tier": 2, "platform": "claude", "skill_type": "testing",
     "source_url": "",
     "description": "Committed E2E regression suite. Complements dev-browser exploratory loop."},
    {"name": "using-git-worktrees","tier": 2, "platform": "claude", "skill_type": "engineering",
     "source_url": "",
     "description": "Isolated git worktrees. Prevents file conflicts in parallel Lead execution."},
    {"name": "oiloil-ui-ux-guide", "tier": 2, "platform": "claude", "skill_type": "design",
     "source_url": "",
     "description": "UX quality gate. CRAP principles, HCI laws, interaction psychology."},
    {"name": "finishing-a-development-branch","tier": 2, "platform": "claude", "skill_type": "engineering",
     "source_url": "",
     "description": "Done protocol: commit, PR, branch cleanup, STATE.md update."},
    {"name": "deep-research",      "tier": 2, "platform": "claude", "skill_type": "research",
     "source_url": "",
     "description": "Gemini Deep Research for architectural decisions before implementation."},
    # Tier 3 — reference / future
    {"name": "brainstorming",      "tier": 3, "platform": "claude", "skill_type": "intake",
     "source_url": "",
     "description": "Structure vague requests before Commander routing."},
    {"name": "find-skills",        "tier": 3, "platform": "claude", "skill_type": "discovery",
     "source_url": "",
     "description": "Discover and install agent skills from marketplace."},
]

# HookDef nodes (from .claude/settings.json)
HOOK_DEFS: list[dict] = [
    {"event": "SessionStart", "script": ".claude/hooks/start-health-daemon.py",     "blocking": False},
    {"event": "SessionStart", "script": "scripts/memory/session_start.py",          "blocking": False},
    {"event": "SessionStart", "script": ".claude/hooks/gsd-check-update.js",        "blocking": False},
    {"event": "SessionStart", "script": ".claude/hooks/check-pending-improvements.py","blocking": False},
    {"event": "PreToolUse",   "script": "scripts/governance/health_gate.py",        "blocking": False},
    {"event": "PreToolUse",   "script": "scripts/memory/pre_tool_update.py",        "blocking": False},
    {"event": "PreToolUse",   "script": "scripts/hooks/antigravity_notify.py",      "blocking": False},
    {"event": "PreToolUse",   "script": "scripts/governance/risk_tier_gate_enforce.py","blocking": True},
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sid(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:12]

def _first_line(text: str, max_len: int = 200) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#* ").strip()
        if line and not line.startswith("---"):
            return line[:max_len]
    return ""


# ── Scanners ──────────────────────────────────────────────────────────────────

def scan_agent_defs() -> list[dict]:
    agents = []
    # Platform wrappers (.claude/agents/)
    for md in (PROJECT_ROOT / ".claude" / "agents").glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        name = md.stem
        agents.append({
            "agent_id":          _sid("claude", name),
            "name":              name,
            "platform":          AGENT_PROVIDER.get(name, "claude"),
            "spec_path":         str(md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "description":       _first_line(text),
            "has_canonical_spec": False,
            "level":             AGENT_LEVELS.get(name, 3),
            "color":             AGENT_COLORS.get(name, ""),
        })
    # Canonical specs (docs/agent-system/specs/)
    specs_dir = PROJECT_ROOT / "docs" / "agent-system" / "specs"
    if specs_dir.exists():
        for md in specs_dir.glob("*.md"):
            text = md.read_text(encoding="utf-8", errors="replace")
            name = md.stem
            existing = next((a for a in agents if a["name"] == name), None)
            if existing:
                existing["canonical_spec_path"] = str(md.relative_to(PROJECT_ROOT)).replace("\\", "/")
                existing["has_canonical_spec"] = True
            else:
                agents.append({
                    "agent_id":           _sid("spec", name),
                    "name":               name,
                    "platform":           "spec-only",   # always spec-only until a wrapper exists
                    "spec_path":          str(md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "description":        _first_line(text),
                    "has_canonical_spec": True,
                    "canonical_spec_path": str(md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "level":              AGENT_LEVELS.get(name, 3),
                    "color":              AGENT_COLORS.get(name, ""),
                })
    return agents


def scan_skill_defs() -> list[dict]:
    skills: list[dict] = []
    existing_names: set[str] = set()

    skills_root = PROJECT_ROOT / ".claude" / "skills"

    # Subdirectory skills (SKILL.md pattern — the majority)
    for skill_dir in skills_root.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            # try name-based SKILL.md (e.g. frontend-design-SKILL.md)
            candidates = list(skill_dir.glob("*SKILL*.md"))
            skill_md = candidates[0] if candidates else None
        if not skill_md:
            continue
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        name = skill_dir.name
        skills.append({
            "skill_id":     _sid("skill", name),
            "name":         name,
            "platform":     "claude",
            "skill_type":   "skill-dir",
            "tier":         1,
            "installed_at": ["claude"],
            "quality_score": None,
            "trigger_count": 0,
            "source_url":   "",
            "spec_path":    str(skill_md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "description":  _first_line(text)[:200],
        })
        existing_names.add(name)

    # Installed YAML skills (legacy flat format)
    for yaml_file in skills_root.glob("*.yaml"):
        text  = yaml_file.read_text(encoding="utf-8", errors="replace")
        name  = yaml_file.stem
        desc  = re.search(r"description:\s*(.+)", text)
        skills.append({
            "skill_id":     _sid("skill", name),
            "name":         name,
            "platform":     "claude",
            "skill_type":   "yaml",
            "tier":         1,       # installed = tier 1
            "installed_at": ["claude"],
            "quality_score": None,
            "trigger_count": 0,
            "source_url":   "",
            "spec_path":    str(yaml_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "description":  (desc.group(1).strip().strip("\"'") if desc else "")[:200],
        })
        existing_names.add(name)

    # Letta SKILL.md files
    letta_root = PROJECT_ROOT / ".letta" / "skills"
    if letta_root.exists():
        for skill_f in letta_root.rglob("SKILL.md"):
            text = skill_f.read_text(encoding="utf-8", errors="replace")
            name = skill_f.parent.name
            skills.append({
                "skill_id":     _sid("letta", name),
                "name":         name,
                "platform":     "letta",
                "skill_type":   "letta-skill",
                "tier":         1,
                "installed_at": ["letta"],
                "quality_score": None,
                "trigger_count": 0,
                "source_url":   "",
                "spec_path":    str(skill_f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "description":  _first_line(text)[:200],
            })
            existing_names.add(name)

    # External skill stubs (not yet installed)
    for ext in EXTERNAL_SKILLS:
        if ext["name"] not in existing_names:
            skills.append({
                "skill_id":     _sid("ext", ext["name"]),
                "name":         ext["name"],
                "platform":     ext["platform"],
                "skill_type":   ext["skill_type"],
                "tier":         ext["tier"],
                "installed_at": [],          # not yet installed
                "quality_score": None,
                "trigger_count": 0,
                "source_url":   ext.get("source_url", ""),
                "spec_path":    "",
                "description":  ext["description"],
            })

    return skills


def scan_hook_defs() -> list[dict]:
    return [{
        "hook_id":  _sid("hook", h["event"], h["script"]),
        "event":    h["event"],
        "script":   h["script"],
        "blocking": h["blocking"],
        "provider": "claude",
    } for h in HOOK_DEFS]


def scan_long_term_patterns() -> list[dict]:
    patterns = []

    def _parse_fj(path: Path) -> list[dict]:
        text = path.read_text(encoding="utf-8", errors="replace")
        for section in re.split(r"^### ", text, flags=re.MULTILINE)[1:]:
            lines = section.strip().splitlines()
            if not lines:
                continue
            header = lines[0].strip()
            parts  = [p.strip() for p in header.split("|")]
            date_str = parts[0] if parts else ""
            task_id  = parts[1] if len(parts) > 1 else ""
            body     = "\n".join(lines[1:]).strip()
            fail     = re.search(r"2\.\s+Failed Y:\s+(.+)", body)
            desc     = fail.group(1).strip()[:300] if fail else body[:300]
            domain   = task_id.split("-")[0] if task_id else "general"
            patterns.append({
                "pattern_id": _sid("fj", date_str, task_id),
                "domain":     domain,
                "source":     "FAILURE_JOURNEY.md",
                "description": desc,
                "task_id":    task_id,
                "StartDate":  f"{date_str}T00:00:00+00:00" if re.match(r"\d{4}-\d{2}-\d{2}", date_str) else _now_iso(),
                "EndDate":    None,
            })
        return patterns

    fj = PROJECT_ROOT / "FAILURE_JOURNEY.md"
    if fj.exists():
        patterns.extend(_parse_fj(fj))

    learnings = PROJECT_ROOT / "LEARNINGS.md"
    if learnings.exists():
        text = learnings.read_text(encoding="utf-8", errors="replace")
        for section in re.split(r"^### |^## ", text, flags=re.MULTILINE)[1:]:
            lines  = section.strip().splitlines()
            header = lines[0].strip()
            body   = "\n".join(lines[1:]).strip()
            if len(body) < 20:
                continue
            patterns.append({
                "pattern_id": _sid("learn", header),
                "domain":     "learnings",
                "source":     "LEARNINGS.md",
                "description": (header + ": " + body[:200]),
                "task_id":    "",
                "StartDate":  _now_iso(),
                "EndDate":    None,
            })
    return patterns


# ── Syncer functions ──────────────────────────────────────────────────────────

def dedup_agent_defs(session) -> int:
    """Remove spec-only AgentDef nodes superseded by a platform wrapper with same name.

    Two strategies:
    1. platform='spec-only' match (standard case)
    2. agent_id prefix match for nodes where platform was incorrectly set
       (forensic-lead bug: spec-only was indexed as 'letta' before this fix)
    """
    # Build the set of spec-only agent_ids from the current scan
    spec_ids = [_sid("spec", name) for name in [
        "commander", "engineering-lead", "infrastructure-lead", "design-lead",
        "project-lead", "forensic-lead", "task-observer", "validator", "bundle",
    ]]
    # Strategy 1: platform='spec-only'
    r1 = session.run("""
        MATCH (spec:AgentDef {platform: 'spec-only'})
        MATCH (wrap:AgentDef {name: spec.name})
        WHERE elementId(wrap) <> elementId(spec)
        DETACH DELETE spec
        RETURN count(spec) AS removed
    """).single()
    removed1 = r1["removed"] if r1 else 0
    # Strategy 2: known spec_ids that survived with wrong platform
    r2 = session.run("""
        UNWIND $ids AS sid
        MATCH (spec:AgentDef {agent_id: sid})
        MATCH (wrap:AgentDef {name: spec.name})
        WHERE elementId(wrap) <> elementId(spec)
        DETACH DELETE spec
        RETURN count(spec) AS removed
    """, ids=spec_ids).single()
    removed2 = r2["removed"] if r2 else 0
    return removed1 + removed2


def sync_agent_defs(session, agents: list[dict]) -> int:
    session.run("CREATE CONSTRAINT agentdef_id_unique IF NOT EXISTS FOR (a:AgentDef) REQUIRE a.agent_id IS UNIQUE")
    for a in agents:
        session.run("""
            MERGE (ad:AgentDef {agent_id: $agent_id})
            SET ad.name = $name, ad.platform = $platform, ad.spec_path = $spec_path,
                ad.description = $description, ad.has_canonical_spec = $hcs,
                ad.canonical_spec_path = $csp, ad.level = $level, ad.color = $color
        """, agent_id=a["agent_id"], name=a["name"], platform=a["platform"],
             spec_path=a["spec_path"], description=a.get("description", ""),
             hcs=a.get("has_canonical_spec", False), csp=a.get("canonical_spec_path", ""),
             level=a.get("level", 3), color=a.get("color", ""))
    return len(agents)


def sync_skill_defs(session, skills: list[dict]) -> int:
    session.run("CREATE CONSTRAINT skilldef_id_unique IF NOT EXISTS FOR (s:SkillDef) REQUIRE s.skill_id IS UNIQUE")
    for s in skills:
        session.run("""
            MERGE (sd:SkillDef {skill_id: $skill_id})
            SET sd.name = $name, sd.platform = $platform, sd.skill_type = $stype,
                sd.tier = $tier, sd.installed_at = $installed_at,
                sd.trigger_count = coalesce(sd.trigger_count, $tc),
                sd.quality_score = coalesce(sd.quality_score, $qs),
                sd.source_url = $source_url, sd.spec_path = $spec_path,
                sd.description = $description
        """, skill_id=s["skill_id"], name=s["name"], platform=s["platform"],
             stype=s["skill_type"], tier=s["tier"], installed_at=s["installed_at"],
             tc=s["trigger_count"], qs=s["quality_score"],
             source_url=s["source_url"], spec_path=s["spec_path"],
             description=s.get("description", ""))
    return len(skills)


def sync_hook_defs(session, hooks: list[dict]) -> int:
    session.run("CREATE CONSTRAINT hookdef_id_unique IF NOT EXISTS FOR (h:HookDef) REQUIRE h.hook_id IS UNIQUE")
    for h in hooks:
        session.run("""
            MERGE (hd:HookDef {hook_id: $hook_id})
            SET hd.event = $event, hd.script = $script,
                hd.blocking = $blocking, hd.provider = $provider
        """, hook_id=h["hook_id"], event=h["event"], script=h["script"],
             blocking=h["blocking"], provider=h["provider"])
        # Bridge: HookDef -> File (if file node exists)
        session.run("""
            MATCH (hd:HookDef {hook_id: $hook_id})
            OPTIONAL MATCH (f:File {path: $script}) WHERE f.EndDate IS NULL
            FOREACH (_ IN CASE WHEN f IS NOT NULL THEN [1] ELSE [] END |
                MERGE (hd)-[:RUNS_SCRIPT]->(f)
            )
        """, hook_id=h["hook_id"], script=h["script"])
    return len(hooks)


def sync_long_term_patterns(session, patterns: list[dict]) -> int:
    session.run("CREATE CONSTRAINT ltpattern_id_unique IF NOT EXISTS FOR (p:LongTermPattern) REQUIRE p.pattern_id IS UNIQUE")
    for p in patterns:
        session.run("""
            MERGE (lp:LongTermPattern {pattern_id: $pattern_id})
            SET lp.domain = $domain, lp.source = $source, lp.description = $description,
                lp.task_id = $task_id, lp.StartDate = $StartDate, lp.EndDate = $EndDate
        """, pattern_id=p["pattern_id"], domain=p["domain"], source=p["source"],
             description=p["description"], task_id=p.get("task_id", ""),
             StartDate=p.get("StartDate"), EndDate=p.get("EndDate"))
    return len(patterns)


def sync_lesson_schema(session) -> None:
    """Ensure :Lesson constraint exists. Lesson nodes are written at runtime by task-observer."""
    session.run("CREATE CONSTRAINT lesson_id_unique IF NOT EXISTS "
                "FOR (l:Lesson) REQUIRE l.lesson_id IS UNIQUE")
    # Schema definition — nodes written by task-observer, read by Bundle at config time.
    # Fields:
    #   lesson_id         (string)  — uuid
    #   pattern           (string)  — what failure pattern was observed
    #   lesson            (string)  — the actionable takeaway for the Lead
    #   applies_to_lead   (string)  — Lead name this lesson is for
    #   applies_to_bundle (string)  — bundle template name, or null = global
    #   confidence        (float)   — failure_count / total_runs_with_pattern
    #   failure_count     (int)     — how many times observed
    #   first_observed    (string)  — ISO timestamp
    #   last_observed     (string)  — ISO timestamp
    #   status            (string)  — "active" | "superseded" | "resolved"
    # Edges:
    #   (:Lesson)-[:APPLIES_TO]->(:AgentDef)       — which Lead
    #   (:Lesson)-[:INFERRED_FROM]->(:TaskExecution) — evidence trail


def sync_bundle_templates(session, templates: list[dict]) -> int:
    """Write :BundleTemplate nodes to Aura — preserves existing trigger_count/scores."""
    session.run("CREATE CONSTRAINT bundle_template_id_unique IF NOT EXISTS "
                "FOR (bt:BundleTemplate) REQUIRE bt.template_id IS UNIQUE")
    for t in templates:
        tid = _sid("bundle", t["name"])
        session.run("""
            MERGE (bt:BundleTemplate {template_id: $tid})
            SET bt.name               = $name,
                bt.description        = $desc,
                bt.domains            = $domains,
                bt.leads              = $leads,
                bt.model_assignments  = $model_assignments,
                bt.budget_allocation  = $budget_allocation,
                bt.skills_override    = $skills_override,
                bt.compound_gate      = $compound_gate,
                bt.trigger_count      = coalesce(bt.trigger_count, 0),
                bt.last_quality_score = coalesce(bt.last_quality_score, 0.0),
                bt.avg_loop_count     = coalesce(bt.avg_loop_count, 0.0),
                bt.is_template        = coalesce(bt.is_template, false),
                bt.created_at         = coalesce(bt.created_at, $now),
                bt.updated_at         = $now
        """, tid=tid, name=t["name"], desc=t["description"],
             domains=t["domains"], leads=t["leads"],
             model_assignments=t["model_assignments"],
             budget_allocation=t["budget_allocation"],
             skills_override=t["skills_override"],
             compound_gate=t["compound_gate"],
             now=_now_iso())
    return len(templates)


def sync_edges(session) -> dict[str, int]:
    counts = {"level_under": 0, "spawns": 0, "uses_skill": 0, "implements": 0,
              "runs_script": 0, "routes_via": 0, "activates_lead": 0}

    # Clear all existing LEVEL_UNDER before recreating from authoritative HIERARCHY map.
    # This ensures stale edges from previous schema iterations are removed.
    session.run("MATCH ()-[r:LEVEL_UNDER]->() DELETE r")

    # LEVEL_UNDER + SPAWNS (permanent hierarchy)
    for supervisor, subordinates in HIERARCHY.items():
        for sub in subordinates:
            r = session.run("""
                MATCH (a:AgentDef {name: $sup}), (b:AgentDef {name: $sub})
                MERGE (b)-[:LEVEL_UNDER]->(a)
                MERGE (a)-[:SPAWNS]->(b)
                RETURN 1 AS ok
            """, sup=supervisor, sub=sub).data()
            if r:
                counts["level_under"] += 1
                counts["spawns"] += 1

    # SPAWNS only (dynamic delegation — no LEVEL_UNDER, not a permanent reporting line)
    for spawner, delegates in SPAWNS_ONLY.items():
        for delegate in delegates:
            session.run("""
                MATCH (a:AgentDef {name: $sp}), (b:AgentDef {name: $dl})
                MERGE (a)-[:SPAWNS]->(b)
            """, sp=spawner, dl=delegate)
            counts["spawns"] += 1

    # USES_SKILL
    for agent_name, skill_names in USES_SKILL.items():
        for skill_name in skill_names:
            r = session.run("""
                MATCH (a:AgentDef {name: $agent}), (sk:SkillDef {name: $skill})
                MERGE (a)-[:USES_SKILL]->(sk)
                RETURN 1 AS ok
            """, agent=agent_name, skill=skill_name).data()
            if r:
                counts["uses_skill"] += 1

    # IMPLEMENTS
    for skill_name, sigs in IMPLEMENTS.items():
        for sig in sigs:
            r = session.run("""
                MATCH (sk:SkillDef {name: $skill}), (f:Function {function_signature: $sig})
                WHERE f.EndDate IS NULL
                MERGE (sk)-[:IMPLEMENTS]->(f)
                RETURN 1 AS ok
            """, skill=skill_name, sig=sig).data()
            if r:
                counts["implements"] += 1

    # ROUTES_VIA: Commander → Bundle (config routing)
    r = session.run("""
        MATCH (cmd:AgentDef {name: 'commander'}), (b:AgentDef {name: 'bundle'})
        MERGE (cmd)-[:ROUTES_VIA]->(b)
        RETURN 1 AS ok
    """).data()
    if r:
        counts["routes_via"] += 1

    # MANAGES: Bundle → BundleTemplate (Bundle owns all templates)
    session.run("""
        MATCH (b:AgentDef {name: 'bundle'})
        MATCH (bt:BundleTemplate)
        MERGE (b)-[:MANAGES]->(bt)
    """)

    # ACTIVATES_LEAD: BundleTemplate → AgentDef (each template activates its leads)
    for t in BUNDLE_TEMPLATES:
        for lead in t["leads"]:
            r = session.run("""
                MATCH (bt:BundleTemplate {name: $name}), (a:AgentDef {name: $lead})
                MERGE (bt)-[:ACTIVATES_LEAD]->(a)
                RETURN 1 AS ok
            """, name=t["name"], lead=lead).data()
            if r:
                counts["activates_lead"] += 1

    # TaskExecution schema update: ensure model-tracking properties exist as constraints
    # (nodes are created at runtime by Commander — we just define the shape here via a comment)
    # Fields: model_requested, model_used, utility_models_used, model_cost_usd,
    #         escalation_triggered, escalation_reason, difficulty_tier
    # These are written by Commander, read by task-observer. No MERGE needed here.

    return counts


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Orchestration Layer Sync ===\n")
    agents   = scan_agent_defs()
    skills   = scan_skill_defs()
    hooks    = scan_hook_defs()
    patterns = scan_long_term_patterns()
    print(f"Scanned: {len(agents)} AgentDef  {len(skills)} SkillDef  "
          f"{len(hooks)} HookDef  {len(patterns)} LongTermPattern")

    syncer = Neo4jCodebaseSync()
    try:
        with syncer.driver.session() as session:
            na = sync_agent_defs(session, agents)
            removed = dedup_agent_defs(session)
            if removed:
                print(f"  Deduped {removed} spec-only node(s) superseded by platform wrappers")
            ns = sync_skill_defs(session, skills)
            nh = sync_hook_defs(session, hooks)
            np = sync_long_term_patterns(session, patterns)
            nb = sync_bundle_templates(session, BUNDLE_TEMPLATES)
            sync_lesson_schema(session)
            ec = sync_edges(session)

        with syncer.driver.session() as s:
            print(f"\n=== Aura verification ===")
            for label, q in [
                (":AgentDef",        "MATCH (n:AgentDef) RETURN count(n)"),
                (":SkillDef",        "MATCH (n:SkillDef) RETURN count(n)"),
                (":HookDef",         "MATCH (n:HookDef) RETURN count(n)"),
                (":LongTermPattern", "MATCH (n:LongTermPattern) RETURN count(n)"),
                (":BundleTemplate",  "MATCH (n:BundleTemplate) RETURN count(n)"),
                (":Lesson",          "MATCH (n:Lesson) RETURN count(n)"),
                ("LEVEL_UNDER",      "MATCH ()-[r:LEVEL_UNDER]->() RETURN count(r)"),
                ("SPAWNS",           "MATCH ()-[r:SPAWNS]->() RETURN count(r)"),
                ("USES_SKILL",       "MATCH ()-[r:USES_SKILL]->() RETURN count(r)"),
                ("IMPLEMENTS",       "MATCH ()-[r:IMPLEMENTS]->() RETURN count(r)"),
                ("RUNS_SCRIPT",      "MATCH ()-[r:RUNS_SCRIPT]->() RETURN count(r)"),
                ("ROUTES_VIA",       "MATCH ()-[r:ROUTES_VIA]->() RETURN count(r)"),
                ("ACTIVATES_LEAD",   "MATCH ()-[r:ACTIVATES_LEAD]->() RETURN count(r)"),
            ]:
                c = s.run(q + " as c").single()["c"]
                print(f"  {label:<20} {c}")
        print("\n[OK] Orchestration sync complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
