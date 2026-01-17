"""expand wallpaperstatusenum with staged statuses

Revision ID: bfa3e6c0c80f
Revises: 266f08311d7a
Create Date: 2025-12-23 06:27:20.775428
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bfa3e6c0c80f'
down_revision: Union[str, Sequence[str], None] = '266f08311d7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add new enum values for staged statuses."""
    op.execute("ALTER TYPE wallpaperstatusenum ADD VALUE IF NOT EXISTS 'preparing'")
    op.execute("ALTER TYPE wallpaperstatusenum ADD VALUE IF NOT EXISTS 'rendering'")
    op.execute("ALTER TYPE wallpaperstatusenum ADD VALUE IF NOT EXISTS 'retrying'")
    op.execute("ALTER TYPE wallpaperstatusenum ADD VALUE IF NOT EXISTS 'finalizing'")


def downgrade() -> None:
    """Downgrade schema: recreate enum without staged statuses."""
    # Rename the current type
    op.execute("ALTER TYPE wallpaperstatusenum RENAME TO wallpaperstatusenum_old")

    # Recreate the original enum type
    sa.Enum(
        "pending",
        "completed",
        "failed",
        name="wallpaperstatusenum"
    ).create(op.get_bind(), checkfirst=False)

    # Alter the column back to the recreated type
    op.execute(
        "ALTER TABLE wallpapers ALTER COLUMN status TYPE wallpaperstatusenum USING status::text::wallpaperstatusenum"
    )

    # Drop the old type
    op.execute("DROP TYPE wallpaperstatusenum_old")
