from __future__ import annotations

import logging

logger = logging.getLogger("sync2meet.upload")

# Assinaturas comuns (primeiros bytes) para gravações
_SIGNATURES: dict[str, list[bytes]] = {
    ".webm": [b"\x1a\x45\xdf\xa3"],
    ".mkv": [b"\x1a\x45\xdf\xa3"],
    ".mp4": [b"ftyp"],
    ".mov": [b"ftyp"],
    ".m4a": [b"ftyp"],
    ".mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa"],
    ".wav": [b"RIFF"],
    ".ogg": [b"OggS"],
}

_MEDIA_EXTS = tuple(_SIGNATURES.keys())


def _matches_mp4_family(head: bytes) -> bool:
    # ISO BMFF: size(4) + 'ftyp' at offset 4, sometimes after a larger box
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return True
    return b"ftyp" in head[:64]


def _matches_webm_family(head: bytes) -> bool:
    return head.startswith(b"\x1a\x45\xdf\xa3")


def _detect_media_ext(head: bytes) -> str | None:
    if not head:
        return None
    if _matches_webm_family(head):
        return ".webm"
    if _matches_mp4_family(head):
        return ".mp4"
    if head.startswith(b"RIFF") and b"WAVE" in head[:16]:
        return ".wav"
    if head.startswith(b"OggS"):
        return ".ogg"
    if head.startswith(b"ID3") or head[:2] in {
        b"\xff\xfb",
        b"\xff\xf3",
        b"\xff\xf2",
        b"\xff\xfa",
    }:
        return ".mp3"
    return None


def _matches_claimed(head: bytes, ext: str) -> bool:
    if ext in (".mp4", ".m4a", ".mov"):
        return _matches_mp4_family(head)
    if ext in (".webm", ".mkv"):
        return _matches_webm_family(head)
    for sig in _SIGNATURES.get(ext, []):
        if head.startswith(sig):
            return True
    return False


def validate_recording_header(file_obj, ext: str) -> None:
    """Valida magic bytes antes de gravar upload (extensão sozinha não basta).

    Se a extensão não bater com o conteúdo mas o ficheiro for outro formato
    de áudio/vídeo conhecido (ex. MP4 com nome .webm do tl;dv), aceita.
    """
    ext = ext.lower()
    if ext not in _SIGNATURES:
        return
    pos = file_obj.tell() if hasattr(file_obj, "tell") else None
    head = file_obj.read(64)
    if hasattr(file_obj, "seek") and pos is not None:
        file_obj.seek(pos)
    elif hasattr(file_obj, "seek"):
        file_obj.seek(0)

    if not head:
        raise ValueError("Ficheiro vazio ou ilegível.")

    if _matches_claimed(head, ext):
        return

    detected = _detect_media_ext(head)
    if detected and detected != ext:
        logger.info(
            "Upload com extensão %s mas conteúdo %s — a aceitar (compat tl;dv/Meet)",
            ext,
            detected,
        )
        return

    if detected is None and ext in _MEDIA_EXTS:
        # Alguns MP4 raros / exports: se ffmpeg conseguir, preferimos mensagem útil
        raise ValueError(
            f"O conteúdo não corresponde a um ficheiro {ext.upper()} válido. "
            "No tl;dv / Meet, descarrega em MP4 ou MP3 e volta a carregar "
            "(não uses um link ou ficheiro HTML renomeado)."
        )

    raise ValueError(
        f"O conteúdo não corresponde a um ficheiro {ext.upper()} válido."
    )
