from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..config import settings

RECORDING_EXTENSIONS = {".mp4", ".m4a", ".mov", ".webm", ".mkv", ".mp3", ".wav"}
TRANSCRIPT_EXTENSIONS = {".vtt", ".txt", ".docx", ".sbv", ".srt"}


def is_recording(filename: str) -> bool:
    return Path(filename).suffix.lower() in RECORDING_EXTENSIONS


def is_transcript(filename: str) -> bool:
    return Path(filename).suffix.lower() in TRANSCRIPT_EXTENSIONS


def detect_import_mode(filename: str) -> str:
    if is_transcript(filename):
        return "transcript"
    if is_recording(filename):
        return "recording"
    raise ValueError(
        f"Formato não suportado: {Path(filename).suffix}. "
        "Gravação Meet: MP4, MOV, WEBM. Transcrição Meet: VTT, TXT, DOCX, SRT."
    )


def parse_transcript_file(file_path: Path) -> dict[str, Any]:
    size = file_path.stat().st_size
    if size > settings.max_transcript_chars:
        raise ValueError(
            f"Transcrição demasiado grande (máx. {settings.max_transcript_chars:,} caracteres)."
        )
    ext = file_path.suffix.lower()
    if ext == ".vtt":
        return _parse_vtt(file_path)
    if ext == ".srt":
        return _parse_srt(file_path)
    if ext == ".docx":
        return _parse_docx(file_path)
    return _parse_plain_text(file_path)


def _read_text_limited(path: Path) -> str:
    max_bytes = settings.max_transcript_chars * 4
    with path.open("rb") as fh:
        data = fh.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(
            f"Transcrição demasiado grande (máx. {settings.max_transcript_chars:,} caracteres)."
        )
    text = data.decode("utf-8", errors="ignore")
    if len(text) > settings.max_transcript_chars:
        raise ValueError(
            f"Transcrição demasiado grande (máx. {settings.max_transcript_chars:,} caracteres)."
        )
    return text


def _parse_vtt(path: Path) -> dict[str, Any]:
    raw = _read_text_limited(path)
    lines = raw.splitlines()
    segments: list[dict[str, Any]] = []
    text_parts: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            times = line.split("-->")
            start = _vtt_time_to_seconds(times[0].strip())
            end = _vtt_time_to_seconds(times[1].strip().split()[0])
            i += 1
            cue_lines: list[str] = []
            while i < len(lines) and lines[i].strip():
                cue_lines.append(lines[i].strip())
                i += 1
            text = " ".join(cue_lines)
            speaker, utterance = _split_speaker(text)
            segments.append(
                {
                    "speaker": speaker,
                    "start": start,
                    "end": end,
                    "text": utterance,
                }
            )
            text_parts.append(f"[{_seconds_label(start)}] {speaker}: {utterance}")
        else:
            i += 1
    full_text = "\n".join(text_parts) if text_parts else raw
    return {
        "text": full_text,
        "segments": segments,
        "language": "pt",
        "provider": "google_meet",
    }


def _parse_srt(path: Path) -> dict[str, Any]:
    raw = _read_text_limited(path)
    blocks = re.split(r"\n\s*\n", raw.strip())
    segments: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        time_line = lines[1] if "-->" in lines[1] else lines[0]
        if "-->" not in time_line:
            continue
        start_s, end_s = time_line.split("-->")
        start = _srt_time_to_seconds(start_s.strip())
        end = _srt_time_to_seconds(end_s.strip())
        content_lines = lines[2:] if "-->" in lines[1] else lines[1:]
        text = " ".join(content_lines)
        speaker, utterance = _split_speaker(text)
        segments.append(
            {"speaker": speaker, "start": start, "end": end, "text": utterance}
        )
        text_parts.append(f"[{_seconds_label(start)}] {speaker}: {utterance}")
    return {
        "text": "\n".join(text_parts),
        "segments": segments,
        "language": "pt",
        "provider": "google_meet",
    }


def _parse_docx(path: Path) -> dict[str, Any]:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text_parts: list[str] = []
    segments: list[dict[str, Any]] = []
    t = 0.0
    for para in paragraphs:
        speaker, utterance = _split_speaker(para)
        segments.append(
            {
                "speaker": speaker,
                "start": t,
                "end": t + 5.0,
                "text": utterance,
            }
        )
        text_parts.append(f"{speaker}: {utterance}")
        t += 5.0
    return {
        "text": "\n".join(text_parts),
        "segments": segments,
        "language": "pt",
        "provider": "google_meet",
    }


def _parse_plain_text(path: Path) -> dict[str, Any]:
    raw = _read_text_limited(path)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    segments: list[dict[str, Any]] = []
    text_parts: list[str] = []
    t = 0.0
    ts_pattern = re.compile(
        r"^(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*[-–]?\s*(.*)$"
    )
    for line in lines:
        m = ts_pattern.match(line)
        if m:
            start = _flex_time_to_seconds(m.group(1))
            body = m.group(2).strip()
            speaker, utterance = _split_speaker(body)
            segments.append(
                {
                    "speaker": speaker,
                    "start": start,
                    "end": start + 5.0,
                    "text": utterance,
                }
            )
            text_parts.append(f"[{m.group(1)}] {speaker}: {utterance}")
            t = start + 5.0
        else:
            speaker, utterance = _split_speaker(line)
            segments.append(
                {
                    "speaker": speaker,
                    "start": t,
                    "end": t + 5.0,
                    "text": utterance,
                }
            )
            text_parts.append(f"{speaker}: {utterance}")
            t += 5.0
    return {
        "text": "\n".join(text_parts) if text_parts else raw,
        "segments": segments,
        "language": "pt",
        "provider": "google_meet",
    }


def _split_speaker(text: str) -> tuple[str, str]:
    if ":" in text:
        head, tail = text.split(":", 1)
        if len(head) < 80:
            return head.strip(), tail.strip()
    return "Participante", text.strip()


def _vtt_time_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(ts)


def _srt_time_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _flex_time_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(ts)


def _seconds_label(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"
