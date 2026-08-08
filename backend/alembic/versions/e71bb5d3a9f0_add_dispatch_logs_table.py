"""add dispatch_logs table

Revision ID: e71bb5d3a9f0
Revises: 5f3a9b2c1d4e
Create Date: 2026-08-08 23:59:04.890859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e71bb5d3a9f0'
down_revision: Union[str, None] = '5f3a9b2c1d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dispatch_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('dispatch_type', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['users.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dispatch_logs_id'), 'dispatch_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_dispatch_logs_id'), table_name='dispatch_logs')
    op.drop_table('dispatch_logs')
