"""
Product Quality Orchestrator Agent

Monitors product completeness, identifies gaps, and dispatches repair jobs.

Usage:
    # Check single product
    python orchestrator/product_quality_agent.py --sku "ABC123"

    # Check and auto-repair
    python orchestrator/product_quality_agent.py --sku "ABC123" --auto-repair

    # Check all products that need attention
    python orchestrator/product_quality_agent.py --check-all --limit 50

    # Trigger after an operation
    python orchestrator/product_quality_agent.py --trigger "seo_update" --sku "ABC123"
"""

import os
import sys
import json
import yaml
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo.seo_generator import ShopifyClient


class ProductQualityAgent:
    """Orchestrates product quality checks and repairs."""

    def __init__(self, master_file=None, rules_file=None):
        if master_file is None:
            from src.core.paths import DATA_DIR
            master_file = str(DATA_DIR / "product_quality_master.json")
        if rules_file is None:
            from src.core.paths import PRODUCT_QUALITY_RULES_PATH
            rules_file = PRODUCT_QUALITY_RULES_PATH
        self.master_file = master_file
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self.master_data = self._load_master_data()
        self.shopify = None

    def _load_rules(self):
        """Load quality rules from YAML."""
        if not os.path.exists(self.rules_file):
            raise FileNotFoundError(f"Rules file not found: {self.rules_file}")

        with open(self.rules_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_master_data(self):
        """Load or create master tracking file."""
        if os.path.exists(self.master_file):
            with open(self.master_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"products": {}, "stats": {}, "last_updated": None}

    def _save_master_data(self):
        """Save master data to file."""
        os.makedirs(os.path.dirname(self.master_file) or ".", exist_ok=True)
        self.master_data["last_updated"] = datetime.now().isoformat()

        with open(self.master_file, 'w', encoding='utf-8') as f:
            json.dump(self.master_data, f, indent=2, ensure_ascii=False)

    def connect_shopify(self):
        """Connect to Shopify."""
        if not self.shopify:
            self.shopify = ShopifyClient()
            if not self.shopify.authenticate():
                raise Exception("Failed to authenticate with Shopify")

    def fetch_product_data(self, sku):
        """
        Fetch complete product data from Shopify including metafields.

        Returns dict with all product data needed for quality check.
        """
        self.connect_shopify()

        query = """
        query GetProduct($query: String!) {
          products(first: 1, query: $query) {
            edges {
              node {
                id
                title
                handle
                descriptionHtml
                vendor
                tags
                productType
                seo {
                  title
                  description
                }
                variants(first: 10) {
                  edges {
                    node {
                      sku
                      barcode
                    }
                  }
                }
                images(first: 20) {
                  edges {
                    node {
                      id
                      url
                    }
                  }
                }
                metafields(first: 50) {
                  edges {
                    node {
                      namespace
                      key
                      value
                    }
                  }
                }
                collections(first: 10) {
                  edges {
                    node {
                      id
                      title
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"query": f"sku:{sku}"}
        result = self.shopify.execute_graphql(query, variables)

        if not result or "data" not in result:
            return None

        edges = result["data"]["products"]["edges"]
        if not edges:
            return None

        node = edges[0]["node"]

        # Parse variants
        variants = [v["node"] for v in node.get("variants", {}).get("edges", [])]
        variant = variants[0] if variants else {}

        # Parse metafields
        metafields = {}
        for mf in node.get("metafields", {}).get("edges", []):
            mf_node = mf["node"]
            key = f"{mf_node['namespace']}.{mf_node['key']}"
            metafields[key] = mf_node["value"]

        # Parse images
        images = [img["node"] for img in node.get("images", {}).get("edges", [])]

        # Parse collections
        collections = [c["node"] for c in node.get("collections", {}).get("edges", [])]

        # Try to get weight from metafields if not in variant
        weight = metafields.get("custom.weight", 0)
        if not weight:
            weight = 0  # Weight not available in this API version

        # Get SEO data
        seo = node.get("seo", {}) or {}

        return {
            "id": node.get("id"),
            "sku": sku,
            "title": node.get("title", ""),
            "handle": node.get("handle", ""),
            "description_html": node.get("descriptionHtml", ""),
            "vendor": node.get("vendor", ""),
            "tags": node.get("tags", []),
            "product_type": node.get("productType", ""),
            "barcode": variant.get("barcode", ""),
            "weight": weight,
            "weight_unit": "kg",
            "images": images,
            "collections": collections,
            "metafields": metafields,
            "seo": seo
        }

    def fetch_all_product_skus(self, limit=50):
        """
        Fetch SKUs of all products from Shopify.

        Args:
            limit: Max number of products to fetch

        Returns:
            List of SKUs
        """
        self.connect_shopify()

        query = """
        query GetProducts($first: Int!, $after: String) {
          products(first: $first, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                title
                variants(first: 1) {
                  edges {
                    node {
                      sku
                    }
                  }
                }
              }
            }
          }
        }
        """

        skus = []
        has_next = True
        cursor = None

        while has_next and len(skus) < limit:
            variables = {"first": min(50, limit - len(skus)), "after": cursor}
            result = self.shopify.execute_graphql(query, variables)

            if not result or "data" not in result:
                break

            edges = result["data"]["products"]["edges"]
            for edge in edges:
                variants = edge["node"].get("variants", {}).get("edges", [])
                if variants:
                    sku = variants[0]["node"].get("sku")
                    if sku:
                        skus.append(sku)

            page_info = result["data"]["products"]["pageInfo"]
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        return skus

    def check_product_quality(self, product_data):
        """
        Check product against quality rules.

        Returns dict with:
        - score: 0-100
        - status: dict of field statuses
        - missing: list of missing fields
        - repair_jobs: list of repair jobs needed
        """
        if not product_data:
            return None

        required_fields = self.rules.get("required_fields", {})
        vendor = product_data.get("vendor", "")

        # Apply vendor-specific overrides
        vendor_rules = self.rules.get("vendor_rules", {}).get(vendor, {})
        for field, override in vendor_rules.items():
            if field in required_fields:
                required_fields[field].update(override)

        status = {}
        missing = []
        repair_jobs = []

        # Check each required field
        for field_name, field_rules in required_fields.items():
            check_result = self._check_field(field_name, field_rules, product_data)
            status[field_name] = check_result

            if not check_result["complete"]:
                missing.append(field_name)

                # Create repair job if script exists
                if field_rules.get("repair_script"):
                    repair_jobs.append({
                        "field": field_name,
                        "script": field_rules["repair_script"],
                        "args": field_rules.get("repair_args", "").format(
                            sku=product_data.get("sku", ""),
                            product_id=product_data.get("id", "")
                        ),
                        "priority": len(missing)  # More missing = higher priority
                    })

        # Calculate score
        total_fields = len(required_fields)
        complete_fields = total_fields - len(missing)
        score = int((complete_fields / total_fields) * 100) if total_fields > 0 else 0

        return {
            "score": score,
            "status": status,
            "missing": missing,
            "missing_count": len(missing),
            "repair_jobs": repair_jobs,
            "checked_at": datetime.now().isoformat()
        }

    def _check_field(self, field_name, field_rules, product_data):
        """Check a single field against its rules."""
        result = {
            "complete": False,
            "message": "",
            "value": None
        }

        # Map field names to product data keys
        field_mapping = {
            "sku": "sku",
            "barcode": "barcode",
            "country_of_origin": "metafields.custom.country_of_origin",
            "hs_code": "metafields.custom.hs_code",
            "weight": "weight",
            "vendor": "vendor",
            "product_type": "product_type",
            "title": "title",
            "description_html": "description_html",
            "images": "images",
            "seo_title": "seo.title",  # Native Shopify SEO field
            "seo_description": "seo.description",  # Native Shopify SEO field
            "tags": "tags",
            "collections": "collections",
            "handle": "handle"
        }

        # Get value from product data
        data_key = field_mapping.get(field_name, field_name)

        if "." in data_key:
            # Nested key (metafields or seo)
            parts = data_key.split(".")
            if parts[0] == "metafields":
                value = product_data.get("metafields", {}).get(".".join(parts[1:]), None)
            elif parts[0] == "seo":
                value = product_data.get("seo", {}).get(parts[1], None)
            else:
                value = None
        else:
            value = product_data.get(data_key)

        result["value"] = value

        # Check if value exists
        if value is None or value == "" or value == [] or value == 0:
            result["message"] = f"Missing {field_rules.get('description', field_name)}"
            return result

        # Check min_length for strings
        if isinstance(value, str) and "min_length" in field_rules:
            if len(value) < field_rules["min_length"]:
                result["message"] = f"Too short ({len(value)} chars, need {field_rules['min_length']})"
                return result

        # Check max_length for strings
        if isinstance(value, str) and "max_length" in field_rules:
            if len(value) > field_rules["max_length"]:
                result["message"] = f"Too long ({len(value)} chars, max {field_rules['max_length']})"
                return result

        # Check min_count for lists
        if isinstance(value, list) and "min_count" in field_rules:
            if len(value) < field_rules["min_count"]:
                result["message"] = f"Insufficient ({len(value)}, need {field_rules['min_count']})"
                return result

        # Check min_value for numbers
        if isinstance(value, (int, float)) and "min_value" in field_rules:
            if value < field_rules["min_value"]:
                result["message"] = f"Too low ({value}, need >= {field_rules['min_value']})"
                return result

        # Special check: handle should match title
        if field_name == "handle" and field_rules.get("validate_against") == "title":
            title = product_data.get("title", "")
            expected_handle = self._slugify(title)
            if value != expected_handle:
                result["message"] = f"Handle mismatch ('{value}' should be '{expected_handle}')"
                return result

        # All checks passed
        result["complete"] = True
        result["message"] = "[OK] Complete"

        if isinstance(value, list):
            result["message"] += f" ({len(value)} items)"
        elif isinstance(value, str) and len(value) > 50:
            result["message"] += f" ({len(value)} chars)"

        return result

    def _slugify(self, text):
        """Convert text to URL-safe slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s]+', '-', text)
        return text.strip('-')

    def update_master_record(self, product_data, quality_check, trigger=None):
        """Update master tracking file with quality check results."""
        product_id = product_data.get("id")
        sku = product_data.get("sku")

        if not product_id:
            return

        # Initialize product record if new
        if product_id not in self.master_data["products"]:
            self.master_data["products"][product_id] = {
                "sku": sku,
                "vendor": product_data.get("vendor"),
                "title": product_data.get("title"),
                "first_checked": datetime.now().isoformat(),
                "repair_history": []
            }

        record = self.master_data["products"][product_id]

        # Update quality data
        record.update({
            "last_checked": quality_check["checked_at"],
            "completeness_score": quality_check["score"],
            "missing_count": quality_check["missing_count"],
            "missing_fields": quality_check["missing"],
            "status": quality_check["status"],
            "pending_repairs": [
                {"field": job["field"], "script": job["script"]}
                for job in quality_check["repair_jobs"]
            ]
        })

        # Add trigger to history
        if trigger:
            record["repair_history"].insert(0, {
                "timestamp": datetime.now().isoformat(),
                "trigger": trigger,
                "score_after": quality_check["score"]
            })

            # Keep only last 20 history entries
            record["repair_history"] = record["repair_history"][:20]

        self._save_master_data()

    def dispatch_repair_jobs(self, repair_jobs, sku, auto_execute=False):
        """
        Dispatch repair jobs to appropriate scripts.

        If auto_execute=True, actually runs the scripts.
        Otherwise, just logs what would be done.
        """
        if not repair_jobs:
            print("   [OK] No repairs needed")
            return []

        print(f"\n   Found {len(repair_jobs)} repair job(s) needed:")

        executed = []

        for i, job in enumerate(repair_jobs, 1):
            print(f"   [{i}] {job['field']}: {job['script']} {job['args']}")

            if auto_execute:
                success = self._execute_repair(job, sku)
                executed.append({
                    "job": job,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                })

        return executed

    def _execute_repair(self, job, sku):
        """Execute a repair script."""
        import subprocess

        script = job["script"]
        args = job["args"]

        # Build command - use absolute path for Windows compatibility
        venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            python_exe = f'"{venv_python}"'  # Quote for spaces in path
        else:
            python_exe = "python"
        cmd = f"{python_exe} {script} {args}"

        print(f"       > Executing: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                print(f"       [OK] Success")
                return True
            else:
                print(f"       [ERROR] Failed: {result.stderr[:200]}")
                return False
        except Exception as e:
            print(f"       [ERROR] Error: {str(e)}")
            return False

    def get_products_needing_repair(self, limit=None):
        """
        Get list of products that need repair, sorted by priority.

        Priority: Most missing fields first, then FIFO (oldest first).
        """
        products = []

        for product_id, record in self.master_data["products"].items():
            if record.get("missing_count", 0) > 0:
                products.append({
                    "product_id": product_id,
                    "sku": record.get("sku"),
                    "missing_count": record.get("missing_count"),
                    "score": record.get("completeness_score", 0),
                    "last_checked": record.get("last_checked"),
                    "missing_fields": record.get("missing_fields", [])
                })

        # Sort: most missing first, then oldest first (FIFO)
        products.sort(key=lambda x: (-x["missing_count"], x.get("last_checked", "")))

        if limit:
            products = products[:limit]

        return products


def main():
    parser = argparse.ArgumentParser(description="Product Quality Orchestrator Agent")

    # Mode selection
    parser.add_argument("--sku", help="Check specific product by SKU")
    parser.add_argument("--check-all", action="store_true", help="Check all products needing repair")
    parser.add_argument("--scan-all", action="store_true", help="Scan all products from Shopify and check quality")
    parser.add_argument("--trigger", help="Trigger event (seo_update, image_scrape, etc.)")

    # Options
    parser.add_argument("--auto-repair", action="store_true", help="Automatically dispatch repair scripts")
    parser.add_argument("--limit", type=int, default=50, help="Max products to check (default: 50)")
    parser.add_argument("--master-file", default="data/product_quality_master.json",
                       help="Master data file path")

    args = parser.parse_args()

    print("=" * 70)
    print("Product Quality Orchestrator Agent")
    print("=" * 70)
    print()

    # Initialize agent
    agent = ProductQualityAgent(master_file=args.master_file)

    if args.sku:
        # Check single product
        print(f"[1/3] Fetching product: {args.sku}")
        product_data = agent.fetch_product_data(args.sku)

        if not product_data:
            print(f"[ERROR] Product not found: {args.sku}")
            return 1

        print(f"[OK] Found: {product_data['title']}")

        print("[2/3] Checking quality...")
        quality_check = agent.check_product_quality(product_data)

        print(f"\n   Completeness Score: {quality_check['score']}/100")
        print(f"   Missing Fields: {quality_check['missing_count']}")

        if quality_check['missing']:
            print(f"\n   Missing:")
            for field in quality_check['missing']:
                status = quality_check['status'][field]
                print(f"      X {field}: {status['message']}")

        print("[3/3] Updating master record...")
        agent.update_master_record(product_data, quality_check, trigger=args.trigger)
        print(f"[OK] Updated: {args.master_file}")

        # Dispatch repairs
        if args.auto_repair:
            print("\n[AUTO-REPAIR] Dispatching repair jobs...")
            executed = agent.dispatch_repair_jobs(
                quality_check['repair_jobs'],
                args.sku,
                auto_execute=True
            )
            print(f"\n[OK] Executed {len(executed)} repair job(s)")
        else:
            agent.dispatch_repair_jobs(quality_check['repair_jobs'], args.sku, auto_execute=False)
            print("\n[TIP] Use --auto-repair to automatically execute repairs")

    elif args.check_all:
        print(f"[1/2] Finding products needing repair...")
        products = agent.get_products_needing_repair(limit=args.limit)

        if not products:
            print("[OK] No products need repair!")
            return 0

        print(f"[OK] Found {len(products)} product(s) needing repair")
        print()

        print("[2/2] Processing products...")
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] {product['sku']} - Score: {product['score']}/100")
            print(f"   Missing {product['missing_count']} field(s): {', '.join(product['missing_fields'][:5])}")

            # Fetch and check
            product_data = agent.fetch_product_data(product['sku'])
            if not product_data:
                print("   [ERROR] Could not fetch product")
                continue

            quality_check = agent.check_product_quality(product_data)
            agent.update_master_record(product_data, quality_check)

            if args.auto_repair:
                executed = agent.dispatch_repair_jobs(
                    quality_check['repair_jobs'],
                    product['sku'],
                    auto_execute=True
                )

    elif args.scan_all:
        print(f"[1/3] Fetching products from Shopify (limit: {args.limit})...")
        skus = agent.fetch_all_product_skus(limit=args.limit)

        if not skus:
            print("[OK] No products found!")
            return 0

        print(f"[OK] Found {len(skus)} product(s)")
        print()

        print("[2/3] Checking product quality...")
        checked = 0
        for i, sku in enumerate(skus, 1):
            print(f"\n[{i}/{len(skus)}] {sku}")

            # Fetch and check
            product_data = agent.fetch_product_data(sku)
            if not product_data:
                print("   [ERROR] Could not fetch product")
                continue

            quality_check = agent.check_product_quality(product_data)
            agent.update_master_record(product_data, quality_check)

            print(f"   Score: {quality_check['score']}/100")
            if quality_check['missing_count'] > 0:
                print(f"   Missing: {', '.join(quality_check['missing'][:5])}")

            if args.auto_repair:
                executed = agent.dispatch_repair_jobs(
                    quality_check['repair_jobs'],
                    sku,
                    auto_execute=True
                )

            checked += 1

        print(f"\n[3/3] Updated master tracking file: {args.master_file}")
        print(f"[OK] Checked {checked} product(s)")

    else:
        parser.error("Must specify --sku, --check-all, or --scan-all")

    print()
    print("=" * 70)
    print("COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
