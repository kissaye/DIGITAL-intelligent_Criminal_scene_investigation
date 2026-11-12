import math

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.viewer import AreaMeasurementCreate, Coordinate3D
from app.services.area_measurements import PLANARITY_TOLERANCE, area_measurement_values


def point(x, y, z=0):
    return Coordinate3D(x=x, y=y, z=z)


def test_triangle_perimeter_area_and_closed_point_normalization():
    values = area_measurement_values([point(0, 0), point(3, 0), point(3, 4), point(0, 0)])
    assert values["pointCount"] == 3
    assert values["perimeter"] == pytest.approx(12)
    assert values["area"] == pytest.approx(6)


def test_square_and_inclined_triangle_are_deterministic():
    square = area_measurement_values([point(0, 0), point(2, 0), point(2, 2), point(0, 2)])
    assert square["perimeter"] == pytest.approx(8)
    assert square["area"] == pytest.approx(4)
    tilted = area_measurement_values([point(0, 0, 0), point(1, 0, 1), point(0, 2, 0)])
    assert tilted["area"] == pytest.approx(math.sqrt(2))
    reverse = area_measurement_values(list(reversed(tilted["points"])))
    assert reverse["area"] == pytest.approx(tilted["area"])


@pytest.mark.parametrize("points", [
    [point(0, 0), point(1, 0)],
    [point(0, 0), point(1, 0), point(1, 0)],
    [point(0, 0), point(1, 0), point(2, 0)],
    [point(0, 0), point(2, 2), point(0, 2), point(2, 0)],
])
def test_degenerate_and_self_crossing_polygons_are_rejected(points):
    with pytest.raises(HTTPException) as error:
        area_measurement_values(points)
    assert error.value.status_code == 422


def test_planarity_tolerance_is_explicit():
    accepted = area_measurement_values([point(0, 0), point(1, 0), point(1, 1, PLANARITY_TOLERANCE / 2), point(0, 1)])
    assert accepted["maxPlaneDeviation"] <= PLANARITY_TOLERANCE
    with pytest.raises(HTTPException, match="同一测量平面"):
        area_measurement_values([point(0, 0), point(1, 0), point(1, 1, PLANARITY_TOLERANCE * 4), point(0, 1)])


@pytest.mark.parametrize("value", ["1", True, None, math.nan, math.inf, -math.inf])
def test_schema_rejects_invalid_coordinates_and_client_results(value):
    payload = {"points": [{"x": value, "y": 0, "z": 0}, {"x": 1, "y": 0, "z": 0}, {"x": 0, "y": 1, "z": 0}]}
    with pytest.raises(ValidationError):
        AreaMeasurementCreate.model_validate(payload)
    with pytest.raises(ValidationError):
        AreaMeasurementCreate.model_validate({"points": [{"x": 0, "y": 0, "z": 0}, {"x": 1, "y": 0, "z": 0}, {"x": 0, "y": 1, "z": 0}], "area": 999})
