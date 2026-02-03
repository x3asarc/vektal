"""
Unit tests for Image Processing Framework

Tests all framework components:
- ImageFramework (main interface)
- ImageProcessor (transformations)
- ImageNamingEngine (filenames + alt text)
- ImageUploadStrategy (upload method selection)
- ImagePositioningEngine (positioning logic)
"""

import unittest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.image_framework import (
    ImageFramework,
    ImageProcessor,
    ImageNamingEngine,
    ImageUploadStrategy,
    ImagePositioningEngine
)


class TestImageFramework(unittest.TestCase):
    """Test main ImageFramework class."""

    def setUp(self):
        """Set up test framework instance."""
        self.framework = ImageFramework()

    def test_framework_loads_rules(self):
        """Test that framework loads rules from YAML config."""
        self.assertIsNotNone(self.framework.rules)
        self.assertEqual(self.framework.rules.get("version"), "1.0")

    def test_process_primary_image(self):
        """Test processing primary image."""
        product = {
            "id": "gid://shopify/Product/123",
            "title": "Galaxy Flakes 15g - Jupiter white",
            "vendor": "Pentart"
        }

        result = self.framework.process_image(
            product=product,
            image_url="https://example.com/image.jpg",
            image_role="primary",
            vendor="Pentart"
        )

        # Verify all required keys present
        self.assertIn("filename", result)
        self.assertIn("alt_text", result)
        self.assertIn("image_type", result)
        self.assertIn("transformations", result)
        self.assertIn("upload_strategy", result)
        self.assertIn("position", result)

        # Verify filename structure (vendor-product-variant.ext)
        self.assertTrue(result["filename"].startswith("pentart-"))
        self.assertTrue(result["filename"].endswith(".png") or result["filename"].endswith(".jpg"))

        # Verify alt text contains key elements
        self.assertIn("Pentart", result["alt_text"])

        # Verify upload strategy
        self.assertEqual(result["upload_strategy"], "staged")

        # Verify position (primary = 0)
        self.assertEqual(result["position"], 0)

    def test_process_shared_image(self):
        """Test processing shared image."""
        product = {
            "id": "gid://shopify/Product/123",
            "title": "Galaxy Flakes 15g - Jupiter white",
            "vendor": "Pentart"
        }

        result = self.framework.process_image(
            product=product,
            image_url="https://example.com/groupshot.jpg",
            image_role="shared",
            vendor="Pentart"
        )

        # Verify filename structure (vendor-product-type.ext)
        self.assertTrue(result["filename"].startswith("pentart-"))

        # Verify position (shared = append)
        self.assertEqual(result["position"], "append")

    def test_slugify(self):
        """Test slug generation."""
        # Test basic slugification
        self.assertEqual(
            self.framework._slugify("Galaxy Flakes 15g"),
            "galaxy-flakes-15g"
        )

        # Test special characters
        self.assertEqual(
            self.framework._slugify("Product Name! @#$"),
            "product-name"
        )

        # Test consecutive spaces/hyphens
        self.assertEqual(
            self.framework._slugify("Product   Name"),
            "product-name"
        )

    def test_validate_filename(self):
        """Test filename validation."""
        # Valid filenames
        self.assertTrue(self.framework.validate_filename("pentart-galaxy-flakes-15g-packshot.jpg"))
        self.assertTrue(self.framework.validate_filename("vendor-product-detail.png"))

        # Invalid filenames (uppercase, spaces, special chars)
        self.assertFalse(self.framework.validate_filename("PENTART-Galaxy-Flakes.JPG"))
        self.assertFalse(self.framework.validate_filename("product name.jpg"))
        self.assertFalse(self.framework.validate_filename("product!@#.jpg"))


