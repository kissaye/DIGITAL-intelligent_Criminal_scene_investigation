from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from sqlalchemy import text

from app.api.deps import get_request_id
from app.schemas.common import APIResponse
from app.core.config import get_settings
from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse[dict[str, str]], summary="Health check")
def health(request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[dict[str, str]]:
    return APIResponse(data={"status": "ok"}, request_id=request_id)


@router.get("/health/ready", response_model=APIResponse[dict[str, str]])
def ready(request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[dict[str, str]]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        with Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2) as redis:
            redis.ping()
    except Exception:
        raise HTTPException(503, "Database or queue is unavailable")
    return APIResponse(data={"status": "ready"}, request_id=request_id)
