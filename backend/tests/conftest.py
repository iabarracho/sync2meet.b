from __future__ import annotations

import os
import tempfile

import pytest

_tmp_storage = tempfile.mkdtemp()
_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["AUTH_ENABLED"] = "true"
os.environ["AUTH_SECRET"] = "test-secret-for-pytest-only-not-production"
os.environ["ALLOWED_EMAIL_DOMAINS"] = "bocaboca.pt"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["STORAGE_DIR"] = _tmp_storage
os.environ["APP_ENV"] = "development"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.database import Base, engine  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    monkeypatch.setattr("app.config.settings.auth_enabled", True)
    monkeypatch.setattr(
        "app.config.settings.auth_secret",
        "test-secret-for-pytest-only-not-production",
    )
