"""Server-authoritative polyline profile calculations."""
import math

from fastapi import HTTPException

EPSILON = 1e-6


def _point(value):
    raw = value.model_dump() if hasattr(value, "model_dump") else value
    return {axis: float(raw[axis]) for axis in ("x", "y", "z")}


def profile_values(points, width):
    result = [_point(point) for point in points]
    if len(result) < 2:
        raise HTTPException(422, "剖面至少需要两个点")
    path_length = 0.0
    for current, following in zip(result, result[1:]):
        length = math.dist(tuple(current.values()), tuple(following.values()))
        if length <= EPSILON:
            raise HTTPException(422, "剖面相邻点不能重合")
        path_length += length
    return {"points": result, "pointCount": len(result), "width": float(width), "pathLength": path_length}
