"""
SEO Content Generator for Shopify Products using Google Gemini AI.

This module provides classes to:
- Generate SEO-optimized content (meta titles, descriptions, product descriptions)
- Fetch products from Shopify via GraphQL
- Validate generated content against best practices
"""

import os
import re
import time
import time
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Import genai correctly
try:
    from google import genai
except ImportError:
    import google.generativeai as genai

from seo.seo_prompts import SYSTEM_INSTRUCTION, get_product_prompt, get_quick_prompt
from seo.seo_validator import SEOValidator

# Load environment variables
load_dotenv()


class SEOContentGenerator:
    """Generates SEO-optimized content using Google Gemini AI."""
    _cooldown_until = None

    def __init__(self, api_key=None, model_id="gemini-2.5-flash"):
        """
        Initialize the SEO content generator.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_id: Gemini model ID to use
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_id = model_id
        self.validator = SEOValidator()
        self.client = None
        self.local_only = False

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            # Allow local-only fallback generation when API key is missing
            self.local_only = True

    def generate_seo_content(self, product_data, quick_mode=True):
        """
        Generate SEO content for a product.

        Args:
            product_data: Dict containing product information:
                - title: Product title
                - vendor: Vendor/brand name
                - product_type: Product category (optional)
                - tags: Product tags (optional)
                - description_html: Current description (optional)
            quick_mode: Use simplified prompt (faster, good for testing)

        Returns:
            Dict with:
                - meta_title: Generated meta title
                - meta_description: Generated meta description
                - description_html: Generated product description HTML
                - validation: Validation results
                - raw_response: Raw AI response for debugging
        """
        # Extract product info
        title = product_data.get("title", "")
        vendor = product_data.get("vendor", "")
        product_type = product_data.get("product_type", "")
        tags = product_data.get("tags", [])
        current_description = product_data.get("description_html", "")
        current_meta_title = product_data.get("seo_title") or product_data.get("meta_title") or ""
        current_meta_description = product_data.get("seo_description") or product_data.get("meta_description") or ""

        # Generate prompt
        if quick_mode:
            prompt = get_quick_prompt(
                title,
                vendor,
                current_description,
                current_meta_title=current_meta_title,
                current_meta_description=current_meta_description,
            )
        else:
            prompt = get_product_prompt(
                title,
                vendor,
                product_type,
                tags,
                current_description,
                current_meta_title=current_meta_title,
                current_meta_description=current_meta_description,
            )

        if self.local_only:
            return self._fallback_generate_seo_content(
                product_data,
                error_message="GEMINI_API_KEY missing - local fallback used"
            )

        if SEOContentGenerator._cooldown_until and time.time() < SEOContentGenerator._cooldown_until:
            return self._fallback_generate_seo_content(
                product_data,
                error_message="Gemini cooldown active - local fallback used"
            )

        try:
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "temperature": 0.7,
                    "response_mime_type": "application/json"
                }
            )

            # Extract response text
            response_text = response.text

            # Parse JSON response
            seo_content = self.validator.extract_json_from_text(response_text)

            if not seo_content:
                return self._fallback_generate_seo_content(product_data, error_message="Failed to parse JSON from AI response")

            # Auto-fix content that's too long (smart truncation)
            seo_content = self.validator.truncate_if_needed(seo_content)

            # Validate content
            validation_results = self.validator.validate_all(seo_content)

            # Add validation results
            seo_content["validation"] = validation_results
            seo_content["raw_response"] = response_text

            return seo_content

        except Exception as e:
            message = str(e)
            if "RESOURCE_EXHAUSTED" in message or "429" in message:
                # Respect retry delay if available
                retry_match = re.search(r"retry in ([0-9]+)s", message)
                cooldown = int(retry_match.group(1)) if retry_match else 60
                SEOContentGenerator._cooldown_until = time.time() + max(cooldown, 5)
            return self._fallback_generate_seo_content(
                product_data,
                error_message=f"Failed to generate SEO content: {message}"
            )

    def _fallback_generate_seo_content(self, product_data, error_message=None):
        """
        Local fallback generator when Gemini API is unavailable or rate-limited.
        Produces reasonable SEO fields without external API calls.
        """
        title = product_data.get("title", "").strip()
        vendor = product_data.get("vendor", "").strip()
        product_type = product_data.get("product_type", "").strip()
        tags = product_data.get("tags", []) or []
        current_meta_title = (product_data.get("seo_title") or product_data.get("meta_title") or "").strip()
        current_meta_description = (product_data.get("seo_description") or product_data.get("meta_description") or "").strip()
        current_description = product_data.get("description_html", "") or ""

        base_title = title if title else "Produkt"
        brand_suffix = f" | {vendor}" if vendor else ""
        meta_title = f"{base_title}{brand_suffix}".strip()

        category = product_type if product_type else "Produkt"
        brand_name = vendor or "unserer Marke"
        tag_text = ", ".join(tags[:6]) if isinstance(tags, list) and tags else ""

        # Extract basic measurements from title (e.g., 100 ml, 20 g, 30 cm)
        measurements = []
        for match in re.findall(r"(\d+(?:[.,]\d+)?)\s*(ml|l|g|kg|cm|mm|m)\b", base_title, re.IGNORECASE):
            measurements.append(f"{match[0].replace(',', '.')} {match[1]}")

        # Meta title: prefer existing if valid length
        if current_meta_title:
            length = len(current_meta_title)
            if SEOValidator.META_TITLE_MIN <= length <= SEOValidator.META_TITLE_MAX:
                meta_title = current_meta_title

        # Meta description: prefer existing if valid length; otherwise extend or rebuild
        meta_description = ""
        if current_meta_description:
            length = len(current_meta_description)
            if SEOValidator.META_DESC_MIN <= length <= SEOValidator.META_DESC_MAX:
                meta_description = current_meta_description
            elif length < SEOValidator.META_DESC_MIN:
                meta_description = (
                    f"{current_meta_description} – {base_title} von {brand_name} "
                    f"für kreative Projekte und saubere Ergebnisse. Jetzt ansehen."
                )
        if not meta_description:
            meta_description = (
                f"Entdecken Sie {base_title} von {brand_name} – ein hochwertiges {category} "
                f"für kreative Projekte, DIY und saubere Ergebnisse. Jetzt ansehen und bestellen."
            )
        meta_description = self.validator.smart_truncate(meta_description, SEOValidator.META_DESC_MAX)

        # Description: structured, information gain, and E‑E‑A‑T aligned without unfounded claims
        excerpt = ""
        if current_description:
            lowered = current_description.lower()
            template_markers = [
                "kurzüberblick",
                "vorteile & einsatzbereiche",
                "information gain",
                "projektideen",
                "qualität & erwartungshaltung",
                "anwendung & tipps",
            ]
            contains_template = any(marker in lowered for marker in template_markers)
            if not contains_template:
                plain = re.sub(r"<[^>]+>", " ", current_description)
                plain = re.sub(r"\s+", " ", plain).strip()
                if plain:
                    excerpt = plain[:240].rsplit(" ", 1)[0]
                    if excerpt and len(excerpt) >= 80:
                        excerpt = f" Hinweis aus der bestehenden Beschreibung: {excerpt}."
                    else:
                        excerpt = ""
        specs_lines = []
        if vendor:
            specs_lines.append(f"<li>Marke: {vendor}</li>")
        if measurements:
            specs_lines.append(f"<li>Größe/Menge: {', '.join(measurements)}</li>")
        if product_type:
            specs_lines.append(f"<li>Kategorie: {product_type}</li>")
        if tag_text:
            specs_lines.append(f"<li>Stichworte: {tag_text}</li>")

        specs_html = ""
        if specs_lines:
            specs_html = "<h2>Technische Daten</h2><ul>" + "".join(specs_lines) + "</ul>"

        description_html = f"""
