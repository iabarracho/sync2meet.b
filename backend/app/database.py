from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

logger = logging.getLogger("sync2meet.db")

_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)
engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_column_names(table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _migrate_schema() -> None:
    """Lightweight migrations for SQLite dev DBs (create_all does not alter tables)."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        if "email_distributions" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE email_distributions (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        meeting_id VARCHAR NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
                        summary_id VARCHAR NOT NULL REFERENCES summaries(id),
                        idempotency_key VARCHAR UNIQUE,
                        status VARCHAR NOT NULL DEFAULT 'pending',
                        created_at DATETIME NOT NULL,
                        completed_at DATETIME,
                        FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE,
                        FOREIGN KEY(summary_id) REFERENCES summaries(id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_email_distributions_meeting_id "
                    "ON email_distributions (meeting_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_email_distributions_idempotency_key "
                    "ON email_distributions (idempotency_key)"
                )
            )
            logger.info("Created email_distributions table")

        if "email_logs" in tables:
            cols = _sqlite_column_names("email_logs")
            if "distribution_id" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE email_logs ADD COLUMN distribution_id VARCHAR "
                        "REFERENCES email_distributions(id) ON DELETE CASCADE"
                    )
                )
                logger.info("Added email_logs.distribution_id column")

        if "processing_jobs" in tables:
            cols = _sqlite_column_names("processing_jobs")
            if "active_key" not in cols:
                conn.execute(
                    text("ALTER TABLE processing_jobs ADD COLUMN active_key VARCHAR")
                )
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_processing_jobs_active_key "
                        "ON processing_jobs (active_key)"
                    )
                )
                logger.info("Added processing_jobs.active_key column")

        if "users" in tables:
            cols = _sqlite_column_names("users")
            if "password_hash" not in cols:
                conn.execute(
                    text("ALTER TABLE users ADD COLUMN password_hash VARCHAR")
                )
                logger.info("Added users.password_hash column")
            if "token_version" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN token_version INTEGER "
                        "NOT NULL DEFAULT 0"
                    )
                )
                logger.info("Added users.token_version column")

        if "password_reset_tokens" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE password_reset_tokens (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token_hash VARCHAR NOT NULL,
                        expires_at DATETIME NOT NULL,
                        used_at DATETIME,
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id "
                    "ON password_reset_tokens (user_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash "
                    "ON password_reset_tokens (token_hash)"
                )
            )
            logger.info("Created password_reset_tokens table")

        if "audit_events" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE audit_events (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        action VARCHAR NOT NULL,
                        user_id VARCHAR,
                        user_email VARCHAR,
                        resource_type VARCHAR,
                        resource_id VARCHAR,
                        detail TEXT,
                        meta JSON,
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_audit_events_action "
                    "ON audit_events (action)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_audit_events_created_at "
                    "ON audit_events (created_at)"
                )
            )
            logger.info("Created audit_events table")

        if "email_distributions" in tables:
            conn.execute(
                text("DROP INDEX IF EXISTS ix_email_distributions_idempotency_key")
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_distribution_meeting_idempotency "
                    "ON email_distributions (meeting_id, idempotency_key)"
                )
            )

        if "meetings" in tables:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_meetings_owner_id "
                    "ON meetings (owner_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_meetings_updated_at "
                    "ON meetings (updated_at)"
                )
            )


def init_db() -> None:
    from . import models  # noqa: F401

    if settings.database_url.startswith("sqlite"):
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA busy_timeout=30000"))
            conn.commit()

    Base.metadata.create_all(bind=engine)
    _migrate_schema()
