"""
Color Learning System

Dynamically learns colors from Shopify catalog during store profile analysis.
Merges store-specific colors with base COLOR_MAP for comprehensive coverage.
"""

import re
from typing import Dict, List, Set, Tuple
from collections import Counter


class ColorLearner:
    """
    Learns colors from product catalog to expand COLOR_MAP dynamically.

    Integrated with StoreProfileAnalyzer (Phase 2.1) to run during
    initial store connection and catalog analysis.
    """

    def __init__(self, base_color_map: Dict[str, str] = None):
        """
        Initialize with base color map.

        Args:
            base_color_map: Base COLOR_MAP from config.py (default colors)
        """
        from .config import COLOR_MAP
        self.base_color_map = base_color_map or COLOR_MAP

        # Common color words in German/English
        self.color_keywords = {
            # German basics
            'weiss', 'weiß', 'schwarz', 'rot', 'blau', 'grün', 'grun',
            'gelb', 'rosa', 'lila', 'violett', 'braun', 'grau', 'orange',

            # English basics
            'white', 'black', 'red', 'blue', 'green', 'yellow', 'pink',
            'purple', 'brown', 'gray', 'grey', 'orange',

            # Metallics
            'gold', 'silber', 'silver', 'bronze', 'kupfer', 'copper',

            # Extended palette
            'türkis', 'turquoise', 'mint', 'aqua', 'navy', 'marine',
            'beige', 'creme', 'cream', 'ivory', 'elfenbein',
            'koralle', 'coral', 'pfirsich', 'peach', 'apricot',
            'lavendel', 'lavender', 'flieder', 'lilac',
            'magenta', 'fuchsia', 'bordeaux', 'burgund', 'burgundy',
            'olive', 'khaki', 'sand', 'taupe',
            'himmelblau', 'sky', 'petrol', 'teal',
            'lime', 'limone', 'neon',

            # Special/gemstone colors
            'jade', 'smaragd', 'emerald', 'saphir', 'sapphire',
            'ruby', 'rubin', 'amber', 'bernstein', 'amethyst',
            'türkis', 'turquoise', 'opal', 'perle', 'pearl',

            # Transparent/metallic effects
            'transparent', 'transluzent', 'metallic', 'iridescent',
            'schimmernd', 'glitzer', 'glitter', 'perlmutt', 'irisierend'
        }

        # Color pattern (word containing color keyword)
        self.color_pattern = re.compile(
            r'\b(\w*(?:' + '|'.join(self.color_keywords) + r')\w*)\b',
            re.IGNORECASE
        )

    def extract_colors_from_catalog(self, products: List[dict]) -> Dict[str, str]:
        """
        Extract all unique colors from product catalog.

        Args:
            products: List of product dicts from Shopify catalog
                     (should have 'title', 'variants', 'tags')

        Returns:
            Dict mapping raw color → normalized color
            Example: {'mintgrün': 'Mint Grün', 'apricot': 'Apricot'}
        """
        color_candidates = []

        for product in products:
            # Extract from title
            title = str(product.get('title', ''))
            color_candidates.extend(self._extract_color_words(title))

            # Extract from variant titles
            variants = product.get('variants', [])
            for variant in variants:
                if isinstance(variant, dict):
                    variant_title = str(variant.get('title', ''))
                    if variant_title and variant_title.lower() != 'default title':
                        color_candidates.extend(self._extract_color_words(variant_title))

                    # Also check variant option values
                    option1 = str(variant.get('option1', ''))
                    option2 = str(variant.get('option2', ''))
                    option3 = str(variant.get('option3', ''))
                    color_candidates.extend(self._extract_color_words(option1))
                    color_candidates.extend(self._extract_color_words(option2))
                    color_candidates.extend(self._extract_color_words(option3))

            # Extract from tags
            tags = product.get('tags', '')
            if isinstance(tags, str):
                color_candidates.extend(self._extract_color_words(tags))

        # Count occurrences (filter noise)
        color_counts = Counter(color_candidates)

        # Build normalized color map
        learned_colors = {}
        for color, count in color_counts.items():
            # Skip if already in base map
            if color.lower() in self.base_color_map:
                continue

            # Only include colors that appear at least 2 times
            # (filters out one-off typos)
            if count >= 2:
                normalized = self._normalize_color(color)
                learned_colors[color.lower()] = normalized

        return learned_colors

    def _extract_color_words(self, text: str) -> List[str]:
        """
        Extract potential color words from text.

        Args:
            text: Product title, variant name, or tag string

        Returns:
            List of potential color words
        """
        if not text or not isinstance(text, str):
            return []

        matches = self.color_pattern.findall(text)

        # Filter out common false positives
        false_positives = {
            'format', 'papier', 'paper', 'farbe', 'paint',
            'decoupage', 'vintage', 'classic', 'modern',
            'set', 'pack', 'premium', 'basic'
        }

        return [
            m for m in matches
            if m.lower() not in false_positives and len(m) >= 3
        ]

    def _normalize_color(self, color: str) -> str:
        """
        Normalize a color string to consistent format.

        German color words get first letter capitalized.
        Compound colors get proper spacing and capitalization.

        Args:
            color: Raw color string (e.g., "mintgrün", "sky-blue")

        Returns:
            Normalized color (e.g., "Mint Grün", "Sky Blue")
        """
        # Remove hyphens, underscores
        normalized = re.sub(r'[-_]', ' ', color)

        # Capitalize each word
        words = normalized.split()
        capitalized_words = []

        for word in words:
            # Keep abbreviations uppercase
            if word.isupper() and len(word) <= 3:
                capitalized_words.append(word)
            else:
                capitalized_words.append(word.capitalize())

        return ' '.join(capitalized_words)

    def merge_with_base_map(self, learned_colors: Dict[str, str]) -> Dict[str, str]:
        """
        Merge learned colors with base COLOR_MAP.

        Base colors take precedence (they're curated).

        Args:
            learned_colors: Colors extracted from catalog

        Returns:
            Combined color map (base + learned)
        """
        combined = dict(self.base_color_map)  # Start with base

        # Add learned colors (won't overwrite base)
        for raw, normalized in learned_colors.items():
            if raw not in combined:
                combined[raw] = normalized

        return combined

    def analyze_catalog_colors(self, products: List[dict]) -> Dict:
        """
        Analyze catalog and return color statistics.

        Useful for understanding color coverage before/after learning.

        Args:
            products: List of product dicts

        Returns:
            Dict with statistics:
            - learned_colors: New colors found
            - total_learned: Count of new colors
            - coverage_increase: % increase in recognized colors
            - sample_products: Example products using new colors
        """
        learned = self.extract_colors_from_catalog(products)

        # Find products using learned colors
        sample_products = []
        for color in list(learned.keys())[:5]:  # Sample 5
            for product in products:
                title = str(product.get('title', '')).lower()
                if color in title:
                    sample_products.append({
                        'title': product.get('title'),
                        'learned_color': learned[color]
                    })
                    break

        base_count = len(self.base_color_map)
        learned_count = len(learned)
        coverage_increase = (learned_count / base_count * 100) if base_count > 0 else 0

        return {
            'learned_colors': learned,
            'total_learned': learned_count,
            'base_colors': base_count,
            'coverage_increase_percent': round(coverage_increase, 1),
            'sample_products': sample_products
        }


