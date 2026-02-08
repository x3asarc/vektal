"""
Product Intent Handler

Handles product-related intents without LLM overhead.
Returns structured data for API consumption.

Phase 5: Called by ChatRouter, response returned as JSON
Phase 10: Response rendered in React chat component
"""

import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ProductHandler:
    """
    Handles product-related intents.

    Generates responses from structured data, no LLM needed.
    """

    def __init__(self, database_path: str = None):
        """
        Initialize product handler.

        Args:
            database_path: Path to SQLite database
        """
        if database_path is None:
            database_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "products.db"

        self.database_path = str(database_path)

    def handle_add_product(self, intent) -> dict:
        """
        Handle ADD_PRODUCT intent.

        Args:
            intent: Intent with SKU entity

        Returns:
            Structured response for product addition workflow
        """
        sku = intent.entities.get('sku')

        if not sku:
            return {
                "status": "error",
                "message": "No SKU provided. Please provide a SKU to add.",
                "example": "R0530"
            }

        # Check if product already exists
        existing = self._check_product_exists(sku)

        if existing:
            return {
                "status": "exists",
                "sku": sku,
                "message": f"Product {sku} already exists",
                "product": existing,
                "actions": [
                    {
                        "type": "update",
                        "label": "Update product",
                        "command": f"update {sku}"
                    },
                    {
                        "type": "view",
                        "label": "View details",
                        "url": f"/products/{sku}"
                    }
                ]
            }

        # Product doesn't exist - initiate scraping workflow
        return {
            "status": "pending",
            "sku": sku,
            "message": f"Initiating scraping for {sku}",
            "workflow": {
                "step": 1,
                "total_steps": 4,
                "current": "vendor_discovery",
                "steps": [
                    "Discover vendor",
                    "Extract product data",
                    "Process images",
                    "Generate SEO content"
                ]
            },
            "actions": [
                {
                    "type": "monitor",
                    "label": "Monitor progress",
                    "url": f"/status/{sku}"
                }
            ]
        }

    def handle_update_product(self, intent) -> dict:
        """
        Handle UPDATE_PRODUCT intent.

        Args:
            intent: Intent with SKU entity

        Returns:
            Structured response for product update workflow
        """
        sku = intent.entities.get('sku')

        if not sku:
            return {
                "status": "error",
                "message": "No SKU provided. Please provide a SKU to update.",
                "example": "update R0530"
            }

        # Check if product exists
        existing = self._check_product_exists(sku)

        if not existing:
            return {
                "status": "not_found",
                "sku": sku,
                "message": f"Product {sku} not found",
                "suggestion": "Would you like to add it?",
                "actions": [
                    {
                        "type": "add",
                        "label": "Add product",
                        "command": f"add {sku}"
                    }
                ]
            }

        # Product exists - initiate refresh
        return {
            "status": "refreshing",
            "sku": sku,
            "message": f"Refreshing product {sku}",
            "current_data": existing,
            "workflow": {
                "step": 1,
                "total_steps": 3,
                "current": "re_scrape",
                "steps": [
                    "Re-scrape vendor data",
                    "Update images",
                    "Refresh SEO content"
                ]
            },
            "actions": [
                {
                    "type": "monitor",
                    "label": "Monitor progress",
                    "url": f"/status/{sku}"
                }
            ]
        }

    def _check_product_exists(self, sku: str) -> Optional[dict]:
        """
        Check if product exists in database.

        Args:
            sku: Product SKU

        Returns:
            Product data if exists, None otherwise
        """
        try:
            import sqlite3
            from pathlib import Path

            db_path = Path(self.database_path)
            if not db_path.exists():
                return None

            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT sku, title, vendor_url, status, last_updated
                FROM products
                WHERE sku = ?
            """, (sku,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "sku": row["sku"],
                    "title": row["title"],
                    "vendor_url": row["vendor_url"],
                    "status": row["status"],
                    "last_updated": row["last_updated"]
                }

            return None

        except Exception as e:
            logger.error(f"Database error checking product: {e}")
            return None
