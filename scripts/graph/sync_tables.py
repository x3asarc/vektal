"""Task 8: SQLAlchemy Table nodes + ACCESSES edges from ORM analysis."""
import ast
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dotenv import load_dotenv
from scripts.graph.sync_to_neo4j import Neo4jCodebaseSync, _normalize_path, _module_name_from_path

load_dotenv()


# ── Table extraction from __tablename__ ──────────────────────────────────────
def _extract_tables_from_models() -> List[Dict[str, Any]]:
    """Extract :Table nodes from SQLAlchemy model __tablename__ assignments."""
    tables = []
    for fp in Path('src/models').rglob('*.py'):
        try:
            tree = ast.parse(fp.read_text(encoding='utf-8'))
        except Exception:
            continue
        file_path = _normalize_path(str(fp))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.Assign):
                    continue
                for t in item.targets:
                    if isinstance(t, ast.Name) and t.id == '__tablename__':
                        if isinstance(item.value, ast.Constant):
                            tables.append({
                                'name': item.value.value,
                                'model_class': node.name,
                                'schema_version': 1,
                                'file_path': file_path,
                            })
    return tables


# ── ORM access extraction ─────────────────────────────────────────────────────
# Model class name → table name mapping (built from extraction above)
_CLASS_TO_TABLE: Dict[str, str] = {}


def _extract_orm_accesses_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Scan a Python file for ORM access patterns and return (function, table) pairs.
    Patterns detected:
      - ModelClass.query          → SELECT on table
      - db.session.query(Model)   → SELECT
      - session.query(Model)      → SELECT
      - db.session.add(Model())   → INSERT (via isinstance check skipped — too dynamic)
      - ModelClass.objects        → Django-style (skip, not used here)
      - select(Model)             → SQLAlchemy 2.x
      - db.session.get(Model, ..) → SELECT by PK
    """
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

    accesses = []
    module_name = _module_name_from_path(_normalize_path(file_path))
    model_names = set(_CLASS_TO_TABLE.keys())

    def _get_model_from_arg(node: ast.expr) -> Optional[str]:
        """Extract model class name from an AST node."""
        if isinstance(node, ast.Name) and node.id in model_names:
            return node.id
        if isinstance(node, ast.Attribute) and node.attr in model_names:
            return node.attr
        return None

    def _scan_for_accesses(stmts, function_full_name: Optional[str]) -> List[Dict]:
        results = []
        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                child_fn = f"{module_name}.{stmt.name}"
                results.extend(_scan_for_accesses(stmt.body, child_fn))
                continue
            for node in ast.walk(stmt):
                if not isinstance(node, ast.Call):
                    continue
                # Pattern: db.session.query(Model, ...) or session.query(Model)
                func = node.func
                if (isinstance(func, ast.Attribute) and func.attr in ('query', 'get', 'add', 'execute')
                        and isinstance(func.value, (ast.Attribute, ast.Name))):
                    for arg in node.args:
                        model = _get_model_from_arg(arg)
                        if model and _CLASS_TO_TABLE.get(model):
                            results.append({
                                'function_full_name': function_full_name,
                                'table_name': _CLASS_TO_TABLE[model],
                                'access_type': func.attr,
                            })
                # Pattern: select(Model)
                if (isinstance(func, ast.Name) and func.id == 'select'):
                    for arg in node.args:
                        model = _get_model_from_arg(arg)
                        if model and _CLASS_TO_TABLE.get(model):
                            results.append({
                                'function_full_name': function_full_name,
                                'table_name': _CLASS_TO_TABLE[model],
                                'access_type': 'select',
                            })
                # Pattern: Model.query.<anything>
                if (isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Attribute)
                        and func.value.attr == 'query'):
                    model_node = func.value.value
                    model = _get_model_from_arg(model_node)
                    if model and _CLASS_TO_TABLE.get(model):
                        results.append({
                            'function_full_name': function_full_name,
                            'table_name': _CLASS_TO_TABLE[model],
                            'access_type': 'query',
                        })
        return results

    return _scan_for_accesses(tree.body, None)


# ── Aura sync ────────────────────────────────────────────────────────────────
def sync_tables(syncer: Neo4jCodebaseSync, tables: List[Dict[str, Any]]):
    with syncer.driver.session() as session:
        session.run("CREATE CONSTRAINT table_name_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.name IS UNIQUE")
        session.run("MATCH (n:Table) DETACH DELETE n")
        for t in tables:
            session.run("""
                MERGE (t:Table {name: $name})
                SET t.model_class = $model_class,
                    t.schema_version = $schema_version,
                    t.file_path = $file_path
            """, **t)
    print(f"[OK] {len(tables)} Table nodes synced")


def sync_accesses(syncer: Neo4jCodebaseSync, accesses: List[Dict[str, Any]]):
    # Deduplicate (function, table) pairs
    seen: Set[tuple] = set()
    unique = []
    for a in accesses:
        key = (a.get('function_full_name'), a['table_name'])
        if key not in seen:
            seen.add(key)
            unique.append(a)

    edge_count = 0
    with syncer.driver.session() as session:
        for a in unique:
            if not a.get('function_full_name'):
                continue
            session.run("""
                MATCH (f:Function {full_name: $fn})
                MATCH (t:Table {name: $table})
                MERGE (f)-[:ACCESSES]->(t)
            """, fn=a['function_full_name'], table=a['table_name'])
            edge_count += 1

    print(f"[OK] {edge_count} ACCESSES edges synced ({len(accesses) - edge_count} module-level skipped)")
    return edge_count


def main():
    print("=== Task 8: Table Sync ===\n")

    # Extract table definitions
    tables = _extract_tables_from_models()
    print(f"Found {len(tables)} tables in src/models/")
    for t in sorted(tables, key=lambda x: x['name']):
        print(f"  {t['name']:45s} ({t['model_class']})")

    # Build class→table map for ORM access detection
    global _CLASS_TO_TABLE
    _CLASS_TO_TABLE = {t['model_class']: t['name'] for t in tables}

    # Scan all Python files for ORM accesses
    print(f"\nScanning for ORM accesses...")
    all_accesses = []
    for fp in Path('src').rglob('*.py'):
        all_accesses.extend(_extract_orm_accesses_from_file(str(fp)))
    print(f"Found {len(all_accesses)} ORM access instances")

    syncer = Neo4jCodebaseSync()
    try:
        sync_tables(syncer, tables)
        edge_count = sync_accesses(syncer, all_accesses)

        # Verify
        with syncer.driver.session() as session:
            tc = session.run("MATCH (n:Table) RETURN count(n) as c").single()['c']
            ec = session.run("MATCH ()-[r:ACCESSES]->() RETURN count(r) as c").single()['c']

        print(f"\n=== Aura verification ===")
        print(f"  :Table nodes:   {tc}")
        print(f"  :ACCESSES edges:{ec}")
        print("\n[OK] Task 8 complete")
    finally:
        syncer.close()


if __name__ == "__main__":
    main()
