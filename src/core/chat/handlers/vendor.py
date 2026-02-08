"""
Vendor Intent Handler

Handles vendor-related intents without LLM overhead.
Returns structured data for API consumption.

Phase 5: Called by ChatRouter, response returned as JSON
Phase 10: Response rendered in React chat component
"""

import logging
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class VendorHandler:
    """
    Handles vendor-related intents.

    Generates responses from structured data, no LLM needed.
    """

    def __init__(self, database_path: str = None):
        """
        Initialize vendor handler.

        Args:
            database_path: Path to SQLite database
        """
        if database_path is None:
            database_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "products.db"

        self.database_path = str(database_path)

    def handle_search_vendor(self, intent) -> dict:
        """
        Handle SEARCH_VENDOR intent.

        Args:
            intent: Intent with SKU entity

        Returns:
            Structured response with vendor info
        """
        sku = intent.entities.get('sku')

        if not sku:
            return {
                "status": "error",
                "message": "No SKU provided. Please provide a SKU to search.",
                "example": "find vendor for R0530"
            }

        # Look up vendor for product
        vendor = self._find_vendor_for_sku(sku)

        if not vendor:
            return {
                "status": "not_found",
                "sku": sku,
                "message": f"No vendor found for {sku}",
                "suggestion": "Product may not be in system yet",
                "actions": [
                    {
                        "type": "add",
                        "label": "Add product",
                        "command": f"add {sku}"
                    }
                ]
            }

        return {
            "status": "found",
            "sku": sku,
            "vendor": vendor,
            "actions": [
                {
                    "type": "visit",
                    "label": "Visit vendor page",
                    "url": vendor.get("product_url")
                },
                {
                    "type": "view_all",
                    "label": f"View all {vendor.get('domain')} products",
                    "url": f"/vendors/{vendor.get('domain')}"
                }
            ]
        }

    def handle_discover_vendor(self, intent) -> dict:
        """
        Handle DISCOVER_VENDOR intent.

        Args:
            intent: Intent with target URL/domain entity

        Returns:
            Structured response for vendor discovery workflow
        """
        target = intent.entities.get('target')

        if not target:
            return {
                "status": "error",
                "message": "No vendor URL or domain provided",
                "example": "discover vendor https://example.com"
            }

        # Check if vendor already known
        existing = self._check_vendor_exists(target)

        if existing:
            return {
                "status": "known",
                "vendor": existing,
                "message": f"Vendor {existing['domain']} is already configured",
                "stats": {
                    "products": existing.get("product_count", 0),
                    "success_rate": existing.get("success_rate", 0)
                },
                "actions": [
                    {
                        "type": "view",
                        "label": "View products",
                        "url": f"/vendors/{existing['domain']}"
                    }
                ]
            }

        # New vendor - initiate discovery
        return {
            "status": "discovering",
            "target": target,
            "message": f"Analyzing vendor site: {target}",
            "workflow": {
                "step": 1,
                "total_steps": 5,
                "current": "site_analysis",
                "steps": [
                    "Analyze site structure",
                    "Detect product patterns",
                    "Extract selectors",
                    "Test extraction",
                    "Generate config"
                ]
            },
            "actions": [
                {
                    "type": "monitor",
                    "label": "Monitor discovery",
                    "url": f"/vendors/discover?target={target}"
                }
            ]
        }

    def handle_list_vendors(self, intent) -> dict:
        """
        Handle LIST_VENDORS intent.

        Args:
            intent: Intent

        Returns:
            Structured response with vendor list
        """
        vendors = self._get_all_vendors()

        if not vendors:
            return {
                "status": "empty",
                "message": "No vendors configured yet",
                "suggestion": "Discover a vendor to get started",
                "example": "discover vendor https://example.com"
            }

        return {
            "status": "success",
            "count": len(vendors),
            "vendors": vendors,
            "actions": [
                {
                    "type": "discover",
                    "label": "Add new vendor",
                    "command": "discover vendor"
                }
            ]
        }

    def _find_vendor_for_sku(self, sku: str) -> Optional[dict]:
        """
        Find vendor for a specific SKU.

        Args:
            sku: Product SKU

        Returns:
            Vendor info if found, None otherwise
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
                SELECT vendor_url, vendor_domain
                FROM products
                WHERE sku = ?
            """, (sku,))

            row = cursor.fetchone()
            conn.close()

            if row and row["vendor_url"]:
                # Extract domain from URL
                from urllib.parse import urlparse
                parsed = urlparse(row["vendor_url"])
                domain = parsed.netloc or row.get("vendor_domain", "unknown")

                return {
                    "domain": domain,
                    "product_url": row["vendor_url"]
                }

            return None

        except Exception as e:
            logger.error(f"Database error finding vendor: {e}")
            return None

    def _check_vendor_exists(self, target: str) -> Optional[dict]:
        """
        Check if vendor exists in config.

        Args:
            target: URL or domain

        Returns:
            Vendor info if exists, None otherwise
        """
        try:
            from urllib.parse import urlparse

            # Extract domain
            if target.startswith('http'):
                domain = urlparse(target).netloc
            else:
                domain = target.strip()

            # Check vendor configs
            config_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "vendors"
            if not config_dir.exists():
                return None

            import json

            for config_file in config_dir.glob("*.json"):
                with open(config_file, 'r') as f:
                    config = json.load(f)

                    if domain in config.get('domain', '') or domain in config.get('base_url', ''):
                        return {
                            "domain": config.get('domain'),
                            "name": config.get('name'),
                            "product_count": 0,  # Would need to query database
                            "success_rate": 0    # Would need to query database
                        }

            return None

        except Exception as e:
            logger.error(f"Error checking vendor: {e}")
            return None

    def _get_all_vendors(self) -> List[dict]:
        """
        Get all configured vendors.

        Returns:
            List of vendor info dicts
        """
        try:
            config_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "vendors"
            if not config_dir.exists():
                return []

            import json
            vendors = []

            for config_file in config_dir.glob("*.json"):
                with open(config_file, 'r') as f:
                    config = json.load(f)

                    vendors.append({
                        "domain": config.get('domain'),
                        "name": config.get('name'),
                        "base_url": config.get('base_url'),
                        "status": "active",
                        "product_count": 0  # Would need to query database
                    })

            return vendors

        except Exception as e:
            logger.error(f"Error listing vendors: {e}")
            return []
