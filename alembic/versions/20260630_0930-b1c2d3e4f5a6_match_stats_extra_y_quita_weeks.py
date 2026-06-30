"""amplia match_stats y elimina la tabla muerta weeks

Revision ID: b1c2d3e4f5a6
Revises: 806ef25d4654
Create Date: 2026-06-30 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = '806ef25d4654'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EXTRA_STAT_COLUMNS = [
    "offsides", "saves", "passes", "total_passes", "tackles",
    "interceptions", "blocked_shots", "crosses", "long_balls",
]


def upgrade() -> None:
    # 1) Metricas adicionales por partido (ya se raspaban de ESPN pero se perdian).
    with op.batch_alter_table('match_stats', schema=None) as batch_op:
        for col in _EXTRA_STAT_COLUMNS:
            batch_op.add_column(sa.Column(col, sa.Integer(), nullable=True))

    # 2) La tabla 'weeks' y matches.week_id nunca se poblaban (se usa week_number).
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_column('week_id')
    op.drop_table('weeks')


def downgrade() -> None:
    op.create_table(
        'weeks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=True),
        sa.Column('week_number', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_weeks_id', 'weeks', ['id'], unique=False)

    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('week_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_matches_week_id_weeks', 'weeks', ['week_id'], ['id'])

    with op.batch_alter_table('match_stats', schema=None) as batch_op:
        for col in reversed(_EXTRA_STAT_COLUMNS):
            batch_op.drop_column(col)
