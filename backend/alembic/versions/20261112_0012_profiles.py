"""Create M9.3 profile measurement tables."""
from alembic import op
import sqlalchemy as sa

revision = "202611120012"
down_revision = "202611110011"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("profile_measurements", sa.Column("id", sa.String(36), primary_key=True), sa.Column("case_version_id", sa.String(36), sa.ForeignKey("case_versions.id", ondelete="CASCADE"), nullable=False), sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("points", sa.JSON(), nullable=False), sa.Column("width", sa.Float(), nullable=False), sa.Column("path_length", sa.Float(), nullable=False), sa.Column("title", sa.String(200)), sa.Column("description", sa.Text()), sa.Column("viewer_state", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_index("ix_profile_measurements_version", "profile_measurements", ["case_version_id"])
    op.create_index("ix_profile_measurements_owner", "profile_measurements", ["owner_id"])
    op.create_table("submission_profiles", sa.Column("id", sa.String(36), primary_key=True), sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False), sa.Column("points", sa.JSON(), nullable=False), sa.Column("width", sa.Float(), nullable=False), sa.Column("path_length", sa.Float(), nullable=False), sa.Column("title", sa.String(200)), sa.Column("description", sa.Text()), sa.Column("viewer_state", sa.JSON()))
    op.create_index("ix_submission_profiles_submission", "submission_profiles", ["submission_id"])

def downgrade():
    op.drop_index("ix_submission_profiles_submission", table_name="submission_profiles")
    op.drop_table("submission_profiles")
    op.drop_index("ix_profile_measurements_owner", table_name="profile_measurements")
    op.drop_index("ix_profile_measurements_version", table_name="profile_measurements")
    op.drop_table("profile_measurements")
