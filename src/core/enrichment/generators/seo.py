"""SEO content generation for German e-commerce.

Generates SEO-optimized meta titles, descriptions, URL handles, and image alt text
following German e-commerce best practices and Google guidelines.
"""
import re
from typing import Optional


class SEOGenerator:
    """Generate SEO-optimized content for German e-commerce"""

    # German umlaut transliteration for URLs
    UMLAUT_MAP = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'
    }

    # Stop words to remove from URLs (after transliteration)
    GERMAN_STOP_WORDS = ['der', 'die', 'das', 'und', 'fuer', 'mit', 'von', 'in', 'zu', 'auf', 'an']

    # Call-to-action phrases for meta descriptions (rotated for variety)
    CTAS = [
        "Jetzt bestellen!",
        "Schnelle Lieferung!",
        "Jetzt entdecken!",
        "Sofort verfügbar!",
        "Online bestellen!"
    ]

    def __init__(self, store_name: str = "Bastelschachtel"):
        """Initialize SEO generator.

        Args:
            store_name: Store name to include in meta titles
        """
        self.store_name = store_name
        self._cta_index = 0  # For rotating CTAs

    def generate_meta_title(self, product_name: str, size: str = None,
                           vendor: str = None, max_length: int = 60) -> str:
        """Generate SEO meta title under 60 chars.

        Format: {product_name} {size} | {store_name}
        Example: "Reispapier Vintage Rose A4 | Bastelschachtel"

        Args:
            product_name: Product name/title
            size: Optional size specification (e.g., "A4", "20ml")
            vendor: Optional vendor name (not typically included to save space)
            max_length: Maximum character length (default: 60)

        Returns:
            SEO-optimized meta title
        """
        # Start with product name
        parts = [product_name]

        # Add size if provided and space allows
        if size:
            parts.append(size)

        # Combine parts
        title = " ".join(parts)

        # Add store name separator if space allows
        separator = f" | {self.store_name}"
        if len(title + separator) <= max_length:
            title += separator
        else:
            # Try to fit by trimming product name
            max_product_length = max_length - len(separator)
            if max_product_length > 20:  # Ensure minimum readable length
                title = title[:max_product_length].rsplit(' ', 1)[0] + separator
            # else: skip store name to preserve product info

        return title[:max_length]

    def generate_meta_description(self, product_name: str, vendor: str,
                                  key_feature: str, size: str = None,
                                  min_length: int = 120,
                                  max_length: int = 160) -> str:
        """Generate meta description 120-160 chars.

        Format: {product_name} von {vendor} - {key_feature}. {size}. {cta}

        Args:
            product_name: Product name/title
            vendor: Vendor/brand name
            key_feature: Key product feature or use case
            size: Optional size specification
            min_length: Minimum character length (default: 120)
            max_length: Maximum character length (default: 160)

        Returns:
            SEO-optimized meta description
        """
        # Build base description
        desc = f"{product_name} von {vendor} - {key_feature}."

        # Add size if provided
        if size:
            desc += f" {size}."

        # Ensure minimum length - pad with generic text if needed BEFORE CTA
        if len(desc) < min_length:
            padding = " Ideal für kreative Bastelprojekte und Handarbeiten aller Art."
            if len(desc + padding) <= max_length:
                desc += padding
            elif len(desc) < min_length:
                # Still too short, add shorter padding
                padding = " Hochwertiges Bastelmaterial für kreative Projekte."
                if len(desc + padding) <= max_length:
                    desc += padding

        # Add CTA if space allows (after padding)
        cta = self._get_next_cta()
        if len(desc + " " + cta) <= max_length:
            desc += f" {cta}"

        return desc[:max_length]

    def generate_url_handle(self, product_name: str, size: str = None,
                           vendor: str = None, max_length: int = 80) -> str:
        """Generate SEO-friendly URL handle.

        Rules:
        - Lowercase
        - German umlaut transliteration (ü → ue)
        - Remove stop words
        - Replace spaces/special chars with hyphens
        - Collapse multiple hyphens
        - Max 80 chars

        Args:
            product_name: Product name/title
            size: Optional size to include in handle
            vendor: Optional vendor name to include
            max_length: Maximum character length (default: 80)

        Returns:
            URL-safe handle (e.g., "pentart-acrylfarbe-gruen-20ml")
        """
        # Combine parts
        parts = []
        if vendor:
            parts.append(vendor)
        parts.append(product_name)
        if size:
            parts.append(size)

        text = " ".join(parts)

        # Lowercase
        handle = text.lower()

        # Transliterate German umlauts
        for umlaut, replacement in self.UMLAUT_MAP.items():
            handle = handle.replace(umlaut, replacement)

        # Replace special characters with hyphens
        handle = re.sub(r'[^a-z0-9\-]', '-', handle)

        # Remove stop words (split by hyphen, filter, rejoin)
        words = handle.split('-')
        words = [w for w in words if w and w not in self.GERMAN_STOP_WORDS]
        handle = '-'.join(words)

        # Collapse multiple hyphens
        handle = re.sub(r'-+', '-', handle)

        # Strip leading/trailing hyphens
        handle = handle.strip('-')

        # Enforce max length
        if len(handle) > max_length:
            # Truncate at last hyphen before max_length
            handle = handle[:max_length]
            if '-' in handle:
                handle = handle.rsplit('-', 1)[0]

        return handle

    def generate_image_alt_text(self, product_type: str, motif: str = None,
                               size: str = None, vendor: str = None,
                               max_length: int = 125) -> str:
        """Generate image alt text for accessibility & SEO.

        Format: {product_type} {motif} {size} {vendor}

        Args:
            product_type: Type of product (e.g., "Reispapier", "Acrylfarbe")
            motif: Optional motif/pattern description
            size: Optional size specification
            vendor: Optional vendor name
            max_length: Maximum character length (default: 125)

        Returns:
            Descriptive alt text for images
        """
        parts = [product_type]

        if motif:
            parts.append(motif)
        if size:
            parts.append(size)
        if vendor:
            parts.append(f"von {vendor}")

        alt_text = " ".join(parts)
        return alt_text[:max_length]

    def _get_next_cta(self) -> str:
        """Get next CTA from rotation list.

        Returns:
            Call-to-action phrase
        """
        cta = self.CTAS[self._cta_index]
        self._cta_index = (self._cta_index + 1) % len(self.CTAS)
        return cta
