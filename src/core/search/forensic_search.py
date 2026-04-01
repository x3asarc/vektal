"""
Forensic Search Engine (Phase 20).

Provides high-performance PostgreSQL Full-Text Search (FTS) 
across isolated tenant schemas.
"""
from sqlalchemy import text, func
from src.models import db, Product, ProductEnrichment

class ForensicSearch:
    """
    Search engine for the Forensic Agent.
    Uses PostgreSQL tsvector and tsquery for 'Grep-like' speed 
    on the database level.
    """

    @staticmethod
    def search(query_str: str, limit: int = 50, offset: int = 0):
        """
        Perform a full-text search across Title, Description, and SKU.
        
        This respects the current PostgreSQL search_path (Tenant Isolation).
        """
        # We use a combined tsvector for search
        # A = Title (Highest weight)
        # B = SKU
        # C = Description
        # D = Enrichment SEO Description
        
        # PostgreSQL FTS Query
        # plainto_tsquery handles natural language input safely
        sql = text("""
            SELECT p.id, p.title, p.sku, p.vendor_code,
                   ts_rank_cd(
                       setweight(to_tsvector('english', coalesce(p.title, '')), 'A') ||
                       setweight(to_tsvector('english', coalesce(p.sku, '')), 'B') ||
                       setweight(to_tsvector('english', coalesce(p.description, '')), 'C'),
                       plainto_tsquery('english', :query)
                   ) AS rank
            FROM products p
            WHERE to_tsvector('english', coalesce(p.title, '') || ' ' || coalesce(p.sku, '') || ' ' || coalesce(p.description, '')) @@ plainto_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = db.session.execute(sql, {"query": query_str, "limit": limit, "offset": offset})
        
        products = []
        for row in result:
            products.append({
                "id": row.id,
                "title": row.title,
                "sku": row.sku,
                "vendor_code": row.vendor_code,
                "relevance": float(row.rank)
            })
            
        return products

    @staticmethod
    def forensic_grep(pattern: str, field: str = 'description'):
        """
        Performs a regex-like 'grep' using PostgreSQL POSIX regex.
        Useful for the Agent to find specific patterns (e.g., HTML tags, specific languages).
        """
        # Validate field to prevent injection (since it's an identifier)
        allowed_fields = ['title', 'description', 'sku', 'vendor_code']
        if field not in allowed_fields:
            field = 'description'
            
        sql = text(f"""
            SELECT id, title, sku, {field} as content
            FROM products
            WHERE {field} ~* :pattern
            LIMIT 100
        """)
        
        result = db.session.execute(sql, {"pattern": pattern})
        
        matches = []
        for row in result:
            matches.append({
                "id": row.id,
                "title": row.title,
                "sku": row.sku,
                "match_content": row.content[:200] + "..." if row.content and len(row.content) > 200 else row.content
            })
            
        return matches
