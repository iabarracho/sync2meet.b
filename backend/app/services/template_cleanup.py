from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Template, TemplateType


def is_copy_name(name: str) -> bool:
    lower = name.lower()
    return "cópia" in lower or "copia" in lower or "(copy)" in lower


def cleanup_duplicate_templates(db: Session) -> int:
    """Remove accidental copies and duplicate rows (keeps oldest per name+type)."""
    removed = 0
    seen: set[tuple[str, TemplateType]] = set()
    for t in db.query(Template).order_by(Template.created_at.asc()).all():
        key = (t.name, t.type)
        if is_copy_name(t.name) or key in seen:
            db.delete(t)
            removed += 1
        else:
            seen.add(key)
    if removed:
        db.commit()
    return removed
