"""Deterministic, guarded 3D polygon measurement calculations."""
import math

from fastapi import HTTPException

AREA_EPSILON = 1e-8
PLANARITY_TOLERANCE = 1e-4


def _point(value):
    raw = value.model_dump() if hasattr(value, "model_dump") else value
    return {axis: float(raw[axis]) for axis in ("x", "y", "z")}


def _same(a, b):
    return all(a[key] == b[key] for key in ("x", "y", "z"))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _intersects(a, b, c, d):
    # Input vertices are distinct neighbours, so collinear touch is invalid too.
    one, two = _orientation(a, b, c), _orientation(a, b, d)
    three, four = _orientation(c, d, a), _orientation(c, d, b)
    if abs(one) <= AREA_EPSILON or abs(two) <= AREA_EPSILON or abs(three) <= AREA_EPSILON or abs(four) <= AREA_EPSILON:
        return True
    return (one > 0) != (two > 0) and (three > 0) != (four > 0)


def area_measurement_values(points):
    """Normalize a closed polygon and calculate perimeter/area server-side.

    Points must lie within PLANARITY_TOLERANCE of the Newell plane.  The
    accepted near-planar polygon uses its Newell vector area, while crossing
    edges are rejected after projection onto that plane's dominant axis.
    """
    normalized = [_point(point) for point in points]
    if len(normalized) > 1 and _same(normalized[0], normalized[-1]):
        normalized.pop()
    if len(normalized) < 3:
        raise HTTPException(422, "区域测量至少需要三个点")
    if len({(point["x"], point["y"], point["z"]) for point in normalized}) < 3:
        raise HTTPException(422, "区域测量至少需要三个不同点")
    if any(_same(normalized[index], normalized[(index + 1) % len(normalized)]) for index in range(len(normalized))):
        raise HTTPException(422, "区域测量不能包含连续重复点")

    vector = [0.0, 0.0, 0.0]
    perimeter = 0.0
    for index, point in enumerate(normalized):
        nxt = normalized[(index + 1) % len(normalized)]
        cross = _cross((point["x"], point["y"], point["z"]), (nxt["x"], nxt["y"], nxt["z"]))
        vector = [vector[axis] + cross[axis] for axis in range(3)]
        perimeter += math.dist(tuple(point.values()), tuple(nxt.values()))
    length = math.sqrt(sum(value * value for value in vector))
    if length / 2 <= AREA_EPSILON:
        raise HTTPException(422, "选取点不能构成有效区域")
    unit = tuple(value / length for value in vector)
    origin = normalized[0]
    deviations = [abs((point["x"] - origin["x"]) * unit[0] + (point["y"] - origin["y"]) * unit[1] + (point["z"] - origin["z"]) * unit[2]) for point in normalized]
    max_deviation = max(deviations)
    if max_deviation > PLANARITY_TOLERANCE:
        raise HTTPException(422, "选取点不在同一测量平面附近")

    drop = max(range(3), key=lambda axis: abs(vector[axis]))
    axes = [axis for axis in range(3) if axis != drop]
    projected = [tuple((point["x"], point["y"], point["z"])[axis] for axis in axes) for point in normalized]
    count = len(projected)
    for first in range(count):
        for second in range(first + 1, count):
            if first == second or (first + 1) % count == second or (second + 1) % count == first:
                continue
            if _intersects(projected[first], projected[(first + 1) % count], projected[second], projected[(second + 1) % count]):
                raise HTTPException(422, "选取区域存在自相交")
    return {"points": normalized, "pointCount": count, "perimeter": perimeter,
            "area": length / 2, "maxPlaneDeviation": max_deviation}
