"""
Quality Scorer and Quality Gate - validate enrichment quality
"""
from typing import Dict, List, Tuple
from ..config import QUALITY_THRESHOLDS


class QualityScorer:
    """Calculate product-level quality scores (0-100)"""

    def calculate_score(self, product: dict) -> int:
        """
        Calculate quality score using weighted formula:
        - Completeness (40-50 points): description length
        - Richness (30-40 points): extracted attributes
        - SEO health (20-30 points): category, tags

        Returns integer 0-100.
        """
        score = 0

        # Completeness: description length
        desc_len = len(str(product.get('description', '')))
        if desc_len > 100:
            score += 40
        elif desc_len > 50:
            score += 30
        elif desc_len > 20:
            score += 15

        # Richness: extracted attributes (10 points each)
        if product.get('extracted_color'):
            score += 10
        if product.get('extracted_size'):
            score += 10
        if product.get('extracted_material'):
            score += 10

        # SEO health (10 points each)
        if product.get('inferred_category'):
            score += 10
        if len(str(product.get('product_type', ''))) > 2:
            score += 10
        if len(str(product.get('tags', ''))) > 10:
            score += 10

        return min(score, 100)


class QualityGate:
    """Validate batch quality meets thresholds before proceeding"""

    def __init__(self):
        self.thresholds = QUALITY_THRESHOLDS
        self.checks: List[dict] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, products: List[dict]) -> Tuple[bool, dict]:
        """
        Run all quality checks on product batch.

        Checks:
        - Description coverage >= 85%
        - Color coverage >= 60%
        - Category coverage >= 75%
        - All products have family_id
        - No duplicate SKUs
        - Critical fields present (title, vendor)

        Returns (passed: bool, report: dict)
        """
        if not products:
            return False, {'error': 'No products to validate'}

        # Reset state
        self.checks = []
        self.errors = []
        self.warnings = []

        # Run all checks
        self.checks = [
            self._check_description_coverage(products),
            self._check_color_coverage(products),
            self._check_category_coverage(products),
            self._check_family_assignment(products),
            self._check_sku_uniqueness(products),
            self._check_critical_fields(products)
        ]

        # Compile results
        passed_checks = sum(1 for c in self.checks if c['passed'])
        total_checks = len(self.checks)

        passed = passed_checks == total_checks

        # Calculate overall score if data_quality_score exists
        avg_score = 0
        scores = [p.get('data_quality_score', 0) for p in products if p.get('data_quality_score')]
        if scores:
            avg_score = sum(scores) / len(scores)

        report = {
            'passed': passed,
            'score': round(avg_score),
            'checks': self.checks,
            'summary': {
                'total_products': len(products),
                'passed_checks': passed_checks,
                'total_checks': total_checks,
                'warnings': len(self.warnings),
                'errors': len(self.errors)
            }
        }

        return passed, report

    def _check_description_coverage(self, products: List[dict]) -> dict:
        """Check description length coverage"""
        min_length = self.thresholds['min_description_length']
        good_descriptions = sum(1 for p in products
                               if len(str(p.get('description', ''))) >= min_length)
        coverage = good_descriptions / len(products) if products else 0

        passed = coverage >= self.thresholds['min_description_coverage']

        check = {
            'name': 'Description Coverage',
            'passed': passed,
            'importance': 'CRITICAL',
            'coverage': round(coverage * 100, 1),
            'threshold': self.thresholds['min_description_coverage'] * 100,
            'details': f"{good_descriptions}/{len(products)} products have adequate descriptions"
        }

        if not passed:
            self.errors.append(f"Insufficient description coverage: {coverage*100:.1f}% < {self.thresholds['min_description_coverage']*100}%")

        return check

    def _check_color_coverage(self, products: List[dict]) -> dict:
        """Check color extraction coverage"""
        has_color = sum(1 for p in products if p.get('extracted_color'))
        coverage = has_color / len(products) if products else 0

        passed = coverage >= self.thresholds['min_color_coverage']

        check = {
            'name': 'Color Coverage',
            'passed': passed,
            'importance': 'HIGH',
            'coverage': round(coverage * 100, 1),
            'threshold': self.thresholds['min_color_coverage'] * 100,
            'details': f"{has_color}/{len(products)} products have extracted color"
        }

        if not passed:
            self.warnings.append(f"Low color coverage: {coverage*100:.1f}%")

        return check

    def _check_category_coverage(self, products: List[dict]) -> dict:
        """Check category inference coverage"""
        has_category = sum(1 for p in products if p.get('inferred_category'))
        coverage = has_category / len(products) if products else 0

        passed = coverage >= self.thresholds['min_category_coverage']

        check = {
            'name': 'Category Coverage',
            'passed': passed,
            'importance': 'HIGH',
            'coverage': round(coverage * 100, 1),
            'threshold': self.thresholds['min_category_coverage'] * 100,
            'details': f"{has_category}/{len(products)} products have inferred category"
        }

        if not passed:
            self.warnings.append(f"Low category coverage: {coverage*100:.1f}%")

        return check

    def _check_family_assignment(self, products: List[dict]) -> dict:
        """Check all products have family_id"""
        assigned = sum(1 for p in products if p.get('family_id'))
        coverage = assigned / len(products) if products else 0

        passed = coverage == 1.0  # Must be 100%

        check = {
            'name': 'Family Assignment',
            'passed': passed,
            'importance': 'MEDIUM',
            'coverage': round(coverage * 100, 1),
            'threshold': 100,
            'details': f"{assigned}/{len(products)} products assigned to families"
        }

        if not passed:
            self.errors.append(f"{len(products) - assigned} products missing family_id")

        return check

    def _check_sku_uniqueness(self, products: List[dict]) -> dict:
        """Check for duplicate SKUs"""
        # Collect non-empty SKUs
        skus = [p.get('sku') for p in products if p.get('sku')]

        if not skus:
            return {
                'name': 'SKU Uniqueness',
                'passed': True,
                'importance': 'LOW',
                'details': 'No SKUs present'
            }

        # Find duplicates
        seen = set()
        duplicates = set()
        for sku in skus:
            if sku in seen:
                duplicates.add(sku)
            seen.add(sku)

        passed = len(duplicates) == 0

        if not passed:
            self.errors.append(f"Found {len(duplicates)} duplicate SKUs")

        return {
            'name': 'SKU Uniqueness',
            'passed': passed,
            'importance': 'CRITICAL',
            'duplicates': len(duplicates),
            'details': f"{len(duplicates)} duplicate SKUs found" if duplicates else "All SKUs unique"
        }

    def _check_critical_fields(self, products: List[dict]) -> dict:
        """Check that critical fields are populated"""
        issues = []

        # Check titles
        empty_titles = sum(1 for p in products
                          if not p.get('title') or len(str(p.get('title', ''))) < 3)
        if empty_titles > 0:
            issues.append(f"{empty_titles} products missing titles")

        # Check vendor
        empty_vendor = sum(1 for p in products
                          if not p.get('vendor') or len(str(p.get('vendor', ''))) < 1)
        if empty_vendor > 0:
            issues.append(f"{empty_vendor} products missing vendor")

        passed = len(issues) == 0

        if not passed:
            self.errors.extend(issues)

        return {
            'name': 'Critical Fields',
            'passed': passed,
            'importance': 'CRITICAL',
            'issues': issues,
            'details': "; ".join(issues) if issues else "All critical fields present"
        }

    def print_report(self, report: dict):
        """Print human-readable quality report"""
        print("\n" + "="*60)
        print("QUALITY GATE REPORT")
        print("="*60)

        print(f"\nOverall Score: {report['score']}/100")
        print(f"Status: {'PASSED' if report['passed'] else 'FAILED'}")

        print(f"\nChecks: {report['summary']['passed_checks']}/{report['summary']['total_checks']} passed")

        print("\nDetailed Results:")
        for check in report['checks']:
            icon = "✓" if check['passed'] else "✗"
            importance = check.get('importance', 'MEDIUM')
            print(f"  {icon} [{importance}] {check['name']}: {check['details']}")

        if self.warnings:
            print("\nWarnings:")
            for w in self.warnings:
                print(f"  - {w}")

        if self.errors:
            print("\nErrors (must fix):")
            for e in self.errors:
                print(f"  - {e}")

        print("\n" + "="*60)

        if not report['passed']:
            print("\nQuality gate FAILED. Fix errors before proceeding.")
        else:
            print("\nQuality gate PASSED! Ready for next step.")
