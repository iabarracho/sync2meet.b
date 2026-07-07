from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models import (
    ActionItem,
    Agenda,
    Meeting,
    MeetingStatus,
    ProcessingJob,
    JobStatus,
    JobType,
    Recording,
    Summary,
    Template,
    TemplateType,
    Transcript,
)
from . import ai as ai_service
from . import documents as doc_service
from .openai_errors import friendly_openai_error
from .transcribe_errors import friendly_transcribe_error

logger = logging.getLogger("sync2meet.jobs")


def _job_active_key(meeting_id: str, job_type: JobType) -> str:
    return f"{meeting_id}:{job_type.value}"


def _touch_job(job: ProcessingJob) -> None:
    job.updated_at = datetime.now(timezone.utc)


def recover_stale_jobs(db: Session, meeting_id: str | None = None) -> int:
    """Mark jobs stuck in pending/running as failed so meetings can recover."""
    now = datetime.now(timezone.utc)
    running_cutoff = now - timedelta(minutes=settings.job_stale_minutes)
    pending_cutoff = now - timedelta(minutes=settings.job_pending_stale_minutes)
    query = db.query(ProcessingJob).filter(
        ProcessingJob.status.in_([JobStatus.pending, JobStatus.running]),
    )
    if meeting_id:
        query = query.filter(ProcessingJob.meeting_id == meeting_id)

    count = 0
    for job in query.all():
        cutoff = (
            pending_cutoff
            if job.status == JobStatus.pending
            else running_cutoff
        )
        if job.updated_at >= cutoff:
            continue
        job.status = JobStatus.failed
        job.active_key = None
        job.error = (
            "Job expirou (processo interrompido ou demasiado tempo). "
            "Tenta novamente."
        )
        _touch_job(job)
        meeting = db.get(Meeting, job.meeting_id)
        if meeting and meeting.status == MeetingStatus.processing:
            meeting.status = MeetingStatus.recorded
        count += 1
    if count:
        db.commit()
        logger.warning("Recovered %d stale job(s)", count)
    return count


def get_active_job(
    db: Session, meeting_id: str, job_type: JobType
) -> ProcessingJob | None:
    return (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.meeting_id == meeting_id,
            ProcessingJob.job_type == job_type,
            ProcessingJob.status.in_([JobStatus.pending, JobStatus.running]),
        )
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )


def enqueue_job(
    db: Session,
    meeting_id: str,
    job_type: JobType,
    background_tasks: BackgroundTasks,
    runner,
    *,
    payload: dict | None = None,
    meeting_status: MeetingStatus | None = None,
) -> ProcessingJob:
    """Create a job atomically; return existing active job if one is already running."""
    recover_stale_jobs(db, meeting_id)

    existing = get_active_job(db, meeting_id, job_type)
    if existing:
        return existing

    if meeting_status is not None:
        meeting = db.get(Meeting, meeting_id)
        if meeting:
            meeting.status = meeting_status

    job = ProcessingJob(
        meeting_id=meeting_id,
        job_type=job_type,
        status=JobStatus.pending,
        payload=payload or {},
        active_key=_job_active_key(meeting_id, job_type),
    )
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
    except IntegrityError:
        db.rollback()
        existing = get_active_job(db, meeting_id, job_type)
        if existing:
            return existing
        raise

    background_tasks.add_task(runner, job.id)
    return job


def get_job(db: Session, meeting_id: str, job_id: str) -> ProcessingJob | None:
    return (
        db.query(ProcessingJob)
        .filter(ProcessingJob.id == job_id, ProcessingJob.meeting_id == meeting_id)
        .first()
    )


def _set_job_status(
    db: Session,
    job: ProcessingJob,
    status: JobStatus,
    *,
    result_id: str | None = None,
    error: str | None = None,
) -> None:
    job.status = status
    if status in (JobStatus.completed, JobStatus.failed):
        job.active_key = None
    if result_id:
        job.result_id = result_id
    if error:
        job.error = error
    _touch_job(job)
    db.commit()


