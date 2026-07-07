from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import User
from ..models import (
    ActionItem,
    ActionItemStatus,
    EmailLog,
    Meeting,
    MeetingStatus,
    SlackLog,
)
from ..schemas import DashboardStats

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


def _meeting_scope_ids(db: Session, user: User):
    query = db.query(Meeting.id)
    if settings.auth_enabled and user.role != "admin":
        query = query.filter(Meeting.owner_id == user.id)
    return {row[0] for row in query.all()}


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    meeting_ids = _meeting_scope_ids(db, user)

    if not meeting_ids:
        return DashboardStats(
            total_meetings=0,
            meetings_this_week=0,
            pending_approval=0,
            completed_meetings=0,
            pending_action_items=0,
            emails_sent=0,
            slack_messages_sent=0,
        )

    total = len(meeting_ids)
    this_week = (
        db.query(func.count(Meeting.id))
        .filter(Meeting.id.in_(meeting_ids), Meeting.meeting_date >= week_start)
        .scalar()
        or 0
    )
    pending_approval = (
        db.query(func.count(Meeting.id))
        .filter(
            Meeting.id.in_(meeting_ids),
            Meeting.status == MeetingStatus.pending_approval,
        )
        .scalar()
        or 0
    )
    completed = (
        db.query(func.count(Meeting.id))
        .filter(
            Meeting.id.in_(meeting_ids),
            Meeting.status.in_(
                [MeetingStatus.approved, MeetingStatus.distributed]
            ),
        )
        .scalar()
        or 0
    )
    pending_actions = (
        db.query(func.count(ActionItem.id))
        .filter(
            ActionItem.meeting_id.in_(meeting_ids),
            ActionItem.status == ActionItemStatus.pending,
        )
        .scalar()
        or 0
    )
    emails = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.meeting_id.in_(meeting_ids),
            EmailLog.status == "sent",
        )
        .scalar()
        or 0
    )
    slack = (
        db.query(func.count(SlackLog.id))
        .filter(
            SlackLog.meeting_id.in_(meeting_ids),
            SlackLog.status == "sent",
        )
        .scalar()
        or 0
    )

    return DashboardStats(
        total_meetings=total,
        meetings_this_week=this_week,
        pending_approval=pending_approval,
        completed_meetings=completed,
        pending_action_items=pending_actions,
        emails_sent=emails,
        slack_messages_sent=slack,
    )
