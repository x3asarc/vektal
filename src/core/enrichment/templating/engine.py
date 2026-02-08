"""Jinja2-based template engine for vendor YAML content templates."""

from jinja2 import Environment, StrictUndefined, BaseLoader
from typing import Dict, Optional


class TemplateEngine:
    """Render vendor YAML content templates using Jinja2"""

    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            undefined=StrictUndefined,  # Raise error on missing variables
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._register_filters()

    def _register_filters(self):
        """Register custom Jinja2 filters for German text"""
        self.env.filters['german_capitalize'] = self._german_capitalize
        self.env.filters['umlaut_safe'] = self._umlaut_safe
        self.env.filters['truncate_german'] = self._truncate_german

    def _german_capitalize(self, text: str) -> str:
        """Capitalize with German umlaut support"""
        if not text:
            return ''
        return text[0].upper() + text[1:]

    def _umlaut_safe(self, text: str) -> str:
        """Transliterate German umlauts for URLs"""
        replacements = {
            'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'
        }
        for umlaut, replacement in replacements.items():
            text = text.replace(umlaut, replacement)
        return text

    def _truncate_german(self, text: str, length: int = 160) -> str:
        """Truncate text at word boundary, respecting German compounds"""
        if len(text) <= length:
            return text
        truncated = text[:length].rsplit(' ', 1)[0]
        return truncated + '...'

    def render(self, template_str: str, context: Dict) -> str:
        """
        Render a template string with context.

        Args:
            template_str: Jinja2 template string from vendor YAML
            context: Variables to substitute

        Returns:
            Rendered string

        Raises:
            UndefinedError if variable missing
        """
        template = self.env.from_string(template_str)
        return template.render(**context)

    def render_product_content(self, vendor_config: dict,
                              product: dict) -> dict:
        """
        Render all content templates for a product.

        Uses vendor YAML enrichment.content_templates section.

        Returns dict with rendered title, description, meta_title, etc.
        """
        templates = vendor_config.get('enrichment', {}).get('content_templates', {})
        context = self._build_context(product, vendor_config)

        result = {}

        # Render title template
        if 'title' in templates:
            title_config = templates['title']
            result['title'] = self.render(
                title_config.get('template', '{product_name}'),
                context
            )[:title_config.get('max_length', 70)]

        # Render description sections
        if 'description' in templates:
            desc_config = templates['description']
            sections = []

            for section_name, section_config in desc_config.get('sections', {}).items():
                try:
                    rendered = self.render(section_config.get('template', ''), context)
                    if rendered.strip():
                        sections.append(rendered)
                except Exception:
                    pass  # Skip sections with missing variables

            result['description'] = '\n\n'.join(sections)

        return result

    def _build_context(self, product: dict, vendor_config: dict) -> dict:
        """Build template context from product and vendor config"""
        vendor_info = vendor_config.get('vendor', {})

        return {
            'product_name': product.get('title', ''),
            'product_type': product.get('product_type', ''),
            'vendor': vendor_info.get('name', ''),
            'size': product.get('extracted_size', ''),
            'size_display': product.get('size_display', ''),
            'color': product.get('extracted_color', ''),
            'material': product.get('extracted_material', ''),
            'category': product.get('inferred_category', ''),
            'sku': product.get('sku', ''),
            'price': product.get('price', ''),
            'origin': vendor_info.get('country', ''),
            'technique': 'Decoupage',  # Default
            'use_cases': ', '.join(product.get('extracted_use_cases', [])),
            'store_name': 'Bastelschachtel',
        }

    def validate_template(self, template_str: str,
                         required_vars: list = None) -> tuple:
        """
        Validate a template string.

        Returns (is_valid: bool, error_message: str or None)
        """
        try:
            template = self.env.from_string(template_str)
            # If required vars specified, try rendering with dummy data
            if required_vars:
                dummy = {var: f'__{var}__' for var in required_vars}
                template.render(**dummy)
            return True, None
        except Exception as e:
            return False, str(e)
