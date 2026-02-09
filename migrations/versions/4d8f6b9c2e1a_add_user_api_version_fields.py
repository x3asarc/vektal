"""Add user API version fields

Revision ID: 4d8f6b9c2e1a
Revises: 3c9b2f7d5a1e
Create Date: 2026-02-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4d8f6b9c2e1a'
down_revision = '3c9b2f7d5a1e'
branch_labels = None
depends_on = None


def upgrade():
    """Add api_version and api_version_locked_until fields to users table."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Add api_version column with temporary server default for backfill
    if dialect == 'postgresql':
        op.add_column('users', sa.Column('api_version', sa.String(length=10), server_default='v1', nullable=False))
    else:
        op.add_column('users', sa.Column('api_version', sa.String(length=10), nullable=False))

    # Add api_version_locked_until column (nullable)
    if dialect == 'postgresql':
        op.add_column('users', sa.Column('api_version_locked_until', sa.DateTime(timezone=True), nullable=True))
    else:
        op.add_column('users', sa.Column('api_version_locked_until', sa.DateTime(), nullable=True))

    # Create index on api_version for efficient filtering
    op.create_index(op.f('ix_users_api_version'), 'users', ['api_version'], unique=False)

    # Add check constraint to enforce valid API versions
    if dialect == 'postgresql':
        op.create_check_constraint(
            'ck_users_api_version',
            'users',
            "api_version IN ('v1', 'v2')"
        )

    # Remove server default after backfill (application-level default is canonical)
    if dialect == 'postgresql':
        op.alter_column('users', 'api_version', server_default=None)


def downgrade():
    """Remove api_version and api_version_locked_until fields from users table."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Drop check constraint
    if dialect == 'postgresql':
        op.drop_constraint('ck_users_api_version', 'users', type_='check')

    # Drop index
    op.drop_index(op.f('ix_users_api_version'), table_name='users')

    # Drop columns
    op.drop_column('users', 'api_version_locked_until')
    op.drop_column('users', 'api_version')
