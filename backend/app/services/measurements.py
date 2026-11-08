import math
from fastapi import HTTPException
EPSILON=1e-6
def points_and_distance(start,end):
    a,b=start.model_dump(),end.model_dump()
    distance=math.dist([a["x"],a["y"],a["z"]],[b["x"],b["y"],b["z"]])
    if distance<=EPSILON: raise HTTPException(422,"起点和终点不能重合")
    return a,b,distance
