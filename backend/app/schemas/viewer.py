from datetime import datetime
from typing import Literal

import math
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Coordinate3D(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float
    z: float
    @field_validator("x", "y", "z", mode="before")
    @classmethod
    def finite_number(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("coordinate must be a finite number")
        return float(value)


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
    model_config = ConfigDict(extra="forbid")
    start_point: Coordinate3D = Field(alias="startPoint")
    end_point: Coordinate3D = Field(alias="endPoint")
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
