from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..models import PasswordResetToken, User
from .auth import hash_password
from .email import send_password_reset_email


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _reset_base_url() -> str:
    if settings.app_public_url.strip():
        return settings.app_public_url.rstrip("/")
    return "http://127.0.0.1:3000"


def build_reset_link(token: str) -> str:
    return f"{_reset_base_url()}/reset-password?token={token}"


def request_password_reset(db: Session, email: str) -> tuple[bool, str | None]:
    """Create token and send email. Returns (sent, error)."""
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not user.password_hash:
        return True, None

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: datetime.now(timezone.utc)})

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.password_reset_hours
    )
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(token),
            expires_at=expires_at,
        )
    )
    db.commit()

    link = build_reset_link(token)
    status, error = send_password_reset_email(
        to_email=user.email,
        user_name=user.name,
        reset_link=link,
        expires_hours=settings.password_reset_hours,
    )
    if status != "sent":
        return False, error
    return True, None


def reset_password_with_token(
    db: Session, token: str, new_password: str
) -> User | None:
    token_hash = _hash_token(token.strip())
    now = datetime.now(timezone.utc)
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    if not row:
        return None

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        return None

    user.password_hash = hash_password(new_password)
    user.token_version += 1
    row.used_at = now
    db.commit()
    db.refresh(user)
    return user
