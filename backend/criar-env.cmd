@echo off
cd /d "%~dp0"
if exist ".env" exit /b 0

(
echo DATABASE_URL=sqlite:///./sync2meet.db
echo APP_ENV=development
echo APP_PUBLIC_URL=
echo CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
echo STORAGE_DIR=./storage
echo API_HOST=0.0.0.0
echo API_PORT=8000
echo.
echo OPENAI_API_KEY=
echo OPENAI_CHAT_MODEL=gpt-4o-mini
echo.
echo TRANSCRIBE_PROVIDER=local
echo FASTER_WHISPER_MODEL=base
echo FASTER_WHISPER_DEVICE=cpu
echo FASTER_WHISPER_COMPUTE_TYPE=int8
echo FASTER_WHISPER_CPU_THREADS=0
echo FASTER_WHISPER_BEAM_SIZE=1
echo FASTER_WHISPER_LANGUAGE=
echo.
echo SLACK_BOT_TOKEN=
echo SLACK_DEFAULT_CHANNEL=#general
echo.
echo SMTP_HOST=
echo SMTP_PORT=587
echo SMTP_USER=
echo SMTP_PASSWORD=
echo SMTP_FROM=Sync2meet ^<no-reply@sync2meet.app^>
echo SMTP_USE_TLS=true
echo.
echo AUTH_ENABLED=true
echo AUTH_SECRET=change-me-use-a-long-random-string
echo AUTH_TOKEN_HOURS=24
echo PASSWORD_RESET_HOURS=1
echo ALLOW_REGISTRATION=true
echo MAX_TEAM_USERS=40
echo MEETING_RETENTION_DAYS=15
echo ALLOWED_EMAIL_DOMAINS=bocaboca.pt
echo ADMIN_EMAILS=
echo TRUSTED_PROXY=false
echo DEV_AUTH_BYPASS=false
echo MAX_UPLOAD_BYTES=2147483648
echo FFMPEG_TIMEOUT_SECONDS=3600
echo JOB_STALE_MINUTES=360
echo JOB_PENDING_STALE_MINUTES=30
) > .env

echo Criado backend\.env — configura OPENAI_API_KEY, AUTH_SECRET e SMTP.
