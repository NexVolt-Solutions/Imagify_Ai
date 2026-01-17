"""add google sign-in fields to users

Revision ID: 7a3e699f13b2
Revises: bfa3e6c0c80f
Create Date: 2025-12-30 05:36:19.934250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a3e699f13b2"
down_revision: Union[str, Sequence[str], None] = "bfa3e6c0c80f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("last_google_id_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("google_picture", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "last_google_id_token")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "google_picture")


