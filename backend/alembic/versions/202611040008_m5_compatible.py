from alembic import op
import sqlalchemy as sa
revision="202611040008";down_revision="202610300007";branch_labels=None;depends_on=None
def upgrade():
 with op.batch_alter_table("case_versions") as b:
  b.add_column(sa.Column("parent_version_id",sa.String(36),nullable=True)); b.create_foreign_key("fk_case_versions_parent","case_versions",["parent_version_id"],["id"])
 op.create_table("case_authorizations",sa.Column("id",sa.String(36),primary_key=True),sa.Column("case_id",sa.String(36),sa.ForeignKey("cases.id",ondelete="CASCADE"),nullable=False),sa.Column("authorization_no",sa.String(200),unique=True,nullable=False),sa.Column("scope",sa.Text(),nullable=False),sa.Column("valid_from",sa.DateTime(timezone=True)),sa.Column("valid_until",sa.DateTime(timezone=True),nullable=False),sa.Column("revoked_at",sa.DateTime(timezone=True)),sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("CURRENT_TIMESTAMP"),nullable=False))
 op.create_table("teaching_copies",sa.Column("id",sa.String(36),primary_key=True),sa.Column("case_version_id",sa.String(36),sa.ForeignKey("case_versions.id"),nullable=False,unique=True),sa.Column("authorization_id",sa.String(36),sa.ForeignKey("case_authorizations.id"),nullable=False),sa.Column("manifest_key",sa.String(512),nullable=False),sa.Column("checksum_sha256",sa.String(64),nullable=False),sa.Column("reviewed_at",sa.DateTime(timezone=True),nullable=False),sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("review_note",sa.Text(),nullable=False),sa.Column("valid_until",sa.DateTime(timezone=True),nullable=False),sa.Column("published_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("published_at",sa.DateTime(timezone=True),server_default=sa.text("CURRENT_TIMESTAMP"),nullable=False))
def downgrade():
 op.drop_table("teaching_copies");op.drop_table("case_authorizations")
 with op.batch_alter_table("case_versions") as b: b.drop_constraint("fk_case_versions_parent",type_="foreignkey");b.drop_column("parent_version_id")
