"""
Planning linker for connecting code to planning documents.
"""

import os
import re
from dataclasses import dataclass
from typing import List, Optional
from src.core.codebase_entities import ImplementsEdge, ReferencesEdge
from src.graph.commit_parser import CommitInfo


@dataclass
class PlanningLink:
    """Represents a discovered link between code and a planning document."""
    code_path: str
    plan_path: str
    link_type: str  # "implements" or "references"
    evidence: str   # commit SHA or line content
    confidence: float  # 1.0 for commit-based, 0.8 for natural reference


# Patterns for natural references in comments/docstrings
NATURAL_REFERENCE_PATTERNS = [
    # Related to Phase 13.2-01
    r'[Rr]elated to [Pp]hase (\d+\.?\d*)-?(\d+)?',
    # See .planning/phases/...
    r'[Ss]ee (\.planning/phases/[^/\s]+/[^/\s]+)',
    # Implements CHAT-05
    r'[Ii]mplements ([A-Z]+-\d+)',
    # Per Phase 14
    r'[Pp]er [Pp]hase (\d+\.?\d*)',
    # Phase 14-01
    r'Phase (\d+\.?\d*)-(\d+)',
]


def resolve_plan_path(phase: str, plan: Optional[str] = None) -> Optional[str]:
    """
    Resolve a phase and optional plan number to an actual file path.
    
    Args:
        phase: Phase number (e.g., "13.2", "14")
        plan: Optional plan number (e.g., "03", "01")
        
    Returns:
        Path to the planning document relative to project root, or None if not found.
    """
    phases_root = ".planning/phases"
    if not os.path.exists(phases_root):
        return None
        
    # Find the directory for the phase
    # Directories might be named "14-continuous-optimization-learning" or just "14"
    phase_dirs = []
    for d in os.listdir(phases_root):
        if d.startswith(f"{phase}-") or d == phase:
            phase_dirs.append(os.path.join(phases_root, d))
            
    if not phase_dirs:
        return None
        
    # We'll take the first matching directory
    phase_dir = phase_dirs[0]
    
    if plan:
        # Look for PLAN file: 14-01-PLAN.md
        pattern = f"{phase}-{plan}-PLAN.md"
        plan_path = os.path.join(phase_dir, pattern)
        if os.path.exists(plan_path):
            return plan_path.replace('\\', '/')
            
    # If no plan specified or plan file not found, return the CONTEXT or README or the dir itself
    for alt in [f"{phase}-CONTEXT.md", "README.md"]:
        alt_path = os.path.join(phase_dir, alt)
        if os.path.exists(alt_path):
            return alt_path.replace('\\', '/')
            
    return os.path.join(phases_root, os.path.basename(phase_dir)).replace('\\', '/')


def link_commit_to_plan(
    commit_info: CommitInfo,
    changed_files: List[str]
) -> List[ImplementsEdge]:
    """
    Link all changed files to the planning doc referenced in commit.
    
    Args:
        commit_info: Parsed commit information.
        changed_files: List of file paths modified in the commit.
        
    Returns:
        List of ImplementsEdge objects.
    """
    if not commit_info.phase_number:
        return []
        
    plan_path = resolve_plan_path(commit_info.phase_number, commit_info.plan_number)
    if not plan_path:
        return []
        
    edges = []
    for file_path in changed_files:
        edges.append(ImplementsEdge(
            from_entity_id=file_path,
            to_entity_id=plan_path,
            code_path=file_path,
            plan_path=plan_path,
            evidence=f"Commit: {commit_info.message.split('\n')[0]}"
        ))
        
    return edges


def detect_natural_references(
    file_content: str,
    file_path: str
) -> List[ReferencesEdge]:
    """
    Detect natural references to planning docs in code comments or docstrings.
    
    Args:
        file_content: The content of the file to scan.
        file_path: Path of the file being scanned.
        
    Returns:
        List of ReferencesEdge objects.
    """
    edges = []
    lines = file_content.split('\n')
    
    for i, line in enumerate(lines):
        line_paths = set()
        for pattern in NATURAL_REFERENCE_PATTERNS:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                doc_path = None
                
                # Determine what kind of match it was
                if ".planning/phases/" in line:
                    # Direct path match
                    doc_path = match.group(1) if len(groups) > 0 else None
                elif len(groups) >= 1 and groups[0] and groups[0][0].isdigit():
                    # Phase match
                    phase = groups[0]
                    plan = groups[1] if len(groups) > 1 else None
                    doc_path = resolve_plan_path(phase, plan)
                elif groups[0] and "-" in groups[0]:
                    # Requirement ID match (e.g., CHAT-05)
                    pass
                
                if doc_path and os.path.exists(doc_path):
                    doc_path = doc_path.replace('\\', '/')
                    if doc_path not in line_paths:
                        edges.append(ReferencesEdge(
                            from_entity_id=file_path,
                            to_entity_id=doc_path,
                            code_path=file_path,
                            doc_path=doc_path,
                            reference_type="comment",
                            evidence=f"Line {i+1}: {line.strip()}"
                        ))
                        line_paths.add(doc_path)
                    
    return edges
