@echo off
cd /d "%~dp0"

echo ========================================
echo  Sync2meet - Arrancar (rede empresa)
echo ========================================
echo.

call parar-tudo.cmd
echo.

if not exist "backend\.venv\Scripts\python.exe" (
  echo Falta instalar. A correr 1-INSTALAR.cmd ...
  call 1-INSTALAR.cmd
  if errorlevel 1 exit /b 1
)

echo [1/3] Backend (porta 8000, rede local)...
start "Sync2meet Backend" cmd /k "cd /d %~dp0backend && iniciar-api-rede.cmd"

call aguardar-porta.cmd 8000 120
if errorlevel 1 (
  echo ERRO: Backend nao arrancou.
  pause
  exit /b 1
)

echo [2/3] Frontend (porta 3000, rede local)...
start "Sync2meet Frontend Rede" cmd /k "cd /d %~dp0 && 3-FRONTEND-REDE.cmd"

call aguardar-porta.cmd 3000 120
if errorlevel 1 (
  echo ERRO: Frontend nao arrancou.
  pause
  exit /b 1
)

echo.
echo [3/3] Link para partilhar com a empresa:
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=1" %%b in ("%%a") do echo   http://%%b:3000
)
echo.
echo  Tu no mesmo PC: http://127.0.0.1:3000
echo  Parar: parar-tudo.cmd
echo.
echo  Guia para a equipa: TESTES-EQUIPA.txt
echo.
pause
