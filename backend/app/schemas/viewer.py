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
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    viewer_state: dict | None = Field(default=None, alias="viewerState")


class MeasurementData(BaseModel):
    id: str
    case_version_id: str = Field(serialization_alias="caseVersionId")
    start_point: dict = Field(serialization_alias="startPoint")
    end_point: dict = Field(serialization_alias="endPoint")
    delta_x: float = Field(serialization_alias="deltaX")
    delta_y: float = Field(serialization_alias="deltaY")
    delta_z: float = Field(serialization_alias="deltaZ")
    horizontal_distance: float = Field(serialization_alias="horizontalDistance")
    vertical_distance: float = Field(serialization_alias="verticalDistance")
    distance: float
    title: str | None = None
    description: str | None = None
    viewer_state: dict | None = Field(serialization_alias="viewerState")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class AreaMeasurementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: list[Coordinate3D] = Field(min_length=3, max_length=100)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    viewer_state: dict | None = Field(default=None, alias="viewerState")


class AreaMeasurementData(BaseModel):
    id: str
    case_version_id: str = Field(serialization_alias="caseVersionId")
    points: list[dict]
    point_count: int = Field(serialization_alias="pointCount")
    perimeter: float
    area: float
    max_plane_deviation: float = Field(serialization_alias="maxPlaneDeviation")
    title: str | None = None
    description: str | None = None
    viewer_state: dict | None = Field(serialization_alias="viewerState")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: list[Coordinate3D] = Field(min_length=2, max_length=50)
    width: float = Field(ge=0.01, le=100)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    viewer_state: dict | None = Field(default=None, alias="viewerState")

    @field_validator("width", mode="before")
    @classmethod
    def finite_width(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("width must be a finite number")
        return float(value)


class ProfileData(BaseModel):
    id: str
    case_version_id: str = Field(serialization_alias="caseVersionId")
    points: list[dict]
    point_count: int = Field(serialization_alias="pointCount")
    width: float
    path_length: float = Field(serialization_alias="pathLength")
    title: str | None = None
    description: str | None = None
    viewer_state: dict | None = Field(serialization_alias="viewerState")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
