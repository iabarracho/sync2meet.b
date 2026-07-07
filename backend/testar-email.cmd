@echo off
cd /d "%~dp0"

echo ========================================
echo  Sync2meet - Teste SMTP
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERRO: .venv em falta. Corre ARRANCAR.cmd primeiro.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\test_smtp.py
echo.
pause
