from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def _utc_timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ApiModel(BaseModel):
    model_config = ConfigDict(json_encoders={datetime: lambda value: _utc_timestamp(value).isoformat().replace("+00:00", "Z")})


class CaseCreate(ApiModel):
    internal_code: str = Field(alias="internalCode", min_length=1, max_length=64)
    teaching_title: str = Field(alias="teachingTitle", min_length=1, max_length=200)
    case_type: str = Field(alias="caseType", min_length=1, max_length=64)
    difficulty: str
    course_tags: list[str] = Field(alias="courseTags", default_factory=list)
    valid_until: datetime | None = Field(alias="validUntil", default=None)
    desensitization_level: str = Field(alias="desensitizationLevel")
    description: str | None = None


class FileData(ApiModel):
    id: str
    file_name: str = Field(serialization_alias="fileName")
    file_size: int = Field(serialization_alias="fileSize")


class VersionCreate(ApiModel):
    file_id: str = Field(alias="fileId", serialization_alias="fileId")


class VersionData(ApiModel):
    id: str
    status: str
    job_id: str | None = Field(serialization_alias="jobId")
    progress: int
    point_count: int | None = Field(serialization_alias="pointCount")
    bounds: dict | None
    failure_reason: str | None = Field(serialization_alias="failureReason")
    created_at: datetime = Field(serialization_alias="createdAt")


class CaseData(ApiModel):
    id: str
    internal_code: str = Field(serialization_alias="internalCode")
    teaching_title: str = Field(serialization_alias="teachingTitle")
    case_type: str = Field(serialization_alias="caseType")
    difficulty: str
    course_tags: list[str] = Field(serialization_alias="courseTags")
    valid_until: datetime | None = Field(serialization_alias="validUntil")
    desensitization_level: str = Field(serialization_alias="desensitizationLevel")
    file: FileData | None
    latest_version: VersionData | None = Field(serialization_alias="latestVersion")
    created_at: datetime = Field(serialization_alias="createdAt")


class JobData(ApiModel):
    id: str
    type: str
    status: str
    progress: int
    version_id: str = Field(serialization_alias="versionId")
    failure_reason: str | None = Field(serialization_alias="failureReason")
    created_at: datetime = Field(serialization_alias="createdAt")
    started_at: datetime | None = Field(serialization_alias="startedAt")
    finished_at: datetime | None = Field(serialization_alias="finishedAt")


class CaseListData(ApiModel):
    items: list[CaseData]
    total: int
