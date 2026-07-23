from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..deps import get_current_user, get_db
from ..models import (
    ActionItem,
    ActionItemStatus,
    Agenda,
    Approval,
    EmailLog,
    EmailDistribution,
    Meeting,
    MeetingStatus,
    Participant,
    Recording,
    SlackLog,
    Summary,
    Template,
    TemplateType,
    Transcript,
    JobType,
    ProcessingJob,
    User,
)
from ..schemas import (
    ActionItemCreate,
    ActionItemOut,
    ActionItemUpdate,
    AgendaGenerateRequest,
    AgendaOut,
    AgendaUpdate,
    ApprovalOut,
    ApprovalRequest,
    EmailLogOut,
    EmailSendRequest,
    EmailDistributionOut,
    MeetingCreate,
    MeetingListItem,
    MeetingOut,
    MeetingUpdate,
    ParticipantCreate,
    ParticipantImport,
    ParticipantOut,
    ParticipantUpdate,
    RecordingOut,
    SlackLogOut,
    SlackPreviewOut,
    SlackSendRequest,
    SummaryGenerateRequest,
    SummaryOut,
    SummaryUpdate,
    TranscriptOut,
    GoogleMeetImportOut,
    JobOut,
)
from ..services import ai as ai_service
from ..services import google_meet_import as gmeet_service
from ..services import jobs as job_service
from ..services import documents as doc_service
from ..services import email as email_service
from ..services import slack as slack_service
from ..services import storage as storage_service
from ..services import audit as audit_service

router = APIRouter(
    prefix="/api/meetings",
    tags=["meetings"],
    dependencies=[Depends(get_current_user)],
)


def _can_access_meeting(meeting: Meeting, user: User) -> bool:
    if not settings.auth_enabled or user.role == "admin":
        return True
    if meeting.owner_id is None:
        return False
    return meeting.owner_id == user.id


def _can_modify_meeting(meeting: Meeting, user: User) -> bool:
    return _can_access_meeting(meeting, user)


def _get_meeting(db: Session, meeting_id: str, user: User) -> Meeting:
    m = (
        db.query(Meeting)
        .options(joinedload(Meeting.participants))
        .filter(Meeting.id == meeting_id)
        .first()
    )
    if not m:
        raise HTTPException(404, "Meeting not found")
    if not _can_access_meeting(m, user):
        raise HTTPException(403, "Sem permissão para aceder a esta reunião.")
    return m


def _date_str(m: Meeting) -> str:
    if m.meeting_date:
        return m.meeting_date.isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def _participants_str(participants: list[Participant]) -> str:
    return ", ".join(p.name for p in participants) if participants else "—"


def _default_template(db: Session, ttype: TemplateType) -> Template | None:
    return (
        db.query(Template)
        .filter(Template.type == ttype, Template.is_default.is_(True))
        .first()
    )


def _participant_count(db: Session, meeting_id: str) -> int:
    return (
        db.query(Participant)
        .filter(Participant.meeting_id == meeting_id)
        .count()
    )


def _ensure_participant_capacity(
    db: Session, meeting_id: str, adding: int = 1
) -> None:
    total = _participant_count(db, meeting_id) + adding
    if total > settings.max_participants_per_meeting:
        raise HTTPException(
            400,
            f"Máximo de {settings.max_participants_per_meeting} participantes por reunião.",
        )


def _assert_no_active_job(
    db: Session, meeting_id: str, job_type: JobType, action: str
) -> None:
    job_service.recover_stale_jobs(db, meeting_id)
    active = job_service.get_active_job(db, meeting_id, job_type)
    if active:
        raise HTTPException(
            409,
            f"Não é possível {action} enquanto há um job «{job_type.value}» em curso.",
        )


def _validate_slack_channel(channel: str) -> str:
    allowed = settings.slack_allowed_channels_list
    if channel not in allowed:
        raise HTTPException(
            400,
            f"Canal Slack não permitido. Canais permitidos: {', '.join(allowed)}",
        )
    return channel


def _latest_summary(db: Session, meeting_id: str) -> Summary | None:
    return (
        db.query(Summary)
        .filter(Summary.meeting_id == meeting_id)
        .order_by(Summary.version.desc())
        .first()
    )


def _latest_agenda(db: Session, meeting_id: str) -> Agenda | None:
    return (
        db.query(Agenda)
        .filter(Agenda.meeting_id == meeting_id)
        .order_by(Agenda.version.desc())
        .first()
    )

# --- Meetings CRUD ---


