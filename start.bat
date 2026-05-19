@echo off
echo Statistics Story Service Starting...

REM Set Ollama environment variables for larger context
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_MAX_LOADED_MODELS=1

REM Check if Ollama is already running
echo Checking Ollama Server...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Ollama is already running.
) else (
    echo Starting Ollama Server with 16K context...
    start "Ollama" cmd /k "set OLLAMA_NUM_PARALLEL=1 && set OLLAMA_MAX_LOADED_MODELS=1 && ollama serve"
    echo Waiting for Ollama to start...
    timeout /t 5 /nobreak >nul
)

REM Start Backend Server
echo Starting Backend Server...
start "Backend" cmd /k "cd /d %~dp0backend && python main.py"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Start Frontend Development Server
echo Starting Frontend Server...
start "Frontend" cmd /k "cd /d %~dp0frontend && set PORT=17200 && set HOST=0.0.0.0 && npm start"

REM Browser will be opened automatically by npm start
REM timeout /t 10 /nobreak >nul
REM start http://localhost:17200

echo Service Started Successfully!
echo Backend: http://localhost:17202
echo Frontend: http://localhost:17200
pause~