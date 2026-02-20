"""
Codebase knowledge graph entity and edge models.

Defines Pydantic v2 models for parsing and indexing Python/TypeScript codebases
into Graphiti/Neo4j for the Phase 14 continuous learning loop.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import Field, field_validator

from .synthex_entities import BaseEntity, BaseEdge


# ===========================================
# Base Validators
# ===========================================

def normalize_path(path: str) -> str:
    """Normalize file paths to use forward slashes and no leading slash."""
    if not path:
        return path
    normalized = path.replace('\\', '/').strip('/')
    return normalized


# ===========================================
# Entity Families
# ===========================================

class FileEntity(BaseEntity):
    """Represents a source file in the codebase."""
    entity_type: str = Field(default="file", frozen=True)
    path: str = Field(..., description="File path relative to project root")
    language: str = Field(..., description="Language (python, typescript, yaml, markdown)")
    purpose: str = Field(..., description="Extracted from docstring or first comment")
    exports: List[str] = Field(default_factory=list, description="Exported names")
    line_count: int = Field(..., description="Total lines in file")
    last_modified: datetime = Field(..., description="Last modified timestamp")
    content_hash: str = Field(..., description="Hash for change detection")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return normalize_path(v)


class ModuleEntity(BaseEntity):
    """Python module (directory with __init__.py) or logical package."""
    entity_type: str = Field(default="module", frozen=True)
    path: str = Field(..., description="Module path relative to project root")
    name: str = Field(..., description="Module name")
    purpose: str = Field(..., description="Module purpose from docstring")
    is_package: bool = Field(default=False, description="Whether this is a package/directory")
    submodules: List[str] = Field(default_factory=list, description="List of submodule paths")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return normalize_path(v)


class ClassEntity(BaseEntity):
    """Class definition."""
    entity_type: str = Field(default="class", frozen=True)
    file_path: str = Field(..., description="File path containing the class")
    name: str = Field(..., description="Class name")
    full_name: str = Field(..., description="Fully qualified name (module.ClassName)")
    purpose: str = Field(..., description="Class purpose from docstring")
    methods: List[str] = Field(default_factory=list, description="List of method names")
    bases: List[str] = Field(default_factory=list, description="Parent classes")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return normalize_path(v)


class FunctionEntity(BaseEntity):
    """Function or method definition."""
    entity_type: str = Field(default="function", frozen=True)
    file_path: str = Field(..., description="File path containing the function")
    name: str = Field(..., description="Function/method name")
    full_name: str = Field(..., description="Fully qualified name")
    signature: str = Field(..., description="Parameters and return type")
    purpose: str = Field(..., description="Function purpose from docstring")
    is_async: bool = Field(default=False, description="Whether function is async")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return normalize_path(v)


class PlanningDocEntity(BaseEntity):
    """Planning, documentation, or operational document."""
    entity_type: str = Field(default="planning_doc", frozen=True)
    path: str = Field(..., description="Document path relative to project root")
    doc_type: str = Field(..., description="Document type (PLAN, SUMMARY, CONTEXT, etc.)")
    phase_number: Optional[str] = Field(None, description="Phase number if applicable")
    plan_number: Optional[str] = Field(None, description="Plan number if applicable")
    title: str = Field(..., description="Document title")
    goal: Optional[str] = Field(None, description="Document goal")
    status: Optional[str] = Field(None, description="Implementation status")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return normalize_path(v)


# ===========================================
# Edge Types
# ===========================================

class CodebaseEdgeType(str, Enum):
    IMPORTS = "imports"
    CONTAINS = "contains"
    CALLS = "calls"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    REFERENCES = "references"


class ImportsEdge(BaseEdge):
    """File imports another file or module."""
    edge_type: str = Field(default=CodebaseEdgeType.IMPORTS.value, frozen=True)
    from_file: str = Field(..., description="Importing file path")
    to_file: str = Field(..., description="Imported file/module path")
    import_type: str = Field(..., description="Import style (absolute, relative, from_import)")
    imported_names: List[str] = Field(default_factory=list, description="Names imported")


class ContainsEdge(BaseEdge):
    """Module contains a file, or File contains a class/function."""
    edge_type: str = Field(default=CodebaseEdgeType.CONTAINS.value, frozen=True)
    container_path: str = Field(..., description="Container path")
    contained_path: str = Field(..., description="Contained path or full name")
    container_type: str = Field(..., description="Type of container (module, file, class)")


class CallsEdge(BaseEdge):
    """Function calls another function/method."""
    edge_type: str = Field(default=CodebaseEdgeType.CALLS.value, frozen=True)
    caller: str = Field(..., description="Calling function full_name")
    callee: str = Field(..., description="Called function full_name")
    call_count: int = Field(default=1, description="Number of times called")


class InheritsEdge(BaseEdge):
    """Class inherits from another class."""
    edge_type: str = Field(default=CodebaseEdgeType.INHERITS.value, frozen=True)
    child_class: str = Field(..., description="Child class full_name")
    parent_class: str = Field(..., description="Parent class full_name")


class ImplementsEdge(BaseEdge):
    """Code entity implements a planning doc requirement."""
    edge_type: str = Field(default=CodebaseEdgeType.IMPLEMENTS.value, frozen=True)
    code_path: str = Field(..., description="Code path or full_name")
    plan_path: str = Field(..., description="Planning doc path")
    evidence: str = Field(..., description="Commit message or comment evidence")


class ReferencesEdge(BaseEdge):
    """Code references a planning doc, or vice versa."""
    edge_type: str = Field(default=CodebaseEdgeType.REFERENCES.value, frozen=True)
    code_path: str = Field(..., description="Code path or full_name")
    doc_path: str = Field(..., description="Document path")
    reference_type: str = Field(..., description="Reference type (comment, docstring, commit)")
