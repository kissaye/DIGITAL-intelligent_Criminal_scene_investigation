"""Focused validation for administrator and student measurement payloads."""
import math

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.student import DraftPayload
from app.schemas.viewer import Coordinate3D, MeasurementCreate
from app.services.measurements import measurement_values, points_and_distance


def point(x=0, y=0, z=0):
    return Coordinate3D(x=x, y=y, z=z)


def test_distance_is_recomputed_from_coordinates():
    start, end, distance = points_and_distance(point(), point(3, 4, 0))
    assert start == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert end == {"x": 3.0, "y": 4.0, "z": 0.0}
    assert distance == 5


def test_m9_measurement_components_and_signed_reverse_delta():
    values = measurement_values(point(0, 0, 9), point(9, 9, 0))
    assert values["deltaX"] == 9
    assert values["deltaY"] == 9
    assert values["deltaZ"] == -9
    assert values["horizontalDistance"] == pytest.approx(12.7279220614)
    assert values["verticalDistance"] == 9
    assert values["distance"] == pytest.approx(15.5884572681)
    reverse = measurement_values(point(9, 9, 0), point(0, 0, 9))
    assert (reverse["deltaX"], reverse["deltaY"], reverse["deltaZ"]) == (-9, -9, 9)


def test_m9_horizontal_and_vertical_measurements():
    assert measurement_values(point(), point(3, 4, 0))["verticalDistance"] == 0
    assert measurement_values(point(), point(0, 0, 5))["horizontalDistance"] == 0


def test_legacy_zero_distance_can_still_be_read_without_bypassing_writes():
    assert measurement_values(point(), point(), validate_distinct=False)["distance"] == 0


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


def test_client_derived_measurement_values_are_rejected():
    with pytest.raises(ValidationError):
        MeasurementCreate.model_validate({
        "startPoint": {"x": 0, "y": 0, "z": 0},
        "endPoint": {"x": 3, "y": 4, "z": 0},
        "distance": 999,
        })


def test_student_payload_is_strict_and_batch_can_be_prevalidated():
    payload = DraftPayload.model_validate({
        "reportContent": {"overview": "", "process": "", "evidenceDescription": "", "preliminaryConclusion": ""},
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


@pytest.mark.parametrize("content", [
    {"overview": "x", "process": "", "evidenceDescription": ""},
    {"overview": "x", "process": "", "evidenceDescription": "", "preliminaryConclusion": "", "extra": "x"},
    {"overview": 1, "process": "", "evidenceDescription": "", "preliminaryConclusion": ""},
    {"overview": None, "process": "", "evidenceDescription": "", "preliminaryConclusion": ""},
    {"overview": [], "process": "", "evidenceDescription": "", "preliminaryConclusion": ""},
    {"overview": True, "process": "", "evidenceDescription": "", "preliminaryConclusion": ""},
])
def test_report_content_is_fixed_and_strict(content):
    with pytest.raises(ValidationError):
        DraftPayload.model_validate({"reportContent": content, "marks": [], "measurements": []})
