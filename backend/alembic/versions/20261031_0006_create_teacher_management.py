"""M4 teacher management; preserve existing M3 tasks."""
from alembic import op
import sqlalchemy as sa

revision = "202610310006"
down_revision = "202610300005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("course_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_tasks_course_id", "courses", ["course_id"], ["id"])
        batch.create_index("ix_tasks_course_id", ["course_id"])
    op.create_table("task_classes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", sa.String(36), sa.ForeignKey("classes.id"), nullable=False),
        sa.UniqueConstraint("task_id", "class_id"))
    op.create_index("ix_task_classes_task_id", "task_classes", ["task_id"])
    op.create_table("task_rubric_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("max_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("max_score > 0", name="ck_rubric_positive"))
    op.create_index("ix_task_rubric_items_task_id", "task_rubric_items", ["task_id"])
    op.create_table("submission_grades",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id"), nullable=False, unique=True),
        sa.Column("graded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("total_score >= 0", name="ck_grade_nonnegative"))
    op.create_table("submission_grade_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("grade_id", sa.String(36), sa.ForeignKey("submission_grades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rubric_item_id", sa.String(36), sa.ForeignKey("task_rubric_items.id"), nullable=False),
        sa.Column("score", sa.Numeric(7, 2), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.UniqueConstraint("grade_id", "rubric_item_id"),
        sa.CheckConstraint("score >= 0", name="ck_grade_item_nonnegative"))
    op.create_index("ix_submission_grade_items_grade_id", "submission_grade_items", ["grade_id"])


def downgrade():
    for table in ("submission_grade_items", "submission_grades", "task_rubric_items", "task_classes"):
        op.drop_table(table)
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_course_id")
        batch.drop_constraint("fk_tasks_course_id", type_="foreignkey")
        batch.drop_column("course_id")
