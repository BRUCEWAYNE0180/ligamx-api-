"""agrega tabla player_match_stats

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-30 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'player_match_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('player_id', sa.Integer(), nullable=True),
        sa.Column('player_name', sa.String(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('team_name', sa.String(), nullable=True),
        sa.Column('season', sa.String(), nullable=True),
        sa.Column('starter', sa.Integer(), nullable=True),
        sa.Column('minutes', sa.Integer(), nullable=True),
        sa.Column('goals', sa.Integer(), nullable=True),
        sa.Column('assists', sa.Integer(), nullable=True),
        sa.Column('shots', sa.Integer(), nullable=True),
        sa.Column('xg', sa.Float(), nullable=True),
        sa.Column('xa', sa.Float(), nullable=True),
        sa.Column('key_passes', sa.Integer(), nullable=True),
        sa.Column('touches', sa.Integer(), nullable=True),
        sa.Column('passes_completed', sa.Integer(), nullable=True),
        sa.Column('passes_attempted', sa.Integer(), nullable=True),
        sa.Column('interceptions', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('stats', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_player_match_stats_id'), 'player_match_stats', ['id'], unique=False)
    op.create_index(op.f('ix_player_match_stats_match_id'), 'player_match_stats', ['match_id'], unique=False)
    op.create_index(op.f('ix_player_match_stats_player_id'), 'player_match_stats', ['player_id'], unique=False)
    op.create_index(op.f('ix_player_match_stats_player_name'), 'player_match_stats', ['player_name'], unique=False)
    op.create_index(op.f('ix_player_match_stats_season'), 'player_match_stats', ['season'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_player_match_stats_season'), table_name='player_match_stats')
    op.drop_index(op.f('ix_player_match_stats_player_name'), table_name='player_match_stats')
    op.drop_index(op.f('ix_player_match_stats_player_id'), table_name='player_match_stats')
    op.drop_index(op.f('ix_player_match_stats_match_id'), table_name='player_match_stats')
    op.drop_index(op.f('ix_player_match_stats_id'), table_name='player_match_stats')
    op.drop_table('player_match_stats')
