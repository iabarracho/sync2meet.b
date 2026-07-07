from __future__ import annotations

import io

import pytest

from app.services import storage as storage_service


def test_sanitize_filename_rejects_traversal():
    with pytest.raises(ValueError):
        storage_service.sanitize_filename("../../etc/passwd")


def test_sanitize_filename_accepts_simple_name():
    assert storage_service.sanitize_filename("recording.webm") == "recording.webm"


def test_save_upload_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service.settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(storage_service.settings, "max_upload_bytes", 1024)

    data = io.BytesIO(b"hello")
    path = storage_service.save_upload("m1", "notes.webm", data)
    assert path.is_file()
    assert "meetings" in str(path)
    assert "recordings" in str(path)


def test_delete_file_rejects_outside_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service.settings, "storage_dir", str(tmp_path))
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        storage_service.delete_file(outside)