def _validate_template_type(template: Template, expected: TemplateType) -> None:
    if template.type != expected:
        raise ValueError(
            f"Template «{template.name}» é do tipo {template.type.value}, "
            f"esperado {expected.value}."
        )


def _next_agenda_version(db: Session, meeting_id: str) -> int:
    latest = (
        db.query(Agenda.version)
        .filter(Agenda.meeting_id == meeting_id)
        .order_by(Agenda.version.desc())
        .first()
    )
    return (latest[0] if latest else 0) + 1


def _next_summary_version(db: Session, meeting_id: str) -> int:
    latest = (
        db.query(Summary.version)
        .filter(Summary.meeting_id == meeting_id)
        .order_by(Summary.version.desc())
        .first()
    )
    return (latest[0] if latest else 0) + 1


def _transcript_text_from_result(result: dict) -> str:
    text = (result.get("text") or "").strip()
    if text:
        return text
    parts: list[str] = []
    for seg in result.get("segments") or []:
        if isinstance(seg, dict):
            seg_text = str(seg.get("text") or "").strip()
            if seg_text:
                parts.append(seg_text)
    return "\n\n".join(parts)


def run_transcribe_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        if job.status not in (JobStatus.pending, JobStatus.running):
            return
        _set_job_status(db, job, JobStatus.running)

        meeting = db.get(Meeting, job.meeting_id)
        if not meeting:
            _set_job_status(db, job, JobStatus.failed, error="Meeting not found")
            return

        rec = (
            db.query(Recording)
            .filter(Recording.meeting_id == job.meeting_id)
            .order_by(Recording.created_at.desc())
            .first()
        )
        if not rec or not Path(rec.file_path).is_file():
            _set_job_status(
                db, job, JobStatus.failed, error="Gravação não encontrada"
            )
            meeting.status = MeetingStatus.recorded
            db.commit()
            return

        db.query(Transcript).filter(
            Transcript.meeting_id == job.meeting_id,
            Transcript.provider.in_(("openai", "faster-whisper", "openai-whisper")),
        ).delete()

        result = asyncio.run(ai_service.transcribe_audio(Path(rec.file_path)))
        _touch_job(job)
        db.commit()
        transcript = Transcript(
            meeting_id=job.meeting_id,
            recording_id=rec.id,
            text=_transcript_text_from_result(result),
            language=result.get("language"),
            segments=result.get("segments"),
            provider=result.get("provider", "faster-whisper"),
        )
        db.add(transcript)
        meeting.status = MeetingStatus.recorded
        db.flush()
        _set_job_status(db, job, JobStatus.completed, result_id=transcript.id)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Transcribe job %s failed", job_id)
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job:
            meeting = db.get(Meeting, job.meeting_id)
            if meeting:
                meeting.status = MeetingStatus.recorded
            _set_job_status(db, job, JobStatus.failed, error=friendly_transcribe_error(exc))
    finally:
        db.close()


