# Product Enrichment Module

AI-powered product enrichment pipeline for transforming raw scraped product data into high-quality, SEO-optimized catalog entries.

## Overview

The enrichment module takes raw product data (title, description, vendor) and enriches it with:

- **Extracted Attributes**: Colors, sizes, materials, categories (German/English)
- **AI-Generated Content**: Product descriptions via OpenRouter API
- **SEO Optimization**: Meta titles, descriptions, URL handles with German umlaut support
- **Vector Embeddings**: 768-dimensional embeddings for semantic search
- **Quality Scoring**: 0-100 quality scores based on completeness
- **Family Grouping**: Variant detection (same product, different sizes/colors)
- **Vendor Integration**: Vendor-specific rules from YAML configuration

## Architecture

```
src/core/enrichment/
├── __init__.py                 # Module exports
├── config.py                   # Constants (COLOR_MAP, QUALITY_THRESHOLDS)
├── pipeline.py                 # Main EnrichmentPipeline orchestrator
├── vendor_integration.py       # Vendor YAML config integration
│
├── extractors/                 # Attribute extraction
│   ├── attributes.py           # AttributeExtractor (color, size, material)
│   └── __init__.py
│
├── generators/                 # Content generation
│   ├── descriptions.py         # AIDescriptionGenerator (OpenRouter)
│   ├── seo.py                  # SEOGenerator (meta content, URL handles)
│   └── __init__.py
│
├── families/                   # Product family grouping
│   ├── grouper.py              # ProductFamilyGrouper
│   └── __init__.py
│
├── quality/                    # Quality validation
│   ├── scorer.py               # QualityScorer, QualityGate
│   └── __init__.py
│
├── embeddings/                 # Vector embeddings
│   ├── generator.py            # EmbeddingGenerator (sentence-transformers)
│   └── __init__.py
│
└── templating/                 # Content templating
    ├── engine.py               # TemplateEngine (Jinja2)
    └── __init__.py
```

## Installation

### Required Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `sentence-transformers>=2.0.0` - Embedding generation
- `jinja2>=3.0.0` - Content templating
- `scikit-learn>=1.0.0` - TF-IDF, cosine similarity
- `cachetools>=5.0.0` - API response caching
- `tenacity>=8.0.0` - Retry logic for API calls
- `pyyaml>=6.0` - Vendor config loading

### Optional Dependencies

For AI description generation:
- OpenRouter API key (set `OPENROUTER_API_KEY` environment variable)
- Model: `google/gemini-flash-1.5` (~$0.03 per 1,000 products)

## Quick Start

### Basic Usage

```python
from src.core.enrichment import EnrichmentPipeline

# Initialize pipeline
pipeline = EnrichmentPipeline(
    openrouter_api_key="your-key-here",  # Optional
    openrouter_model="google/gemini-flash-1.5"
)

# Raw product data from scraper
products = [
    {
        'title': 'Pentart Acrylfarbe Jade 20ml',
        'description': 'Hochwertige Acrylfarbe',
        'vendor': 'Pentart'
    }
]

# Run enrichment
enriched_products, quality_report = pipeline.run(products)

# Check results
print(f"Quality score: {enriched_products[0]['data_quality_score']}/100")
print(f"Extracted color: {enriched_products[0]['extracted_color']}")
print(f"Family ID: {enriched_products[0]['family_id']}")
```

### With Vendor Configuration

```python
# Load vendor-specific enrichment rules
enriched_products, report = pipeline.run(
    products,
    vendor_slug="pentart"  # Auto-loads config/vendors/pentart.yaml
)
```

### Partial Re-runs (Skip Steps)

```python
# Skip expensive operations
enriched_products, report = pipeline.run(
    products,
    skip_ai=True,           # Skip AI description generation
    skip_embeddings=True,   # Skip embedding generation
    skip_quality_gate=True  # Skip quality validation
)
```

## Pipeline Workflow

The enrichment pipeline runs 7 steps sequentially:

### Step 1: Attribute Extraction

Extracts structured attributes from product text:

