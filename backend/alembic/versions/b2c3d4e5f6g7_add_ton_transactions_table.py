"""Add ton_transactions table

Tracks TON blockchain deposits for:
- Preventing double-crediting
- Audit trail
- Transaction status monitoring

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-06 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ton_transactions table."""
    op.create_table(
        'ton_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tx_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('lt', sa.BigInteger(), nullable=False),
        sa.Column('sender_address', sa.String(68), nullable=False),
        sa.Column('amount_nanoton', sa.BigInteger(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('ledger_entry_id', sa.Integer(), sa.ForeignKey('ledger.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        # Constraints
        sa.CheckConstraint("status IN ('pending', 'confirmed', 'credited', 'failed')", name='ton_tx_valid_status'),
        sa.CheckConstraint('amount_nanoton > 0', name='ton_tx_positive_amount'),
    )

    # Indexes
    op.create_index('ix_ton_transactions_id', 'ton_transactions', ['id'])
    op.create_index('ix_ton_transactions_tx_hash', 'ton_transactions', ['tx_hash'], unique=True)
    op.create_index('ix_ton_transactions_telegram_id', 'ton_transactions', ['telegram_id'])
    op.create_index('ix_ton_transactions_status', 'ton_transactions', ['status'])
    op.create_index('ix_ton_transactions_user_id', 'ton_transactions', ['user_id'])
    op.create_index('idx_ton_tx_status_created', 'ton_transactions', ['status', 'created_at'])


def downgrade() -> None:
    """Drop ton_transactions table."""
    op.drop_index('idx_ton_tx_status_created', table_name='ton_transactions')
    op.drop_index('ix_ton_transactions_user_id', table_name='ton_transactions')
    op.drop_index('ix_ton_transactions_status', table_name='ton_transactions')
    op.drop_index('ix_ton_transactions_telegram_id', table_name='ton_transactions')
    op.drop_index('ix_ton_transactions_tx_hash', table_name='ton_transactions')
    op.drop_index('ix_ton_transactions_id', table_name='ton_transactions')
    op.drop_table('ton_transactions')
