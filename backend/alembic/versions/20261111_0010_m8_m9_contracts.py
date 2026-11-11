"""M8.3 report contract / M9.1 measurement labels.

Revision ID: 202611110010
Revises: 202611050009
"""
from alembic import op
import sqlalchemy as sa

revision = "202611110010"
down_revision = "202611050009"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("measurements", "submission_measurements"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("title", sa.String(length=200), nullable=True))
            batch.add_column(sa.Column("description", sa.Text(), nullable=True))


def downgrade():
    for table in ("submission_measurements", "measurements"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("description")
            batch.drop_column("title")
