from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: str, tenant_id: str) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "tenant_id": tenant_id, "exp": expires, "iat": datetime.now(timezone.utc)},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM], options={"require": ["sub", "tenant_id", "exp"]})
    except InvalidTokenError as exc:
        raise ValueError("Invalid access token") from exc
    if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("tenant_id"), str):
        raise ValueError("Invalid access token")
    return payload
