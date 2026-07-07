from __future__ import annotations



import logging

import subprocess

import tempfile

from pathlib import Path



from ..config import settings



logger = logging.getLogger("sync2meet.audio")



# Tamanho máximo por chunk (evita OOM em gravações muito longas).

MAX_TRANSCRIBE_CHUNK_BYTES = 24 * 1024 * 1024

SEGMENT_SECONDS = 600  # 10 minutes per chunk if still too large





def _ffmpeg_exe() -> str:

    import imageio_ffmpeg



    return imageio_ffmpeg.get_ffmpeg_exe()





def _run_ffmpeg(args: list[str]) -> None:

    cmd = [_ffmpeg_exe(), *args]

    proc = subprocess.run(

        cmd,

        capture_output=True,

        text=True,

        timeout=settings.ffmpeg_timeout_seconds,

    )

    if proc.returncode != 0:

        detail = (proc.stderr or proc.stdout or "ffmpeg failed").strip()

        raise RuntimeError(detail[-500:])





def _compress_for_transcription(source: Path, dest: Path) -> None:

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Mono 16 kHz — formato ideal para Whisper / faster-whisper.

    _run_ffmpeg(

        [

            "-y",

            "-i",

            str(source),

            "-vn",

            "-ac",

            "1",

            "-ar",

            "16000",

            "-c:a",

            "libmp3lame",

            "-q:a",

            "2",

            str(dest),

        ]

    )





def _split_for_transcription(source: Path, out_dir: Path) -> list[Path]:

    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = str(out_dir / "part_%03d.mp3")

    _run_ffmpeg(

        [

            "-y",

            "-i",

            str(source),

            "-f",

            "segment",

            "-segment_time",

            str(SEGMENT_SECONDS),

            "-vn",

            "-ac",

            "1",

            "-ar",

            "16000",

            "-c:a",

            "libmp3lame",

            "-q:a",

            "2",

            pattern,

        ]

    )

    parts = sorted(out_dir.glob("part_*.mp3"))

    if not parts:

        raise RuntimeError("Nao foi possivel dividir o audio para transcricao.")

    oversized = [p for p in parts if p.stat().st_size > MAX_TRANSCRIBE_CHUNK_BYTES]

    if oversized:

        raise RuntimeError(

            "Audio demasiado longo mesmo apos divisao. "

            "Usa um ficheiro mais curto ou importa transcrição VTT/TXT."

        )

    return parts





def prepare_audio_files(source: Path) -> tuple[list[Path], Path | None]:

    """

    Returns (files_to_transcribe, temp_dir_to_cleanup).

    temp_dir is set when we created transcoded files in a temp folder.

    """

    size = source.stat().st_size

    if size <= MAX_TRANSCRIBE_CHUNK_BYTES:

        return [source], None



    logger.info(

        "Audio %s (%d bytes) — a comprimir/dividir para transcricao local",

        source.name,

        size,

    )



    temp_dir = Path(tempfile.mkdtemp(prefix="sync2meet_audio_"))

    compressed = temp_dir / f"{source.stem}_compressed.mp3"

    _compress_for_transcription(source, compressed)



    if compressed.stat().st_size <= MAX_TRANSCRIBE_CHUNK_BYTES:

        return [compressed], temp_dir



    parts = _split_for_transcription(compressed, temp_dir / "parts")

    return parts, temp_dir





def cleanup_temp_dir(temp_dir: Path | None) -> None:

    if not temp_dir or not temp_dir.exists():

        return

    import shutil



    try:

        shutil.rmtree(temp_dir, ignore_errors=True)

    except OSError:

        logger.warning("Could not remove temp audio dir %s", temp_dir)


