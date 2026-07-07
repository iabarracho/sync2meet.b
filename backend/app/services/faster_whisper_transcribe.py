from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

from ..config import settings

logger = logging.getLogger("sync2meet.whisper")

_model = None
_model_lock = threading.Lock()


def _resolve_device() -> tuple[str, str]:
    device = settings.faster_whisper_device.strip().lower()
    compute = settings.faster_whisper_compute_type
    if device == "auto":
        try:
            import ctranslate2 as ct

            if ct.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:
            pass
        return "cpu", compute
    if device == "cuda":
        return "cuda", compute if compute != "int8" else "float16"
    return device, compute


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel

        device, compute = _resolve_device()
        threads = settings.faster_whisper_cpu_threads_resolved
        logger.info(
            "A carregar faster-whisper: model=%s device=%s compute=%s threads=%d",
            settings.faster_whisper_model,
            device,
            compute,
            threads,
        )
        _model = WhisperModel(
            settings.faster_whisper_model,
            device=device,
            compute_type=compute,
            cpu_threads=threads,
            num_workers=1,
        )
        return _model


def transcribe_file(file_path: Path) -> dict[str, Any]:
    """Transcreve um ficheiro de áudio localmente (sem API OpenAI)."""
    model = _get_model()
    lang = (settings.faster_whisper_language or "").strip() or None
    initial_prompt = (settings.faster_whisper_initial_prompt or "").strip() or None

    segments_iter, info = model.transcribe(
        str(file_path),
        language=lang,
        initial_prompt=initial_prompt,
        vad_filter=settings.faster_whisper_vad_filter,
        beam_size=settings.faster_whisper_beam_size,
        best_of=1,
        condition_on_previous_text=False,
        temperature=0,
    )

    all_segments: list[dict[str, Any]] = []
    texts: list[str] = []
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if text:
            texts.append(text)
        all_segments.append(
            {
                "speaker": "Speaker",
                "start": float(seg.start),
                "end": float(seg.end),
                "text": text,
            }
        )

    return {
        "text": "\n\n".join(texts),
        "language": getattr(info, "language", None),
        "segments": all_segments,
        "provider": "faster-whisper",
    }
