import math

from fastapi import HTTPException

EPSILON = 1e-6


def _point(value):
    """Return the already schema-validated coordinate as a JSON mapping."""
    raw = value.model_dump() if hasattr(value, "model_dump") else value
    return {axis: float(raw[axis]) for axis in ("x", "y", "z")}


def measurement_values(start, end, *, validate_distinct=True):
    """Compute every persisted/returned measurement value from its endpoints."""
    a, b = _point(start), _point(end)
    delta_x = b["x"] - a["x"]
    delta_y = b["y"] - a["y"]
    delta_z = b["z"] - a["z"]
    horizontal = math.hypot(delta_x, delta_y)
    distance = math.hypot(horizontal, delta_z)
    if validate_distinct and distance <= EPSILON:
        raise HTTPException(422, "起点和终点不能重合")
    return {"start": a, "end": b, "deltaX": delta_x, "deltaY": delta_y,
            "deltaZ": delta_z, "horizontalDistance": horizontal,
            "verticalDistance": abs(delta_z), "distance": distance}


def points_and_distance(start, end):
    """Compatibility helper for call sites that persist the original three values."""
    values = measurement_values(start, end)
    return values["start"], values["end"], values["distance"]
