#!/usr/bin/env python3
"""Sync codebase entities directly to Neo4j for visualization."""

import ast
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple, Set

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from src.graph.codebase_scanner import scan_codebase, ScanConfig
from src.graph.file_parser import parse_python_file
from src.core.embeddings import EMBEDDING_DIMENSION

load_dotenv()


def _normalize_path(path: str) -> str:
    """Normalize file paths for stable graph identity across platforms."""
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _module_name_from_path(path: str) -> str:
    normalized = _normalize_path(path)
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


def _extract_phase_number(path: str) -> Optional[str]:
    match = re.search(r"/phases/([0-9]+(?:\.[0-9]+)?)", _normalize_path(path))
    if match:
        return match.group(1)
    return None


def _candidate_path_matches(candidate: str, all_paths: Set[str]) -> List[str]:
    """Find exact/suffix path matches for an import candidate."""
    normalized = _normalize_path(candidate)
    variants = {normalized}
    if normalized.startswith("src/"):
        variants.add(normalized[4:])
    else:
        variants.add(f"src/{normalized}")

    matches: List[str] = []
    for variant in variants:
        if variant in all_paths and variant not in matches:
            matches.append(variant)
        for file_path in all_paths:
            if file_path.endswith(f"/{variant}") and file_path not in matches:
                matches.append(file_path)
    return matches


def _extract_alias_map(tree: ast.AST) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Import):
            for alias in node.names:
                key = alias.asname or alias.name.split(".")[0]
                alias_map[key] = alias.name
        elif isinstance(node, ast.ImportFrom):
            base_module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                key = alias.asname or alias.name
                alias_map[key] = f"{base_module}.{alias.name}".strip(".")
    return alias_map