<p><strong>{base_title}</strong> von {brand_name} ist ein {category} für kreative Projekte. Diese Kurzfassung gibt Ihnen die wichtigsten Informationen zu Einsatz, Verarbeitung und Ergebnis, damit Sie schnell einschätzen können, ob das Produkt zu Ihrem Vorhaben passt. Ideal für alle, die klare Orientierung, saubere Resultate und verlässliche Effekte erwarten.</p>
<p>Im Detail finden Sie hier Vorteile, Anwendungstipps und Hinweise zur Kombination mit anderen Materialien. So vermeiden Sie unnötige Nacharbeit und erzielen eine gleichmäßige Optik.{excerpt}</p>

<h2>Vorteile & Einsatzbereiche</h2>
<ul>
  <li>Geeignet für kreative Techniken, Dekoration und DIY</li>
  <li>Leicht kombinierbar mit gängigen Bastelmaterialien</li>
  <li>Gute Kontrolle beim Auftragen für gleichmäßige Resultate</li>
  <li>Praktisch für kleine Projekte und präzise Arbeiten</li>
  <li>Für Einsteiger und Fortgeschrittene gleichermaßen geeignet</li>
</ul>

{specs_html}

<h2>Anwendung & Tipps</h2>
<p>Arbeiten Sie schrittweise und in dünnen Schichten, damit sich das Material gleichmäßig verteilt. Testen Sie das Produkt vorab an einer unauffälligen Stelle und kombinieren Sie es mit passenden Untergründen, wenn Sie eine besonders saubere Haftung oder ein gleichmäßiges Finish wünschen. Nutzen Sie saubere Werkzeuge und vermeiden Sie Staub, um ein ruhigeres, konsistentes Ergebnis zu erzielen.</p>

