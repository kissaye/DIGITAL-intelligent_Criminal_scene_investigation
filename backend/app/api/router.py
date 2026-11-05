from fastapi import APIRouter

from app.api.routes import auth, cases, health, viewer, student, teacher, m5, desensitization

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(viewer.router)
api_router.include_router(student.router)
api_router.include_router(teacher.router)
api_router.include_router(m5.router)
api_router.include_router(desensitization.router)
