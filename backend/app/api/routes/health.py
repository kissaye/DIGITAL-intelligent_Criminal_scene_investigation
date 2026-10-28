from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_request_id
from app.schemas.common import APIResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse[dict[str, str]], summary="Health check")
def health(request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[dict[str, str]]:
    return APIResponse(data={"status": "ok"}, request_id=request_id)
