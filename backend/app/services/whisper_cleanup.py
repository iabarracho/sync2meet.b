from __future__ import annotations

import re
from typing import Any

# Whisper often hallucinates these on silence, music, or bad exports (not real speech).
_HALLUCINATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"legendas pela comunidade amara\.org",
        r"subtitles by the amara\.org community",
        r"legendas por la comunidad amara\.org",
        r"amara\.org",
        r"obrigado por assistir",
        r"thank you for watching",
        r"thanks for watching",
        r"inscreva-se no canal",
        r"subscribe to (the )?channel",
        r"\[música\]",
        r"\[music\]",
        r"\[aplausos\]",
        r"\[applause\]",
        r"♪+",
    )
]


def _strip_hallucinations(text: str) -> str:
    cleaned = text
    for pattern in _HALLUCINATION_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def clean_whisper_result(result: dict[str, Any]) -> dict[str, Any]:
    text = _strip_hallucinations((result.get("text") or "").strip())
    segments: list[dict[str, Any]] = []
    for seg in result.get("segments") or []:
        seg_text = _strip_hallucinations(str(seg.get("text") or ""))
        if not seg_text:
            continue
        segments.append({**seg, "text": seg_text})

    return {**result, "text": text, "segments": segments}


def ensure_usable_transcript(text: str) -> None:
    if len(text.strip()) < 40:
        raise ValueError(
            "A transcrição ficou vazia ou sem fala útil. O áudio pode estar mudo, "
            "com muito ruído, ou não ser a gravação da reunião. "
            "Tenta outro ficheiro ou importa VTT/TXT do Google Meet."
        )

    words = text.split()
    if len(words) < 8:
        raise ValueError(
            "Quase não há texto na transcrição — o Whisper não ouviu fala clara. "
            "Confirma que carregaste a gravação certa (não um vídeo com legendas). "
            "Alternativa: exportar transcrição VTT do Google Meet."
        )
