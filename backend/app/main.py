from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings, validate_production_settings
from .errors import ConfigurationError
from .database import init_db
from .deps import get_db
from .middleware.security import SecurityHeadersMiddleware
from .routers import auth_router, dashboard_router, meetings_router, templates_router
from .seed import seed_database

_RETENTION_INTERVAL_SECONDS = 6 * 60 * 60  # 6 horas


async def _retention_loop() -> None:
    import logging

    from .database import SessionLocal
    from .services import retention as retention_service

    logger = logging.getLogger("sync2meet")
    while True:
        await asyncio.sleep(_RETENTION_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            removed = retention_service.purge_expired_meetings(db)
            if removed:
                logger.info("Retention loop: %d reunião(ões) apagada(s)", removed)
        except Exception:
            logger.exception("Retention loop failed")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    logger = logging.getLogger("sync2meet")
    retention_task: asyncio.Task | None = None
    try:
        validate_production_settings()
        init_db()
        from .database import SessionLocal
        from .services import jobs as job_service
        from .services import retention as retention_service

        db = SessionLocal()
        try:
            recovered = job_service.recover_stale_jobs(db)
            if recovered:
                logger.warning("Recovered %d stale job(s) on startup", recovered)
            removed = retention_service.purge_expired_meetings(db)
            if removed:
                logger.info("Retention on startup: %d meeting(s) removed", removed)
            seed_database(db)
            logger.info("Database ready; built-in templates seeded if missing.")
        finally:
            db.close()

        if settings.meeting_retention_days > 0:
            retention_task = asyncio.create_task(_retention_loop())
    except Exception as exc:
        logger.error("Startup failed (database): %s", exc)
        raise
    yield
    if retention_task:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_display_name + " API",
    version="0.1.0",
    description="Meeting lifecycle automation for consultancies and project teams.",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(meetings_router)
app.include_router(templates_router)


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(
    _request: Request, exc: ConfigurationError
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict:
    if settings.is_production:
        return {"status": "ok"}
    return {
        "status": "ok",
        "openai": settings.openai_enabled,
        "transcribe_provider": settings.transcribe_provider,
        "transcribe_use_openai": settings.transcribe_use_openai,
        "slack": settings.slack_enabled,
        "email": settings.email_enabled,
        "auth_enabled": settings.auth_enabled,
        "meeting_retention_days": settings.meeting_retention_days,
    }