```python
from src.core.enrichment.extractors import AttributeExtractor

extractor = AttributeExtractor()
attrs = extractor.extract_all(
    title="Pentart Acrylfarbe Jade 20ml",
    description="Hochwertige Acrylfarbe für Decoupage"
)

# Returns:
# {
#   'extracted_color': 'Jade Grün',
#   'extracted_size': '20',
#   'extracted_unit': 'ml',
#   'extracted_material': 'Acryl',
#   'inferred_category': 'Farbe'
# }
```

**Supports:**
- **Colors**: 38 German/English variants (rot→Rot, jade→Jade Grün)
- **Sizes**: ml, g, kg, cm, mm, A4, A3 formats
- **Materials**: Acryl, Textil, Harz, Papier, etc.
- **Categories**: 9 categories (Farbe, Papier, Kleber, etc.)

### Step 2: Vendor Rules

Applies vendor-specific enrichment from YAML config:

```yaml
# config/vendors/pentart.yaml
enrichment:
  tagging:
    always_add:
      - "vendor:Pentart"
      - "quality:premium"
    conditional:
      - condition: "title contains 'Acryl'"
        add_tags:
          - "type:acrylic-paint"
```

### Step 3: AI Description Generation

Generates German descriptions for low-quality products:

```python
from src.core.enrichment.generators import AIDescriptionGenerator

generator = AIDescriptionGenerator(
    api_key="your-openrouter-key",
    model="google/gemini-flash-1.5"
)

description = generator.generate_description(
    product={'title': 'Pentart Jade 20ml', 'vendor': 'Pentart'},
    examples=[]  # Finds similar products automatically
)
```

**Features:**
- Few-shot learning from similar products
- 30-day TTL cache (10,000 entries)
- Exponential backoff retry (3 attempts)
- Cost: ~$0.03 per 1,000 products

### Step 4: Product Families

Groups variants by normalized title:

```python
from src.core.enrichment.families import ProductFamilyGrouper

grouper = ProductFamilyGrouper()
products = [
    {'title': 'Pentart Acrylfarbe Jade 20ml'},
    {'title': 'Pentart Acrylfarbe Jade 50ml'}
]

grouped = grouper.create_families(products)

# Both products get same family_id
# First product marked as is_base_variant=True
```

### Step 5: Vector Embeddings

Generates 768-dimensional embeddings for semantic search:

```python
from src.core.enrichment.embeddings import EmbeddingGenerator

generator = EmbeddingGenerator()
embedding = generator.generate_embedding({
    'title': 'Pentart Acrylfarbe Jade 20ml',
    'description': 'Hochwertige Farbe',
    'tags': 'decoupage,craft'
})

# Returns: numpy array with shape (768,)
```

**Field Weighting:**
- Title: 2x (most important)
- Description: 1x
- Tags: 1.5x

### Step 6: Quality Scoring

Calculates 0-100 quality score:

```python
from src.core.enrichment.quality import QualityScorer

scorer = QualityScorer()
score = scorer.calculate_score({
    'description': 'High-quality paint for decoupage...',  # 40 pts
    'extracted_color': 'Jade Grün',                        # 10 pts
    'extracted_size': '20ml',                              # 10 pts
    'extracted_material': 'Acryl',                         # 10 pts
    'inferred_category': 'Farbe',                          # 10 pts
    'product_type': 'Paint',                               # 10 pts
    'tags': 'decoupage,craft'                              # 10 pts
})

# Returns: 90 (high quality)
```

### Step 7: Quality Gate

Validates batch quality before proceeding:

```python
from src.core.enrichment.quality import QualityGate

gate = QualityGate()
passed, report = gate.validate(enriched_products)

if not passed:
    print(f"Quality gate failed:")
    print(f"  Description coverage: {report['description_coverage']}%")
    print(f"  Color coverage: {report['color_coverage']}%")
```

**Thresholds:**
- Description coverage: ≥85%
- Color coverage: ≥60%
- Category coverage: ≥75%
- Family assignment: 100%
- SKU uniqueness: 100%

