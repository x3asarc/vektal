#!/usr/bin/env python3
"""Sync codebase entities directly to Neo4j for visualization."""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from src.graph.codebase_scanner import scan_codebase, ScanConfig
from src.core.embeddings import EMBEDDING_DIMENSION

load_dotenv()


class Neo4jCodebaseSync:
    """Direct Neo4j sync for codebase knowledge graph."""

    def __init__(self):
        self.uri = os.getenv('NEO4J_URI')
        self.user = os.getenv('NEO4J_USER')
        self.password = os.getenv('NEO4J_PASSWORD')

        if not all([self.uri, self.user, self.password]):
            raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set in .env")

        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def create_schema(self):
        """Create node labels, indexes, and vector index."""
        with self.driver.session() as session:
            # Create constraints for unique paths
            session.run("CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")
            session.run("CREATE CONSTRAINT class_signature_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.signature IS UNIQUE")
            session.run("CREATE CONSTRAINT function_signature_unique IF NOT EXISTS FOR (f:Function) REQUIRE f.signature IS UNIQUE")

            # Create indexes for common queries
            session.run("CREATE INDEX file_language IF NOT EXISTS FOR (f:File) ON (f.language)")
            session.run("CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)")
            session.run("CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name)")

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
                session.run("""
                    MERGE (f:File {path: $path})
                    SET f.language = $language,
                        f.purpose = $purpose,
                        f.line_count = $line_count,
                        f.content_hash = $content_hash,
                        f.embedding = $embedding,
                        f.exports = $exports
                """,
                path=file_dict.get('path', ''),
                language=file_dict.get('language', ''),
                purpose=file_dict.get('purpose', ''),
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
                # Create class node
                session.run("""
                    MERGE (c:Class {signature: $signature})
                    SET c.name = $name,
                        c.file_path = $file_path,
                        c.docstring = $docstring,
                        c.line_start = $line_start,
                        c.line_end = $line_end,
                        c.base_classes = $base_classes,
                        c.methods = $methods,
                        c.embedding = $embedding
                """,
                signature=cls_dict.get('signature', ''),
                name=cls_dict.get('name', ''),
                file_path=cls_dict.get('file_path', ''),
                docstring=cls_dict.get('docstring', ''),
                line_start=cls_dict.get('line_start', 0),
                line_end=cls_dict.get('line_end', 0),
                base_classes=cls_dict.get('base_classes', []),
                methods=cls_dict.get('methods', []),
                embedding=cls_dict.get('embedding', [])
                )

                # Link to file
                session.run("""
                    MATCH (f:File {path: $file_path})
                    MATCH (c:Class {signature: $signature})
                    MERGE (f)-[:DEFINES_CLASS]->(c)
                """,
                file_path=cls_dict.get('file_path', ''),
                signature=cls_dict.get('signature', '')
                )
        print(f"[OK] {len(classes)} classes synced")

    def sync_functions(self, functions: List[Dict[str, Any]]):
        """Create Function nodes and link to files."""
        with self.driver.session() as session:
            for func in functions:
                func_dict = func if isinstance(func, dict) else func.__dict__
                # Create function node
                session.run("""
                    MERGE (f:Function {signature: $signature})
                    SET f.name = $name,
                        f.file_path = $file_path,
                        f.docstring = $docstring,
                        f.line_start = $line_start,
                        f.line_end = $line_end,
                        f.is_async = $is_async,
                        f.is_method = $is_method,
                        f.embedding = $embedding
                """,
                signature=func_dict.get('signature', ''),
                name=func_dict.get('name', ''),
                file_path=func_dict.get('file_path', ''),
                docstring=func_dict.get('docstring', ''),
                line_start=func_dict.get('line_start', 0),
                line_end=func_dict.get('line_end', 0),
                is_async=func_dict.get('is_async', False),
                is_method=func_dict.get('is_method', False),
                embedding=func_dict.get('embedding', [])
                )

                # Link to file
                session.run("""
                    MATCH (file:File {path: $file_path})
                    MATCH (func:Function {signature: $signature})
                    MERGE (file)-[:DEFINES_FUNCTION]->(func)
                """,
                file_path=func_dict.get('file_path', ''),
                signature=func_dict.get('signature', '')
                )
        print(f"[OK] {len(functions)} functions synced")

    def sync_planning_docs(self, docs: List[Dict[str, Any]]):
        """Create PlanningDoc nodes."""
        with self.driver.session() as session:
            for doc in docs:
                doc_dict = doc if isinstance(doc, dict) else doc.__dict__
                session.run("""
                    MERGE (d:PlanningDoc {path: $path})
                    SET d.title = $title,
                        d.doc_type = $doc_type,
                        d.phase = $phase,
                        d.content = $content,
                        d.embedding = $embedding
                """,
                path=doc_dict.get('path', ''),
                title=doc_dict.get('title', ''),
                doc_type=doc_dict.get('doc_type', 'unknown'),
                phase=doc_dict.get('phase', ''),
                content=doc_dict.get('content', ''),
                embedding=doc_dict.get('embedding', [])
                )
        print(f"[OK] {len(docs)} planning docs synced")


def main():
    print("=== Neo4j Codebase Sync ===\n")

    # Scan codebase
    print("Scanning codebase...")
    config = ScanConfig(generate_embeddings=True)
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

        print("\n[OK] Sync complete!")
        print("\nVisualization queries:")
        print("─" * 60)
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
