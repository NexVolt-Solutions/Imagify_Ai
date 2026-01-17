"""add reset_verified to users

Revision ID: 9325bac69bed
Revises: 30e46afdf0a1
Create Date: 2025-12-17 06:33:43.338452
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9325bac69bed'
down_revision: Union[str, Sequence[str], None] = '30e46afdf0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column(
            'reset_verified',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'reset_verified')
