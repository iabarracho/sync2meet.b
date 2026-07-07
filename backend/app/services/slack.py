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
        return "failed", data.get("error", "unknown_error")
    except Exception as exc:  # noqa: BLE001
        return "failed", str(exc)
