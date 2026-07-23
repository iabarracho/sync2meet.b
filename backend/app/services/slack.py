from __future__ import annotations

import httpx

from ..config import settings
from ..errors import require_slack


def format_action_items_message(action_items: list[dict]) -> str:
    lines: list[str] = []
    for item in action_items:
        slack = item.get("assignee_slack") or item.get("assignee_name") or "unassigned"
        if slack and not slack.startswith("@"):
            slack = f"@{slack}"
        task = item.get("task", "")
        timing = item.get("timing", "")
        line = f"{slack}\n\n{task}"
        if timing:
            line += f" até {timing}"
        lines.append(line)
    return "\n\n".join(lines) if lines else "Sem action items para esta reunião."


async def send_slack_message(channel: str, message: str) -> tuple[str, str | None]:
    require_slack()

    channel = channel or settings.slack_default_channel
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {settings.slack_bot_token}",
        "Content-Type": "application/json",
    }
    payload = {"channel": channel, "text": message}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30)
            data = resp.json()
        if data.get("ok"):
            return "sent", None
        return "failed", _friendly_slack_error(data.get("error", "unknown_error"), channel)
    except Exception as exc:  # noqa: BLE001
        return "failed", str(exc)


def _friendly_slack_error(code: str, channel: str) -> str:
    mapping = {
        "invalid_auth": "Token Slack inválido. Verifica SLACK_BOT_TOKEN no servidor.",
        "not_authed": "Token Slack em falta ou inválido.",
        "channel_not_found": (
            f"Canal «{channel}» não encontrado. "
            "Confirma SLACK_DEFAULT_CHANNEL e convida o bot para esse canal."
        ),
        "not_in_channel": (
            f"O bot Slack não está no canal «{channel}». "
            "No Slack: abre o canal → Integrar apps → adiciona o bot."
        ),
        "is_archived": f"O canal «{channel}» está arquivado.",
        "msg_too_long": "A mensagem Slack é demasiado longa.",
        "rate_limited": "Slack limitou pedidos. Tenta daqui a um minuto.",
    }
    return mapping.get(code, f"Erro Slack: {code}")
