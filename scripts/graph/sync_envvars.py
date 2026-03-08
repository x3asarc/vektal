"""Task 7: EnvVar AST visitor — extract env var dependencies + risk tiers."""
import ast
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync, _normalize_path, _module_name_from_path

load_dotenv()

# ── Risk tier classification ────────────────────────────────────────────────
_TIER1_SUFFIXES = ('PASSWORD', 'SECRET', 'PRIVATE_KEY', 'CREDENTIAL', 'CERT')
_TIER1_PATTERNS = ('API_KEY', 'AUTH_TOKEN', 'ACCESS_TOKEN', 'CLIENT_SECRET',
                   'WEBHOOK_SECRET', 'SIGNING_KEY', 'ENCRYPTION_KEY')
_TIER2_SUFFIXES = ('_URL', '_URI', '_HOST', '_PORT', '_DSN', '_BACKEND', '_BROKER')
_TIER2_PATTERNS = ('ENABLED', 'ORACLE', 'CELERY_BROKER', 'CELERY_RESULT',
                   'REDIS_URL', 'DATABASE_URL', 'NEO4J_URI', 'TELEGRAM_CHAT_ID')
_TIER3_SUFFIXES = ('_TIMEOUT', '_INTERVAL', '_LIMIT', '_COUNT', '_RETRIES',
                   '_SECONDS', '_DAYS', '_SIZE', '_THRESHOLD', '_BATCH')
_TIER3_PATTERNS = ('API_VERSION', 'RETRY', 'TIMEOUT', 'INTERVAL', 'BATCH',
                   'MAX_', 'MIN_', 'LIMIT', 'PRICE')


def _classify_risk_tier(name: str) -> int:
    up = name.upper()
    for suffix in _TIER1_SUFFIXES:
        if up.endswith(suffix):
            return 1
    for pat in _TIER1_PATTERNS:
        if pat in up:
            return 1
    for suffix in _TIER2_SUFFIXES:
        if up.endswith(suffix):
            return 2
    for pat in _TIER2_PATTERNS:
        if pat in up:
            return 2
    for suffix in _TIER3_SUFFIXES:
        if up.endswith(suffix):
            return 3
    for pat in _TIER3_PATTERNS:
        if pat in up:
            return 3
    return 4  # Contextual default


# ── AST extraction ───────────────────────────────────────────────────────────
def _is_env_call(node: ast.Call) -> Optional[str]:
    """Return the var name if node is os.getenv/os.environ.get/os.environ[]. Else None."""
    func = node.func
    # os.getenv("VAR")
    if (isinstance(func, ast.Attribute) and func.attr == 'getenv'
            and isinstance(func.value, ast.Name) and func.value.id == 'os'):
        if node.args and isinstance(node.args[0], ast.Constant):
            return str(node.args[0].value)
    # os.environ.get("VAR")
    if (isinstance(func, ast.Attribute) and func.attr == 'get'
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == 'environ'
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == 'os'):
        if node.args and isinstance(node.args[0], ast.Constant):
            return str(node.args[0].value)
    return None


def _has_default(node: ast.Call) -> bool:
    """True if the getenv/environ.get call has a non-None default."""
    return len(node.args) >= 2 or any(kw.arg == 'default' for kw in node.keywords)


