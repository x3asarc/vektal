"""
Periodic consistency daemon for graph/filesystem synchronization.

Detects divergence between the codebase knowledge graph and the actual filesystem,
providing repair logic for missing, stale, or modified files.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import os
import time
import hashlib
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.core.graphiti_client import get_graphiti_client
from src.graph.codebase_scanner import scan_codebase, ScanConfig

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyReport:
    """Report of divergence between graph and filesystem."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    files_in_filesystem: int = 0
    files_in_graph: int = 0
    missing_from_graph: List[str] = field(default_factory=list)  # Files on disk but not in graph
    stale_in_graph: List[str] = field(default_factory=list)      # Files in graph but not on disk
    hash_mismatches: List[str] = field(default_factory=list)     # Files changed since last sync
    graph_last_sync: Optional[datetime] = None
    is_consistent: bool = True
    duration_seconds: float = 0.0


@dataclass
class RepairResult:
    """Result of a repair operation."""
    files_added: int = 0
    files_removed: int = 0
    files_updated: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = True


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of file content."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error computing hash for {file_path}: {e}")
        return ""


def check_consistency(include_dirs: List[str] = None, exclude_patterns: List[str] = None) -> ConsistencyReport:
    """
    Check consistency between the filesystem and the knowledge graph.
    
    Args:
        include_dirs: List of directories to scan (default: all major project directories)
        exclude_patterns: List of patterns to exclude
        
    Returns:
        ConsistencyReport detailing any divergence.
    """
    start_time = time.time()
    report = ConsistencyReport()
    
    if include_dirs is None:
        include_dirs = [
            "src", "tests", ".planning", "docs", "frontend", "scripts", 
            "migrations", "config", "ops", "reports", "seo", "utils", "web"
        ]
    
    if exclude_patterns is None:
        exclude_patterns = ["__pycache__", ".git", "node_modules", ".venv", "venv", ".next", "dist", "build"]
        
    # 1. Scan filesystem
    files_on_disk = {}
    
    # 1a. Scan Root Files (Non-recursive)
    for filename in os.listdir("."):
        if os.path.isfile(filename):
            # Skip excluded patterns
            if any(excl in filename for excl in exclude_patterns):
                continue
            files_on_disk[filename] = compute_file_hash(filename)

    # 1b. Scan Directories
    for include_dir in include_dirs:
        if not os.path.exists(include_dir):
            continue
        for root, dirs, filenames in os.walk(include_dir):
            # Filter directories
            dirs[:] = [d for d in dirs if not any(excl in os.path.join(root, d) for excl in exclude_patterns)]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, ".").replace('\\', '/')
                
                # Skip excluded patterns in file path
                if any(excl in rel_path for excl in exclude_patterns):
                    continue
                    
                files_on_disk[rel_path] = compute_file_hash(file_path)
                
    report.files_in_filesystem = len(files_on_disk)
    
    # 2. Query graph (simulated for now, would use Cypher in real Neo4j)
    # MATCH (f:File) RETURN f.path, f.content_hash
    client = get_graphiti_client()
    files_in_graph = {} # path -> hash
    
    if client:
        try:
            # This is where we would execute a real Cypher query
            # result = client.query("MATCH (f:File) RETURN f.path, f.content_hash")
            # for record in result:
            #     files_in_graph[record['f.path']] = record['f.content_hash']
            pass
        except Exception as e:
            logger.error(f"Error querying graph for consistency: {e}")
            
    report.files_in_graph = len(files_in_graph)
    
    # 3. Compare
    disk_paths = set(files_on_disk.keys())
    graph_paths = set(files_in_graph.keys())
    
    report.missing_from_graph = sorted(list(disk_paths - graph_paths))
    report.stale_in_graph = sorted(list(graph_paths - disk_paths))
    
    # Check for hash mismatches in common files
    common_paths = disk_paths & graph_paths
    for path in common_paths:
        if files_on_disk[path] != files_in_graph[path]:
            report.hash_mismatches.append(path)
            
    report.is_consistent = not (report.missing_from_graph or report.stale_in_graph or report.hash_mismatches)
    report.duration_seconds = time.time() - start_time
    
    return report


def repair_divergence(report: ConsistencyReport, dry_run: bool = True) -> RepairResult:
    """
    Repair divergence detected by the consistency checker.
    
    Args:
        report: The ConsistencyReport to act upon.
        dry_run: If True, only simulate the repair.
        
    Returns:
        RepairResult with counts of actions taken.
    """
    result = RepairResult(dry_run=dry_run)
    
    # 1. Add missing files
    for path in report.missing_from_graph:
        result.files_added += 1
        if not dry_run:
            # In a real impl, we would scan and add to graph
            # scan_res = scan_codebase(".", ScanConfig(include_dirs=[os.path.dirname(path)]))
            pass
            
    # 2. Remove stale entries (soft delete)
    for path in report.stale_in_graph:
        result.files_removed += 1
        if not dry_run:
            # Mark as status: removed in Neo4j
            pass
            
    # 3. Update changed files
    for path in report.hash_mismatches:
        result.files_updated += 1
        if not dry_run:
            # Re-parse and update in Neo4j
            pass
            
    return result
