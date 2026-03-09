"""
aura-oracle — Graph Query Composition Engine

Agents call ask(domain, question, context) instead of writing raw Cypher.
Add new BLOCKS as the graph schema grows. Update DOMAIN_PROFILES to wire them in.
"""

from dotenv import load_dotenv
from neo4j import GraphDatabase
import os, json, sys, argparse

load_dotenv()
_driver = None

def _get_driver():
    global _driver
    if _driver is None:
        uri  = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        pwd  = os.getenv("NEO4J_PASSWORD")
        if not uri or not pwd:
            raise RuntimeError("NEO4J_URI / NEO4J_PASSWORD not set. Check .env.")
        _driver = GraphDatabase.driver(uri, auth=(user, pwd))
    return _driver


# ══════════════════════════════════════════════════════════════════════════
#  BUILDING BLOCKS
#  Each block is a self-contained Cypher fragment + metadata.
#  Add new blocks here as graph schema grows (Tasks 6-9).
#  schema_task = None means always available.
# ══════════════════════════════════════════════════════════════════════════

BLOCKS = {

    # ── WHO: Ownership & Callers ──────────────────────────────────────────

    "calls_inbound": {
        "description": "WHO calls the given functions (depth 1 callers).",
        "question": "WHO",
        "params_required": ["sigs"],
        "cypher": (
            "UNWIND $sigs AS sig "
            "MATCH (caller:Function)-[:CALLS]->(f:Function) "
            "WHERE f.function_signature CONTAINS sig AND f.EndDate IS NULL "
            "RETURN DISTINCT caller.function_signature AS caller_sig, "
            "       caller.file_path AS caller_fp, sig AS called"
        ),
        "limit": 30,
        "schema_task": None,
    },

    "calls_inbound_deep": {
        "description": "WHO are the ancestors of the given functions (depth 3 — full ownership chain).",
        "question": "WHO",
        "params_required": ["sigs"],
        "cypher": (
            "UNWIND $sigs AS sig "
            "MATCH path = (ancestor:Function)-[:CALLS*1..3]->(f:Function) "
            "WHERE f.function_signature CONTAINS sig AND f.EndDate IS NULL "
            "RETURN DISTINCT ancestor.function_signature AS ancestor_sig, "
            "       ancestor.file_path AS ancestor_fp, length(path) AS depth"
        ),
        "limit": 30,
        "schema_task": None,
    },

    "file_owners": {
        "description": "WHO imports a given file (reverse import graph).",
        "question": "WHO",
        "params_required": ["fps"],
        "cypher": (
            "UNWIND $fps AS fp "
            "MATCH (importer:File)-[:IMPORTS]->(target:File {path: fp}) "
            "RETURN DISTINCT importer.path AS importer, fp AS imported"
        ),
        "limit": 20,
        "schema_task": None,
    },

    # ── WHAT: Nodes & Entities ────────────────────────────────────────────

    "function_nodes": {
        "description": "WHAT functions exist in the given file paths (active only).",
        "question": "WHAT",
        "params_required": ["fps"],
        "cypher": (
            "MATCH (fn:Function)-[:DEFINED_IN]->(f:File) "
            "WHERE f.path IN $fps AND fn.EndDate IS NULL "
            "RETURN fn.function_signature AS sig, fn.name AS name, f.path AS fp"
        ),
        "limit": 50,
        "schema_task": None,
    },

    "class_nodes": {
        "description": "WHAT classes exist in the given file paths.",
        "question": "WHAT",
        "params_required": ["fps"],
        "cypher": (
            "MATCH (c:Class)-[:DEFINED_IN]->(f:File) "
            "WHERE f.path IN $fps AND c.EndDate IS NULL "
            "RETURN c.name AS class_name, f.path AS fp"
        ),
        "limit": 30,
        "schema_task": None,
    },

    "api_route_nodes": {
        "description": "WHAT API routes exist, optionally filtered by file paths.",
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (r:APIRoute)-[:DEFINED_IN]->(f:File) "
            "WHERE size($fps) = 0 OR f.path IN $fps "
            "RETURN r.method AS method, r.path AS route, r.handler AS handler, f.path AS fp"
        ),
        "limit": 50,
        "schema_task": 6,
    },

    "celery_task_nodes": {
        "description": "WHAT Celery tasks exist and on which queues.",
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (ct:CeleryTask) "
            "RETURN ct.name AS task, ct.queue AS queue, ct.file_path AS fp"
        ),
        "limit": 30,
        "schema_task": 6,
    },

    "env_var_nodes": {
        "description": "WHAT environment variables exist — names + risk tier ONLY. Values are NEVER returned.",
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (e:EnvVar) "
            "RETURN e.name AS name, e.risk_tier AS risk_tier, e.file_path AS fp "
            "ORDER BY e.risk_tier DESC, e.name"
        ),
        "limit": 60,
        "schema_task": 7,
    },

    "table_nodes": {
        "description": "WHAT database tables exist and where they are defined.",
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (t:Table)-[:DEFINED_IN]->(f:File) "
            "RETURN t.name AS table_name, t.columns AS columns, f.path AS fp "
            "ORDER BY t.name"
        ),
        "limit": 30,
        "schema_task": 8,
    },

    "skill_defs": {
        "description": "WHAT skills are installed and on which platforms.",
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (s:SkillDef) "
            "RETURN s.name AS name, s.skill_type AS type, s.tier AS tier, "
            "       s.installed_at AS platforms, s.quality_score AS quality "
            "ORDER BY s.tier, s.name"
        ),
        "limit": 50,
        "schema_task": None,
    },

    "agent_defs": {
        "description": "WHAT agents are registered in the system.",
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (a:AgentDef) "
            "RETURN a.name AS name, a.platform AS platform, a.role AS role, "
            "       a.letta_agent_id AS letta_id ORDER BY a.name"
        ),
        "limit": 30,
        "schema_task": None,
    },

    "sentry_unresolved": {
        "description": "WHAT open Sentry issues exist (unresolved), newest first.",
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (si:SentryIssue) WHERE si.resolved = false "
            "RETURN si.issue_id AS id, si.title AS title, si.category AS category, "
            "       si.culprit AS culprit, si.timestamp AS ts "
            "ORDER BY si.timestamp DESC"
        ),
        "limit": 20,
        "schema_task": None,
    },

    "sentry_for_files": {
        "description": "WHAT Sentry issues are associated with the given file paths.",
        "question": "WHAT",
        "params_required": ["fps"],
        "cypher": (
            "MATCH (si:SentryIssue) WHERE si.resolved = false "
            "AND any(fp IN $fps WHERE si.culprit CONTAINS fp) "
            "RETURN si.issue_id AS id, si.title AS title, si.culprit AS culprit "
            "ORDER BY si.timestamp DESC"
        ),
        "limit": 10,
        "schema_task": None,
    },

    # ── WHERE: Location & Scope ───────────────────────────────────────────

    "files_by_prefix": {
        "description": "WHERE are the files in a given path prefix.",
        "question": "WHERE",
        "params_required": ["prefix"],
        "cypher": (
            "MATCH (f:File) WHERE f.path STARTS WITH $prefix "
            "RETURN f.path AS path, f.module AS module ORDER BY f.path"
        ),
        "limit": 50,
        "schema_task": None,
    },

    "files_by_keywords": {
        "description": "WHERE are files matching any of the given keywords in their path.",
        "question": "WHERE",
        "params_required": ["keywords"],
        "cypher": (
            "MATCH (f:File) "
            "WHERE any(kw IN $keywords WHERE f.path CONTAINS kw) "
            "RETURN f.path AS path, f.module AS module ORDER BY f.path"
        ),
        "limit": 30,
        "schema_task": None,
    },

    "blast_radius": {
        "description": "WHERE does a change propagate to — outbound call chain depth 2.",
        "question": "WHERE",
        "params_required": ["sigs"],
        "cypher": (
            "UNWIND $sigs AS sig "
            "MATCH (f:Function {function_signature: sig})-[:CALLS*1..2]->(c:Function) "
            "WHERE f.EndDate IS NULL AND c.EndDate IS NULL "
            "RETURN DISTINCT c.function_signature AS fn, c.file_path AS fp"
        ),
        "limit": 30,
        "schema_task": None,
    },

    "import_chain": {
        "description": "WHERE does a file's imports reach (transitive import graph depth 2).",
        "question": "WHERE",
        "params_required": ["fps"],
        "cypher": (
            "UNWIND $fps AS fp "
            "MATCH (f:File {path: fp})-[:IMPORTS*1..2]->(dep:File) "
            "RETURN DISTINCT fp AS source, dep.path AS dependency"
        ),
        "limit": 30,
        "schema_task": None,
    },

    # ── WHY: Intent & Rationale ───────────────────────────────────────────

    "code_intent_episodes": {
        "description": "WHY was this code written — CODE_INTENT episodes linked to functions.",
        "question": "WHY",
        "params_required": ["sigs"],
        "cypher": (
            "UNWIND $sigs AS sig "
            "MATCH (ep:Episode)-[:REFERS_TO]->(f:Function) "
            "WHERE f.function_signature CONTAINS sig "
            "AND ep.episode_type = 'CODE_INTENT' "
            "RETURN ep.content AS intent, ep.created_at AS ts, f.function_signature AS fn"
        ),
        "limit": 10,
        "schema_task": 11,
    },

    "long_term_patterns": {
        "description": "WHY decisions were made — LongTermPattern nodes by domain.",
        "question": "WHY",
        "params_required": ["domains"],
        "cypher": (
            "MATCH (lp:LongTermPattern) "
            "WHERE size($domains) = 0 OR lp.domain IN $domains "
            "RETURN lp.description AS description, lp.domain AS domain, lp.task_id AS task_id "
            "ORDER BY lp.StartDate DESC"
        ),
        "limit": 10,
        "schema_task": None,
    },

    "planning_docs": {
        "description": "WHY — PlanningDoc nodes (phase plans, summaries, decision records).",
        "question": "WHY",
        "params_required": ["keywords"],
        "cypher": (
            "MATCH (pd:PlanningDoc) "
            "WHERE size($keywords) = 0 OR any(kw IN $keywords WHERE pd.title CONTAINS kw) "
            "RETURN pd.title AS title, pd.path AS path, pd.doc_type AS type "
            "ORDER BY pd.path"
        ),
        "limit": 20,
        "schema_task": None,
    },

    "active_lessons": {
        "description": "WHY patterns to avoid — active Lessons inferred from failures.",
        "question": "WHY",
        "params_required": ["lead"],
        "cypher": (
            "MATCH (l:Lesson) WHERE l.status = 'active' "
            "AND ($lead = '' OR exists { MATCH (l)-[:APPLIES_TO]->(a:AgentDef {name: $lead}) }) "
            "RETURN l.pattern AS pattern, l.recommendation AS rec, "
            "       l.domain AS domain, l.confidence AS confidence "
            "ORDER BY l.confidence DESC"
        ),
        "limit": 10,
        "schema_task": None,
    },

    # ── WHEN: Temporal & History ──────────────────────────────────────────

    "task_execution_history": {
        "description": "WHEN and how tasks were executed — quality, loop counts, models used.",
        "question": "WHEN",
        "params_required": [],
        "cypher": (
            "MATCH (te:TaskExecution) "
            "RETURN te.task_type AS type, te.lead_invoked AS lead, "
            "       te.quality_gate_passed AS passed, te.loop_count AS loops, "
            "       te.skills_used AS skills, te.model_used AS model, "
            "       te.created_at AS ts ORDER BY te.created_at DESC"
        ),
        "limit": 30,
        "schema_task": None,
    },

    "failure_timeline": {
        "description": "WHEN did failures occur — Sentry issues + failure patterns chronologically.",
        "question": "WHEN",
        "params_required": [],
        "cypher": (
            "MATCH (si:SentryIssue) "
            "RETURN si.issue_id AS id, si.title AS title, si.culprit AS culprit, "
            "       si.timestamp AS ts, si.resolved AS resolved "
            "ORDER BY si.timestamp DESC"
        ),
        "limit": 20,
        "schema_task": None,
    },

    "bundle_template_history": {
        "description": "WHEN were BundleTemplates last used and with what quality score.",
        "question": "WHEN",
        "params_required": ["domains"],
        "cypher": (
            "MATCH (bt:BundleTemplate) "
            "WHERE size($domains) = 0 OR any(d IN bt.domains WHERE d IN $domains) "
            "RETURN bt.name AS name, bt.task_type AS type, bt.trigger_count AS runs, "
            "       bt.last_quality_score AS quality, bt.is_template AS promoted "
            "ORDER BY bt.trigger_count DESC, bt.last_quality_score DESC"
        ),
        "limit": 10,
        "schema_task": None,
    },

    # ── HOW: Data Flow & Dependency Chains ────────────────────────────────

    "full_call_chain": {
        "description": "HOW does execution flow — full inbound + outbound chain for a suspect.",
        "question": "HOW",
        "params_required": ["suspect"],
        "cypher": (
            "MATCH (f:Function) WHERE f.function_signature CONTAINS $suspect "
            "AND f.EndDate IS NULL "
            "OPTIONAL MATCH (caller:Function)-[:CALLS]->(f) "
            "OPTIONAL MATCH (f)-[:CALLS]->(callee:Function) WHERE callee.EndDate IS NULL "
            "RETURN f.function_signature AS fn, f.file_path AS fp, "
            "       collect(DISTINCT caller.function_signature) AS callers, "
            "       collect(DISTINCT callee.function_signature) AS callees"
        ),
        "limit": 20,
        "schema_task": None,
    },

    "data_access_chain": {
        "description": "HOW does a module access the database — Function→ACCESSES→Table chain.",
        "question": "HOW",
        "params_required": ["fps"],
        "cypher": (
            "MATCH (fn:Function)-[:ACCESSES]->(t:Table) "
            "WHERE fn.file_path IN $fps AND fn.EndDate IS NULL "
            "RETURN fn.function_signature AS fn, fn.file_path AS fp, "
            "       t.name AS table_name, t.columns AS columns"
        ),
        "limit": 30,
        "schema_task": 8,
    },

    "route_to_function_chain": {
        "description": "HOW does an API route connect to its handler function.",
        "question": "HOW",
        "params_required": ["route_path"],
        "cypher": (
            "MATCH (r:APIRoute)-[:DEFINED_IN]->(f:File) "
            "WHERE r.path CONTAINS $route_path "
            "OPTIONAL MATCH (fn:Function {function_signature: r.handler})-[:DEFINED_IN]->(f) "
            "RETURN r.method AS method, r.path AS route, r.handler AS handler, "
            "       fn.function_signature AS fn_sig, f.path AS fp"
        ),
        "limit": 10,
        "schema_task": 6,
    },

    # ── CROSS-DOMAIN (Gemini recommendation — Project Lead + Engineering Lead) ──

    "cross_domain_impact": {
        "description": (
            "HOW does a change in one domain silently break another — "
            "detects IMPORTS and CALLS relationships that cross folder/domain boundaries. "
            "e.g. frontend/ → src/api/, src/config/ → src/billing/, src/ui/ → src/core/. "
            "This is the #1 source of hidden regressions in multi-domain platforms."
        ),
        "question": "HOW",
        "params_required": ["fps"],  # files being changed
        "cypher": (
            # Domain boundary map: anything crossing these prefixes is a cross-domain edge
            "WITH ["
            "  ['frontend/', 'src/'],"
            "  ['src/api/', 'src/core/'],"
            "  ['src/api/', 'src/tasks/'],"
            "  ['src/billing/', 'src/core/'],"
            "  ['src/billing/', 'src/models/'],"
            "  ['src/graph/', 'src/api/'],"
            "  ['src/config/', 'src/billing/'],"
            "  ['src/config/', 'src/api/']"
            "] AS boundary_pairs "
            "UNWIND $fps AS changed_fp "
            "MATCH (changed:File {path: changed_fp}) "
            "MATCH (changed)-[:IMPORTS]->(dep:File) "
            "WHERE any(pair IN boundary_pairs WHERE "
            "  (changed_fp STARTS WITH pair[0] AND dep.path STARTS WITH pair[1]) OR "
            "  (changed_fp STARTS WITH pair[1] AND dep.path STARTS WITH pair[0])) "
            "RETURN changed_fp AS source_file, dep.path AS cross_domain_dep, "
            "       'IMPORTS' AS relationship_type "
            "UNION "
            "UNWIND $fps AS changed_fp "
            "MATCH (fn:Function)-[:DEFINED_IN]->(f:File {path: changed_fp}) "
            "MATCH (fn)-[:CALLS]->(callee:Function)-[:DEFINED_IN]->(callee_f:File) "
            "WHERE fn.EndDate IS NULL AND callee.EndDate IS NULL "
            "AND any(pair IN ["
            "  ['frontend/', 'src/'],"
            "  ['src/api/', 'src/core/'],"
            "  ['src/billing/', 'src/core/'],"
            "  ['src/graph/', 'src/api/']"
            "] WHERE "
            "  (changed_fp STARTS WITH pair[0] AND callee_f.path STARTS WITH pair[1]) OR "
            "  (changed_fp STARTS WITH pair[1] AND callee_f.path STARTS WITH pair[0])) "
            "RETURN changed_fp AS source_file, callee_f.path AS cross_domain_dep, "
            "       'CALLS' AS relationship_type"
        ),
        "limit": 40,
        "schema_task": None,
    },

    "cross_domain_env_coupling": {
        "description": (
            "WHAT EnvVar nodes are consumed across domain boundaries — "
            "detects when an Infrastructure change (new/removed EnvVar) "
            "silently breaks Engineering functions in a different domain. "
            "e.g. a billing EnvVar used in a graph function."
        ),
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (e:EnvVar)<-[:USES]-(fn:Function)-[:DEFINED_IN]->(f:File) "
            "WHERE e.EndDate IS NULL AND fn.EndDate IS NULL "
            "WITH e.name AS env, e.risk_tier AS risk, e.file_path AS defined_in, "
            "     collect(DISTINCT f.path) AS used_in_files "
            "WHERE size(used_in_files) > 0 "
            "WITH env, risk, defined_in, used_in_files, "
            "     [fp IN used_in_files WHERE "
            "       NOT (defined_in IS NOT NULL AND fp STARTS WITH split(defined_in,'/')[0])] "
            "     AS cross_domain_usages "
            "WHERE size(cross_domain_usages) > 0 "
            "RETURN env, risk, defined_in, cross_domain_usages "
            "ORDER BY risk DESC, env"
        ),
        "limit": 30,
        "schema_task": 7,  # requires EnvVar nodes (Task 7) + USES edges
    },

    "cross_domain_route_coupling": {
        "description": (
            "WHAT API routes are called by unexpected domains — "
            "detects hidden coupling where frontend components call backend routes "
            "that are also called by background workers, creating race conditions "
            "or shared state dependencies. Flags API surface area shared across >1 domain."
        ),
        "question": "WHAT",
        "params_required": [],
        "cypher": (
            "MATCH (r:APIRoute)-[:DEFINED_IN]->(rf:File) "
            "MATCH (caller:Function)-[:CALLS_ROUTE]->(r) "
            "MATCH (caller)-[:DEFINED_IN]->(cf:File) "
            "WHERE rf.EndDate IS NULL "
            "WITH r.method AS method, r.path AS route, rf.path AS route_file, "
            "     collect(DISTINCT cf.path) AS caller_files, "
            "     collect(DISTINCT caller.function_signature) AS callers "
            "WITH method, route, route_file, caller_files, callers, "
            "     [fp IN caller_files WHERE NOT fp STARTS WITH split(route_file,'/')[0]] "
            "     AS cross_domain_callers "
            "WHERE size(cross_domain_callers) > 0 "
            "RETURN method, route, route_file, cross_domain_callers, callers"
        ),
        "limit": 20,
        "schema_task": 6,  # requires APIRoute nodes (Task 6) + CALLS_ROUTE edges
    },

}


