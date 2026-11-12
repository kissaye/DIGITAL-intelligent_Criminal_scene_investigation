import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_admin
from app.core.config import get_settings
from app.models.case import Annotation, AreaMeasurement, AuditLog, CaseVersion, DesensitizationRule, Measurement, TeachingCopy
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.viewer import AnnotationCreate, AnnotationData, AreaMeasurementCreate, AreaMeasurementData, MeasurementCreate, MeasurementData
from app.services.area_measurements import area_measurement_values
from app.services.practice_access import require_open_task
from app.services.measurements import measurement_values

router = APIRouter(tags=["viewer"])
settings = get_settings()

def _ready(db: Session, version_id: str) -> CaseVersion:
    item = db.scalar(select(CaseVersion).where(CaseVersion.id == version_id))
    if item is None: raise HTTPException(404, "Case version not found")
    if item.status not in {"READY", "PUBLISHED"} or not item.viewer_manifest_key: raise HTTPException(409, "Viewer is unavailable")
    return item

def _annotation(item: Annotation) -> AnnotationData:
    return AnnotationData(id=item.id, case_version_id=item.case_version_id, scope=item.scope, type=item.type, geometry=item.geometry, title=item.title, description=item.description, viewer_state=item.viewer_state, created_at=item.created_at, updated_at=item.updated_at)

def _measurement(item: Measurement) -> MeasurementData:
    values = measurement_values(item.start_point, item.end_point, validate_distinct=False)
    return MeasurementData(id=item.id, case_version_id=item.case_version_id, start_point=values["start"], end_point=values["end"], delta_x=values["deltaX"], delta_y=values["deltaY"], delta_z=values["deltaZ"], horizontal_distance=values["horizontalDistance"], vertical_distance=values["verticalDistance"], distance=values["distance"], title=item.title, description=item.description, viewer_state=item.viewer_state, created_at=item.created_at, updated_at=item.updated_at)

def _area_measurement(item: AreaMeasurement) -> AreaMeasurementData:
    values = area_measurement_values(item.points)
    return AreaMeasurementData(id=item.id, case_version_id=item.case_version_id, points=values["points"], point_count=values["pointCount"], perimeter=values["perimeter"], area=values["area"], max_plane_deviation=values["maxPlaneDeviation"], title=item.title, description=item.description, viewer_state=item.viewer_state, created_at=item.created_at, updated_at=item.updated_at)

