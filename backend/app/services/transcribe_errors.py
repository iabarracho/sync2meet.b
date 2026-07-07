from __future__ import annotations


def friendly_transcribe_error(exc: BaseException) -> str:
    msg = str(exc)
    lower = msg.lower()
    if "ffmpeg" in lower or "no such file" in lower and "audio" in lower:
        return (
            "Não foi possível processar o áudio. Confirma que o ficheiro é uma "
            "gravação válida (MP4, WEBM, MP3) ou importa VTT/TXT do Google Meet."
        )
    if "cuda" in lower or "cudnn" in lower:
        return (
            "Erro na GPU para transcrição. Define FASTER_WHISPER_DEVICE=cpu no .env "
            "e reinicia o backend."
        )
    if "out of memory" in lower or "oom" in lower:
        return (
            "Memória insuficiente para transcrever este ficheiro. "
            "Usa um modelo mais pequeno (FASTER_WHISPER_MODEL=base ou tiny) "
            "ou importa a transcrição VTT do Google Meet."
        )
    if "model" in lower and ("download" in lower or "hub" in lower):
        return (
            "Não foi possível carregar o modelo faster-whisper. "
            "Verifica ligação à internet na primeira execução (download do modelo) "
            "ou o valor de FASTER_WHISPER_MODEL no .env."
        )
    if "insufficient_quota" in lower or "quota" in lower:
        return (
            "Quota OpenAI esgotada. Verifica billing em platform.openai.com "
            "ou define TRANSCRIBE_PROVIDER=local no .env."
        )
    return msg or "Falha na transcrição."