class TestImageProcessor(unittest.TestCase):
    """Test ImageProcessor class."""

    def setUp(self):
        """Set up test processor."""
        framework = ImageFramework()
        self.processor = framework.processor

    def test_get_transformations_primary(self):
        """Test getting transformations for primary image."""
        transformations = self.processor.get_transformations(
            image_type="packshot",
            image_role="primary",
            vendor="Pentart"
        )

        # Verify transformation keys
        self.assertIn("convert_to_square", transformations)
        self.assertIn("ensure_transparency", transformations)
        self.assertIn("format", transformations)

        # Primary images should be PNG
        self.assertEqual(transformations["format"], "png")

    def test_get_transformations_shared(self):
        """Test getting transformations for shared image."""
        transformations = self.processor.get_transformations(
            image_type="groupshot",
            image_role="shared",
            vendor="Pentart"
        )

        # Shared images should be JPG
        self.assertEqual(transformations["format"], "jpg")

    def test_square_conversion_config(self):
        """Test square conversion configuration."""
        transformations = self.processor.get_transformations(
            image_type="packshot",
            image_role="primary"
        )

        square_config = transformations.get("convert_to_square", {})
        self.assertEqual(square_config.get("method"), "center_crop")
        self.assertEqual(square_config.get("target_size"), 900)


class TestImageNamingEngine(unittest.TestCase):
    """Test ImageNamingEngine class."""

    def setUp(self):
        """Set up test naming engine."""
        framework = ImageFramework()
        self.naming_engine = framework.naming_engine

    def test_generate_primary_filename(self):
        """Test generating filename for primary image."""
        product_context = {
            "product_slug": "galaxy-flakes-15g",
            "variant_slug": "jupiter-white",
            "vendor": "Pentart",
            "role": "primary"
        }

        filename = self.naming_engine.generate_filename(
            image_type="packshot",
            product_context=product_context,
            image_role="primary",
            vendor="pentart"
        )

        # Should match pattern: vendor-product-variant.ext
        self.assertTrue(filename.startswith("pentart-"))
        self.assertIn("galaxy-flakes-15g", filename)
        self.assertIn("jupiter-white", filename)
        self.assertTrue(filename.endswith(".png"))

    def test_generate_shared_filename(self):
        """Test generating filename for shared image."""
        product_context = {
            "product_slug": "galaxy-flakes-15g",
            "vendor": "Pentart",
            "role": "shared"
        }

        filename = self.naming_engine.generate_filename(
            image_type="groupshot",
            product_context=product_context,
            image_role="shared",
            vendor="pentart"
        )

        # Should match pattern: vendor-product-type.ext
        self.assertTrue(filename.startswith("pentart-"))
        self.assertIn("galaxy-flakes-15g", filename)
        self.assertIn("groupshot", filename)

    def test_generate_primary_alt_text(self):
        """Test generating alt text for primary image."""
        product_context = {
            "product_line": "Galaxy Flakes 15g",
            "variant_name": "Jupiter white",
            "vendor": "Pentart",
            "role": "primary"
        }

        alt_text = self.naming_engine.generate_alt_text(
            image_type="packshot",
            product_context=product_context,
            image_role="primary",
            vendor="Pentart"
        )

        # Should contain key elements
        self.assertIn("Galaxy Flakes 15g", alt_text)
        self.assertIn("Jupiter white", alt_text)
        self.assertIn("Pentart", alt_text)
        self.assertIn("Produktfoto", alt_text)  # German translation

    def test_generate_shared_alt_text(self):
        """Test generating alt text for shared image."""
        product_context = {
            "product_line": "Galaxy Flakes",
            "vendor": "Pentart",
            "role": "shared"
        }

        alt_text = self.naming_engine.generate_alt_text(
            image_type="groupshot",
            product_context=product_context,
            image_role="shared",
            vendor="Pentart"
        )

        # Should contain key elements
        self.assertIn("Galaxy Flakes", alt_text)
        self.assertIn("Pentart", alt_text)
        self.assertIn("Gruppenbild", alt_text)  # German translation

    def test_alt_text_max_length(self):
        """Test alt text respects max length."""
        product_context = {
            "product_line": "Very Long Product Name That Exceeds Maximum Length Limit",
            "variant_name": "Very Long Variant Name That Also Exceeds Maximum Length Limit",
            "vendor": "Very Long Vendor Name",
            "role": "primary"
        }

        alt_text = self.naming_engine.generate_alt_text(
            image_type="packshot",
            product_context=product_context,
            image_role="primary",
            vendor="Very Long Vendor Name"
        )

        # Should be truncated to max length (125)
        self.assertLessEqual(len(alt_text), 125)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test lowercase conversion
        result = self.naming_engine._sanitize_filename("PENTART-Galaxy-Flakes.PNG")
        self.assertEqual(result, "pentart-galaxy-flakes.png")

        # Test space replacement
        result = self.naming_engine._sanitize_filename("pentart galaxy flakes.png")
        self.assertEqual(result, "pentart-galaxy-flakes.png")

        # Test special character removal (special chars removed, no hyphens added)
        result = self.naming_engine._sanitize_filename("pentart!@#galaxy$%^flakes.png")
        self.assertEqual(result, "pentartgalaxyflakes.png")


