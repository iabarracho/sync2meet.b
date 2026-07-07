@echo off
cd /d "%~dp0"

echo ========================================
echo  Sync2meet - Instalar dependencias
echo ========================================
echo.

echo [1/2] Backend (Python)...
cd backend
if not exist ".venv\Scripts\python.exe" (
  echo A criar ambiente virtual .venv ...
  py -m venv .venv
  if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instala de python.org
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

call criar-env.cmd

cd ..
echo.
echo [2/2] Frontend (Node/npm)...
cd frontend
where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo ERRO: Node.js nao encontrado. Instala de nodejs.org
  pause
  exit /b 1
)

call npm.cmd install
if errorlevel 1 (
  echo ERRO ao instalar dependencias npm.
  pause
  exit /b 1
)

cd ..
echo.
echo ========================================
echo  Instalacao concluida!
echo ========================================
echo Proximo: duplo-clique em ARRANCAR.cmd
echo.
pause
