from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AnnotationCreate(BaseModel):
    type: Literal["POINT_MARK", "AREA_MARK"]
    geometry: dict
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    viewer_state: dict | None = Field(default=None, alias="viewerState")


class AnnotationData(AnnotationCreate):
    id: str
    case_version_id: str = Field(serialization_alias="caseVersionId")
    scope: str
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class MeasurementCreate(BaseModel):
    start_point: dict = Field(alias="startPoint")
    end_point: dict = Field(alias="endPoint")
    distance: float | None = None
    viewer_state: dict | None = Field(default=None, alias="viewerState")


class MeasurementData(BaseModel):
    id: str
    case_version_id: str = Field(serialization_alias="caseVersionId")
    start_point: dict = Field(serialization_alias="startPoint")
    end_point: dict = Field(serialization_alias="endPoint")
    distance: float
    viewer_state: dict | None = Field(serialization_alias="viewerState")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
