@echo off
echo Statistics Story Service Starting...

REM Check if Ollama is already running
echo Checking Ollama Server...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Ollama is already running.
) else (
    echo Starting Ollama Server...
    start "Ollama" cmd /k "ollama serve"
    echo Waiting for Ollama to start...
    timeout /t 3 /nobreak >nul
)

REM Start Backend Server
echo Starting Backend Server...
start "Backend" cmd /k "cd /d %~dp0backend && python main.py"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Start Frontend Development Server
echo Starting Frontend Server...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm start"

REM Browser will be opened automatically by npm start
REM timeout /t 10 /nobreak >nul
REM start http://localhost:3006

echo Service Started Successfully!
echo Backend: http://localhost:8001
echo Frontend: http://localhost:3006
pause~