"""add goals table

Revision ID: c8f3a2b1e002
Revises: b71e0a3d0001
Create Date: 2026-08-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8f3a2b1e002'
down_revision: Union[str, None] = 'b71e0a3d0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'goals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('kind', sa.String(), nullable=False, server_default='research'),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('cadence', sa.String(), nullable=False, server_default='0 7 * * *'),
        sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_goals_project_id'), 'goals', ['project_id'], unique=False)
    op.create_index(op.f('ix_goals_status'), 'goals', ['status'], unique=False)
    op.create_index(op.f('ix_goals_kind'), 'goals', ['kind'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_goals_kind'), table_name='goals')
    op.drop_index(op.f('ix_goals_status'), table_name='goals')
    op.drop_index(op.f('ix_goals_project_id'), table_name='goals')
    op.drop_table('goals')
