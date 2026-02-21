"""
Git commit message parser for extracting phase and plan references.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CommitInfo:
    """Extracted information from a git commit message."""
    message: str
    commit_type: Optional[str] = None  # feat, fix, docs, refactor, etc.
    phase_number: Optional[str] = None  # "13.2", "14", "12"
    plan_number: Optional[str] = None  # "03", "01"
    requirement_id: Optional[str] = None  # "CHAT-05", "GRAPH-01"
    description: str = ""  # Rest of message


# Phase-plan pattern: (13.2-03), (14-01)
PHASE_PLAN_PATTERN = r'\((\d+\.?\d*)-(\d+)\)'

# Phase-only pattern: (phase-12), (Phase 12)
PHASE_ONLY_PATTERN = r'\((?:phase[- ]?)(\d+\.?\d*)\)'

# Requirement pattern: (CHAT-05), (GRAPH-01), or just CHAT-05
REQUIREMENT_PATTERN = r'(?:\()?([A-Z]+-\d+)(?:\))?'

# Commit type pattern: feat(scope): message or feat: message
COMMIT_TYPE_PATTERN = r'^(\w+)(?:\(.*\))?!?:'


def parse_commit_message(message: str) -> CommitInfo:
    """
    Parse a commit message to extract phase, plan, and requirement references.
    
    Args:
        message: The full commit message string.
        
    Returns:
        CommitInfo object with extracted metadata.
    """
    first_line = message.split('\n')[0].strip()
    
    commit_type = None
    type_match = re.match(COMMIT_TYPE_PATTERN, first_line)
    if type_match:
        commit_type = type_match.group(1)
        
    phase_number = None
    plan_number = None
    requirement_id = None
    
    # Check for Phase-Plan pattern: (13.2-03)
    pp_match = re.search(PHASE_PLAN_PATTERN, first_line)
    if pp_match:
        phase_number = pp_match.group(1)
        plan_number = pp_match.group(2)
        
    # Check for Phase-only if no phase found yet: (phase-12)
    if not phase_number:
        p_match = re.search(PHASE_ONLY_PATTERN, first_line, re.IGNORECASE)
        if p_match:
            phase_number = p_match.group(1)
            
    # Check for Requirement pattern: (CHAT-05)
    req_match = re.search(REQUIREMENT_PATTERN, first_line)
    if req_match:
        requirement_id = req_match.group(1)
        
    # Extract description (remove the type prefix if present)
    description = first_line
    if type_match:
        description = first_line[type_match.end():].strip()
        
    return CommitInfo(
        message=message,
        commit_type=commit_type,
        phase_number=phase_number,
        plan_number=plan_number,
        requirement_id=requirement_id,
        description=description
    )


def get_commits_for_files(file_paths: List[str]) -> List[CommitInfo]:
    """
    Get commit information for a list of files using git log.
    
    Args:
        file_paths: List of file paths relative to project root.
        
    Returns:
        List of CommitInfo objects for commits affecting these files.
    """
    commits = []
    seen_shas = set()
    
    for path in file_paths:
        try:
            # Get git log for the file
            # Format: %H (hash), %s (subject), %b (body)
            # Use --follow to track renames
            result = subprocess.run(
                ["git", "log", "--follow", "--format=%H%n%s%n%b%n---END-COMMIT---", "--", path],
                capture_output=True,
                text=True,
                check=True
            )
            
            commit_blocks = result.stdout.split("---END-COMMIT---\n")
            for block in commit_blocks:
                if not block.strip():
                    continue
                    
                lines = block.strip().split('\n')
                if len(lines) < 2:
                    continue
                    
                sha = lines[0].strip()
                if sha in seen_shas:
                    continue
                seen_shas.add(sha)
                
                message = "\n".join(lines[1:])
                commits.append(parse_commit_message(message))
                
        except subprocess.CalledProcessError:
            # Likely not a git repo or file not found in git
            continue
            
    return commits
