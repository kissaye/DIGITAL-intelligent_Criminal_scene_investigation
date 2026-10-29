"""Create M2 annotations and measurements."""
from alembic import op
import sqlalchemy as sa

revision = "202610290004"
down_revision = "202610280003"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("annotations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_version_id", sa.String(36), nullable=False), sa.Column("owner_id", sa.Integer(), nullable=False), sa.Column("scope", sa.String(40), nullable=False), sa.Column("type", sa.String(20), nullable=False), sa.Column("geometry", sa.JSON(), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("viewer_state", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["case_version_id"],["case_versions.id"],ondelete="CASCADE"), sa.ForeignKeyConstraint(["owner_id"],["users.id"],ondelete="CASCADE"))
    op.create_index("ix_annotations_case_version_id", "annotations", ["case_version_id"]); op.create_index("ix_annotations_owner_id", "annotations", ["owner_id"])
    op.create_table("measurements", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_version_id", sa.String(36), nullable=False), sa.Column("owner_id", sa.Integer(), nullable=False), sa.Column("start_point", sa.JSON(), nullable=False), sa.Column("end_point", sa.JSON(), nullable=False), sa.Column("distance", sa.Float(), nullable=False), sa.Column("viewer_state", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["case_version_id"],["case_versions.id"],ondelete="CASCADE"), sa.ForeignKeyConstraint(["owner_id"],["users.id"],ondelete="CASCADE"))
    op.create_index("ix_measurements_case_version_id", "measurements", ["case_version_id"]); op.create_index("ix_measurements_owner_id", "measurements", ["owner_id"])

def downgrade() -> None:
    op.drop_table("measurements"); op.drop_table("annotations")