# ══════════════════════════════════════════════════════════════════════════
#  DOMAIN PROFILES
#  Maps each agent domain to the W-questions it should run by default.
#  Add new blocks to these lists — agents get them for free.
# ══════════════════════════════════════════════════════════════════════════

DOMAIN_PROFILES = {
    "engineering": {
        "WHO":  ["calls_inbound", "file_owners"],
        "WHAT": ["function_nodes", "api_route_nodes", "sentry_for_files"],
        "WHERE":["blast_radius", "import_chain"],
        "WHY":  ["long_term_patterns", "active_lessons", "code_intent_episodes"],
        "WHEN": ["task_execution_history", "failure_timeline"],
        # cross_domain_impact: catches silent breaks when engineering touches shared boundaries
        "HOW":  ["full_call_chain", "data_access_chain", "route_to_function_chain", "cross_domain_impact"],
    },
    "design": {
        "WHO":  ["file_owners"],
        "WHAT": ["function_nodes", "skill_defs"],
        "WHERE":["files_by_prefix", "files_by_keywords"],
        "WHY":  ["long_term_patterns", "active_lessons", "planning_docs"],
        "WHEN": ["task_execution_history"],
        # cross_domain_impact: frontend changes that CALL or IMPORT backend utilities
        "HOW":  ["full_call_chain", "cross_domain_impact"],
    },
    "forensic": {
        "WHO":  ["calls_inbound_deep", "file_owners"],
        "WHAT": ["sentry_unresolved", "sentry_for_files", "function_nodes"],
        "WHERE":["blast_radius", "files_by_keywords", "import_chain"],
        "WHY":  ["long_term_patterns", "active_lessons", "code_intent_episodes"],
        "WHEN": ["failure_timeline", "task_execution_history"],
        # cross_domain_impact: regressions almost always originate at domain boundaries
        "HOW":  ["full_call_chain", "data_access_chain", "cross_domain_impact"],
    },
    "infrastructure": {
        "WHO":  ["file_owners"],
        # cross_domain_env_coupling: infra changes (EnvVars) that silently break engineering
        "WHAT": ["env_var_nodes", "celery_task_nodes", "table_nodes", "api_route_nodes",
                 "cross_domain_env_coupling"],
        "WHERE":["files_by_prefix", "files_by_keywords"],
        "WHY":  ["long_term_patterns", "active_lessons", "planning_docs"],
        "WHEN": ["failure_timeline", "task_execution_history"],
        "HOW":  ["data_access_chain", "route_to_function_chain", "cross_domain_impact"],
    },
    "project": {
        "WHO":  ["agent_defs"],
        # Project Lead gets ALL cross-domain blocks — it owns the full picture
        "WHAT": ["skill_defs", "agent_defs", "cross_domain_env_coupling",
                 "cross_domain_route_coupling"],
        "WHERE":["files_by_prefix", "blast_radius"],
        "WHY":  ["long_term_patterns", "active_lessons", "planning_docs"],
        "WHEN": ["task_execution_history", "bundle_template_history"],
        # cross_domain_impact is the Project Lead's primary collision detector
        "HOW":  ["full_call_chain", "cross_domain_impact", "cross_domain_route_coupling"],
    },
    "bundle": {
        "WHO":  ["agent_defs"],
        "WHAT": ["skill_defs", "agent_defs"],
        "WHERE":[],
        "WHY":  ["active_lessons"],
        "WHEN": ["bundle_template_history", "task_execution_history"],
        "HOW":  [],
    },
}

