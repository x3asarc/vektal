"""Phase 8 resolution pipeline tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.product import Product
from src.models.resolution_batch import ResolutionItem
from src.models.resolution_snapshot import ResolutionSnapshot
from src.models.shopify import ShopifyStore
from src.models.user import AccountStatus, User, UserTier
from src.models.vendor import Vendor, VendorCatalogItem
from src.resolution.contracts import Candidate
from src.resolution.dry_run_compiler import compile_dry_run
from tests.api.conftest import TestConfig


@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed_user_store():
    user = User(
        email="pipeline@example.com",
        tier=UserTier.TIER_1,
        account_status=AccountStatus.ACTIVE,
        email_verified=True,
        api_version="v1",
    )
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()

    store = ShopifyStore(
        user_id=user.id,
        shop_domain="pipeline-test.myshopify.com",
        shop_name="Pipeline Test",
        access_token_encrypted=b"test-token",
        is_active=True,
    )
    db.session.add(store)
    db.session.flush()
    return user, store


def test_source_order_short_circuit_prefers_shopify(app):
    with app.app_context():
        user, store = _seed_user_store()
        product = Product(
            store_id=store.id,
            title="Ceramic Vase",
            sku="SKU-001",
            barcode="111",
            price=10.0,
            is_active=True,
        )
        db.session.add(product)

        vendor = Vendor(user_id=user.id, name="Pentart", code="PENTART", is_active=True)
        db.session.add(vendor)
        db.session.flush()
        db.session.add(
            VendorCatalogItem(
                vendor_id=vendor.id,
                sku="SKU-001",
                barcode="111",
                name="Supplier Ceramic Vase",
                price=15.0,
                is_active=True,
                raw_data={"product_type": "Decor"},
            )
        )
        db.session.commit()

        batch = compile_dry_run(
            user_id=user.id,
            store_id=store.id,
            supplier_code="PENTART",
            supplier_verified=True,
            rows=[{"sku": "SKU-001", "title": "Supplier Ceramic Vase", "price": 15.0}],
        )

        item = ResolutionItem.query.filter_by(batch_id=batch.id).first()
        snapshot = ResolutionSnapshot.query.filter_by(
            batch_id=batch.id,
            item_id=item.id,
            snapshot_type="product_pre_change",
        ).first()
        assert snapshot is not None
        assert (snapshot.payload or {}).get("source_used") == "shopify"


def test_web_source_is_blocked_when_supplier_unverified(app, monkeypatch):
    import src.resolution.dry_run_compiler as compiler

    called = []

    def _fake_web(*args, **kwargs):
        called.append(True)
        return [
            Candidate(
                source="web",
                product_id=None,
                shopify_product_id=None,
                sku="WEB-SKU",
                barcode=None,
                title="Web Product",
                price=None,
                variant_options=[],
                payload={"title": "Web Product"},
            )
        ]

    monkeypatch.setattr(compiler, "search_web_candidates", _fake_web)

    with app.app_context():
        user, store = _seed_user_store()
        compile_dry_run(
            user_id=user.id,
            store_id=store.id,
            supplier_code="UNKNOWN",
            supplier_verified=False,
            rows=[{"sku": "NO-MATCH"}],
        )
        assert called == []


def test_structural_conflict_marks_new_variants_detected(app):
    with app.app_context():
        user, store = _seed_user_store()
        db.session.add(
            Product(
                store_id=store.id,
                title="Paint Set",
                sku="SKU-RED",
                barcode="222",
                price=7.5,
                is_active=True,
            )
        )
        db.session.commit()

        batch = compile_dry_run(
            user_id=user.id,
            store_id=store.id,
            supplier_code="PENTART",
            supplier_verified=True,
            rows=[{"sku": "SKU-RED", "variant_options": ["Red", "Blue"]}],
        )
        item = ResolutionItem.query.filter_by(batch_id=batch.id).first()
        assert item.status == "structural_conflict"
        assert item.structural_state == "new_variants_detected"


def test_dry_run_persists_manifest_and_product_snapshots(app):
    with app.app_context():
        user, store = _seed_user_store()
        db.session.add(
            Product(
                store_id=store.id,
                title="Notebook",
                sku="NB-1",
                barcode="333",
                price=4.2,
                is_active=True,
            )
        )
        db.session.commit()

        batch = compile_dry_run(
            user_id=user.id,
            store_id=store.id,
            supplier_code="PENTART",
            supplier_verified=True,
            rows=[
                {"sku": "NB-1", "price": 5.1},
                {"title": "Unmatched Product", "price": 1.0},
            ],
        )

        manifest = ResolutionSnapshot.query.filter_by(
            batch_id=batch.id,
            snapshot_type="batch_manifest",
        ).first()
        product_snapshots = ResolutionSnapshot.query.filter_by(
            batch_id=batch.id,
            snapshot_type="product_pre_change",
        ).all()
        assert manifest is not None
        assert len(product_snapshots) == 2
