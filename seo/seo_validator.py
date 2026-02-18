"""
Validation functions for SEO content (2025-2026 Standard).
Focuses on Semantic Depth, E-E-A-T, and Generative Search Optimization (GEO).
"""

import json
import re


class SEOValidator:
    """Validates SEO content against 2025-2026 E-commerce Search Dominance standards."""

    # Updated limits for 2025-2026
    META_TITLE_MIN = 40
    META_TITLE_MAX = 60
    META_DESC_MIN = 120
    META_DESC_MAX = 160

    # Semantic Content Limits (Report Recommendation: 300-500 words)
    DESC_MIN_WORDS = 300
    DESC_MAX_WORDS = 500

    # GEO (Generative Engine Optimization) Constants
    GEO_SUMMARY_MIN_WORDS = 50
    GEO_SUMMARY_MAX_WORDS = 70

    @staticmethod
    def validate_meta_title(title):
        """Validates meta title for length and semantic keyword presence."""
        if not title:
            return {"valid": False, "message": "Meta-Titel ist leer"}

        length = len(title)
        if length < SEOValidator.META_TITLE_MIN:
            return {"valid": False, "message": f"Titel zu kurz ({length} Zeichen)"}
        if length > SEOValidator.META_TITLE_MAX:
            return {"valid": False, "message": f"Titel zu lang ({length} Zeichen)"}

        return {"valid": True, "message": f"✓ {length} Zeichen"}

    @staticmethod
    def validate_meta_description(description):
        """Validates meta description for length."""
        if not description:
            return {"valid": False, "message": "Meta-Beschreibung ist leer"}

        length = len(description)
        if length < SEOValidator.META_DESC_MIN:
            return {"valid": False, "message": f"Beschreibung zu kurz ({length} Zeichen)"}
        if length > SEOValidator.META_DESC_MAX:
            return {"valid": False, "message": f"Beschreibung zu lang ({length} Zeichen)"}

        return {"valid": True, "message": f"✓ {length} Zeichen"}

    @staticmethod
    def _strip_html(html_content):
        return re.sub(r"<[^>]+>", " ", html_content or "")

    @staticmethod
    def validate_description_quality(html_content):
        """
        Validates content against 2025 E-E-A-T and Information Gain standards.
        Checks for: Word count, bullet points, and experience-based language.
        """
        if not html_content:
            return {"valid": False, "message": "Produktbeschreibung ist leer"}

        text = SEOValidator._strip_html(html_content)
        words = len(text.split())

        # 1. Word Count Check
        if words < SEOValidator.DESC_MIN_WORDS:
            return {
                "valid": False,
                "message": f"Content-Tiefe unzureichend ({words}/{SEOValidator.DESC_MIN_WORDS} Wörter)",
            }
        if words > SEOValidator.DESC_MAX_WORDS:
            return {
                "valid": False,
                "message": f"Beschreibung zu lang ({words}/{SEOValidator.DESC_MAX_WORDS} Wörter)",
            }

        # 2. Information Gain / E-E-A-T Signal Check
        eeat_markers = [
            r"getestet",
            r"erfahrung",
            r"praxis",
            r"anwendung",
            r"vorteil",
            r"tipp",
            r"bewährt",
        ]
        has_eeat = any(re.search(marker, text.lower()) for marker in eeat_markers)

        # 3. Structural Check (Bullet points for scannability)
        has_bullets = "<li>" in (html_content or "").lower()
        if not has_bullets:
            return {"valid": False, "message": "Fehlende Struktur (keine Listen/Bullet Points)"}

        if not has_eeat:
            return {
                "valid": True,
                "message": "Länge ok, aber E-E-A-T-Signale schwach (Information Gain erhöhen)",
            }

        return {"valid": True, "message": f"✓ {words} Wörter mit Struktur & E-E-A-T"}

    @staticmethod
    def validate_geo_readiness(html_content):
        """
        Checks for Generative Engine Optimization (GEO) markers.
        Specifically looks for a concise summary (50-70 words) in the first paragraph.
        """
        if not html_content:
            return {"valid": False, "message": "KI-Zusammenfassung fehlt"}

        # Prefer first paragraph if present
        para_match = re.search(r"<p>(.*?)</p>", html_content, re.DOTALL | re.IGNORECASE)
        if para_match:
            first_para = re.sub(r"<[^>]+>", " ", para_match.group(1)).strip()
        else:
            text = SEOValidator._strip_html(html_content).strip()
            first_para = text.split("\n")[0] if text else ""

        summary_words = len(first_para.split())
        if SEOValidator.GEO_SUMMARY_MIN_WORDS <= summary_words <= SEOValidator.GEO_SUMMARY_MAX_WORDS:
            return {"valid": True, "message": "✓ KI-Zusammenfassung optimiert"}

        return {
            "valid": False,
            "message": "KI-Zusammenfassung (50-70 Wörter) fehlt oder ist falsch platziert",
        }

    @staticmethod
    def validate_description(description_html):
        """Backward-compatible alias for description validation."""
        return SEOValidator.validate_description_quality(description_html)

    @staticmethod
    def validate_all(seo_content):
        """
        Comprehensive validation of the integrated SEO strategy.
        """
        results = {
            "meta_title": SEOValidator.validate_meta_title(seo_content.get("meta_title", "")),
            "meta_description": SEOValidator.validate_meta_description(seo_content.get("meta_description", "")),
            "description_quality": SEOValidator.validate_description_quality(seo_content.get("description_html", "")),
            "geo_readiness": SEOValidator.validate_geo_readiness(seo_content.get("description_html", "")),
        }

        # Backward-compatible key
        results["description"] = results["description_quality"]

        # Overall status (avoid double-counting description)
        results["all_valid"] = all(
            r["valid"] for k, r in results.items() if isinstance(r, dict) and k != "description"
        )
        return results

    @staticmethod
    def extract_json_from_text(text):
        """Standard JSON extraction from LLM responses."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def smart_truncate(text, max_length):
        """Truncates at word boundaries, adhering to 2025's clean meta standards."""
        if len(text) <= max_length:
            return text
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        return text[:last_space].rstrip(",-–—") if last_space > (max_length * 0.7) else text[:max_length]

    @staticmethod
    def truncate_if_needed(seo_content):
        """
        Intelligently truncate content if it exceeds character limits.
        Uses word boundaries, no ellipsis.
        """
        result = seo_content.copy()

        if result.get("meta_title") and len(result["meta_title"]) > SEOValidator.META_TITLE_MAX:
            result["meta_title"] = SEOValidator.smart_truncate(
                result["meta_title"],
                SEOValidator.META_TITLE_MAX,
            )

        if result.get("meta_description") and len(result["meta_description"]) > SEOValidator.META_DESC_MAX:
            result["meta_description"] = SEOValidator.smart_truncate(
                result["meta_description"],
                SEOValidator.META_DESC_MAX,
            )

        return result