ALL_QUESTIONS = ["WHO", "WHAT", "WHERE", "WHY", "WHEN", "HOW"]


# ══════════════════════════════════════════════════════════════════════════
#  COMPOSER
# ══════════════════════════════════════════════════════════════════════════

def _run_block(name: str, ctx: dict) -> dict:
    """Execute a single block and return {block, count, data} or {block, skipped}."""
    block = BLOCKS.get(name)
    if not block:
        return {"block": name, "error": "unknown block"}

    # Check schema availability
    task_req = block.get("schema_task")
    if task_req:
        return {"block": name, "skipped": f"requires graph sprint Task {task_req}", "data": []}

    # Build params — use context values matching required param names
    params = {}
    for p in block.get("params_required", []):
        val = ctx.get(p)
        if val is None:
            # Use safe defaults for optional params
            defaults = {"sigs": [], "fps": [], "domains": [], "keywords": [],
                        "suspect": "", "prefix": "", "lead": "", "route_path": ""}
            val = defaults.get(p, "")
        params[p] = val

    cypher = block["cypher"] + f" LIMIT {block['limit']}"

    try:
        driver = _get_driver()
        with driver.session() as s:
            data = s.run(cypher, **params).data()
        return {"block": name, "question": block["question"],
                "description": block["description"], "count": len(data), "data": data}
    except Exception as e:
        return {"block": name, "error": str(e), "data": []}


