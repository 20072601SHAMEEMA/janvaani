@echo off
cd /d "%~dp0"
echo Installing requirements (first time only)...
python -m pip install -q -r requirements.txt
echo.
echo Starting JanVaani... your browser will open in a few seconds.
echo Keep this window open. Close it to stop the app.
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8000"
python -m uvicorn app.main:app --port 8000
pause
