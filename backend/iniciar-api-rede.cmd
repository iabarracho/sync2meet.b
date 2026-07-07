@echo off
cd /d "%~dp0"

echo ========================================
echo  Sync2meet - API REDE (porta 8000)
echo ========================================
echo.

call parar-api.cmd
timeout /t 2 /nobreak >nul

call criar-env.cmd

if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
)

.venv\Scripts\pip.exe install -r requirements.txt -q

echo API rede: http://0.0.0.0:8000/api/health
echo Mantem esta janela aberta. Ctrl+C para parar.
echo.
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000
if errorlevel 1 pause
