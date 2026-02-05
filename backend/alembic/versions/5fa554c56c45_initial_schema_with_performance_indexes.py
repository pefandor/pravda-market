"""Initial schema with performance indexes

Revision ID: 5fa554c56c45
Revises:
Create Date: 2026-02-02 18:01:04.969990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fa554c56c45'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables and indexes."""

    # 1. Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('telegram_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)

    # 2. Markets table
    op.create_table(
        'markets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=False),
        sa.Column('resolved', sa.Boolean(), server_default='false'),
        sa.Column('resolution_value', sa.Boolean(), nullable=True),
        sa.Column('outcome', sa.String(10), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('yes_price', sa.Integer(), server_default='5000'),
        sa.Column('no_price', sa.Integer(), server_default='5000'),
        sa.Column('volume', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_markets_id', 'markets', ['id'])
    op.create_index('ix_markets_category', 'markets', ['category'])
    op.create_index('ix_markets_resolved', 'markets', ['resolved'])

    # 3. Orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('market_id', sa.Integer(), sa.ForeignKey('markets.id'), nullable=False),
        sa.Column('side', sa.String(3), nullable=False),
        sa.Column('price_bp', sa.Integer(), nullable=False),
        sa.Column('amount_kopecks', sa.BigInteger(), nullable=False),
        sa.Column('filled_kopecks', sa.BigInteger(), server_default='0'),
        sa.Column('status', sa.String(20), server_default="'open'"),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('price_bp >= 0 AND price_bp <= 10000', name='valid_price'),
        sa.CheckConstraint('amount_kopecks > 0', name='positive_amount'),
        sa.CheckConstraint("side IN ('yes', 'no')", name='valid_side'),
        sa.CheckConstraint("status IN ('open', 'partial', 'filled', 'cancelled')", name='valid_status'),
    )
    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])
    op.create_index('ix_orders_market_id', 'orders', ['market_id'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_matching', 'orders', ['market_id', 'side', 'price_bp', 'created_at'])

    # 4. Ledger table
    op.create_table(
        'ledger',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount_kopecks', sa.BigInteger(), nullable=False),
        sa.Column('type', sa.String(30), nullable=False),
        sa.Column('reference_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ledger_id', 'ledger', ['id'])
    op.create_index('ix_ledger_user_id', 'ledger', ['user_id'])
    op.create_index('ix_ledger_type', 'ledger', ['type'])
    op.create_index('idx_ledger_user_type', 'ledger', ['user_id', 'type'])

    # 5. Trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('market_id', sa.Integer(), sa.ForeignKey('markets.id'), nullable=False),
        sa.Column('yes_order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('no_order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('price_bp', sa.Integer(), nullable=False),
        sa.Column('amount_kopecks', sa.BigInteger(), nullable=False),
        sa.Column('yes_cost_kopecks', sa.BigInteger(), nullable=False),
        sa.Column('no_cost_kopecks', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('price_bp >= 0 AND price_bp <= 10000', name='trade_valid_price'),
        sa.CheckConstraint('amount_kopecks > 0', name='trade_positive_amount'),
        sa.CheckConstraint('yes_cost_kopecks >= 0', name='trade_positive_yes_cost'),
        sa.CheckConstraint('no_cost_kopecks >= 0', name='trade_positive_no_cost'),
        sa.CheckConstraint('yes_cost_kopecks + no_cost_kopecks = amount_kopecks', name='trade_settlement_invariant'),
    )
    op.create_index('ix_trades_id', 'trades', ['id'])
    op.create_index('ix_trades_market_id', 'trades', ['market_id'])
    op.create_index('ix_trades_created_at', 'trades', ['created_at'])
    op.create_index('idx_trades_market_created', 'trades', ['market_id', 'created_at'])
    op.create_index('idx_trades_yes_order', 'trades', ['yes_order_id'])
    op.create_index('idx_trades_no_order', 'trades', ['no_order_id'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('trades')
    op.drop_table('ledger')
    op.drop_table('orders')
    op.drop_table('markets')
    op.drop_table('users')