## SEO Generation

### Meta Content

```python
from src.core.enrichment.generators import SEOGenerator

seo = SEOGenerator(store_name="Bastelschachtel")

# Meta title (≤60 chars)
title = seo.generate_meta_title(
    product_name="Pentart Acrylfarbe Jade",
    size="20ml"
)
# "Pentart Acrylfarbe Jade 20ml | Bastelschachtel"

# Meta description (120-160 chars)
desc = seo.generate_meta_description(
    product_name="Pentart Acrylfarbe Jade",
    vendor="Pentart",
    key_feature="Hochwertige Acrylfarbe",
    size="20ml"
)

# URL handle (German umlaut transliteration)
handle = seo.generate_url_handle("Pentart Acrylfarbe Grün 20ml")
# "pentart-acrylfarbe-gruen-20ml"
```

### German Umlaut Transliteration

| Input | Output |
|-------|--------|
| ä | ae |
| ö | oe |
| ü | ue |
| ß | ss |

Stop words removed: `der`, `die`, `das`, `und`, `für`, `mit`, `von`

## Content Templating

### Jinja2 Templates

```python
from src.core.enrichment.templating import TemplateEngine

engine = TemplateEngine()

# Render template with product context
result = engine.render(
    template_str="{vendor} - {product_name} {size}",
    context={
        'vendor': 'Pentart',
        'product_name': 'Acrylfarbe Jade',
        'size': '20ml'
    }
)
# "Pentart - Acrylfarbe Jade 20ml"
```

### Custom German Filters

```jinja2
{{ product_name | german_capitalize }}
{{ url_text | umlaut_safe }}
{{ long_description | truncate_german(160) }}
```

## Vendor Integration

### Loading Vendor Config

```python
from src.core.enrichment.vendor_integration import VendorEnrichmentConfig

config = VendorEnrichmentConfig(vendor_slug="pentart")

# Apply all vendor rules
enriched = config.enrich_product({
    'title': 'Pentart Acrylfarbe Jade 20ml',
    'tags': 'existing,tags'
})

# Auto-tags applied, product_type set, vendor_keywords added
```

### YAML Structure

```yaml
enrichment:
  keywords:
    primary: [decoupage, mixed-media]
    secondary: [craft, DIY]

  tagging:
    always_add:
      - "vendor:Pentart"
    conditional:
      - condition: "title contains 'Acryl'"
        add_tags: ["type:acrylic"]

  categories:
    default: "Craft Supplies"
    product_type_rules:
      - match: "acrylfarbe"
        product_type: "Farbe"
```

## Configuration

### Environment Variables

```bash
# Required for AI generation
export OPENROUTER_API_KEY="your-key-here"

# Optional: Override model
export OPENROUTER_MODEL="google/gemini-flash-1.5"
```

### Quality Thresholds

Edit `src/core/enrichment/config.py`:

```python
QUALITY_THRESHOLDS = {
    'min_description_length': 20,
    'min_description_coverage': 0.85,  # 85%
    'min_color_coverage': 0.60,        # 60%
    'min_category_coverage': 0.75,     # 75%
    'min_overall_score': 70
}
```

### Color Map

Add custom colors to `COLOR_MAP`:

```python
COLOR_MAP = {
    'rot': 'Rot',
    'jade': 'Jade Grün',
    # Add your colors here
}
```

## Checkpointing & Resumability

The pipeline saves checkpoints after each step:

```python
# Run pipeline (saves checkpoints)
pipeline.run(products)

# Resume from checkpoint
products = pipeline.load_checkpoint('extraction')
```

**Checkpoint locations:** `data/enrichment_checkpoints/`

**Available checkpoints:**
- `checkpoint_extraction.json` - After attribute extraction
- `checkpoint_vendor_rules.json` - After vendor rules
- `checkpoint_templates.json` - After template application
- `checkpoint_ai.json` - After AI generation
- `checkpoint_families.json` - After family grouping
- `checkpoint_embeddings.json` - After embedding generation

## Testing

### Run All Tests

