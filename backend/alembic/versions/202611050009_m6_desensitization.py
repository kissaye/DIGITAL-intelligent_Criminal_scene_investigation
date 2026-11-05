from alembic import op
import sqlalchemy as sa
revision="202611050009"; down_revision="202611040008"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("desensitization_rules",sa.Column("id",sa.String(36),primary_key=True),sa.Column("case_version_id",sa.String(36),sa.ForeignKey("case_versions.id",ondelete="CASCADE"),nullable=False),sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("mode",sa.String(10),nullable=False),sa.Column("geometry",sa.JSON(),nullable=False),sa.Column("title",sa.String(200),nullable=False),sa.Column("description",sa.Text()),sa.Column("status",sa.String(10),nullable=False,server_default="DRAFT"),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_index("ix_desensitization_rules_version","desensitization_rules",["case_version_id"])
    with op.batch_alter_table("teaching_copies") as b: b.add_column(sa.Column("desensitization_rules",sa.JSON(),nullable=False,server_default="[]"))
def downgrade():
    with op.batch_alter_table("teaching_copies") as b: b.drop_column("desensitization_rules")
    op.drop_index("ix_desensitization_rules_version",table_name="desensitization_rules"); op.drop_table("desensitization_rules")
