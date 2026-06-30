"""agrega external_365_id a players

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-30 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.add_column(sa.Column('external_365_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_players_external_365_id', ['external_365_id'])


def downgrade() -> None:
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_index('ix_players_external_365_id')
        batch_op.drop_column('external_365_id')
