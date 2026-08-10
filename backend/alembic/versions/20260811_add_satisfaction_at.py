"""add satisfaction_at to tickets

Revision ID: 20260811_add_satisfaction_at
Revises: 40164b94b52f
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260811_add_satisfaction_at'
down_revision: Union[str, None] = '40164b94b52f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('satisfaction_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('tickets', 'satisfaction_at')
