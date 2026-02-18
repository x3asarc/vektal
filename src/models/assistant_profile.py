"""Assistant profile model for user/team enabled-skill governance."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantProfile(db.Model, TimestampMixin):
    """Profile contract controlling enabled skills and policy toggles."""

    __tablename__ = "assistant_profiles"
    __table_args__ = (
        CheckConstraint(
            "profile_scope IN ('user', 'team')",
            name="assistant_profile_scope",
        ),
        CheckConstraint(
            "user_id IS NOT NULL OR store_id IS NOT NULL",
            name="assistant_profile_target_present",
        ),
        Index("ix_assistant_profile_user_scope", "user_id", "profile_scope", "is_active"),
        Index("ix_assistant_profile_store_scope", "store_id", "profile_scope", "is_active"),
    )

    id = db.Column(Integer, primary_key=True)
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    profile_scope = db.Column(String(16), nullable=False, default="user")
    name = db.Column(String(128), nullable=True)
    enabled_skill_set = db.Column(JSON, nullable=False, default=list)
    settings_json = db.Column(JSON, nullable=True)
    is_active = db.Column(Boolean, nullable=False, default=True)
    priority = db.Column(Integer, nullable=False, default=0)

    store = relationship("ShopifyStore", backref="assistant_profiles")
    user = relationship("User", backref="assistant_profiles")

    def __repr__(self) -> str:
        return (
            f"<AssistantProfile id={self.id} scope={self.profile_scope} "
            f"user_id={self.user_id} store_id={self.store_id}>"
        )