```bash
# Unit tests (fast)
pytest tests/unit/ -v

# Integration tests (includes model loading)
pytest tests/integration/ -v

# Specific test files
pytest tests/unit/test_attribute_extraction.py -v
pytest tests/integration/test_enrichment_pipeline.py -v
```

### Test Coverage

| Component | Tests | Coverage |
|-----------|-------|----------|
| Attribute Extraction | 34 | Colors, sizes, materials, categories |
| AI Descriptions & SEO | 27 | Caching, similarity, URL handles |
| Product Families | 21 | Grouping, base variants, quality scoring |
| Embeddings | 15 | Dimensions, weighting, similarity |
| Vendor Integration | 12 | YAML loading, auto-tags, mapping |
| Pipeline Integration | 10 | Full workflow, checkpoints, skip flags |
| **Total** | **119** | **All passing** |

## Performance

### Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Attribute extraction | ~5ms/product | No API calls |
| AI generation | ~300ms/product | OpenRouter API, cached |
| Embedding generation | ~50ms/product | Batch 32, sentence-transformers |
| SEO generation | ~2ms/product | Pure computation |
| Full pipeline (100 products) | ~8 seconds | Skip AI: 2 seconds |

### Optimization Tips

1. **Skip AI for high-quality products** - Check quality score first
2. **Batch embedding generation** - Use `batch_size=32` (default)
3. **Enable caching** - 30-day TTL cache for AI responses
4. **Pre-filter products** - Remove duplicates before enrichment
5. **Use checkpoints** - Resume failed runs from last step

## API Reference

### EnrichmentPipeline

```python
EnrichmentPipeline(
    openrouter_api_key: str = None,
    openrouter_model: str = "google/gemini-flash-1.5",
    checkpoint_dir: str = "data/enrichment_checkpoints"
)
```

**Methods:**
- `run(products, vendor_config, skip_*, force)` - Run enrichment pipeline
- `load_checkpoint(step_name)` - Load products from checkpoint
- `_step_extract_attributes(products)` - Step 1
- `_step_apply_vendor_rules(products)` - Step 1.5
- `_step_apply_templates(products, vendor_config)` - Step 2
- `_step_ai_generation(products, max_products)` - Step 3
- `_step_create_families(products)` - Step 4
- `_step_generate_embeddings(products)` - Step 5
- `_step_calculate_scores(products)` - Step 6
- `_step_quality_gate(products, force)` - Step 7

### AttributeExtractor

```python
AttributeExtractor()
```

**Methods:**
- `extract_from_title(title: str) -> dict` - Extract from title
- `extract_from_description(description: str) -> dict` - Extract from description
- `extract_all(title: str, description: str) -> dict` - Extract all attributes

### AIDescriptionGenerator

```python
AIDescriptionGenerator(
    api_key: str = None,
    model: str = "google/gemini-flash-1.5",
    site_name: str = "Bastelschachtel"
)
```

**Methods:**
- `generate_description(product: dict, examples: list) -> str`
- `generate_batch(products: list, catalog_embeddings, catalog_data) -> list`
- `find_similar_products(target_embedding, catalog_embeddings, catalog_data, top_k=3) -> list`

### SEOGenerator

```python
SEOGenerator(store_name: str = "Bastelschachtel")
```

**Methods:**
- `generate_meta_title(product_name, size, vendor, max_length=60) -> str`
- `generate_meta_description(product_name, vendor, key_feature, size, min_length=120, max_length=160) -> str`
- `generate_url_handle(product_name, size, vendor, max_length=80) -> str`
- `generate_image_alt_text(product_type, motif, size, vendor, max_length=125) -> str`

### ProductFamilyGrouper

```python
ProductFamilyGrouper()
```

**Methods:**
- `create_families(products: list) -> list` - Group variants into families
- `get_family_summary(family_id: str) -> dict` - Get family details

### QualityScorer & QualityGate

```python
QualityScorer()
QualityGate()
```

