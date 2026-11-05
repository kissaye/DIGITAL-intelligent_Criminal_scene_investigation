"""M5 publication validity rules shared by teacher, student and viewer routes."""
from datetime import UTC, datetime
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.case import Case, CaseAuthorization, TeachingCopy
from app.core.config import get_settings

def utc(value: datetime | None) -> datetime | None:
    if value is None: return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

def require_teaching_version(db: Session, version):
    if version is None or version.status != "PUBLISHED":
        raise HTTPException(409, "Published teaching version required")
    copy = db.scalar(select(TeachingCopy).where(TeachingCopy.case_version_id == version.id))
    authorization = db.get(CaseAuthorization, copy.authorization_id) if copy else None
    case = db.get(Case, version.case_id)
    now = datetime.now(UTC)
    if (copy is None or authorization is None or case is None or authorization.revoked_at is not None
            or utc(authorization.valid_until) <= now or utc(copy.valid_until) <= now
            or (case.valid_until is not None and utc(case.valid_until) <= now)):
        raise HTTPException(409, "Teaching publication or authorization is expired or revoked")
    try:
        root = Path(get_settings().storage_root).resolve()
        key = Path(copy.manifest_key)
        if not root.is_dir() or key.is_absolute() or ".." in key.parts:
            raise ValueError()
        unresolved = root / key
        current = root
        for part in key.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError()
        manifest = unresolved.resolve()
        copy_root = manifest.parent
        if (root not in manifest.parents or manifest.name != "metadata.json"
                or not copy_root.is_dir() or copy_root.is_symlink()
                or manifest.is_symlink() or not manifest.is_file()):
            raise ValueError()
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(409, "Teaching manifest is unavailable or unsafe")
    return copy
