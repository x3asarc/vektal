"""
Full codebase scanner for knowledge graph population.

Scans src/, tests/, .planning/, docs/ and indexes all files, classes, functions.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import os
import time
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import logging

from src.core.codebase_entities import FileEntity, ClassEntity, FunctionEntity, PlanningDocEntity
from src.core.embeddings import generate_embedding, batch_generate_embeddings
from src.core.summary_generator import (
    generate_file_summary,
    generate_function_summary,
    generate_class_summary,
    generate_planning_doc_summary
)
from src.graph.file_parser import (
    parse_python_file,
    parse_markdown_file,
    detect_language
)

logger = logging.getLogger(__name__)


def _normalize_rel_path(path: str) -> str:
    """Normalize scanned relative paths for cross-platform graph consistency."""
    return path.replace("\\", "/")


def _to_module_name(rel_path: str) -> str:
    """Convert normalized file path to dotted module form."""
    normalized = _normalize_rel_path(rel_path)
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


@dataclass
class ScanConfig:
    """Configuration for codebase scan."""
    include_dirs: List[str] = field(default_factory=lambda: [
        "src", "tests", ".planning", "docs", "frontend", "scripts", 
        "migrations", "config", "ops", "reports", "seo", "utils", "web"
    ])
    exclude_patterns: List[str] = field(default_factory=lambda: ["__pycache__", ".git", "node_modules", ".venv", "venv", ".next", "dist", "build"])
    generate_embeddings: bool = True
    checkpoint_file: Optional[str] = None
    batch_size: int = 100


@dataclass
class CodebaseScanResult:
    """Result of codebase scan."""
    files: List[dict]
    classes: List[dict]
    functions: List[dict]
    planning_docs: List[dict]
    errors: List[str]
    scan_duration_seconds: float


def scan_codebase(root_path: str, config: ScanConfig) -> CodebaseScanResult:
    """
    Scan codebase and extract all entities.

    Args:
        root_path: Project root directory
        config: Scan configuration

    Returns:
        CodebaseScanResult with all extracted entities
    """
    start_time = time.time()
    errors = []
    files = []
    classes = []
    functions = []
    planning_docs = []

    # 1. Scan Root Files (Non-recursive)
    # This captures README.md, requirements.txt, etc. without double-scanning subdirs
    for filename in os.listdir(root_path):
        file_path = os.path.join(root_path, filename)
        if os.path.isfile(file_path):
            rel_path = _normalize_rel_path(filename)  # Relative path is just the filename
            
            # Skip excluded patterns
            if any(excl in rel_path for excl in config.exclude_patterns):
                continue
                
            # Detect language
            language = detect_language(file_path)
            if language == 'unknown':
                continue
                
            try:
                # Process root file (reusing logic)
                if language == 'python':
                    result = parse_python_file(file_path)
                    if result.errors:
                        errors.extend(result.errors)
                    
                    summary = generate_file_summary(rel_path)
                    embedding = generate_embedding(summary) if config.generate_embeddings and summary else []
                    
                    files.append({
                        'path': rel_path,
                        'language': language,
                        'summary': summary,
                        'embedding': embedding
                    })
                    # Add classes/functions from root scripts...
                    for cls in result.classes:
                        cls_summary = generate_class_summary(rel_path, cls.name, cls.bases, cls.docstring, cls.methods)
                        cls_embedding = generate_embedding(cls_summary) if config.generate_embeddings else []
                        classes.append({
                            'file_path': rel_path,
                            'name': cls.name,
                            'full_name': f"{_to_module_name(rel_path)}.{cls.name}",
                            'summary': cls_summary,
                            'embedding': cls_embedding
                        })
                    for func in result.functions:
                        func_summary = generate_function_summary(rel_path, func.name, func.signature, func.docstring)
                        func_embedding = generate_embedding(func_summary) if config.generate_embeddings else []
                        functions.append({
                            'file_path': rel_path,
                            'name': func.name,
                            'full_name': f"{_to_module_name(rel_path)}.{func.name}",
                            'signature': func.signature,
                            'summary': func_summary,
                            'embedding': func_embedding
                        })

                elif language == 'markdown': # Handle root markdown
                    result = parse_markdown_file(file_path)
                    summary = generate_planning_doc_summary(
                        rel_path, result.doc_type or 'DOCUMENTATION',
                        result.title, result.frontmatter.get('status')
                    )
                    embedding = generate_embedding(summary) if config.generate_embeddings else []
                    planning_docs.append({
                        'path': rel_path,
                        'doc_type': result.doc_type or 'DOCUMENTATION',
                        'title': result.title or os.path.basename(rel_path),
                        'summary': summary,
                        'embedding': embedding
                    })
            except Exception as e:
                logger.error(f"Error scanning root file {rel_path}: {e}")
                errors.append(f"{rel_path}: {e}")

    # 2. Walk directory tree (Recursive)
    for include_dir in config.include_dirs:
        dir_path = os.path.join(root_path, include_dir)
        if not os.path.exists(dir_path):
            continue

        for root, dirs, filenames in os.walk(dir_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(excl in os.path.join(root, d) for excl in config.exclude_patterns)]

            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = _normalize_rel_path(os.path.relpath(file_path, root_path))

                # Skip excluded patterns
                if any(excl in rel_path for excl in config.exclude_patterns):
                    continue

                # Detect language
                language = detect_language(file_path)
                if language == 'unknown':
                    continue

                # Parse file based on type
                try:
                    if language == 'python':
                        result = parse_python_file(file_path)
                        if result.errors:
                            errors.extend(result.errors)

                        # Create file summary and embedding
                        summary = generate_file_summary(rel_path)
                        embedding = generate_embedding(summary) if config.generate_embeddings and summary else []

                        files.append({
                            'path': rel_path,
                            'language': language,
                            'summary': summary,
                            'embedding': embedding
                        })

                        # Add classes
                        for cls in result.classes:
                            cls_summary = generate_class_summary(
                                rel_path, cls.name, cls.bases, cls.docstring, cls.methods
                            )
                            cls_embedding = generate_embedding(cls_summary) if config.generate_embeddings else []
                            classes.append({
                                'file_path': rel_path,
                                'name': cls.name,
                                'full_name': f"{_to_module_name(rel_path)}.{cls.name}",
                                'summary': cls_summary,
                                'embedding': cls_embedding
                            })

                        # Add functions
                        for func in result.functions:
                            func_summary = generate_function_summary(
                                rel_path, func.name, func.signature, func.docstring
                            )
                            func_embedding = generate_embedding(func_summary) if config.generate_embeddings else []
                            functions.append({
                                'file_path': rel_path,
                                'name': func.name,
                                'full_name': f"{_to_module_name(rel_path)}.{func.name}",
                                'signature': func.signature,
                                'summary': func_summary,
                                'embedding': func_embedding
                            })

                    elif language == 'markdown' and '.planning' in rel_path:
                        result = parse_markdown_file(file_path)
                        summary = generate_planning_doc_summary(
                            rel_path, result.doc_type or 'MARKDOWN',
                            result.title, result.frontmatter.get('status')
                        )
                        embedding = generate_embedding(summary) if config.generate_embeddings else []
                        planning_docs.append({
                            'path': rel_path,
                            'doc_type': result.doc_type or 'MARKDOWN',
                            'title': result.title or os.path.basename(rel_path),
                            'summary': summary,
                            'embedding': embedding
                        })

                except Exception as e:
                    logger.error(f"Error scanning {rel_path}: {e}")
                    errors.append(f"{rel_path}: {e}")

    duration = time.time() - start_time

    return CodebaseScanResult(
        files=files,
        classes=classes,
        functions=functions,
        planning_docs=planning_docs,
        errors=errors,
        scan_duration_seconds=duration
    )
