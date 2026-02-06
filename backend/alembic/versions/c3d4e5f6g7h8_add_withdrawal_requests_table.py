"""Add withdrawal_requests table

Tracks TON withdrawal requests for:
- User withdrawal management
- Operator batch processing
- Audit trail

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-06 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create withdrawal_requests table."""
    op.create_table(
        'withdrawal_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('ton_address', sa.String(68), nullable=False),
        sa.Column('amount_nanoton', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('tx_hash', sa.String(64), nullable=True, unique=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('ledger_entry_id', sa.Integer(), sa.ForeignKey('ledger.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        # Constraints
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name='withdrawal_valid_status'
        ),
        sa.CheckConstraint('amount_nanoton > 0', name='withdrawal_positive_amount'),
    )

    # Indexes
    op.create_index('ix_withdrawal_requests_id', 'withdrawal_requests', ['id'])
    op.create_index('ix_withdrawal_requests_user_id', 'withdrawal_requests', ['user_id'])
    op.create_index('ix_withdrawal_requests_status', 'withdrawal_requests', ['status'])
    op.create_index('idx_withdrawal_status_created', 'withdrawal_requests', ['status', 'created_at'])
    op.create_index('idx_withdrawal_user_status', 'withdrawal_requests', ['user_id', 'status'])


def downgrade() -> None:
    """Drop withdrawal_requests table."""
    op.drop_index('idx_withdrawal_user_status', table_name='withdrawal_requests')
    op.drop_index('idx_withdrawal_status_created', table_name='withdrawal_requests')
    op.drop_index('ix_withdrawal_requests_status', table_name='withdrawal_requests')
    op.drop_index('ix_withdrawal_requests_user_id', table_name='withdrawal_requests')
    op.drop_index('ix_withdrawal_requests_id', table_name='withdrawal_requests')
    op.drop_table('withdrawal_requests')
