from __future__ import annotations

import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path

from ..config import settings
from ..errors import require_email


def smtp_from_address() -> str:
    _, addr = parseaddr(settings.smtp_from)
    return addr or settings.smtp_user or ""


def friendly_smtp_error(error: str | None) -> str:
    msg = (error or "").strip()
    if not msg:
        return "Não foi possível enviar o email."
    lower = msg.lower()
    if "535" in msg or "badcredentials" in lower or "username and password not accepted" in lower:
        account = settings.smtp_user or "conta SMTP"
        return (
            f"Gmail rejeitou o login para {account}. "
            "A App Password tem de ser criada nessa mesma conta Google "
            "(myaccount.google.com/apppasswords), não noutra. "
            "Se já criaste, gera uma nova App Password e atualiza SMTP_PASSWORD no backend/.env; "
            "depois reinicia com parar-tudo.cmd e ARRANCAR.cmd."
        )
    if "authentication failed" in lower:
        return "Falha de autenticação SMTP. Verifica SMTP_USER e SMTP_PASSWORD no backend/.env."
    return msg


def send_meeting_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: list[Path] | None = None,
) -> tuple[str, str | None]:
    """Returns (status, error). status: sent | scheduled | failed."""
    require_email()

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for path in attachments or []:
        if path.exists():
            part = MIMEApplication(path.read_bytes(), Name=path.name)
            part["Content-Disposition"] = f'attachment; filename="{path.name}"'
            msg.attach(part)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(smtp_from_address(), [to_email], msg.as_string())
        return "sent", None
    except Exception as exc:  # noqa: BLE001
        return "failed", friendly_smtp_error(str(exc))


def build_distribution_body(
    meeting_title: str,
    meeting_date: str,
    short_summary: str,
) -> str:
    return (
        f"Reunião: {meeting_title}\n"
        f"Data: {meeting_date}\n\n"
        f"Resumo:\n{short_summary}\n\n"
        "Em anexo encontram o PDF e DOCX da ata aprovada.\n\n"
        f"— {settings.app_display_name}"
    )


def schedule_status(scheduled_for: datetime | None) -> str:
    if scheduled_for and scheduled_for > datetime.now(timezone.utc):
        return "scheduled"
    return "sent"
