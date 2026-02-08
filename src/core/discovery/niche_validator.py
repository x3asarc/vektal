"""
Niche Validation

Validates vendor niche compatibility with store niche.
CRITICAL for preventing wrong vendor matches (e.g., car parts for craft store).
"""

from dataclasses import dataclass
from typing import Optional
import re


# Niche definitions with keywords for detection and validation
NICHE_DEFINITIONS = {
    "arts_and_crafts": {
        "display_name": "Arts & Crafts",
        "keywords": [
            "craft", "crafts", "crafting", "basteln", "bastel",
            "decoupage", "scrapbook", "scrapbooking",
            "paper", "papier", "rice paper", "reispapier",
            "napkin", "serviette", "servietten",
            "paint", "farbe", "acrylic", "acryl",
            "stencil", "schablone", "stamp", "stempel",
            "brush", "pinsel", "canvas", "leinwand",
            "diy", "handmade", "handgemacht", "hobby",
            "art supplies", "kunstbedarf"
        ],
        "related": ["home_garden"],  # Somewhat compatible
        "incompatible": ["automotive", "electronics"]
    },
    "automotive": {
        "display_name": "Automotive",
        "keywords": [
            "car", "auto", "vehicle", "fahrzeug",
            "motor", "engine", "brake", "bremse",
            "oil", "oel", "filter", "tire", "reifen",
            "wheel", "rad", "battery", "batterie",
            "exhaust", "auspuff", "spark plug", "zuendkerze",
            "parts", "teile", "ersatzteile"
        ],
        "related": [],
        "incompatible": ["arts_and_crafts", "fashion", "food_beverage"]
    },
    "electronics": {
        "display_name": "Electronics",
        "keywords": [
            "electronic", "elektronik", "circuit", "schaltkreis",
            "resistor", "widerstand", "capacitor", "kondensator",
            "led", "arduino", "raspberry", "sensor",
            "component", "bauteil", "pcb", "chip",
            "wire", "kabel", "solder", "loeten"
        ],
        "related": [],
        "incompatible": ["arts_and_crafts", "fashion", "food_beverage"]
    },
    "fashion": {
        "display_name": "Fashion",
        "keywords": [
            "clothing", "kleidung", "dress", "kleid",
            "shirt", "hemd", "pants", "hose",
            "shoes", "schuhe", "accessory", "accessoire",
            "jewelry", "schmuck", "necklace", "kette",
            "ring", "bracelet", "armband", "fashion", "mode"
        ],
        "related": ["home_garden"],
        "incompatible": ["automotive", "electronics"]
    },
    "home_garden": {
        "display_name": "Home & Garden",
        "keywords": [
            "furniture", "moebel", "decor", "deko",
            "garden", "garten", "plant", "pflanze",
            "pot", "topf", "tool", "werkzeug",
            "kitchen", "kueche", "bathroom", "bad",
            "bedroom", "schlafzimmer", "living", "wohnen"
        ],
        "related": ["arts_and_crafts", "fashion"],
        "incompatible": ["automotive", "electronics"]
    },
    "food_beverage": {
        "display_name": "Food & Beverage",
        "keywords": [
            "food", "lebensmittel", "beverage", "getraenk",
            "snack", "drink", "essen", "trinken",
            "organic", "bio", "natural", "natuerlich"
        ],
        "related": [],
        "incompatible": ["automotive", "electronics"]
    }
}


@dataclass
class NicheValidationResult:
    """Result of niche validation."""
    is_compatible: bool
    store_niche: str
    detected_niche: Optional[str]
    confidence_modifier: float  # 1.0 = no change, 0.5 = penalty, 0.0 = reject
    message: str
    matched_keywords: list[str]


def get_niche_keywords(niche: str) -> list[str]:
    """Get keywords for a niche."""
    definition = NICHE_DEFINITIONS.get(niche, {})
    return definition.get("keywords", [])


def get_niche_display_name(niche: str) -> str:
    """Get display name for a niche."""
    definition = NICHE_DEFINITIONS.get(niche, {})
    return definition.get("display_name", niche.replace("_", " ").title())


