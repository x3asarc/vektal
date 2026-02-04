Vision AI Alt Text Generator
===========================

This project includes a Vision AI module for generating German SEO-friendly alt text with
intelligent caching to reduce API costs. The implementation lives in `src/core`, with a
lightweight public wrapper package in `vision_ai`.

Quick Start
-----------

```bash
python -m vision_ai.test \
  --image "https://cdn.shopify.com/..." \
  --title "Pentart Acrylfarben Metallic Set" \
  --vendor "Pentart" \
  --type "Acrylfarben" \
  --tags "metallic,acryl,basteln"
```

You can also run the existing CLI tool:

```bash
python cli/vision/generate_vision_alt_text.py \
  --image-url "https://cdn.shopify.com/..." \
  --title "Pentart Acrylfarben Metallic Set" \
  --vendor "Pentart" \
  --type "Acrylfarben" \
  --tags "metallic,acryl,basteln"
```

Python Usage
------------

```python
from vision_ai import AltTextGenerator

generator = AltTextGenerator(
    cache_db_path="data/vision_cache.db",
    model="google/gemini-flash-1.5-8b",
)

alt_text = generator.generate(
    image_url="https://cdn.shopify.com/s/files/1/0624/...",
    product_context={
        "title": "Pentart Acrylfarben Set Metallic",
        "vendor": "Pentart",
        "product_type": "Acrylfarben",
        "tags": ["metallic", "acryl", "basteln"],
    },
)
```

Environment Variables
---------------------

```
OPENROUTER_API_KEY=your_key_here
VISION_AI_PROVIDER=openrouter
VISION_AI_MODEL=google/gemini-flash-1.5-8b
VISION_AI_MAX_RETRIES=3
VISION_AI_CACHE_DB=data/vision_cache.db
VISION_AI_DAILY_BUDGET_EUR=5.0
VISION_AI_MONTHLY_BUDGET_EUR=50.0
```

Files and Modules
-----------------

Core implementation (used by the pipeline):
- `src/core/vision_client.py`
- `src/core/vision_cache.py`
- `src/core/vision_engine.py`
- `src/core/vision_prompts.py`

Public wrapper package:
- `vision_ai/__init__.py`
- `vision_ai/client.py`
- `vision_ai/cache.py`
- `vision_ai/generator.py`
- `vision_ai/prompts.py`
- `vision_ai/stats.py`

Cache Database
--------------

The default cache database is `data/vision_cache.db` (overridable by `VISION_AI_CACHE_DB`).
It stores image hashes, alt text, and usage stats to reduce API calls and track spend.
