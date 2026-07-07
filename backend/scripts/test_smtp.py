"""Test SMTP config (does not print password). Run: python scripts/test_smtp.py"""
from __future__ import annotations

import smtplib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings, ENV_FILE  # noqa: E402


def main() -> int:
    print(f"ENV_FILE: {ENV_FILE} (exists={ENV_FILE.exists()})")
    print(f"smtp_host: {settings.smtp_host}")
    print(f"smtp_port: {settings.smtp_port}")
    print(f"smtp_user: {settings.smtp_user}")
    print(f"smtp_from: {settings.smtp_from}")
    print(f"smtp_use_tls: {settings.smtp_use_tls}")
    pw = settings.smtp_password or ""
    print(f"smtp_password_set: {bool(pw)} (length={len(pw)})")
    print(f"email_enabled: {settings.email_enabled}")

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            if line.strip().startswith("SMTP_") and "=" in line:
                key, _, val = line.partition("=")
                val = val.strip()
                if "PASSWORD" in key:
                    print(f"  {key.strip()}: len={len(val)}")
                else:
                    print(f"  {key.strip()}: {val}")

    if not settings.email_enabled:
        print("SMTP login: SKIP (config incomplete)")
        return 1

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls()
                server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
        print("SMTP login: OK")
        return 0
    except Exception as exc:
        print(f"SMTP login: FAIL ({type(exc).__name__})")
        print(str(exc)[:300])
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
