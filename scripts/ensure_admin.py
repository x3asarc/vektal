from src.api.app import create_openapi_app
from src.models import db, User, UserTier, AccountStatus, ShopifyStore
from src.core.encryption import encrypt_token

def ensure_admin():
    app = create_openapi_app()
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email="admin@station.com").first()
        if not admin:
            admin = User(
                email="admin@station.com",
                tier=UserTier.TIER_3,
                account_status=AccountStatus.ACTIVE,
                email_verified=True,
                api_version="v1"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin@station.com / admin123")
        else:
            admin.set_password("admin123")
            admin.account_status = AccountStatus.ACTIVE
            db.session.commit()
            print("Admin user password reset: admin@station.com / admin123")

        # Ensure a mock store exists for this admin to see the dashboard
        if not admin.shopify_store:
            store = ShopifyStore(
                user_id=admin.id,
                shop_domain="station-dev.myshopify.com",
                shop_name="Station Dev Store",
                access_token_encrypted=encrypt_token("mock_token"),
                is_active=True
            )
            db.session.add(store)
            db.session.commit()
            print("Mock store created for admin.")

if __name__ == "__main__":
    ensure_admin()
