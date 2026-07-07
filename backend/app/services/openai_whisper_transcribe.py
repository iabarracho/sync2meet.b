from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..config import settings
from ..errors import require_openai
from .audio_prep import SEGMENT_SECONDS, cleanup_temp_dir, prepare_audio_files

logger = logging.getLogger("sync2meet.whisper")

# Limite da API OpenAI Whisper (~25 MB)
_OPENAI_MAX_BYTES = 24 * 1024 * 1024


def _openai_client():
    require_openai()
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def _transcribe_chunk_openai(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    if size > _OPENAI_MAX_BYTES:
        raise ValueError(
            f"Segmento de áudio demasiado grande para a API ({size // (1024 * 1024)} MB). "
            "Contacta o administrador."
        )
    client = _openai_client()
    lang = (settings.faster_whisper_language or "").strip() or None
    with path.open("rb") as audio_file:
        kwargs: dict[str, Any] = {
            "model": "whisper-1",
            "file": audio_file,
            "response_format": "verbose_json",
        }
        if lang:
            kwargs["language"] = lang
        result = client.audio.transcriptions.create(**kwargs)

    text = (getattr(result, "text", None) or "").strip()
    segments: list[dict[str, Any]] = []
    for seg in getattr(result, "segments", None) or []:
        if isinstance(seg, dict):
            seg_text = str(seg.get("text") or "").strip()
            segments.append(
                {
                    "speaker": "Speaker",
                    "start": float(seg.get("start", 0)),
                    "end": float(seg.get("end", 0)),
                    "text": seg_text,
                }
            )

    return {
        "text": text,
        "language": getattr(result, "language", None),
        "segments": segments,
        "provider": "openai-whisper",
    }


async def transcribe_openai_audio(file_path: Path) -> dict[str, Any]:
    """Transcrição rápida via API OpenAI (~minutos em vez de horas). Custo ~0,006 USD/min."""
    audio_files, temp_dir = prepare_audio_files(file_path)
    try:
        workers = min(6, max(1, len(audio_files)))
        logger.info(
            "Transcrição OpenAI Whisper: %d segmento(s), %d worker(s)",
            len(audio_files),
            workers,
        )
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            tasks = [
                loop.run_in_executor(pool, _transcribe_chunk_openai, chunk)
                for chunk in audio_files
            ]
            chunk_results = await asyncio.gather(*tasks)

        texts: list[str] = []
        all_segments: list[dict[str, Any]] = []
        language: str | None = None
        time_offset = 0.0

        for chunk_result in chunk_results:
            chunk_text = (chunk_result.get("text") or "").strip()
            if chunk_text:
                texts.append(chunk_text)
            if language is None:
                language = chunk_result.get("language")

            chunk_segments = chunk_result.get("segments") or []
            if chunk_segments:
                for seg in chunk_segments:
                    seg_text = str(seg.get("text") or "").strip()
                    if not seg_text:
                        continue
                    all_segments.append(
                        {
                            "speaker": seg.get("speaker", "Speaker"),
                            "start": float(seg["start"]) + time_offset,
                            "end": float(seg["end"]) + time_offset,
                            "text": seg_text,
                        }
                    )
                time_offset = all_segments[-1]["end"]
            elif chunk_text:
                time_offset += SEGMENT_SECONDS

        return {
            "text": "\n\n".join(texts),
            "language": language,
            "segments": all_segments,
            "provider": "openai-whisper",
        }
    finally:
        cleanup_temp_dir(temp_dir)
