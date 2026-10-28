"""Create M0 identity tables."""
from alembic import op
import sqlalchemy as sa

revision = "202610280001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("roles", sa.Column("id", sa.Integer(), nullable=False), sa.Column("code", sa.String(length=32), nullable=False), sa.Column("name", sa.String(length=64), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("code"))
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)
    op.create_table("users", sa.Column("id", sa.Integer(), nullable=False), sa.Column("username", sa.String(length=64), nullable=False), sa.Column("display_name", sa.String(length=128), nullable=False), sa.Column("password_hash", sa.String(length=255), nullable=False), sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("username"))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("user_roles", sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("role_id", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("user_id", "role_id"), sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"))


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")
