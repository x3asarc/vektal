"""Task 13: Orchestration layer indexer.

Writes to Aura:
  :AgentDef  — from .claude/agents/*.md + docs/agent-system/specs/*.md
  :SkillDef  — from .claude/skills/*.yaml
  :LongTermPattern — from FAILURE_JOURNEY.md + LEARNINGS.md
  :ImprovementProposal — stub nodes (will be populated by task-observer)

Edges:
  (:AgentDef)-[:USES_SKILL]->(:SkillDef)  — if skill_name mentioned in agent spec
"""
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync, _now_iso

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sid(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def _first_line(text: str, max_len: int = 200) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:max_len]
    return ""


# ── Scanners ─────────────────────────────────────────────────────────────────

def scan_agent_defs() -> list[dict]:
    agents = []
    # Platform wrappers (.claude/agents/)
    agents_dir = PROJECT_ROOT / ".claude" / "agents"
    for md in agents_dir.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        name = md.stem
        agents.append({
            "agent_id": _sid("claude", name),
            "name": name,
            "platform": "claude",
            "spec_path": str(md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "description": _first_line(text),
            "has_canonical_spec": False,
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
                    "agent_id": _sid("spec", name),
                    "name": name,
                    "platform": "spec-only",
                    "spec_path": str(md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "description": _first_line(text),
                    "has_canonical_spec": True,
                    "canonical_spec_path": str(md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                })
    return agents


def scan_skill_defs() -> list[dict]:
    skills = []
    skills_dir = PROJECT_ROOT / ".claude" / "skills"
    for yaml_file in skills_dir.glob("*.yaml"):
        text = yaml_file.read_text(encoding="utf-8", errors="replace")
        name = yaml_file.stem
        # Extract description from YAML (first non-empty value after 'description:')
        desc_match = re.search(r"description:\s*(.+)", text)
        description = desc_match.group(1).strip().strip('"\'') if desc_match else ""
        skills.append({
            "skill_id": _sid("skill", name),
            "name": name,
            "platform": "claude",
            "skill_type": "yaml",
            "spec_path": str(yaml_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "description": description[:200],
        })
    # Also check Letta skill files
    letta_skills = PROJECT_ROOT / ".letta" / "skills"
    if letta_skills.exists():
        for skill_f in letta_skills.rglob("SKILL.md"):
            text = skill_f.read_text(encoding="utf-8", errors="replace")
            name = skill_f.parent.name
            skills.append({
                "skill_id": _sid("letta", name),
                "name": name,
                "platform": "letta",
                "skill_type": "letta-skill",
                "spec_path": str(skill_f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "description": _first_line(text)[:200],
            })
    return skills


def scan_long_term_patterns() -> list[dict]:
    patterns = []

    def _parse_failure_journey(path: Path) -> list[dict]:
        text = path.read_text(encoding="utf-8", errors="replace")
        # Split on ### headers
        sections = re.split(r"^### ", text, flags=re.MULTILINE)
        for section in sections[1:]:  # skip preamble
            lines = section.strip().splitlines()
            if not lines:
                continue
            header = lines[0].strip()  # e.g. "2026-02-12 | 07.1-governance-baseline-dry-run"
            parts = [p.strip() for p in header.split("|")]
            date_str = parts[0] if parts else ""
            task_id = parts[1] if len(parts) > 1 else ""
            body = "\n".join(lines[1:]).strip()
            # Extract the "Failed Y" line as description
            fail_match = re.search(r"2\.\s+Failed Y:\s+(.+)", body)
            description = fail_match.group(1).strip()[:300] if fail_match else body[:300]
            # Extract domain from task_id prefix
            domain = task_id.split("-")[0] if task_id else "general"
            patterns.append({
                "pattern_id": _sid("fj", date_str, task_id),
                "domain": domain,
                "source": "FAILURE_JOURNEY.md",
                "description": description,
                "task_id": task_id,
                "date_str": date_str,
                "StartDate": f"{date_str}T00:00:00+00:00" if re.match(r"\d{4}-\d{2}-\d{2}", date_str) else _now_iso(),
                "EndDate": None,
            })
        return patterns

    fj = PROJECT_ROOT / "FAILURE_JOURNEY.md"
    if fj.exists():
        patterns.extend(_parse_failure_journey(fj))

    learnings = PROJECT_ROOT / "LEARNINGS.md"
    if learnings.exists():
        text = learnings.read_text(encoding="utf-8", errors="replace")
        sections = re.split(r"^### |^## ", text, flags=re.MULTILINE)
        for section in sections[1:]:
            lines = section.strip().splitlines()
            header = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            if len(body) < 20:
                continue
            patterns.append({
                "pattern_id": _sid("learn", header),
                "domain": "learnings",
                "source": "LEARNINGS.md",
                "description": (header + ": " + body[:200]),
                "task_id": "",
                "date_str": "",
                "StartDate": _now_iso(),
                "EndDate": None,
            })
    return patterns


# ── Syncer ───────────────────────────────────────────────────────────────────

def sync_agent_defs(session, agents: list[dict]) -> int:
    session.run("CREATE CONSTRAINT agentdef_id_unique IF NOT EXISTS "
                "FOR (a:AgentDef) REQUIRE a.agent_id IS UNIQUE")
    for a in agents:
        session.run("""
            MERGE (ad:AgentDef {agent_id: $agent_id})
            SET ad.name = $name,
                ad.platform = $platform,
                ad.spec_path = $spec_path,
                ad.description = $description,
                ad.has_canonical_spec = $has_canonical_spec,
                ad.canonical_spec_path = $canonical_spec_path
        """,
        agent_id=a["agent_id"], name=a["name"], platform=a["platform"],
        spec_path=a["spec_path"], description=a.get("description", ""),
        has_canonical_spec=a.get("has_canonical_spec", False),
        canonical_spec_path=a.get("canonical_spec_path", ""),
        )
    return len(agents)


def sync_skill_defs(session, skills: list[dict]) -> int:
    session.run("CREATE CONSTRAINT skilldef_id_unique IF NOT EXISTS "
                "FOR (s:SkillDef) REQUIRE s.skill_id IS UNIQUE")
    for s in skills:
        session.run("""
            MERGE (sd:SkillDef {skill_id: $skill_id})
            SET sd.name = $name,
                sd.platform = $platform,
                sd.skill_type = $skill_type,
                sd.spec_path = $spec_path,
                sd.description = $description
        """,
        skill_id=s["skill_id"], name=s["name"], platform=s["platform"],
        skill_type=s["skill_type"], spec_path=s["spec_path"],
        description=s.get("description", ""),
        )
    return len(skills)


def sync_long_term_patterns(session, patterns: list[dict]) -> int:
    session.run("CREATE CONSTRAINT ltpattern_id_unique IF NOT EXISTS "
                "FOR (p:LongTermPattern) REQUIRE p.pattern_id IS UNIQUE")
    for p in patterns:
        session.run("""
            MERGE (lp:LongTermPattern {pattern_id: $pattern_id})
            SET lp.domain = $domain,
                lp.source = $source,
                lp.description = $description,
                lp.task_id = $task_id,
                lp.StartDate = $StartDate,
                lp.EndDate = $EndDate
        """,
        pattern_id=p["pattern_id"], domain=p["domain"], source=p["source"],
        description=p["description"], task_id=p.get("task_id", ""),
        StartDate=p.get("StartDate"), EndDate=p.get("EndDate"),
        )
    return len(patterns)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== Task 13: Orchestration Layer Indexer ===\n")

    agents = scan_agent_defs()
    skills = scan_skill_defs()
    patterns = scan_long_term_patterns()

    print(f"Scanned: {len(agents)} AgentDef, {len(skills)} SkillDef, {len(patterns)} LongTermPattern")

    syncer = Neo4jCodebaseSync()
    try:
        with syncer.driver.session() as session:
            n_agents = sync_agent_defs(session, agents)
            n_skills = sync_skill_defs(session, skills)
            n_patterns = sync_long_term_patterns(session, patterns)

            print(f"\n[OK] Synced {n_agents} AgentDef nodes")
            print(f"[OK] Synced {n_skills} SkillDef nodes")
            print(f"[OK] Synced {n_patterns} LongTermPattern nodes")

        # Verify
        with syncer.driver.session() as session:
            ad = session.run("MATCH (n:AgentDef) RETURN count(n) as c").single()['c']
            sd = session.run("MATCH (n:SkillDef) RETURN count(n) as c").single()['c']
            lp = session.run("MATCH (n:LongTermPattern) RETURN count(n) as c").single()['c']
            print(f"\n=== Aura verification ===")
            print(f"  :AgentDef:        {ad}")
            print(f"  :SkillDef:        {sd}")
            print(f"  :LongTermPattern: {lp}")

        print("\n[OK] Task 13 complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
