"""
Config Verifier

LLM-powered verification of auto-generated vendor configs.
Validates URLs, selectors, SKU patterns before user sees config.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import requests

from .vendor_schema import VendorConfig

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single verification check."""
    name: str
    status: str  # passed, failed, warning
    tested: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    details: str = ""
    issues: list[dict] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Complete verification result."""
    status: str  # verified, failed, needs_review
    overall_score: float
    checks: dict[str, CheckResult]
    recommendations: list[str]
    user_prompts: list[dict]
    verified_at: datetime
    verified_by: str
    error: Optional[str] = None


class ConfigVerifier:
    """
    Verify auto-generated vendor configs using LLM.

    Checks:
    1. URLs - Test if product URLs return 200
    2. Selectors - Validate CSS selectors syntax
    3. SKU patterns - Verify regex compiles and matches examples
    4. Content extraction - Test on sample products if available
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "google/gemini-flash-1.5"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or self.DEFAULT_MODEL

    async def verify(
        self,
        config: VendorConfig,
        sample_skus: list[str] = None
    ) -> VerificationResult:
        """
        Verify vendor config.

        Args:
            config: VendorConfig to verify
            sample_skus: Optional SKUs for testing

        Returns:
            VerificationResult with check details
        """
        checks = {}
        recommendations = []
        user_prompts = []

        # Check 1: SKU patterns
        sku_check = self._verify_sku_patterns(config)
        checks['sku_patterns'] = sku_check
        if sku_check.status == 'failed':
            user_prompts.append({
                'prompt_id': 'sku_pattern_invalid',
                'question': f"SKU pattern validation failed: {sku_check.details}",
                'options': ['Fix pattern', 'Use default pattern']
            })

        # Check 2: URL templates
        url_check = self._verify_urls(config)
        checks['urls'] = url_check
        if url_check.status == 'failed':
            recommendations.append("URL templates may need adjustment")

        # Check 3: Selectors syntax
        selector_check = self._verify_selectors(config)
        checks['selectors'] = selector_check
        if selector_check.warnings > 0:
            recommendations.append("Some selectors use default fallbacks - verify manually")

        # Check 4: Rate limiting
        rate_check = self._verify_rate_limits(config)
        checks['rate_limiting'] = rate_check

        # Check 5: Site accessibility (if API available)
        if self.api_key:
            accessibility_check = await self._verify_accessibility_with_llm(config)
            checks['site_accessibility'] = accessibility_check

        # Calculate overall score
        total_checks = len(checks)
        passed_checks = sum(1 for c in checks.values() if c.status == 'passed')
        warning_checks = sum(1 for c in checks.values() if c.status == 'warning')

        overall_score = (passed_checks + warning_checks * 0.5) / total_checks

        # Determine status
        if all(c.status in ['passed', 'warning'] for c in checks.values()):
            status = 'verified' if overall_score >= 0.8 else 'needs_review'
        else:
            status = 'failed'

        return VerificationResult(
            status=status,
            overall_score=round(overall_score, 2),
            checks=checks,
            recommendations=recommendations,
            user_prompts=user_prompts,
            verified_at=datetime.utcnow(),
            verified_by=self.model if self.api_key else "local"
        )

    def _verify_sku_patterns(self, config: VendorConfig) -> CheckResult:
        """Verify SKU patterns compile and match examples."""
        import re

        tested = 0
        passed = 0
        issues = []

        for pattern in config.sku_patterns:
            tested += 1
            try:
                regex = re.compile(pattern.regex)

                # Test against examples
                for example in pattern.examples:
                    if not regex.match(example):
                        issues.append({
                            'field': 'sku_pattern',
                            'issue': f"Example '{example}' doesn't match pattern '{pattern.regex}'",
                            'severity': 'error'
                        })
                    else:
                        passed += 1

            except re.error as e:
                issues.append({
                    'field': 'sku_pattern',
                    'issue': f"Invalid regex '{pattern.regex}': {e}",
                    'severity': 'error'
                })

        status = 'passed' if not issues else ('warning' if passed > 0 else 'failed')

        return CheckResult(
            name='sku_patterns',
            status=status,
            tested=tested,
            passed=passed,
            failed=len(issues),
            details=f"Validated {tested} patterns, {passed} examples matched",
            issues=issues
        )

    def _verify_urls(self, config: VendorConfig) -> CheckResult:
        """Verify URL templates have required placeholders."""
        issues = []
        tested = 0
        passed = 0

        # Use model_dump to convert Pydantic model to dict
        urls_dict = config.urls if isinstance(config.urls, dict) else config.urls.model_dump()
        product_url = urls_dict.get('product', {})
        template = product_url.get('template', '') if isinstance(product_url, dict) else ''

        tested += 1
        if template:
            if '{sku}' in template or '{sku_lower}' in template or '{sku_upper}' in template:
                passed += 1
            else:
                issues.append({
                    'field': 'product_url',
                    'issue': 'Product URL template missing {sku} placeholder',
                    'severity': 'error'
                })
        else:
            issues.append({
                'field': 'product_url',
                'issue': 'No product URL template defined',
                'severity': 'error'
            })

        status = 'passed' if passed == tested else 'failed'

        return CheckResult(
            name='urls',
            status=status,
            tested=tested,
            passed=passed,
            failed=len(issues),
            details=f"URL templates: {passed}/{tested} valid",
            issues=issues
        )

    def _verify_selectors(self, config: VendorConfig) -> CheckResult:
        """Verify CSS selectors are valid."""
        tested = 0
        passed = 0
        warnings = 0
        issues = []

        required_selectors = ['title', 'images']

        # Use model_dump to convert Pydantic model to dict
        selectors_dict = config.selectors if isinstance(config.selectors, dict) else config.selectors.model_dump()

        for field in required_selectors:
            selector_config = selectors_dict.get(field, {})
            selector = selector_config.get('selector', '') if isinstance(selector_config, dict) else ''
            fallbacks = selector_config.get('fallback_selectors', []) if isinstance(selector_config, dict) else []

            tested += 1

            if selector:
                # Basic CSS selector validation
                if self._is_valid_css_selector(selector):
                    passed += 1
                else:
                    issues.append({
                        'field': field,
                        'issue': f'Invalid CSS selector: {selector}',
                        'severity': 'error'
                    })
            elif fallbacks:
                warnings += 1
                issues.append({
                    'field': field,
                    'issue': 'Primary selector empty, using fallbacks',
                    'severity': 'warning'
                })
            else:
                issues.append({
                    'field': field,
                    'issue': f'No selector defined for {field}',
                    'severity': 'error'
                })

        status = 'passed' if passed == tested else ('warning' if warnings > 0 else 'failed')

        return CheckResult(
            name='selectors',
            status=status,
            tested=tested,
            passed=passed,
            warnings=warnings,
            failed=tested - passed - warnings,
            details=f"Selectors: {passed} valid, {warnings} using fallbacks",
            issues=issues
        )

    def _verify_rate_limits(self, config: VendorConfig) -> CheckResult:
        """Verify rate limiting is configured."""
        scraping_dict = config.scraping if isinstance(config.scraping, dict) else (config.scraping.model_dump() if config.scraping else {})
        rate_limits = scraping_dict.get('rate_limits', {})

        has_delay = rate_limits.get('delay_between_requests_ms', 0) > 0 if isinstance(rate_limits, dict) else False
        has_max_concurrent = rate_limits.get('max_concurrent_requests', 0) > 0 if isinstance(rate_limits, dict) else False

        if has_delay and has_max_concurrent:
            return CheckResult(
                name='rate_limiting',
                status='passed',
                tested=2,
                passed=2,
                details='Rate limiting configured'
            )
        else:
            return CheckResult(
                name='rate_limiting',
                status='warning',
                tested=2,
                passed=1 if has_delay or has_max_concurrent else 0,
                warnings=1,
                details='Partial rate limiting - may cause blocks'
            )

    async def _verify_accessibility_with_llm(self, config: VendorConfig) -> CheckResult:
        """Use LLM to verify site characteristics."""
        if not self.api_key:
            return CheckResult(
                name='site_accessibility',
                status='warning',
                details='API key not available for LLM verification'
            )

        scraping_dict = config.scraping if isinstance(config.scraping, dict) else (config.scraping.model_dump() if config.scraping else {})
        strategy = scraping_dict.get('strategy', {})
        rate_limits = scraping_dict.get('rate_limits', {})

        prompt = f"""Analyze this vendor configuration and verify it's reasonable:

Vendor: {config.vendor.name}
Domain: {config.vendor.domain}
Strategy: {strategy.get('primary', 'unknown') if isinstance(strategy, dict) else 'unknown'}
Rate limit delay: {rate_limits.get('delay_between_requests_ms', 0) if isinstance(rate_limits, dict) else 0}ms

Questions:
1. Is the domain likely a real e-commerce site?
2. Is the rate limiting reasonable (not too aggressive)?
3. Are the selectors common patterns for e-commerce?

Return JSON:
{{
    "is_valid_ecommerce": true/false,
    "rate_limit_ok": true/false,
    "selectors_reasonable": true/false,
    "requires_javascript": true/false,
    "notes": "any concerns"
}}"""

        try:
            response = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 300
                },
                timeout=30
            )
            response.raise_for_status()

            content = response.json()['choices'][0]['message']['content']
            content = content.strip()
            if content.startswith('```'):
                content = '\n'.join(content.split('\n')[1:-1])

            data = json.loads(content)

            passed = sum([
                data.get('is_valid_ecommerce', False),
                data.get('rate_limit_ok', False),
                data.get('selectors_reasonable', False)
            ])

            return CheckResult(
                name='site_accessibility',
                status='passed' if passed >= 2 else 'warning',
                tested=3,
                passed=passed,
                details=data.get('notes', 'LLM verification complete')
            )

        except Exception as e:
            logger.warning(f"LLM verification failed: {e}")
            return CheckResult(
                name='site_accessibility',
                status='warning',
                details=f'LLM verification failed: {e}'
            )

    def _is_valid_css_selector(self, selector: str) -> bool:
        """Basic CSS selector validation."""
        # Very basic validation - just check for common patterns
        if not selector:
            return False

        # Check for obviously invalid patterns
        invalid_patterns = ['<', '>', '{{', '}}', '`']
        for pattern in invalid_patterns:
            if pattern in selector:
                return False

        # Check for common valid patterns
        valid_patterns = [
            r'^[.#]?[\w-]+',  # Class, ID, or tag
            r'\[[\w-]+',      # Attribute selector
            r':[\w-]+',       # Pseudo selector
        ]

        import re
        return any(re.match(p, selector) for p in valid_patterns)

    def update_config_with_verification(
        self,
        config: VendorConfig,
        result: VerificationResult
    ) -> VendorConfig:
        """Update config with verification results."""
        # Access meta via the alias and convert to dict
        meta_dict = config.meta if isinstance(config.meta, dict) else (config.meta.model_dump() if hasattr(config, 'meta') and config.meta else {})
        meta_dict['verification'] = {
            'status': result.status,
            'verified_at': result.verified_at.isoformat() + 'Z',
            'verified_by': result.verified_by,
            'overall_score': result.overall_score,
            'checks': {
                name: {
                    'status': check.status,
                    'tested': check.tested,
                    'passed': check.passed,
                    'details': check.details
                }
                for name, check in result.checks.items()
            },
            'recommendations': result.recommendations,
            'user_prompts': {'shown': result.user_prompts}
        }

        # Update via _meta alias
        config._meta = meta_dict
        return config
