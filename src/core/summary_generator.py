"""
Hierarchical summary generator for codebase knowledge graph embeddings.

Extracts summaries (not full content) following "keyboard analogy":
- See file purpose, exports, imports at a glance
- See function signatures and purpose without implementations
- See class structure without method bodies

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import ast
import os
import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def generate_file_summary(file_path: str) -> Optional[str]:
    """
    Generate hierarchical summary for a file.

    Format:
        File: {file_path}
        Purpose: {file_docstring or first comment}
        Exports: {comma-separated exported names}
        Imports: {comma-separated import names}

    Args:
        file_path: Relative path from project root

    Returns:
        Formatted summary string or None if file can't be read/parsed
    """
    try:
        # Handle different file types
        if file_path.endswith('.md'):
            return _generate_markdown_summary(file_path)
        elif file_path.endswith('.py'):
            return _generate_python_file_summary(file_path)
        else:
            # Generic file summary
            return f"File: {file_path}\nPurpose: No description available\nType: {os.path.splitext(file_path)[1]}"

    except Exception as e:
        logger.warning(f"Failed to generate summary for {file_path}: {e}")
        return None


def _generate_python_file_summary(file_path: str) -> Optional[str]:
    """Generate summary for Python file using AST parsing."""
    try:
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)

        # Extract file docstring
        purpose = ast.get_docstring(tree) or "No description available"
        # Use only first line of docstring
        purpose = purpose.split('\n')[0].strip()

        # Extract exports (top-level classes, functions, constants)
        exports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):  # Skip private
                    exports.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        exports.append(target.id)

        # Extract imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Format summary
        exports_str = ', '.join(sorted(set(exports))) if exports else "None"
        imports_str = ', '.join(sorted(set(imports))[:10]) if imports else "None"  # Limit to 10
        if len(imports) > 10:
            imports_str += f" (+{len(imports)-10} more)"

        return f"""File: {file_path}
Purpose: {purpose}
Exports: {exports_str}
Imports: {imports_str}"""

    except SyntaxError as e:
        logger.warning(f"Syntax error parsing {file_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error generating Python file summary for {file_path}: {e}")
        return None


def _generate_markdown_summary(file_path: str) -> Optional[str]:
    """Generate summary for Markdown file."""
    try:
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract title from first # heading
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else os.path.basename(file_path)

        # Extract goal from "Goal:" line
        goal_match = re.search(r'^\*\*Goal:\*\*\s+(.+)$', content, re.MULTILINE)
        if not goal_match:
            goal_match = re.search(r'^Goal:\s+(.+)$', content, re.MULTILINE)
        goal = goal_match.group(1) if goal_match else "No goal specified"

        # Extract status from frontmatter if present
        status = "Unknown"
        if content.startswith('---'):
            frontmatter_end = content.find('---', 3)
            if frontmatter_end > 0:
                frontmatter = content[3:frontmatter_end]
                status_match = re.search(r'^status:\s*(.+)$', frontmatter, re.MULTILINE)
                if status_match:
                    status = status_match.group(1).strip()

        return f"""Planning: {file_path}
Title: {title}
Goal: {goal}
Status: {status}"""

    except Exception as e:
        logger.warning(f"Error generating Markdown summary for {file_path}: {e}")
        return None


def generate_function_summary(
    file_path: str,
    function_name: str,
    signature: str,
    docstring: Optional[str] = None
) -> str:
    """
    Generate summary for a function or method.

    Format:
        Function: {module}.{class}.{function_name} or {module}.{function_name}
        Signature: {signature}
        Purpose: {docstring first line}
        File: {file_path}

    Args:
        file_path: Source file path
        function_name: Function name (may include class prefix)
        signature: Function signature string
        docstring: Function docstring

    Returns:
        Formatted summary string
    """
    # Convert file path to module name
    module = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')

    # Extract purpose from docstring
    purpose = "No description available"
    if docstring:
        purpose = docstring.split('\n')[0].strip()

    return f"""Function: {module}.{function_name}
Signature: {signature}
Purpose: {purpose}
File: {file_path}"""


def generate_class_summary(
    file_path: str,
    class_name: str,
    bases: List[str],
    docstring: Optional[str] = None,
    methods: Optional[List[str]] = None
) -> str:
    """
    Generate summary for a class.

    Format:
        Class: {module}.{class_name}
        Inherits: {comma-separated bases}
        Purpose: {docstring first line}
        Methods: {comma-separated method names}
        File: {file_path}

    Args:
        file_path: Source file path
        class_name: Class name
        bases: Parent class names
        docstring: Class docstring
        methods: List of method names

    Returns:
        Formatted summary string
    """
    # Convert file path to module name
    module = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')

    # Extract purpose from docstring
    purpose = "No description available"
    if docstring:
        purpose = docstring.split('\n')[0].strip()

    # Format bases
    bases_str = ', '.join(bases) if bases else "object"

    # Format methods (limit to first 20)
    methods = methods or []
    methods_str = ', '.join(sorted(methods)[:20]) if methods else "None"
    if len(methods) > 20:
        methods_str += f" (+{len(methods)-20} more)"

    return f"""Class: {module}.{class_name}
Inherits: {bases_str}
Purpose: {purpose}
Methods: {methods_str}
File: {file_path}"""


def generate_planning_doc_summary(
    path: str,
    doc_type: str,
    goal: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    Generate summary for a planning document.

    Format:
        Planning: {path}
        Type: {doc_type}
        Goal: {goal}
        Status: {status}

    Args:
        path: Document path
        doc_type: Document type (PLAN, SUMMARY, CONTEXT, etc.)
        goal: Document goal
        status: Document status

    Returns:
        Formatted summary string
    """
    goal_str = goal or "No goal specified"
    status_str = status or "Unknown"

    return f"""Planning: {path}
Type: {doc_type}
Goal: {goal_str}
Status: {status_str}"""
