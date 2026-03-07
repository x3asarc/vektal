import os
from urllib.parse import urlparse
import requests

from src.core.image_scraper import ShopifyClient


class ShopifyResolver:
    def __init__(
        self,
        shop_domain=None,
        access_token=None,
        api_version=None,
        use_rest_fallback=True,
        max_rest_pages=3,
        session=None,
    ):
        self.shop_domain = shop_domain or os.getenv("SHOP_DOMAIN")
        self.api_version = api_version or os.getenv("API_VERSION", "2024-01")
        self.use_rest_fallback = use_rest_fallback
        self.max_rest_pages = max_rest_pages
        self.session = session or requests.Session()
        self.client = ShopifyClient()

        if self.shop_domain:
            self.client.shop_domain = self.shop_domain
            self.client.api_version = self.api_version
            self.client.graphql_endpoint = (
                f"https://{self.shop_domain}/admin/api/{self.api_version}/graphql.json"
            )

        if access_token:
            self.client.access_token = access_token
        else:
            self.client.authenticate()

        self._cache = {}

    def resolve_identifier(self, identifier):
        kind = identifier.get("kind")
        value = str(identifier.get("value", "")).strip()
        if not value:
            return {"matches": [], "errors": ["empty identifier"], "used_rest": False}

        cache_key = f"{kind}:{value}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if kind in ("sku", "ean"):
            result = self._resolve_sku_or_ean(kind, value)
        elif kind == "handle":
            result = self._resolve_by_handle(value)
        elif kind == "url":
            handle = self._handle_from_url(value)
            result = self._resolve_by_handle(handle) if handle else {"matches": [], "errors": ["invalid url"], "used_rest": False}
        elif kind == "title":
            result = self._resolve_by_title(value)
        else:
            result = {"matches": [], "errors": ["unknown identifier type"], "used_rest": False}

        self._cache[cache_key] = result
        return result

    def _resolve_sku_or_ean(self, kind, value):
        matches = []
        errors = []
        used_rest = False

        sku_matches = self._query_products(f"sku:{value}")
        matches.extend(sku_matches)

        if not matches:
            barcode_matches = self._query_products(f"barcode:{value}")
            matches.extend(barcode_matches)
        else:
            barcode_matches = self._query_products(f"barcode:{value}")
            matches.extend(barcode_matches)

        matches = self._dedupe(matches)

        if not matches and self.use_rest_fallback:
            rest_match = None
            if kind == "sku":
                rest_match = self._rest_find_by_variant_field("sku", value)
            elif kind == "ean":
                rest_match = self._rest_find_by_variant_field("barcode", value)
            if rest_match:
                matches = [rest_match]
                used_rest = True

        if not matches:
            errors.append("no product found")

        return {"matches": matches, "errors": errors, "used_rest": used_rest}

    def _resolve_by_handle(self, handle):
        if not handle:
            return {"matches": [], "errors": ["empty handle"], "used_rest": False}

        node = self._query_product_by_handle(handle)
        if node:
            return {"matches": [node], "errors": [], "used_rest": False}

        if self.use_rest_fallback:
            rest_node = self._rest_get_product_by_handle(handle)
            if rest_node:
                return {"matches": [rest_node], "errors": [], "used_rest": True}

        return {"matches": [], "errors": ["no product found"], "used_rest": False}

    def _resolve_by_title(self, title):
        matches = self._query_products(f"title:*{title}*")
        return {"matches": matches, "errors": [] if matches else ["no product found"], "used_rest": False}

    def fetch_updated_products(self, since_at: str, limit: int = 50):
        """
        Fetch products updated since a specific ISO timestamp using GraphQL.
        Used for Phase 17 reconciliation polling.
        """
        query = f"updated_at:>{since_at}"
        return self._query_products(query, first=limit)

    def _query_products(self, query, first=5):
        gql = """
        query FindProducts($query: String!, $first: Int!) {
          products(first: $first, query: $query) {
            edges {
              node {
                id
                handle
                title
                vendor
                descriptionHtml
                tags
                productType
                seo { title description }
                collections(first: 10) {
                  edges {
                    node {
                      id
                      title
                    }
                  }
                }
                media(first: 10) {
                  edges {
                    node {
                      ... on MediaImage {
                        id
                        image { url }
                      }
                    }
                  }
                }
                variants(first: 10) {
                  edges {
                    node {
                      id
                      sku
                      barcode
                      price
                      inventoryItem { id }
                    }
                  }
                }
              }
            }
          }
        }
        """
        result = self.client.execute_graphql(gql, {"query": query, "first": first})
        if not result or not result.get("data", {}).get("products", {}).get("edges"):
            return []

        nodes = [edge["node"] for edge in result["data"]["products"]["edges"]]
        return [self._normalize_product(node) for node in nodes]

    def _query_product_by_handle(self, handle):
        gql = """
        query GetProductByHandle($handle: String!) {
          productByHandle(handle: $handle) {
            id
            handle
            title
            vendor
            descriptionHtml
            tags
            productType
            seo { title description }
            collections(first: 10) {
              edges {
                node {
                  id
                  title
                }
              }
            }
            media(first: 10) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image { url }
                  }
                }
              }
            }
            variants(first: 10) {
              edges {
                node {
                  id
                  sku
                  barcode
                  price
                  inventoryItem { id }
                }
              }
            }
          }
        }
        """
        result = self.client.execute_graphql(gql, {"handle": handle})
        node = result.get("data", {}).get("productByHandle") if result else None
        return self._normalize_product(node) if node else None

    def _normalize_product(self, node):
        if not node:
            return None

        media_edges = node.get("media", {}).get("edges", []) if node.get("media") else []
        media = []
        for edge in media_edges:
            media_node = edge.get("node") or {}
            image = media_node.get("image") or {}
            url = image.get("url")
            if url:
                media.append({"id": media_node.get("id"), "url": url})

        variants = []
        variant_edges = node.get("variants", {}).get("edges", []) if node.get("variants") else []
        for edge in variant_edges:
            v = edge.get("node") or {}
            variants.append({
                "id": v.get("id"),
                "sku": v.get("sku"),
                "barcode": v.get("barcode"),
                "price": v.get("price"),
                "weight": v.get("weight"),
                "weight_unit": v.get("weightUnit"),
                "inventory_item_id": (v.get("inventoryItem") or {}).get("id"),
            })

        primary_variant = variants[0] if variants else {}

        collections = []
        collection_edges = node.get("collections", {}).get("edges", []) if node.get("collections") else []
        for edge in collection_edges:
            c = edge.get("node") or {}
            if c:
                collections.append({"id": c.get("id"), "title": c.get("title")})

        product = {
            "id": node.get("id"),
            "handle": node.get("handle"),
            "title": node.get("title"),
            "vendor": node.get("vendor"),
            "description_html": node.get("descriptionHtml"),
            "tags": node.get("tags") or [],
            "product_type": node.get("productType"),
            "seo_title": (node.get("seo") or {}).get("title"),
            "seo_description": (node.get("seo") or {}).get("description"),
            "collections": collections,
            "media": media,
            "images": media,
            "variants": variants,
            "primary_variant": primary_variant,
        }

        self._enrich_with_rest_details(product)
        return product

    def _enrich_with_rest_details(self, product):
        primary_variant = product.get("primary_variant") or {}
        variant_gid = primary_variant.get("id")
        inv_gid = primary_variant.get("inventory_item_id")

        if variant_gid and primary_variant.get("weight") is None:
            rest_variant = self._rest_get_variant_by_id(variant_gid)
            if rest_variant:
                primary_variant["weight"] = rest_variant.get("weight")
                primary_variant["weight_unit"] = rest_variant.get("weight_unit")
                primary_variant["sku"] = rest_variant.get("sku") or primary_variant.get("sku")
                primary_variant["barcode"] = rest_variant.get("barcode") or primary_variant.get("barcode")

        if inv_gid and (not primary_variant.get("inventory_country") or not primary_variant.get("inventory_hs_code")):
            rest_inv = self._rest_get_inventory_item(inv_gid)
            if rest_inv:
                primary_variant["inventory_country"] = rest_inv.get("country_code_of_origin")
                primary_variant["inventory_hs_code"] = rest_inv.get("harmonized_system_code")

        product["primary_variant"] = primary_variant

    def _dedupe(self, matches):
        seen = set()
        deduped = []
        for m in matches:
            if not m:
                continue
            pid = m.get("id")
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            deduped.append(m)
        return deduped

    def _handle_from_url(self, value):
        try:
            parsed = urlparse(value)
            parts = parsed.path.strip("/").split("/")
            if "products" in parts:
                idx = parts.index("products")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except Exception:
            return None
        return None

    def _rest_headers(self):
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.client.access_token,
        }

    def _rest_base(self):
        return f"https://{self.shop_domain}/admin/api/{self.api_version}"

    def _rest_get_product_by_handle(self, handle):
        url = f"{self._rest_base()}/products.json"
        params = {"handle": handle, "fields": "id,handle,title,vendor,product_type,tags,images,variants"}
        try:
            resp = self.session.get(url, headers=self._rest_headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            products = data.get("products", [])
            if not products:
                return None
            return self._normalize_rest_product(products[0])
        except Exception:
            return None

    def _rest_find_by_variant_field(self, field, value):
        since_id = 0
        pages = 0
        while pages < self.max_rest_pages:
            url = f"{self._rest_base()}/variants.json"
            params = {"limit": 250, "since_id": since_id}
            try:
                resp = self.session.get(url, headers=self._rest_headers(), params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                variants = data.get("variants", [])
                if not variants:
                    return None
                for variant in variants:
                    if str(variant.get(field, "")) == str(value):
                        product_id = variant.get("product_id")
                        return self._rest_get_product_by_id(product_id)
                since_id = variants[-1].get("id", since_id)
                pages += 1
            except Exception:
                return None
        return None

    def _rest_get_product_by_id(self, product_id):
        if not product_id:
            return None
        url = f"{self._rest_base()}/products/{product_id}.json"
        params = {"fields": "id,handle,title,vendor,product_type,tags,images,variants"}
        try:
            resp = self.session.get(url, headers=self._rest_headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            product = data.get("product")
            if not product:
                return None
            return self._normalize_rest_product(product)
        except Exception:
            return None

    def _rest_get_variant_by_id(self, variant_gid):
        variant_id = str(variant_gid).split("/")[-1]
        url = f"{self._rest_base()}/variants/{variant_id}.json"
        try:
            resp = self.session.get(url, headers=self._rest_headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json().get("variant")
            if not data:
                return None
            return {
                "sku": data.get("sku"),
                "barcode": data.get("barcode"),
                "weight": data.get("weight"),
                "weight_unit": data.get("weight_unit"),
            }
        except Exception:
            return None

    def _rest_get_inventory_item(self, inventory_gid):
        inv_id = str(inventory_gid).split("/")[-1]
        url = f"{self._rest_base()}/inventory_items/{inv_id}.json"
        try:
            resp = self.session.get(url, headers=self._rest_headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json().get("inventory_item")
            if not data:
                return None
            return {
                "country_code_of_origin": data.get("country_code_of_origin"),
                "harmonized_system_code": data.get("harmonized_system_code"),
            }
        except Exception:
            return None

    def _normalize_rest_product(self, product):
        images = []
        for img in product.get("images", []) or []:
            url = img.get("src")
            if url:
                images.append({"id": img.get("id"), "url": url})

        variants = []
        for v in product.get("variants", []) or []:
            variants.append({
                "id": f"gid://shopify/ProductVariant/{v.get('id')}",
                "sku": v.get("sku"),
                "barcode": v.get("barcode"),
                "price": v.get("price"),
                "weight": v.get("weight"),
                "weight_unit": v.get("weight_unit"),
                "inventory_item_id": f"gid://shopify/InventoryItem/{v.get('inventory_item_id')}" if v.get("inventory_item_id") else None,
            })

        primary_variant = variants[0] if variants else {}

        product = {
            "id": f"gid://shopify/Product/{product.get('id')}",
            "handle": product.get("handle"),
            "title": product.get("title"),
            "vendor": product.get("vendor"),
            "description_html": product.get("body_html"),
            "tags": [t.strip() for t in (product.get("tags") or "").split(",") if t.strip()],
            "product_type": product.get("product_type"),
            "seo_title": None,
            "seo_description": None,
            "media": images,
            "images": images,
            "variants": variants,
            "primary_variant": primary_variant,
        }

        self._enrich_with_rest_details(product)
        return product
