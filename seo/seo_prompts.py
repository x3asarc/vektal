"""
SEO prompt templates for Gemini AI content generation.
Optimized for German e-commerce market and 2026 best practices.
"""

SYSTEM_INSTRUCTION = """Du bist ein Experte für SEO-Texterstellung, spezialisiert auf E-Commerce-Produktoptimierung nach den Best Practices von 2026. Generiere SEO-optimierte Inhalte auf Deutsch, die:

1. Meta-Titel (50-60 Zeichen max):
   - Primäres Keyword am Anfang einbeziehen
   - Einzigartig und überzeugend sein
   - Markennamen einbeziehen, wenn Platz vorhanden

2. Meta-Beschreibung (155-160 Zeichen max):
   - Wichtige Informationen vorne platzieren (Mobile-First)
   - Call-to-Action einbeziehen
   - Natürliche Keyword-Integration
   - Suchabsicht beantworten

3. Produktbeschreibung (300-500 Wörter):
   - Stichpunkte für Eigenschaften verwenden
   - FAQ-Bereich einbeziehen
   - Für AI-Parsing optimiert
   - Natürliche Sprache, nutzenorientiert
   - Spezifikationen einbeziehen

WICHTIG: Alle Inhalte müssen auf Deutsch für den deutschen Markt sein.

Gib die Antwort als JSON zurück:
{
  "meta_title": "...",
  "meta_description": "...",
  "description_html": "..."
}"""


def get_product_prompt(
    title,
    vendor,
    product_type,
    tags,
    current_description,
    current_meta_title=None,
    current_meta_description=None,
):
    """
    Generate the user prompt for SEO content generation.

    Args:
        title: Product title
        vendor: Vendor/brand name
        product_type: Product category
        tags: Product tags (list or comma-separated string)
        current_description: Existing product description HTML

    Returns:
        Formatted prompt string
    """
    # Convert tags to string if it's a list
    if isinstance(tags, list):
        tags_str = ", ".join(tags)
    else:
        tags_str = tags or "Keine Tags"

    # Clean up current description (remove excessive HTML, truncate if too long)
    clean_description = current_description or "Keine vorhandene Beschreibung"
    if len(clean_description) > 1000:
        clean_description = clean_description[:1000] + "..."

    meta_block = ""
    if current_meta_title or current_meta_description:
        meta_block = (
            f"\nAktueller Meta-Titel: {current_meta_title or 'Nicht vorhanden'}\n"
            f"Aktuelle Meta-Beschreibung: {current_meta_description or 'Nicht vorhanden'}\n"
        )

    prompt = f"""Generiere SEO-optimierte Inhalte für dieses Produkt:

Produkt: {title}
Hersteller: {vendor}
Kategorie: {product_type or 'Nicht angegeben'}
Tags: {tags_str}
Aktuelle Beschreibung: {clean_description}{meta_block}

WICHTIG: Verbessere und optimiere die vorhandene Beschreibung, ersetze sie nicht vollständig. Behalte nützliche Informationen bei und füge SEO-Optimierung hinzu.

Zusätzlicher Kontext:
- Zielgruppe: Bastel-Enthusiasten, DIY-Kreative
- Markt: Deutscher E-Commerce
- Fokus: Natürliche Sprache, keine Keyword-Stuffing

Generiere:
1. Einen prägnanten Meta-Titel (50-60 Zeichen), der das Hauptkeyword und den Markennamen enthält
2. Eine überzeugende Meta-Beschreibung (155-160 Zeichen) mit Call-to-Action
3. Eine erweiterte Produktbeschreibung (300-500 Wörter) mit:
   - Einleitungsabsatz mit Hauptvorteilen
   - Stichpunkte für wichtige Eigenschaften
   - Technische Spezifikationen
   - FAQ-Bereich (2-3 häufige Fragen)
   - HTML-Formatierung verwenden (<h2>, <ul>, <li>, <p>, <strong>)

Gib die Antwort als valides JSON zurück."""

    return prompt


def get_quick_prompt(title, vendor, current_description, current_meta_title=None, current_meta_description=None):
    """
    Simplified prompt for quick testing.

    Args:
        title: Product title
        vendor: Vendor/brand name
        current_description: Existing product description

    Returns:
        Formatted prompt string
    """
    import re

    clean_description = current_description or "Keine vorhandene Beschreibung"

    # Extract video embeds (iframes) to preserve
    video_embeds = re.findall(r'<iframe[^>]*>.*?</iframe>', clean_description, re.DOTALL | re.IGNORECASE)
    video_note = ""
    if video_embeds:
        video_note = (
            "\n\nWICHTIG: Die Beschreibung enthält eingebettete Videos. "
            f"Füge diese Videos am Ende der neuen Beschreibung ein:\n{video_embeds[0]}"
        )

    # Truncate for AI context (but keep full for video detection)
    if len(clean_description) > 500:
        clean_description = clean_description[:500] + "..."

    meta_block = ""
    if current_meta_title or current_meta_description:
        meta_block = (
            f"\nAktueller Meta-Titel: {current_meta_title or 'Nicht vorhanden'}\n"
            f"Aktuelle Meta-Beschreibung: {current_meta_description or 'Nicht vorhanden'}"
        )

    prompt = f"""Generiere SEO-optimierte Inhalte auf Deutsch für:

Produkt: {title}
Hersteller: {vendor}
Aktuelle Beschreibung: {clean_description}{video_note}{meta_block}

Erstelle:
1. Meta-Titel (50-60 Zeichen): Produkt + Hersteller, keyword-optimiert
2. Meta-Beschreibung (155-160 Zeichen): Überzeugend mit Call-to-Action
3. Produktbeschreibung (300-400 Wörter): Erweitert mit HTML-Formatierung, Stichpunkten, FAQ

WICHTIG: Falls Videos vorhanden sind, füge sie am Ende der neuen Beschreibung ein (vor dem Call-to-Action).

Antworte mit validem JSON:
{{
  "meta_title": "...",
  "meta_description": "...",
  "description_html": "..."
}}"""

    return prompt
