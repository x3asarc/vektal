"""
Pentart Product Database Module

Provides access to the Pentart product catalog stored in SQLite database.
"""

import sqlite3
import os
from typing import Optional, Dict, List


class PentartDatabase:
    """Interface to the Pentart products catalog database."""

    def __init__(self, db_path: str = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            from src.core.paths import DB_PATH
            db_path = DB_PATH
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def get_by_article_number(self, article_number: str) -> Optional[Dict]:
        """
        Lookup product by article number (SKU).

        Args:
            article_number: Product SKU/article number

        Returns:
            Dictionary with product data or None if not found
        """
        if not article_number:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Clean article number (strip whitespace)
            article_number = str(article_number).strip()

            cursor.execute(
                "SELECT * FROM pentart_products WHERE article_number = ?",
                (article_number,)
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

        finally:
            conn.close()

    def get_by_ean(self, ean: str) -> Optional[Dict]:
        """
        Lookup product by EAN barcode.

        Args:
            ean: Product EAN/barcode

        Returns:
            Dictionary with product data or None if not found
        """
        if not ean:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Clean EAN (strip whitespace)
            ean = str(ean).strip()

            cursor.execute(
                "SELECT * FROM pentart_products WHERE ean = ?",
                (ean,)
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

        finally:
            conn.close()

    def search_by_description(self, query: str) -> List[Dict]:
        """
        Search products by description (case-insensitive partial match).

        Args:
            query: Search term

        Returns:
            List of matching products
        """
        if not query:
            return []

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM pentart_products WHERE description LIKE ? ORDER BY description",
                (f"%{query}%",)
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_all_products(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get all products from the catalog.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of all products
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if limit:
                cursor.execute(
                    "SELECT * FROM pentart_products ORDER BY id LIMIT ?",
                    (limit,)
                )
            else:
                cursor.execute("SELECT * FROM pentart_products ORDER BY id")

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def search_by_article_prefix(self, prefix: str, limit: int = 50) -> List[Dict]:
        """
        Find products by article number prefix.
        
        Useful for finding products in the same product group.
        Example: prefix "400" finds all products with article numbers 40000-40099.
        
        Args:
            prefix: Article number prefix to search for
            limit: Maximum number of results
            
        Returns:
            List of matching products
        """
        if not prefix:
            return []
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT * FROM pentart_products 
                   WHERE article_number LIKE ? 
                   ORDER BY article_number
                   LIMIT ?""",
                (f"{prefix}%", limit)
            )
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        
        finally:
            conn.close()

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Dictionary with counts and statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            stats = {}

            # Total products
            cursor.execute("SELECT COUNT(*) as count FROM pentart_products")
            stats['total_products'] = cursor.fetchone()['count']

            # Products with EAN
            cursor.execute("SELECT COUNT(*) as count FROM pentart_products WHERE ean IS NOT NULL AND ean != ''")
            stats['products_with_ean'] = cursor.fetchone()['count']

            # Products with weight
            cursor.execute("SELECT COUNT(*) as count FROM pentart_products WHERE product_weight IS NOT NULL")
            stats['products_with_weight'] = cursor.fetchone()['count']

            # Products with article number
            cursor.execute("SELECT COUNT(*) as count FROM pentart_products WHERE article_number IS NOT NULL AND article_number != ''")
            stats['products_with_article_number'] = cursor.fetchone()['count']

            return stats

        finally:
            conn.close()
