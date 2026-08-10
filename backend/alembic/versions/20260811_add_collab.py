"""add ticket_collaborations table

Revision ID: 20260811_add_collab
Revises: 20260811_add_satisfaction_at
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260811_add_collab'
down_revision: Union[str, None] = '20260811_add_satisfaction_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ticket_collaborations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('from_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('to_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('ticket_collaborations')
