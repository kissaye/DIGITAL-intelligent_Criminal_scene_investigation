from alembic import op
import sqlalchemy as sa
revision="202610300007"; down_revision="202610300006"; branch_labels=None; depends_on=None
def upgrade(): op.add_column("courses",sa.Column("description",sa.Text(),nullable=True))
def downgrade(): op.drop_column("courses","description")
