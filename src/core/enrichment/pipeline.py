"""Main enrichment pipeline orchestrator."""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from .extractors.attributes import AttributeExtractor
from .generators.descriptions import AIDescriptionGenerator
from .generators.seo import SEOGenerator
from .families.grouper import ProductFamilyGrouper
from .quality.scorer import QualityScorer, QualityGate
from .embeddings.generator import EmbeddingGenerator
from .templating.engine import TemplateEngine
from .config import QUALITY_THRESHOLDS
from .vendor_integration import VendorEnrichmentConfig, detect_vendor_from_product, load_vendor_enrichment_config


class EnrichmentPipeline:
    """Orchestrates the complete product enrichment process"""

    def __init__(self,
                 openrouter_api_key: str = None,
                 openrouter_model: str = "google/gemini-flash-1.5",
                 checkpoint_dir: str = "data/enrichment_checkpoints"):
        """
        Initialize pipeline components.

        Args:
            openrouter_api_key: API key for AI description generation
            openrouter_model: Model to use for descriptions
            checkpoint_dir: Directory for saving intermediate checkpoints
        """
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_model = openrouter_model
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components (lazy loaded where expensive)
        self.extractor = AttributeExtractor()
        self.seo_generator = SEOGenerator()
        self.family_grouper = ProductFamilyGrouper()
        self.quality_scorer = QualityScorer()
        self.quality_gate = QualityGate()
        self.template_engine = TemplateEngine()

        # Lazy loaded (expensive to init)
        self._ai_generator: Optional[AIDescriptionGenerator] = None
        self._embedding_generator: Optional[EmbeddingGenerator] = None

    @property
    def ai_generator(self) -> AIDescriptionGenerator:
        """Lazy load AI generator"""
        if self._ai_generator is None:
            self._ai_generator = AIDescriptionGenerator(
                api_key=self.openrouter_api_key,
                model=self.openrouter_model
            )
        return self._ai_generator

    @property
    def embedding_generator(self) -> EmbeddingGenerator:
        """Lazy load embedding generator"""
        if self._embedding_generator is None:
            self._embedding_generator = EmbeddingGenerator()
        return self._embedding_generator

    def _load_vendor_config(self, vendor_slug: str) -> Optional[dict]:
        """Load vendor config from YAML file by slug.

        This enables the vendor_slug parameter in run() to auto-load config.
        """
        config = load_vendor_enrichment_config(vendor_slug)
        if config:
            return config.raw_config
        return None

    def run(self,
            products: List[dict],
            vendor_config: dict = None,
            vendor_slug: str = None,
            skip_extraction: bool = False,
            skip_ai: bool = False,
            skip_families: bool = False,
            skip_embeddings: bool = False,
            skip_quality_gate: bool = False,
            force: bool = False,
            max_ai_products: int = None) -> tuple:
        """
        Run the complete enrichment pipeline.

        Steps:
        1. Extract attributes from titles/descriptions
        2. Apply vendor templates (if vendor_config provided)
        3. Generate AI descriptions (for low-quality products)
        4. Create product families
        5. Generate embeddings
        6. Quality gate validation
        7. Save output

        Args:
            products: List of raw product dicts from scraper
            vendor_config: Vendor YAML config dict for templates/rules (explicit)
            vendor_slug: Vendor identifier to auto-load config from YAML file
                         NOTE: Auto-loading implemented in Plan 06 via
                         _load_vendor_config() method added to this class
            skip_*: Flags to skip individual steps
            force: Bypass quality gate
            max_ai_products: Limit AI generation count

        Returns:
            (enriched_products: list, quality_report: dict)

        Vendor Config Loading (implemented in Plan 06):
            If vendor_slug provided but vendor_config is None, Plan 06 adds
            _load_vendor_config(vendor_slug) to load from config/vendors/{slug}.yaml
        """
        print("\n" + "="*60)
        print("PRODUCT ENRICHMENT PIPELINE")
        print("="*60)
        print(f"Products: {len(products)}")
        print(f"AI Model: {self.openrouter_model}")

        # Auto-load vendor config if vendor_slug provided
        if vendor_slug and not vendor_config:
            vendor_config = self._load_vendor_config(vendor_slug)

        # Step 1: Extract attributes
        if not skip_extraction:
            products = self._step_extract_attributes(products)
            self._save_checkpoint(products, 'extraction')

        # Step 1.5: Apply vendor-specific enrichment rules
        products = self._step_apply_vendor_rules(products)
        self._save_checkpoint(products, 'vendor_rules')

        # Step 2: Apply vendor templates (if config provided)
        if vendor_config:
            products = self._step_apply_templates(products, vendor_config)
            self._save_checkpoint(products, 'templates')

        # Step 3: Generate AI descriptions for low-quality products
        if not skip_ai and self.openrouter_api_key:
            products = self._step_ai_generation(products, max_ai_products)
            self._save_checkpoint(products, 'ai')

        # Step 4: Create product families
        if not skip_families:
            products = self._step_create_families(products)
            self._save_checkpoint(products, 'families')

        # Step 5: Generate embeddings
        if not skip_embeddings:
            products = self._step_generate_embeddings(products)
            self._save_checkpoint(products, 'embeddings')

        # Step 6: Calculate quality scores
        products = self._step_calculate_scores(products)

        # Step 7: Quality gate
        passed, report = True, {}
        if not skip_quality_gate:
            passed, report = self._step_quality_gate(products, force)

        if not passed and not force:
            print("\n[BLOCKED] Pipeline halted at quality gate.")
            return products, report

        print("\n[SUCCESS] Pipeline complete!")
        self._print_summary(products)

        return products, report

    def _step_extract_attributes(self, products: List[dict]) -> List[dict]:
        """Step 1: Extract color, size, material, category"""
        print("\n[Step 1] Extracting attributes...")

        for product in products:
            attrs = self.extractor.extract_all(
                product.get('title', ''),
                product.get('description', '')
            )
            product.update(attrs)
            product['enrichment_status'] = 'extracted'

        extracted_colors = sum(1 for p in products if p.get('extracted_color'))
        print(f"  * Extracted color for {extracted_colors}/{len(products)} products")

        return products

    def _step_apply_vendor_rules(self, products: List[dict]) -> List[dict]:
        """Apply vendor-specific enrichment rules from YAML"""
        print("\n[Step 1.5] Applying vendor enrichment rules...")

        # Group products by vendor
        vendor_configs = {}

        for product in products:
            vendor_slug = detect_vendor_from_product(product)
            if vendor_slug and vendor_slug not in vendor_configs:
                config = load_vendor_enrichment_config(vendor_slug)
                vendor_configs[vendor_slug] = config

            if vendor_slug and vendor_configs.get(vendor_slug):
                vendor_configs[vendor_slug].enrich_product(product)

        applied_count = sum(1 for p in products if p.get('vendor_keywords'))
        print(f"  * Applied vendor rules to {applied_count}/{len(products)} products")

        return products

    def _step_apply_templates(self, products: List[dict],
                             vendor_config: dict) -> List[dict]:
        """Step 2: Apply vendor YAML content templates"""
        print("\n[Step 2] Applying vendor templates...")

        for product in products:
            rendered = self.template_engine.render_product_content(
                vendor_config, product
            )
            # Only update if templates produced content
            if rendered.get('title'):
                product['title'] = rendered['title']
            if rendered.get('description'):
                product['description'] = rendered['description']
            product['enrichment_status'] = 'templated'

        return products

    def _step_ai_generation(self, products: List[dict],
                           max_products: int = None) -> List[dict]:
        """Step 3: Generate AI descriptions for low-quality products"""
        print("\n[Step 3] AI description generation...")

        # Find products needing AI help
        needs_ai = [
            p for p in products
            if self.quality_scorer.calculate_score(p) < 50
            or len(str(p.get('description', ''))) < 20
        ]

        if max_products:
            needs_ai = needs_ai[:max_products]

        if not needs_ai:
            print("  No products need AI generation")
            return products

        print(f"  Generating for {len(needs_ai)} products...")

        # Generate descriptions
        for product in needs_ai:
            try:
                desc = self.ai_generator.generate_description(
                    product,
                    examples=[]  # Will find similar internally
                )
                if desc:
                    product['description'] = desc
                    product['ai_generated'] = True
                    product['ai_model_used'] = self.openrouter_model
                    product['enrichment_status'] = 'ai_generated'
            except Exception as e:
                print(f"  WARNING: AI generation failed for {product.get('title', 'unknown')}: {e}")

        return products

    def _step_create_families(self, products: List[dict]) -> List[dict]:
        """Step 4: Group variants into families"""
        print("\n[Step 4] Creating product families...")
        return self.family_grouper.create_families(products)

    def _step_generate_embeddings(self, products: List[dict]) -> List[dict]:
        """Step 5: Generate 768-dim embeddings for semantic search"""
        print("\n[Step 5] Generating embeddings...")

        embeddings = self.embedding_generator.generate_batch(
            products, show_progress=True
        )

        for product, embedding in zip(products, embeddings):
            product['embedding'] = embedding.tolist()  # Convert for JSON
            product['embedding_hash'] = self.embedding_generator.compute_content_hash(product)

        return products

    def _step_calculate_scores(self, products: List[dict]) -> List[dict]:
        """Step 6: Calculate quality scores"""
        print("\n[Step 6] Calculating quality scores...")

        for product in products:
            product['data_quality_score'] = self.quality_scorer.calculate_score(product)

        avg_score = sum(p['data_quality_score'] for p in products) / len(products)
        print(f"  * Average quality score: {avg_score:.1f}/100")

        return products

    def _step_quality_gate(self, products: List[dict],
                          force: bool = False) -> tuple:
        """Step 7: Quality gate validation"""
        print("\n[Step 7] Quality gate validation...")
        passed, report = self.quality_gate.validate(products)

        if not passed and force:
            print("  WARNING: Quality gate failed but --force enabled")
            return True, report

        return passed, report

    def _save_checkpoint(self, products: List[dict], step_name: str):
        """Save checkpoint for resumability"""
        checkpoint_path = self.checkpoint_dir / f'checkpoint_{step_name}.json'

        # Remove numpy arrays for JSON serialization
        serializable = []
        for p in products:
            p_copy = p.copy()
            if 'embedding' in p_copy and hasattr(p_copy['embedding'], 'tolist'):
                p_copy['embedding'] = p_copy['embedding'].tolist()
            serializable.append(p_copy)

        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)

        print(f"  * Checkpoint saved: {checkpoint_path.name}")

    def load_checkpoint(self, step_name: str) -> List[dict]:
        """Load products from checkpoint"""
        checkpoint_path = self.checkpoint_dir / f'checkpoint_{step_name}.json'
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _print_summary(self, products: List[dict]):
        """Print enrichment summary"""
        print("\n" + "="*60)
        print("ENRICHMENT SUMMARY")
        print("="*60)

        total = len(products)
        ai_generated = sum(1 for p in products if p.get('ai_generated'))
        avg_score = sum(p.get('data_quality_score', 0) for p in products) / total
        families = len(set(p.get('family_id') for p in products if p.get('family_id')))

        print(f"  Total products: {total}")
        print(f"  AI descriptions: {ai_generated}")
        print(f"  Product families: {families}")
        print(f"  Average quality: {avg_score:.1f}/100")
        print("="*60)
