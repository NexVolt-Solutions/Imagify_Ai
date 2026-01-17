from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '30e46afdf0a1'
down_revision = '182d715a148a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("wallpapers") as batch_op:
        batch_op.drop_column("title")
        batch_op.drop_column("ai_model")
        batch_op.drop_column("thumbnail_url")


def downgrade():
    with op.batch_alter_table("wallpapers") as batch_op:
        batch_op.add_column(sa.Column("title", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("ai_model", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_url", sa.String(255), nullable=True))
