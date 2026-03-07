"""
Shopify integration models.

ShopifyStore: One-to-one with User, stores encrypted OAuth token
ShopifyCredential: Additional API keys and secrets for Shopify API access
"""
from sqlalchemy import String, Integer, LargeBinary, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.models import db, TimestampMixin


class ShopifyStore(db.Model, TimestampMixin):
    """
    Shopify store configuration with encrypted OAuth token.

    One-to-one with User (v1.0 requirement).
    OAuth access token stored encrypted using Fernet.
    """
    __tablename__ = 'shopify_stores'

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,  # One store per user for v1.0
        nullable=False,
        index=True
    )

    # Store identification
    shop_domain = db.Column(String(255), unique=True, nullable=False, index=True)
    shop_name = db.Column(String(255))

    # Encrypted OAuth token (using Fernet encryption)
    access_token_encrypted = db.Column(LargeBinary, nullable=False)

    # Store status
    is_active = db.Column(Boolean, default=True, nullable=False)

    # Ingest watermarks (Phase 17)
    last_full_ingest_at = db.Column(db.DateTime(timezone=True))
    last_shopify_cursor = db.Column(String(255))

    # Relationships
    user = relationship('User', back_populates='shopify_store')

    products = relationship(
        'Product',
        back_populates='store',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def set_access_token(self, plaintext_token: str) -> None:
        """
        Encrypt and store Shopify OAuth access token.

        Args:
            plaintext_token: Unencrypted OAuth token from Shopify
        """
        # Deferred import to avoid circular dependency
        from src.core.encryption import encrypt_token
        self.access_token_encrypted = encrypt_token(plaintext_token)

    def get_access_token(self) -> str:
        """
        Decrypt and return Shopify OAuth access token.

        Returns:
            Plaintext OAuth token for Shopify API requests

        Raises:
            ValueError: If token is not set
        """
        if not self.access_token_encrypted:
            raise ValueError(f"No access token set for store {self.shop_domain}")

        # Deferred import to avoid circular dependency
        from src.core.encryption import decrypt_token
        return decrypt_token(self.access_token_encrypted)

    def __repr__(self):
        return f'<ShopifyStore {self.shop_domain} user_id={self.user_id}>'


class ShopifyCredential(db.Model, TimestampMixin):
    """
    Additional Shopify API credentials (API keys, webhook secrets, etc.).

    Supports multiple credential types per store for different integrations.
    """
    __tablename__ = 'shopify_credentials'

    id = db.Column(Integer, primary_key=True)
    store_id = db.Column(
        Integer,
        ForeignKey('shopify_stores.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Credential metadata
    credential_type = db.Column(
        String(50),
        nullable=False,
        index=True
    )  # e.g., 'api_key', 'webhook_secret', 'storefront_token'

    credential_name = db.Column(String(255))  # Human-readable name

    # Encrypted credential value
    credential_value_encrypted = db.Column(LargeBinary, nullable=False)

    # Status
    is_active = db.Column(Boolean, default=True, nullable=False)

    # Relationships
    store = relationship('ShopifyStore', backref='credentials')

    def set_credential(self, plaintext_value: str) -> None:
        """
        Encrypt and store credential value.

        Args:
            plaintext_value: Unencrypted credential
        """
        from src.core.encryption import encrypt_token
        self.credential_value_encrypted = encrypt_token(plaintext_value)

    def get_credential(self) -> str:
        """
        Decrypt and return credential value.

        Returns:
            Plaintext credential value

        Raises:
            ValueError: If credential is not set
        """
        if not self.credential_value_encrypted:
            raise ValueError(f"No credential value set for {self.credential_type}")

        from src.core.encryption import decrypt_token
        return decrypt_token(self.credential_value_encrypted)

    def __repr__(self):
        return f'<ShopifyCredential {self.credential_type} store_id={self.store_id}>'