<h2>Information Gain – Worauf es wirklich ankommt</h2>
<p>Der entscheidende Unterschied liegt im kontrollierten Auftrag und einer sauberen Vorbereitung der Oberfläche. Wer gründlich vorbereitet, erzielt sichtbar bessere Resultate und vermeidet unnötige Nacharbeit. Achten Sie auf eine gleichmäßige Schichtstärke, denn kleine Unterschiede wirken sich besonders bei dekorativen Effekten deutlich aus.</p>

<h2>Projektideen & Kombinationen</h2>
<p>Setzen Sie {base_title} für Karten, Deko-Elemente, Mixed-Media-Projekte oder Akzente auf Holz, Papier und passenden Trägern ein. In Kombination mit klaren Medien, Lacken oder geeigneten Klebern entstehen glatte Übergänge und ein sauberes Gesamtbild. So können Sie Farben, Formen und Effekte gezielt steuern, ohne dass das Projekt überladen wirkt.</p>

<h2>Qualität & Erwartungshaltung</h2>
<p>Für beste Ergebnisse ist Geduld ein wichtiger Faktor: Lassen Sie jede Schicht vollständig trocknen und arbeiten Sie bei Bedarf in mehreren Durchgängen. So vermeiden Sie Schlieren und erhalten eine gleichmäßige Oberfläche. Die Kombination aus Technik, Untergrund und Verarbeitung entscheidet über das finale Erscheinungsbild.</p>

