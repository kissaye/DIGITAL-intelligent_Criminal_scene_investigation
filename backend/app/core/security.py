from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import get_settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def create_access_token(subject: str) -> tuple[str, int]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return (jwt.encode({"sub": subject, "exp": expires_at, "type": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), settings.access_token_expire_minutes * 60)


def decode_access_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        if payload.get("type") != "access" or not isinstance(subject, str):
            raise InvalidTokenError("Invalid token claims")
        return subject
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}) from exc
