"""
User model for multi-tenant platform.

Each user has:
- Authentication credentials (email, password_hash)
- Subscription tier (free, pro, enterprise)
- One-to-one relationship with ShopifyStore (v1.0)
- One-to-many relationships with Vendors and Jobs
"""
from sqlalchemy import String, Enum as SQLEnum, Integer, Boolean, DateTime
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from src.models import db, TimestampMixin
import enum


class UserTier(enum.Enum):
    """User subscription tiers."""
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class AccountStatus(enum.Enum):
    """User account status for OAuth flow."""
    PENDING_OAUTH = "pending_oauth"
    ACTIVE = "active"
    INCOMPLETE = "incomplete"
    SUSPENDED = "suspended"


class User(db.Model, UserMixin, TimestampMixin):
    """
    User model for authentication and tenant isolation.

    Each user represents a separate tenant with isolated data.
    v1.0: One Shopify store per user (multi-store in v2.0).
    """
    __tablename__ = 'users'

    id = db.Column(Integer, primary_key=True)
    email = db.Column(String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(String(255), nullable=False)
    tier = db.Column(
        SQLEnum(UserTier, name='user_tier', create_constraint=True),
        default=UserTier.TIER_1,
        nullable=False,
        index=True
    )

    # Authentication status
    account_status = db.Column(
        SQLEnum(AccountStatus, name='account_status', create_constraint=True),
        default=AccountStatus.PENDING_OAUTH,
        nullable=False,
        index=True
    )
    email_verified = db.Column(Boolean, default=False, nullable=False)
    email_verification_token = db.Column(String(255), nullable=True)

    # OAuth tracking
    oauth_attempts = db.Column(Integer, default=0, nullable=False)
    last_oauth_attempt = db.Column(DateTime, nullable=True)
    oauth_completion_deadline = db.Column(DateTime, nullable=True)

    # Tier change tracking
    pending_tier = db.Column(
        SQLEnum(UserTier, name='pending_user_tier', create_constraint=True),
        nullable=True
    )
    tier_change_effective_date = db.Column(DateTime, nullable=True)

    # Billing cycle tracking
    billing_period_start = db.Column(DateTime, nullable=True)
    billing_period_end = db.Column(DateTime, nullable=True)

    # Stripe integration
    stripe_customer_id = db.Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = db.Column(String(255), unique=True, nullable=True)
    stripe_subscription_item_id = db.Column(String(255), nullable=True)

    # API versioning
    api_version = db.Column(String(10), default='v1', nullable=False, index=True)
    api_version_locked_until = db.Column(DateTime(timezone=True), nullable=True)

    # Relationships (one-to-one with ShopifyStore for v1.0)
    shopify_store = relationship(
        'ShopifyStore',
        back_populates='user',
        uselist=False,  # One-to-one
        cascade='all, delete-orphan'
    )

    # One-to-many relationships
    vendors = relationship(
        'Vendor',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic'  # For efficient filtering
    )

    jobs = relationship(
        'Job',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic',
        order_by='Job.created_at.desc()'
    )

    def __repr__(self):
        return f'<User {self.email} tier={self.tier.value} status={self.account_status.value}>'

    @property
    def is_active(self):
        """
        Flask-Login checks this to allow/deny login.

        Users must be able to log in before OAuth completion (PENDING_OAUTH),
        so only suspended accounts are denied at session level.
        """
        return self.account_status != AccountStatus.SUSPENDED

    def set_password(self, plaintext_password: str) -> None:
        """Hash password with bcrypt before storing."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        self.password_hash = bcrypt.generate_password_hash(plaintext_password).decode('utf-8')

    def check_password(self, plaintext_password: str) -> bool:
        """Verify password against hash (timing-safe comparison)."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        return bcrypt.check_password_hash(self.password_hash, plaintext_password)
