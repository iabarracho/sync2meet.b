from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from ..config import settings


def sanitize_filename(filename: str) -> str:
    """Basename only; reject path traversal."""
    if not filename or not filename.strip():
        raise ValueError("Filename required")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError("Invalid filename")
    safe = Path(filename).name
    if not safe or safe in (".", ".."):
        raise ValueError("Invalid filename")
    return safe


def _write_with_limit(file_obj, dest: Path, max_bytes: int) -> int:
    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                limit_mb = max_bytes / (1024 * 1024)
                if limit_mb >= 1024:
                    raise ValueError(
                        f"Ficheiro demasiado grande (máximo {limit_mb / 1024:.1f} GB)."
                    )
                raise ValueError(
                    f"Ficheiro demasiado grande (máximo {int(limit_mb)} MB)."
                )
            out.write(chunk)
    return total


def meeting_dir(meeting_id: str) -> Path:
    path = settings.storage_path / "meetings" / meeting_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(meeting_id: str, filename: str, file_obj) -> Path:
    safe_name = sanitize_filename(filename)
    dest_dir = (meeting_dir(meeting_id) / "recordings").resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = (dest_dir / f"{uuid.uuid4().hex}_{safe_name}").resolve()
    if not dest.is_relative_to(dest_dir):
        raise ValueError("Invalid upload path")
    try:
        size = _write_with_limit(file_obj, dest, settings.max_upload_bytes)
    except ValueError:
        dest.unlink(missing_ok=True)
        raise
    if size == 0:
        dest.unlink(missing_ok=True)
        raise ValueError("Ficheiro vazio")
    return dest


def save_template_upload(filename: str, file_obj) -> Path:
    safe_name = sanitize_filename(filename)
    upload_dir = (settings.storage_path / "templates").resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = (upload_dir / f"{uuid.uuid4().hex}_{safe_name}").resolve()
    if not dest.is_relative_to(upload_dir):
        raise ValueError("Invalid upload path")
    try:
        size = _write_with_limit(file_obj, dest, settings.max_upload_bytes)
    except ValueError:
        dest.unlink(missing_ok=True)
        raise
    if size == 0:
        dest.unlink(missing_ok=True)
        raise ValueError("Ficheiro vazio")
    return dest


def docs_dir(meeting_id: str, kind: str) -> Path:
    path = meeting_dir(meeting_id) / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def delete_file(path: str | Path) -> None:
    p = Path(path).resolve()
    root = settings.storage_path.resolve()
    if not p.is_relative_to(root):
        raise ValueError("Caminho de ficheiro fora do storage permitido")
    if p.is_file():
        p.unlink(missing_ok=True)


def delete_meeting_storage(meeting_id: str) -> None:
    path = settings.storage_path / "meetings" / meeting_id
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
