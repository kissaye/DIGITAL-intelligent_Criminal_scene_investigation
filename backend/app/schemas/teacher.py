from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid", str_strip_whitespace=True)


class NameInput(Input):
    name: str = Field(min_length=1, max_length=200)


class MemberInput(Input):
    student_id: int = Field(alias="studentId", gt=0)


class RubricInput(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    max_score: Decimal = Field(alias="maxScore", gt=0, le=99999, max_digits=7, decimal_places=2)


class TaskInput(Input):
    course_id: str = Field(alias="courseId")
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(default="", max_length=20000)
    case_version_id: str = Field(alias="caseVersionId")
    class_ids: list[str] = Field(alias="classIds", min_length=1, max_length=100)
    start_at: datetime | None = Field(default=None, alias="startAt")
    due_at: datetime | None = Field(default=None, alias="dueAt")
    allow_late: bool = Field(default=False, alias="allowLate")
    rubric: list[RubricInput] = Field(min_length=1, max_length=100)

    @field_validator("start_at", "due_at")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Time zone is required")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_at and self.due_at and self.start_at >= self.due_at:
            raise ValueError("Deadline must follow start time")
        if sum(x.max_score for x in self.rubric) > Decimal("99999.99"):
            raise ValueError("Maximum total score exceeded")
        return self


class GradeItemInput(Input):
    rubric_item_id: str = Field(alias="rubricItemId")
    score: Decimal = Field(ge=0, le=99999, max_digits=7, decimal_places=2)
    comment: str = Field(default="", max_length=4000)


class GradeInput(Input):
    feedback: str = Field(default="", max_length=20000)
    items: list[GradeItemInput] = Field(max_length=100)