def load_store_colors(store_profile_path: str = None) -> Dict[str, str]:
    """
    Load store-specific colors from store profile.

    Called by EnrichmentPipeline to get dynamic color map.

    Args:
        store_profile_path: Path to store profile JSON
                           Default: data/store_profile.json

    Returns:
        Dict mapping raw color → normalized color
        Empty dict if profile not found
    """
    import json
    from pathlib import Path

    if not store_profile_path:
        store_profile_path = Path('data/store_profile.json')
    else:
        store_profile_path = Path(store_profile_path)

    if not store_profile_path.exists():
        return {}

    try:
        with open(store_profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        # Colors stored in profile['colors']['learned']
        return profile.get('colors', {}).get('learned', {})
    except Exception:
        return {}


def save_store_colors(learned_colors: Dict[str, str],
                     store_profile_path: str = None):
    """
    Save learned colors to store profile.

    Called by StoreProfileAnalyzer after catalog analysis.

    Args:
        learned_colors: Dict of learned colors
        store_profile_path: Path to store profile JSON
    """
    import json
    from pathlib import Path

    if not store_profile_path:
        store_profile_path = Path('data/store_profile.json')
    else:
        store_profile_path = Path(store_profile_path)

    # Load existing profile or create new
    profile = {}
    if store_profile_path.exists():
        with open(store_profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

    # Update colors section
    if 'colors' not in profile:
        profile['colors'] = {}

    profile['colors']['learned'] = learned_colors
    profile['colors']['count'] = len(learned_colors)

    # Save
    store_profile_path.parent.mkdir(parents=True, exist_ok=True)
    with open(store_profile_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
