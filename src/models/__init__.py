"""
SQLAlchemy models and database utilities.

This module provides:
- db: SQLAlchemy instance with naming convention for Alembic
- TimestampMixin: Reusable mixin for created_at/updated_at timestamps
"""
from datetime import datetime, timezone
from sqlalchemy import MetaData
from flask_sqlalchemy import SQLAlchemy

# Naming convention for auto-generated constraints (required for Alembic)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


# Import all models for Alembic migration detection
from src.models.user import User, UserTier, AccountStatus
from src.models.oauth_attempt import OAuthAttempt
from src.models.shopify import ShopifyStore, ShopifyCredential
from src.models.vendor import Vendor, VendorCatalogItem
from src.models.product import Product, ProductEnrichment, ProductImage
from src.models.job import Job, JobResult, JobStatus, JobType
from src.models.ingest_chunk import IngestChunk, IngestChunkStatus
from src.models.audit_checkpoint import AuditCheckpoint, AuditDispatchStatus
from src.models.resolution_batch import ResolutionBatch, ResolutionItem, ResolutionChange
from src.models.resolution_rule import ResolutionRule
from src.models.resolution_snapshot import ResolutionSnapshot
from src.models.recovery_log import RecoveryLog
from src.models.chat_session import ChatSession
from src.models.chat_message import ChatMessage
from src.models.chat_action import ChatAction


__all__ = [
    'db',
    'TimestampMixin',
    # User models
    'User',
    'UserTier',
    'AccountStatus',
    'OAuthAttempt',
    # Shopify models
    'ShopifyStore',
    'ShopifyCredential',
    # Vendor models
    'Vendor',
    'VendorCatalogItem',
    # Product models
    'Product',
    'ProductEnrichment',
    'ProductImage',
    # Job models
    'Job',
    'JobResult',
    'JobStatus',
    'JobType',
    'IngestChunk',
    'IngestChunkStatus',
    'AuditCheckpoint',
    'AuditDispatchStatus',
    'ResolutionBatch',
    'ResolutionItem',
    'ResolutionChange',
    'ResolutionRule',
    'ResolutionSnapshot',
    'RecoveryLog',
    'ChatSession',
    'ChatMessage',
    'ChatAction',
]
