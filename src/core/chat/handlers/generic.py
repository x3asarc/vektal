"""
Generic Intent Handler

Handles generic intents (help, status) without LLM overhead.
Returns structured data for API consumption.

Phase 5: Called by ChatRouter, response returned as JSON
Phase 10: Response rendered in React chat component
"""

import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class GenericHandler:
    """
    Handles generic intents.

    Generates responses from static data, no LLM or database needed.
    """

    @staticmethod
    def _build_unknown_message(raw_message: str) -> str:
        text = (raw_message or "").strip().lower()
        if re.search(r"\b(hi|hello|hey|yo|sup|what'?s up|whats up)\b", text):
            return (
                "Hey! I am here and ready to help. "
                "Tell me what you want to do with your products, and I can guide you step by step."
            )
        if re.search(r"\b(thanks|thank you|thx)\b", text):
            return "Anytime. If you want, I can help you add, update, or review products next."
        if re.search(r"\b(who are you|what can you do|capabilities|can you help)\b", text):
            return (
                "I can help with product operations like adding SKUs, updating product data, "
                "finding vendors, and checking system state."
            )
        if re.search(
            r"\b(what should i give you|what should i type|what do you need|what can i provide|how should i ask)\b",
            text,
        ):
            return (
                "Tell me the outcome you want in plain language. "
                "For example: 'add SKU R0530', 'find vendor for R0530', or 'update R0530'."
            )
        if re.search(
            r"\b(where do i start|how do i start|get started|not sure where to start|don't know where to start|dont know where to start)\b",
            text,
        ):
            return (
                "Start with one specific outcome. "
                "For example: add one SKU, update one SKU, or ask me to find a vendor for one SKU."
            )
        return (
            "I did not map that to a concrete product operation yet, "
            "but I can still help you get to the right action quickly."
        )

    def handle_help(self, intent) -> dict:
        """
        Handle HELP intent.

        Args:
            intent: Intent

        Returns:
            Structured help response
        """
        return {
            "status": "success",
            "message": "Available commands",
            "commands": [
                {
                    "category": "Product Management",
                    "items": [
                        {
                            "command": "R0530",
                            "description": "Add product by SKU",
                            "example": "R0530"
                        },
                        {
                            "command": "add sku: R0530",
                            "description": "Add product (explicit)",
                            "example": "add sku: R0530"
                        },
                        {
                            "command": "update R0530",
                            "description": "Refresh product data",
                            "example": "update R0530"
                        }
                    ]
                },
                {
                    "category": "Vendor Management",
                    "items": [
                        {
                            "command": "find vendor for R0530",
                            "description": "Look up vendor for SKU",
                            "example": "find vendor for R0530"
                        },
                        {
                            "command": "discover vendor <url>",
                            "description": "Learn new vendor site",
                            "example": "discover vendor https://example.com"
                        },
                        {
                            "command": "list vendors",
                            "description": "Show all vendors",
                            "example": "list vendors"
                        }
                    ]
                },
                {
                    "category": "System",
                    "items": [
                        {
                            "command": "status",
                            "description": "Check system status",
                            "example": "status"
                        },
                        {
                            "command": "help",
                            "description": "Show this help",
                            "example": "help"
                        }
                    ]
                }
            ],
            "tips": [
                "Just type a SKU (like R0530) to add it quickly",
                "Use natural language: 'who sells R0530?' works too"
            ]
        }

    def handle_status(self, intent) -> dict:
        """
        Handle GET_STATUS intent.

        Args:
            intent: Intent

        Returns:
            Structured status response
        """
        # Get system statistics
        stats = self._get_system_stats()

        return {
            "status": "success",
            "message": "System status",
            "stats": stats,
            "health": {
                "database": "ok" if stats.get("products_total", 0) >= 0 else "error",
                "vendors": "ok" if stats.get("vendors_configured", 0) > 0 else "warning",
                "status_message": self._get_health_message(stats)
            },
            "actions": [
                {
                    "type": "view_products",
                    "label": "View all products",
                    "url": "/products"
                },
                {
                    "type": "view_vendors",
                    "label": "View vendors",
                    "url": "/vendors"
                }
            ]
        }

    def handle_unknown(self, intent) -> dict:
        """
        Handle UNKNOWN intent.

        Args:
            intent: Intent

        Returns:
            Structured response with guidance on supported commands
        """
        message = self._build_unknown_message(getattr(intent, "raw_message", ""))
        return {
            "status": "unknown",
            "message": message,
            "suggestions": [
                "Add a product by SKU, e.g. R0530",
                "Find supplier for a SKU, e.g. find vendor for R0530",
                "Update a product, e.g. update R0530",
                "See configured suppliers with: list vendors",
                "Check platform state with: status",
            ]
        }

    def _get_system_stats(self) -> dict:
        """
        Get system statistics.

        Returns:
            Stats dictionary
        """
        try:
            import sqlite3
            from pathlib import Path

            # Check products database
            db_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "products.db"
            products_total = 0
            products_pending = 0
            products_complete = 0

            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM products")
                products_total = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM products WHERE status = 'pending'")
                products_pending = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM products WHERE status = 'complete'")
                products_complete = cursor.fetchone()[0]

                conn.close()

            # Check vendor configs
            config_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "vendors"
            vendors_configured = 0

            if config_dir.exists():
                vendors_configured = len(list(config_dir.glob("*.json")))

            return {
                "products_total": products_total,
                "products_pending": products_pending,
                "products_complete": products_complete,
                "vendors_configured": vendors_configured
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "products_total": 0,
                "products_pending": 0,
                "products_complete": 0,
                "vendors_configured": 0,
                "error": str(e)
            }

    def _get_health_message(self, stats: dict) -> str:
        """
        Get health status message.

        Args:
            stats: System stats

        Returns:
            Health message
        """
        if stats.get("error"):
            return "System error - database not accessible"

        if stats.get("vendors_configured", 0) == 0:
            return "No vendors configured - discover a vendor to start"

        if stats.get("products_total", 0) == 0:
            return "No products yet - add a SKU to start"

        pending = stats.get("products_pending", 0)
        if pending > 0:
            return f"System operational - {pending} products processing"

        return "System operational - all products up to date"
