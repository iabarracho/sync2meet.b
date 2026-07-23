from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

from ..config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    )
    return hmac.compare_digest(digest.hex(), expected)


def create_access_token(user_id: str, token_version: int = 0) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + settings.auth_token_hours * 3600,
        "tv": token_version,
    }
    data = urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    sig = hmac.new(
        settings.auth_secret.encode("utf-8"),
        data.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{data}.{sig}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    data, sig = token.rsplit(".", 1)
    expected = hmac.new(
        settings.auth_secret.encode("utf-8"),
        data.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(urlsafe_b64decode(data.encode("ascii")))
    except (json.JSONDecodeError, ValueError):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None
    if not payload.get("sub"):
        return None
    return payload


def email_domain_allowed(email: str, *, role: str | None = None) -> bool:
    """Admin pode usar qualquer email; restantes só domínios configurados."""
    if role == "admin":
        return True
    domains = settings.allowed_email_domains_list
    if not domains:
        return True
    parts = email.lower().strip().rsplit("@", 1)
    if len(parts) != 2 or not parts[0]:
        return False
    host = parts[1]
    return host in domains


def allowed_domains_label() -> str:
    domains = settings.allowed_email_domains_list
    if not domains:
        return ""
    return ", ".join(f"@{d}" for d in domains)
