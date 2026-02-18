"""
Product Analyzer Module

Auto-detects and proposes corrections for:
1. SKU/EAN mismatch: When SKU field contains EAN barcode instead of article number
2. Naming inconsistencies: When product title doesn't match product group naming pattern

This module implements a feedback loop architecture:
- Input: EAN/SKU identifier
- Analysis: Detect discrepancies via Pentart DB and Shopify product group comparison
- Output: Correction plan to feed back into the pipeline
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class SkuIssue:
    """Detected SKU/EAN mismatch."""
    detected: bool = False
    current_sku: Optional[str] = None
    current_barcode: Optional[str] = None
    correct_sku: Optional[str] = None  # Article number from DB
    correct_barcode: Optional[str] = None  # EAN from DB


@dataclass
class NamingIssue:
    """Detected naming inconsistency."""
    detected: bool = False
    current_title: Optional[str] = None
    suggested_title: Optional[str] = None
    db_title: Optional[str] = None  # Title from Pentart DB
    group_pattern: Optional[str] = None  # Detected pattern from product group
    similar_products: List[Dict] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class AnalysisResult:
    """Result of product analysis."""
    product_id: Optional[str] = None
    sku_issue: SkuIssue = field(default_factory=SkuIssue)
    naming_issue: NamingIssue = field(default_factory=NamingIssue)
    corrections: List[Dict] = field(default_factory=list)
    
    def has_issues(self) -> bool:
        return self.sku_issue.detected or self.naming_issue.detected


class ProductAnalyzer:
    """
    Auto-detect SKU/naming issues before pipeline processing.
    
    For Pentart products:
    - Lookup by EAN/SKU in Pentart DB
    - Cross-reference with similar products in Shopify
    - Detect naming pattern from product group
    
    For non-Pentart products:
    - Find similar products in Shopify by title/handle pattern
    - Detect naming convention from group
    """
    
    def __init__(self, context: Dict = None):
        self.context = context or {}
        self._pentart_db = None
        self._resolver = None
    
    @property
    def pentart_db(self):
        """Lazy load Pentart database."""
        if self._pentart_db is None:
            try:
                from utils.pentart_db import PentartDatabase
                self._pentart_db = PentartDatabase()
            except Exception:
                self._pentart_db = False  # Mark as unavailable
        return self._pentart_db if self._pentart_db else None
    
    @property
    def resolver(self):
        """Get or create Shopify resolver from context."""
        if self._resolver is None:
            self._resolver = self.context.get("resolver")
        return self._resolver
    
    def analyze(self, product: Dict, identifier: Dict, vendor: str = None) -> AnalysisResult:
        """
        Analyze product for SKU/naming issues.
        
        Args:
            product: Normalized Shopify product data
            identifier: {"kind": "sku"|"ean"|"handle", "value": "..."}
            vendor: Product vendor (e.g., "Pentart")
            
        Returns:
            AnalysisResult with detected issues and proposed corrections
        """
        result = AnalysisResult()
        
        if not product:
            return result
        
        result.product_id = product.get("id")
        vendor = vendor or product.get("vendor") or ""
        is_pentart = "pentart" in vendor.lower()
        
        # Get current variant data
        primary_variant = product.get("primary_variant") or {}
        current_sku = primary_variant.get("sku")
        current_barcode = primary_variant.get("barcode")
        
        # Detect SKU/EAN mismatch
        result.sku_issue = self.detect_sku_ean_mismatch(
            product, identifier, is_pentart
        )
        
        # Detect naming inconsistency
        result.naming_issue = self.detect_naming_inconsistency(
            product, identifier, is_pentart
        )
        
        # Build correction plan
        result.corrections = self._build_corrections(result, product)
        
        return result
    
    def detect_sku_ean_mismatch(
        self,
        product: Dict,
        identifier: Dict,
        is_pentart: bool
    ) -> SkuIssue:
        """
        Check if SKU field contains EAN instead of article number.

        Detection logic:
        - Use SKU/EAN validator to check if SKU field contains an EAN (13-digit barcode)
        - Cross-reference with Pentart DB to confirm and get correct SKU

        IMPORTANT: SKUs are NOT 13 characters. If a field contains a 13-digit number,
        it's an EAN barcode, not a SKU. SKUs are typically 5-10 character alphanumeric codes.
        """
        from src.utils.sku_ean_validator import is_ean, is_sku

        issue = SkuIssue()

        primary_variant = product.get("primary_variant") or {}
        current_sku = primary_variant.get("sku")
        current_barcode = primary_variant.get("barcode")

        issue.current_sku = current_sku
        issue.current_barcode = current_barcode

        if not current_sku:
            return issue

        sku_str = str(current_sku).strip()

        # CRITICAL CHECK: Is the SKU field actually an EAN?
        # SKUs are NOT 13-digit numbers - those are EAN barcodes
        if is_ean(sku_str):
            # SKU field contains an EAN - this is wrong!

            # For Pentart products, look up the correct SKU from DB
            if is_pentart and self.pentart_db:
                # Try to find product by EAN (using current SKU as EAN)
                db_record = self.pentart_db.get_by_ean(sku_str)

                if db_record:
                    article_number = db_record.get("article_number")
                    db_ean = db_record.get("ean")

                    # Confirm mismatch: SKU contains EAN, but should be article_number
                    if article_number and str(article_number) != sku_str:
                        issue.detected = True
                        issue.correct_sku = str(article_number)
                        issue.correct_barcode = db_ean
                    else:
                        # EAN detected but no article number in DB
                        issue.detected = True
                        issue.correct_sku = None  # Unknown - needs manual lookup
                        issue.correct_barcode = sku_str
                else:
                    # EAN detected but not in DB
                    issue.detected = True
                    issue.correct_sku = None  # Unknown - needs manual lookup
                    issue.correct_barcode = sku_str
            else:
                # Non-Pentart or no DB - still flag the issue
                issue.detected = True
                issue.correct_sku = None  # Unknown without DB
                issue.correct_barcode = sku_str

        return issue
    
    def detect_naming_inconsistency(
        self, 
        product: Dict, 
        identifier: Dict,
        is_pentart: bool
    ) -> NamingIssue:
        """
        Detect naming inconsistencies by comparing with product group.
        
        For Pentart:
        1. Lookup by EAN/SKU in DB → get article_number
        2. Find similar products in Shopify by article number prefix
        3. Extract naming pattern from group
        4. Compare current title against pattern
        
        For non-Pentart:
        1. Find similar products in Shopify
        2. Detect naming pattern from group
        """
        issue = NamingIssue()
        issue.current_title = product.get("title")
        
        if not issue.current_title:
            return issue
        
        if is_pentart:
            issue = self._detect_pentart_naming_issue(product, identifier, issue)
        else:
            issue = self._detect_general_naming_issue(product, issue)
        
        return issue
    
    def _detect_pentart_naming_issue(
        self, 
        product: Dict, 
        identifier: Dict,
        issue: NamingIssue
    ) -> NamingIssue:
        """
        Detect naming issues for Pentart products.
        
        Only proposes title changes when:
        1. There are at least 3 similar products in Shopify with the same pattern
        2. The current title clearly doesn't match the established pattern
        3. The DB title matches the pattern used by other products in Shopify
        """
        if not self.pentart_db:
            return issue
        
        # Get identifier value
        id_value = identifier.get("value", "")
        id_kind = identifier.get("kind", "")
        
        # Get current SKU/barcode from product
        primary_variant = product.get("primary_variant") or {}
        current_sku = primary_variant.get("sku")
        current_barcode = primary_variant.get("barcode")
        
        # Find product in Pentart DB
        db_record = None
        
        # Try by EAN first (using current_sku if it looks like EAN)
        if current_sku and len(str(current_sku)) == 13:
            db_record = self.pentart_db.get_by_ean(str(current_sku))
        
        if not db_record and current_barcode:
            db_record = self.pentart_db.get_by_ean(str(current_barcode))
        
        if not db_record and id_kind == "ean":
            db_record = self.pentart_db.get_by_ean(str(id_value))
        
        if not db_record:
            return issue
        
        # Get article number and DB title
        article_number = db_record.get("article_number")
        db_title = db_record.get("description")
        issue.db_title = db_title
        
        if not article_number:
            return issue
        
        # Find similar products by article number prefix
        # Extract prefix (e.g., 40070 → 400)
        article_str = str(article_number)
        if len(article_str) >= 3:
            prefix = article_str[:3]
            similar_products = self._find_products_by_article_prefix(prefix)
            issue.similar_products = similar_products
            
            # Only consider title change if we found enough similar products
            # to establish a clear naming pattern (minimum 3 products)
            if len(similar_products) >= 3:
                # Extract naming pattern from SHOPIFY titles (not DB titles)
                shopify_titles = [p.get("title") for p in similar_products if p.get("title")]
                
                if shopify_titles:
                    pattern = self._extract_naming_pattern(
                        [{"title": t} for t in shopify_titles]
                    )
                    issue.group_pattern = pattern
                    
                    # Check if current title matches the SHOPIFY pattern
                    if pattern and not self._title_matches_pattern(
                        issue.current_title, pattern
                    ):
                        # Only suggest if DB title ALSO matches the pattern
                        # (i.e., the DB uses the same naming convention as Shopify)
                        if db_title and self._title_matches_pattern(db_title, pattern):
                            issue.detected = True
                            issue.suggested_title = db_title
                            issue.confidence = 0.9
                        else:
                            # DB title doesn't match either - might be Hungarian vs German
                            # In this case, try to derive the correct title from pattern
                            derived_title = self._derive_title_from_pattern(
                                pattern, issue.current_title, db_title, shopify_titles
                            )
                            if derived_title and derived_title != issue.current_title:
                                issue.detected = True
                                issue.suggested_title = derived_title
                                issue.confidence = 0.7
        
        return issue
    
    def _derive_title_from_pattern(
        self, 
        pattern: str, 
        current_title: str,
        db_title: str,
        shopify_titles: List[str]
    ) -> Optional[str]:
        """
        Try to derive the correct title based on the Shopify naming pattern.
        
        This handles cases where the DB has Hungarian names but Shopify uses English.
        """
        if not pattern or not shopify_titles:
            return None
        
        # Extract prefix and suffix from pattern
        parts = pattern.split("{variable}")
        if len(parts) != 2:
            return None
        
        prefix, suffix = parts
        
        # Check if the current title just has a different base but same structure
        # (e.g., "Harztönung" vs "Resin Tint" but same color/size)
        
        # Try to find what the variable part should be
        # by comparing with DB title structure
        if not db_title:
            return None
        
        # Extract the variable part from DB title (the color/variant name)
        # This is a simple heuristic - extract words that aren't in prefix/suffix
        db_words = db_title.lower().split()
        prefix_words = prefix.lower().split()
        suffix_words = suffix.lower().split()
        
        variable_words = []
        for word in db_words:
            if word not in prefix_words and word not in suffix_words:
                # Check if this word is likely a color/variant (exists in other titles)
                for st in shopify_titles:
                    if word in st.lower():
                        variable_words.append(word)
                        break
        
        if variable_words:
            variable = " ".join(variable_words)
            return f"{prefix}{variable}{suffix}".strip()
        
        return None
    
    def _detect_general_naming_issue(
        self, 
        product: Dict,
        issue: NamingIssue
    ) -> NamingIssue:
        """Detect naming issues for non-Pentart products."""
        # Find similar products by title pattern
        title = product.get("title") or ""
        
        # Extract base pattern from title (remove size/color variations)
        base_pattern = self._extract_base_title_pattern(title)
        
        if not base_pattern or not self.resolver:
            return issue
        
        # Search for similar products
        try:
            search_result = self.resolver._query_products(f"title:*{base_pattern}*", first=10)
            if search_result:
                issue.similar_products = search_result
                pattern = self._extract_naming_pattern(search_result)
                issue.group_pattern = pattern
        except Exception:
            pass
        
        return issue
    
    def _find_products_by_article_prefix(self, prefix: str) -> List[Dict]:
        """
        Find products in Shopify with similar article numbers.
        
        Uses Pentart DB to find all products with same prefix,
        then searches Shopify for those that exist in the store.
        """
        if not self.pentart_db:
            return []
        
        # Get all products from Pentart DB with similar article numbers
        try:
            db_products = self.pentart_db.search_by_article_prefix(prefix)
        except AttributeError:
            # Method doesn't exist yet, fall back to description search
            return []
        
        if not db_products or not self.resolver:
            return []
        
        # Search Shopify for these products by EAN
        similar = []
        for db_prod in db_products[:10]:  # Limit to 10
            ean = db_prod.get("ean")
            if ean:
                try:
                    result = self.resolver._query_products(f"barcode:{ean}", first=1)
                    if result:
                        # Add DB info to result
                        result[0]["_db_title"] = db_prod.get("description")
                        result[0]["_article_number"] = db_prod.get("article_number")
                        similar.append(result[0])
                except Exception:
                    pass
        
        return similar
    
    def _extract_naming_pattern(self, products: List[Dict]) -> Optional[str]:
        """
        Extract common naming pattern from a group of products.
        
        Example: ["Resin Tint white 20 ml", "Resin Tint jade 20 ml"]
        Pattern: "Resin Tint {color} 20 ml"
        """
        if not products or len(products) < 2:
            return None
        
        titles = [p.get("title") or p.get("_db_title") or "" for p in products]
        titles = [t for t in titles if t]
        
        if len(titles) < 2:
            return None
        
        # Find common prefix
        prefix = self._find_common_prefix(titles)
        
        # Find common suffix
        suffix = self._find_common_suffix(titles)
        
        if prefix or suffix:
            return f"{prefix}{{variable}}{suffix}"
        
        return None
    
    def _find_common_prefix(self, strings: List[str]) -> str:
        """Find common prefix among strings."""
        if not strings:
            return ""
        
        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        
        # Trim to last space for word boundary
        if prefix and not prefix.endswith(" "):
            last_space = prefix.rfind(" ")
            if last_space > 0:
                prefix = prefix[:last_space + 1]
        
        return prefix
    
    def _find_common_suffix(self, strings: List[str]) -> str:
        """Find common suffix among strings."""
        if not strings:
            return ""
        
        reversed_strings = [s[::-1] for s in strings]
        reversed_suffix = self._find_common_prefix(reversed_strings)
        suffix = reversed_suffix[::-1]
        
        # Trim to first space for word boundary
        if suffix and not suffix.startswith(" "):
            first_space = suffix.find(" ")
            if first_space > 0:
                suffix = suffix[first_space:]
        
        return suffix
    
    def _title_matches_pattern(self, title: str, pattern: str) -> bool:
        """Check if title matches the detected pattern."""
        if not title or not pattern:
            return True
        
        # Extract prefix and suffix from pattern
        parts = pattern.split("{variable}")
        if len(parts) != 2:
            return True
        
        prefix, suffix = parts
        
        # Check if title has same prefix/suffix
        title_lower = title.lower().strip()
        prefix_lower = prefix.lower().strip()
        suffix_lower = suffix.lower().strip()
        
        has_prefix = not prefix_lower or title_lower.startswith(prefix_lower)
        has_suffix = not suffix_lower or title_lower.endswith(suffix_lower)
        
        return has_prefix and has_suffix
    
    def _extract_base_title_pattern(self, title: str) -> Optional[str]:
        """Extract base pattern from title, removing size/color variations."""
        if not title:
            return None
        
        # Remove common size patterns
        pattern = re.sub(r'\d+\s*(ml|g|kg|cm|mm|l)\b', '', title, flags=re.IGNORECASE)
        
        # Remove common color words
        colors = ['white', 'black', 'red', 'blue', 'green', 'yellow', 'orange', 
                  'purple', 'pink', 'brown', 'gold', 'silver', 'bronze',
                  'weiß', 'schwarz', 'rot', 'blau', 'grün', 'gelb']
        for color in colors:
            pattern = re.sub(rf'\b{color}\b', '', pattern, flags=re.IGNORECASE)
        
        # Clean up
        pattern = re.sub(r'\s+', ' ', pattern).strip()
        
        return pattern if len(pattern) > 3 else None
    
    def _build_corrections(self, result: AnalysisResult, product: Dict) -> List[Dict]:
        """Build list of corrections to apply."""
        corrections = []
        
        if result.sku_issue.detected:
            corrections.append({
                "type": "sku_fix",
                "field": "sku",
                "current": result.sku_issue.current_sku,
                "proposed": result.sku_issue.correct_sku,
                "reason": "SKU contains EAN barcode instead of article number"
            })
        
        if result.naming_issue.detected:
            corrections.append({
                "type": "title_fix",
                "field": "title",
                "current": result.naming_issue.current_title,
                "proposed": result.naming_issue.suggested_title,
                "reason": f"Title doesn't match product group pattern: {result.naming_issue.group_pattern}",
                "confidence": result.naming_issue.confidence
            })
        
        return corrections


def present_analysis_cli(analysis: AnalysisResult, auto_approve: bool = False) -> List[Dict]:
    """
    Present analysis results in CLI and get user confirmation.

    Args:
        analysis: The analysis result
        auto_approve: If True, automatically approve all fixes (for --auto-apply mode)

    Returns list of approved corrections.
    """
    import sys

    if not analysis.has_issues():
        return []

    print("\n" + "=" * 60)
    print("PRODUCT ANALYSIS - Issues Detected")
    print("=" * 60)

    approved = []

    if analysis.sku_issue.detected:
        print("\n[SKU/EAN Mismatch]")
        print(f"  Current SKU: {analysis.sku_issue.current_sku}")
        print(f"  Should be:   {analysis.sku_issue.correct_sku}")
        print(f"  (Current SKU appears to be EAN barcode)")

        if auto_approve:
            print("  Auto-approving SKU fix (--auto-apply mode)")
            approved.append({
                "type": "sku_fix",
                "field": "sku",
                "value": analysis.sku_issue.correct_sku
            })
        elif sys.stdin.isatty():
            resp = input("  Fix SKU? (y/n): ").strip().lower()
            if resp == "y":
                approved.append({
                    "type": "sku_fix",
                    "field": "sku",
                    "value": analysis.sku_issue.correct_sku
                })

    if analysis.naming_issue.detected:
        print("\n[Naming Inconsistency]")
        print(f"  Current title: {analysis.naming_issue.current_title}")
        print(f"  Suggested:     {analysis.naming_issue.suggested_title}")
        print(f"  Group pattern: {analysis.naming_issue.group_pattern}")
        print(f"  Confidence:    {analysis.naming_issue.confidence:.0%}")

        if analysis.naming_issue.similar_products:
            print("  Similar products in group:")
            for p in analysis.naming_issue.similar_products[:5]:
                print(f"    - {p.get('title')}")

        if auto_approve:
            print("  Auto-approving title fix (--auto-apply mode)")
            approved.append({
                "type": "title_fix",
                "field": "title",
                "value": analysis.naming_issue.suggested_title
            })
        elif sys.stdin.isatty():
            resp = input("  Fix title? (y/n): ").strip().lower()
            if resp == "y":
                approved.append({
                    "type": "title_fix",
                    "field": "title",
                    "value": analysis.naming_issue.suggested_title
                })

    print("=" * 60 + "\n")
    
    return approved
