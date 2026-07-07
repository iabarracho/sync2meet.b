from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

from ..config import settings

_lock = Lock()
_attempts: dict[str, list[float]] = defaultdict(list)

# (max attempts, window seconds)
AUTH_LIMIT = (20, 300)
UPLOAD_LIMIT = (40, 3600)
TRANSCRIBE_LIMIT = (15, 3600)

_LIMITS: dict[str, tuple[int, int]] = {
    "login": AUTH_LIMIT,
    "register": AUTH_LIMIT,
    "upload": UPLOAD_LIMIT,
    "transcribe": TRANSCRIBE_LIMIT,
}


def _client_ip(request: Request) -> str:
    if settings.trusted_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _client_key(request: Request, suffix: str) -> str:
    return f"{_client_ip(request)}:{suffix}"


def check_rate_limit(request: Request, *, bucket: str) -> None:
    """Simple in-memory rate limiter."""
    key = _client_key(request, bucket)
    max_attempts, window = _LIMITS.get(bucket, AUTH_LIMIT)
    now = time.time()
    cutoff = now - window
    with _lock:
        hits = [t for t in _attempts[key] if t > cutoff]
        if len(hits) >= max_attempts:
            raise HTTPException(
                429,
                "Demasiados pedidos. Aguarda alguns minutos e tenta novamente.",
            )
        hits.append(now)
        _attempts[key] = hits


def reset_rate_limit(request: Request, *, bucket: str) -> None:
    key = _client_key(request, bucket)
    with _lock:
        _attempts.pop(key, None)
