@echo off
cd /d "%~dp0"

echo ========================================
echo  Sync2meet - API (porta 8000)
echo ========================================
echo.

call parar-api.cmd
timeout /t 2 /nobreak >nul

call criar-env.cmd

echo A preparar Python...
if not exist ".venv\Scripts\python.exe" (
  echo A criar .venv ...
  py -m venv .venv
  if errorlevel 1 (
    echo ERRO: Instala Python 3.11+ de python.org
    pause
    exit /b 1
  )
)

.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
  echo ERRO ao instalar dependencias Python.
  pause
  exit /b 1
)

echo.
echo API: http://127.0.0.1:8000/api/health
echo Mantem esta janela aberta. Ctrl+C para parar.
echo.
.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 3600
if errorlevel 1 (
  echo.
  echo ERRO na porta 8000. Corre parar-api.cmd na pasta backend.
  pause
)
