"""
Unit tests for product family grouping and quality validation
"""
import pytest
from src.core.enrichment.families.grouper import ProductFamilyGrouper
from src.core.enrichment.quality.scorer import QualityScorer, QualityGate


class TestProductFamilyGrouper:
    @pytest.fixture
    def grouper(self):
        return ProductFamilyGrouper()

    def test_same_product_different_sizes(self, grouper):
        """Products with same name but different sizes grouped together"""
        products = [
            {'id': '1', 'title': 'Pentart Acrylfarbe Jade 20ml'},
            {'id': '2', 'title': 'Pentart Acrylfarbe Jade 50ml'},
        ]
        result = grouper.create_families(products)
        # Both should have same family_id
        assert result[0]['family_id'] == result[1]['family_id']

    def test_different_products_separate_families(self, grouper):
        """Different products get different family IDs"""
        products = [
            {'id': '1', 'title': 'Pentart Acrylfarbe Jade 20ml'},
            {'id': '2', 'title': 'Reispapier Vintage Rose A4'},
        ]
        result = grouper.create_families(products)
        assert result[0]['family_id'] != result[1]['family_id']

    def test_base_variant_marked(self, grouper):
        """First product in family marked as base variant"""
        products = [
            {'id': '1', 'title': 'Pentart Acrylfarbe Jade 20ml'},
            {'id': '2', 'title': 'Pentart Acrylfarbe Jade 50ml'},
        ]
        result = grouper.create_families(products)
        assert result[0]['is_base_variant'] is True
        assert result[1]['is_base_variant'] is False

    def test_variant_count_set(self, grouper):
        """variant_count reflects family size"""
        products = [
            {'id': '1', 'title': 'Pentart Acrylfarbe Jade 20ml'},
            {'id': '2', 'title': 'Pentart Acrylfarbe Jade 50ml'},
            {'id': '3', 'title': 'Pentart Acrylfarbe Jade 100ml'},
        ]
        result = grouper.create_families(products)
        assert all(p['variant_count'] == 3 for p in result)

    def test_family_key_removes_size(self, grouper):
        """Family key removes size patterns"""
        # Use longer titles that won't trigger fallback
        key1 = grouper._generate_family_key({'title': 'Awesome Product 20ml'})
        key2 = grouper._generate_family_key({'title': 'Awesome Product 50ml'})
        assert key1 == key2
        assert key1 == 'awesome product'

    def test_family_key_removes_color(self, grouper):
        """Family key removes color names"""
        key1 = grouper._generate_family_key({'title': 'Pentart Farbe Jade 20ml'})
        key2 = grouper._generate_family_key({'title': 'Pentart Farbe Ruby 20ml'})
        # Should match after removing jade/ruby AND 20ml
        assert 'jade' not in key1.lower()
        assert 'ruby' not in key2.lower()

    def test_family_key_removes_dimensions(self, grouper):
        """Family key removes dimension patterns"""
        key = grouper._generate_family_key({'title': 'Papier 14x14cm'})
        assert '14' not in key
        assert 'x' not in key

    def test_family_colors_collected(self, grouper):
        """Family collects all color variants"""
        products = [
            {'id': '1', 'title': 'Acryl Paint Red 20ml', 'extracted_color': 'Red'},
            {'id': '2', 'title': 'Acryl Paint Blue 20ml', 'extracted_color': 'Blue'},
        ]
        result = grouper.create_families(products)
        # Should be same family (only color differs)
        assert result[0]['family_id'] == result[1]['family_id']
        # Should have both colors in family_colors
        colors = set(result[0]['family_colors'] + result[1]['family_colors'])
        assert 'Red' in colors
        assert 'Blue' in colors

    def test_family_sizes_collected(self, grouper):
        """Family collects all size variants"""
        products = [
            {'id': '1', 'title': 'Product 20ml', 'extracted_size': '20', 'extracted_unit': 'ml'},
            {'id': '2', 'title': 'Product 50ml', 'extracted_size': '50', 'extracted_unit': 'ml'},
        ]
        result = grouper.create_families(products)
        sizes = set(result[0]['family_sizes'] + result[1]['family_sizes'])
        assert '20ml' in sizes
        assert '50ml' in sizes

    def test_get_family_summary(self, grouper):
        """get_family_summary returns complete family info"""
        products = [
            {'id': '1', 'title': 'Awesome Product 20ml', 'extracted_color': 'Red'},
            {'id': '2', 'title': 'Awesome Product 50ml', 'extracted_color': 'Blue'},
        ]
        result = grouper.create_families(products)
        family_id = result[0]['family_id']
        summary = grouper.get_family_summary(family_id)

        assert summary['family_id'] == family_id
        assert summary['product_count'] == 2
        assert len(summary['available_colors']) == 2
        assert len(summary['variants']) == 2