def run_agenda_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        if job.status not in (JobStatus.pending, JobStatus.running):
            return
        _set_job_status(db, job, JobStatus.running)

        meeting = db.get(Meeting, job.meeting_id)
        if not meeting:
            _set_job_status(db, job, JobStatus.failed, error="Meeting not found")
            return

        transcript = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == job.meeting_id)
            .order_by(Transcript.created_at.desc())
            .first()
        )
        if not transcript or not transcript.text.strip():
            _set_job_status(
                db,
                job,
                JobStatus.failed,
                error="Sem transcrição. Carrega áudio/transcrição primeiro.",
            )
            return

        template_id = (job.payload or {}).get("template_id")
        template = (
            db.get(Template, template_id)
            if template_id
            else db.query(Template)
            .filter(Template.type == TemplateType.agenda, Template.is_default.is_(True))
            .first()
        )
        if not template:
            _set_job_status(db, job, JobStatus.failed, error="No agenda template")
            return
        try:
            _validate_template_type(template, TemplateType.agenda)
        except ValueError as exc:
            _set_job_status(db, job, JobStatus.failed, error=str(exc))
            return

        meeting_date = (
            meeting.meeting_date.isoformat() if meeting.meeting_date else ""
        )
        analysis = asyncio.run(ai_service.analyze_transcript(transcript.text))
        base = doc_service.render_agenda_variables(
            template.content,
            meeting.client_name,
            meeting_date,
        )
        content = asyncio.run(
            ai_service.fill_template(
                base,
                {
                    "NOME CLIENTE": meeting.client_name,
                    "DATA": meeting_date,
                },
                analysis,
            )
        )

        agenda = Agenda(
            meeting_id=job.meeting_id,
            template_id=template.id,
            content=content,
            version=_next_agenda_version(db, job.meeting_id),
        )
        db.add(agenda)
        meeting.status = MeetingStatus.agenda_ready
        db.flush()
        _set_job_status(db, job, JobStatus.completed, result_id=agenda.id)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agenda job %s failed", job_id)
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job:
            _set_job_status(db, job, JobStatus.failed, error=friendly_openai_error(exc))
    finally:
        db.close()


def run_minutes_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        if job.status not in (JobStatus.pending, JobStatus.running):
            return
        _set_job_status(db, job, JobStatus.running)

        meeting = db.get(Meeting, job.meeting_id)
        if not meeting:
            _set_job_status(db, job, JobStatus.failed, error="Meeting not found")
            return

        transcript = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == job.meeting_id)
            .order_by(Transcript.created_at.desc())
            .first()
        )
        if not transcript:
            _set_job_status(db, job, JobStatus.failed, error="No transcript")
            return

        template_id = (job.payload or {}).get("template_id")
        template = (
            db.get(Template, template_id)
            if template_id
            else db.query(Template)
            .filter(Template.type == TemplateType.minutes, Template.is_default.is_(True))
            .first()
        )
        if not template:
            _set_job_status(db, job, JobStatus.failed, error="No minutes template")
            return
        try:
            _validate_template_type(template, TemplateType.minutes)
        except ValueError as exc:
            _set_job_status(db, job, JobStatus.failed, error=str(exc))
            return

        participants_str = ", ".join(p.name for p in meeting.participants) or "—"
        meeting_date = (
            meeting.meeting_date.isoformat()
            if meeting.meeting_date
            else ""
        )

        analysis = asyncio.run(ai_service.analyze_transcript(transcript.text))
        base = doc_service.render_minutes_variables(
            template.content,
            meeting.client_name,
            meeting_date,
            participants_str,
        )
        content = asyncio.run(
            ai_service.fill_template(
                base,
                {
                    "NOME CLIENTE": meeting.client_name,
                    "DATA": meeting_date,
                    "PARTICIPANTES": participants_str,
                },
                analysis,
            )
        )

        db.query(ActionItem).filter(ActionItem.meeting_id == job.meeting_id).delete()

        summary = Summary(
            meeting_id=job.meeting_id,
            transcript_id=transcript.id,
            template_id=template.id,
            content=content,
            short_summary=doc_service.short_summary_from_content(content),
            analysis=analysis,
            version=_next_summary_version(db, job.meeting_id),
        )
        db.add(summary)
        db.flush()

        for item in analysis.get("action_items", []):
            db.add(
                ActionItem(
                    meeting_id=job.meeting_id,
                    summary_id=summary.id,
                    task=item.get("task", ""),
                    assignee_name=item.get("assignee_name"),
                    assignee_slack=item.get("assignee_slack"),
                    timing=item.get("timing"),
                )
            )

        meeting.status = MeetingStatus.pending_approval
        _set_job_status(db, job, JobStatus.completed, result_id=summary.id)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Minutes job %s failed", job_id)
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        if job:
            _set_job_status(db, job, JobStatus.failed, error=friendly_openai_error(exc))
    finally:
        db.close()
