"""
Configuration for Product Enrichment Pipeline

Constants and thresholds for attribute extraction, quality scoring,
and AI-driven description generation. German-first design.
"""

# New fields added by enrichment pipeline
ENRICHED_FIELDS = [
    'extracted_color',
    'extracted_size',
    'extracted_unit',
    'extracted_material',
    'inferred_category',
    'extracted_use_cases',
    'family_id',
    'enrichment_status',  # 'original', 'enriched', 'ai_generated'
    'data_quality_score'
]

# Quality thresholds for product data scoring
QUALITY_THRESHOLDS = {
    'min_description_length': 20,
    'min_description_coverage': 0.85,  # 85% of products need descriptions
    'min_color_coverage': 0.60,
    'min_category_coverage': 0.75,
    'min_overall_score': 70
}

# Color normalization map (German and English variations)
COLOR_MAP = {
    # White
    'weiss': 'Weiß', 'weis': 'Weiß', 'white': 'Weiß',

    # Black
    'schwarz': 'Schwarz', 'black': 'Schwarz',

    # Red
    'rot': 'Rot', 'red': 'Rot', 'ruby': 'Ruby Rot',

    # Blue
    'blau': 'Blau', 'blue': 'Blau', 'saphir': 'Saphir Blau',

    # Green
    'grun': 'Grün', 'grün': 'Grün', 'green': 'Grün', 'jade': 'Jade Grün',

    # Yellow
    'gelb': 'Gelb', 'yellow': 'Gelb', 'gold': 'Gold',

    # Silver
    'silber': 'Silber', 'silver': 'Silber',

    # Bronze/Copper
    'bronze': 'Bronze', 'kupfer': 'Kupfer',

    # Pink
    'rosa': 'Rosa', 'pink': 'Rosa',

    # Purple
    'lila': 'Lila', 'violett': 'Violett', 'purple': 'Lila',

    # Brown
    'braun': 'Braun', 'brown': 'Braun',

    # Gray
    'grau': 'Grau', 'grey': 'Grau', 'gray': 'Grau',

    # Orange/Turquoise
    'orange': 'Orange', 'türkis': 'Türkis', 'turquoise': 'Türkis',

    # Beige/Cream/Transparent
    'beige': 'Beige', 'creme': 'Creme', 'transparent': 'Transparent'
}

# Category detection keywords (German craft supply categories)
CATEGORY_KEYWORDS = {
    'Farbe': ['farbe', 'acryl', 'öl', 'aquarell', 'pigment', 'tinte', 'lack', 'grundierung', 'resin tint', 'malfarbe'],
    'Kleber': ['kleber', 'leim', 'bond', 'haftung', 'fixierung', 'klebstoff'],
    'Folie': ['folie', 'dekorfolie', 'transferfolie', 'mylar', 'goldfolie', 'silberfolie'],
    'Papier': ['papier', 'karton', 'pappe', 'cardstock', 'serviette', 'motivserviette'],
    'Werkzeug': ['pinsel', 'spachtel', 'messer', 'schere', 'werkzeug', 'pinselset'],
    'Verzierung': ['strass', 'perlen', 'borte', 'bänder', 'applikation', 'glitter', 'pailletten'],
    'Harz': ['harz', 'epoxid', 'epoxy', 'resin', 'giessharz', 'giessen'],
    'Stempel': ['stempel', 'stempelkissen', 'stempelfarbe'],
    'Schablone': ['schablone', 'template', 'mask']
}

# Use case detection patterns
USE_CASE_PATTERNS = {
    'Decoupage': ['serviette', 'decoupage', 'serviettentechnik', 'transfer'],
    'Schmuckherstellung': ['schmuck', 'jewelry', 'anhänger', 'kette', 'ohrring', 'armband'],
    'Resin-Art': ['harz', 'epoxid', 'resin', 'giessen', 'casting'],
    'Textilgestaltung': ['textil', 'stoff', 'kleidung', 't-shirt', 'stoffmalerei'],
    'Mixed Media': ['mixed media', 'collage', 'assemblage'],
    'Kartenherstellung': ['karte', 'cardmaking', 'einladung', 'grußkarte'],
    'Scrapbooking': ['scrapbook', 'album', 'fotoalbum', 'erinnerungsalbum']
}
