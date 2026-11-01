"""M5 publication and authorization."""
from alembic import op
import sqlalchemy as sa
revision='202611010007'
down_revision='202610310006'
branch_labels=None
depends_on=None


def upgrade():
    with op.batch_alter_table('case_versions') as b:
        b.add_column(sa.Column('parent_version_id',sa.String(36)))
        b.create_foreign_key('fk_version_parent','case_versions',['parent_version_id'],['id'])
    op.create_table('case_authorizations',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('case_id',sa.String(36),sa.ForeignKey('cases.id'),nullable=False),
        sa.Column('reference',sa.String(200),nullable=False),sa.Column('scope',sa.Text(),nullable=False),
        sa.Column('valid_until',sa.DateTime(timezone=True),nullable=False),sa.Column('revoked_at',sa.DateTime(timezone=True)),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index('ix_case_authorizations_case_id','case_authorizations',['case_id'])
    op.create_table('teaching_copies',
        sa.Column('id',sa.String(36),primary_key=True),sa.Column('version_id',sa.String(36),sa.ForeignKey('case_versions.id'),unique=True,nullable=False),
        sa.Column('authorization_id',sa.String(36),sa.ForeignKey('case_authorizations.id'),nullable=False),
        sa.Column('manifest_key',sa.String(512),nullable=False),sa.Column('checksum',sa.String(64),nullable=False),
        sa.Column('review_note',sa.Text(),nullable=False),sa.Column('valid_until',sa.DateTime(timezone=True),nullable=False),
        sa.Column('published_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('published_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))


def downgrade():
    op.execute("UPDATE case_versions SET status='READY' WHERE status='PUBLISHED'")
    op.drop_table('teaching_copies');op.drop_table('case_authorizations')
    with op.batch_alter_table('case_versions') as b:
        b.drop_constraint('fk_version_parent',type_='foreignkey');b.drop_column('parent_version_id')