@router.get("/case-versions/{version_id}/viewer-config")
def viewer_config(version_id: str, response: Response, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    version = _ready(db, version_id)
    exp = datetime.now(UTC) + timedelta(minutes=settings.viewer_token_expire_minutes)
    token = jwt.encode({"sub": str(admin.id), "version": version_id, "exp": exp, "type": "viewer"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    response.set_cookie(f"viewer_{version_id}", token, max_age=settings.viewer_token_expire_minutes * 60, httponly=True, samesite="lax", path=f"{settings.api_v1_prefix}/viewer-assets/{version_id}")
    db.add(AuditLog(action="VIEWER_OPENED", actor_id=admin.id, case_id=version.case_id, case_version_id=version.id))
    db.commit()
    copy=db.scalar(select(TeachingCopy).where(TeachingCopy.case_version_id==version.id))
    if copy:
        rule_snapshots = copy.desensitization_rules
    else:
        rule_snapshots = [
            {"id": rule.id, "mode": rule.mode, "geometry": rule.geometry, "title": rule.title, "description": rule.description or ""}
            for rule in db.scalars(select(DesensitizationRule).where(DesensitizationRule.case_version_id == version.id, DesensitizationRule.mode == "HIDE", DesensitizationRule.status == "APPLIED")).all()
        ]
    rules=[{**rule,"enforced":False,"preview":True} for rule in rule_snapshots]
    return APIResponse(data={"versionId": version.id, "manifestUrl": f"{settings.api_v1_prefix}/viewer-assets/{version.id}/metadata.json", "initialCamera": {}, "pointBudget": 1000000, "capabilities": {"annotations": True, "measurements": True}, "forcedDesensitizationRules":rules}, request_id=request_id)

@router.get("/viewer-assets/{version_id}/{asset_path:path}")
def viewer_asset(version_id: str, asset_path: str, request: Request, db: Annotated[Session, Depends(get_db)]):
    token = request.cookies.get(f"viewer_{version_id}")
    try:
        claims = jwt.decode(token or "", settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if claims.get("type") not in {"viewer", "student_viewer"} or claims.get("version") != version_id: raise ValueError()
    except Exception: raise HTTPException(401, "Viewer asset credential is invalid or expired")
    version = db.scalar(select(CaseVersion).where(CaseVersion.id == version_id))
    if version is None: raise HTTPException(404, "Case version not found")
    if claims.get("type") == "student_viewer":
        try:
            student = db.get(User, int(claims["sub"]))
        except (KeyError, TypeError, ValueError):
            raise HTTPException(401, "Viewer asset credential is invalid")
        if student is None: raise HTTPException(401, "Viewer asset credential is invalid")
        _, checked_version, copy = require_open_task(db, claims.get("task"), student, version_id)
        if checked_version.id != version.id: raise HTTPException(401, "Viewer asset credential is invalid")
        root = (Path(settings.storage_root).resolve() / copy.manifest_key).resolve().parent
    else:
        version = _ready(db, version_id)
        root = (Path(settings.storage_root).resolve() / "cases" / version.case_id / "versions" / version.id / "potree").resolve()
    target = (root / asset_path).resolve()
    if root not in target.parents and target != root: raise HTTPException(404, "Asset not found")
    if target.suffix.lower() not in {".json", ".bin"}: raise HTTPException(404, "Asset not found")
    if not target.is_file(): raise HTTPException(404, "Asset not found")
    db.add(AuditLog(action="VIEWER_ASSET_ACCESSED", actor_id=int(claims["sub"]), case_id=version.case_id, case_version_id=version.id, detail={"asset": asset_path}))
    db.commit()
    return FileResponse(target)

@router.get("/case-versions/{version_id}/annotations")
def annotations(version_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id)
    rows = db.scalars(select(Annotation).where(Annotation.case_version_id == version_id, Annotation.owner_id == admin.id, Annotation.scope == "ADMIN_WORKSPACE")).all()
    return APIResponse(data=[_annotation(row) for row in rows], request_id=request_id)

@router.post("/case-versions/{version_id}/annotations", status_code=201)
def create_annotation(version_id: str, payload: AnnotationCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id); item = Annotation(case_version_id=version_id, owner_id=admin.id, scope="ADMIN_WORKSPACE", type=payload.type, geometry=payload.geometry, title=payload.title, description=payload.description, viewer_state=payload.viewer_state); db.add(item); db.flush(); db.add(AuditLog(action="ANNOTATION_CREATED", actor_id=admin.id, case_version_id=version_id, detail={"annotationId": item.id})); db.commit(); db.refresh(item); return APIResponse(data=_annotation(item), request_id=request_id)

@router.put("/annotations/{annotation_id}")
def update_annotation(annotation_id: str, payload: AnnotationCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    item = db.scalar(select(Annotation).where(Annotation.id == annotation_id));
    if item is None: raise HTTPException(404, "Annotation not found")
    if item.owner_id != admin.id or item.scope != "ADMIN_WORKSPACE": raise HTTPException(403, "Only the owner may modify this annotation")
    for key, value in {"type": payload.type, "geometry": payload.geometry, "title": payload.title, "description": payload.description, "viewer_state": payload.viewer_state}.items(): setattr(item, key, value)
    db.add(AuditLog(action="ANNOTATION_UPDATED", actor_id=admin.id, case_version_id=item.case_version_id, detail={"annotationId": item.id})); db.commit(); db.refresh(item); return APIResponse(data=_annotation(item), request_id=request_id)

@router.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    item = db.scalar(select(Annotation).where(Annotation.id == annotation_id));
    if item is None: raise HTTPException(404, "Annotation not found")
    if item.owner_id != admin.id or item.scope != "ADMIN_WORKSPACE": raise HTTPException(403, "Only the owner may delete this annotation")
    db.add(AuditLog(action="ANNOTATION_DELETED", actor_id=admin.id, case_version_id=item.case_version_id, detail={"annotationId": item.id})); db.delete(item); db.commit(); return APIResponse(data={}, request_id=request_id)

@router.get("/case-versions/{version_id}/measurements")
def measurements(version_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id); rows = db.scalars(select(Measurement).where(Measurement.case_version_id == version_id, Measurement.owner_id == admin.id)).all(); return APIResponse(data=[_measurement(row) for row in rows], request_id=request_id)

@router.post("/case-versions/{version_id}/measurements", status_code=201)
def create_measurement(version_id: str, payload: MeasurementCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id)
    values=measurement_values(payload.start_point,payload.end_point)
    item = Measurement(case_version_id=version_id, owner_id=admin.id, start_point=values["start"], end_point=values["end"], distance=values["distance"], title=payload.title, description=payload.description, viewer_state=payload.viewer_state); db.add(item); db.flush(); db.add(AuditLog(action="MEASUREMENT_CREATED", actor_id=admin.id, case_version_id=version_id, detail={"measurementId": item.id,"title":item.title})); db.commit(); db.refresh(item); return APIResponse(data=_measurement(item), request_id=request_id)

@router.delete("/measurements/{measurement_id}")
def delete_measurement(measurement_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    item = db.scalar(select(Measurement).where(Measurement.id == measurement_id));
    if item is None: raise HTTPException(404, "Measurement not found")
    if item.owner_id != admin.id: raise HTTPException(403, "Only the owner may delete this measurement")
    db.add(AuditLog(action="MEASUREMENT_DELETED", actor_id=admin.id, case_version_id=item.case_version_id, detail={"measurementId": item.id})); db.delete(item); db.commit(); return APIResponse(data={}, request_id=request_id)

@router.get("/case-versions/{version_id}/area-measurements")
def area_measurements(version_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id)
    rows = db.scalars(select(AreaMeasurement).where(AreaMeasurement.case_version_id == version_id, AreaMeasurement.owner_id == admin.id)).all()
    return APIResponse(data=[_area_measurement(row) for row in rows], request_id=request_id)

@router.post("/case-versions/{version_id}/area-measurements", status_code=201)
def create_area_measurement(version_id: str, payload: AreaMeasurementCreate, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    _ready(db, version_id)
    values = area_measurement_values(payload.points)
    item = AreaMeasurement(case_version_id=version_id, owner_id=admin.id, points=values["points"], perimeter=values["perimeter"], area=values["area"], title=payload.title, description=payload.description, viewer_state=payload.viewer_state)
    db.add(item); db.flush(); db.add(AuditLog(action="AREA_MEASUREMENT_CREATED", actor_id=admin.id, case_version_id=version_id, detail={"areaMeasurementId": item.id, "pointCount": values["pointCount"], "title": item.title})); db.commit(); db.refresh(item)
    return APIResponse(data=_area_measurement(item), request_id=request_id)

@router.delete("/area-measurements/{area_measurement_id}")
def delete_area_measurement(area_measurement_id: str, admin: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]):
    item = db.scalar(select(AreaMeasurement).where(AreaMeasurement.id == area_measurement_id))
    if item is None: raise HTTPException(404, "Area measurement not found")
    if item.owner_id != admin.id: raise HTTPException(403, "Only the owner may delete this area measurement")
    db.add(AuditLog(action="AREA_MEASUREMENT_DELETED", actor_id=admin.id, case_version_id=item.case_version_id, detail={"areaMeasurementId": item.id, "pointCount": len(item.points), "title": item.title})); db.delete(item); db.commit()
    return APIResponse(data={}, request_id=request_id)
