"""
User model for multi-tenant platform.

Each user has:
- Authentication credentials (email, password_hash)
- Subscription tier (free, pro, enterprise)
- One-to-one relationship with ShopifyStore (v1.0)
- One-to-many relationships with Vendors and Jobs
"""
from sqlalchemy import String, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from src.models import db, TimestampMixin
import enum


class UserTier(enum.Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(db.Model, TimestampMixin):
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
        default=UserTier.FREE,
        nullable=False,
        index=True
    )

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
        return f'<User {self.email} tier={self.tier.value}>'
