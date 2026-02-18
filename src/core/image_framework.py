"""
Master Image Processing Framework
Centralizes ALL image processing rules and logic from YAML config.

This framework eliminates uncertainty by codifying:
- Image transformation rules (square, transparency, format)
- Upload strategy selection (staged vs simple)
- Positioning/ordering logic (replace vs append)
- Filename generation (hybrid AI + SEO)
- Alt text generation (German, AI-enhanced)
- Deletion safeguards (never delete without confirmation)

Usage:
    framework = ImageFramework()
    result = framework.process_image(product, image_url, image_role="primary")
    # Returns: {filename, alt_text, transformations, upload_strategy, position}
"""

import os
import re
import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, List, Any
from PIL import Image
import io
import requests

logger = logging.getLogger(__name__)


class ImageFramework:
    """
    Master framework that loads and enforces all image processing rules.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize framework with rules from YAML config.

        Args:
            config_path: Path to image_processing_rules.yaml
                        (defaults to config/image_processing_rules.yaml)
        """
        if config_path is None:
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "image_processing_rules.yaml"

        self.config_path = Path(config_path)
        self.rules = self.load_rules()
        self.processor = ImageProcessor(self.rules)
        self.naming_engine = ImageNamingEngine(self.rules)
        self.upload_strategy = ImageUploadStrategy(self.rules)
        self.positioning_engine = ImagePositioningEngine(self.rules)

    def load_rules(self) -> Dict:
        """Load rules from YAML config file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
            logger.info(f"Loaded image processing rules v{rules.get('version', 'unknown')}")
            return rules
        except Exception as e:
            logger.error(f"Failed to load image processing rules: {e}")
            raise

    def process_image(
        self,
        product: Dict,
        image_url: str,
        image_role: str = "primary",
        vendor: str = None
    ) -> Dict:
        """
        Process an image according to framework rules.

        Args:
            product: Shopify product data
            image_url: URL of image to process
            image_role: "primary" or "shared"
            vendor: Vendor name (optional, extracted from product if not provided)

        Returns:
            Dict with:
                - filename: Generated filename (hybrid naming)
                - alt_text: Generated alt text (German, AI-enhanced)
                - image_type: AI-determined type (packshot, groupshot, detail, lifestyle)
                - transformations: Dict of transformations to apply
                - upload_strategy: "staged" or "simple"
                - position: Where to position image (0 for primary, "append" for shared)
                - metadata: Additional metadata for logging/tracking
        """
        # Extract vendor
        vendor = vendor or product.get("vendor", "")

        # Step 1: Determine image type (vision AI or fallback)
        image_type = self._identify_image_type(image_url, product)

        # Step 2: Extract product context for naming
        product_context = self._extract_product_context(product, image_role)

        # Step 3: Generate filename (hybrid naming)
        filename = self.naming_engine.generate_filename(
            image_type=image_type,
            product_context=product_context,
            image_role=image_role,
            vendor=vendor
        )

        # Step 4: Generate alt text (AI-enhanced or template)
        alt_text = self.naming_engine.generate_alt_text(
            image_type=image_type,
            product_context=product_context,
            image_role=image_role,
            vendor=vendor
        )

        # Step 5: Determine transformations to apply
        transformations = self.processor.get_transformations(
            image_type=image_type,
            image_role=image_role,
            vendor=vendor
        )

        # Step 6: Determine upload strategy
        upload_method = self.upload_strategy.determine_method(
            image_role=image_role,
            vendor=vendor
        )

        # Step 7: Determine positioning
        position = self.positioning_engine.get_position(
            image_role=image_role,
            vendor=vendor
        )

        result = {
            "filename": filename,
            "alt_text": alt_text,
            "image_type": image_type,
            "transformations": transformations,
            "upload_strategy": upload_method,
            "position": position,
            "metadata": {
                "framework_version": self.rules.get("version"),
                "vendor": vendor,
                "image_role": image_role,
                "product_id": product.get("id"),
                "product_title": product.get("title")
            }
        }

        logger.info(
            f"Framework processed image: type={image_type}, role={image_role}, "
            f"filename={filename}, upload={upload_method}"
        )

        return result

    def _identify_image_type(self, image_url: str, product: Dict) -> str:
        """
        Identify image type using vision AI (or fallback to default).

        Args:
            image_url: URL of image
            product: Product data

        Returns:
            Image type: "packshot", "groupshot", "detail", or "lifestyle"
        """
        workflow = self.rules.get("workflow", {})
        step_1 = workflow.get("step_1_identify", {})

        # Check if vision AI is enabled
        vision_config = self.rules.get("vision_ai", {})
        if not vision_config.get("enabled", True):
            return step_1.get("fallback", "detail")

        # Try to use vision AI (delegated to vision_engine)
        # For now, return fallback - integration with vision_engine comes later
        # TODO: Integrate with vision_engine.py to call AI
        return step_1.get("fallback", "detail")

    def _extract_product_context(self, product: Dict, image_role: str) -> Dict:
        """
        Extract product context for filename/alt text generation.

        Args:
            product: Shopify product data
            image_role: "primary" or "shared"

        Returns:
            Dict with product_name, product_line, variant_name, etc.
        """
        title = product.get("title", "")
        vendor = product.get("vendor", "")

        # Extract product line (e.g., "Galaxy Flakes 15g" from "Galaxy Flakes 15g - Jupiter white")
        # Simple heuristic: take first part before " - " or first 3 words
        if " - " in title:
            product_line = title.split(" - ")[0].strip()
        else:
            words = title.split()[:3]
            product_line = " ".join(words)

        # Convert to slug format
        product_slug = self._slugify(product_line)

        # Extract variant name (for primary images)
        variant_name = ""
        if image_role == "primary" and " - " in title:
            variant_name = title.split(" - ", 1)[1].strip()

        variant_slug = self._slugify(variant_name) if variant_name else ""

        return {
            "product_name": title,
            "product_line": product_line,
            "product_slug": product_slug,
            "variant_name": variant_name,
            "variant_slug": variant_slug,
            "vendor": vendor,
            "role": image_role
        }

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Lowercase
        text = text.lower()
        # Replace spaces with hyphens
        text = re.sub(r'\s+', '-', text)
        # Remove special characters (keep only alphanumeric, hyphens, dots)
        text = re.sub(r'[^a-z0-9\-\.]', '', text)
        # Remove consecutive hyphens
        text = re.sub(r'-+', '-', text)
        # Strip leading/trailing hyphens
        text = text.strip('-')
        return text

    def validate_filename(self, filename: str) -> bool:
        """
        Validate filename against sanitization rules.

        Args:
            filename: Filename to validate

        Returns:
            True if valid, False otherwise
        """
        sanitization = self.rules.get("naming", {}).get("sanitization", {})

        # Check length
        max_length = sanitization.get("max_length", 100)
        if len(filename) > max_length:
            return False

        # Check allowed characters
        allowed_chars = sanitization.get("allowed_chars", "a-z0-9-_.")
        pattern = f"^[{allowed_chars}]+$"
        if not re.match(pattern, filename):
            return False

        return True


class ImageProcessor:
    """
    Handles image transformations (square conversion, transparency, format).
    """

    def __init__(self, rules: Dict):
        self.rules = rules

    def get_transformations(
        self,
        image_type: str,
        image_role: str,
        vendor: str = None
    ) -> Dict:
        """
        Get transformation rules for this image.

        Args:
            image_type: Image type (packshot, groupshot, detail, lifestyle)
            image_role: "primary" or "shared"
            vendor: Vendor name

        Returns:
            Dict of transformation rules to apply
        """
        transformation_rules = self.rules.get("transformation", {})
        always = transformation_rules.get("always", [])

        # Build transformation config
        transformations = {}

        for transform in always:
            if isinstance(transform, dict):
                for transform_type, config in transform.items():
                    transformations[transform_type] = config

        # Add format-specific rules
        formats = transformation_rules.get("formats", {})

        # Determine format based on image type and role
        if image_role == "primary" or image_type in ["packshot", "detail"]:
            format_name = "png"
        else:
            format_name = "jpg"

        format_config = formats.get(format_name, {})
        transformations["format"] = format_name
        transformations["format_config"] = format_config

        # Add dimension rules
        dimensions = transformation_rules.get("dimensions", {})
        transformations["dimensions"] = dimensions

        return transformations

    def apply_transformations(self, image_data: bytes, transformations: Dict) -> bytes:
        """
        Apply transformations to image data.

        Args:
            image_data: Raw image bytes
            transformations: Transformation rules from get_transformations()

        Returns:
            Transformed image bytes
        """
        try:
            img = Image.open(io.BytesIO(image_data))

            # Apply square conversion
            if "convert_to_square" in transformations:
                square_config = transformations["convert_to_square"]
                img = self._convert_to_square(img, square_config)

            # Ensure transparency (convert to RGBA)
            if "ensure_transparency" in transformations:
                transparency_config = transformations["ensure_transparency"]
                if transparency_config.get("convert_to_rgba", True):
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")

            # Convert format
            output_format = transformations.get("format", "png").upper()
            format_config = transformations.get("format_config", {})

            # Save to bytes
            output = io.BytesIO()

            if output_format == "PNG":
                compression = format_config.get("compression", 6)
                img.save(output, format="PNG", compress_level=compression)
            elif output_format == "JPG" or output_format == "JPEG":
                # Convert RGBA to RGB for JPEG
                if img.mode == "RGBA":
                    # Create white background
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # Use alpha as mask
                    img = background
                quality = format_config.get("quality", 95)
                img.save(output, format="JPEG", quality=quality)
            else:
                img.save(output, format=output_format)

            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to apply transformations: {e}")
            return image_data  # Return original on error

    def _convert_to_square(self, img: Image.Image, config: Dict) -> Image.Image:
        """
        Convert image to square (1:1 aspect ratio).

        Args:
            img: PIL Image
            config: Square conversion config

        Returns:
            Square PIL Image
        """
        method = config.get("method", "center_crop")
        target_size = config.get("target_size", 900)

        width, height = img.size

        if width == height:
            # Already square, just resize
            return img.resize((target_size, target_size), Image.Resampling.LANCZOS)

        if method == "center_crop":
            # Crop to square from center
            min_dim = min(width, height)
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            right = left + min_dim
            bottom = top + min_dim
            img = img.crop((left, top, right, bottom))
            return img.resize((target_size, target_size), Image.Resampling.LANCZOS)

        elif method == "contain":
            # Fit inside square with padding
            max_dim = max(width, height)
            new_img = Image.new("RGBA", (max_dim, max_dim), (255, 255, 255, 0))
            paste_x = (max_dim - width) // 2
            paste_y = (max_dim - height) // 2
            new_img.paste(img, (paste_x, paste_y))
            return new_img.resize((target_size, target_size), Image.Resampling.LANCZOS)

        elif method == "cover":
            # Cover entire square (crop excess)
            max_dim = max(width, height)
            scale = max_dim / min(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Center crop to square
            left = (new_width - max_dim) // 2
            top = (new_height - max_dim) // 2
            img = img.crop((left, top, left + max_dim, top + max_dim))
            return img.resize((target_size, target_size), Image.Resampling.LANCZOS)

        return img


class ImageNamingEngine:
    """
    Generates filenames and alt text using hybrid naming (AI + SEO).
    """

    def __init__(self, rules: Dict):
        self.rules = rules

    def generate_filename(
        self,
        image_type: str,
        product_context: Dict,
        image_role: str,
        vendor: str
    ) -> str:
        """
        Generate filename using hybrid naming rules.

        Args:
            image_type: AI-determined type (packshot, groupshot, detail, lifestyle)
            product_context: Product context dict
            image_role: "primary" or "shared"
            vendor: Vendor name

        Returns:
            Generated filename
        """
        naming_rules = self.rules.get("naming", {})

        if image_role == "primary":
            pattern = naming_rules.get("primary", {}).get("pattern", "{vendor}-{product_line}-{variant_name}.{ext}")
        else:
            pattern = naming_rules.get("shared", {}).get("pattern", "{vendor}-{product_line}-{image_type}.{ext}")

        # Determine extension based on image type
        if image_role == "primary" or image_type in ["packshot", "detail"]:
            ext = "png"
        else:
            ext = "jpg"

        # Build filename
        filename = pattern.format(
            vendor=vendor.lower(),
            product_line=product_context.get("product_slug", ""),
            variant_name=product_context.get("variant_slug", ""),
            image_type=image_type,
            ext=ext
        )

        # Sanitize
        filename = self._sanitize_filename(filename)

        return filename

    def generate_alt_text(
        self,
        image_type: str,
        product_context: Dict,
        image_role: str,
        vendor: str
    ) -> str:
        """
        Generate alt text using hybrid naming rules.

        Args:
            image_type: AI-determined type
            product_context: Product context dict
            image_role: "primary" or "shared"
            vendor: Vendor name

        Returns:
            Generated alt text (German)
        """
        alt_text_rules = self.rules.get("alt_text", {})
        naming_rules = self.rules.get("naming", {})

        # Get German translation of image type
        image_types = naming_rules.get("image_types", {})
        image_type_german = image_types.get(image_type, {}).get("german", "Detailansicht")

        if image_role == "primary":
            template = alt_text_rules.get("primary_template", "{product_name} - {variant_name} - {image_type_german} - {vendor}")
            alt_text = template.format(
                product_name=product_context.get("product_line", ""),
                variant_name=product_context.get("variant_name", ""),
                image_type_german=image_type_german,
                vendor=vendor
            )
        else:
            template = alt_text_rules.get("shared_template", "{product_line} von {vendor} - {image_type_german}")
            alt_text = template.format(
                product_line=product_context.get("product_line", ""),
                vendor=vendor,
                image_type_german=image_type_german
            )

        # Validate length
        max_length = alt_text_rules.get("max_length", 125)
        if len(alt_text) > max_length:
            alt_text = alt_text[:max_length - 3] + "..."

        return alt_text

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename according to rules."""
        sanitization = self.rules.get("naming", {}).get("sanitization", {})

        # Lowercase
        if sanitization.get("lowercase", True):
            filename = filename.lower()

        # Replace spaces with hyphens FIRST (before removing special chars)
        replace_spaces = sanitization.get("replace_spaces", "-")
        filename = filename.replace(" ", replace_spaces)

        # Split filename and extension to preserve extension
        name_parts = filename.rsplit(".", 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            ext = "." + ext
        else:
            name = filename
            ext = ""

        # Remove special characters from name (keep only allowed)
        allowed_chars = sanitization.get("allowed_chars", "a-z0-9-_.")
        # Build regex character class (hyphen must be first or last to be literal)
        # Format: [a-z0-9_.-] where hyphen is last
        pattern = r"[^a-z0-9_.\-]"
        name = re.sub(pattern, "", name)

        # Remove consecutive hyphens/underscores
        name = re.sub(r'[-_]+', '-', name)
        name = name.strip('-_')

        # Recombine with extension
        filename = name + ext

        # Check max length
        max_length = sanitization.get("max_length", 100)
        if len(filename) > max_length:
            # Preserve extension
            name = name[:max_length - len(ext)]
            filename = name + ext

        return filename


class ImageUploadStrategy:
    """
    Determines upload method (staged vs simple).
    """

    def __init__(self, rules: Dict):
        self.rules = rules

    def determine_method(self, image_role: str, vendor: str = None) -> str:
        """
        Determine upload method based on rules.

        Args:
            image_role: "primary" or "shared"
            vendor: Vendor name

        Returns:
            "staged" or "simple"
        """
        upload_rules = self.rules.get("upload", {})

        # Check staged upload conditions
        staged_config = upload_rules.get("staged_uploads", {})
        use_when = staged_config.get("use_when", {})

        # Handle both dict and list formats
        if isinstance(use_when, list):
            # List format from YAML (convert to dict)
            use_when_dict = {}
            for item in use_when:
                if isinstance(item, dict):
                    use_when_dict.update(item)
            use_when = use_when_dict

        # Always use staged uploads for exact filename control
        if use_when.get("need_exact_filename", True):
            return "staged"

        # Use staged for replacing primary
        if image_role == "primary" and use_when.get("replacing_primary", True):
            return "staged"

        return "simple"


class ImagePositioningEngine:
    """
    Handles image positioning and ordering logic.
    """

    def __init__(self, rules: Dict):
        self.rules = rules

    def get_position(self, image_role: str, vendor: str = None) -> Any:
        """
        Get position for image based on role.

        Args:
            image_role: "primary" or "shared"
            vendor: Vendor name

        Returns:
            Position (0 for primary, "append" for shared)
        """
        positioning_rules = self.rules.get("positioning", {})

        if image_role == "primary":
            return positioning_rules.get("primary", {}).get("position", 0)
        else:
            return positioning_rules.get("shared", {}).get("position", "append")

    def get_action(self, image_role: str) -> str:
        """
        Get positioning action (replace_and_reorder, append_only, etc.).

        Args:
            image_role: "primary" or "shared"

        Returns:
            Action string
        """
        positioning_rules = self.rules.get("positioning", {})

        if image_role == "primary":
            return positioning_rules.get("primary", {}).get("action", "replace_and_reorder")
        else:
            return positioning_rules.get("shared", {}).get("action", "append_only")


def get_framework() -> ImageFramework:
    """
    Get singleton instance of ImageFramework.
    """
    if not hasattr(get_framework, "_instance"):
        get_framework._instance = ImageFramework()
    return get_framework._instance


if __name__ == "__main__":
    # Test the framework
    framework = ImageFramework()
    print(f"Framework loaded: version {framework.rules.get('version')}")
    print(f"Vision AI enabled: {framework.rules.get('vision_ai', {}).get('enabled')}")
    print(f"Default image format: {framework.rules.get('defaults', {}).get('image_format')}")
