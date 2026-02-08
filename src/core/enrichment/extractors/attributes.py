"""
Attribute extraction from product titles and descriptions.

Extracts structured attributes like colors, sizes, materials, and categories
from German and English product text.
"""
import re
from typing import Dict, List, Optional
from ..config import COLOR_MAP, CATEGORY_KEYWORDS, USE_CASE_PATTERNS


class AttributeExtractor:
    """Extract structured attributes from product text (German-first)"""

    def __init__(self):
        """Initialize extractor with compiled regex patterns"""
        # Color patterns: all keys from COLOR_MAP + special colors
        color_keys = '|'.join(COLOR_MAP.keys())
        self.color_patterns = [
            re.compile(r'\b(' + color_keys + r')\b', re.IGNORECASE),
            re.compile(
                r'\b(jade|ruby|emerald|saphir|kupfer|magenta|cyan|bordeaux|'
                r'petrol|mint|lavendel|koralle)\b',
                re.IGNORECASE
            )
        ]

        # Size patterns: various formats (20ml, 50g, 14x14cm, A4)
        self.size_patterns = [
            # Simple: 20ml, 50g, 100pcs
            re.compile(r'(\d+(?:[.,]\d+)?)\s*(ml|l|g|kg|cm|mm|m²|m2|pcs|stk|stück|piece|pack|set)', re.IGNORECASE),
            # Dimensions: 14x14cm
            re.compile(r'(\d+)\s*x\s*(\d+)\s*(cm|mm)', re.IGNORECASE),
            # German comma format: 14, 14cm
            re.compile(r'(\d+),\s*(\d+)\s*(cm|mm)', re.IGNORECASE),
            # Verbose: 10cm x 15cm
            re.compile(r'(\d+)\s*(cm|mm)\s*x\s*(\d+)\s*(cm|mm)', re.IGNORECASE),
            # Paper formats: A4, A3, A5
            re.compile(r'\b(A[0-9]|DIN\s*A[0-9])\b', re.IGNORECASE)
        ]

        # Material patterns
        self.material_patterns = [
            re.compile(
                r'\b(acryl|acrylfarbe|öl|ölfarbe|harz|epoxid|epoxy|'
                r'wasserbasis|wasserbasiert|alkohol|textil|textilfarbe|'
                r'holz|glas|metall|kunststoff|papier|pappe|stoff|leder|'
                r'keramik|porzellan)\b',
                re.IGNORECASE
            )
        ]

    def extract_from_title(self, title: str) -> Dict:
        """
        Extract color, size, unit, material, category from product title.

        Args:
            title: Product title string

        Returns:
            Dict with extracted_color, extracted_size, extracted_unit,
            extracted_material, inferred_category
        """
        if not isinstance(title, str):
            title = str(title)

        title_lower = title.lower()
        result = {
            'extracted_color': None,
            'extracted_size': None,
            'extracted_unit': None,
            'extracted_material': None,
            'inferred_category': None
        }

        # Extract color (normalize to standard names)
        for pattern in self.color_patterns:
            match = pattern.search(title_lower)
            if match:
                raw_color = match.group(1).lower()
                result['extracted_color'] = COLOR_MAP.get(raw_color, raw_color.capitalize())
                break

        # Extract size and unit
        for pattern in self.size_patterns:
            match = pattern.search(title_lower)
            if match:
                # Handle paper format (A4, A3, etc.)
                if 'A' in match.group(0).upper() or 'DIN' in match.group(0).upper():
                    result['extracted_size'] = match.group(1).upper()
                    result['extracted_unit'] = 'format'
                # Handle dimension format (14x14cm)
                elif 'x' in match.group(0).lower() and len(match.groups()) >= 3:
                    if match.lastindex >= 3:
                        result['extracted_size'] = f"{match.group(1)}x{match.group(2)}"
                        result['extracted_unit'] = match.group(3).lower()
                    else:
                        result['extracted_size'] = match.group(1)
                        result['extracted_unit'] = match.group(2).lower()
                # Simple size (20ml, 50g)
                else:
                    result['extracted_size'] = match.group(1).replace(',', '.')
                    result['extracted_unit'] = match.group(2).lower()
                break

        # Extract material
        for pattern in self.material_patterns:
            match = pattern.search(title_lower)
            if match:
                material = match.group(1)
                # Normalize common materials
                if material in ['acrylfarbe', 'acryl']:
                    material = 'Acryl'
                elif material in ['öl', 'ölfarbe']:
                    material = 'Öl'
                elif material in ['textil', 'textilfarbe']:
                    material = 'Textil'
                elif material in ['harz', 'epoxid', 'epoxy']:
                    material = 'Harz'
                else:
                    material = material.capitalize()
                result['extracted_material'] = material
                break

        # Infer category from keywords
        result['inferred_category'] = self._infer_category(title_lower)

        return result

    def extract_from_description(self, description: str) -> Dict:
        """
        Extract use cases and feature flags from product description.

        Args:
            description: Product description text

        Returns:
            Dict with extracted_use_cases (list), has_care_instructions,
            is_waterproof, is_washable, is_heat_resistant, is_solvent_free,
            is_non_toxic
        """
        if not isinstance(description, str) or len(description) < 5:
            return {
                'extracted_use_cases': [],
                'has_care_instructions': False,
                'is_waterproof': False,
                'is_washable': False,
                'is_heat_resistant': False,
                'is_solvent_free': False,
                'is_non_toxic': False
            }

        desc_lower = description.lower()

        # Extract use cases
        use_cases = []
        for use_case, keywords in USE_CASE_PATTERNS.items():
            if any(kw in desc_lower for kw in keywords):
                use_cases.append(use_case)

        # Extract feature flags
        features = {
            'has_care_instructions': any(word in desc_lower for word in ['waschbar', 'pflege', 'reinigung']),
            'is_waterproof': any(word in desc_lower for word in ['wasserfest', 'wasserdicht', 'wasserabweisend']),
            'is_washable': any(word in desc_lower for word in ['waschbar', 'waschfest']),
            'is_heat_resistant': any(word in desc_lower for word in ['hitzebeständig', 'hitze', 'brennbar']),
            'is_solvent_free': any(word in desc_lower for word in ['lösemittelfrei', 'lösungsmittelfrei']),
            'is_non_toxic': any(word in desc_lower for word in ['ungiftig', 'kindersicher', 'nicht giftig'])
        }

        return {
            'extracted_use_cases': use_cases,
            **features
        }

    def extract_all(self, title: str, description: str = "") -> Dict:
        """
        Extract all attributes from both title and description.

        Args:
            title: Product title
            description: Product description (optional)

        Returns:
            Combined dict with all extracted attributes
        """
        title_attrs = self.extract_from_title(title)
        desc_attrs = self.extract_from_description(description)

        return {
            **title_attrs,
            **desc_attrs
        }

    def calculate_quality_score(self, product_data: Dict) -> int:
        """
        Calculate 0-100 quality score based on data completeness.

        Scoring breakdown:
        - Description quality (40-50 points): >100 chars = 40, >50 = 30, >20 = 15
        - Structured data (30-40 points): Color +10, Size +10, Material +10, +10 extra
        - Categorization (20-30 points): Category +10, Product type +10, +10 extra
        - Tags (10 points): Tags present = +10

        Args:
            product_data: Dict with product fields (description, extracted_*,
                         product_type, tags)

        Returns:
            Quality score 0-100
        """
        score = 0

        # Description quality (up to 40 points)
        desc_len = len(str(product_data.get('description', '')))
        if desc_len > 100:
            score += 40
        elif desc_len > 50:
            score += 30
        elif desc_len > 20:
            score += 15

        # Structured data richness (up to 30 points)
        if product_data.get('extracted_color'):
            score += 10
        if product_data.get('extracted_size'):
            score += 10
        if product_data.get('extracted_material'):
            score += 10

        # Categorization (up to 20 points)
        if product_data.get('inferred_category'):
            score += 10
        if product_data.get('product_type') and len(str(product_data.get('product_type', ''))) > 2:
            score += 10

        # Tags presence (up to 10 points)
        if product_data.get('tags') and len(str(product_data.get('tags', ''))) > 10:
            score += 10

        return min(score, 100)

    def _infer_category(self, text_lower: str) -> Optional[str]:
        """
        Infer product category from text using CATEGORY_KEYWORDS.

        Args:
            text_lower: Lowercased text to analyze

        Returns:
            Category name or None if no match
        """
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return category
        return None
