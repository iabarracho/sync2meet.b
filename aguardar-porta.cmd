@echo off
setlocal
set PORT=%~1
set MAX=%~2
if "%PORT%"=="" exit /b 1
if "%MAX%"=="" set MAX=90
set /a ELAPSED=0
:wait_loop
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 exit /b 0
if %ELAPSED% geq %MAX% exit /b 1
timeout /t 2 /nobreak >nul
set /a ELAPSED+=2
goto wait_loop
