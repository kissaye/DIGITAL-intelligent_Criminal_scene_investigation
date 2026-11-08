"""Focused validation for administrator and student measurement payloads."""
import math

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.student import DraftPayload
from app.schemas.viewer import Coordinate3D, MeasurementCreate
from app.services.measurements import points_and_distance


def point(x=0, y=0, z=0):
    return Coordinate3D(x=x, y=y, z=z)


def test_distance_is_recomputed_from_coordinates():
    start, end, distance = points_and_distance(point(), point(3, 4, 0))
    assert start == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert end == {"x": 3.0, "y": 4.0, "z": 0.0}
    assert distance == 5


@pytest.mark.parametrize("end", [point(), point(1e-7, 0, 0), point(1e-6, 0, 0)])
def test_zero_or_near_zero_distance_is_rejected(end):
    with pytest.raises(HTTPException) as error:
        points_and_distance(point(), end)
    assert error.value.status_code == 422


@pytest.mark.parametrize("value", ["1", True, None, math.nan, math.inf, -math.inf, []])
def test_coordinate_rejects_non_finite_or_non_json_numbers(value):
    with pytest.raises(ValidationError):
        Coordinate3D.model_validate({"x": value, "y": 0, "z": 0})


def test_coordinate_requires_all_axes_and_forbids_extras():
    with pytest.raises(ValidationError):
        Coordinate3D.model_validate({"x": 0, "y": 0})
    with pytest.raises(ValidationError):
        Coordinate3D.model_validate({"x": 0, "y": 0, "z": 0, "w": 0})


def test_client_distance_is_ignored():
    payload = MeasurementCreate.model_validate({
        "startPoint": {"x": 0, "y": 0, "z": 0},
        "endPoint": {"x": 3, "y": 4, "z": 0},
        "distance": 999,
    })
    assert points_and_distance(payload.start_point, payload.end_point)[2] == 5


def test_student_payload_is_strict_and_batch_can_be_prevalidated():
    payload = DraftPayload.model_validate({
        "reportContent": {},
        "marks": [],
        "measurements": [{
            "startPoint": {"x": 0, "y": 0, "z": 0},
            "endPoint": {"x": 3, "y": 4, "z": 0},
        }],
    })
    assert points_and_distance(payload.measurements[0].start_point, payload.measurements[0].end_point)[2] == 5
    with pytest.raises(ValidationError):
        DraftPayload.model_validate({
            "measurements": [{
                "startPoint": {"x": 0, "y": 0, "z": 0},
                "endPoint": {"x": 0, "y": 0},
            }],
        })
