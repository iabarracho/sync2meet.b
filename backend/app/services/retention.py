from __future__ import annotations



import logging

from datetime import datetime, timedelta, timezone



from sqlalchemy.orm import Session



from ..config import settings

from ..models import Meeting

from . import storage as storage_service



logger = logging.getLogger("sync2meet.retention")





def purge_expired_meetings(db: Session) -> int:

    """Remove meetings older than meeting_retention_days (DB + ficheiros)."""

    days = settings.meeting_retention_days

    if days <= 0:

        return 0



    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    expired = (

        db.query(Meeting)

        .filter(Meeting.created_at < cutoff)

        .order_by(Meeting.created_at.asc())

        .all()

    )

    if not expired:

        return 0



    meeting_ids = [m.id for m in expired]

    for meeting in expired:

        db.delete(meeting)



    db.commit()



    for meeting_id in meeting_ids:

        storage_service.delete_meeting_storage(meeting_id)



    logger.info(

        "Retention: apagadas %d reunião(ões) com mais de %d dias",

        len(meeting_ids),

        days,

    )

    return len(meeting_ids)


