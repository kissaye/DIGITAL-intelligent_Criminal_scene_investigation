"""Create M9.2 area measurement tables."""
from alembic import op
import sqlalchemy as sa

revision = "202611110011"
down_revision = "202611110010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("area_measurements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_version_id", sa.String(36), sa.ForeignKey("case_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("points", sa.JSON(), nullable=False), sa.Column("perimeter", sa.Float(), nullable=False), sa.Column("area", sa.Float(), nullable=False),
        sa.Column("title", sa.String(200)), sa.Column("description", sa.Text()), sa.Column("viewer_state", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_index("ix_area_measurements_version", "area_measurements", ["case_version_id"])
    op.create_index("ix_area_measurements_owner", "area_measurements", ["owner_id"])
    op.create_table("submission_area_measurements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("points", sa.JSON(), nullable=False), sa.Column("perimeter", sa.Float(), nullable=False), sa.Column("area", sa.Float(), nullable=False),
        sa.Column("title", sa.String(200)), sa.Column("description", sa.Text()), sa.Column("viewer_state", sa.JSON()))
    op.create_index("ix_submission_area_measurements_submission", "submission_area_measurements", ["submission_id"])


def downgrade():
    op.drop_index("ix_submission_area_measurements_submission", table_name="submission_area_measurements")
    op.drop_table("submission_area_measurements")
    op.drop_index("ix_area_measurements_owner", table_name="area_measurements")
    op.drop_index("ix_area_measurements_version", table_name="area_measurements")
    op.drop_table("area_measurements")
