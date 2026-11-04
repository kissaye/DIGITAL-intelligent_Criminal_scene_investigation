from alembic import op
import sqlalchemy as sa
revision="202610300006"; down_revision="202610300005"; branch_labels=None; depends_on=None
def upgrade():
    with op.batch_alter_table("tasks") as b: b.add_column(sa.Column("class_id",sa.String(36),nullable=True)); b.create_foreign_key("fk_tasks_class_id","classes",["class_id"],["id"]); b.create_index("ix_tasks_class_id",["class_id"])
    with op.batch_alter_table("submissions") as b: b.add_column(sa.Column("score",sa.Float(),nullable=True)); b.add_column(sa.Column("feedback",sa.Text(),nullable=True)); b.add_column(sa.Column("graded_at",sa.DateTime(timezone=True),nullable=True)); b.add_column(sa.Column("graded_by",sa.Integer(),nullable=True)); b.create_foreign_key("fk_submissions_graded_by","users",["graded_by"],["id"])
def downgrade():
    with op.batch_alter_table("submissions") as b: b.drop_column("graded_by");b.drop_column("graded_at");b.drop_column("feedback");b.drop_column("score")
    with op.batch_alter_table("tasks") as b: b.drop_index("ix_tasks_class_id");b.drop_column("class_id")