**Methods:**
- `calculate_score(product: dict) -> int` - Calculate 0-100 score
- `validate(products: list) -> tuple[bool, dict]` - Validate batch quality

### EmbeddingGenerator

```python
EmbeddingGenerator(model_name: str = None)
```

**Methods:**
- `generate_embedding(product: dict) -> np.ndarray` - Generate 768-dim embedding
- `generate_batch(products: list, batch_size=32, show_progress=True) -> list`
- `compute_content_hash(product: dict) -> str` - Hash for change detection
- `needs_reembedding(product: dict, stored_hash: str) -> bool`

### VendorEnrichmentConfig

```python
VendorEnrichmentConfig(vendor_slug: str = None, config_path: str = None)
```

**Methods:**
- `apply_auto_tags(product: dict) -> list[str]` - Apply tagging rules
- `get_product_type(product: dict) -> str` - Determine product_type
- `get_collections(product: dict) -> list[str]` - Determine collections
- `enrich_product(product: dict) -> dict` - Apply all enrichment rules

## Output Format

### Enriched Product Schema

```python
{
    # Original fields
    'id': str,
    'title': str,
    'description': str,
    'vendor': str,
    'sku': str,
    'price': float,

    # Extracted attributes
    'extracted_color': str,           # "Jade Grün"
    'extracted_size': str,            # "20"
    'extracted_unit': str,            # "ml"
    'extracted_material': str,        # "Acryl"
    'inferred_category': str,         # "Farbe"

    # Vendor enrichment
    'product_type': str,              # From YAML rules
    'tags': str,                      # Comma-separated
    'vendor_keywords': list[str],     # From YAML

    # SEO fields
    'meta_title': str,                # Optional
    'meta_description': str,          # Optional
    'url_handle': str,                # Optional

    # AI generation
    'ai_generated': bool,             # True if AI-generated
    'ai_model_used': str,             # Model name

    # Family grouping
    'family_id': str,                 # "fam_00001"
    'is_base_variant': bool,          # True for first variant
    'variant_count': int,             # Total variants in family

    # Embeddings
    'embedding': list[float],         # 768-dimensional vector
    'embedding_hash': str,            # Content hash

    # Quality
    'data_quality_score': int,        # 0-100
    'enrichment_status': str          # Status indicator
}
```

## Troubleshooting

### Common Issues

**1. Import errors**
```python
# Error: ModuleNotFoundError: No module named 'sentence_transformers'
# Fix: Install dependencies
pip install sentence-transformers>=2.0.0
```

**2. Model download slow**
```python
# sentence-transformers downloads model on first use (~500MB)
# Solution: Pre-download model
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
```

**3. API rate limiting**
```python
# Error: OpenRouter rate limit exceeded
# Fix: Reduce max_ai_products or add delay
pipeline.run(products, max_ai_products=50)  # Limit to 50
```

**4. Quality gate blocking**
```python
# Products not meeting 85% threshold
# Option 1: Force through gate
pipeline.run(products, force=True)

# Option 2: Run AI generation to improve quality
pipeline.run(products, skip_ai=False)
```

**5. Memory issues with embeddings**
```python
# Large batches exhaust memory
# Solution: Process in chunks
for chunk in chunks(products, 100):
    pipeline.run(chunk)
```

## Contributing

When adding new features:

1. **Add tests** - Minimum 80% coverage
2. **Update this README** - Document new features
3. **Update config.py** - Add new constants/thresholds
4. **Run full test suite** - `pytest tests/ -v`
5. **Check performance** - Benchmark new operations

## License

Internal use only - Part of Shopify Multi-Supplier Platform

## Related Documentation

- **Vendor YAML Template**: `config/vendors/_template.yaml`
- **Phase Documentation**: `.planning/phases/02.2-product-enrichment-pipeline/`
- **Test Files**: `tests/unit/`, `tests/integration/`
- **Architecture**: `docs/ARCHITECTURE.md`

---

**Built with**: sentence-transformers, OpenRouter API, Jinja2, scikit-learn

**Phase**: 2.2 - Product Enrichment Pipeline (Complete ✓)
