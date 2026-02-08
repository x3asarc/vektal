"""
Product Family Grouper - groups variants (same product, different sizes/colors)
"""
import re
from typing import Dict, List, Set
from collections import defaultdict


class ProductFamilyGrouper:
    """Group product variants into families (same product, different sizes/colors)"""

    def __init__(self):
        self.families: Dict[str, dict] = {}
        self.family_counter: int = 0

    def create_families(self, products: List[dict]) -> List[dict]:
        """
        Group products into families based on normalized title similarity.

        Example:
        - "Pentart Acrylfarbe Jade 20ml"
        - "Pentart Acrylfarbe Jade 50ml"
        → Same family, different sizes

        Returns products with family_id, is_base_variant, variant_count added.
        """
        # Reset for new batch
        self.families = {}
        self.family_counter = 0

        # Group by base product name
        for product in products:
            family_key = self._generate_family_key(product)

            if family_key not in self.families:
                self.family_counter += 1
                self.families[family_key] = {
                    'family_id': f"fam_{self.family_counter:05d}",
                    'base_title': family_key,
                    'product_ids': [],
                    'variants': [],
                    'colors': set(),
                    'sizes': set(),
                    'materials': set()
                }

            family = self.families[family_key]
            product_id = product.get('id', product.get('sku', f"product_{len(family['product_ids'])}"))
            family['product_ids'].append(product_id)
            family['variants'].append({
                'id': product_id,
                'title': product.get('title', ''),
                'sku': product.get('sku', ''),
                'color': product.get('extracted_color'),
                'size': product.get('extracted_size'),
                'unit': product.get('extracted_unit')
            })

            # Collect family attributes
            if product.get('extracted_color'):
                family['colors'].add(product['extracted_color'])
            if product.get('extracted_size'):
                size_str = f"{product['extracted_size']}{product.get('extracted_unit', '')}"
                family['sizes'].add(size_str)
            if product.get('extracted_material'):
                family['materials'].add(product['extracted_material'])

        # Assign family IDs back to products
        enriched_products = []
        for product in products:
            family_key = self._generate_family_key(product)
            family_data = self.families.get(family_key, {})

            product_id = product.get('id', product.get('sku'))

            # Add family metadata
            product['family_id'] = family_data.get('family_id')
            product['variant_count'] = len(family_data.get('product_ids', []))

            # Mark first product as base variant
            product['is_base_variant'] = (product_id == family_data.get('product_ids', [None])[0])

            # Add family metadata
            product['family_colors'] = sorted(list(family_data.get('colors', [])))
            product['family_sizes'] = sorted(list(family_data.get('sizes', [])),
                                            key=self._size_sort_key)

            enriched_products.append(product)

        return enriched_products

    def _generate_family_key(self, product: dict) -> str:
        """
        Generate normalized family key by removing variant indicators.

        Removes:
        - Size patterns: 20ml, 50g, 100cm
        - Dimension patterns: 14x14cm
        - Color names: rot, blau, grün, jade, ruby
        """
        title = product.get('title', '')

        # Remove size patterns: 20ml, 50g, etc.
        key = re.sub(r'\d+[.,]?\d*\s*(ml|l|g|kg|cm|mm|m²|m2|pcs|stk|piece)',
                     '', title, flags=re.IGNORECASE)

        # Remove dimension patterns: 14x14cm
        key = re.sub(r'\d+\s*x\s*\d+\s*(cm|mm)',
                     '', key, flags=re.IGNORECASE)

        # Remove standalone color names
        color_pattern = r'\b(rot|blau|grün|gelb|schwarz|weiß|gold|silber|bronze|jade|ruby|emerald)\b'
        key = re.sub(color_pattern, '', key, flags=re.IGNORECASE)

        # Normalize whitespace
        key = re.sub(r'\s+', ' ', key).strip().lower()

        # Sanity check - if too short, use original
        if len(key) < 10:
            key = title.lower()

        return key

    def _size_sort_key(self, size_str: str) -> float:
        """Extract numeric value from size for sorting"""
        match = re.search(r'([0-9]+[.,]?[0-9]*)', size_str.replace(',', '.'))
        if match:
            return float(match.group(1))
        return 0.0

    def get_family_summary(self, family_id: str) -> dict:
        """Get summary of a product family for display"""
        for family in self.families.values():
            if family['family_id'] == family_id:
                return {
                    'family_id': family['family_id'],
                    'base_title': family['base_title'],
                    'product_count': len(family['product_ids']),
                    'available_colors': sorted(list(family['colors'])),
                    'available_sizes': sorted(list(family['sizes']), key=self._size_sort_key),
                    'materials': sorted(list(family['materials'])),
                    'variants': family['variants']
                }
        return {}
