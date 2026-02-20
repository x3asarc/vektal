"""
Language-specific file parsers for codebase knowledge graph.

Extracts entities (classes, functions, imports) from different file types.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import ast
import os
import re
import yaml
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# ===========================================
# Parse Result Data Classes
# ===========================================

@dataclass
class ImportInfo:
    """Information about an import statement."""
    name: str
    from_module: Optional[str] = None
    is_relative: bool = False
    imported_names: List[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """Information about a function or method."""
    name: str
    signature: str
    docstring: Optional[str]
    is_async: bool
    line_start: int
    line_end: int


@dataclass
class ClassInfo:
    """Information about a class definition."""
    name: str
    bases: List[str]
    methods: List[str]
    docstring: Optional[str]
    line_start: int
    line_end: int


@dataclass
class PythonFileParseResult:
    """Result of parsing a Python file."""
    file_path: str
    module_docstring: Optional[str]
    imports: List[ImportInfo]
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    errors: List[str]


@dataclass
class MarkdownFileParseResult:
    """Result of parsing a Markdown file."""
    file_path: str
    title: Optional[str]
    frontmatter: Dict[str, Any]
    headers: List[str]
    doc_type: Optional[str]


# ===========================================
# File Type Detection
# ===========================================

def detect_language(file_path: str) -> str:
    """
    Detect programming language from file extension.

    Args:
        file_path: Path to file

    Returns:
        Language identifier (python, typescript, markdown, yaml, unknown)
    """
    ext = os.path.splitext(file_path)[1].lower()

    language_map = {
        '.py': 'python',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.md': 'markdown',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.js': 'javascript',
        '.jsx': 'javascript',
    }

    return language_map.get(ext, 'unknown')


# ===========================================
# Python File Parsing
# ===========================================

def parse_python_file(file_path: str) -> PythonFileParseResult:
    """
    Parse Python file using AST to extract entities.

    Args:
        file_path: Path to Python file

    Returns:
        PythonFileParseResult with extracted entities

    Example:
        >>> result = parse_python_file("src/core/embeddings.py")
        >>> print(f"Functions: {len(result.functions)}")
        >>> print(f"Classes: {len(result.classes)}")
    """
    errors = []

    try:
        # Read file with encoding fallback
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            errors.append("File encoding is not UTF-8, using latin-1 fallback")

        # Parse AST
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            # Return partial result with error
            return PythonFileParseResult(
                file_path=file_path,
                module_docstring=None,
                imports=[],
                classes=[],
                functions=[],
                errors=errors
            )

        # Extract module docstring
        module_docstring = ast.get_docstring(tree)

        # Extract imports
        imports = _extract_imports(tree)

        # Extract classes
        classes = _extract_classes(tree)

        # Extract top-level functions
        functions = _extract_functions(tree)

        return PythonFileParseResult(
            file_path=file_path,
            module_docstring=module_docstring,
            imports=imports,
            classes=classes,
            functions=functions,
            errors=errors
        )

    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
        return PythonFileParseResult(
            file_path=file_path,
            module_docstring=None,
            imports=[],
            classes=[],
            functions=[],
            errors=errors
        )
    except Exception as e:
        logger.error(f"Unexpected error parsing {file_path}: {e}")
        errors.append(f"Unexpected error: {e}")
        return PythonFileParseResult(
            file_path=file_path,
            module_docstring=None,
            imports=[],
            classes=[],
            functions=[],
            errors=errors
        )


def _extract_imports(tree: ast.AST) -> List[ImportInfo]:
    """Extract import statements from AST."""
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    name=alias.name,
                    from_module=None,
                    is_relative=False,
                    imported_names=[]
                ))
        elif isinstance(node, ast.ImportFrom):
            # Handle 'from X import Y'
            imported_names = [alias.name for alias in node.names]
            imports.append(ImportInfo(
                name=node.module or "",
                from_module=node.module,
                is_relative=node.level > 0,
                imported_names=imported_names
            ))

    return imports


def _extract_classes(tree: ast.AST) -> List[ClassInfo]:
    """Extract class definitions from AST."""
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Extract base class names
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(f"{base.value.id if isinstance(base.value, ast.Name) else '...'}.{base.attr}")

            # Extract method names
            methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]

            # Get docstring
            docstring = ast.get_docstring(node)

            classes.append(ClassInfo(
                name=node.name,
                bases=bases,
                methods=methods,
                docstring=docstring,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno
            ))

    return classes


def _extract_functions(tree: ast.AST) -> List[FunctionInfo]:
    """Extract top-level function definitions from AST."""
    functions = []

    # Only get top-level functions (not methods)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Build signature
            args = []
            for arg in node.args.args:
                args.append(arg.arg)
            signature = f"({', '.join(args)})"

            # Get docstring
            docstring = ast.get_docstring(node)

            functions.append(FunctionInfo(
                name=node.name,
                signature=signature,
                docstring=docstring,
                is_async=isinstance(node, ast.AsyncFunctionDef),
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno
            ))

    return functions


# ===========================================
# Markdown File Parsing
# ===========================================

def parse_markdown_file(file_path: str) -> MarkdownFileParseResult:
    """
    Parse Markdown file to extract metadata.

    Args:
        file_path: Path to Markdown file

    Returns:
        MarkdownFileParseResult with extracted metadata
    """
    try:
        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()

        # Extract YAML frontmatter
        frontmatter = {}
        if content.startswith('---'):
            end_idx = content.find('---', 3)
            if end_idx > 0:
                frontmatter_text = content[3:end_idx]
                try:
                    frontmatter = yaml.safe_load(frontmatter_text) or {}
                except yaml.YAMLError:
                    logger.warning(f"Invalid YAML frontmatter in {file_path}")

        # Extract title (first # heading)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else None

        # Extract all headers
        headers = re.findall(r'^#{2,6}\s+(.+)$', content, re.MULTILINE)

        # Detect planning doc type
        doc_type = _detect_doc_type(file_path, content, frontmatter)

        return MarkdownFileParseResult(
            file_path=file_path,
            title=title,
            frontmatter=frontmatter,
            headers=headers,
            doc_type=doc_type
        )

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return MarkdownFileParseResult(
            file_path=file_path,
            title=None,
            frontmatter={},
            headers=[],
            doc_type=None
        )
    except Exception as e:
        logger.error(f"Error parsing Markdown file {file_path}: {e}")
        return MarkdownFileParseResult(
            file_path=file_path,
            title=None,
            frontmatter={},
            headers=[],
            doc_type=None
        )


def _detect_doc_type(file_path: str, content: str, frontmatter: Dict[str, Any]) -> Optional[str]:
    """Detect planning document type from path and content."""
    # Check frontmatter
    if 'type' in frontmatter:
        return frontmatter['type'].upper()

    # Check filename
    file_name = os.path.basename(file_path).upper()
    if 'PLAN' in file_name:
        return 'PLAN'
    elif 'SUMMARY' in file_name:
        return 'SUMMARY'
    elif 'CONTEXT' in file_name:
        return 'CONTEXT'
    elif 'VERIFICATION' in file_name:
        return 'VERIFICATION'
    elif 'ROADMAP' in file_name:
        return 'ROADMAP'
    elif 'STATE' in file_name:
        return 'STATE'
    elif 'REQUIREMENTS' in file_name:
        return 'REQUIREMENTS'

    # Check path
    if '.planning' in file_path:
        return 'PLANNING'

    return None


# ===========================================
# YAML File Parsing
# ===========================================

def parse_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    Parse YAML file safely.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML content or empty dict on error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"YAML file not found: {file_path}")
        return {}
    except yaml.YAMLError as e:
        logger.warning(f"YAML parse error in {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error parsing YAML {file_path}: {e}")
        return {}
