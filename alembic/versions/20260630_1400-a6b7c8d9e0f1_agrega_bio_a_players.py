"""agrega bio (flag_url, height, weight) a players

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-30 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.add_column(sa.Column('flag_url', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('height', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('weight', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_column('weight')
        batch_op.drop_column('height')
        batch_op.drop_column('flag_url')
