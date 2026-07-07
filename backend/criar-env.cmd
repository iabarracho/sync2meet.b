@echo off
cd /d "%~dp0"
if exist ".env" exit /b 0

(
echo DATABASE_URL=sqlite:///./sync2meet.db
echo APP_ENV=development
echo CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
echo STORAGE_DIR=./storage
echo OPENAI_API_KEY=
echo OPENAI_CHAT_MODEL=gpt-4o-mini
echo FASTER_WHISPER_MODEL=base
echo FASTER_WHISPER_DEVICE=cpu
echo FASTER_WHISPER_COMPUTE_TYPE=int8
echo FASTER_WHISPER_LANGUAGE=
echo SLACK_BOT_TOKEN=
echo SLACK_DEFAULT_CHANNEL=#general
echo SMTP_HOST=
echo SMTP_PORT=587
echo SMTP_USER=
echo SMTP_PASSWORD=
echo SMTP_FROM=Sync2meet ^<no-reply@sync2meet.app^>
echo SMTP_USE_TLS=true
echo AUTH_ENABLED=true
echo AUTH_SECRET=change-me-use-a-long-random-string
echo ALLOW_REGISTRATION=true
echo MAX_TEAM_USERS=30
) > .env

echo Criado backend\.env — configura OPENAI_API_KEY e AUTH_SECRET.
