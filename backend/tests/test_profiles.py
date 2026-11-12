import math

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.viewer import Coordinate3D, ProfileCreate
from app.services.profiles import profile_values


def point(x, y, z=0):
    return Coordinate3D(x=x, y=y, z=z)


def test_profile_two_and_three_point_lengths_and_reverse_order():
    straight = profile_values([point(0, 0, 0), point(3, 4, 0)], 1)
    assert straight["pathLength"] == pytest.approx(5)
    bend = profile_values([point(0, 0, 0), point(3, 4, 0), point(3, 4, 12)], 1)
    assert bend["pathLength"] == pytest.approx(17)
    assert profile_values(list(reversed(bend["points"])), 1)["pathLength"] == pytest.approx(17)


@pytest.mark.parametrize("points", [[point(0, 0)], [point(0, 0), point(0, 0)], [point(0, 0), point(1e-7, 0)]])
def test_profile_requires_distinct_adjacent_points(points):
    with pytest.raises(HTTPException) as error:
        profile_values(points, 1)
    assert error.value.status_code == 422


@pytest.mark.parametrize("width", [0, -1, 100.1, "1", True, math.nan, math.inf])
def test_profile_schema_rejects_invalid_width_and_derived_values(width):
    base = {"points": [{"x": 0, "y": 0, "z": 0}, {"x": 1, "y": 0, "z": 0}], "width": width}
    with pytest.raises(ValidationError):
        ProfileCreate.model_validate(base)
    with pytest.raises(ValidationError):
        ProfileCreate.model_validate({"points": [{"x": 0, "y": 0, "z": 0}, {"x": 1, "y": 0, "z": 0}], "width": 1, "pathLength": 99})


@pytest.mark.parametrize("value", ["1", True, None, math.nan, math.inf, -math.inf])
def test_profile_schema_rejects_invalid_coordinates(value):
    with pytest.raises(ValidationError):
        ProfileCreate.model_validate({"points": [{"x": value, "y": 0, "z": 0}, {"x": 1, "y": 0, "z": 0}], "width": 1})