def detect_niche_from_text(text: str) -> tuple[Optional[str], float, list[str]]:
    """
    Detect niche from text content.

    Args:
        text: Text to analyze (title, description, etc.)

    Returns:
        Tuple of (niche, confidence, matched_keywords)
    """
    text_lower = text.lower()

    niche_scores = {}
    niche_matches = {}

    for niche, definition in NICHE_DEFINITIONS.items():
        matches = []
        for keyword in definition["keywords"]:
            if keyword in text_lower:
                matches.append(keyword)

        if matches:
            niche_scores[niche] = len(matches)
            niche_matches[niche] = matches

    if not niche_scores:
        return None, 0.0, []

    best_niche = max(niche_scores, key=niche_scores.get)
    total = sum(niche_scores.values())
    confidence = niche_scores[best_niche] / total if total > 0 else 0

    return best_niche, round(confidence, 2), niche_matches.get(best_niche, [])


def validate_niche_match(
    store_niche: str,
    vendor_niche: Optional[str] = None,
    vendor_text: str = "",
    strict_mode: bool = True
) -> NicheValidationResult:
    """
    Validate if vendor niche is compatible with store niche.

    Args:
        store_niche: Store's primary niche
        vendor_niche: Vendor's declared niche (if known)
        vendor_text: Text to analyze if vendor_niche not provided
        strict_mode: If True, incompatible niches get confidence=0

    Returns:
        NicheValidationResult with compatibility assessment
    """
    store_def = NICHE_DEFINITIONS.get(store_niche, {})

    # Detect vendor niche if not provided
    if not vendor_niche and vendor_text:
        vendor_niche, _, matched = detect_niche_from_text(vendor_text)
    else:
        matched = []

    # If we couldn't detect vendor niche, be cautious
    if not vendor_niche:
        return NicheValidationResult(
            is_compatible=True,  # Allow but flag
            store_niche=store_niche,
            detected_niche=None,
            confidence_modifier=0.7,  # 30% penalty for unknown niche
            message="Could not determine vendor niche - proceeding with caution",
            matched_keywords=[]
        )

    # Same niche - perfect match
    if vendor_niche == store_niche:
        return NicheValidationResult(
            is_compatible=True,
            store_niche=store_niche,
            detected_niche=vendor_niche,
            confidence_modifier=1.0,
            message=f"Niche match: {get_niche_display_name(vendor_niche)}",
            matched_keywords=matched
        )

    # Check if niches are related
    related = store_def.get("related", [])
    if vendor_niche in related:
        return NicheValidationResult(
            is_compatible=True,
            store_niche=store_niche,
            detected_niche=vendor_niche,
            confidence_modifier=0.9,  # 10% penalty for related
            message=f"Related niche: {get_niche_display_name(vendor_niche)}",
            matched_keywords=matched
        )

    # Check if niches are incompatible
    incompatible = store_def.get("incompatible", [])
    if vendor_niche in incompatible:
        if strict_mode:
            return NicheValidationResult(
                is_compatible=False,
                store_niche=store_niche,
                detected_niche=vendor_niche,
                confidence_modifier=0.0,  # Reject
                message=(
                    f"NICHE MISMATCH: {get_niche_display_name(vendor_niche)} "
                    f"is incompatible with {get_niche_display_name(store_niche)} store"
                ),
                matched_keywords=matched
            )
        else:
            return NicheValidationResult(
                is_compatible=False,
                store_niche=store_niche,
                detected_niche=vendor_niche,
                confidence_modifier=0.2,  # 80% penalty in flexible mode
                message=(
                    f"Niche mismatch: {get_niche_display_name(vendor_niche)} "
                    f"(requires confirmation)"
                ),
                matched_keywords=matched
            )

    # Different but not explicitly related or incompatible
    return NicheValidationResult(
        is_compatible=True,
        store_niche=store_niche,
        detected_niche=vendor_niche,
        confidence_modifier=0.8,  # 20% penalty
        message=f"Different niche: {get_niche_display_name(vendor_niche)}",
        matched_keywords=matched
    )
