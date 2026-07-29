from __future__ import annotations

import io

import pytest

from app.services import upload_validate as uv


def test_validate_webm_header():
    f = io.BytesIO(b"\x1a\x45\xdf\xa3" + b"\x00" * 12)
    uv.validate_recording_header(f, ".webm")
    assert f.tell() == 0


def test_accepts_mp4_bytes_with_webm_extension():
    """tl;dv / browsers sometimes label MP4 downloads as .webm."""
    f = io.BytesIO(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 20)
    uv.validate_recording_header(f, ".webm")


def test_validate_rejects_fake_mp3():
    f = io.BytesIO(b"not-audio-file!!")
    with pytest.raises(ValueError, match="MP3"):
        uv.validate_recording_header(f, ".mp3")


def test_validate_rejects_html_named_webm():
    f = io.BytesIO(b"<!DOCTYPE html><html>")
    with pytest.raises(ValueError, match="WEBM"):
        uv.validate_recording_header(f, ".webm")
