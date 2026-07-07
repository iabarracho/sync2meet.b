from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: str = "development"
    app_display_name: str = "Sync2meet - BocàBoca"
    # URL pública do site (ex. https://sync2meet.empresa.pt) — usado em CORS e cookies
    app_public_url: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # SQLite por defeito (funciona sem Docker). Para PostgreSQL, define DATABASE_URL no .env
    database_url: str = "sqlite:///./sync2meet.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    storage_dir: str = "./storage"

    # OpenAI (apenas chat: ata, agenda, templates — não transcrição)
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"

    # Transcrição: local (faster-whisper) ou openai (rápido, ~0,006 USD/min)
    # auto = OpenAI se houver chave, senão local
    transcribe_provider: str = "auto"
    faster_whisper_model: str = "base"
    faster_whisper_device: str = "cpu"
    faster_whisper_compute_type: str = "int8"
    faster_whisper_cpu_threads: int = 0  # 0 = todos os núcleos CPU
    faster_whisper_beam_size: int = 1  # 1 = mais rápido (5 = mais preciso)
    # Vazio = deteção automática (reuniões PT + EN). Use "pt" ou "en" para forçar.
    faster_whisper_language: str = ""
    faster_whisper_initial_prompt: str = (
        "Reunião profissional. Participantes falam português europeu e inglês. "
        "Transcrever fielmente ambos os idiomas, nomes de clientes e projetos."
    )
    faster_whisper_vad_filter: bool = True

    # Slack
    slack_bot_token: str | None = None
    slack_default_channel: str = "#general"

    # Email / SMTP
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "Sync2meet <no-reply@sync2meet.app>"
    smtp_use_tls: bool = True

    # Limits & reliability
    max_participants_per_meeting: int = 50
    max_transcript_chars: int = 2_000_000
    max_upload_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB — reuniões longas (1h+)
    allowed_upload_extensions: str = ".webm,.mp4,.mp3,.wav,.m4a,.ogg,.vtt,.txt"
    job_stale_minutes: int = 360  # 6 h — transcrição local de áudio longo
    ffmpeg_timeout_seconds: int = 3600  # 1 h — compressão/divisão ffmpeg
    job_poll_max_attempts: int = 1200
    # Comma-separated Slack channels; empty = only slack_default_channel allowed
    slack_allowed_channels: str = ""

    # Auth (multi-user team)
    auth_enabled: bool = True
    auth_secret: str = "change-me-in-production"
    auth_token_hours: int = 24
    allow_registration: bool = True
    max_team_users: int = 30
    # Só em dev local: auto-login como primeiro user quando AUTH_ENABLED=false
    dev_auth_bypass: bool = False
    # Confiar em X-Forwarded-For (só atrás de nginx/proxy de confiança)
    trusted_proxy: bool = False
    job_pending_stale_minutes: int = 30
    # Reuniões e ficheiros apagados automaticamente após N dias (0 = desativado)
    meeting_retention_days: int = 15
    # Opcional: bootstrap inicial name:email:password (não necessário com registo aberto)
    team_users: str = ""
    # Registo/login: só emails destes domínios (ex. bocaboca.pt). Admin isento.
    allowed_email_domains: str = "bocaboca.pt"

    @field_validator("smtp_user", "smtp_password", mode="before")
    @classmethod
    def normalize_smtp_secret(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().strip('"').strip("'")
        if " " in cleaned and "@" not in cleaned:
            cleaned = cleaned.replace(" ", "")
        return cleaned or None

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.app_public_url:
            public = self.app_public_url.rstrip("/")
            if public not in origins:
                origins.append(public)
        return origins

    @property
    def cors_origin_regex(self) -> str | None:
        if self.is_production:
            return None
        return r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?"

    @property
    def cookie_secure(self) -> bool:
        return self.is_production and self.app_public_url.startswith("https://")

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        if not p.is_absolute():
            p = (ENV_FILE.parent / p).resolve()
        else:
            p = p.resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def transcribe_use_openai(self) -> bool:
        mode = self.transcribe_provider.strip().lower()
        if mode == "openai":
            return self.openai_enabled
        if mode == "local":
            return False
        return self.openai_enabled  # auto

    @property
    def faster_whisper_cpu_threads_resolved(self) -> int:
        if self.faster_whisper_cpu_threads > 0:
            return self.faster_whisper_cpu_threads
        import os

        return os.cpu_count() or 4

    @property
    def slack_enabled(self) -> bool:
        return bool(self.slack_bot_token)

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def slack_allowed_channels_list(self) -> list[str]:
        if not self.slack_allowed_channels.strip():
            return [self.slack_default_channel]
        return [
            c.strip()
            for c in self.slack_allowed_channels.split(",")
            if c.strip()
        ]

    @property
    def allowed_email_domains_list(self) -> list[str]:
        return [
            d.strip().lower().lstrip("@")
            for d in self.allowed_email_domains.split(",")
            if d.strip()
        ]


    @property
    def allowed_upload_extensions_list(self) -> list[str]:
        return [
            e.strip().lower()
            for e in self.allowed_upload_extensions.split(",")
            if e.strip()
        ]


def validate_production_settings() -> None:
    if not settings.is_production:
        if settings.auth_enabled and settings.auth_secret in (
            "",
            "change-me-in-production",
            "change-me-use-a-long-random-string",
        ):
            import warnings

            warnings.warn(
                "AUTH_SECRET fraco — define uma string aleatória longa antes de produção.",
                stacklevel=2,
            )
        return
    if not settings.auth_enabled:
        raise RuntimeError("AUTH_ENABLED deve ser true em produção.")
    if settings.auth_enabled and settings.auth_secret in (
        "",
        "change-me-in-production",
        "change-me-use-a-long-random-string",
    ):
        raise RuntimeError(
            "AUTH_SECRET inseguro em produção. Define uma string aleatória longa no .env."
        )
    if settings.auth_enabled and not settings.team_users.strip() and not settings.allow_registration:
        raise RuntimeError(
            "Em produção: ativa ALLOW_REGISTRATION=true ou define TEAM_USERS no .env."
        )
    if settings.auth_enabled and not settings.allowed_email_domains_list:
        raise RuntimeError(
            "ALLOWED_EMAIL_DOMAINS não pode estar vazio em produção."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
