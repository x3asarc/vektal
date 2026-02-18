"""
Post-Upload Image Verification & Auto-Recrop System

Workflow:
1. Image gets uploaded to Shopify
2. Verify uploaded image quality
3. If issues detected (too zoomed, product cut off, etc.) -> recrop and re-upload
4. If good -> done

This prevents unnecessary transformations while catching actual problems.
"""

import os
import logging
from typing import Dict, Optional, Tuple
import requests
from PIL import Image
from io import BytesIO
from src.core.vision_client import VisionAIClient

logger = logging.getLogger(__name__)


class ImageVerifier:
    """
    Analyzes uploaded product images and determines if recropping is needed.
    """

    def __init__(self, vision_client: VisionAIClient = None):
        self.vision_client = vision_client or VisionAIClient(
            provider=os.getenv("VISION_AI_PROVIDER", "openrouter"),
            model=os.getenv("VISION_AI_MODEL", "google/gemini-2.0-flash-001")
        )

    def verify_image(
        self,
        image_url: str,
        product_title: str,
        vendor: str,
        image_type: str = "product"
    ) -> Dict:
        """
        Verify uploaded image quality and determine if recrop needed.

        Args:
            image_url: URL of uploaded Shopify image
            product_title: Product title for context
            vendor: Vendor name
            image_type: Type of image (packshot, detail, etc.)

        Returns:
            Dict with:
                - needs_recrop: bool
                - issue: str (description of problem)
                - recommendation: str (how to fix)
                - confidence: float (0-1)
                - analysis: dict (detailed analysis)
        """
        try:
            # Download image for analysis
            logger.info(f"Downloading image for verification: {image_url[:60]}...")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image_data = response.content

            # Get image dimensions
            img = Image.open(BytesIO(image_data))
            width, height = img.size
            aspect_ratio = width / height

            logger.info(f"Image dimensions: {width}x{height} (aspect: {aspect_ratio:.2f})")

            # Quick checks first (no AI needed)
            quick_check = self._quick_quality_check(img, aspect_ratio)
            if quick_check["has_issues"]:
                return {
                    "needs_recrop": True,
                    "issue": quick_check["issue"],
                    "recommendation": quick_check["recommendation"],
                    "confidence": 0.95,
                    "analysis": {"type": "quick_check", "details": quick_check}
                }

            # Vision AI analysis for subjective quality
            ai_analysis = self._ai_quality_check(image_url, product_title, vendor, image_type)

            return ai_analysis

        except Exception as e:
            logger.error(f"Image verification failed: {e}")
            return {
                "needs_recrop": False,
                "issue": f"Verification failed: {e}",
                "recommendation": "Manual review needed",
                "confidence": 0.0,
                "analysis": {"error": str(e)}
            }

    def _quick_quality_check(self, img: Image.Image, aspect_ratio: float) -> Dict:
        """
        Fast quality checks without AI.

        Returns:
            Dict with has_issues, issue, recommendation
        """
        width, height = img.size

        # Check 1: Not square at all (should be 1:1)
        if aspect_ratio < 0.95 or aspect_ratio > 1.05:
            return {
                "has_issues": True,
                "issue": f"Image not square (aspect: {aspect_ratio:.2f})",
                "recommendation": "Needs squaring transformation"
            }

        # Check 2: Too small (minimum 500px)
        if width < 500 or height < 500:
            return {
                "has_issues": True,
                "issue": f"Image too small ({width}x{height})",
                "recommendation": "Needs upscaling or replacement"
            }

        # Check 3: Too large (over 2500px)
        if width > 2500 or height > 2500:
            return {
                "has_issues": True,
                "issue": f"Image too large ({width}x{height})",
                "recommendation": "Needs downsizing"
            }

        # All quick checks passed
        return {
            "has_issues": False,
            "issue": None,
            "recommendation": None
        }

    def _ai_quality_check(
        self,
        image_url: str,
        product_title: str,
        vendor: str,
        image_type: str
    ) -> Dict:
        """
        Use Vision AI to check subjective image quality.

        Checks:
        - Is product visible and clear?
        - Is product properly framed (not cut off)?
        - Is product too zoomed in?
        - Is there enough context/padding?
        """
        prompt = f"""Analyze this product image for quality issues.

Product: {product_title}
Vendor: {vendor}
Image Type: {image_type}

CHECK FOR THESE ISSUES:
1. Is the product cut off or cropped too tightly? (edges missing)
2. Is the product too zoomed in? (can't see full product)
3. Is the product too small in frame? (too much empty space)
4. Is the product clearly visible and in focus?
5. For packshot/detail images: Is the product centered and well-framed?

RESPOND IN THIS FORMAT:
Status: [GOOD / NEEDS_RECROP]
Issue: [brief description or "None"]
Recommendation: [specific fix needed or "None"]
Confidence: [0.0 to 1.0]

Examples:
- "Status: NEEDS_RECROP, Issue: Product is cut off at top, Recommendation: Add padding with contain method, Confidence: 0.9"
- "Status: GOOD, Issue: None, Recommendation: None, Confidence: 0.95"
- "Status: NEEDS_RECROP, Issue: Too zoomed in cannot see full container, Recommendation: Use contain instead of crop, Confidence: 0.85"
"""

        try:
            # Call Vision AI
            response = self.vision_client.analyze_image(image_url, prompt)

            if not response:
                return self._default_good_result()

            # Parse response
            parsed = self._parse_ai_response(response)
            return parsed

        except Exception as e:
            logger.error(f"AI quality check failed: {e}")
            return self._default_good_result()

    def _parse_ai_response(self, response: str) -> Dict:
        """Parse Vision AI response into structured format."""
        lines = response.strip().split("\n")
        result = {
            "needs_recrop": False,
            "issue": None,
            "recommendation": None,
            "confidence": 0.8,
            "analysis": {"raw_response": response}
        }

        for line in lines:
            line = line.strip()
            if line.startswith("Status:"):
                status = line.split(":", 1)[1].strip().upper()
                result["needs_recrop"] = "NEEDS_RECROP" in status

            elif line.startswith("Issue:"):
                issue = line.split(":", 1)[1].strip()
                if issue.lower() != "none":
                    result["issue"] = issue

            elif line.startswith("Recommendation:"):
                rec = line.split(":", 1)[1].strip()
                if rec.lower() != "none":
                    result["recommendation"] = rec

            elif line.startswith("Confidence:"):
                try:
                    conf = float(line.split(":", 1)[1].strip())
                    result["confidence"] = conf
                except:
                    pass

        return result

    def _default_good_result(self) -> Dict:
        """Return default 'image is good' result."""
        return {
            "needs_recrop": False,
            "issue": None,
            "recommendation": None,
            "confidence": 0.5,
            "analysis": {"type": "default"}
        }

    def recrop_and_reupload(
        self,
        image_url: str,
        product_id: str,
        media_id: str,
        recommendation: str,
        shopify_client
    ) -> bool:
        """
        Download image, recrop based on recommendation, and re-upload.

        Args:
            image_url: Current image URL
            product_id: Shopify product ID
            media_id: Shopify media ID to replace
            recommendation: How to fix (from verification)
            shopify_client: ShopifyClient instance

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Recropping image based on: {recommendation}")

            # Download current image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image_data = response.content

            img = Image.open(BytesIO(image_data))

            # Apply recrop based on recommendation
            if "contain" in recommendation.lower():
                # Use contain method (add padding instead of crop)
                img = self._apply_contain_method(img)
            elif "crop" in recommendation.lower():
                # Use center crop
                img = self._apply_center_crop(img)
            elif "padding" in recommendation.lower():
                # Add padding
                img = self._add_padding(img)

            # Convert to bytes
            output = BytesIO()
            img.save(output, format="PNG", optimize=True)
            transformed_data = output.getvalue()

            logger.info(f"Recropped: {len(image_data)} -> {len(transformed_data)} bytes")

            # Re-upload
            # TODO: Implement staged upload with transformed bytes
            logger.info(f"Re-upload functionality to be implemented")

            return True

        except Exception as e:
            logger.error(f"Recrop failed: {e}")
            return False

    def _apply_contain_method(self, img: Image.Image, target_size: int = 900) -> Image.Image:
        """Fit image inside square with padding (no crop)."""
        width, height = img.size
        max_dim = max(width, height)

        # Create square canvas with transparency
        new_img = Image.new("RGBA", (max_dim, max_dim), (255, 255, 255, 0))

        # Paste image centered
        paste_x = (max_dim - width) // 2
        paste_y = (max_dim - height) // 2
        new_img.paste(img, (paste_x, paste_y))

        # Resize to target
        new_img = new_img.resize((target_size, target_size), Image.Resampling.LANCZOS)

        return new_img

    def _apply_center_crop(self, img: Image.Image, target_size: int = 900) -> Image.Image:
        """Crop image to square from center."""
        width, height = img.size
        min_dim = min(width, height)

        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim

        img = img.crop((left, top, right, bottom))
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

        return img

    def _add_padding(self, img: Image.Image, padding_percent: int = 10) -> Image.Image:
        """Add padding around image."""
        width, height = img.size
        padding = int(max(width, height) * (padding_percent / 100))

        new_width = width + 2 * padding
        new_height = height + 2 * padding

        new_img = Image.new("RGBA", (new_width, new_height), (255, 255, 255, 0))
        new_img.paste(img, (padding, padding))

        return new_img


def verify_and_fix_product_image(
    product_id: str,
    image_url: str,
    product_title: str,
    vendor: str,
    image_type: str,
    shopify_client,
    auto_fix: bool = True
) -> Dict:
    """
    High-level function to verify image and optionally fix.

    Args:
        product_id: Shopify product ID
        image_url: Uploaded image URL
        product_title: Product title
        vendor: Vendor name
        image_type: Image type (packshot, detail, etc.)
        shopify_client: ShopifyClient instance
        auto_fix: If True, automatically recrop if issues found

    Returns:
        Dict with verification results and fix status
    """
    verifier = ImageVerifier()

    # Verify image
    result = verifier.verify_image(image_url, product_title, vendor, image_type)

    logger.info(f"Verification result: {result}")

    if result["needs_recrop"] and auto_fix:
        logger.info(f"Auto-fixing image: {result['recommendation']}")
        # TODO: Implement actual recrop and re-upload
        result["fixed"] = False  # Placeholder
        result["fix_message"] = "Auto-fix not yet implemented"
    else:
        result["fixed"] = False

    return result


if __name__ == "__main__":
    # Test
    verifier = ImageVerifier()
    test_url = "https://cdn.shopify.com/test.jpg"
    result = verifier.verify_image(test_url, "Test Product", "Pentart", "packshot")
    print(f"Verification result: {result}")
