from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditEvent

logger = logging.getLogger("sync2meet.audit")


def log_audit(
    db: Session,
    *,
    action: str,
    user_id: str | None = None,
    user_email: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    meta: dict[str, Any] | None = None,
    commit: bool = True,
) -> None:
    event = AuditEvent(
        action=action,
        user_id=user_id,
        user_email=user_email,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        meta=meta or {},
    )
    db.add(event)
    if commit:
        db.commit()
    logger.info(
        "audit action=%s user=%s resource=%s:%s detail=%s",
        action,
        user_email or user_id,
        resource_type,
        resource_id,
        detail,
    )