def _attribute_to_symbol(node: ast.AST) -> Optional[str]:
    parts: List[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


def _extract_called_symbol(call_node: ast.Call, alias_map: Dict[str, str]) -> Optional[str]:
    func_node = call_node.func
    if isinstance(func_node, ast.Name):
        symbol = func_node.id
        return alias_map.get(symbol, symbol)

    if isinstance(func_node, ast.Attribute):
        symbol = _attribute_to_symbol(func_node)
        if not symbol:
            return None
        parts = symbol.split(".")
        if parts and parts[0] in alias_map:
            base = alias_map[parts[0]]
            tail = ".".join(parts[1:])
            return f"{base}.{tail}" if tail else base
        return symbol

    return None


def _resolve_callee_full_name(
    symbol: Optional[str],
    src_file: str,
    by_file_and_name: Dict[Tuple[str, str], str],
    by_name: Dict[str, List[str]],
    by_full_name: Set[str],
) -> Optional[str]:
    if not symbol:
        return None

    symbol = symbol.strip(".")
    if symbol in by_full_name:
        return symbol

    parts = symbol.split(".")
    simple_name = parts[-1]

    local_match = by_file_and_name.get((src_file, simple_name))
    if local_match:
        return local_match

    if len(parts) >= 2:
        module_path = _normalize_path(".".join(parts[:-1]).replace(".", "/"))
        for candidate in (f"{module_path}.py", f"{module_path}/__init__.py"):
            for file_path, name in by_file_and_name:
                if name != simple_name:
                    continue
                if file_path == candidate or file_path.endswith(f"/{candidate}"):
                    return by_file_and_name[(file_path, name)]

    candidates = by_name.get(simple_name, [])
    if len(candidates) == 1:
        return candidates[0]

    return None


class Neo4jCodebaseSync:
    """Direct Neo4j sync for codebase knowledge graph."""

    def __init__(self):
        self.uri = os.getenv('NEO4J_URI')
        self.user = os.getenv('NEO4J_USER') or os.getenv('NEO4J_USERNAME') or 'neo4j'
        self.password = os.getenv('NEO4J_PASSWORD')

        if not all([self.uri, self.password]):
            raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set in .env")

        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def create_schema(self):
        """Create node labels, indexes, and vector index."""
        with self.driver.session() as session:
            # Remove legacy constraints from earlier schema versions.
            session.run("DROP CONSTRAINT class_signature_unique IF EXISTS")
            session.run("DROP CONSTRAINT function_signature_unique IF EXISTS")

            # Create constraints for unique paths
            session.run("CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")
            session.run("CREATE CONSTRAINT class_full_name_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.full_name IS UNIQUE")
            session.run("CREATE CONSTRAINT function_full_name_unique IF NOT EXISTS FOR (f:Function) REQUIRE f.full_name IS UNIQUE")
            session.run("CREATE CONSTRAINT planning_doc_path_unique IF NOT EXISTS FOR (d:PlanningDoc) REQUIRE d.path IS UNIQUE")

            # Create indexes for common queries
            session.run("CREATE INDEX file_language IF NOT EXISTS FOR (f:File) ON (f.language)")
            session.run("CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)")
            session.run("CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name)")
            session.run("CREATE INDEX function_signature IF NOT EXISTS FOR (f:Function) ON (f.function_signature)")

            print("[OK] Schema and indexes created")

    def create_vector_index(self):
        """Create vector similarity index for embeddings."""
        with self.driver.session() as session:
            # Drop existing vector index if it exists
            try:
                session.run("DROP INDEX codebase_embeddings IF EXISTS")
            except:
                pass

            # Create new vector index
            query = f"""
            CREATE VECTOR INDEX codebase_embeddings IF NOT EXISTS
            FOR (n:File)
            ON n.embedding
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {EMBEDDING_DIMENSION},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """
            session.run(query)
            print(f"[OK] Vector index created ({EMBEDDING_DIMENSION} dimensions)")

    def clear_graph(self):
        """Clear all existing codebase nodes."""
        with self.driver.session() as session:
            session.run("MATCH (n:File) DETACH DELETE n")
            session.run("MATCH (n:Class) DETACH DELETE n")
            session.run("MATCH (n:Function) DETACH DELETE n")
            session.run("MATCH (n:PlanningDoc) DETACH DELETE n")
            print("[OK] Existing graph cleared")

    def sync_files(self, files: List[Dict[str, Any]]):
        """Create File nodes with embeddings."""
        with self.driver.session() as session:
            for file in files:
                file_dict = file if isinstance(file, dict) else file.__dict__
                file_path = _normalize_path(file_dict.get('path', ''))
                session.run("""
                    MERGE (f:File {path: $path})
                    SET f.language = $language,
                        f.purpose = $purpose,
                        f.summary = $summary,
                        f.line_count = $line_count,
                        f.content_hash = $content_hash,
                        f.embedding = $embedding,
                        f.exports = $exports
                """,
                path=file_path,
                language=file_dict.get('language', ''),
                purpose=file_dict.get('purpose') or file_dict.get('summary', ''),
                summary=file_dict.get('summary', ''),
                line_count=file_dict.get('line_count', 0),
                content_hash=file_dict.get('content_hash', ''),
                embedding=file_dict.get('embedding', []),
                exports=file_dict.get('exports', [])
                )
        print(f"[OK] {len(files)} files synced")

    def sync_classes(self, classes: List[Dict[str, Any]]):
        """Create Class nodes and link to files."""
        with self.driver.session() as session:
            for cls in classes:
                cls_dict = cls if isinstance(cls, dict) else cls.__dict__
                file_path = _normalize_path(cls_dict.get('file_path', ''))
                full_name = cls_dict.get('full_name') or f"{_module_name_from_path(file_path)}.{cls_dict.get('name', '')}"
                # Create class node
                session.run("""
                    MERGE (c:Class {full_name: $full_name})
                    SET c.name = $name,
                        c.full_name = $full_name,
                        c.file_path = $file_path,
                        c.purpose = $purpose,
                        c.line_start = $line_start,
                        c.line_end = $line_end,
                        c.base_classes = $base_classes,
                        c.methods = $methods,
                        c.embedding = $embedding
                """,
                full_name=full_name,
                name=cls_dict.get('name', ''),
                file_path=file_path,
                purpose=cls_dict.get('purpose') or cls_dict.get('summary') or cls_dict.get('docstring', ''),
                line_start=cls_dict.get('line_start', 0),
                line_end=cls_dict.get('line_end', 0),
                base_classes=cls_dict.get('bases') or cls_dict.get('base_classes', []),
                methods=cls_dict.get('methods', []),
                embedding=cls_dict.get('embedding', [])
                )

                # Link to file
                session.run("""
                    MATCH (f:File {path: $file_path})
                    MATCH (c:Class {full_name: $full_name})
                    MERGE (f)-[:DEFINES_CLASS]->(c)
                    MERGE (f)-[:CONTAINS]->(c)
                """,
                file_path=file_path,
                full_name=full_name
                )
        print(f"[OK] {len(classes)} classes synced")

    def sync_functions(self, functions: List[Dict[str, Any]]):
        """Create Function nodes and link to files."""
        with self.driver.session() as session:
            for func in functions:
                func_dict = func if isinstance(func, dict) else func.__dict__
                file_path = _normalize_path(func_dict.get('file_path', ''))
                full_name = func_dict.get('full_name') or f"{_module_name_from_path(file_path)}.{func_dict.get('name', '')}"
                # Create function node
                session.run("""
                    MERGE (f:Function {full_name: $full_name})
                    SET f.name = $name,
                        f.full_name = $full_name,
                        f.function_signature = $full_name,
                        f.signature = $signature,
                        f.file_path = $file_path,
                        f.purpose = $purpose,
                        f.line_start = $line_start,
                        f.line_end = $line_end,
                        f.is_async = $is_async,
                        f.is_method = $is_method,
                        f.embedding = $embedding
                """,
                full_name=full_name,
                name=func_dict.get('name', ''),
                signature=func_dict.get('signature', ''),
                file_path=file_path,
                purpose=func_dict.get('purpose') or func_dict.get('summary') or func_dict.get('docstring', ''),
                line_start=func_dict.get('line_start', 0),
                line_end=func_dict.get('line_end', 0),
                is_async=func_dict.get('is_async', False),
                is_method=func_dict.get('is_method', False),
                embedding=func_dict.get('embedding', [])
                )

                # Link to file
                session.run("""
                    MATCH (file:File {path: $file_path})
                    MATCH (func:Function {full_name: $full_name})
                    MERGE (file)-[:DEFINES_FUNCTION]->(func)
                    MERGE (file)-[:CONTAINS]->(func)
                """,
                file_path=file_path,
                full_name=full_name
                )
        print(f"[OK] {len(functions)} functions synced")

    def sync_planning_docs(self, docs: List[Dict[str, Any]]):
        """Create PlanningDoc nodes."""
        with self.driver.session() as session:
            for doc in docs:
                doc_dict = doc if isinstance(doc, dict) else doc.__dict__
                path = _normalize_path(doc_dict.get('path', ''))
                session.run("""
                    MERGE (d:PlanningDoc {path: $path})
                    SET d.title = $title,
                        d.doc_type = $doc_type,
                        d.phase_number = $phase_number,
                        d.goal = $goal,
                        d.summary = $summary,
                        d.embedding = $embedding
                """,
                path=path,
                title=doc_dict.get('title', ''),
                doc_type=doc_dict.get('doc_type', 'unknown'),
                phase_number=doc_dict.get('phase_number') or _extract_phase_number(path),
                goal=doc_dict.get('goal') or doc_dict.get('title', ''),
                summary=doc_dict.get('summary', ''),
                embedding=doc_dict.get('embedding', [])
                )
        print(f"[OK] {len(docs)} planning docs synced")

    def sync_imports(self, files: List[Dict[str, Any]]):
        """Create IMPORTS edges between File nodes for resolvable Python imports."""
        file_paths = {
            _normalize_path((item if isinstance(item, dict) else item.__dict__).get('path', ''))
            for item in files
        }
        file_paths = {p for p in file_paths if p}

        edges_created = 0
        with self.driver.session() as session:
            for item in files:
                file_dict = item if isinstance(item, dict) else item.__dict__
                src_path = _normalize_path(file_dict.get('path', ''))
                if not src_path.endswith('.py') or not Path(src_path).exists():
                    continue

                try:
                    parsed = parse_python_file(src_path)
                except Exception:
                    continue

                for imp in parsed.imports:
                    if not imp.name:
                        continue

                    candidates = []
                    if imp.from_module:
                        base = imp.from_module.replace('.', '/')
                        # from x import y -> x/y.py (preferred), x.py, x/__init__.py
                        for imported_name in imp.imported_names:
                            if imported_name == "*":
                                continue
                            candidates.append(f"{base}/{imported_name}.py")
                        candidates.append(f"{base}.py")
                        candidates.append(f"{base}/__init__.py")
                    else:
                        dotted = imp.name.replace('.', '/')
                        candidates.append(f"{dotted}.py")
                        candidates.append(f"{dotted}/__init__.py")

                    resolved_targets: Set[str] = set()
                    for candidate in candidates:
                        for match in _candidate_path_matches(candidate, file_paths):
                            resolved_targets.add(match)

                    for dst_path in resolved_targets:
                        session.run(
                            """
                            MATCH (src:File {path: $src_path})
                            MATCH (dst:File {path: $dst_path})
                            MERGE (src)-[r:IMPORTS]->(dst)
                            SET r.import_type = $import_type,
                                r.import_module = $import_module,
                                r.imported_names = $imported_names
                            """,
                            src_path=src_path,
                            dst_path=dst_path,
                            import_type='from_import' if imp.from_module else 'absolute',
                            import_module=imp.from_module or imp.name,
                            imported_names=imp.imported_names,
                        )
                        edges_created += 1

        print(f"[OK] {edges_created} import edges synced")

    def sync_calls(self, functions: List[Dict[str, Any]]):
        """Create CALLS edges between Function nodes using AST call extraction."""
        by_file_and_name: Dict[Tuple[str, str], str] = {}
        by_name: Dict[str, List[str]] = defaultdict(list)
        by_full_name: Set[str] = set()

        for item in functions:
            fn = item if isinstance(item, dict) else item.__dict__
            file_path = _normalize_path(fn.get("file_path", ""))
            name = fn.get("name", "")
            if not file_path or not name:
                continue
            full_name = fn.get("full_name") or f"{_module_name_from_path(file_path)}.{name}"
            by_file_and_name[(file_path, name)] = full_name
            by_full_name.add(full_name)
            by_name[name].append(full_name)

        edge_counts: Dict[Tuple[str, str], int] = defaultdict(int)

        for file_path in {path for path, _ in by_file_and_name}:
            if not file_path.endswith(".py") or not Path(file_path).exists():
                continue
            try:
                tree = ast.parse(Path(file_path).read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                try:
                    tree = ast.parse(Path(file_path).read_text(encoding="latin-1"))
                except Exception:
                    continue
            except Exception:
                continue

            alias_map = _extract_alias_map(tree)
            top_level_functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for fn_node in top_level_functions:
                caller_full_name = by_file_and_name.get((file_path, fn_node.name))
                if not caller_full_name:
                    continue
                for node in ast.walk(fn_node):
                    if not isinstance(node, ast.Call):
                        continue
                    symbol = _extract_called_symbol(node, alias_map)
                    callee_full_name = _resolve_callee_full_name(
                        symbol=symbol,
                        src_file=file_path,
                        by_file_and_name=by_file_and_name,
                        by_name=by_name,
                        by_full_name=by_full_name,
                    )
                    if not callee_full_name or callee_full_name == caller_full_name:
                        continue
                    edge_counts[(caller_full_name, callee_full_name)] += 1

        with self.driver.session() as session:
            for (caller_full_name, callee_full_name), call_count in edge_counts.items():
                session.run(
                    """
                    MATCH (caller:Function {full_name: $caller})
                    MATCH (callee:Function {full_name: $callee})
                    MERGE (caller)-[r:CALLS]->(callee)
                    SET r.call_count = $call_count
                    """,
                    caller=caller_full_name,
                    callee=callee_full_name,
                    call_count=call_count,
                )

        print(f"[OK] {len(edge_counts)} call edges synced")


def main():
    print("=== Neo4j Codebase Sync ===\n")

    # Scan codebase
    print("Scanning codebase...")
    generate_embeddings = os.getenv("GRAPH_SYNC_EMBEDDINGS", "true").lower() == "true"
    config = ScanConfig(generate_embeddings=generate_embeddings)
    result = scan_codebase('.', config)

    print(f"Scan complete: {len(result.files)} files, {len(result.classes)} classes, {len(result.functions)} functions")
    print()

    # Connect to Neo4j
    print("Connecting to Neo4j...")
    syncer = Neo4jCodebaseSync()

    try:
        # Setup
        syncer.create_schema()
        syncer.create_vector_index()
        syncer.clear_graph()
        print()

        # Sync entities
        print("Syncing entities...")
        syncer.sync_files(result.files)
        syncer.sync_classes(result.classes)
        syncer.sync_functions(result.functions)
        syncer.sync_planning_docs(result.planning_docs)
        syncer.sync_imports(result.files)
        syncer.sync_calls(result.functions)

        print("\n[OK] Sync complete!")
        print("\nVisualization queries:")
        print("-" * 60)
        print("// 1. Overview")
        print("MATCH (n) RETURN labels(n)[0] as Type, count(n) as Count")
        print()
        print("// 2. File relationships")
        print("MATCH (f:File)-[r]->(other)")
        print("RETURN f, r, other LIMIT 50")
        print()
        print("// 3. Find similar files (semantic search)")
        print("MATCH (f:File {path: 'src/core/embeddings.py'})")
        print("CALL db.index.vector.queryNodes('codebase_embeddings', 10, f.embedding)")
        print("YIELD node, score")
        print("RETURN node.path, score ORDER BY score DESC")
        print()
        print("// 4. Class hierarchy")
        print("MATCH (f:File)-[:DEFINES_CLASS]->(c:Class)")
        print("RETURN f.path, c.name, c.base_classes LIMIT 20")

    finally:
        syncer.close()


if __name__ == "__main__":
    main()