def ask(domain: str = None, question: str = None,
        blocks: list = None, context: dict = None) -> dict:
    """
    Main entry point for all agents.

    Args:
        domain:   Agent domain — engineering / design / forensic / infrastructure / project / bundle
        question: Single W-question — WHO / WHAT / WHERE / WHY / WHEN / HOW
                  If None, runs all W-questions for the domain
        blocks:   Explicit block list (overrides domain + question)
        context:  Dict with any of: sigs, fps, prefix, keywords, suspect, domains,
                  lead, route_path, task (free-text description)
    """
    context = context or {}
    results = {}

    if blocks:
        # Explicit block execution
        for b in blocks:
            results[b] = _run_block(b, context)

    elif domain:
        profile = DOMAIN_PROFILES.get(domain)
        if not profile:
            return {"error": f"Unknown domain '{domain}'. Use: {list(DOMAIN_PROFILES.keys())}"}

        questions_to_run = [question] if question else ALL_QUESTIONS
        for q in questions_to_run:
            block_names = profile.get(q, [])
            results[q] = {}
            for b in block_names:
                results[q][b] = _run_block(b, context)

    else:
        return {"error": "Provide domain or blocks. Run with --list to see options."}

    return {"domain": domain, "question": question, "context_keys": list(context.keys()), "results": results}