@router.get("", response_model=list[MeetingListItem])
def list_meetings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Meeting]:
    query = db.query(Meeting)
    if settings.auth_enabled and user.role != "admin":
        query = query.filter(Meeting.owner_id == user.id)
    return query.order_by(Meeting.updated_at.desc()).all()


@router.post("", response_model=MeetingOut, status_code=201)
def create_meeting(body: MeetingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Meeting:
    meeting = Meeting(
        client_name=body.client_name,
        title=body.title,
        meeting_date=body.meeting_date,
        meeting_time=body.meeting_time,
        description=body.description,
        owner_id=user.id if settings.auth_enabled else None,
    )
    db.add(meeting)
    db.flush()
    if body.participants:
        _ensure_participant_capacity(db, meeting.id, len(body.participants))
    for p in body.participants:
        db.add(
            Participant(
                meeting_id=meeting.id,
                name=p.name,
                email=str(p.email),
                role=p.role,
                slack_username=p.slack_username,
            )
        )
    db.commit()
    db.refresh(meeting)
    return _get_meeting(db, meeting.id, user)


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Meeting:
    return _get_meeting(db, meeting_id, user)


@router.patch("/{meeting_id}", response_model=MeetingOut)
def update_meeting(
    meeting_id: str, body: MeetingUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Meeting:
    m = _get_meeting(db, meeting_id, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    return _get_meeting(db, meeting_id, user)


@router.delete("/{meeting_id}", status_code=204, response_class=Response)
def delete_meeting(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(404, "Meeting not found")
    if not _can_modify_meeting(m, user):
        raise HTTPException(403, "Sem permissão para apagar esta reunião.")
    db.delete(m)
    db.commit()
    storage_service.delete_meeting_storage(meeting_id)
    audit_service.log_audit(
        db,
        action="meeting.delete",
        user_id=user.id,
        user_email=user.email,
        resource_type="meeting",
        resource_id=meeting_id,
        detail=m.title,
    )
    return Response(status_code=204)


# --- Participants ---


@router.post("/{meeting_id}/participants", response_model=ParticipantOut, status_code=201)
def add_participant(
    meeting_id: str,
    body: ParticipantCreate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> Participant:
    _get_meeting(db, meeting_id, user)
    _ensure_participant_capacity(db, meeting_id)
    p = Participant(
        meeting_id=meeting_id,
        name=body.name,
        email=str(body.email),
        role=body.role,
        slack_username=body.slack_username,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch(
    "/{meeting_id}/participants/{participant_id}",
    response_model=ParticipantOut,
)
def update_participant(
    meeting_id: str,
    participant_id: str,
    body: ParticipantUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> Participant:
    _get_meeting(db, meeting_id, user)
    p = db.get(Participant, participant_id)
    if not p or p.meeting_id != meeting_id:
        raise HTTPException(404, "Participant not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete(
    "/{meeting_id}/participants/{participant_id}",
    status_code=204,
    response_class=Response,
)
def remove_participant(
    meeting_id: str, participant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    _get_meeting(db, meeting_id, user)
    p = db.get(Participant, participant_id)
    if not p or p.meeting_id != meeting_id:
        raise HTTPException(404, "Participant not found")
    db.delete(p)
    db.commit()
    return Response(status_code=204)


@router.post("/{meeting_id}/participants/import", response_model=list[ParticipantOut])
def import_participants(
    meeting_id: str,
    body: ParticipantImport,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> list[Participant]:
    _get_meeting(db, meeting_id, user)
    if not body.participants:
        return []
    _ensure_participant_capacity(db, meeting_id, len(body.participants))
    created: list[Participant] = []
    for item in body.participants:
        p = Participant(
            meeting_id=meeting_id,
            name=item.name,
            email=str(item.email),
            role=item.role,
            slack_username=item.slack_username,
        )
        db.add(p)
        created.append(p)
    db.commit()
    for p in created:
        db.refresh(p)
    return created


# --- Agenda ---


@router.get("/{meeting_id}/agenda", response_model=AgendaOut | None)
def get_agenda(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Agenda | None:
    _get_meeting(db, meeting_id, user)
    return _latest_agenda(db, meeting_id)


@router.post("/{meeting_id}/agenda/generate", response_model=JobOut, status_code=202)
async def generate_agenda(
    meeting_id: str,
    body: AgendaGenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> ProcessingJob:
    _get_meeting(db, meeting_id, user)
    transcript = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.created_at.desc())
        .first()
    )
    if not transcript or not transcript.text.strip():
        raise HTTPException(
            400,
            "Carrega áudio/transcrição e transcreve primeiro, ou importa um VTT/TXT.",
        )

    running = job_service.enqueue_job(
        db,
        meeting_id,
        JobType.agenda,
        background_tasks,
        job_service.run_agenda_job,
        payload={"template_id": body.template_id},
    )
    return running


@router.patch("/{meeting_id}/agenda", response_model=AgendaOut)
def update_agenda(
    meeting_id: str, body: AgendaUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Agenda:
    _get_meeting(db, meeting_id, user)
    agenda = _latest_agenda(db, meeting_id)
    if not agenda:
        raise HTTPException(404, "Agenda not found")
    agenda.content = body.content
    db.commit()
    db.refresh(agenda)
    return agenda


@router.post("/{meeting_id}/agenda/export/pdf")
def export_agenda_pdf(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FileResponse:
    _get_meeting(db, meeting_id, user)
    agenda = _latest_agenda(db, meeting_id)
    if not agenda:
        raise HTTPException(404, "Agenda not found")
    out = storage_service.docs_dir(meeting_id, "agendas") / f"agenda_v{agenda.version}.pdf"
    doc_service.export_pdf(agenda.content, out)
    agenda.pdf_path = str(out)
    db.commit()
    return FileResponse(out, filename=out.name, media_type="application/pdf")


@router.post("/{meeting_id}/agenda/export/docx")
def export_agenda_docx(
    meeting_id: str,
    body: AgendaUpdate | None = Body(default=None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> FileResponse:
    _get_meeting(db, meeting_id, user)
    agenda = _latest_agenda(db, meeting_id)
    content: str | None = None
    version = 1
    if body and body.content.strip():
        content = body.content
        if agenda:
            agenda.content = body.content
            version = agenda.version
    elif agenda:
        content = agenda.content
        version = agenda.version
    if not agenda or not content:
        raise HTTPException(404, "Gera a agenda primeiro")
    agenda.content = content
    out = storage_service.docs_dir(meeting_id, "agendas") / f"agenda_v{version}.docx"
    doc_service.export_docx(content, out)
    agenda.docx_path = str(out)
    db.commit()
    return FileResponse(
        out,
        filename=out.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# --- Recordings & transcription ---


@router.get("/{meeting_id}/recordings", response_model=list[RecordingOut])
def list_recordings(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Recording]:
    _get_meeting(db, meeting_id, user)
    return (
        db.query(Recording)
        .filter(Recording.meeting_id == meeting_id)
        .order_by(Recording.created_at.desc())
        .all()
    )


@router.post("/{meeting_id}/recordings", response_model=RecordingOut, status_code=201)
async def upload_recording(
    meeting_id: str,
    request: Request,
    file: UploadFile = File(...),
    source: str = Query("upload"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> Recording:
    from ..services import rate_limit as rate_limit_service
    from ..services import upload_validate as upload_validate_service

    rate_limit_service.check_rate_limit(request, bucket="upload")
    m = _get_meeting(db, meeting_id, user)
    if not file.filename:
        raise HTTPException(400, "Filename required")
    ext = Path(file.filename).suffix.lower()
    allowed = settings.allowed_upload_extensions_list
    if allowed and ext not in allowed:
        raise HTTPException(
            400,
            f"Tipo de ficheiro não permitido. Extensões aceites: {', '.join(allowed)}",
        )
    try:
        upload_validate_service.validate_recording_header(file.file, ext)
        path = storage_service.save_upload(meeting_id, file.filename, file.file)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(500, f"Nao foi possivel guardar o ficheiro: {exc}") from exc
    except Exception as exc:
        import logging

        logging.getLogger("sync2meet").exception("Upload recording failed")
        raise HTTPException(
            500,
            "Erro ao guardar a gravação. Se o ficheiro for muito grande, "
            f"o limite é {settings.max_upload_bytes // (1024 * 1024 * 1024)} GB.",
        ) from exc
    rec = Recording(
        meeting_id=meeting_id,
        filename=file.filename,
        file_path=str(path),
        mime_type=file.content_type,
        source=source,
        size_bytes=path.stat().st_size,
    )
    m.status = MeetingStatus.recorded
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def _sync_status_after_media_change(db: Session, meeting: Meeting) -> None:
    has_summary = (
        db.query(Summary)
        .filter(Summary.meeting_id == meeting.id)
        .order_by(Summary.version.desc())
        .first()
    )
    if has_summary and meeting.status in {
        MeetingStatus.minutes_ready,
        MeetingStatus.pending_approval,
        MeetingStatus.approved,
        MeetingStatus.distributed,
    }:
        return

    has_transcript = (
        db.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
    )
    has_recording = (
        db.query(Recording).filter(Recording.meeting_id == meeting.id).first()
    )
    if has_transcript or has_recording:
        meeting.status = MeetingStatus.recorded
    elif db.query(Agenda).filter(Agenda.meeting_id == meeting.id).first():
        meeting.status = MeetingStatus.agenda_ready
    else:
        meeting.status = MeetingStatus.draft


@router.delete(
    "/{meeting_id}/recordings/{recording_id}",
    status_code=204,
    response_class=Response,
)
def delete_recording(
    meeting_id: str, recording_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    m = _get_meeting(db, meeting_id, user)
    rec = db.get(Recording, recording_id)
    if not rec or rec.meeting_id != meeting_id:
        raise HTTPException(404, "Recording not found")

    _assert_no_active_job(db, meeting_id, JobType.transcribe, "apagar a gravação")

    db.query(Transcript).filter(Transcript.recording_id == recording_id).delete()
    storage_service.delete_file(rec.file_path)
    db.delete(rec)
    _sync_status_after_media_change(db, m)
    db.commit()
    return Response(status_code=204)


@router.delete(
    "/{meeting_id}/transcript",
    status_code=204,
    response_class=Response,
)
def delete_transcript(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    m = _get_meeting(db, meeting_id, user)
    deleted = (
        db.query(Transcript).filter(Transcript.meeting_id == meeting_id).delete()
    )
    if not deleted:
        raise HTTPException(404, "Transcript not found")
    _sync_status_after_media_change(db, m)
    db.commit()
    return Response(status_code=204)


@router.post(
    "/{meeting_id}/import/google-meet",
    response_model=GoogleMeetImportOut,
    status_code=201,
)
async def import_google_meet(
    meeting_id: str,
    request: Request,
    file: UploadFile = File(...),
    mode: str | None = Form(None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> GoogleMeetImportOut:
    """
    Import Google Meet assets:
    - recording: MP4/MOV/WEBM (gravação exportada do Drive)
    - transcript: VTT, TXT, DOCX, SRT (transcrição exportada do Meet/Docs)
    """
    from ..services import rate_limit as rate_limit_service
    from ..services import upload_validate as upload_validate_service

    rate_limit_service.check_rate_limit(request, bucket="upload")
    m = _get_meeting(db, meeting_id, user)
    if not file.filename:
        raise HTTPException(400, "Filename required")

    import_mode = mode or "auto"
    if import_mode == "auto":
        try:
            import_mode = gmeet_service.detect_import_mode(file.filename)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    if import_mode not in ("recording", "transcript"):
        raise HTTPException(400, "mode must be recording, transcript, or auto")

    ext = Path(file.filename).suffix.lower()
    if import_mode == "recording":
        try:
            upload_validate_service.validate_recording_header(file.file, ext)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    path = storage_service.save_upload(meeting_id, file.filename, file.file)

    if import_mode == "recording":
        if not gmeet_service.is_recording(file.filename):
            raise HTTPException(
                400,
                "Ficheiro não parece gravação. Use MP4, MOV ou WEBM do Google Meet.",
            )
        rec = Recording(
            meeting_id=meeting_id,
            filename=file.filename,
            file_path=str(path),
            mime_type=file.content_type,
            source="google_meet",
            size_bytes=path.stat().st_size,
        )
        m.status = MeetingStatus.recorded
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return GoogleMeetImportOut(
            import_type="recording",
            message=(
                "Gravação Google Meet importada. Clica «Transcrever» ou importa "
                "a transcrição oficial do Meet."
            ),
            recording=RecordingOut.model_validate(rec),
        )

    if not gmeet_service.is_transcript(file.filename):
        raise HTTPException(
            400,
            "Ficheiro não parece transcrição. Exporta do Meet: VTT, TXT ou DOCX.",
        )

    try:
        parsed = gmeet_service.parse_transcript_file(path)
    except ValueError as exc:
        storage_service.delete_file(str(path))
        raise HTTPException(400, str(exc)) from exc

    rec = Recording(
        meeting_id=meeting_id,
        filename=file.filename,
        file_path=str(path),
        mime_type=file.content_type,
        source="google_meet_transcript",
        size_bytes=path.stat().st_size,
    )
    db.add(rec)
    db.flush()

    transcript = Transcript(
        meeting_id=meeting_id,
        recording_id=rec.id,
        text=parsed["text"],
        language=parsed.get("language"),
        segments=parsed.get("segments"),
        provider=parsed.get("provider", "google_meet"),
    )
    m.status = MeetingStatus.recorded
    db.add(transcript)
    db.commit()
    db.refresh(rec)
    db.refresh(transcript)
    return GoogleMeetImportOut(
        import_type="transcript",
        message=(
            "Transcrição Google Meet importada. Podes gerar a ata sem transcrever áudio."
        ),
        recording=RecordingOut.model_validate(rec),
        transcript=TranscriptOut.model_validate(transcript),
    )


@router.post("/{meeting_id}/transcribe", response_model=JobOut, status_code=202)
async def transcribe_meeting(
    meeting_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> ProcessingJob:
    from ..services import rate_limit as rate_limit_service

    rate_limit_service.check_rate_limit(request, bucket="transcribe")
    m = _get_meeting(db, meeting_id, user)
    existing = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.created_at.desc())
        .first()
    )
    if existing and existing.provider == "google_meet":
        raise HTTPException(
            400,
            "Transcrição Google Meet já importada. Gera a ata diretamente.",
        )

    rec = (
        db.query(Recording)
        .filter(Recording.meeting_id == meeting_id)
        .order_by(Recording.created_at.desc())
        .first()
    )
    if not rec:
        raise HTTPException(
            400,
            "Carrega uma gravação ou importa a transcrição do Google Meet primeiro.",
        )

    job = job_service.enqueue_job(
        db,
        meeting_id,
        JobType.transcribe,
        background_tasks,
        job_service.run_transcribe_job,
        meeting_status=MeetingStatus.processing,
    )
    return job


@router.get("/{meeting_id}/jobs/{job_id}", response_model=JobOut)
def get_job_status(
    meeting_id: str, job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProcessingJob:
    _get_meeting(db, meeting_id, user)
    job = job_service.get_job(db, meeting_id, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{meeting_id}/transcript", response_model=TranscriptOut | None)
def get_transcript(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Transcript | None:
    _get_meeting(db, meeting_id, user)
    return (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.created_at.desc())
        .first()
    )


# --- Minutes / Summary ---


@router.post("/{meeting_id}/minutes/generate", response_model=JobOut, status_code=202)
async def generate_minutes(
    meeting_id: str,
    body: SummaryGenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> ProcessingJob:
    _get_meeting(db, meeting_id, user)
    transcript = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.created_at.desc())
        .first()
    )
    if not transcript or not transcript.text.strip():
        raise HTTPException(
            400,
            "Carrega áudio/transcrição e transcreve primeiro, ou importa um VTT/TXT.",
        )

    job = job_service.enqueue_job(
        db,
        meeting_id,
        JobType.minutes,
        background_tasks,
        job_service.run_minutes_job,
        payload={"template_id": body.template_id},
        meeting_status=MeetingStatus.processing,
    )
    return job


@router.get("/{meeting_id}/minutes", response_model=SummaryOut | None)
def get_minutes(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Summary | None:
    _get_meeting(db, meeting_id, user)
    return (
        db.query(Summary)
        .filter(Summary.meeting_id == meeting_id)
        .order_by(Summary.version.desc())
        .first()
    )


@router.patch("/{meeting_id}/minutes", response_model=SummaryOut)
def update_minutes(
    meeting_id: str, body: SummaryUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Summary:
    _get_meeting(db, meeting_id, user)
    summary = (
        db.query(Summary)
        .filter(Summary.meeting_id == meeting_id, Summary.is_approved.is_(False))
        .order_by(Summary.version.desc())
        .first()
    )
    if not summary:
        raise HTTPException(404, "Editable minutes not found")
    if body.content is not None:
        summary.content = body.content
    if body.short_summary is not None:
        summary.short_summary = body.short_summary
    meeting = db.get(Meeting, meeting_id)
    if meeting and meeting.status not in (MeetingStatus.approved, MeetingStatus.distributed):
        meeting.status = MeetingStatus.pending_approval
    db.commit()
    db.refresh(summary)
    return summary


@router.post("/{meeting_id}/minutes/export/docx")
def export_minutes_docx(
    meeting_id: str,
    body: SummaryUpdate | None = Body(default=None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> FileResponse:
    """Export draft minutes as Word for preview before approval."""
    m = _get_meeting(db, meeting_id, user)
    summary = (
        db.query(Summary)
        .filter(Summary.meeting_id == meeting_id, Summary.is_approved.is_(False))
        .order_by(Summary.version.desc())
        .first()
    )
    content: str | None = None
    version = 1
    if body and body.content and body.content.strip():
        content = body.content
        if summary:
            summary.content = body.content
            if body.short_summary is not None:
                summary.short_summary = body.short_summary
            version = summary.version
            meeting = _get_meeting(db, meeting_id, user)
            if meeting.status not in (MeetingStatus.approved, MeetingStatus.distributed):
                meeting.status = MeetingStatus.pending_approval
    elif summary:
        content = summary.content
        version = summary.version
    if not content:
        raise HTTPException(404, "Gera a ata primeiro")
    db.commit()
    out = (
        storage_service.docs_dir(meeting_id, "drafts")
        / f"ata_rascunho_v{version}.docx"
    )
    doc_service.export_docx(content, out)
    safe_client = re.sub(r"[^\w\-]+", "_", m.client_name)[:40]
    return FileResponse(
        out,
        filename=f"ata_{safe_client}_rascunho.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# --- Action items ---


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemOut])
def list_action_items(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ActionItem]:
    _get_meeting(db, meeting_id, user)
    return (
        db.query(ActionItem)
        .filter(ActionItem.meeting_id == meeting_id)
        .order_by(ActionItem.created_at)
        .all()
    )


@router.post("/{meeting_id}/action-items", response_model=ActionItemOut, status_code=201)
def create_action_item(
    meeting_id: str,
    body: ActionItemCreate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> ActionItem:
    _get_meeting(db, meeting_id, user)
    item = ActionItem(meeting_id=meeting_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch(
    "/{meeting_id}/action-items/{item_id}", response_model=ActionItemOut
)
def update_action_item(
    meeting_id: str,
    item_id: str,
    body: ActionItemUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> ActionItem:
    _get_meeting(db, meeting_id, user)
    item = db.get(ActionItem, item_id)
    if not item or item.meeting_id != meeting_id:
        raise HTTPException(404, "Action item not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


# --- Approval ---


def _approve_summary(
    db: Session,
    meeting: Meeting,
    summary: Summary,
    *,
    approved_by: str | None = None,
) -> Approval:
    if summary.is_approved:
        existing = (
            db.query(Approval)
            .filter(Approval.summary_id == summary.id)
            .order_by(Approval.created_at.desc())
            .first()
        )
        if existing:
            return existing

    docs = storage_service.docs_dir(meeting.id, "approved")
    pdf = docs / f"ata_v{summary.version}.pdf"
    docx = docs / f"ata_v{summary.version}.docx"
    doc_service.export_pdf(summary.content, pdf)
    doc_service.export_docx(summary.content, docx)

    summary.is_approved = True
    summary.pdf_path = str(pdf)
    summary.docx_path = str(docx)
    meeting.status = MeetingStatus.approved

    approval = Approval(
        meeting_id=meeting.id,
        summary_id=summary.id,
        approved_by=approved_by,
        approved_version=summary.version,
        locked_content=summary.content,
        pdf_path=str(pdf),
        docx_path=str(docx),
    )
    db.add(approval)
    return approval


def _approved_summary(db: Session, meeting_id: str) -> Summary | None:
    return (
        db.query(Summary)
        .filter(Summary.meeting_id == meeting_id, Summary.is_approved.is_(True))
        .order_by(Summary.version.desc())
        .first()
    )


def _resolve_summary_for_distribution(db: Session, meeting: Meeting) -> Summary:
    """Require an approved summary; block if a newer unapproved draft exists."""
    latest = _latest_summary(db, meeting.id)
    if not latest:
        raise HTTPException(400, "Gera a ata antes de enviar o email.")

    approved = _approved_summary(db, meeting.id)
    if not approved:
        raise HTTPException(
            409,
            "Aprova a ata antes de enviar o email — clica em «Aprovar Ata» no passo 4.",
        )

    if latest.version > approved.version and not latest.is_approved:
        raise HTTPException(
            409,
            "Existe uma nova versão da ata não aprovada. Aprova ou regera antes de enviar.",
        )

    return approved


def _ensure_summary_attachments(summary: Summary) -> list[Path]:
    attachments: list[Path] = []
    if summary.pdf_path and Path(summary.pdf_path).is_file():
        attachments.append(Path(summary.pdf_path))
    if summary.docx_path and Path(summary.docx_path).is_file():
        attachments.append(Path(summary.docx_path))
    if not attachments:
        raise HTTPException(
            500,
            "Documentos da ata não encontrados. Aprova novamente antes de enviar.",
        )
    return attachments


def _already_emailed_summary(
    db: Session, meeting_id: str, summary_id: str, to_email: str
) -> EmailLog | None:
    """Skip re-sending to recipients who already received this summary version."""
    return (
        db.query(EmailLog)
        .join(EmailDistribution, EmailLog.distribution_id == EmailDistribution.id)
        .filter(
            EmailDistribution.meeting_id == meeting_id,
            EmailDistribution.summary_id == summary_id,
            EmailLog.to_email == to_email,
            EmailLog.status == "sent",
        )
        .order_by(EmailLog.created_at.desc())
        .first()
    )


def _execute_email_distribution(
    db: Session,
    meeting: Meeting,
    distribution: EmailDistribution,
    summary: Summary,
    body: EmailSendRequest,
    user: User,
) -> EmailDistribution:
    if distribution.status in ("completed", "scheduled"):
        return distribution
    if distribution.status == "sending":
        db.refresh(distribution)
        return distribution

    attachments = _ensure_summary_attachments(summary)
    distribution.status = "sending"
    db.flush()

    logs: list[EmailLog] = []
    now = datetime.now(timezone.utc)
    defer_send = bool(body.scheduled_for and body.scheduled_for > now)

    for p in meeting.participants:
        prior_sent = (
            db.query(EmailLog)
            .filter(
                EmailLog.distribution_id == distribution.id,
                EmailLog.to_email == p.email,
                EmailLog.status == "sent",
            )
            .first()
        )
        if prior_sent:
            logs.append(prior_sent)
            continue

        if not body.force_resend:
            already = _already_emailed_summary(
                db, meeting.id, summary.id, p.email
            )
            if already:
                logs.append(already)
                continue

        subject = f"[{settings.app_display_name}] {meeting.title} — {_date_str(meeting)}"
        body_text = email_service.build_distribution_body(
            meeting.title, _date_str(meeting), summary.short_summary or ""
        )

        if defer_send:
            log = EmailLog(
                meeting_id=meeting.id,
                distribution_id=distribution.id,
                to_email=p.email,
                subject=subject,
                body=body_text,
                attachments=[str(a) for a in attachments],
                status="scheduled",
                provider="smtp",
                scheduled_for=body.scheduled_for,
            )
            db.add(log)
            logs.append(log)
            continue

        log = EmailLog(
            meeting_id=meeting.id,
            distribution_id=distribution.id,
            to_email=p.email,
            subject=subject,
            body=body_text,
            attachments=[str(a) for a in attachments],
            status="pending",
            provider="smtp",
            scheduled_for=body.scheduled_for,
        )
        db.add(log)
        db.flush()

        status, error = email_service.send_meeting_email(
            p.email, subject, body_text, attachments
        )
        log.status = status
        log.error = error
        logs.append(log)

    sent = [log for log in logs if log.status == "sent"]
    failed = [log for log in logs if log.status not in ("sent", "scheduled", "pending")]
    scheduled = [log for log in logs if log.status == "scheduled"]

    if scheduled and not sent and not failed:
        distribution.status = "scheduled"
    elif failed and sent:
        distribution.status = "partial"
    elif failed:
        distribution.status = "failed"
    else:
        distribution.status = "completed"
        meeting.status = MeetingStatus.distributed

    distribution.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(distribution)

    if distribution.status == "completed":
        audit_service.log_audit(
            db,
            action="email.distribute",
            user_id=user.id,
            user_email=user.email,
            resource_type="meeting",
            resource_id=meeting.id,
            detail=f"distribution={distribution.id}",
        )

    if not sent and not scheduled:
        detail = failed[0].error if failed else "Não foi possível enviar o email."
        raise HTTPException(502, email_service.friendly_smtp_error(detail))

    if failed:
        failed_addrs = ", ".join(log.to_email for log in failed)
        raise HTTPException(
            502,
            f"Enviado para {len(sent)} destinatário(s), mas falhou para: {failed_addrs}. "
            f"{email_service.friendly_smtp_error(failed[0].error)}",
        )

    return distribution


@router.post("/{meeting_id}/approve", response_model=ApprovalOut, status_code=201)
def approve_minutes(
    meeting_id: str,
    body: ApprovalRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> Approval:
    m = _get_meeting(db, meeting_id, user)
    summary = db.get(Summary, body.summary_id)
    if not summary or summary.meeting_id != meeting_id:
        raise HTTPException(404, "Summary not found")

    if summary.is_approved:
        existing = (
            db.query(Approval)
            .filter(Approval.summary_id == summary.id)
            .order_by(Approval.created_at.desc())
            .first()
        )
        if existing:
            return existing

    latest = _latest_summary(db, meeting_id)
    if latest and latest.id != summary.id and latest.version > summary.version:
        raise HTTPException(
            409,
            "Existe uma versão mais recente da ata. Aprova a versão mais recente.",
        )

    approval = _approve_summary(db, m, summary, approved_by=user.name)
    db.commit()
    db.refresh(approval)
    audit_service.log_audit(
        db,
        action="minutes.approve",
        user_id=user.id,
        user_email=user.email,
        resource_type="meeting",
        resource_id=meeting_id,
        detail=f"summary v{summary.version}",
    )
    return approval


# --- Distribution ---


@router.get("/{meeting_id}/email-logs", response_model=list[EmailLogOut])
def list_email_logs(
    meeting_id: str,
    distribution_id: str | None = Query(None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> list[EmailLog]:
    _get_meeting(db, meeting_id, user)
    query = db.query(EmailLog).filter(EmailLog.meeting_id == meeting_id)
    if distribution_id:
        query = query.filter(EmailLog.distribution_id == distribution_id)
    return query.order_by(EmailLog.created_at.desc()).all()


@router.get(
    "/{meeting_id}/distributions/{distribution_id}",
    response_model=EmailDistributionOut,
)
def get_email_distribution(
    meeting_id: str,
    distribution_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> EmailDistribution:
    _get_meeting(db, meeting_id, user)
    dist = db.get(EmailDistribution, distribution_id)
    if not dist or dist.meeting_id != meeting_id:
        raise HTTPException(404, "Distribution not found")
    return dist


@router.post("/{meeting_id}/distribute/email", response_model=EmailDistributionOut)
def distribute_email(
    meeting_id: str,
    body: EmailSendRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> EmailDistribution:
    key = (body.idempotency_key or idempotency_key or "").strip() or None

    if key:
        existing = (
            db.query(EmailDistribution)
            .filter(
                EmailDistribution.meeting_id == meeting_id,
                EmailDistribution.idempotency_key == key,
            )
            .first()
        )
        if existing:
            if existing.status in ("completed", "scheduled"):
                return existing
            if existing.status in ("partial", "failed", "sending"):
                m = _get_meeting(db, meeting_id, user)
                summary = db.get(Summary, existing.summary_id)
                if summary:
                    return _execute_email_distribution(db, m, existing, summary, body, user)
            if existing.status == "pending":
                return existing

    m = _get_meeting(db, meeting_id, user)
    if not m.participants:
        raise HTTPException(
            400,
            "Não há destinatários. Adiciona participantes com email em «Editar emails».",
        )

    if m.status == MeetingStatus.distributed and not body.force_resend:
        raise HTTPException(
            409,
            "Email já foi distribuído. Usa force_resend para reenviar.",
        )

    summary = _resolve_summary_for_distribution(db, m)

    distribution = EmailDistribution(
        meeting_id=meeting_id,
        summary_id=summary.id,
        idempotency_key=key,
        status="pending",
    )
    db.add(distribution)
    try:
        db.commit()
        db.refresh(distribution)
    except IntegrityError:
        db.rollback()
        if key:
            existing = (
                db.query(EmailDistribution)
                .filter(
                    EmailDistribution.meeting_id == meeting_id,
                    EmailDistribution.idempotency_key == key,
                )
                .first()
            )
            if existing:
                return existing
        raise HTTPException(409, "Distribuição duplicada em curso. Tenta novamente.")

    return _execute_email_distribution(db, m, distribution, summary, body, user)


@router.get("/{meeting_id}/slack/preview", response_model=SlackPreviewOut)
def preview_slack(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SlackPreviewOut:
    _get_meeting(db, meeting_id, user)
    return _slack_preview(db, meeting_id)


def _slack_preview(db: Session, meeting_id: str) -> SlackPreviewOut:
    items = (
        db.query(ActionItem)
        .filter(ActionItem.meeting_id == meeting_id)
        .all()
    )
    payload = [
        {
            "task": i.task,
            "assignee_name": i.assignee_name,
            "assignee_slack": i.assignee_slack or i.assignee_name,
            "timing": i.timing,
        }
        for i in items
    ]
    return SlackPreviewOut(
        channel=settings.slack_default_channel,
        message=slack_service.format_action_items_message(payload),
    )


@router.post("/{meeting_id}/slack/send", response_model=SlackLogOut, status_code=201)
async def send_slack(
    meeting_id: str,
    body: SlackSendRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> SlackLog:
    _get_meeting(db, meeting_id, user)
    preview = _slack_preview(db, meeting_id)
    channel = body.channel or preview.channel or settings.slack_default_channel
    channel = _validate_slack_channel(channel)
    status, error = await slack_service.send_slack_message(channel, preview.message)
    log = SlackLog(
        meeting_id=meeting_id,
        channel=channel,
        message=preview.message,
        status=status,
        provider="slack",
        error=error,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    if status != "sent":
        raise HTTPException(502, error or "Falha ao enviar para o Slack.")
    return log


@router.post("/{meeting_id}/start", response_model=MeetingOut)
def start_meeting(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Meeting:
    m = _get_meeting(db, meeting_id, user)
    m.status = MeetingStatus.in_progress
    db.commit()
    return _get_meeting(db, meeting_id, user)
