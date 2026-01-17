"""Remove unused user fields

Revision ID: c2fa3fb7a67d
Revises: 9325bac69bed
Create Date: 2025-12-17 09:44:13.112689
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2fa3fb7a67d'
down_revision: Union[str, Sequence[str], None] = '9325bac69bed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: remove unused user fields."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("first_name")
        batch_op.drop_column("last_name")
        batch_op.drop_column("phone_number")


def downgrade() -> None:
    """Downgrade schema: restore removed fields."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("first_name", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("last_name", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("phone_number", sa.String(length=20), nullable=True))


