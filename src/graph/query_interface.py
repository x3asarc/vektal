"""
Unified query interface for LLMs to interact with the knowledge graph.

Provides template-based queries for common developer/AI tasks and
natural language fallback for more complex scenarios.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import os
import time
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.core.graphiti_client import get_graphiti_client
from src.graph.query_templates import QUERY_TEMPLATES, execute_template

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a knowledge graph query."""
    success: bool = False
    data: List[Dict[str, Any]] = field(default_factory=list)
    query_type: str = "template"  # "template" or "natural_language"
    template_used: Optional[str] = None
    cypher_generated: Optional[str] = None  # For natural language
    duration_ms: float = 0.0
    error: Optional[str] = None


def match_query_to_template(query: str) -> Optional[tuple]:
    """
    Match a natural language query to a pre-built template.
    
    Args:
        query: Natural language query string.
        
    Returns:
        (template_name, params) tuple or None if no match.
    """
    query = query.lower().strip()
    
    # "what imports X" or "X imported by" -> imports template
    if match := re.search(r'what imports ([\w/.-]+)', query):
        return "imports", {"file_path": match.group(1)}
    
    # "what does X depend on" or "X imports" -> imported_by template
    if match := re.search(r'what does ([\w/.-]+) depend on', query):
        return "imported_by", {"file_path": match.group(1)}
    
    # "find similar to X" -> similar_files template
    if match := re.search(r'find similar to ([\w/.-]+)', query):
        return "similar_files", {"file_path": match.group(1), "limit": 5, "threshold": 0.6}
    
    # "what implements Phase X" -> phase_code template
    if match := re.search(r'what implements phase ([\d.]+)', query):
        return "phase_code", {"phase": match.group(1)}
        
    # "impact radius of X" -> impact_radius template
    if match := re.search(r'impact radius of ([\w/.-]+)', query):
        return "impact_radius", {"file_path": match.group(1)}
        
    # "callers of function X" -> function_callers template
    if match := re.search(r'callers of function ([\w.]+)', query):
        return "function_callers", {"function_name": match.group(1)}
        
    return None


def query_graph(query: str, use_natural_language: bool = False) -> QueryResult:
    """
    Unified query interface for the codebase knowledge graph.
    
    Args:
        query: The query string (can be natural language or template name).
        use_natural_language: Whether to fallback to LLM-generated Cypher.
        
    Returns:
        QueryResult with data and metadata.
    """
    start_time = time.time()
    result = QueryResult()
    
    # 1. Try direct template match by name
    if query in QUERY_TEMPLATES:
        result.template_used = query
        result.data = execute_template(query, {})
        result.success = True
        result.duration_ms = (time.time() - start_time) * 1000
        return result
        
    # 2. Try matching natural language to a template
    template_match = match_query_to_template(query)
    if template_match:
        template_name, params = template_match
        result.template_used = template_name
        result.data = execute_template(template_name, params)
        result.success = True
        result.duration_ms = (time.time() - start_time) * 1000
        return result
        
    # 3. Fallback to natural language via LLM (if enabled)
    if use_natural_language:
        result.query_type = "natural_language"
        # cypher = generate_cypher_from_natural_language(query)
        # result.cypher_generated = cypher
        # result.data = execute_cypher(cypher)
        # result.success = True
        result.error = "Natural language querying not yet implemented"
        
    result.duration_ms = (time.time() - start_time) * 1000
    return result
