from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_request_id(request: Request) -> str:
    return request.state.request_id


def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)], db: Annotated[Session, Depends(get_db)]) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token is required", headers={"WWW-Authenticate": "Bearer"})
    username = decode_access_token(credentials.credentials)
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not available", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if "ADMIN" not in {role.code for role in user.roles}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role is required")
    return user
