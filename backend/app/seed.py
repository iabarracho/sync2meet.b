from sqlalchemy.orm import Session

from .models import Template, User, Meeting
from .services.builtin_templates import BUILTIN_TEMPLATES
from .services.template_cleanup import cleanup_duplicate_templates
from .config import settings
from .services.auth import hash_password


def _parse_team_users(raw: str) -> list[tuple[str, str, str, str]]:
    entries: list[tuple[str, str, str, str]] = []
    for i, part in enumerate(raw.split(",")):
        part = part.strip()
        if not part:
            continue
        pieces = part.split(":")
        if len(pieces) != 3:
            continue
        name, email, password = (p.strip() for p in pieces)
        if not name or not email or not password:
            continue
        role = "admin" if i == 0 else "member"
        entries.append((name, email.lower(), password, role))
    return entries


def promote_admin_emails(db: Session) -> None:
    for email in settings.admin_emails_list:
        user = db.query(User).filter(User.email == email).first()
        if user and user.role != "admin":
            user.role = "admin"


def backfill_meeting_owners(db: Session) -> None:
    admin = (
        db.query(User)
        .filter(User.role == "admin")
        .order_by(User.created_at.asc())
        .first()
    )
    if not admin:
        return
    updated = (
        db.query(Meeting)
        .filter(Meeting.owner_id.is_(None))
        .update({Meeting.owner_id: admin.id}, synchronize_session=False)
    )
    if updated:
        db.commit()


def seed_database(db: Session) -> None:
    team = _parse_team_users(settings.team_users)
    if team:
        for name, email, password, role in team:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                existing.name = name
                existing.role = role
            else:
                db.add(
                    User(
                        name=name,
                        email=email,
                        role=role,
                        password_hash=hash_password(password),
                    )
                )

    for spec in BUILTIN_TEMPLATES:
        existing = (
            db.query(Template)
            .filter(
                Template.name == spec["name"],
                Template.type == spec["type"],
                Template.source == spec["source"],
            )
            .order_by(Template.created_at.asc())
            .first()
        )
        if existing:
            existing.content = spec["content"]
            existing.structure = spec.get("structure")
            existing.is_default = spec["is_default"]
        else:
            db.add(
                Template(
                    name=spec["name"],
                    type=spec["type"],
                    source=spec["source"],
                    content=spec["content"],
                    structure=spec.get("structure"),
                    is_default=spec["is_default"],
                )
            )
    promote_admin_emails(db)
    db.commit()
    cleanup_duplicate_templates(db)
    backfill_meeting_owners(db)
