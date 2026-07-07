from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import (
    ActionItemStatus,
    MeetingStatus,
    TemplateSource,
    TemplateType,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Participants
# --------------------------------------------------------------------------- #
class ParticipantBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: str | None = Field(default=None, max_length=80)
    slack_username: str | None = Field(default=None, max_length=80)


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    slack_username: str | None = None


class ParticipantOut(ORMModel, ParticipantBase):
    id: str
    meeting_id: str


class ParticipantImport(BaseModel):
    participants: list[ParticipantCreate]


# --------------------------------------------------------------------------- #
# Meetings
# --------------------------------------------------------------------------- #
class MeetingBase(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    meeting_date: date | None = None
    meeting_time: time | None = None
    description: str | None = Field(default=None, max_length=5000)


class MeetingCreate(MeetingBase):
    participants: list[ParticipantCreate] = []


class MeetingUpdate(BaseModel):
    client_name: str | None = None
    title: str | None = None
    meeting_date: date | None = None
    meeting_time: time | None = None
    description: str | None = None


class MeetingOut(ORMModel, MeetingBase):
    id: str
    status: MeetingStatus
    created_at: datetime
    updated_at: datetime
    participants: list[ParticipantOut] = []


class MeetingListItem(ORMModel):
    id: str
    client_name: str
    title: str
    meeting_date: date | None = None
    status: MeetingStatus
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
class TemplateBase(BaseModel):
    name: str
    type: TemplateType
    content: str = ""


class TemplateCreate(TemplateBase):
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    is_default: bool | None = None


class TemplateOut(ORMModel):
    id: str
    name: str
    type: TemplateType
    source: TemplateSource
    content: str
    structure: dict[str, Any] | None = None
    is_default: bool
    can_delete: bool = True
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Agendas
# --------------------------------------------------------------------------- #
class AgendaGenerateRequest(BaseModel):
    template_id: str | None = None


class AgendaUpdate(BaseModel):
    content: str


class AgendaOut(ORMModel):
    id: str
    meeting_id: str
    template_id: str | None = None
    content: str
    version: int
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Recordings / Transcripts
# --------------------------------------------------------------------------- #
class RecordingOut(ORMModel):
    id: str
    meeting_id: str
    filename: str
    mime_type: str | None = None
    source: str
    size_bytes: int | None = None
    duration_seconds: float | None = None
    created_at: datetime


class TranscriptSegment(BaseModel):
    speaker: str
    start: float
    end: float
    text: str


class TranscriptOut(ORMModel):
    id: str
    meeting_id: str
    recording_id: str | None = None
    text: str
    language: str | None = None
    segments: list[dict[str, Any]] | None = None
    provider: str
    created_at: datetime


class GoogleMeetImportOut(BaseModel):
    import_type: str  # recording | transcript
    message: str
    recording: RecordingOut | None = None
    transcript: TranscriptOut | None = None


# --------------------------------------------------------------------------- #
# Summaries / Minutes
# --------------------------------------------------------------------------- #
class SummaryGenerateRequest(BaseModel):
    template_id: str | None = None


class SummaryUpdate(BaseModel):
    content: str | None = None
    short_summary: str | None = None


class SummaryOut(ORMModel):
    id: str
    meeting_id: str
    transcript_id: str | None = None
    template_id: str | None = None
    content: str
    short_summary: str | None = None
    analysis: dict[str, Any] | None = None
    version: int
    is_approved: bool
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Action items
# --------------------------------------------------------------------------- #
class ActionItemBase(BaseModel):
    task: str
    assignee_name: str | None = None
    assignee_slack: str | None = None
    timing: str | None = None
    due_date: date | None = None


class ActionItemCreate(ActionItemBase):
    pass


class ActionItemUpdate(BaseModel):
    task: str | None = None
    assignee_name: str | None = None
    assignee_slack: str | None = None
    timing: str | None = None
    due_date: date | None = None
    status: ActionItemStatus | None = None


class ActionItemOut(ORMModel, ActionItemBase):
    id: str
    meeting_id: str
    status: ActionItemStatus
    created_at: datetime


# --------------------------------------------------------------------------- #
# Approvals
# --------------------------------------------------------------------------- #
class ApprovalRequest(BaseModel):
    summary_id: str


class ApprovalOut(ORMModel):
    id: str
    meeting_id: str
    summary_id: str
    approved_by: str | None = None
    approved_version: int
    created_at: datetime


# --------------------------------------------------------------------------- #
# Distribution
# --------------------------------------------------------------------------- #
class EmailSendRequest(BaseModel):
    scheduled_for: datetime | None = None  # None => send now
    idempotency_key: str | None = None
    force_resend: bool = False


class EmailLogOut(ORMModel):
    id: str
    meeting_id: str
    distribution_id: str | None = None
    to_email: str
    subject: str
    status: str
    provider: str
    error: str | None = None
    scheduled_for: datetime | None = None
    created_at: datetime


class EmailDistributionOut(ORMModel):
    id: str
    meeting_id: str
    summary_id: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    logs: list[EmailLogOut] = []


class SlackPreviewOut(BaseModel):
    channel: str
    message: str


class SlackSendRequest(BaseModel):
    channel: str | None = None


class SlackLogOut(ORMModel):
    id: str
    meeting_id: str
    channel: str
    message: str
    status: str
    provider: str
    created_at: datetime


# --------------------------------------------------------------------------- #
# Background jobs
# --------------------------------------------------------------------------- #
class JobOut(ORMModel):
    id: str
    meeting_id: str
    job_type: str
    status: str
    result_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
class DashboardStats(BaseModel):
    total_meetings: int
    meetings_this_week: int
    pending_approval: int
    completed_meetings: int
    pending_action_items: int
    emails_sent: int
    slack_messages_sent: int


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthConfigOut(BaseModel):
    auth_enabled: bool
    allow_registration: bool
    max_team_users: int
    users_count: int | None = None
    allowed_email_domains: list[str] = []


class UserOut(ORMModel):
    id: str
    name: str
    email: str
    role: str


class AuthSessionOut(BaseModel):
    """Sessão criada — token só via cookie HttpOnly, não no JSON."""

    user: UserOut


class TokenOut(AuthSessionOut):
    """Resposta interna (proxy Next.js lê o cookie Set-Cookie do backend)."""

    access_token: str = ""
    token_type: str = "bearer"
