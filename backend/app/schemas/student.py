from pydantic import BaseModel, ConfigDict, Field

from app.schemas.viewer import Coordinate3D


class ReportContent(BaseModel):
    """The fixed M8.3 report contract; empty strings are valid draft values."""
    model_config = ConfigDict(extra="forbid")
    overview: str = Field(max_length=10000, strict=True)
    process: str = Field(max_length=10000, strict=True)
    evidence_description: str = Field(alias="evidenceDescription", max_length=10000, strict=True)
    preliminary_conclusion: str = Field(alias="preliminaryConclusion", max_length=10000, strict=True)


class StudentMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    start_point: Coordinate3D = Field(alias="startPoint")
    end_point: Coordinate3D = Field(alias="endPoint")
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    viewer_state: dict | None = Field(default=None, alias="viewerState")


class DraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_content: ReportContent = Field(alias="reportContent")
    marks: list[dict] = Field(default_factory=list)
    measurements: list[StudentMeasurement] = Field(default_factory=list)
