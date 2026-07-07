from __future__ import annotations

from app.services.auth import email_domain_allowed


def test_email_domain_rejects_subdomain_spoof():
    assert email_domain_allowed("user@evil.bocaboca.pt", role="member") is False


def test_email_domain_allowed_member():
    assert email_domain_allowed("user@bocaboca.pt", role="member") is True
    assert email_domain_allowed("user@gmail.com", role="member") is False


def test_email_domain_admin_exempt():
    assert email_domain_allowed("admin@gmail.com", role="admin") is True
