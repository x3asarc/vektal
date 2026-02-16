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
from src.models.product_change_event import ProductChangeEvent
from src.models.vendor_field_mapping import VendorFieldMapping
from src.models.product_enrichment_run import ProductEnrichmentRun
from src.models.product_enrichment_item import ProductEnrichmentItem
from src.models.chat_session import ChatSession
from src.models.chat_message import ChatMessage
from src.models.chat_action import ChatAction
from src.models.assistant_tool_registry import AssistantToolRegistry
from src.models.assistant_tenant_tool_policy import AssistantTenantToolPolicy
from src.models.assistant_profile import AssistantProfile
from src.models.assistant_memory_fact import AssistantMemoryFact
from src.models.assistant_memory_embedding import AssistantMemoryEmbedding
from src.models.assistant_route_event import AssistantRouteEvent
from src.models.assistant_delegation_event import AssistantDelegationEvent
from src.models.assistant_runtime_policy import AssistantRuntimePolicy
from src.models.assistant_execution_ledger import AssistantExecutionLedger
from src.models.assistant_verification_event import AssistantVerificationEvent
from src.models.assistant_kill_switch import AssistantKillSwitch
from src.models.assistant_field_policy import AssistantFieldPolicy
from src.models.assistant_deployment_policy import AssistantDeploymentPolicy
from src.models.assistant_provider_route_event import AssistantProviderRouteEvent
from src.models.assistant_preference_signal import AssistantPreferenceSignal
from src.models.assistant_verification_signal import AssistantVerificationSignal


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
    'ProductChangeEvent',
    'VendorFieldMapping',
    'ProductEnrichmentRun',
    'ProductEnrichmentItem',
    'ChatSession',
    'ChatMessage',
    'ChatAction',
    'AssistantToolRegistry',
    'AssistantTenantToolPolicy',
    'AssistantProfile',
    'AssistantMemoryFact',
    'AssistantMemoryEmbedding',
    'AssistantRouteEvent',
    'AssistantDelegationEvent',
    'AssistantRuntimePolicy',
    'AssistantExecutionLedger',
    'AssistantVerificationEvent',
    'AssistantKillSwitch',
    'AssistantFieldPolicy',
    'AssistantDeploymentPolicy',
    'AssistantProviderRouteEvent',
    'AssistantPreferenceSignal',
    'AssistantVerificationSignal',
]
