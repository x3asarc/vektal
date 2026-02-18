"""Add auth fields to users and create oauth_attempts table

Revision ID: 3c9b2f7d5a1e
Revises: e6eec7532bd6
Create Date: 2026-02-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c9b2f7d5a1e'
down_revision = 'e6eec7532bd6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Update user_tier enum values (FREE/PRO/ENTERPRISE -> TIER_1/2/3)
    if dialect == 'postgresql':
        op.execute("ALTER TYPE user_tier RENAME TO user_tier_old")
        user_tier_enum = sa.Enum('TIER_1', 'TIER_2', 'TIER_3', name='user_tier')
        user_tier_enum.create(bind)
        op.execute(
            "ALTER TABLE users ALTER COLUMN tier TYPE user_tier USING "
            "CASE "
            "WHEN tier='FREE' THEN 'TIER_1' "
            "WHEN tier='PRO' THEN 'TIER_2' "
            "WHEN tier='ENTERPRISE' THEN 'TIER_3' "
            "ELSE 'TIER_1' "
            "END::user_tier"
        )
        op.execute("DROP TYPE user_tier_old")
    else:
        user_tier_enum = sa.Enum('TIER_1', 'TIER_2', 'TIER_3', name='user_tier')

    account_status_enum = sa.Enum(
        'PENDING_OAUTH', 'ACTIVE', 'INCOMPLETE', 'SUSPENDED', name='account_status'
    )
    pending_user_tier_enum = sa.Enum('TIER_1', 'TIER_2', 'TIER_3', name='pending_user_tier')

    if dialect == 'postgresql':
        account_status_enum.create(bind)
        pending_user_tier_enum.create(bind)

    # Add auth fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'account_status',
            account_status_enum,
            nullable=False,
            server_default='PENDING_OAUTH'
        ))
        batch_op.add_column(sa.Column(
            'email_verified',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        ))
        batch_op.add_column(sa.Column('email_verification_token', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column(
            'oauth_attempts',
            sa.Integer(),
            nullable=False,
            server_default='0'
        ))
        batch_op.add_column(sa.Column('last_oauth_attempt', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('oauth_completion_deadline', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('pending_tier', pending_user_tier_enum, nullable=True))
        batch_op.add_column(sa.Column('tier_change_effective_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('billing_period_start', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('billing_period_end', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('stripe_customer_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('stripe_subscription_item_id', sa.String(length=255), nullable=True))

        batch_op.create_index(batch_op.f('ix_users_account_status'), ['account_status'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_stripe_customer_id'), ['stripe_customer_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_stripe_subscription_id'), ['stripe_subscription_id'], unique=True)

    # Create oauth_attempts table
    op.create_table(
        'oauth_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('shop_domain', sa.String(length=255), nullable=False),
        sa.Column('state_token', sa.String(length=64), nullable=False),
        sa.Column('result', sa.String(length=50), nullable=False),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_oauth_attempts'))
    )
    with op.batch_alter_table('oauth_attempts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_oauth_attempts_expires_at'), ['expires_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_oauth_attempts_state_token'), ['state_token'], unique=True)
        batch_op.create_index(batch_op.f('ix_oauth_attempts_user_id'), ['user_id'], unique=False)


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table('oauth_attempts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_oauth_attempts_user_id'))
        batch_op.drop_index(batch_op.f('ix_oauth_attempts_state_token'))
        batch_op.drop_index(batch_op.f('ix_oauth_attempts_expires_at'))
    op.drop_table('oauth_attempts')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_stripe_subscription_id'))
        batch_op.drop_index(batch_op.f('ix_users_stripe_customer_id'))
        batch_op.drop_index(batch_op.f('ix_users_account_status'))

        batch_op.drop_column('stripe_subscription_item_id')
        batch_op.drop_column('stripe_subscription_id')
        batch_op.drop_column('stripe_customer_id')
        batch_op.drop_column('billing_period_end')
        batch_op.drop_column('billing_period_start')
        batch_op.drop_column('tier_change_effective_date')
        batch_op.drop_column('pending_tier')
        batch_op.drop_column('oauth_completion_deadline')
        batch_op.drop_column('last_oauth_attempt')
        batch_op.drop_column('oauth_attempts')
        batch_op.drop_column('email_verification_token')
        batch_op.drop_column('email_verified')
        batch_op.drop_column('account_status')

    if dialect == 'postgresql':
        op.execute("DROP TYPE account_status")
        op.execute("DROP TYPE pending_user_tier")

        op.execute("ALTER TYPE user_tier RENAME TO user_tier_new")
        old_user_tier_enum = sa.Enum('FREE', 'PRO', 'ENTERPRISE', name='user_tier')
        old_user_tier_enum.create(bind)
        op.execute(
            "ALTER TABLE users ALTER COLUMN tier TYPE user_tier USING "
            "CASE "
            "WHEN tier='TIER_1' THEN 'FREE' "
            "WHEN tier='TIER_2' THEN 'PRO' "
            "WHEN tier='TIER_3' THEN 'ENTERPRISE' "
            "ELSE 'FREE' "
            "END::user_tier"
        )
        op.execute("DROP TYPE user_tier_new")
