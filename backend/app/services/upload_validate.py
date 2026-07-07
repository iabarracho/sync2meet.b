from __future__ import annotations

import logging

logger = logging.getLogger("sync2meet.upload")

# Assinaturas comuns (primeiros bytes) para gravações
_SIGNATURES: dict[str, list[bytes]] = {
    ".webm": [b"\x1a\x45\xdf\xa3"],
    ".mp4": [b"\x00\x00\x00", b"ftyp"],  # ftyp at offset 4
    ".mov": [b"\x00\x00\x00", b"ftyp"],
    ".m4a": [b"\x00\x00\x00", b"ftyp"],
    ".mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],
    ".wav": [b"RIFF"],
    ".ogg": [b"OggS"],
}


def _matches_mp4_family(head: bytes) -> bool:
    return len(head) >= 8 and head[4:8] == b"ftyp"


def validate_recording_header(file_obj, ext: str) -> None:
    """Valida magic bytes antes de gravar upload (extensão sozinha não basta)."""
    ext = ext.lower()
    if ext not in _SIGNATURES:
        return
    pos = file_obj.tell() if hasattr(file_obj, "tell") else None
    head = file_obj.read(16)
    if hasattr(file_obj, "seek") and pos is not None:
        file_obj.seek(pos)
    elif hasattr(file_obj, "seek"):
        file_obj.seek(0)

    if not head:
        raise ValueError("Ficheiro vazio ou ilegível.")

    if ext in (".mp4", ".m4a", ".mov"):
        if not _matches_mp4_family(head):
            raise ValueError(
                f"O ficheiro não parece ser {ext.upper()} válido. "
                "Verifica o formato da gravação."
            )
        return

    for sig in _SIGNATURES[ext]:
        if ext == ".mp4":
            continue
        if head.startswith(sig):
            return
        if sig == b"\x00\x00\x00" and _matches_mp4_family(head):
            return

    raise ValueError(
        f"O conteúdo não corresponde a um ficheiro {ext.upper()} válido."
    )
