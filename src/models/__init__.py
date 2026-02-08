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


__all__ = ['db', 'TimestampMixin']
