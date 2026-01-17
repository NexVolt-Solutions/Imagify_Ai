"""add login tracking fields

Revision ID: 266f08311d7a
Revises: c2fa3fb7a67d
Create Date: 2025-12-17 16:12:46.690962
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '266f08311d7a'
down_revision: Union[str, Sequence[str], None] = 'c2fa3fb7a67d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('last_login_ip', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('last_login_device', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_login_device')
    op.drop_column('users', 'last_login_ip')
