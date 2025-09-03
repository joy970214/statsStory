@echo off
echo Statistics Story Service Starting...

REM Start Backend Server
echo Starting Backend Server...
start "Backend" cmd /k "cd /d %~dp0backend && python main.py"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Start Frontend Development Server  
echo Starting Frontend Server...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm start"

REM Auto open browser after 10 seconds
timeout /t 10 /nobreak >nul
start http://localhost:3006

echo Service Started Successfully!
echo Backend: http://localhost:8001
echo Frontend: http://localhost:3006
pause~