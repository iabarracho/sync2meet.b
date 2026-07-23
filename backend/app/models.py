from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MeetingStatus(str, enum.Enum):
    draft = "draft"
    agenda_ready = "agenda_ready"
    in_progress = "in_progress"
    recorded = "recorded"
    processing = "processing"
    minutes_ready = "minutes_ready"
    pending_approval = "pending_approval"
    approved = "approved"
    distributed = "distributed"


class DocumentKind(str, enum.Enum):
    agenda = "agenda"
    minutes = "minutes"


class ActionItemStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"


class TemplateType(str, enum.Enum):
    agenda = "agenda"
    minutes = "minutes"


class TemplateSource(str, enum.Enum):
    builtin = "builtin"
    docx = "docx"
    pdf = "pdf"
    markdown = "markdown"


# --------------------------------------------------------------------------- #
# Core entities
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="member")  # admin | member
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meetings: Mapped[list["Meeting"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    client_name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    meeting_date: Mapped[date | None] = mapped_column(Date)
    meeting_time: Mapped[time | None] = mapped_column(Time)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus), default=MeetingStatus.draft, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, index=True
    )

    owner: Mapped[User | None] = relationship(back_populates="meetings")
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    agendas: Mapped[list["Agenda"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    recordings: Mapped[list["Recording"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["Summary"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    email_logs: Mapped[list["EmailLog"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    email_distributions: Mapped[list["EmailDistribution"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    slack_logs: Mapped[list["SlackLog"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str | None] = mapped_column(String)
    slack_username: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="participants")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[TemplateType] = mapped_column(Enum(TemplateType), index=True)
    source: Mapped[TemplateSource] = mapped_column(
        Enum(TemplateSource), default=TemplateSource.builtin
    )
    # Raw template body (markdown-ish). Built-ins keep the spec structure.
    content: Mapped[str] = mapped_column(Text, default="")
    # AI-extracted structure: sections, tables, placeholders.
    structure: Mapped[dict | None] = mapped_column(JSON)
    original_file_path: Mapped[str | None] = mapped_column(String)
    is_default: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Agenda(Base):
    __tablename__ = "agendas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    template_id: Mapped[str | None] = mapped_column(ForeignKey("templates.id"))
    content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    pdf_path: Mapped[str | None] = mapped_column(String)
    docx_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    meeting: Mapped[Meeting] = relationship(back_populates="agendas")


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="upload")  # upload|teams|zoom|meet|direct
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="recordings")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    recording_id: Mapped[str | None] = mapped_column(ForeignKey("recordings.id"))
    text: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str | None] = mapped_column(String)
    # [{speaker, start, end, text}]
    segments: Mapped[list | None] = mapped_column(JSON)
    provider: Mapped[str] = mapped_column(String, default="openai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="transcripts")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    transcript_id: Mapped[str | None] = mapped_column(ForeignKey("transcripts.id"))
    template_id: Mapped[str | None] = mapped_column(ForeignKey("templates.id"))
    # Rendered minutes document (markdown-ish following the template).
    content: Mapped[str] = mapped_column(Text, default="")
    short_summary: Mapped[str | None] = mapped_column(Text)
    # Structured analysis: topics, decisions, risks, dependencies, next_steps...
    analysis: Mapped[dict | None] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_approved: Mapped[bool] = mapped_column(default=False)
    pdf_path: Mapped[str | None] = mapped_column(String)
    docx_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    meeting: Mapped[Meeting] = relationship(back_populates="summaries")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    summary_id: Mapped[str | None] = mapped_column(ForeignKey("summaries.id"))
    task: Mapped[str] = mapped_column(Text, nullable=False)
    assignee_name: Mapped[str | None] = mapped_column(String)
    assignee_slack: Mapped[str | None] = mapped_column(String)
    timing: Mapped[str | None] = mapped_column(String)  # free-form "até 15/07"
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ActionItemStatus] = mapped_column(
        Enum(ActionItemStatus), default=ActionItemStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="action_items")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    summary_id: Mapped[str] = mapped_column(ForeignKey("summaries.id"))
    approved_by: Mapped[str | None] = mapped_column(String)
    approved_version: Mapped[int] = mapped_column(Integer, default=1)
    locked_content: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str | None] = mapped_column(String)
    docx_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="approvals")


class EmailDistribution(Base):
    """One email send batch for a meeting (idempotent unit of work)."""

    __tablename__ = "email_distributions"
    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "idempotency_key",
            name="uq_distribution_meeting_idempotency",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    summary_id: Mapped[str] = mapped_column(ForeignKey("summaries.id"))
    idempotency_key: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending | sending | completed | partial | failed | scheduled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    meeting: Mapped[Meeting] = relationship(back_populates="email_distributions")
    logs: Mapped[list["EmailLog"]] = relationship(
        back_populates="distribution", cascade="all, delete-orphan"
    )


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    distribution_id: Mapped[str | None] = mapped_column(
        ForeignKey("email_distributions.id", ondelete="CASCADE"), index=True
    )
    to_email: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    attachments: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="sent")
    provider: Mapped[str] = mapped_column(String, default="smtp")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="email_logs")
    distribution: Mapped["EmailDistribution | None"] = relationship(
        back_populates="logs"
    )


class JobType(str, enum.Enum):
    transcribe = "transcribe"
    agenda = "agenda"
    minutes = "minutes"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.pending, index=True
    )
    payload: Mapped[dict | None] = mapped_column(JSON)
    result_id: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text)
    # Set while pending/running to enforce one active job per meeting+type.
    active_key: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    meeting: Mapped[Meeting] = relationship(back_populates="processing_jobs")


class SlackLog(Base):
    __tablename__ = "slack_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String, default="")
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="sent")
    provider: Mapped[str] = mapped_column(String, default="slack")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    meeting: Mapped[Meeting] = relationship(back_populates="slack_logs")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String, index=True)
    user_email: Mapped[str | None] = mapped_column(String)
    resource_type: Mapped[str | None] = mapped_column(String)
    resource_id: Mapped[str | None] = mapped_column(String, index=True)
    detail: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )
