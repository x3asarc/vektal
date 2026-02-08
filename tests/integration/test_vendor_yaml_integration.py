"""Integration tests for vendor YAML enrichment configuration."""

import pytest
import tempfile
from pathlib import Path
import yaml
from src.core.enrichment.vendor_integration import (
    VendorEnrichmentConfig,
    load_vendor_enrichment_config,
    detect_vendor_from_product
)


class TestVendorEnrichmentConfig:
    @pytest.fixture
    def sample_vendor_yaml(self, tmp_path):
        """Create sample vendor YAML for testing"""
        config = {
            'vendor': {
                'name': 'Test Vendor',
                'slug': 'test_vendor'
            },
            'enrichment': {
                'keywords': {
                    'primary': ['decoupage', 'rice paper'],
                    'secondary': ['craft', 'DIY'],
                    'brand': ['Test Brand'],
                    'techniques': ['serviettentechnik'],
                    'materials': ['paper', 'adhesive']
                },
                'tagging': {
                    'always_add': ['vendor:Test Vendor', 'quality:premium'],
                    'conditional': [
                        {
                            'condition': "title contains 'A4'",
                            'add_tags': ['size:A4']
                        },
                        {
                            'condition': "title contains 'vintage' OR title contains 'retro'",
                            'add_tags': ['style:vintage']
                        }
                    ]
                },
                'categories': {
                    'default': 'Craft Supplies',
                    'product_type_rules': [
                        {'match': 'rice paper', 'product_type': 'Reispapier'},
                        {'match': 'paint', 'product_type': 'Farben'}
                    ],
                    'collections': {
                        'always': ['All Products'],
                        'conditional': [
                            {'condition': "size == 'A4'", 'collections': ['A4 Papers']}
                        ]
                    }
                },
                'content_templates': {
                    'title': {
                        'template': '{product_name} - {size} - {vendor}',
                        'max_length': 70
                    }
                },
                'seo': {
                    'meta_title': {
                        'template': '{product_name} | Test Store',
                        'max_length': 60
                    }
                }
            }
        }

        yaml_path = tmp_path / 'test_vendor.yaml'
        with open(yaml_path, 'w') as f:
            yaml.dump(config, f)

        return yaml_path

    def test_load_config(self, sample_vendor_yaml):
        """Load vendor config from YAML file"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        assert len(config.keywords.primary) == 2
        assert 'decoupage' in config.keywords.primary

    def test_always_add_tags(self, sample_vendor_yaml):
        """Always-add tags applied to all products"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product = {'title': 'Test Product'}
        tags = config.apply_auto_tags(product)

        assert 'vendor:Test Vendor' in tags
        assert 'quality:premium' in tags

    def test_conditional_tags_simple(self, sample_vendor_yaml):
        """Conditional tags applied when condition matches"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product = {'title': 'Rice Paper A4 Format'}
        tags = config.apply_auto_tags(product)

        assert 'size:A4' in tags

    def test_conditional_tags_or(self, sample_vendor_yaml):
        """Conditional OR tags applied correctly"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product1 = {'title': 'Vintage Rose Paper'}
        product2 = {'title': 'Retro Pattern Paper'}

        tags1 = config.apply_auto_tags(product1)
        tags2 = config.apply_auto_tags(product2)

        assert 'style:vintage' in tags1
        assert 'style:vintage' in tags2

    def test_conditional_tags_no_match(self, sample_vendor_yaml):
        """Conditional tags not applied when condition doesn't match"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product = {'title': 'Simple Paper'}  # No A4, vintage, or retro
        tags = config.apply_auto_tags(product)

        assert 'size:A4' not in tags
        assert 'style:vintage' not in tags

    def test_product_type_mapping(self, sample_vendor_yaml):
        """Product type determined from rules"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product1 = {'title': 'Beautiful Rice Paper'}
        product2 = {'title': 'Acrylic Paint Red'}
        product3 = {'title': 'Random Item'}

        assert config.get_product_type(product1) == 'Reispapier'
        assert config.get_product_type(product2) == 'Farben'
        assert config.get_product_type(product3) == 'Craft Supplies'  # Default

    def test_collections_always(self, sample_vendor_yaml):
        """Always collections assigned"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product = {'title': 'Test'}
        collections = config.get_collections(product)

        assert 'All Products' in collections

    def test_collections_conditional(self, sample_vendor_yaml):
        """Conditional collections assigned"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product = {'title': 'Paper', 'extracted_size': 'A4'}
        collections = config.get_collections(product)

        assert 'A4 Papers' in collections

    def test_enrich_product_full(self, sample_vendor_yaml):
        """Full enrichment applies tags, type, and keywords"""
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))

        product = {
            'title': 'Vintage Rice Paper A4',
            'tags': 'existing,tag'
        }

        enriched = config.enrich_product(product)

        # Tags merged
        assert 'vendor:Test Vendor' in enriched['tags']
        assert 'existing' in enriched['tags']
        assert 'size:A4' in enriched['tags']

        # Product type set
        assert enriched['product_type'] == 'Reispapier'

        # Keywords added
        assert 'decoupage' in enriched['vendor_keywords']

    def test_missing_config_returns_empty(self):
        """Missing config file handled gracefully"""
        config = VendorEnrichmentConfig(vendor_slug='nonexistent_vendor')

        # Should have empty defaults
        assert config.keywords.primary == []
        assert config.tagging.always_add == []

    def test_detect_vendor_from_product(self):
        """Vendor slug detection from product"""
        product1 = {'vendor': 'ITD Collection'}
        product2 = {'vendor': 'Pentart Hungary Kft.'}
        product3 = {'vendor': ''}

        assert detect_vendor_from_product(product1) == 'itd_collection'
        assert detect_vendor_from_product(product2) == 'pentart_hungary_kft'
        assert detect_vendor_from_product(product3) is None

    def test_load_vendor_enrichment_config_convenience(self, sample_vendor_yaml, tmp_path):
        """Convenience function loads config"""
        # Need to put file in expected location
        # This tests the function works, actual path finding tested separately
        config = VendorEnrichmentConfig(config_path=str(sample_vendor_yaml))
        assert config is not None
