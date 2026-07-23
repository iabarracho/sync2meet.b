from __future__ import annotations

from unittest.mock import patch

from app.services.auth import email_domain_allowed


def test_email_domain_rejects_subdomain_spoof():
    with patch("app.services.auth.settings") as mock_settings:
        mock_settings.allowed_email_domains_list = ["bocaboca.pt"]
        assert email_domain_allowed("user@evil.bocaboca.pt", role="member") is False


def test_email_domain_allowed_member_when_restricted():
    with patch("app.services.auth.settings") as mock_settings:
        mock_settings.allowed_email_domains_list = ["bocaboca.pt"]
        assert email_domain_allowed("user@bocaboca.pt", role="member") is True
        assert email_domain_allowed("user@gmail.com", role="member") is False


def test_email_domain_open_when_unrestricted():
    with patch("app.services.auth.settings") as mock_settings:
        mock_settings.allowed_email_domains_list = []
        assert email_domain_allowed("user@gmail.com", role="member") is True
        assert email_domain_allowed("user@bocaboca.pt", role="member") is True


def test_email_domain_admin_exempt():
    assert email_domain_allowed("admin@gmail.com", role="admin") is True
