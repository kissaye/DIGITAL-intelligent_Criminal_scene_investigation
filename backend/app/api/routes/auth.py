from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_request_id
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenData, UserProfile
from app.schemas.common import APIResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


def to_profile(user: User) -> UserProfile:
    return UserProfile(id=user.id, username=user.username, display_name=user.display_name, roles=sorted(role.code for role in user.roles))


@router.post("/login", response_model=APIResponse[TokenData], summary="Log in")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[TokenData]:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token, expires_in = create_access_token(user.username)
    return APIResponse(data=TokenData(access_token=token, token_type="bearer", expires_in=expires_in, user=to_profile(user)), request_id=request_id)


@router.get("/me", response_model=APIResponse[UserProfile], summary="Current user")
def me(user: Annotated[User, Depends(get_current_user)], request_id: Annotated[str, Depends(get_request_id)]) -> APIResponse[UserProfile]:
    return APIResponse(data=to_profile(user), request_id=request_id)
