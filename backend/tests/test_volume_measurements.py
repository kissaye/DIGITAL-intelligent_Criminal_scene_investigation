import math
import pytest
from pydantic import ValidationError
from app.schemas.viewer import Coordinate3D, VolumeMeasurementCreate
from app.services.volumes import volume_values

def point(x,y,z): return Coordinate3D(x=x,y=y,z=z)
def test_box_volume_is_server_computed_and_rotation_does_not_change_it():
    values=volume_values(point(4.5,4.5,4.5),point(3,4,5),point(1,2,3))
    assert (values["length"],values["width"],values["height"],values["volume"]) == (3,4,5,60)

@pytest.mark.parametrize("payload",[
    {"center":{"x":0,"y":0,"z":0},"size":{"x":0,"y":1,"z":1},"rotation":{"x":0,"y":0,"z":0}},
    {"center":{"x":0,"y":0,"z":0},"size":{"x":1000001,"y":1,"z":1},"rotation":{"x":0,"y":0,"z":0}},
    {"center":{"x":"0","y":0,"z":0},"size":{"x":1,"y":1,"z":1},"rotation":{"x":0,"y":0,"z":0}},
    {"center":{"x":0,"y":0,"z":0},"size":{"x":1,"y":1,"z":1},"rotation":{"x":math.inf,"y":0,"z":0}},
    {"center":{"x":0,"y":0,"z":0},"size":{"x":1,"y":1,"z":1},"rotation":{"x":0,"y":0,"z":0},"volume":999},
])
def test_volume_schema_rejects_invalid_or_client_calculated_values(payload):
    with pytest.raises(ValidationError): VolumeMeasurementCreate.model_validate(payload)
