"""Server-authoritative Potree BoxVolume measurements, not object volumes."""

def _point(value):
    raw = value.model_dump() if hasattr(value, "model_dump") else value
    return {axis: float(raw[axis]) for axis in ("x", "y", "z")}


def volume_values(center, size, rotation):
    center_value, size_value, rotation_value = _point(center), _point(size), _point(rotation)
    return {"center": center_value, "size": size_value, "rotation": rotation_value,
            "length": size_value["x"], "width": size_value["y"], "height": size_value["z"],
            "volume": size_value["x"] * size_value["y"] * size_value["z"]}
