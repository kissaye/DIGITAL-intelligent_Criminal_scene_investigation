from datetime import UTC, datetime
from fastapi import HTTPException
from sqlalchemy import select
from app.models.case import Case
from app.models.publication import CaseAuthorization, TeachingCopy
from app.services.practice_access import utc


def require_teaching_version(db, version):
    if not version or version.status != 'PUBLISHED':
        raise HTTPException(409, 'Published teaching version required')
    copy = db.scalar(select(TeachingCopy).where(TeachingCopy.version_id == version.id))
    authorization = db.get(CaseAuthorization, copy.authorization_id) if copy else None
    case = db.get(Case, version.case_id)
    now = datetime.now(UTC)
    if not copy or not authorization or authorization.revoked_at or utc(copy.valid_until) <= now or utc(authorization.valid_until) <= now or (case.valid_until and utc(case.valid_until) <= now):
        raise HTTPException(409, 'Teaching publication or authorization is expired/revoked')
    return copy
