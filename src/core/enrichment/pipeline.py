"""Main enrichment pipeline orchestrator."""

import json
from pathlib import Path
from typing import Any, List, Dict, Optional
from datetime import datetime

from .extractors.attributes import AttributeExtractor
try:
    from .generators.descriptions import AIDescriptionGenerator
except Exception:  # pragma: no cover - fallback for optional runtime dependency
    class AIDescriptionGenerator:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ImportError("AIDescriptionGenerator dependencies are not installed.")

try:
    from .generators.seo import SEOGenerator
except Exception:  # pragma: no cover - fallback for optional runtime dependency
    class SEOGenerator:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ImportError("SEOGenerator dependencies are not installed.")
from .families.grouper import ProductFamilyGrouper
from .quality.scorer import QualityScorer, QualityGate
try:
    from .embeddings.generator import EmbeddingGenerator
except Exception:  # pragma: no cover - fallback for optional runtime dependency
    class EmbeddingGenerator:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ImportError("EmbeddingGenerator dependencies are not installed.")
from .templating.engine import TemplateEngine
from .config import QUALITY_THRESHOLDS, COLOR_MAP
from .vendor_integration import VendorEnrichmentConfig, detect_vendor_from_product, load_vendor_enrichment_config
from .color_learning import load_store_colors
from .eligibility import build_eligibility_matrix
from .idempotency import EnrichmentIdempotencyCache, compute_enrichment_hash
from .oracle_contract import OracleDecision
from .oracles.content_oracle import evaluate_content_oracle
from .oracles.policy_oracle import evaluate_policy_oracle
from .oracles.visual_oracle import evaluate_visual_oracle
from .profiles import get_profile
from .retrieval_payload import build_retrieval_payload
from .retries import RetryPolicy, execute_with_retry


class EnrichmentPipeline:
    """Orchestrates the complete product enrichment process"""

    def __init__(self,
                 openrouter_api_key: str = None,
                 openrouter_model: str = "google/gemini-flash-1.5",
                 checkpoint_dir: str = "data/enrichment_checkpoints",
                 store_profile_path: str = None):
        """
        Initialize pipeline components.

        Args:
            openrouter_api_key: API key for AI description generation
            openrouter_model: Model to use for descriptions
            checkpoint_dir: Directory for saving intermediate checkpoints
            store_profile_path: Path to store profile JSON (for learned colors)
                               Default: data/store_profile.json
        """
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_model = openrouter_model
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Load store-specific colors learned from catalog analysis
        store_colors = load_store_colors(store_profile_path)

        # Merge with base COLOR_MAP (base takes precedence)
        combined_color_map = dict(COLOR_MAP)
        combined_color_map.update(store_colors)

        # Log color expansion
        if store_colors:
            print(f"Loaded {len(store_colors)} store-specific colors from catalog analysis")
            print(f"Total color vocabulary: {len(combined_color_map)} colors")

        # Initialize components (lazy loaded where expensive)
        # Pass combined color map to extractor for dynamic recognition
        self.extractor = AttributeExtractor(custom_color_map=combined_color_map)
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


