@echo off
cd /d "%~dp0"

echo ========================================
echo  Sync2meet - Arrancar
echo ========================================
echo.

call parar-tudo.cmd
echo.

if not exist "backend\.venv\Scripts\python.exe" (
  echo Falta instalar. A correr 1-INSTALAR.cmd ...
  call 1-INSTALAR.cmd
  if errorlevel 1 exit /b 1
)

if not exist "frontend\node_modules\" (
  echo A instalar frontend...
  cd frontend
  call npm.cmd install
  cd ..
  if errorlevel 1 (
    echo ERRO no npm. Corre 1-INSTALAR.cmd
    pause
    exit /b 1
  )
)

echo [1/3] Backend (porta 8000)...
start "Sync2meet Backend" cmd /k "cd /d %~dp0backend && iniciar-api.cmd"

call aguardar-porta.cmd 8000 120
if errorlevel 1 (
  echo ERRO: Backend nao arrancou. Ve a janela Sync2meet Backend.
  pause
  exit /b 1
)
echo Backend OK.

echo.
echo [2/3] Frontend (porta 3000)...
start "Sync2meet Frontend" cmd /k "cd /d %~dp0 && 3-FRONTEND.cmd"

call aguardar-porta.cmd 3000 120
if errorlevel 1 (
  echo ERRO: Frontend nao arrancou. Ve a janela Sync2meet Frontend.
  pause
  exit /b 1
)
echo Frontend OK.

echo.
echo [3/3] A abrir browser...
start http://127.0.0.1:3000

echo.
echo Sync2meet a correr!
echo  Site: http://127.0.0.1:3000
echo  API:  http://127.0.0.1:8000/api/health
echo  Parar: parar-tudo.cmd
echo.
pause
