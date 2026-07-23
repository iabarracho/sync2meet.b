from __future__ import annotations

from unittest.mock import patch

from app.models import PasswordResetToken, User
from app.services.auth import hash_password, verify_password
from app.services import password_reset as password_reset_service
from app.services.password_reset import _hash_token
import secrets


def test_request_password_reset_unknown_email(db):
    status, error = password_reset_service.request_password_reset(
        db, "nobody@example.com"
    )
    assert status == "not_found"
    assert error is None


def test_request_password_reset_sends_for_existing_user(db):
    user = User(
        name="Test",
        email="user@example.com",
        role="member",
        password_hash=hash_password("old-password"),
    )
    db.add(user)
    db.commit()

    with patch.object(
        password_reset_service,
        "send_password_reset_email",
        return_value=("sent", None),
    ), patch.object(
        password_reset_service,
        "build_reset_link",
        return_value="http://test/reset",
    ):
        status, error = password_reset_service.request_password_reset(
            db, user.email
        )

    assert status == "sent"
    assert error is None


def test_reset_password_with_valid_token(db):
    user = User(
        name="Test",
        email="reset@example.com",
        role="member",
        password_hash=hash_password("old-password"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    with patch.object(
        password_reset_service,
        "send_password_reset_email",
        return_value=("sent", None),
    ), patch.object(
        password_reset_service,
        "build_reset_link",
        return_value="http://test/reset",
    ):
        password_reset_service.request_password_reset(db, user.email)

    token = secrets.token_urlsafe(32)
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .first()
    )
    row.token_hash = _hash_token(token)
    db.commit()

    updated = password_reset_service.reset_password_with_token(
        db, token, "new-password-123"
    )
    assert updated is not None
    assert verify_password("new-password-123", updated.password_hash)
    assert updated.token_version == 1


def test_reset_password_rejects_invalid_token(db):
    user = User(
        name="Test",
        email="other@example.com",
        role="member",
        password_hash=hash_password("secret"),
    )
    db.add(user)
    db.commit()

    assert (
        password_reset_service.reset_password_with_token(
            db, "invalid-token", "new-password-123"
        )
        is None
    )