class GovernedEnrichmentPipeline:
    """
    Retrieval-first enrichment engine with profile gears and Oracle arbitration.
    """

    def __init__(self, *, cache_ttl_seconds: int = 3600):
        self.cache = EnrichmentIdempotencyCache(ttl_seconds=cache_ttl_seconds)

    @staticmethod
    def _classify_retry_error(exc: Exception) -> str:
        if isinstance(exc, TimeoutError):
            return "timeout"
        if isinstance(exc, ConnectionError):
            return "connectivity"
        if isinstance(exc, PermissionError):
            return "policy_error"
        if isinstance(exc, ValueError):
            return "validation_error"
        return "server_error"

    @staticmethod
    def _fold_oracle_decisions(decisions: list[OracleDecision]) -> OracleDecision:
        severity = {"accept": 0, "suggest": 1, "hold": 2, "reject": 3}
        if not decisions:
            return OracleDecision(
                decision="accept",
                confidence=1.0,
                reason_codes=("no_oracle_constraints",),
                evidence_refs=(),
                requires_user_action=False,
            )
        final = max(decisions, key=lambda item: severity[item.decision])
        reason_codes: list[str] = []
        evidence_refs: list[str] = []
        for decision in decisions:
            reason_codes.extend(decision.reason_codes)
            evidence_refs.extend(decision.evidence_refs)
        return OracleDecision(
            decision=final.decision,
            confidence=min(decision.confidence for decision in decisions),
            reason_codes=tuple(sorted(set(reason_codes))),
            evidence_refs=tuple(sorted(set(evidence_refs))),
            requires_user_action=any(item.requires_user_action for item in decisions),
        )

    def resolve_field_update(
        self,
        *,
        field_name: str,
        merchant_value: Any,
        candidate_value: Any,
        confidence: float,
        structural_conflict: bool = False,
        visual_hex: str | None = None,
        immutable_fields: list[str] | None = None,
        hitl_thresholds: dict | None = None,
    ) -> dict[str, Any]:
        """Resolve one field update with merchant-first and policy-aware arbitration."""
        decisions: list[OracleDecision] = [
            evaluate_content_oracle(
                merchant_value=merchant_value,
                candidate_value=candidate_value,
                confidence=confidence,
                structural_conflict=structural_conflict,
                evidence_refs=[f"field:{field_name}"],
            ),
            evaluate_policy_oracle(
                field_name=field_name,
                before_value=merchant_value,
                after_value=candidate_value,
                immutable_fields=immutable_fields or [],
                hitl_thresholds=hitl_thresholds or {},
            ),
        ]
        if visual_hex is not None and field_name == "color":
            decisions.append(
                evaluate_visual_oracle(
                    text_color=str(candidate_value) if candidate_value is not None else None,
                    visual_hex=visual_hex,
                    confidence=confidence,
                    evidence_refs=["visual_hex"],
                )
            )
        final = self._fold_oracle_decisions(decisions)
        return {
            "field_name": field_name,
            "merchant_value": merchant_value,
            "candidate_value": candidate_value,
            "final_decision": final.to_dict(),
            "oracle_decisions": [decision.to_dict() for decision in decisions],
        }

    def enrich_products(
        self,
        *,
        products: list[dict],
        profile_name: str,
        target_language: str,
        policy_version: int,
    ) -> list[dict]:
        """Build retrieval payloads with profile-dependent Oracle arbitration and idempotent reuse."""
        profile = get_profile(profile_name)
        retry_policy = RetryPolicy(max_attempts=profile.max_retry_attempts)
        enriched: list[dict] = []

        for product in products:
            key = compute_enrichment_hash(
                product_payload=product,
                policy_version=policy_version,
                profile_name=profile.name,
            )

            def _compute():
                eligibility = build_eligibility_matrix(product)
                payload = build_retrieval_payload(
                    product=product,
                    target_language=target_language,
                    profile_name=profile.name,
                    confidence_by_field={
                        "color": float(product.get("color_confidence", 0.8)),
                        "material": float(product.get("material_confidence", 0.8)),
                        "finish_effect": float(product.get("finish_confidence", 0.75)),
                    },
                    source_by_field={
                        "color": "vision_verified" if profile.include_visual_oracle else "ai_inferred",
                        "material": "ai_inferred",
                        "finish_effect": "ai_inferred",
                    },
                    eligibility_matrix=eligibility,
                )
                title_update = self.resolve_field_update(
                    field_name="title",
                    merchant_value=product.get("merchant_title", product.get("title")),
                    candidate_value=payload.get("identity", {}).get("title"),
                    confidence=float(product.get("title_confidence", 0.9)),
                    structural_conflict=bool(product.get("title_structural_conflict", False)),
                    immutable_fields=product.get("immutable_fields", []),
                    hitl_thresholds=product.get("hitl_thresholds", {}),
                )
                decisions = [title_update]
                if profile.include_visual_oracle and payload.get("physical", {}).get("color"):
                    decisions.append(
                        self.resolve_field_update(
                            field_name="color",
                            merchant_value=product.get("merchant_color"),
                            candidate_value=payload.get("physical", {}).get("color"),
                            confidence=float(product.get("color_confidence", 0.8)),
                            structural_conflict=False,
                            visual_hex=product.get("visual_hex"),
                            immutable_fields=product.get("immutable_fields", []),
                            hitl_thresholds=product.get("hitl_thresholds", {}),
                        )
                    )

                return {
                    "idempotency_key": key,
                    "cache_reused": False,
                    "profile": profile.name,
                    "tier": profile.tier,
                    "retrieval_payload": payload,
                    "oracle_resolution": decisions,
                }

            retry_result = execute_with_retry(
                operation=_compute,
                classify_error=self._classify_retry_error,
                policy=retry_policy,
            )
            payload, cache_reused = self.cache.get_or_set(key, lambda: retry_result.result)
            result = dict(payload)
            result["cache_reused"] = cache_reused
            result["retry_attempts"] = retry_result.attempts
            result["profile_contract"] = {
                "include_visual_oracle": profile.include_visual_oracle,
                "include_second_opinion": profile.include_second_opinion,
                "include_multilingual_norm": profile.include_multilingual_norm,
            }
            enriched.append(result)

        return enriched
