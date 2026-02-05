"""BigInteger for telegram_id and volume

Fixes overflow risk:
- telegram_id: Telegram IDs can exceed 2^31 (Integer max)
- volume: High-volume markets can exceed ~21.5M kopecks

Revision ID: a1b2c3d4e5f6
Revises: 5fa554c56c45
Create Date: 2026-02-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5fa554c56c45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: Integer -> BigInteger for telegram_id and volume."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'telegram_id',
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('markets') as batch_op:
        batch_op.alter_column(
            'volume',
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade: BigInteger -> Integer (data loss possible if values > 2^31)."""
    with op.batch_alter_table('markets') as batch_op:
        batch_op.alter_column(
            'volume',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True,
        )

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'telegram_id',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
