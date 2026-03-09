"""
aura-oracle — Centralised Cypher query registry for all agents.

Usage:
    from .claude.skills.aura-oracle.queries import run_query
    result = run_query("blast_radius", {"sigs": ["src.api.v1.chat.routes.create_message"]})

Growing dictionary: add new queries here as the graph schema expands.
Schema grows with Tasks 6-9 (APIRoute, CeleryTask, EnvVar, Table nodes).
"""

from dotenv import load_dotenv
from neo4j import GraphDatabase
import os, json, sys

load_dotenv()
_driver = None

def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))
        )
    return _driver


# ─────────────────────────────────────────────
# QUERY REGISTRY
# Each entry: name → {cypher, description, params_schema}
# ─────────────────────────────────────────────

QUERIES = {

    # ── ENGINEERING ──────────────────────────────────────────────────────

    "blast_radius": {
        "description": "Functions called by the affected functions (depth 2). Returns file paths + signatures.",
        "params": ["sigs"],  # list of function_signature strings
        "cypher": (
            "UNWIND $sigs AS sig "
            "MATCH (f:Function {function_signature: sig})-[:CALLS*1..2]->(c:Function) "
            "WHERE f.EndDate IS NULL AND c.EndDate IS NULL "
            "RETURN DISTINCT c.function_signature AS fn, c.file_path AS fp"
        ),
        "limit": 30,
    },

    "inbound_callers": {
        "description": "Who calls the given function signatures (depth 1).",
        "params": ["sigs"],
        "cypher": (
            "UNWIND $sigs AS sig "
            "MATCH (caller:Function)-[:CALLS]->(f:Function {function_signature: sig}) "
            "WHERE f.EndDate IS NULL "
            "RETURN DISTINCT caller.function_signature AS fn, caller.file_path AS fp"
        ),
        "limit": 20,
    },

    "full_call_chain": {
        "description": "Full inbound + outbound call chain for a suspect function (forensic).",
        "params": ["suspect"],  # partial string match
        "cypher": (
            "MATCH (c:Function)-[:CALLS]->(f:Function) "
            "WHERE f.function_signature CONTAINS $suspect AND f.EndDate IS NULL "
            "RETURN c.function_signature AS caller, c.file_path AS caller_fp, "
            "       f.function_signature AS callee, f.file_path AS callee_fp"
        ),
        "limit": 30,
    },

    "files_by_module": {
        "description": "All File nodes in a given module/directory prefix.",
        "params": ["prefix"],  # e.g. 'src/billing' or 'frontend/src/app'
        "cypher": (
            "MATCH (f:File) WHERE f.path STARTS WITH $prefix "
            "RETURN f.path, f.module ORDER BY f.path"
        ),
        "limit": 50,
    },

    "functions_in_files": {
        "description": "All Function nodes defined in a list of file paths.",
        "params": ["fps"],  # list of file paths
        "cypher": (
            "MATCH (fn:Function)-[:DEFINED_IN]->(f:File) WHERE f.path IN $fps "
            "AND fn.EndDate IS NULL "
            "RETURN fn.function_signature AS sig, fn.name AS name, f.path AS fp"
        ),
        "limit": 50,
    },

    # ── FORENSIC ─────────────────────────────────────────────────────────

    "open_sentry_issues": {
        "description": "All unresolved Sentry issues, newest first.",
        "params": [],
        "cypher": (
            "MATCH (si:SentryIssue) WHERE si.resolved = false "
            "RETURN si.issue_id, si.title, si.category, si.culprit, si.timestamp "
            "ORDER BY si.timestamp DESC"
        ),
        "limit": 20,
    },

    "sentry_issues_for_files": {
        "description": "Unresolved Sentry issues whose culprit matches any of the given file paths.",
        "params": ["fps"],
        "cypher": (
            "MATCH (si:SentryIssue) WHERE si.resolved = false "
            "AND any(fp IN $fps WHERE si.culprit CONTAINS fp) "
            "RETURN si.issue_id, si.title, si.culprit ORDER BY si.timestamp DESC"
        ),
        "limit": 10,
    },

    "failure_patterns": {
        "description": "LongTermPatterns for forensic/reliability domains.",
        "params": [],
        "cypher": (
            "MATCH (lp:LongTermPattern) WHERE lp.domain IN ['forensic','reliability','bug'] "
            "RETURN lp.description, lp.domain, lp.task_id ORDER BY lp.StartDate DESC"
        ),
        "limit": 10,
    },

    # ── INFRASTRUCTURE ───────────────────────────────────────────────────

    "env_vars": {
        "description": "EnvVar nodes — names + risk tier only. NEVER returns values.",
        "params": [],
        "cypher": (
            "MATCH (e:EnvVar) "
            "RETURN e.name, e.risk_tier, e.file_path ORDER BY e.risk_tier"
        ),
        "limit": 50,
    },

    "celery_tasks": {
        "description": "All CeleryTask nodes with queue and file path.",
        "params": [],
        "cypher": (
            "MATCH (ct:CeleryTask) "
            "RETURN ct.name, ct.queue, ct.file_path"
        ),
        "limit": 30,
    },

    "api_routes": {
        "description": "APIRoute nodes, optionally filtered by file paths.",
        "params": ["fps"],  # can be empty list for all routes
        "cypher": (
            "MATCH (r:APIRoute)-[:DEFINED_IN]->(f:File) "
            "WHERE size($fps) = 0 OR f.path IN $fps "
            "RETURN r.method, r.path, r.handler, f.path AS file"
        ),
        "limit": 50,
    },

    "db_tables": {
        "description": "SQLAlchemy Table nodes and the files that define them.",
        "params": [],
        "cypher": (
            "MATCH (t:Table)-[:DEFINED_IN]->(f:File) "
            "RETURN t.name, t.columns, f.path ORDER BY t.name"
        ),
        "limit": 30,
    },

    # ── PROJECT / BUNDLE ─────────────────────────────────────────────────

    "bundle_templates": {
        "description": "BundleTemplate nodes matching given domains, ranked by quality.",
        "params": ["domains"],  # list of domain strings
        "cypher": (
            "MATCH (bt:BundleTemplate) "
            "WHERE size($domains) = 0 OR any(d IN bt.domains WHERE d IN $domains) "
            "RETURN bt.name, bt.task_type, bt.leads, bt.last_quality_score, bt.trigger_count, bt.is_template "
            "ORDER BY bt.trigger_count DESC, bt.last_quality_score DESC"
        ),
        "limit": 5,
    },

    "active_lessons": {
        "description": "Active Lesson nodes, optionally filtered by Lead name.",
        "params": ["lead"],  # can be empty string for all leads
        "cypher": (
            "MATCH (l:Lesson) WHERE l.status = 'active' "
            "AND ($lead = '' OR exists { MATCH (l)-[:APPLIES_TO]->(a:AgentDef {name: $lead}) }) "
            "RETURN l.pattern, l.recommendation, l.domain, l.confidence "
            "ORDER BY l.confidence DESC"
        ),
        "limit": 10,
    },

    "task_execution_history": {
        "description": "Recent TaskExecution records for learning and routing.",
        "params": [],
        "cypher": (
            "MATCH (te:TaskExecution) "
            "RETURN te.task_type, te.lead_invoked, te.quality_gate_passed, "
            "       te.loop_count, te.skills_used, te.model_used, te.created_at "
            "ORDER BY te.created_at DESC"
        ),
        "limit": 30,
    },

    "long_term_patterns": {
        "description": "LongTermPattern nodes by domain.",
        "params": ["domains"],  # list, or empty for all
        "cypher": (
            "MATCH (lp:LongTermPattern) "
            "WHERE size($domains) = 0 OR lp.domain IN $domains "
            "RETURN lp.description, lp.domain, lp.task_id ORDER BY lp.StartDate DESC"
        ),
        "limit": 10,
    },

    # ── DESIGN ───────────────────────────────────────────────────────────

    "frontend_files": {
        "description": "Frontend File nodes matching keyword list.",
        "params": ["keywords"],  # list of strings to match in path
        "cypher": (
            "MATCH (f:File) WHERE f.path STARTS WITH 'frontend/' "
            "AND (size($keywords) = 0 OR any(kw IN $keywords WHERE f.path CONTAINS kw)) "
            "RETURN f.path, f.module ORDER BY f.path"
        ),
        "limit": 30,
    },

    "skill_defs": {
        "description": "SkillDef nodes, optionally filtered by platform or tier.",
        "params": ["platform", "tier"],  # can be empty string for any
        "cypher": (
            "MATCH (s:SkillDef) "
            "WHERE ($platform = '' OR $platform IN s.installed_at) "
            "AND ($tier = 0 OR s.tier = $tier) "
            "RETURN s.name, s.skill_type, s.tier, s.installed_at, s.quality_score "
            "ORDER BY s.tier, s.name"
        ),
        "limit": 50,
    },

    "agent_defs": {
        "description": "AgentDef nodes — all registered agents.",
        "params": [],
        "cypher": (
            "MATCH (a:AgentDef) "
            "RETURN a.name, a.platform, a.role, a.letta_agent_id "
            "ORDER BY a.name"
        ),
        "limit": 30,
    },
}


def run_query(name: str, params: dict = None, limit: int = None) -> dict:
    """Execute a named query and return results as a dict."""
    if name not in QUERIES:
        return {"error": f"Unknown query: '{name}'. Available: {sorted(QUERIES.keys())}"}

    q = QUERIES[name]
    params = params or {}
    cypher = q["cypher"]
    effective_limit = limit or q["limit"]
    cypher_with_limit = f"{cypher} LIMIT {effective_limit}"

    try:
        driver = _get_driver()
        with driver.session() as s:
            result = s.run(cypher_with_limit, **params).data()
        return {"query": name, "count": len(result), "data": result}
    except Exception as e:
        return {"query": name, "error": str(e), "data": []}


def list_queries() -> list:
    """Return all available query names and descriptions."""
    return [{"name": k, "description": v["description"], "params": v["params"]}
            for k, v in QUERIES.items()]


if __name__ == "__main__":
    # CLI: python queries.py <query_name> [json_params]
    if len(sys.argv) < 2:
        print(json.dumps(list_queries(), indent=2))
    else:
        name = sys.argv[1]
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        print(json.dumps(run_query(name, params), indent=2))