<h2>FAQ</h2>
<p><strong>Für welche Projekte eignet sich {base_title}?</strong> Für kreative Projekte, Bastelarbeiten, Dekoration und Mixed-Media-Anwendungen, bei denen ein sauberes Ergebnis wichtig ist und feine Details zählen.</p>
<p><strong>Kann ich es mit anderen Materialien kombinieren?</strong> Ja, in den meisten Fällen ist eine Kombination mit gängigen Bastelmaterialien möglich. Testen Sie die Verträglichkeit vorab, besonders bei neuen Untergründen oder Medien.</p>
<p><strong>Wie erziele ich die besten Resultate?</strong> In dünnen Schichten arbeiten, ausreichend trocknen lassen und die Oberfläche sauber vorbereiten. Gleichmäßige Werkzeuge und ein ruhiger Auftrag verbessern die Ergebnisse sichtbar.</p>
"""

        seo_content = {
            "meta_title": meta_title,
            "meta_description": meta_description,
            "description_html": description_html,
            "fallback": True
        }

        # Auto-fix content length and validate
        seo_content = self.validator.truncate_if_needed(seo_content)
        validation_results = self.validator.validate_all(seo_content)
        seo_content["validation"] = validation_results
        seo_content["raw_response"] = None
        if error_message:
            seo_content["error"] = error_message

        return seo_content


class ProductFetcher:
    """Fetches products from Shopify using GraphQL."""

    def __init__(self, shopify_client):
        """
        Initialize the product fetcher.

        Args:
            shopify_client: Authenticated ShopifyClient instance
        """
        self.client = shopify_client

    def fetch_by_sku(self, sku):
        """
        Fetch a single product by SKU.

        Args:
            sku: Product SKU

        Returns:
            Product data dict or None
        """
        query = """
        query GetProductBySKU($query: String!) {
          products(first: 1, query: $query) {
            edges {
              node {
                id
                title
                descriptionHtml
                vendor
                tags
                productType
                variants(first: 1) {
                  edges {
                    node {
                      sku
                      barcode
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"query": f"sku:{sku}"}
        result = self.client.execute_graphql(query, variables)

        if result and "data" in result:
            edges = result["data"]["products"]["edges"]
            if edges:
                return self._parse_product_node(edges[0]["node"])

        return None

    def fetch_by_vendor(self, vendor, limit=50):
        """
        Fetch products by vendor name.

        Args:
            vendor: Vendor/brand name
            limit: Maximum number of products to fetch

        Returns:
            List of product data dicts
        """
        query = """
        query GetProductsByVendor($query: String!, $first: Int!) {
          products(first: $first, query: $query) {
            edges {
              node {
                id
                title
                descriptionHtml
                vendor
                tags
                productType
                variants(first: 1) {
                  edges {
                    node {
                      sku
                      barcode
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """

        variables = {
            "query": f"vendor:{vendor}",
            "first": min(limit, 50)
        }

        result = self.client.execute_graphql(query, variables)

        if result and "data" in result:
            edges = result["data"]["products"]["edges"]
            return [self._parse_product_node(edge["node"]) for edge in edges]

        return []

    def fetch_by_title(self, title_pattern, limit=50):
        """
        Fetch products by title pattern.

        Args:
            title_pattern: Title search pattern
            limit: Maximum number of products to fetch

        Returns:
            List of product data dicts
        """
        query = """
        query GetProductsByTitle($query: String!, $first: Int!) {
          products(first: $first, query: $query) {
            edges {
              node {
                id
                title
                descriptionHtml
                vendor
                tags
                productType
                variants(first: 1) {
                  edges {
                    node {
                      sku
                      barcode
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "query": f"title:*{title_pattern}*",
            "first": min(limit, 50)
        }

        result = self.client.execute_graphql(query, variables)

        if result and "data" in result:
            edges = result["data"]["products"]["edges"]
            return [self._parse_product_node(edge["node"]) for edge in edges]

        return []

    def fetch_by_barcode(self, barcode):
        """
        Fetch a single product by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Product data dict or None
        """
        query = """
        query GetProductByBarcode($query: String!) {
          products(first: 1, query: $query) {
            edges {
              node {
                id
                title
                descriptionHtml
                vendor
                tags
                productType
                variants(first: 10) {
                  edges {
                    node {
                      sku
                      barcode
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"query": f"barcode:{barcode}"}
        result = self.client.execute_graphql(query, variables)

        if result and "data" in result:
            edges = result["data"]["products"]["edges"]
            if edges:
                return self._parse_product_node(edges[0]["node"])

        return None

    def fetch_by_handle(self, handle):
        """
        Fetch a single product by handle.

        Args:
            handle: Product handle (from URL: /products/handle)

        Returns:
            Product data dict or None
        """
        query = """
        query GetProductByHandle($handle: String!) {
          productByHandle(handle: $handle) {
            id
            title
            descriptionHtml
            vendor
            tags
            productType
            variants(first: 1) {
              edges {
                node {
                  sku
                  barcode
                }
              }
            }
          }
        }
        """

        variables = {"handle": handle}
        result = self.client.execute_graphql(query, variables)

        if result and "data" in result and result["data"].get("productByHandle"):
            return self._parse_product_node(result["data"]["productByHandle"])

        return None

    def fetch_by_collection(self, collection_id, limit=50):
        """
        Fetch products in a collection.

        Args:
            collection_id: Collection ID (gid://shopify/Collection/123) or handle
            limit: Maximum number of products to fetch

        Returns:
            List of product data dicts
        """
        # If collection_id looks like a handle (no gid://), query by handle
        if not collection_id.startswith("gid://"):
            query = """
            query GetCollectionByHandle($handle: String!) {
              collectionByHandle(handle: $handle) {
                id
                title
                products(first: $first) {
                  edges {
                    node {
                      id
                      title
                      descriptionHtml
                      vendor
                      tags
                      productType
                      variants(first: 1) {
                        edges {
                          node {
                            sku
                            barcode
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            variables = {"handle": collection_id, "first": min(limit, 50)}
            result = self.client.execute_graphql(query, variables)

            if result and "data" in result and result["data"].get("collectionByHandle"):
                edges = result["data"]["collectionByHandle"]["products"]["edges"]
                return [self._parse_product_node(edge["node"]) for edge in edges]
        else:
            # Query by GID
            query = """
            query GetCollectionById($id: ID!, $first: Int!) {
              collection(id: $id) {
                id
                title
                products(first: $first) {
                  edges {
                    node {
                      id
                      title
                      descriptionHtml
                      vendor
                      tags
                      productType
                      variants(first: 1) {
                        edges {
                          node {
                            sku
                            barcode
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            variables = {"id": collection_id, "first": min(limit, 50)}
            result = self.client.execute_graphql(query, variables)

            if result and "data" in result and result["data"].get("collection"):
                edges = result["data"]["collection"]["products"]["edges"]
                return [self._parse_product_node(edge["node"]) for edge in edges]

        return []

    def _parse_product_node(self, node):
        """
        Parse a product node from GraphQL response.

        Args:
            node: Product node from GraphQL

        Returns:
            Standardized product data dict
        """
        # Extract SKU from first variant
        sku = ""
        barcode = ""
        if node.get("variants") and node["variants"]["edges"]:
            variant = node["variants"]["edges"][0]["node"]
            sku = variant.get("sku", "")
            barcode = variant.get("barcode", "")

        return {
            "id": node.get("id", ""),
            "title": node.get("title", ""),
            "description_html": node.get("descriptionHtml", ""),
            "vendor": node.get("vendor", ""),
            "tags": node.get("tags", []),
            "product_type": node.get("productType", ""),
            "sku": sku,
            "barcode": barcode
        }


class ProductUpdater:
    """Updates Shopify products with SEO-optimized content."""

    def __init__(self, shopify_client):
        """
        Initialize the product updater.

        Args:
            shopify_client: Authenticated ShopifyClient instance
        """
        self.client = shopify_client

    def update_product_seo(self, product_id, seo_content):
        """
        Update a single product's SEO content.

        Updates:
        - Product description HTML
        - Meta title (via metafield)
        - Meta description (via metafield)

        Args:
            product_id: Shopify product ID (gid://shopify/Product/...)
            seo_content: Dict with meta_title, meta_description, description_html

        Returns:
            Dict with success status and details
        """
        mutation = """
        mutation UpdateProductSEO($input: ProductInput!) {
          productUpdate(input: $input) {
            product {
              id
              title
              descriptionHtml
              seo {
                title
                description
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        # Prepare SEO input (using native Shopify SEO fields, not metafields)
        seo_input = {}

        if seo_content.get("meta_title"):
            seo_input["title"] = seo_content["meta_title"]

        if seo_content.get("meta_description"):
            seo_input["description"] = seo_content["meta_description"]

        # Build input - ONLY include fields that have actual content
        input_data = {"id": product_id}

        # CRITICAL: Only update description if we have new content
        # NEVER send empty string which would delete existing description
        if seo_content.get("description_html") and len(seo_content.get("description_html", "").strip()) > 0:
            input_data["descriptionHtml"] = seo_content["description_html"]

        # Only add SEO if we have SEO updates
        if seo_input:
            input_data["seo"] = seo_input

        variables = {"input": input_data}

        result = self.client.execute_graphql(mutation, variables)

        if result and "data" in result:
            user_errors = result["data"]["productUpdate"].get("userErrors", [])
            if user_errors:
                return {
                    "success": False,
                    "errors": user_errors
                }

            return {
                "success": True,
                "product": result["data"]["productUpdate"]["product"]
            }

        return {
            "success": False,
            "errors": [{"message": "Failed to execute GraphQL mutation"}]
        }

    def batch_update_products(self, updates):
        """
        Update multiple products with SEO content.

        Args:
            updates: List of dicts with product_id and seo_content

        Returns:
            Dict with results for each product
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(updates)
        }

        for i, update in enumerate(updates, 1):
            product_id = update.get("product_id")
            seo_content = update.get("seo_content")
            product_title = update.get("product_title", "Unknown")

            print(f"   [{i}/{len(updates)}] Updating: {product_title[:50]}...")

            result = self.update_product_seo(product_id, seo_content)

            if result.get("success"):
                results["successful"].append({
                    "product_id": product_id,
                    "title": product_title
                })
                print(f"       [OK] Successfully updated")
            else:
                results["failed"].append({
                    "product_id": product_id,
                    "title": product_title,
                    "errors": result.get("errors", [])
                })
                print(f"       [ERROR] Update failed: {result.get('errors')}")

            # Rate limiting - pause between updates
            if i < len(updates):
                time.sleep(0.5)

        return results


class ShopifyClient:
    """Simplified Shopify GraphQL client for SEO generator."""

    def __init__(self):
        """Initialize Shopify client."""
        self.access_token = None
        self.shop_domain = os.getenv("SHOP_DOMAIN")
        self.api_version = os.getenv("API_VERSION", "2024-01")
        self.client_id = os.getenv("SHOPIFY_CLIENT_ID")
        self.client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")

        if not all([self.shop_domain, self.client_id, self.client_secret]):
            raise ValueError("Missing Shopify credentials in environment variables")

        self.graphql_endpoint = f"https://{self.shop_domain}/admin/api/{self.api_version}/graphql.json"

    def authenticate(self):
        """Authenticate with Shopify using client credentials."""
        import requests

        token_endpoint = f"https://{self.shop_domain}/admin/oauth/access_token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        try:
            response = requests.post(token_endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get("access_token")
            print(f"[OK] Successfully authenticated with Shopify")
            return True
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            return False

    def execute_graphql(self, query, variables=None):
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables dict

        Returns:
            Response data dict
        """
        import requests

        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(self.graphql_endpoint, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            print(f"GraphQL Errors: {result['errors']}")
            return None

        return result
