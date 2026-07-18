from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
import bcrypt
from jose import JWTError, jwt
from typing import Any

from enterprise_rag_common.config import settings
from enterprise_rag_common.enums import UserRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, role: UserRole, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "region": settings.data_region,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def can_access_document(user_role: UserRole, allowed_roles: list[UserRole]) -> bool:
    if user_role == UserRole.ADMIN:
        return True
    return user_role in allowed_roles