def _extract_envvars_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Walk a Python file and return all env var accesses with function context."""
    try:
        source = Path(file_path).read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            source = Path(file_path).read_text(encoding='latin-1')
        except Exception:
            return []
    except Exception:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results = []
    module_name = _module_name_from_path(_normalize_path(file_path))
    norm_path = _normalize_path(file_path)

    def _scan_body(stmts, function_full_name: Optional[str]):
        """Recursively scan statements, tracking function context."""
        for stmt in stmts:
            # Enter function scope
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                child_fn = f"{module_name}.{stmt.name}"
                _scan_body(stmt.body, child_fn)
                continue
            # Scan all call nodes in this statement
            for node in ast.walk(stmt):
                if not isinstance(node, ast.Call):
                    continue
                var_name = _is_env_call(node)
                if var_name:
                    results.append({
                        'var_name': var_name,
                        'has_default': _has_default(node),
                        'risk_tier': _classify_risk_tier(var_name),
                        'function_full_name': function_full_name,
                        'file_path': norm_path,
                    })

    # Top-level module body (function_full_name=None for module-level reads)
    _scan_body(tree.body, None)
    return results


# ── Aura sync ────────────────────────────────────────────────────────────────
def sync_envvars(syncer: Neo4jCodebaseSync, accesses: List[Dict[str, Any]]):
    """Write :EnvVar nodes and :DEPENDS_ON_CONFIG edges."""
    # Deduplicate EnvVar nodes (one per unique name)
    unique_vars: Dict[str, Dict] = {}
    for a in accesses:
        name = a['var_name']
        if name not in unique_vars:
            unique_vars[name] = {
                'name': name,
                'risk_tier': a['risk_tier'],
                'has_default': a['has_default'],
            }
        else:
            # If any access lacks a default, mark has_default False
            if not a['has_default']:
                unique_vars[name]['has_default'] = False

    with syncer.driver.session() as session:
        session.run("CREATE CONSTRAINT envvar_name_unique IF NOT EXISTS FOR (e:EnvVar) REQUIRE e.name IS UNIQUE")
        session.run("MATCH (n:EnvVar) DETACH DELETE n")

        # Write EnvVar nodes
        for var in unique_vars.values():
            session.run("""
                MERGE (e:EnvVar {name: $name})
                SET e.risk_tier = $risk_tier,
                    e.has_default = $has_default
            """, **var)

        # Write DEPENDS_ON_CONFIG edges (function-level only, skip module-level)
        edge_count = 0
        for a in accesses:
            if not a['function_full_name']:
                continue
            session.run("""
                MATCH (f:Function {full_name: $fn})
                MATCH (e:EnvVar {name: $name})
                MERGE (f)-[:DEPENDS_ON_CONFIG]->(e)
            """, fn=a['function_full_name'], name=a['var_name'])
            edge_count += 1

    return len(unique_vars), edge_count


def main():
    print("=== Task 7: EnvVar Sync ===\n")

    py_files = [str(p) for p in Path('src').rglob('*.py')]
    print(f"Scanning {len(py_files)} Python files...")

    all_accesses = []
    for fp in py_files:
        all_accesses.extend(_extract_envvars_from_file(fp))

    print(f"Found {len(all_accesses)} env var accesses")

    # Show tier breakdown before writing
    from collections import Counter
    tier_counts = Counter(a['risk_tier'] for a in all_accesses)
    unique_names = set(a['var_name'] for a in all_accesses)
    print(f"Unique vars: {len(unique_names)}")
    print(f"Tier breakdown: {dict(sorted(tier_counts.items()))}")

    syncer = Neo4jCodebaseSync()
    try:
        node_count, edge_count = sync_envvars(syncer, all_accesses)

        # Verify
        with syncer.driver.session() as session:
            t1 = session.run("MATCH (e:EnvVar) WHERE e.risk_tier = 1 RETURN count(e) as c").single()['c']
            t2 = session.run("MATCH (e:EnvVar) WHERE e.risk_tier = 2 RETURN count(e) as c").single()['c']
            t3 = session.run("MATCH (e:EnvVar) WHERE e.risk_tier = 3 RETURN count(e) as c").single()['c']
            t4 = session.run("MATCH (e:EnvVar) WHERE e.risk_tier = 4 RETURN count(e) as c").single()['c']
            edges = session.run("MATCH ()-[r:DEPENDS_ON_CONFIG]->() RETURN count(r) as c").single()['c']

        print(f"\n=== Aura verification ===")
        print(f"  :EnvVar nodes:        {node_count}")
        print(f"    Tier 1 (Vital):     {t1}")
        print(f"    Tier 2 (Operational):{t2}")
        print(f"    Tier 3 (Functional): {t3}")
        print(f"    Tier 4 (Contextual): {t4}")
        print(f"  :DEPENDS_ON_CONFIG:   {edges}")
        print("\n[OK] Task 7 complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
