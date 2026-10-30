from pydantic import BaseModel, Field
class DraftPayload(BaseModel):
    report_content: dict|None=Field(default=None,alias="reportContent"); marks:list[dict]=[]; measurements:list[dict]=[]