class TestQualityScorer:
    @pytest.fixture
    def scorer(self):
        return QualityScorer()

    def test_high_quality_product(self, scorer):
        """Product with all fields scores 85+"""
        product = {
            'description': 'A' * 150,
            'extracted_color': 'Red',
            'extracted_size': '20',
            'extracted_material': 'Acryl',
            'inferred_category': 'Farbe',
            'product_type': 'Paint',
            'tags': 'decoupage,craft,DIY'
        }
        score = scorer.calculate_score(product)
        assert score >= 85

    def test_low_quality_product(self, scorer):
        """Product with missing fields scores <50"""
        product = {'description': 'Short'}
        score = scorer.calculate_score(product)
        assert score < 50

    def test_score_bounds(self, scorer):
        """Score always 0-100"""
        # Empty product
        assert scorer.calculate_score({}) >= 0

        # Over-complete product
        product = {
            'description': 'A' * 1000,
            'extracted_color': 'X',
            'extracted_size': 'X',
            'extracted_material': 'X',
            'inferred_category': 'X',
            'product_type': 'X',
            'tags': 'X' * 100
        }
        assert scorer.calculate_score(product) <= 100

    def test_description_scoring(self, scorer):
        """Description length affects score"""
        long_desc = scorer.calculate_score({'description': 'A' * 150})
        medium_desc = scorer.calculate_score({'description': 'A' * 60})
        short_desc = scorer.calculate_score({'description': 'A' * 25})

        assert long_desc > medium_desc > short_desc

    def test_attributes_add_points(self, scorer):
        """Each extracted attribute adds points"""
        base = scorer.calculate_score({'description': 'A' * 100})
        with_color = scorer.calculate_score({'description': 'A' * 100, 'extracted_color': 'Red'})
        with_size = scorer.calculate_score({'description': 'A' * 100, 'extracted_size': '20'})

        assert with_color == base + 10
        assert with_size == base + 10


class TestQualityGate:
    @pytest.fixture
    def gate(self):
        return QualityGate()

    def test_passes_with_good_data(self, gate):
        """Gate passes with 85%+ description coverage"""
        # Create 10 products, 9 with good descriptions (90%)
        products = []
        for i in range(9):
            products.append({
                'id': str(i),
                'title': f'Product {i}',
                'vendor': 'TestVendor',
                'description': 'A' * 50,
                'extracted_color': 'Red',
                'inferred_category': 'Farbe',
                'family_id': f'fam_{i:05d}',
                'sku': f'SKU-{i}'
            })
        # One with short description
        products.append({
            'id': '9',
            'title': 'Product 9',
            'vendor': 'TestVendor',
            'description': 'Short',
            'extracted_color': 'Red',
            'inferred_category': 'Farbe',
            'family_id': 'fam_00009',
            'sku': 'SKU-9'
        })

        passed, report = gate.validate(products)
        assert passed is True
        assert report['summary']['passed_checks'] == 6

    def test_fails_with_poor_description_coverage(self, gate):
        """Gate fails with <85% description coverage"""
        # Create 10 products, only 5 with good descriptions (50%)
        products = []
        for i in range(5):
            products.append({
                'id': str(i),
                'title': f'Product {i}',
                'vendor': 'TestVendor',
                'description': 'A' * 50,
                'family_id': f'fam_{i:05d}'
            })
        for i in range(5, 10):
            products.append({
                'id': str(i),
                'title': f'Product {i}',
                'vendor': 'TestVendor',
                'description': 'X',
                'family_id': f'fam_{i:05d}'
            })

        passed, report = gate.validate(products)
        assert passed is False
        assert 'Description Coverage' in [c['name'] for c in report['checks'] if not c['passed']]

    def test_fails_with_missing_families(self, gate):
        """Gate fails if products missing family_id"""
        products = [
            {'id': '1', 'title': 'Product 1', 'vendor': 'Test', 'description': 'A' * 50},
            {'id': '2', 'title': 'Product 2', 'vendor': 'Test', 'description': 'A' * 50}
        ]

        passed, report = gate.validate(products)
        assert passed is False
        # Should fail family assignment check
        family_check = [c for c in report['checks'] if c['name'] == 'Family Assignment'][0]
        assert family_check['passed'] is False

    def test_fails_with_duplicate_skus(self, gate):
        """Gate fails with duplicate SKUs"""
        products = [
            {'id': '1', 'title': 'Product 1', 'vendor': 'Test', 'description': 'A' * 50, 'sku': 'SKU-1', 'family_id': 'fam_1'},
            {'id': '2', 'title': 'Product 2', 'vendor': 'Test', 'description': 'A' * 50, 'sku': 'SKU-1', 'family_id': 'fam_2'}
        ]

        passed, report = gate.validate(products)
        assert passed is False
        sku_check = [c for c in report['checks'] if c['name'] == 'SKU Uniqueness'][0]
        assert sku_check['passed'] is False
        assert sku_check['duplicates'] == 1

    def test_fails_with_missing_critical_fields(self, gate):
        """Gate fails with missing titles or vendors"""
        products = [
            {'id': '1', 'description': 'A' * 50, 'family_id': 'fam_1'}  # Missing title and vendor
        ]

        passed, report = gate.validate(products)
        assert passed is False
        critical_check = [c for c in report['checks'] if c['name'] == 'Critical Fields'][0]
        assert critical_check['passed'] is False

    def test_empty_products_returns_error(self, gate):
        """Gate returns error with empty product list"""
        passed, report = gate.validate([])
        assert passed is False
        assert 'error' in report
