# Author: Pradeep Sahoo — Retail Nexus AI
"""JWT auth, role-based authorization, password hashing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import get_settings


class Role(str, Enum):
    ANALYST = "supply_chain_analyst"
    STORE_MANAGER = "store_manager"
    PROCUREMENT = "procurement_manager"
    DIRECTOR = "supply_chain_director"
    ADMIN = "administrator"


# Which roles can approve which recommendation risk levels.
# Keyed role -> allowed max risk tier.
APPROVAL_AUTHORITY: dict[Role, int] = {
    Role.ANALYST: 1,       # Informational / Low
    Role.STORE_MANAGER: 2,  # +Medium
    Role.PROCUREMENT: 3,    # +High
    Role.DIRECTOR: 4,       # +Critical
    Role.ADMIN: 4,
}

RISK_TIER_VALUE: dict[str, int] = {
    "INFORMATIONAL": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


class TokenPayload(BaseModel):
    sub: str
    role: Role
    exp: int


class User(BaseModel):
    username: str
    role: Role
    display_name: str


_PWD = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dev-only in-memory user store. Swap for DB-backed when real auth is wired.
_DEV_USERS: dict[str, dict] = {
    "demo-analyst": {"password": _PWD.hash("demo"), "role": Role.ANALYST, "display": "Demo Analyst"},
    "demo-manager": {"password": _PWD.hash("demo"), "role": Role.STORE_MANAGER, "display": "Demo Store Manager"},
    "demo-procurement": {"password": _PWD.hash("demo"), "role": Role.PROCUREMENT, "display": "Demo Procurement"},
    "demo-director": {"password": _PWD.hash("demo"), "role": Role.DIRECTOR, "display": "Demo Director"},
    "demo-admin": {"password": _PWD.hash("demo"), "role": Role.ADMIN, "display": "Demo Admin"},
}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def verify_password(plain: str, hashed: str) -> bool:
    return _PWD.verify(plain, hashed)


def authenticate(username: str, password: str) -> User | None:
    rec = _DEV_USERS.get(username)
    if not rec or not verify_password(password, rec["password"]):
        return None
    return User(username=username, role=rec["role"], display_name=rec["display"])


def create_access_token(user: User) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user.username, "role": user.role.value, "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        data = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**data)
    except (JWTError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token") from e


def current_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    data = _decode(token)
    rec = _DEV_USERS.get(data.sub)
    display = rec["display"] if rec else data.sub
    return User(username=data.sub, role=data.role, display_name=display)


def optional_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> User | None:
    if not token:
        return None
    try:
        data = _decode(token)
    except HTTPException:
        return None
    rec = _DEV_USERS.get(data.sub)
    display = rec["display"] if rec else data.sub
    return User(username=data.sub, role=data.role, display_name=display)


def require_roles(*roles: Role):
    def _dep(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles and Role.ADMIN not in roles and user.role != Role.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        if user.role not in roles and user.role != Role.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return user
    return _dep


def can_approve(user: User, risk_tier: str) -> bool:
    max_tier = APPROVAL_AUTHORITY.get(user.role, 0)
    needed = RISK_TIER_VALUE.get(risk_tier.upper(), 4)
    return max_tier >= needed