class TestImageUploadStrategy(unittest.TestCase):
    """Test ImageUploadStrategy class."""

    def setUp(self):
        """Set up test upload strategy."""
        framework = ImageFramework()
        self.upload_strategy = framework.upload_strategy

    def test_determine_method_primary(self):
        """Test upload method for primary image."""
        method = self.upload_strategy.determine_method(
            image_role="primary",
            vendor="Pentart"
        )

        # Primary images should use staged upload
        self.assertEqual(method, "staged")

    def test_determine_method_shared(self):
        """Test upload method for shared image."""
        method = self.upload_strategy.determine_method(
            image_role="shared",
            vendor="Pentart"
        )

        # Shared images should use staged upload (for filename control)
        self.assertEqual(method, "staged")


class TestImagePositioningEngine(unittest.TestCase):
    """Test ImagePositioningEngine class."""

    def setUp(self):
        """Set up test positioning engine."""
        framework = ImageFramework()
        self.positioning_engine = framework.positioning_engine

    def test_get_position_primary(self):
        """Test position for primary image."""
        position = self.positioning_engine.get_position(
            image_role="primary",
            vendor="Pentart"
        )

        # Primary should be position 0 (featured)
        self.assertEqual(position, 0)

    def test_get_position_shared(self):
        """Test position for shared image."""
        position = self.positioning_engine.get_position(
            image_role="shared",
            vendor="Pentart"
        )

        # Shared should be appended
        self.assertEqual(position, "append")

    def test_get_action_primary(self):
        """Test action for primary image."""
        action = self.positioning_engine.get_action(image_role="primary")

        # Primary should replace and reorder
        self.assertEqual(action, "replace_and_reorder")

    def test_get_action_shared(self):
        """Test action for shared image."""
        action = self.positioning_engine.get_action(image_role="shared")

        # Shared should only append
        self.assertEqual(action, "append_only")


class TestFrameworkIntegration(unittest.TestCase):
    """Test end-to-end framework integration."""

    def setUp(self):
        """Set up test framework."""
        self.framework = ImageFramework()

    def test_pentart_galaxy_flakes_primary(self):
        """Test complete flow for Pentart Galaxy Flakes primary image."""
        product = {
            "id": "gid://shopify/Product/123",
            "title": "Galaxy Flakes 15g - Jupiter white",
            "vendor": "Pentart"
        }

        result = self.framework.process_image(
            product=product,
            image_url="https://cdn.shopify.com/image.jpg",
            image_role="primary",
            vendor="Pentart"
        )

        # Verify filename follows pattern
        self.assertTrue(result["filename"].startswith("pentart-galaxy-flakes"))
        self.assertIn("jupiter-white", result["filename"])

        # Verify German alt text
        self.assertIn("Pentart", result["alt_text"])
        self.assertIn("Jupiter white", result["alt_text"])

        # Verify transformations
        self.assertIn("convert_to_square", result["transformations"])
        self.assertEqual(result["transformations"]["format"], "png")

        # Verify upload strategy
        self.assertEqual(result["upload_strategy"], "staged")

        # Verify position
        self.assertEqual(result["position"], 0)

    def test_pentart_galaxy_flakes_shared(self):
        """Test complete flow for Pentart Galaxy Flakes shared image."""
        product = {
            "id": "gid://shopify/Product/123",
            "title": "Galaxy Flakes 15g - Jupiter white",
            "vendor": "Pentart"
        }

        result = self.framework.process_image(
            product=product,
            image_url="https://cdn.shopify.com/groupshot.jpg",
            image_role="shared",
            vendor="Pentart"
        )

        # Verify filename follows shared pattern (no variant name)
        self.assertTrue(result["filename"].startswith("pentart-galaxy-flakes"))
        self.assertNotIn("jupiter-white", result["filename"])

        # Verify position (append)
        self.assertEqual(result["position"], "append")


if __name__ == "__main__":
    unittest.main()
