from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0", description="M0 identity and M1 controlled case import APIs.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def error_response(request: Request, status_code: int, message: str, details: list[dict] | None = None) -> JSONResponse:
    content = {"code": status_code, "message": message, "data": {}, "requestId": getattr(request.state, "request_id", str(uuid4()))}
    if details is not None:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for issue in exc.errors():
        safe_context = {
            key: value
            for key, value in (issue.get("ctx") or {}).items()
            if value is None or isinstance(value, (str, int, float, bool))
        }
        details.append({
            "type": issue.get("type"),
            "loc": list(issue.get("loc") or ()),
            "msg": issue.get("msg"),
            "ctx": safe_context,
        })
    return error_response(request, 422, "请求数据校验失败", details)


app.include_router(api_router, prefix=settings.api_v1_prefix)
