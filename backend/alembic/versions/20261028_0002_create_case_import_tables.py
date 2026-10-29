"""Create M1 controlled case import tables."""
from alembic import op
import sqlalchemy as sa

revision = "202610280002"
down_revision = "202610280001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("cases", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("title", sa.String(length=200), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("created_by_id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_table("files", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("case_id", sa.String(length=36), nullable=False), sa.Column("storage_key", sa.String(length=512), nullable=False), sa.Column("original_name", sa.String(length=255), nullable=False), sa.Column("mime_type", sa.String(length=100), nullable=False), sa.Column("size_bytes", sa.BigInteger(), nullable=False), sa.Column("checksum_sha256", sa.String(length=64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("storage_key"))
    op.create_index("ix_files_case_id", "files", ["case_id"])
    op.create_table("case_versions", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("case_id", sa.String(length=36), nullable=False), sa.Column("source_file_id", sa.String(length=36), nullable=False), sa.Column("version_number", sa.Integer(), nullable=False), sa.Column("status", sa.String(length=20), nullable=False), sa.Column("point_count", sa.BigInteger(), nullable=True), sa.Column("bounds", sa.JSON(), nullable=True), sa.Column("viewer_manifest_key", sa.String(length=512), nullable=True), sa.Column("error_message", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["source_file_id"], ["files.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("case_id", "version_number", name="uq_case_versions_case_number"))
    op.create_index("ix_case_versions_case_id", "case_versions", ["case_id"])
    op.create_table("jobs", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("type", sa.String(length=50), nullable=False), sa.Column("case_version_id", sa.String(length=36), nullable=False), sa.Column("status", sa.String(length=20), nullable=False), sa.Column("progress", sa.Integer(), nullable=False), sa.Column("error_message", sa.Text(), nullable=True), sa.Column("started_at", sa.DateTime(timezone=True), nullable=True), sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["case_version_id"], ["case_versions.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_jobs_case_version_id", "jobs", ["case_version_id"])
    op.create_table("audit_logs", sa.Column("id", sa.String(length=36), nullable=False), sa.Column("action", sa.String(length=64), nullable=False), sa.Column("actor_id", sa.Integer(), nullable=True), sa.Column("case_id", sa.String(length=36), nullable=True), sa.Column("case_version_id", sa.String(length=36), nullable=True), sa.Column("job_id", sa.String(length=36), nullable=True), sa.Column("detail", sa.JSON(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_case_id", "audit_logs", ["case_id"])
    op.create_index("ix_audit_logs_case_version_id", "audit_logs", ["case_version_id"])
    op.create_index("ix_audit_logs_job_id", "audit_logs", ["job_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("jobs")
    op.drop_table("case_versions")
    op.drop_table("files")
    op.drop_table("cases")
