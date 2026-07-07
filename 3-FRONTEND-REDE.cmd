@echo off
cd /d "%~dp0frontend"

echo ========================================
echo  Sync2meet - Frontend REDE (porta 3000)
echo ========================================
echo.

echo.

if not exist ".env.local" (
  echo NEXT_PUBLIC_AUTH_ENABLED=true> ".env.local"
)

if not exist "node_modules\" (
  echo A instalar dependencias...
  call npm.cmd install
  if errorlevel 1 (
    echo ERRO na instalacao. Corre 1-INSTALAR.cmd na raiz.
    pause
    exit /b 1
  )
)

netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
  echo Frontend ja esta a correr na porta 3000.
  pause
  exit /b 0
)

echo A aceitar ligacoes da rede local (0.0.0.0:3000)
echo Mantem esta janela aberta. Ctrl+C para parar.
echo.
call npm.cmd run dev:rede
if errorlevel 1 pause
