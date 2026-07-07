from __future__ import annotations

import io

import pytest

from app.services import upload_validate as uv


def test_validate_webm_header():
    f = io.BytesIO(b"\x1a\x45\xdf\xa3" + b"\x00" * 12)
    uv.validate_recording_header(f, ".webm")
    assert f.tell() == 0


def test_validate_rejects_fake_mp3():
    f = io.BytesIO(b"not-audio-file!!")
    with pytest.raises(ValueError, match="MP3"):
        uv.validate_recording_header(f, ".mp3")
