"""add max_concurrent_tickets to users

Revision ID: 20260821_add_max_concurrent
Revises: 20260811_add_collab
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260821_add_max_concurrent'
down_revision: Union[str, None] = '20260811_add_collab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('max_concurrent_tickets', sa.Integer(), nullable=False, server_default='5'))


def downgrade() -> None:
    op.drop_column('users', 'max_concurrent_tickets')