def list_blocks() -> list:
    return [{"name": k, "question": v["question"], "description": v["description"],
             "params": v.get("params_required", []),
             "schema_task": v.get("schema_task")}
            for k, v in BLOCKS.items()]


def list_domains() -> dict:
    return {d: {q: blocks for q, blocks in profile.items()}
            for d, profile in DOMAIN_PROFILES.items()}


# ══════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="aura-oracle — graph query composition engine")
    parser.add_argument("--domain",   help="Agent domain (engineering/design/forensic/infrastructure/project/bundle)")
    parser.add_argument("--question", help="Single W-question (WHO/WHAT/WHERE/WHY/WHEN/HOW)")
    parser.add_argument("--blocks",   help="Comma-separated explicit block names")
    parser.add_argument("--context",  help="JSON context dict", default="{}")
    parser.add_argument("--list",     action="store_true", help="List all blocks")
    parser.add_argument("--domains",  action="store_true", help="Show domain profiles")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_blocks(), indent=2))
    elif args.domains:
        print(json.dumps(list_domains(), indent=2))
    else:
        ctx = json.loads(args.context)
        blk = args.blocks.split(",") if args.blocks else None
        result = ask(domain=args.domain, question=args.question, blocks=blk, context=ctx)
        print(json.dumps(result, indent=2))
