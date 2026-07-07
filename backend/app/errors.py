class ConfigurationError(Exception):
    """Configuração em falta em backend/.env."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "OPENAI_API_KEY em falta em backend/.env. Reinicia o backend após guardar."
        )


def require_openai() -> None:
    from .config import settings

    if not settings.openai_enabled:
        raise ConfigurationError()


def require_email() -> None:
    from .config import settings

    if not settings.email_enabled:
        raise ConfigurationError(
            "SMTP em falta. Configura SMTP_HOST, SMTP_USER e SMTP_PASSWORD em backend/.env."
        )


def require_slack() -> None:
    from .config import settings

    if not settings.slack_enabled:
        raise ConfigurationError(
            "Slack em falta. Configura SLACK_BOT_TOKEN em backend/.env."
        )
