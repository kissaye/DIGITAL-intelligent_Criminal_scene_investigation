"""Align case metadata with M1 frontend contract."""
from alembic import op
import sqlalchemy as sa

revision = "202610280003"
down_revision = "202610280002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.add_column(sa.Column("internal_code", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("teaching_title", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("case_type", sa.String(length=64), nullable=False, server_default="OTHER"))
        batch.add_column(sa.Column("difficulty", sa.String(length=32), nullable=False, server_default="BEGINNER"))
        batch.add_column(sa.Column("course_tags", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("desensitization_level", sa.String(length=32), nullable=False, server_default="NONE"))
    op.execute("UPDATE cases SET internal_code = id, teaching_title = title WHERE internal_code IS NULL OR teaching_title IS NULL")
    with op.batch_alter_table("cases") as batch:
        batch.alter_column("internal_code", nullable=False)
        batch.alter_column("teaching_title", nullable=False)
        batch.create_unique_constraint("uq_cases_internal_code", ["internal_code"])
        batch.create_index("ix_cases_internal_code", ["internal_code"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.drop_index("ix_cases_internal_code")
        batch.drop_constraint("uq_cases_internal_code", type_="unique")
        batch.drop_column("desensitization_level")
        batch.drop_column("valid_until")
        batch.drop_column("course_tags")
        batch.drop_column("difficulty")
        batch.drop_column("case_type")
        batch.drop_column("teaching_title")
        batch.drop_column("internal_code")
