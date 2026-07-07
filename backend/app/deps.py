from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User
from .services.auth import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def active_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(401, "Sessão expirada. Inicia sessão novamente.")
    return user


def _user_from_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user = db.get(User, payload["sub"])
    if not user:
        return None
    token_tv = payload.get("tv", 0)
    if not isinstance(token_tv, int):
        token_tv = 0
    if user.token_version != token_tv:
        return None
    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get("sync2meet_token")
    user = _user_from_token(db, token)
    if user:
        request.state.user = user
        return user

    if (
        settings.dev_auth_bypass
        and not settings.is_production
        and not settings.auth_enabled
    ):
        user = db.query(User).order_by(User.created_at.asc()).first()
        if user:
            request.state.user = user
            return user
        raise HTTPException(503, "Nenhum utilizador configurado.")

    raise HTTPException(401, "Sessão expirada. Inicia sessão novamente.")


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Apenas administradores podem executar esta ação.")
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User | None:
    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get("sync2meet_token")
    return _user_from_token(db, token)
