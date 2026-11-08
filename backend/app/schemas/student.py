from pydantic import BaseModel, ConfigDict, Field
from app.schemas.viewer import Coordinate3D
class StudentMeasurement(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id:str|None=None
    start_point:Coordinate3D=Field(alias="startPoint")
    end_point:Coordinate3D=Field(alias="endPoint")
    viewer_state:dict|None=Field(default=None,alias="viewerState")
class DraftPayload(BaseModel):
    report_content: dict|None=Field(default=None,alias="reportContent"); marks:list[dict]=[]; measurements:list[StudentMeasurement]=[]
