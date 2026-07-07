@echo off
cd /d "%~dp0"
echo A parar API na porta 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
  echo A terminar processo PID %%a
  taskkill /PID %%a /F >nul 2>&1
)
echo Feito.
